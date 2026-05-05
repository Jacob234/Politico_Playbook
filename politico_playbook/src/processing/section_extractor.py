"""Section-aware Stage 2 extractor — bridges raw_emails store and OpenRouter.

This is the new entry point for entity extraction, replacing the
ANTHROPIC-SDK-direct claude_nlp_processor.py. The old processor remains in
the codebase for reference but is deprecated.

Pipeline per email:
  1. Read RawEmail from SQLite.
  2. Look up the newsletter's parser in the registry.
  3. Parse the plaintext into Sections (sponsor blocks stripped, sections
     classified by section_taxonomy.yaml).
  4. For each section that's NOT skip_extraction:
     a. Pick the section-type-specific prompt from extraction_prompts.yaml.
     b. Call OpenRouter via the model-agnostic client.
     c. Persist the parsed JSON result.
  5. Mark the email as 'parsed' (or 'failed') in raw_emails.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

import yaml

from politico_playbook.src.ingestion.newsletter_registry import NewsletterRegistry
from politico_playbook.src.ingestion.parser_base import (
    SectionTaxonomy,
    get_parser,
)
from politico_playbook.src.ingestion.raw_store import RawEmail, RawEmailStore
from politico_playbook.src.llm.openrouter_client import LLMResponse, OpenRouterClient


logger = logging.getLogger("processing.section_extractor")


# ---------------------------------------------------------------------------
# Extraction-results schema, added alongside the existing raw_emails table.
# ---------------------------------------------------------------------------
EXTRACTIONS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS extractions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    gmail_message_id  TEXT NOT NULL,
    section_index     INTEGER NOT NULL,
    section_header    TEXT,
    section_type      TEXT NOT NULL,
    model_id          TEXT NOT NULL,
    prompt_tokens     INTEGER,
    completion_tokens INTEGER,
    raw_response      TEXT,            -- full LLM response
    parsed_json       TEXT,            -- JSON of structured output (or NULL)
    extraction_status TEXT NOT NULL,   -- 'ok' | 'parse_failed' | 'api_failed'
    extracted_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (gmail_message_id) REFERENCES raw_emails(gmail_message_id),
    UNIQUE (gmail_message_id, section_index, model_id)
);

CREATE INDEX IF NOT EXISTS idx_extractions_msg
    ON extractions(gmail_message_id);
CREATE INDEX IF NOT EXISTS idx_extractions_type
    ON extractions(section_type);
"""


def _ensure_extractions_table(db_path: str | Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(EXTRACTIONS_SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Prompt loading with `inherit:` resolution.
# ---------------------------------------------------------------------------
@dataclass
class PromptConfig:
    system: str
    user_template: str
    json_schema: dict


class PromptRegistry:
    def __init__(self, raw: dict):
        self._raw = raw or {}
        self._resolved: dict[str, PromptConfig] = {}
        # Eagerly resolve `inherit:` to catch errors at load time.
        for key in self._raw:
            self._resolve(key, set())

    @classmethod
    def load(cls, path: str | Path) -> "PromptRegistry":
        with open(path, "r", encoding="utf-8") as f:
            return cls(yaml.safe_load(f) or {})

    def _resolve(self, key: str, seen: set[str]) -> PromptConfig:
        if key in self._resolved:
            return self._resolved[key]
        if key in seen:
            raise ValueError(f"Cyclic inherit chain at {key!r}")
        seen.add(key)
        entry = self._raw.get(key)
        if entry is None:
            raise KeyError(f"No prompt config for section_type {key!r}")
        if "inherit" in entry:
            base = self._resolve(entry["inherit"], seen)
            cfg = PromptConfig(
                system=entry.get("system", base.system),
                user_template=entry.get("user_template", base.user_template),
                json_schema=entry.get("json_schema", base.json_schema),
            )
        else:
            cfg = PromptConfig(
                system=entry["system"],
                user_template=entry["user_template"],
                json_schema=entry["json_schema"],
            )
        self._resolved[key] = cfg
        return cfg

    def for_section_type(self, section_type: str) -> PromptConfig:
        # Falls back to 'unclassified' for unknown types.
        if section_type in self._resolved:
            return self._resolved[section_type]
        return self._resolved["unclassified"]


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------
@dataclass
class ExtractionRecord:
    gmail_message_id: str
    section_index: int
    section_header: Optional[str]
    section_type: str
    model_id: str
    prompt_tokens: int
    completion_tokens: int
    raw_response: str
    parsed_json: Optional[str]
    extraction_status: str  # 'ok' | 'parse_failed' | 'api_failed'


class SectionExtractor:
    def __init__(
        self,
        db_path: str | Path,
        registry: NewsletterRegistry,
        taxonomy: SectionTaxonomy,
        prompts: PromptRegistry,
        llm: OpenRouterClient,
    ):
        self.db_path = Path(db_path)
        self.registry = registry
        self.taxonomy = taxonomy
        self.prompts = prompts
        self.llm = llm
        _ensure_extractions_table(self.db_path)
        self.store = RawEmailStore(self.db_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def process_email(self, email: RawEmail) -> list[ExtractionRecord]:
        nl = self.registry.get(email.newsletter_slug)
        parser_name = nl.parser if nl else "default"
        parser = get_parser(
            parser_name,
            newsletter_slug=email.newsletter_slug,
            taxonomy=self.taxonomy,
        )
        plaintext = email.plaintext_body or ""
        if not plaintext.strip():
            logger.warning("Empty plaintext body for %s", email.gmail_message_id)
            self.store.update_status(email.gmail_message_id, "skipped")
            return []

        parsed = parser.parse(plaintext)

        records: list[ExtractionRecord] = []
        for idx, section in enumerate(parsed.sections):
            if section.skip_extraction:
                continue
            if not section.body.strip():
                continue
            record = self._extract_one_section(email, idx, section)
            self._save_extraction(record)
            records.append(record)

        any_ok = any(r.extraction_status == "ok" for r in records)
        self.store.update_status(
            email.gmail_message_id,
            "parsed" if (records and any_ok) else "failed",
        )
        return records

    def _extract_one_section(self, email: RawEmail, idx: int, section) -> ExtractionRecord:
        prompt = self.prompts.for_section_type(section.section_type)
        user_msg = prompt.user_template.format(
            section_body=section.body,
            section_header=section.header,
            section_type=section.section_type,
            newsletter_slug=email.newsletter_slug,
            received_date=email.received_at.strftime("%Y-%m-%d"),
        )

        try:
            resp: LLMResponse = self.llm.complete(
                system=prompt.system,
                user=user_msg,
                json_schema=prompt.json_schema,
            )
        except Exception as e:
            logger.error("LLM error on %s section %d: %s", email.gmail_message_id, idx, e)
            return ExtractionRecord(
                gmail_message_id=email.gmail_message_id,
                section_index=idx,
                section_header=section.header,
                section_type=section.section_type,
                model_id=self.llm.model_id,
                prompt_tokens=0,
                completion_tokens=0,
                raw_response=str(e),
                parsed_json=None,
                extraction_status="api_failed",
            )

        status = "ok" if resp.parsed is not None else "parse_failed"
        return ExtractionRecord(
            gmail_message_id=email.gmail_message_id,
            section_index=idx,
            section_header=section.header,
            section_type=section.section_type,
            model_id=resp.model_id,
            prompt_tokens=resp.prompt_tokens,
            completion_tokens=resp.completion_tokens,
            raw_response=resp.content,
            parsed_json=json.dumps(resp.parsed) if resp.parsed is not None else None,
            extraction_status=status,
        )

    def _save_extraction(self, record: ExtractionRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO extractions (
                    gmail_message_id, section_index, section_header,
                    section_type, model_id, prompt_tokens, completion_tokens,
                    raw_response, parsed_json, extraction_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.gmail_message_id,
                    record.section_index,
                    record.section_header,
                    record.section_type,
                    record.model_id,
                    record.prompt_tokens,
                    record.completion_tokens,
                    record.raw_response,
                    record.parsed_json,
                    record.extraction_status,
                ),
            )

    def process_pending(self, limit: Optional[int] = None) -> dict:
        """Process all 'pending' emails in the store. Idempotent at the
        message level via raw_emails.processing_status.
        """
        n_emails = 0
        n_sections = 0
        n_failed = 0
        for email in self.store.iter_pending(limit=limit):
            try:
                records = self.process_email(email)
            except Exception as e:
                logger.exception("Unexpected error on %s", email.gmail_message_id)
                self.store.update_status(email.gmail_message_id, "failed")
                n_failed += 1
                continue
            n_emails += 1
            n_sections += len(records)
        summary = {
            "emails_processed": n_emails,
            "sections_extracted": n_sections,
            "failures": n_failed,
        }
        logger.info("Extraction complete: %s", summary)
        return summary
