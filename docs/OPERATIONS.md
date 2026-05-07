# Operations Runbook

How to run, observe, and diagnose the v0.2 pipeline. Anchored on what's
actually in `data/raw_emails.db` as of 2026-05-05 — every claim about
failure rates and counts has a SQL query you can re-run to verify against
current state.

For schema details see [SCHEMA.md](./SCHEMA.md); for what each command
mutates see [ARCHITECTURE.md](./ARCHITECTURE.md).

## Day-to-day commands

All operations go through one CLI runner:
[`politico_playbook.ingestion.runner`](../politico_playbook/ingestion/runner.py).
Invoke with `python -m politico_playbook.ingestion.runner <mode>`.

### Daily incremental fetch

```bash
# Pulls only messages newer than MAX(received_at) in the local DB.
python -m politico_playbook.ingestion.runner incremental
```

`incremental` mode adds an `after:YYYY/MM/DD` clause to the Gmail query, so
it doesn't even pay to fetch already-stored messages. Safe to run
unattended; idempotent.

#### Cron template (macOS launchd or cron)

```cron
# Every weekday at 09:30 ET. Adjust path/venv to your install.
30 9 * * 1-5 cd /Users/jacobkeller/Documents/Projects/Politico_Playbook && \
  /usr/bin/env -i HOME="$HOME" PATH="/usr/bin:/bin" \
  ./.venv/bin/python -m politico_playbook.ingestion.runner incremental \
  >> logs/incremental.log 2>&1
```

The `env -i` strip is intentional — cron's environment is minimal and
inheriting your interactive shell's vars is a footgun (`PYTHONPATH`,
in particular, frequently breaks the import). Keep `HOME` so the OAuth
token cache resolves.

### Resuming a partial backfill

```bash
# Just re-run; idempotency means no duplicate work.
python -m politico_playbook.ingestion.runner backfill
```

If the previous backfill crashed, every message it already stored is a
no-op for the second run — `RawEmailStore.upsert` uses `INSERT OR IGNORE`,
and the runner short-circuits with `has_message()` before the expensive
`fetch_message` call.

To resume scoped to one newsletter:

```bash
python -m politico_playbook.ingestion.runner backfill \
    --newsletter politicoplaybook
```

### Running Stage 2 extraction

```bash
# Process all 'pending' messages in the store.
python -m politico_playbook.ingestion.runner extract

# Cap at N messages (testing — keeps spend low).
python -m politico_playbook.ingestion.runner extract --limit 5
```

Each pending message hits OpenRouter once per non-skipped section. Watch
the log for the per-section status: `ok`, `parse_failed`, or `api_failed`.

### Inventory

```bash
python -m politico_playbook.ingestion.runner inventory
```

Prints per-newsletter counts and the total. No fetching, no LLM calls.

## Re-extracting with a different model

Stage 2 idempotency keys on `(gmail_message_id, section_index, model_id)`.
Switching `MODEL_ID` produces a *new* row instead of overwriting. So:

```bash
# Round 1: run with the cheap workhorse
echo "MODEL_ID=deepseek/deepseek-v4-flash-20260423" >> .env
python -m politico_playbook.ingestion.runner extract --limit 25

# Round 2: re-run with a stronger model — produces a parallel set of rows
sed -i '' 's|MODEL_ID=.*|MODEL_ID=anthropic/claude-haiku-4.5|' .env
# Mark the messages as pending again so extract picks them up
sqlite3 data/raw_emails.db "UPDATE raw_emails SET processing_status='pending' WHERE processing_status='parsed'"
python -m politico_playbook.ingestion.runner extract --limit 25
```

Compare with the [A/B query](./SCHEMA.md#ab-model-comparison).

> **Caveat**: re-flipping `processing_status='pending'` will cause Stage 2
> to re-process every section, including sections that succeeded with the
> first model. The extractions row for the first model stays put (different
> `model_id` → different UNIQUE key); you end up with two rows per section
> per model. That's the goal for A/B, but if you're only re-running because
> of a bug, scope the UPDATE to just the failed messages:

```sql
UPDATE raw_emails
SET processing_status='pending'
WHERE processing_status='failed';
```

## Diagnosing `parse_failed`

The current parse-failure rate against the live DB:

```sql
SELECT
    section_type,
    SUM(CASE WHEN extraction_status='parse_failed' THEN 1 ELSE 0 END) AS failed,
    COUNT(*) AS total,
    ROUND(100.0 * SUM(CASE WHEN extraction_status='parse_failed' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct
FROM extractions
GROUP BY section_type
ORDER BY pct DESC;
```

As of 2026-05-05 this returns roughly:

| section_type   | failed | total | pct  |
|----------------|--------|-------|------|
| `lead_story`   | 7      | 15    | 46.7 |
| `news_brief`   | 5      | 14    | 35.7 |
| `social_graph` | 3      | 29    | 10.3 |

Lead-story and news-brief failures dominate; social-graph is mostly fine.
The pattern is consistent with the schemas — `lead_story` has the largest
schema (entities + actions + quotes with nested optional fields); free-form
prose with strict JSON output is hard for free-tier models.

### Surface failed rows

```sql
-- Latest parse_failed extractions with truncated raw response
SELECT
    e.id,
    e.section_type,
    e.section_header,
    e.model_id,
    substr(e.raw_response, 1, 200) AS preview
FROM extractions e
WHERE e.extraction_status = 'parse_failed'
ORDER BY e.id DESC
LIMIT 20;
```

### Triage checklist

For each failure mode, what to look for in `raw_response` and what to fix:

| Symptom in `raw_response`                            | Likely cause                                         | Fix |
|------------------------------------------------------|------------------------------------------------------|-----|
| ` ```json {...} ``` ` markdown fences                | Model emitted code-fenced JSON                       | Add "Return raw JSON only — no code fences." to the system prompt. |
| Curly quotes (`"..."` instead of `"..."`)            | Model copied curly quotes from input                 | Add explicit "Use ASCII straight quotes only" instruction; or post-process. |
| Trailing commas before `}` or `]`                    | Model habitually trains on JS-style JSON             | Use a stricter model or a JSON-mode-supporting one. |
| Output truncated mid-object                          | `max_tokens=2048` exceeded                           | Bump `max_tokens` in [`openrouter_client.py`](../politico_playbook/llm/openrouter_client.py); split the section. |
| Plausible JSON but wrong shape (extra/missing keys)  | `strict: true` schema validation failed              | Tighten the prompt to enumerate required keys; or relax the schema. |

The `_extract_one_section` path catches `json.JSONDecodeError` from the
client and records the row as `parse_failed`. The OpenRouter client
(`openrouter_client.py:140-144`) logs a warning for each failed parse — set
`LOG_LEVEL=DEBUG` in `.env` to see them streamed.

### Prompt-tightening workflow

1. Pull a failure: `SELECT raw_response FROM extractions WHERE id=<id>;`.
2. Identify the offense (use the table above).
3. Edit the offending section in
   [`extraction_prompts.yaml`](../politico_playbook/config/extraction_prompts.yaml).
4. Mark the failed messages as pending again:

   ```sql
   UPDATE raw_emails SET processing_status='pending'
   WHERE gmail_message_id IN (
     SELECT DISTINCT gmail_message_id FROM extractions WHERE extraction_status='parse_failed'
   );
   ```
5. Re-run `extract --limit 5` to validate; iterate.

## Diagnosing `api_failed`

`api_failed` rows are the OpenRouter request raising. The `raw_response`
column is the exception text. Two failure shapes dominate:

### Rate limits (free-tier models)

```text
Error code: 429 - {'error': {'message': 'Rate limit exceeded:
limit_rpm/qwen/qwen3-next-80b-a3b-instruct-2509/...
limited to 8 requests per minute. Please retry shortly.', ...}}
```

Free-tier OpenRouter models (model IDs ending in `:free`) cap at single-
digit RPM. They're for development sampling, not backfill. Switch to a paid
slug for any sustained run:

```bash
# In .env
MODEL_ID=deepseek/deepseek-v4-flash-20260423   # ~$0.14/$0.28 per M tokens
```

If you see 429s from a paid model, check OpenRouter's status page and your
account balance.

### Model removed / renamed

OpenRouter occasionally retires or re-slugs models. The exception will
read like `model 'foo/bar' not found`. Validate any `MODEL_ID` you set
against [openrouter.ai/models](https://openrouter.ai/models) before
backfill.

### Surface api_failed rows

```sql
SELECT id, section_header, model_id, substr(raw_response, 1, 200) AS preview
FROM extractions
WHERE extraction_status = 'api_failed'
ORDER BY id DESC;
```

### Recovery

Once you've fixed the underlying cause (model swap, balance top-up):

```sql
-- Reset just the affected messages
UPDATE raw_emails SET processing_status='pending'
WHERE gmail_message_id IN (
  SELECT DISTINCT gmail_message_id FROM extractions WHERE extraction_status='api_failed'
);
```

Then run `extract` again. The new row replaces the old one for the same
`(message, section, model)` key.

## Quota management

### Gmail API

Read-only Gmail traffic is generous: the user-level quota is in the millions
of units per day, and listing a thread costs ~5 units. We're nowhere close.
Throttling not required.

### OpenRouter

Two ceilings to track:

- **Model-level RPM** (free-tier models): hard, per-minute. Can't be raised.
  Solution: paid model.
- **Account spend**: dashboard at [openrouter.ai/credits](https://openrouter.ai/credits).
  Watch token usage by model:

  ```sql
  SELECT
      model_id,
      COUNT(*) AS calls,
      SUM(prompt_tokens) AS in_tokens,
      SUM(completion_tokens) AS out_tokens
  FROM extractions
  GROUP BY model_id
  ORDER BY calls DESC;
  ```

  Multiply by the model's per-token cost (from
  [openrouter.ai/models](https://openrouter.ai/models)) to estimate spend.
  As of 2026-05-05 the live DB shows:

  ```
  deepseek/deepseek-v4-flash               | 51 calls | 61,763 in | 77,703 out
  qwen/qwen3-next-80b-a3b-instruct:free    |  7 calls |  3,809 in |  2,921 out
  ```

  At DeepSeek's $0.14/M input + $0.28/M output, that's roughly $0.03 to date
  — an entire single-newsletter backfill. Paid models are not the cost
  driver at this scale; the prompt design is what matters.

## Inventory & monitoring

### What's in the store right now

```sql
-- Per-newsletter coverage and date range
SELECT
    newsletter_slug,
    COUNT(*) AS messages,
    MIN(received_at) AS earliest,
    MAX(received_at) AS latest
FROM raw_emails
GROUP BY newsletter_slug
ORDER BY messages DESC;

-- Stage 2 progress
SELECT processing_status, COUNT(*) FROM raw_emails GROUP BY processing_status;
```

### Backfill scope estimate

The registry enumerates 27 newsletters, but only `politicoplaybook` has
been backfilled so far (25 messages over a two-week window). Order of
magnitude for a 15-month full backfill, assuming the median newsletter
publishes ~5×/week:

```
27 newsletters × ~5 issues/week × ~65 weeks ≈ 8,800 messages
```

At Stage 2 cost (~50 messages → 51 LLM calls → ~140k tokens with DeepSeek),
total spend for a full 15-month backfill is in the **single-digit dollars**
range against DeepSeek-class models. Don't pre-optimize.

### Logs

The runner uses Python's stdlib `logging` with format
`%(asctime)s [%(levelname)s] %(name)s: %(message)s`. Default level is
`INFO`; override with `--log-level DEBUG` or `LOG_LEVEL=DEBUG` in `.env`.

Per-module loggers:

- `ingestion.runner` — top-level orchestration
- `llm.openrouter` — request/response, JSON parse warnings
- `processing.section_extractor` — per-section extraction events

Pipe to a file for long backfills; the log lines contain enough context to
reconstruct what happened section-by-section without re-running.

## OAuth token recovery

If `token.json` rots (scope changes, account revocation), delete it and
re-run any ingest command:

```bash
rm ~/.config/politico-pipeline/token.json
python -m politico_playbook.ingestion.runner incremental
# Browser tab opens for re-consent.
```

For broader OAuth troubleshooting, see [oauth-setup.md](./oauth-setup.md).

## When something feels wrong

Quick triage queries:

```sql
-- 1. Is the store actually growing?
SELECT COUNT(*) FROM raw_emails;
SELECT MAX(ingested_at) FROM raw_emails;

-- 2. Are extractions keeping up?
SELECT processing_status, COUNT(*) FROM raw_emails GROUP BY processing_status;

-- 3. Is one model causing all failures?
SELECT model_id, extraction_status, COUNT(*)
FROM extractions
GROUP BY model_id, extraction_status;

-- 4. Are sections being typed correctly?
SELECT section_type, COUNT(*)
FROM extractions
GROUP BY section_type
ORDER BY 2 DESC;
```

If you see a flood of `unclassified` extractions, a newsletter has likely
introduced a header that's not in
[`section_taxonomy.yaml`](../politico_playbook/config/section_taxonomy.yaml).
Add it under `shared:` or `by_newsletter:` and re-extract — see
[CONFIGURATION.md → Adding a header](./CONFIGURATION.md#adding-a-header).
