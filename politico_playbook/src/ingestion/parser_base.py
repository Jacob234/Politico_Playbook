"""Newsletter body preprocessing — sponsor stripping, section detection.

This module sits between raw ingestion (Gmail -> SQLite) and Stage 2 entity
extraction (LLM). It does NOT extract entities; it cleans and structures the
plaintext so Stage 2 receives high-signal input.

Why preprocess at all:
  1. Sponsor blocks ('BEGIN-REGION ... END-REGION') pollute entity extraction.
  2. Named sections ('TRANSITIONS', 'MEDIA MOVES', etc.) carry strong type
     priors — e.g., names appearing in TRANSITIONS are personnel changes,
     names in HAPPY BIRTHDAY are social-graph hits.
  3. Footers (subscription links, family newsletter list) add noise.

This is a flexible parser: the default handles ~95% of Politico newsletters.
Per-newsletter overrides go in the registry's `parser:` field and dispatch
through `get_parser()` below.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Sponsor block stripping — BEGIN-REGION / END-REGION pattern observed in samples.
# ---------------------------------------------------------------------------
_SPONSOR_BLOCK_RE = re.compile(
    r"BEGIN-REGION\s+\S+.*?END-REGION",
    re.DOTALL | re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# SECTION TAXONOMY — TO BE DEFINED BY DOMAIN OWNER.
# ---------------------------------------------------------------------------
# Each entry maps a section header (as it appears in the newsletter, case-
# insensitive) to a section_type tag. Stage 2 receives sections individually
# along with their type; a section-type tag tells the LLM what kind of entities
# to expect.
#
# Empty by default — fill in based on the categories you actually want to
# extract differently. See parser_base.py docstring for examples observed
# in the May 2026 sample.
SECTION_TAXONOMY: dict[str, str] = {
    # "TRANSITIONS":               "personnel_change",
    # "MEDIA MOVES":               "personnel_change",
    # "WHITE HOUSE DEPARTURE LOUNGE": "personnel_change",
    # "SPOTTED":                   "social_graph",
    # "HAPPY BIRTHDAY":            "social_graph",
    # "DRIVING THE DAY":           "lead_story",
    # "5 THINGS YOU NEED TO KNOW": "news_brief",
    # "TALK OF THE TOWN":          "social_brief",
    # "THE FRONT PAGE":            "news_brief",
}


@dataclass
class Section:
    header: str           # Original header text as found in the body.
    section_type: str     # Tag from SECTION_TAXONOMY, or 'unclassified'.
    body: str             # Section content with header stripped.


@dataclass
class ParsedNewsletter:
    plaintext_clean: str               # Body with sponsor blocks removed.
    sections: list[Section] = field(default_factory=list)
    unmatched_body: str = ""           # Text that did not fall under any detected section.


class DefaultParser:
    """Generic Politico newsletter preprocessor.

    Subclass and override `_split_into_sections` for newsletters with
    non-standard structure (e.g., the politicopro.com multi-vertical sender).
    """

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

    @staticmethod
    def _split_into_sections(text: str) -> tuple[list[Section], str]:
        """Split text into (sections, unmatched_body) using SECTION_TAXONOMY.

        Section headers in Politico newsletters appear on their own line,
        in ALL CAPS. We walk lines and start a new section when we hit a
        line that matches a known header.

        If SECTION_TAXONOMY is empty, returns ([], full_text) — the whole body
        becomes 'unmatched', which Stage 2 receives as a single blob.
        """
        if not SECTION_TAXONOMY:
            return [], text

        # Normalize for matching but preserve original header casing.
        lookup = {key.upper(): tag for key, tag in SECTION_TAXONOMY.items()}

        sections: list[Section] = []
        current_header: Optional[str] = None
        current_type: str = "unclassified"
        current_buf: list[str] = []
        prelude: list[str] = []

        def flush():
            nonlocal current_header, current_type, current_buf
            if current_header is not None:
                sections.append(
                    Section(
                        header=current_header,
                        section_type=current_type,
                        body="\n".join(current_buf).strip(),
                    )
                )
            current_header = None
            current_type = "unclassified"
            current_buf = []

        for line in text.splitlines():
            stripped = line.strip()
            tag = lookup.get(stripped.upper())
            if tag is not None:
                flush()
                current_header = stripped
                current_type = tag
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


def get_parser(parser_name: str) -> DefaultParser:
    cls = _PARSER_REGISTRY.get(parser_name, DefaultParser)
    return cls()
