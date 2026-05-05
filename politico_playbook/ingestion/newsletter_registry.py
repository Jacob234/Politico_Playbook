"""Newsletter registry — sender-slug-keyed config loaded from YAML.

A newsletter is identified by the local-part of its sender address:
  politicoplaybook@email.politico.com -> slug: 'politicoplaybook'

Special case: politicopro.com domain has one shared sender for many
sub-newsletters; it gets a synthetic slug 'newsletter_politicopro' and
its parser dispatches by subject.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


# Synthetic slug used for the multi-vertical politicopro.com sender.
PRO_MULTI_VERTICAL_SLUG = "newsletter_politicopro"


@dataclass(frozen=True)
class Newsletter:
    slug: str
    display_name: str
    parser: str
    priority: int
    active: bool
    notes: str = ""


class NewsletterRegistry:
    def __init__(self, newsletters: dict[str, Newsletter], allowed_domains: list[str]):
        self._newsletters = newsletters
        self._allowed_domains = [d.lower() for d in allowed_domains]

    @classmethod
    def load(cls, config_path: str | Path) -> "NewsletterRegistry":
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        newsletters: dict[str, Newsletter] = {}
        for slug, fields in (data.get("newsletters") or {}).items():
            newsletters[slug] = Newsletter(
                slug=slug,
                display_name=fields.get("display_name", slug),
                parser=fields.get("parser", "default"),
                priority=int(fields.get("priority", 3)),
                active=bool(fields.get("active", True)),
                notes=fields.get("notes", "") or "",
            )

        allowed_domains = data.get("allowed_domains") or []
        return cls(newsletters, allowed_domains)

    def is_allowed_domain(self, domain: str) -> bool:
        return domain.lower() in self._allowed_domains

    def slug_from_sender(self, sender_address: str) -> Optional[str]:
        """Map a sender address to a registry slug, or None if out of scope.

        Examples:
            'politicoplaybook@email.politico.com' -> 'politicoplaybook'
            'newsletter@email.politicopro.com' -> 'newsletter_politicopro' (synthetic)
        """
        if "@" not in sender_address:
            return None
        local, _, domain = sender_address.partition("@")
        if not self.is_allowed_domain(domain):
            return None
        if domain.lower() == "email.politicopro.com":
            return PRO_MULTI_VERTICAL_SLUG
        return local.lower()

    def get(self, slug: str) -> Optional[Newsletter]:
        return self._newsletters.get(slug)

    def is_active(self, slug: str) -> bool:
        n = self.get(slug)
        return bool(n and n.active)

    def active_slugs(self) -> list[str]:
        return [slug for slug, n in self._newsletters.items() if n.active]

    def all(self) -> list[Newsletter]:
        return list(self._newsletters.values())

    def by_priority(self) -> list[Newsletter]:
        return sorted(self._newsletters.values(), key=lambda n: (n.priority, n.slug))

    def gmail_query_for_active(self) -> str:
        """Build a Gmail search query covering all allowed domains.

        We filter by domain at the API layer; per-newsletter active filtering
        happens after fetch (cheap, since domain query already narrows the corpus).
        """
        clauses = [f"from:{domain}" for domain in self._allowed_domains]
        return " OR ".join(clauses)
