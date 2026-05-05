# Multi-Newsletter Ingestion Redesign

**Date**: 2026-05-05
**Status**: Approved by user, in implementation
**Predecessor tag**: `v0.1-poc-single-source`

## Context

The original POC was scoped to a single newsletter (Politico Playbook), 4-day window, 10-email cap. Ingestion was IMAP with hardcoded date logic. The user now subscribes to 25+ Politico newsletters across the politico.com landscape (~8K–15K newsletters across ~15 months of history) and wants to load them all into the existing 4-stage processing pipeline.

The processing pipeline (Stages 2–4) is source-agnostic and stays. The ingestion layer (Stage 1) is being rebuilt.

## Design Decisions

### 1. Gmail API + OAuth (replacing IMAP)

- IMAP App Passwords are on Google's slow-deprecation track.
- Gmail API: batch fetch (~10x faster), proper threading, label filtering, page tokens, official long-term support.
- Library: `google-api-python-client` + `google-auth-oauthlib`.
- Scopes: `https://www.googleapis.com/auth/gmail.readonly` only. No write access.
- Token persistence: `~/.config/politico-pipeline/token.json`, refreshed on expiry.

### 2. SQLite raw email store (replacing `data/raw/*.html` files)

- Single file, `data/raw_emails.db`.
- Primary key `gmail_message_id` makes ingestion idempotent.
- Re-running ingestion is a no-op for already-stored messages.
- Per-newsletter incremental queries become trivial: `MAX(received_at) WHERE newsletter_slug = ?`.
- Schema:
  ```sql
  CREATE TABLE raw_emails (
      gmail_message_id TEXT PRIMARY KEY,
      gmail_thread_id  TEXT NOT NULL,
      newsletter_slug  TEXT NOT NULL,
      sender_address   TEXT NOT NULL,
      subject          TEXT,
      received_at      TIMESTAMP NOT NULL,
      plaintext_body   TEXT,
      html_body        TEXT,
      ingested_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      processing_status TEXT DEFAULT 'pending'  -- pending, parsed, failed, skipped
  );
  CREATE INDEX idx_newsletter_received ON raw_emails(newsletter_slug, received_at DESC);
  CREATE INDEX idx_status ON raw_emails(processing_status);
  ```
- HTML retained for archival; plaintext is what downstream parsers use (Gmail API extracts it for free).

### 3. Newsletter registry (sender-slug-keyed)

- Sender pattern is exceptionally clean: `<slug>@email.politico.com`. Slug uniquely identifies the newsletter.
- Registry lives in `politico_playbook/config/newsletters.yaml`:
  ```yaml
  newsletters:
    politicoplaybook:
      display_name: "POLITICO Playbook"
      parser: default
      priority: 1
      active: true
    westwingplaybook:
      display_name: "West Wing Playbook"
      parser: default
      priority: 1
      active: true
    # ... etc
  ```
- Adding/disabling a newsletter is a config edit, no code change.
- Special case: `newsletter@email.politicopro.com` covers multiple Pro verticals — disambiguated by subject-line patterns (handled in a separate adapter).

### 4. Parser strategy

- Politico newsletters share enough structure that **one shared parser handles ~95%** of the corpus.
- Common structure observed:
  - Lead `Presented by` sponsor line
  - `By <author(s)>` byline
  - Section headers in caps (`DRIVING THE DAY`, `THE FRONT PAGE`, `5 THINGS YOU NEED TO KNOW`)
  - Sponsor blocks delimited by `BEGIN-REGION ... END-REGION` markers — strip these
  - Named structured sections that are entity-extraction goldmines: `TRANSITIONS`, `MEDIA MOVES`, `WHITE HOUSE DEPARTURE LOUNGE`, `SPOTTED`, `HAPPY BIRTHDAY`
- Section-aware extraction: feed named sections to Stage 2 separately with section-type metadata. Significantly improves entity-extraction quality vs whole-body blob.
- Per-newsletter overrides (Politico Pro multi-vertical, Brussels/London Playbook with different conventions) handled via `parser:` field in registry.

### 5. Model layer: OpenRouter (replacing direct Anthropic SDK)

- Library: OpenAI Python SDK pointed at OpenRouter's OpenAI-compatible base URL (`https://openrouter.ai/api/v1`).
- Model selection via `MODEL_ID` env var. Single string change to swap providers.
- Prompt caching: pass-through via `extra_body={"cache_control": ...}` when routing to Anthropic models. Helper isolates this.
- Structured output: `response_format={"type": "json_schema", "json_schema": {...}}` — OpenRouter normalizes across providers.
- **Tradeoff accepted**: Anthropic Message Batches API (50% off) is not proxied by OpenRouter. We get caching but not batching. Net cost reduction ~5x rather than ~10x.
- Default model: `tencent/hy3-preview:free` for plumbing/dev (rate-limited free tier — exact slug to verify against OpenRouter catalog at implementation time). For production runs, expected swap to `anthropic/claude-haiku-4.5` or similar paid model.

### 6. Ingestion modes

- `--backfill`: pulls all history matching Gmail query. Idempotent — safe to re-run.
- `--incremental`: pulls messages with `internalDate > MAX(received_at) FROM raw_emails`. Default mode for ongoing.
- `--newsletter <slug>`: scope to a single newsletter. Useful for debugging.
- `--limit N`: cap for testing.

### 7. Backfill strategy

- Initial backfill via Gmail API (acceptable for ~15K messages — Gmail allows ~250 quota units/sec, message.get is ~5 units, so ~50/sec → ~5 minutes total).
- Google Takeout mbox path: not implementing initially. Bolt-on if Gmail API rate limits become a problem during backfill.

## Out of Scope (this redesign)

- Stages 2–4 internals (only the model-call layer changes via OpenRouter swap).
- Visualization, web UI, advanced analytics.
- Real-time / streaming ingestion (cron-driven incremental is sufficient).
- Multi-account or non-Gmail sources.

## Phasing

| Phase | Deliverable | Ship test |
|-------|-------------|-----------|
| 1 | Gmail API client + OAuth, SQLite schema, registry (4 newsletters) | Backfill 4 newsletters Mar 2026 → present, query DB |
| 2 | Section-aware parser, all 25+ newsletters in registry, full backfill | Full corpus in DB |
| 3 | Stage 2 swap to OpenRouter, structured extraction with new parser | Process 100 newsletters end-to-end |
| 4 | Documentation, CLAUDE.md update, retire `email_client.py` (keep tagged in v0.1-poc-single-source) | Old code path documented as historical |

## File Layout

```
politico_playbook/
├── config/
│   └── newsletters.yaml          # NEW: registry
├── src/
│   ├── ingestion/                # NEW: replaces extraction/
│   │   ├── __init__.py
│   │   ├── gmail_client.py       # OAuth + API wrapper
│   │   ├── newsletter_registry.py
│   │   ├── raw_store.py          # SQLite layer
│   │   ├── parser_base.py        # shared parser
│   │   └── runner.py             # CLI entry: backfill/incremental
│   ├── extraction/               # KEPT for now, marked deprecated in __init__.py
│   ├── processing/
│   │   └── claude_nlp_processor.py  # refactor to OpenRouter
│   └── ...
├── data/
│   ├── raw_emails.db             # NEW: SQLite store
│   └── raw/                      # OLD: archived 20 HTMLs, gitignored going forward
└── ...
```

## Key Risks

1. **OAuth token UX** for the single-developer use case. Mitigation: token persistence + `--auth` subcommand for re-auth. One-time browser flow on first run.
2. **Gmail API quota during backfill**. Mitigation: respect 429s with exponential backoff, batch metadata fetches.
3. **Free model rate limits** on `tencent/hy3-preview:free`. Mitigation: design Stage 2 around per-newsletter rate budget; document the upgrade path to paid models.
4. **Politico newsletter format drift over 15 months of backfill**. Mitigation: parser is best-effort with graceful fallback to "raw plaintext to Stage 2" if section detection fails.
