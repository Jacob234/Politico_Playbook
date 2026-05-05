"""Gmail API client with OAuth (replaces the IMAP-based email_client.py).

Read-only access. Token persistence lives at GOOGLE_OAUTH_TOKEN_PATH so the
browser flow runs once.

Two-phase fetch pattern:
  1. list_message_ids(query): cheap, returns IDs only, paginated.
  2. fetch_message(id): full message including plaintext body.

This separation lets the runner check the SQLite store for already-ingested
IDs *before* paying the cost of fetching full messages.
"""

from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from typing import Iterator, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


@dataclass(frozen=True)
class GmailMessage:
    """Subset of a Gmail message we care about."""

    message_id: str
    thread_id: str
    sender_address: str           # lowercased local@domain
    subject: Optional[str]
    received_at: datetime          # tz-aware UTC
    plaintext_body: Optional[str]
    html_body: Optional[str]


class GmailClient:
    def __init__(
        self,
        client_secrets_path: str | Path,
        token_path: str | Path,
    ):
        self.client_secrets_path = Path(os.path.expanduser(str(client_secrets_path)))
        self.token_path = Path(os.path.expanduser(str(token_path)))
        self._service = None

    def _credentials(self) -> Credentials:
        creds: Optional[Credentials] = None
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.client_secrets_path.exists():
                    raise FileNotFoundError(
                        f"OAuth client secrets not found at {self.client_secrets_path}. "
                        "Download from Google Cloud Console and set GOOGLE_OAUTH_CLIENT_SECRETS."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.client_secrets_path), SCOPES
                )
                creds = flow.run_local_server(port=0)
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            self.token_path.write_text(creds.to_json())

        return creds

    def _get_service(self):
        if self._service is None:
            self._service = build("gmail", "v1", credentials=self._credentials(), cache_discovery=False)
        return self._service

    def list_message_ids(self, query: str, page_size: int = 500) -> Iterator[str]:
        """Stream message IDs matching `query`. Paginates until exhausted."""
        service = self._get_service()
        page_token: Optional[str] = None
        while True:
            try:
                resp = service.users().messages().list(
                    userId="me",
                    q=query,
                    maxResults=page_size,
                    pageToken=page_token,
                ).execute()
            except HttpError as e:
                self._handle_http_error(e)
                continue

            for msg in resp.get("messages", []):
                yield msg["id"]

            page_token = resp.get("nextPageToken")
            if not page_token:
                return

    def fetch_message(self, message_id: str) -> GmailMessage:
        service = self._get_service()
        try:
            raw = service.users().messages().get(
                userId="me",
                id=message_id,
                format="full",
            ).execute()
        except HttpError as e:
            self._handle_http_error(e)
            return self.fetch_message(message_id)

        return self._to_gmail_message(raw)

    def _to_gmail_message(self, raw: dict) -> GmailMessage:
        headers = {h["name"].lower(): h["value"] for h in raw.get("payload", {}).get("headers", [])}

        # Sender: parseaddr handles 'Name <addr@host>' and bare addresses.
        _, sender_addr = parseaddr(headers.get("from", ""))
        sender_addr = sender_addr.lower()

        subject = headers.get("subject")

        received_at = self._extract_received_at(raw, headers)

        plaintext, html = self._extract_bodies(raw.get("payload", {}))

        return GmailMessage(
            message_id=raw["id"],
            thread_id=raw["threadId"],
            sender_address=sender_addr,
            subject=subject,
            received_at=received_at,
            plaintext_body=plaintext,
            html_body=html,
        )

    @staticmethod
    def _extract_received_at(raw: dict, headers: dict[str, str]) -> datetime:
        # Prefer Gmail's internalDate (ms since epoch) — authoritative and tz-stable.
        internal = raw.get("internalDate")
        if internal:
            return datetime.fromtimestamp(int(internal) / 1000, tz=timezone.utc)
        # Fallback: parse Date header.
        date_str = headers.get("date")
        if date_str:
            dt = parsedate_to_datetime(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        raise ValueError(f"Cannot determine received_at for message {raw.get('id')}")

    def _extract_bodies(self, payload: dict) -> tuple[Optional[str], Optional[str]]:
        """Walk the MIME tree and return (plaintext, html). Either may be None."""
        plaintext: Optional[str] = None
        html: Optional[str] = None

        for part in self._walk_parts(payload):
            mime = part.get("mimeType", "")
            data = part.get("body", {}).get("data")
            if not data:
                continue
            decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            if mime == "text/plain" and plaintext is None:
                plaintext = decoded
            elif mime == "text/html" and html is None:
                html = decoded

        return plaintext, html

    @staticmethod
    def _walk_parts(payload: dict) -> Iterator[dict]:
        yield payload
        for part in payload.get("parts", []) or []:
            yield from GmailClient._walk_parts(part)

    @staticmethod
    def _handle_http_error(error: HttpError) -> None:
        """Backoff on rate limits; raise on other errors."""
        status = error.resp.status if error.resp is not None else None
        if status in (429, 500, 502, 503):
            # Exponential backoff with jitter would be more robust;
            # this is the minimal correct version.
            time.sleep(2.0)
            return
        raise error
