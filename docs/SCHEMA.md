# Database Schema Reference

The pipeline stores everything in a single SQLite file: `data/raw_emails.db`
(path overridable via `RAW_EMAILS_DB` env var). Two tables — `raw_emails` for
the Stage 1 ingestion store, and `extractions` for the Stage 2 LLM output —
plus their indices.

This document is the source of truth for column semantics, value enumerations,
and constraint behavior. Schema lives in code at
[`politico_playbook/ingestion/raw_store.py`](../politico_playbook/ingestion/raw_store.py)
and
[`politico_playbook/processing/section_extractor.py`](../politico_playbook/processing/section_extractor.py);
re-derive at any time with:

```bash
sqlite3 data/raw_emails.db ".schema"
```

## `raw_emails` — Stage 1 ingestion store

One row per Gmail message that matched the registry's allowed-domain filter.
Idempotent on `gmail_message_id`: re-running `backfill` is a no-op for rows
already present.

| Column              | Type      | Null | Notes |
|---------------------|-----------|------|-------|
| `gmail_message_id`  | TEXT      | PK   | Gmail's stable message ID. Re-ingestion is keyed on this — same ID means we already have it. |
| `gmail_thread_id`   | TEXT      | NO   | Same value as the message ID for newsletters (each message is its own thread); preserved for join compatibility. |
| `newsletter_slug`   | TEXT      | NO   | Registry slug (e.g., `politicoplaybook`). Resolved from the sender's local-part, except `politicopro.com` maps to `newsletter_politicopro`. |
| `sender_address`    | TEXT      | NO   | Full `from` address as Gmail returned it. |
| `subject`           | TEXT      | YES  | Subject line. |
| `received_at`       | TIMESTAMP | NO   | When Gmail received the message (UTC). |
| `plaintext_body`    | TEXT      | YES  | The text/plain MIME part. Stage 2 reads this. |
| `html_body`         | TEXT      | YES  | The text/html MIME part. Kept for future re-parsing. |
| `ingested_at`       | TIMESTAMP | NO   | `DEFAULT CURRENT_TIMESTAMP`. When the row landed in our DB. |
| `processing_status` | TEXT      | NO   | `DEFAULT 'pending'`. Stage 2 lifecycle state — see below. |

### `processing_status` values

Defined in
[`raw_store.py:40`](../politico_playbook/ingestion/raw_store.py) as the
`VALID_STATUSES` frozenset.

| Value      | Set by                                         | Meaning |
|------------|------------------------------------------------|---------|
| `pending`  | Default at insert                              | Stage 2 has not run on this row yet. |
| `parsed`   | `SectionExtractor.process_email`               | Stage 2 ran and at least one section produced an `ok` extraction. |
| `failed`   | `SectionExtractor.process_email` / `process_pending` | Stage 2 ran but every section failed (`api_failed` or `parse_failed`), OR an unexpected exception bubbled up. |
| `skipped`  | `SectionExtractor.process_email`               | Plaintext body was empty/whitespace-only — nothing to extract. |

Indexed by `idx_status` so `iter_pending()` is O(matching rows).

### Sample row

Pulled from the live DB on 2026-05-05 (body bytes summarized rather than
inlined):

```json
{
  "gmail_message_id":   "19df9390559f0601",
  "gmail_thread_id":    "19df9390559f0601",
  "newsletter_slug":    "politicoplaybook",
  "sender_address":     "politicoplaybook@email.politico.com",
  "subject":            "Whose strait is it anyway?",
  "received_at":        "2026-05-05 17:39:15+00:00",
  "ingested_at":        "2026-05-06 01:12:50",
  "processing_status":  "parsed",
  "plaintext_len":      15694,
  "html_len":           63295
}
```

## `extractions` — Stage 2 LLM output

One row per `(email × section × model)` triple. Section indices are 0-based
within an email; the same section can appear multiple times in the table if
re-run with different `MODEL_ID`s (useful for A/B comparison).

| Column              | Type      | Null | Notes |
|---------------------|-----------|------|-------|
| `id`                | INTEGER   | PK   | `AUTOINCREMENT`. Surrogate key for FK from future tables. |
| `gmail_message_id`  | TEXT      | NO   | FK → `raw_emails(gmail_message_id)`. |
| `section_index`     | INTEGER   | NO   | 0-based position of the section within the parsed newsletter. |
| `section_header`    | TEXT      | YES  | Original header text as it appeared (e.g., `"TALK OF THE TOWN"`). |
| `section_type`      | TEXT      | NO   | Resolved semantic type — see below. |
| `model_id`          | TEXT      | NO   | OpenRouter model ID at time of extraction (e.g., `deepseek/deepseek-v4-flash`). |
| `prompt_tokens`     | INTEGER   | YES  | Input tokens charged. 0 on `api_failed`. |
| `completion_tokens` | INTEGER   | YES  | Output tokens charged. 0 on `api_failed`. |
| `raw_response`      | TEXT      | YES  | Full LLM response text. On `api_failed`, contains the exception message. |
| `parsed_json`       | TEXT      | YES  | `json.dumps()` of the structured output. NULL when `extraction_status != 'ok'`. |
| `extraction_status` | TEXT      | NO   | `ok` \| `parse_failed` \| `api_failed`. |
| `extracted_at`      | TIMESTAMP | NO   | `DEFAULT CURRENT_TIMESTAMP`. |

### Constraints

- `UNIQUE (gmail_message_id, section_index, model_id)`. The Stage 2 driver
  uses `INSERT OR REPLACE` on this key, so a re-run of `extract` against the
  same email+model is idempotent: it overwrites the prior row in place.
  Switching `MODEL_ID` produces a *new* row instead of overwriting — A/B
  comparison is just a query.
- `FOREIGN KEY (gmail_message_id) REFERENCES raw_emails(gmail_message_id)`.
  SQLite does not enforce FKs by default, but the constraint documents intent
  and is honored if `PRAGMA foreign_keys=ON` is set.

### `extraction_status` values

| Value          | Set by                                          | Meaning |
|----------------|--------------------------------------------------|---------|
| `ok`           | `SectionExtractor._extract_one_section`          | LLM returned content AND it parsed as JSON matching the schema. |
| `parse_failed` | `SectionExtractor._extract_one_section`          | API call succeeded, but the response wasn't valid JSON. `raw_response` holds the offending output for debugging. |
| `api_failed`   | `SectionExtractor._extract_one_section` (except path) | The OpenRouter request raised — rate limit, network, model-removed, etc. `raw_response` holds the exception text. Tokens recorded as 0. |

### `section_type` values

Defined in
[`config/section_taxonomy.yaml`](../politico_playbook/config/section_taxonomy.yaml)
under `types:`. Plus the implicit `unclassified` fallback for unknown headers.

| Type                | Skip extraction? | Priority | Description |
|---------------------|:----------------:|----------|-------------|
| `personnel_change`  | no               | high     | Job moves — TRANSITIONS, MEDIA MOVES, Names in the News |
| `social_graph`      | no               | high     | Guest lists, birthday rosters — SPOTTED, HAPPY BIRTHDAY, TALK OF THE TOWN |
| `lead_story`        | no               | medium   | Top story narrative — DRIVING THE DAY |
| `news_brief`        | no               | medium   | Numbered news lists — 5 THINGS, THE FRONT PAGE |
| `state_news`        | no               | medium   | State-level news with locality context |
| `campaign_news`     | no               | high     | Endorsements, polling, fundraising |
| `financial`         | no               | medium   | Lobbying, donor money, settlements |
| `links_only`        | yes              | low      | Link roundups — WHAT WE'RE READING |
| `ignore`            | yes              | none     | Trivia, footers, sponsor messages |
| `unclassified`      | no               | —        | Header not in taxonomy; gets the generic prompt |

Sections marked `skip_extraction: true` (`links_only`, `ignore`, plus anything
in the `skip_headers` list) are recognized as section breaks but never sent
to the LLM. They will not appear in the `extractions` table.

## Indices

| Index                     | Table         | Columns                                  | Helps |
|---------------------------|---------------|------------------------------------------|-------|
| `sqlite_autoindex_…_1`    | `raw_emails`  | `gmail_message_id` (auto from PK)        | Idempotent inserts; `has_message()` checks. |
| `idx_newsletter_received` | `raw_emails`  | `(newsletter_slug, received_at DESC)`    | `latest_received_at()` for incremental mode; per-newsletter time-window queries. |
| `idx_status`              | `raw_emails`  | `processing_status`                      | `iter_pending()` scan. |
| `sqlite_autoindex_…_1`    | `extractions` | `(gmail_message_id, section_index, model_id)` (auto from UNIQUE) | `INSERT OR REPLACE` idempotency lookup. |
| `idx_extractions_msg`     | `extractions` | `gmail_message_id`                       | Joining extractions back to their source email. |
| `idx_extractions_type`    | `extractions` | `section_type`                           | Slicing by section type for analytics. |

## Sample queries

All of these run cleanly against `data/raw_emails.db` as of 2026-05-05.

### Inventory

```sql
-- Per-newsletter row count (matches the `inventory` CLI mode)
SELECT newsletter_slug, COUNT(*) AS n
FROM raw_emails
GROUP BY newsletter_slug
ORDER BY n DESC;

-- Earliest and latest message in the store
SELECT MIN(received_at), MAX(received_at) FROM raw_emails;

-- Stage 2 progress
SELECT processing_status, COUNT(*) FROM raw_emails GROUP BY processing_status;
```

### Extraction quality

```sql
-- Section-type × outcome matrix
SELECT section_type, extraction_status, COUNT(*)
FROM extractions
GROUP BY section_type, extraction_status
ORDER BY section_type, extraction_status;

-- Parse-failure rate per section type (fraction failing JSON parse)
SELECT
    section_type,
    SUM(CASE WHEN extraction_status='parse_failed' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS parse_fail_rate
FROM extractions
GROUP BY section_type;
```

### Joining raw → extractions

```sql
-- All extracted social_graph entries with their newsletter and date
SELECT
    r.newsletter_slug,
    r.received_at,
    e.section_header,
    json_extract(e.parsed_json, '$.context.event_name') AS event,
    json_array_length(json_extract(e.parsed_json, '$.people')) AS people_count
FROM extractions e
JOIN raw_emails r USING (gmail_message_id)
WHERE e.section_type = 'social_graph'
  AND e.extraction_status = 'ok'
ORDER BY r.received_at DESC;
```

### A/B model comparison

```sql
-- For sections extracted by multiple models, compare outcomes
SELECT
    gmail_message_id, section_index, section_header,
    model_id, extraction_status, completion_tokens
FROM extractions
WHERE (gmail_message_id, section_index) IN (
    SELECT gmail_message_id, section_index
    FROM extractions
    GROUP BY gmail_message_id, section_index
    HAVING COUNT(DISTINCT model_id) > 1
)
ORDER BY gmail_message_id, section_index, model_id;
```

## What lives outside this DB

- **OAuth client/token**: `~/.config/politico-pipeline/{oauth_client.json,token.json}`
  (paths configurable; see [`oauth-setup.md`](./oauth-setup.md)).
- **OpenRouter API key, MODEL_ID**: `.env` at the repo root.
- **Stage 3/4 file-based output**: legacy `data/structured/` from v0.1; not
  produced by the v0.2 pipeline. See [ROADMAP.md](./ROADMAP.md) for the
  port-to-SQLite plan.
