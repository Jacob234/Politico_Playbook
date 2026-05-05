"""Ingestion runner — orchestrates Gmail fetch + registry filtering + SQLite store.

Modes:
  backfill    Pull all matching messages from Gmail (idempotent).
  incremental Pull only messages newer than the last stored message.

Examples:
  python -m politico_playbook.src.ingestion.runner backfill
  python -m politico_playbook.src.ingestion.runner incremental
  python -m politico_playbook.src.ingestion.runner backfill --newsletter politicoplaybook --limit 50
  python -m politico_playbook.src.ingestion.runner inventory  # report what's in the DB
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from politico_playbook.src.ingestion.gmail_client import GmailClient, GmailMessage
from politico_playbook.src.ingestion.newsletter_registry import NewsletterRegistry
from politico_playbook.src.ingestion.raw_store import RawEmail, RawEmailStore


logger = logging.getLogger("ingestion.runner")


def _project_root() -> Path:
    # politico_playbook/src/ingestion/runner.py -> project root is 3 parents up
    return Path(__file__).resolve().parents[3]


def _setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _build_query(
    registry: NewsletterRegistry,
    since: Optional[datetime],
    newsletter_slug: Optional[str],
) -> str:
    """Compose the Gmail search query.

    - Always restricts to allowed domains (cheap server-side filter).
    - If 'since' is provided, adds `after:YYYY/MM/DD`.
    - If a single newsletter slug is provided, uses its specific sender.
    """
    if newsletter_slug:
        # Single sender. Note: this still needs domain context — assume politico.com
        # as default; politicopro is a special case handled by registry.
        nl = registry.get(newsletter_slug)
        if nl is None:
            raise ValueError(f"Unknown newsletter slug: {newsletter_slug}")
        if newsletter_slug == "newsletter_politicopro":
            base = "from:newsletter@email.politicopro.com"
        else:
            base = f"from:{newsletter_slug}@email.politico.com"
    else:
        base = registry.gmail_query_for_active()

    if since:
        # Gmail uses YYYY/MM/DD; treat as local date in UTC.
        date_str = since.strftime("%Y/%m/%d")
        return f"({base}) after:{date_str}"
    return base


def _to_raw_email(msg: GmailMessage, slug: str) -> RawEmail:
    return RawEmail(
        gmail_message_id=msg.message_id,
        gmail_thread_id=msg.thread_id,
        newsletter_slug=slug,
        sender_address=msg.sender_address,
        subject=msg.subject,
        received_at=msg.received_at,
        plaintext_body=msg.plaintext_body,
        html_body=msg.html_body,
    )


def run_ingestion(
    mode: str,
    *,
    registry: NewsletterRegistry,
    store: RawEmailStore,
    gmail: GmailClient,
    newsletter_slug: Optional[str] = None,
    limit: Optional[int] = None,
) -> dict:
    since: Optional[datetime] = None
    if mode == "incremental":
        since = store.latest_received_at(newsletter_slug)
        if since is None:
            logger.info("No prior data; falling back to full backfill.")
        else:
            logger.info("Incremental mode: pulling messages after %s", since.isoformat())

    query = _build_query(registry, since, newsletter_slug)
    logger.info("Gmail query: %s", query)

    inserted = 0
    duplicates = 0
    out_of_scope = 0
    inactive = 0
    fetched = 0

    for message_id in gmail.list_message_ids(query):
        if limit is not None and fetched >= limit:
            logger.info("Hit --limit %d, stopping.", limit)
            break

        # Cheap idempotency check before the expensive fetch.
        if store.has_message(message_id):
            duplicates += 1
            continue

        msg = gmail.fetch_message(message_id)
        fetched += 1

        slug = registry.slug_from_sender(msg.sender_address)
        if slug is None:
            out_of_scope += 1
            logger.debug("Out-of-scope sender: %s", msg.sender_address)
            continue

        if not registry.is_active(slug):
            inactive += 1
            logger.debug("Inactive newsletter %s, skipping %s", slug, message_id)
            continue

        if store.upsert(_to_raw_email(msg, slug)):
            inserted += 1
            if inserted % 50 == 0:
                logger.info("Inserted %d so far (newsletter=%s)", inserted, slug)

    summary = {
        "mode": mode,
        "query": query,
        "fetched": fetched,
        "inserted": inserted,
        "duplicates": duplicates,
        "out_of_scope": out_of_scope,
        "inactive": inactive,
    }
    logger.info("Ingestion complete: %s", summary)
    return summary


def report_inventory(store: RawEmailStore, registry: NewsletterRegistry) -> None:
    counts = store.counts_by_newsletter()
    total = store.total_count()
    print(f"\nTotal raw emails stored: {total}\n")
    print(f"{'Newsletter':<35} {'Count':>8}  Display Name")
    print("-" * 80)
    for slug, n in counts.items():
        nl = registry.get(slug)
        name = nl.display_name if nl else "(unregistered)"
        print(f"{slug:<35} {n:>8}  {name}")


def main(argv: Optional[list[str]] = None) -> int:
    load_dotenv(dotenv_path=_project_root() / ".env")

    parser = argparse.ArgumentParser(description="Politico newsletter ingestion runner")
    parser.add_argument("mode", choices=["backfill", "incremental", "inventory"])
    parser.add_argument("--newsletter", help="Restrict to a single newsletter slug")
    parser.add_argument("--limit", type=int, help="Cap fetched messages (testing)")
    parser.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "INFO"))
    args = parser.parse_args(argv)

    _setup_logging(args.log_level)

    project_root = _project_root()
    registry_path = project_root / "politico_playbook" / "config" / "newsletters.yaml"
    db_path = project_root / os.getenv("RAW_EMAILS_DB", "data/raw_emails.db")

    registry = NewsletterRegistry.load(registry_path)
    store = RawEmailStore(db_path)

    if args.mode == "inventory":
        report_inventory(store, registry)
        return 0

    gmail = GmailClient(
        client_secrets_path=os.getenv(
            "GOOGLE_OAUTH_CLIENT_SECRETS",
            "~/.config/politico-pipeline/oauth_client.json",
        ),
        token_path=os.getenv(
            "GOOGLE_OAUTH_TOKEN_PATH",
            "~/.config/politico-pipeline/token.json",
        ),
    )

    summary = run_ingestion(
        args.mode,
        registry=registry,
        store=store,
        gmail=gmail,
        newsletter_slug=args.newsletter,
        limit=args.limit,
    )
    return 0 if summary["inserted"] >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
