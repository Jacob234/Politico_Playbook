"""Newsletter body preprocessing — sponsor stripping, section detection.

This module sits between raw ingestion (Gmail -> SQLite) and Stage 2 entity
extraction (LLM). It does NOT extract entities; it cleans and structures the
plaintext so Stage 2 receives high-signal input.

The section taxonomy lives in YAML at config/section_taxonomy.yaml — see that
file for the lookup precedence and schema. This module just enforces it.

Why preprocess at all:
  1. Sponsor blocks ('BEGIN-REGION ... END-REGION') pollute entity extraction.
  2. Named sections carry strong type priors — e.g., names appearing in
     'TRANSITIONS' are personnel changes, names in 'HAPPY BIRTHDAY' are
     social-graph hits.
  3. Different newsletters use different labels for the same concept; the YAML
     resolves them to a shared semantic type.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


# ---------------------------------------------------------------------------
# Sponsor block stripping — BEGIN-REGION / END-REGION pattern observed
# in Politico newsletter samples.
# ---------------------------------------------------------------------------
_SPONSOR_BLOCK_RE = re.compile(
    r"BEGIN-REGION\s+\S+.*?END-REGION",
    re.DOTALL | re.IGNORECASE,
)


@dataclass
class Section:
    header: str             # Original header text as found in the body.
    section_type: str       # Type from taxonomy, or 'unclassified'.
    body: str               # Section content with header stripped.
    skip_extraction: bool = False  # True for links_only / ignore / skip_headers.


@dataclass
class ParsedNewsletter:
    plaintext_clean: str               # Body with sponsor blocks removed.
    sections: list[Section] = field(default_factory=list)
    unmatched_body: str = ""           # Text before any detected section.


def _normalize(header: str) -> str:
    """Match key for headers: strip whitespace, drop trailing colons, lowercase."""
    return header.strip().rstrip(":").lower()


class SectionTaxonomy:
    """Loaded section_taxonomy.yaml with fast per-newsletter lookup."""

    def __init__(self, raw: dict):
        self._types: dict[str, dict] = raw.get("types") or {}

        # Pre-normalize keys for case/colon-insensitive matching.
        self._shared = {
            _normalize(k): v for k, v in (raw.get("shared") or {}).items()
        }
        self._by_newsletter: dict[str, dict[str, str]] = {}
        for slug, mapping in (raw.get("by_newsletter") or {}).items():
            self._by_newsletter[slug] = {
                _normalize(k): v for k, v in (mapping or {}).items()
            }
        self._skip_headers = {
            _normalize(h) for h in (raw.get("skip_headers") or [])
        }

    @classmethod
    def load(cls, path: str | Path) -> "SectionTaxonomy":
        with open(path, "r", encoding="utf-8") as f:
            return cls(yaml.safe_load(f) or {})

    def lookup(self, header: str, newsletter_slug: Optional[str] = None) -> tuple[str, bool]:
        """Resolve a header to (section_type, skip_extraction) given the newsletter context.

        Returns ('unclassified', False) if the header is not in the taxonomy.
        """
        norm = _normalize(header)

        # 1. Per-newsletter override wins.
        if newsletter_slug and newsletter_slug in self._by_newsletter:
            t = self._by_newsletter[newsletter_slug].get(norm)
            if t:
                return t, self._is_skip_type(t)

        # 2. Cross-newsletter shared mapping.
        t = self._shared.get(norm)
        if t:
            return t, self._is_skip_type(t)

        # 3. Skip-but-recognize.
        if norm in self._skip_headers:
            return "ignore", True

        return "unclassified", False

    def is_known_header(self, header: str, newsletter_slug: Optional[str] = None) -> bool:
        """Whether `header` is in the taxonomy at all (for any of the three layers)."""
        norm = _normalize(header)
        if newsletter_slug and norm in self._by_newsletter.get(newsletter_slug, {}):
            return True
        return norm in self._shared or norm in self._skip_headers

    def _is_skip_type(self, section_type: str) -> bool:
        meta = self._types.get(section_type) or {}
        return bool(meta.get("skip_extraction"))


def _default_taxonomy_path() -> Path:
    # politico_playbook/src/ingestion/parser_base.py
    # ->                    ../../config/section_taxonomy.yaml
    return Path(__file__).resolve().parents[2] / "config" / "section_taxonomy.yaml"


class DefaultParser:
    """Generic Politico newsletter preprocessor.

    Subclass and override `_split_into_sections` for newsletters with
    non-standard structure (e.g., the politicopro.com multi-vertical sender).
    """

    def __init__(
        self,
        taxonomy: Optional[SectionTaxonomy] = None,
        newsletter_slug: Optional[str] = None,
    ):
        self.taxonomy = taxonomy or SectionTaxonomy.load(_default_taxonomy_path())
        self.newsletter_slug = newsletter_slug

    def parse(self, plaintext: str) -> ParsedNewsletter:
        clean = self._strip_sponsor_blocks(plaintext)
        sections, unmatched = self._split_into_sections(clean)
        return ParsedNewsletter(
            plaintext_clean=clean,
            sections=sections,
            unmatched_body=unmatched,
        )

    @staticmethod
    def _strip_sponsor_blocks(text: str) -> str:
        return _SPONSOR_BLOCK_RE.sub("", text)

    def _split_into_sections(self, text: str) -> tuple[list[Section], str]:
        """Walk lines; start a new section when a line matches a known header.

        A "header" is a stripped non-empty line that exactly matches an entry
        in the taxonomy (case-insensitive, trailing-colon-tolerant).
        """
        sections: list[Section] = []
        current_header: Optional[str] = None
        current_type: str = "unclassified"
        current_skip: bool = False
        current_buf: list[str] = []
        prelude: list[str] = []

        def flush():
            nonlocal current_header, current_type, current_skip, current_buf
            if current_header is not None:
                sections.append(
                    Section(
                        header=current_header,
                        section_type=current_type,
                        body="\n".join(current_buf).strip(),
                        skip_extraction=current_skip,
                    )
                )
            current_header = None
            current_type = "unclassified"
            current_skip = False
            current_buf = []

        for line in text.splitlines():
            stripped = line.strip()
            if stripped and self.taxonomy.is_known_header(stripped, self.newsletter_slug):
                flush()
                current_header = stripped
                current_type, current_skip = self.taxonomy.lookup(
                    stripped, self.newsletter_slug
                )
            elif current_header is None:
                prelude.append(line)
            else:
                current_buf.append(line)
        flush()

        return sections, "\n".join(prelude).strip()


class ProMultiVerticalParser(DefaultParser):
    """Stub for politicopro.com sender (one address, many sub-newsletters).

    The sub-newsletter is identified from the subject line. Default behavior
    falls through to DefaultParser for now.
    """

    # TODO: implement subject-pattern -> sub-newsletter routing once we have
    # a sample of Pro newsletter subjects in the DB.


_PARSER_REGISTRY: dict[str, type[DefaultParser]] = {
    "default": DefaultParser,
    "pro_multi_vertical": ProMultiVerticalParser,
}


def get_parser(
    parser_name: str,
    *,
    newsletter_slug: Optional[str] = None,
    taxonomy: Optional[SectionTaxonomy] = None,
) -> DefaultParser:
    cls = _PARSER_REGISTRY.get(parser_name, DefaultParser)
    return cls(taxonomy=taxonomy, newsletter_slug=newsletter_slug)
