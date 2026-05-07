# Architecture

End-to-end overview of the v0.2 pipeline: how a Gmail message becomes a row
in the `extractions` table. Reference docs split this material by topic —
schema details live in [SCHEMA.md](./SCHEMA.md), config semantics in
[CONFIGURATION.md](./CONFIGURATION.md), JSON output shapes in
[EXTRACTION-OUTPUT.md](./EXTRACTION-OUTPUT.md). This page is the connective
tissue.

For the original design rationale (why these decisions, what was rejected),
see the [v0.2 design spec](./superpowers/specs/2026-05-05-multi-newsletter-ingestion-design.md).

## Data flow

```
                    ┌──────────────────────────────────────┐
                    │  Gmail (politicollector@gmail.com)   │
                    └──────────────────┬───────────────────┘
                                       │  OAuth (gmail.readonly)
                                       ▼
                ┌──────────────────────────────────────────────┐
                │  GmailClient.list_message_ids + fetch_message │
                │  ingestion/gmail_client.py                   │
                └──────────────────┬───────────────────────────┘
                                       │  GmailMessage
                                       ▼
                ┌──────────────────────────────────────────────┐
                │  NewsletterRegistry.slug_from_sender         │
                │  ingestion/newsletter_registry.py            │
                │  ─ allowed-domain check                       │
                │  ─ sender → slug (politicopro = synthetic)    │
                │  ─ active? (skip inactive)                    │
                └──────────────────┬───────────────────────────┘
                                       │  RawEmail dataclass
                                       ▼
                ┌──────────────────────────────────────────────┐
                │  RawEmailStore.upsert (INSERT OR IGNORE)     │
                │  ingestion/raw_store.py                      │
                │  ─ idempotent on gmail_message_id             │
                │  ─ initial processing_status = 'pending'      │
                └──────────────────┬───────────────────────────┘
                                       │
                                       ▼
                ╔══════════════════════════════════════════════╗
                ║       data/raw_emails.db :: raw_emails       ║
                ╚══════════════════════════════════════════════╝
                                       │
                                       │  iter_pending()
                                       ▼
                ┌──────────────────────────────────────────────┐
                │  DefaultParser.parse                         │
                │  ingestion/parser_base.py                    │
                │  ─ strip BEGIN-REGION...END-REGION sponsor    │
                │  ─ split on known headers                     │
                │  ─ classify each section via SectionTaxonomy  │
                │     (per-newsletter > shared > skip > unclass)│
                └──────────────────┬───────────────────────────┘
                                       │  list[Section]
                                       ▼
                ┌──────────────────────────────────────────────┐
                │  PromptRegistry.for_section_type             │
                │  processing/section_extractor.py             │
                │  ─ resolves `inherit:` chain                  │
                │  ─ returns (system, user_template, schema)    │
                └──────────────────┬───────────────────────────┘
                                       │
                                       ▼
                ┌──────────────────────────────────────────────┐
                │  OpenRouterClient.complete                   │
                │  llm/openrouter_client.py                    │
                │  ─ OpenAI SDK → openrouter.ai/api/v1          │
                │  ─ response_format = json_schema (strict)     │
                │  ─ Anthropic prompt-cache marker if model     │
                │    starts with `anthropic/`                   │
                └──────────────────┬───────────────────────────┘
                                       │  LLMResponse(content, parsed, …)
                                       ▼
                ┌──────────────────────────────────────────────┐
                │  SectionExtractor._save_extraction           │
                │  ─ INSERT OR REPLACE (idempotent on UNIQUE)   │
                │  ─ status: ok | parse_failed | api_failed     │
                └──────────────────┬───────────────────────────┘
                                       │
                                       ▼
                ╔══════════════════════════════════════════════╗
                ║      data/raw_emails.db :: extractions       ║
                ╚══════════════════════════════════════════════╝
                                       │
                                       │  ⏳ not yet implemented in v0.2
                                       ▼
                  ┌────────────────────────────────────────┐
                  │  Stage 3: Entity normalization (⏳)    │
                  │  Stage 4: Graph + temporal (⏳)        │
                  │  See ROADMAP.md                         │
                  └────────────────────────────────────────┘
```

## Component map

| File | Role |
|------|------|
| [`ingestion/gmail_client.py`](../politico_playbook/ingestion/gmail_client.py) | OAuth flow + Gmail API fetch. Returns `GmailMessage` dataclasses. |
| [`ingestion/newsletter_registry.py`](../politico_playbook/ingestion/newsletter_registry.py) | Loads `newsletters.yaml`. Maps sender address → slug → `Newsletter` config. |
| [`ingestion/raw_store.py`](../politico_playbook/ingestion/raw_store.py) | SQLite `raw_emails` table. Idempotent upsert; `iter_pending()` for Stage 2. |
| [`ingestion/parser_base.py`](../politico_playbook/ingestion/parser_base.py) | Sponsor strip + section split. `SectionTaxonomy` resolves headers to types. Parser registry: `default`, `pro_multi_vertical`. |
| [`ingestion/runner.py`](../politico_playbook/ingestion/runner.py) | Single CLI entry point: `backfill | incremental | inventory | extract`. |
| [`llm/openrouter_client.py`](../politico_playbook/llm/openrouter_client.py) | OpenAI SDK → OpenRouter. Provider-agnostic completion with optional structured-output mode. |
| [`processing/section_extractor.py`](../politico_playbook/processing/section_extractor.py) | Stage 2 driver. Owns `extractions` table DDL. `PromptRegistry` resolves `inherit:` chains. |
| [`processing/database_normalizer.py`](../politico_playbook/processing/database_normalizer.py) | ⏳ Stage 3 — file-based v0.1 code; not yet ported to SQLite. |
| [`processing/temporal_analyzer.py`](../politico_playbook/processing/temporal_analyzer.py) | ⏳ Stage 4 — file-based v0.1 code; not yet ported. |
| [`config/newsletters.yaml`](../politico_playbook/config/newsletters.yaml) | Registry: 27 newsletters across the POLITICO landscape. |
| [`config/section_taxonomy.yaml`](../politico_playbook/config/section_taxonomy.yaml) | Header → semantic-type mappings, with per-newsletter overrides. |
| [`config/extraction_prompts.yaml`](../politico_playbook/config/extraction_prompts.yaml) | Per-section-type system/user prompt + JSON schema. |

## Stage maturity matrix

| Stage   | Description                       | Status  | Persistence layer            |
|---------|-----------------------------------|---------|------------------------------|
| Stage 1 | Gmail → SQLite raw store          | ✅      | `raw_emails` table           |
| Stage 2 | Section-aware LLM extraction      | ✅      | `extractions` table          |
| Stage 3 | Entity normalization & dedup      | ⏳      | TBD (legacy: `data/structured/`) |
| Stage 4 | Graph build + temporal analytics  | ⏳      | TBD (legacy: `data/structured/`) |
| Stage 5 | Visualization                     | 🚧      | Not started                  |

Stage 3 and 4 file-based code from v0.1 still lives in
`processing/database_normalizer.py` and `processing/temporal_analyzer.py` for
reference but is not invoked by the runner. The port-to-SQLite design lives
in [ROADMAP.md](./ROADMAP.md#stage-3-entity-normalization-port).

## Idempotency

Re-running any pipeline command must be safe. Two keys make this work:

| Boundary       | Key                                                              | Mechanism |
|----------------|------------------------------------------------------------------|-----------|
| Gmail ingest   | `raw_emails.gmail_message_id` (PRIMARY KEY)                      | `INSERT OR IGNORE` — `RawEmailStore.upsert` returns `True` only on first insert. The runner also short-circuits with `has_message()` before the expensive `fetch_message` call. |
| Stage 2 extract | `extractions(gmail_message_id, section_index, model_id)` (UNIQUE) | `INSERT OR REPLACE` — re-running with the same model overwrites; switching `MODEL_ID` produces a new row instead of clobbering. |

Practical implications:

- `backfill` is always safe; it'll just re-issue the Gmail query and skip
  every dup.
- `incremental` adds a server-side `after:YYYY/MM/DD` clause based on the
  store's `MAX(received_at)`, so it doesn't even fetch dups in the first
  place.
- `extract` skips messages whose `processing_status` is not `pending`. To
  re-extract, manually flip status: `UPDATE raw_emails SET processing_status='pending' WHERE …`.
- A/B comparing two models: change `MODEL_ID` in `.env`, run `extract`. Both
  rows now exist in `extractions`; query with the comparison SQL in
  [SCHEMA.md → A/B model comparison](./SCHEMA.md#ab-model-comparison).

## Why these design choices

Quick rationale; the [design spec](./superpowers/specs/2026-05-05-multi-newsletter-ingestion-design.md)
has the full discussion.

### Gmail API + OAuth (not IMAP + App Password)

App Passwords were deprecated for personal Google accounts. OAuth gives us
read-only scope (`gmail.readonly`), per-message message IDs that survive
folder moves, and label/category filtering at the API layer. Setup friction
is real but one-time; see [oauth-setup.md](./oauth-setup.md).

### SQLite (not Postgres, not files)

Single-user, single-host workload. SQLite gives us:

- Free joins between `raw_emails` and `extractions`.
- JSON1 functions for queries against `parsed_json` without a separate ETL.
- A single file (`raw_emails.db`) that backs up trivially.
- No daemon to manage.

Postgres would be overkill for ~1k–10k messages. We can migrate later if
volume demands it; the schema is portable.

### OpenRouter (not direct Anthropic SDK)

Cost dropped ~5× vs. v0.1 (caching only — OpenRouter doesn't proxy
Anthropic's Message Batches API), but the bigger win is **provider
optionality**: change `MODEL_ID` to swap from DeepSeek to Claude to Gemini
without touching code. Stage 2 prompts work across providers because we
talk to all of them through the OpenAI Chat Completions schema.

Tradeoff: when routing to Anthropic models we lose the 50% Batches discount.
For high-volume backfill against a Claude model, calling Anthropic directly
is cheaper. The runtime client (`llm/openrouter_client.py:_is_anthropic_model`)
does pass through Anthropic's `cache_control` marker for prompt caching.

### YAML-driven config (not hardcoded)

`newsletters.yaml`, `section_taxonomy.yaml`, and `extraction_prompts.yaml`
are data, not code. Adding the 28th newsletter, retypring a section, or
tightening a prompt is a YAML edit + a re-run — no PR, no test churn.
[CONFIGURATION.md](./CONFIGURATION.md) walks through each file.

### Section-typed prompts (not whole-body extraction)

A `personnel_change` section is a numbered list of name/role pairs; a
`lead_story` is free-form prose; a `social_graph` section is a comma-
separated name dump. One prompt does *not* fit all of these. The taxonomy
pre-classifies sections so Stage 2 can specialize. See
[EXTRACTION-OUTPUT.md](./EXTRACTION-OUTPUT.md) for what each specialization
returns.

## Operational expectations

- **Backfill cost & rate**: model-dependent. Free-tier models (`*:free`) cap
  at single-digit RPM and *will* return `429`s under any sustained load.
  Paid workhorses like `deepseek/deepseek-v4-flash` handle batches; see
  [OPERATIONS.md → Quota management](./OPERATIONS.md#quota-management).
- **Stage 2 quality**: ~25% of `lead_story` and `news_brief` extractions
  currently land in `parse_failed` — strict JSON-schema validation rejects
  smart quotes, trailing commas, and code-fence-wrapped output. Triage SQL
  and prompt-tightening checklist live in
  [OPERATIONS.md → Diagnosing parse_failed](./OPERATIONS.md#diagnosing-parse_failed).
- **No scheduler**: the runner is invoked manually or via cron — see
  [OPERATIONS.md → Daily incremental fetch](./OPERATIONS.md#daily-incremental-fetch).

## Where Stage 3+ will plug in

Stage 3 reads `extractions` and writes a normalized entity store; Stage 4
builds the graph from that. The file-based v0.1 versions
(`database_normalizer.py`, `temporal_analyzer.py`) define the analytical
surface but consume JSON files, not the SQLite extractions table. The port
plan is a sketched-out section in [ROADMAP.md](./ROADMAP.md).
