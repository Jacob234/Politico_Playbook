"""SQLite-backed store for raw Gmail messages.

Idempotency comes from gmail_message_id as PRIMARY KEY: re-running ingestion
is a no-op for already-stored messages. Per-newsletter incremental queries
become trivial.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, Optional


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS raw_emails (
    gmail_message_id  TEXT PRIMARY KEY,
    gmail_thread_id   TEXT NOT NULL,
    newsletter_slug   TEXT NOT NULL,
    sender_address    TEXT NOT NULL,
    subject           TEXT,
    received_at       TIMESTAMP NOT NULL,
    plaintext_body    TEXT,
    html_body         TEXT,
    ingested_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processing_status TEXT NOT NULL DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_newsletter_received
    ON raw_emails(newsletter_slug, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_status
    ON raw_emails(processing_status);
"""


VALID_STATUSES = frozenset({"pending", "parsed", "failed", "skipped"})


@dataclass(frozen=True)
class RawEmail:
    gmail_message_id: str
    gmail_thread_id: str
    newsletter_slug: str
    sender_address: str
    subject: Optional[str]
    received_at: datetime
    plaintext_body: Optional[str]
    html_body: Optional[str]
    processing_status: str = "pending"


class RawEmailStore:
    """Thin wrapper around sqlite3 with idempotent inserts and incremental queries."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def upsert(self, email: RawEmail) -> bool:
        """Insert if new, ignore if already present. Returns True if inserted."""
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO raw_emails (
                    gmail_message_id, gmail_thread_id, newsletter_slug,
                    sender_address, subject, received_at,
                    plaintext_body, html_body, processing_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    email.gmail_message_id,
                    email.gmail_thread_id,
                    email.newsletter_slug,
                    email.sender_address,
                    email.subject,
                    email.received_at,
                    email.plaintext_body,
                    email.html_body,
                    email.processing_status,
                ),
            )
            return cur.rowcount > 0

    def upsert_many(self, emails: Iterable[RawEmail]) -> tuple[int, int]:
        """Bulk insert. Returns (inserted_count, duplicate_count)."""
        inserted = 0
        skipped = 0
        for email in emails:
            if self.upsert(email):
                inserted += 1
            else:
                skipped += 1
        return inserted, skipped

    def has_message(self, gmail_message_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM raw_emails WHERE gmail_message_id = ? LIMIT 1",
                (gmail_message_id,),
            ).fetchone()
            return row is not None

    def latest_received_at(self, newsletter_slug: Optional[str] = None) -> Optional[datetime]:
        """Get the timestamp of the most recent email, optionally scoped to a newsletter.

        Used by --incremental mode to compute the Gmail query lower bound.
        """
        with self._connect() as conn:
            if newsletter_slug:
                row = conn.execute(
                    "SELECT MAX(received_at) AS ts FROM raw_emails WHERE newsletter_slug = ?",
                    (newsletter_slug,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT MAX(received_at) AS ts FROM raw_emails",
                ).fetchone()
            ts = row["ts"] if row else None
            if isinstance(ts, str):
                return datetime.fromisoformat(ts)
            return ts

    def counts_by_newsletter(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT newsletter_slug, COUNT(*) AS n
                FROM raw_emails
                GROUP BY newsletter_slug
                ORDER BY n DESC
                """
            ).fetchall()
            return {row["newsletter_slug"]: row["n"] for row in rows}

    def total_count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM raw_emails").fetchone()
            return row["n"]

    def update_status(self, gmail_message_id: str, status: str) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status {status!r}; valid: {sorted(VALID_STATUSES)}")
        with self._connect() as conn:
            conn.execute(
                "UPDATE raw_emails SET processing_status = ? WHERE gmail_message_id = ?",
                (status, gmail_message_id),
            )

    def iter_pending(self, newsletter_slug: Optional[str] = None, limit: Optional[int] = None) -> Iterator[RawEmail]:
        """Stream pending messages for downstream Stage 2 processing."""
        sql = "SELECT * FROM raw_emails WHERE processing_status = 'pending'"
        params: list = []
        if newsletter_slug:
            sql += " AND newsletter_slug = ?"
            params.append(newsletter_slug)
        sql += " ORDER BY received_at ASC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        with self._connect() as conn:
            for row in conn.execute(sql, params):
                yield RawEmail(
                    gmail_message_id=row["gmail_message_id"],
                    gmail_thread_id=row["gmail_thread_id"],
                    newsletter_slug=row["newsletter_slug"],
                    sender_address=row["sender_address"],
                    subject=row["subject"],
                    received_at=row["received_at"] if isinstance(row["received_at"], datetime)
                                else datetime.fromisoformat(row["received_at"]),
                    plaintext_body=row["plaintext_body"],
                    html_body=row["html_body"],
                    processing_status=row["processing_status"],
                )
