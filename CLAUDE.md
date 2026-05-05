# Politico Playbook Extraction Tool - Development Guide

## Project Overview

NLP data extraction tool for analyzing the **POLITICO newsletter family** —
~27 newsletters across the Politico landscape (flagship Playbook, state
Playbooks, vertical dailies, weeklies, Politico Pro) — to extract structured
political intelligence data.

### Project Goals
1. **Multi-Newsletter Ingestion**: Pull all subscribed POLITICO newsletters
   from a dedicated Gmail inbox via the Gmail API.
2. **Section-Aware Parsing**: Strip sponsor blocks, identify named sections
   (`TRANSITIONS`, `MEDIA MOVES`, `SPOTTED`, `HAPPY BIRTHDAY`, etc.) and
   resolve cross-newsletter label variants to a shared semantic taxonomy.
3. **Entity & Relationship Extraction**: Use a model-agnostic LLM layer
   (OpenRouter) with section-typed prompts to extract:
   - Personnel changes (job moves — entity goldmine)
   - Social graph (event attendance, birthday rosters)
   - Lead-story narrative entities
   - Campaign-news data (candidates, endorsements, fundraising)
4. **Idempotent Storage**: SQLite-backed raw email store and structured
   extraction store, both keyed for safe re-runs.
5. **Visualization**: Future — network graphs showing political relationships.

### Current Implementation Status

**v0.2 Multi-newsletter pipeline (current)**
- ✅ Gmail API + OAuth ingestion (`src/ingestion/gmail_client.py`)
- ✅ SQLite raw email store, idempotent on `gmail_message_id` (`src/ingestion/raw_store.py`)
- ✅ Newsletter registry (27 newsletters in `config/newsletters.yaml`)
- ✅ Section taxonomy with per-newsletter overrides (`config/section_taxonomy.yaml`)
- ✅ Section-aware parser (`src/ingestion/parser_base.py`)
- ✅ OpenRouter client, model-swappable via `MODEL_ID` env var (`src/llm/openrouter_client.py`)
- ✅ Section-typed extraction prompts (`config/extraction_prompts.yaml`)
- ✅ Stage 2 extractor with structured JSON output (`src/processing/section_extractor.py`)
- ✅ Single CLI runner: `backfill | incremental | inventory | extract`
- ⏳ Stage 3 (entity normalization/dedup) and Stage 4 (graph/temporal) — not yet
  ported to the new SQLite-backed pipeline; old file-based versions remain in
  `src/processing/database_normalizer.py` and `temporal_analyzer.py`.

**v0.1 POC (deprecated, preserved at git tag `v0.1-poc-single-source`)**
- IMAP App Password ingestion, single newsletter (Playbook), 4-day window
- Direct Anthropic SDK calls, two-tier Haiku/Sonnet routing
- File-based raw HTML / structured JSON
- Old code remains at `src/extraction/` and `src/processing/claude_nlp_processor.py`
  (marked deprecated). Do not extend; new work goes in the v0.2 modules.

## Project Structure (v0.2)

```
politico_playbook/
├── config/
│   ├── newsletters.yaml          # 27 newsletters keyed by sender slug
│   ├── section_taxonomy.yaml     # Header → semantic-type mappings
│   ├── extraction_prompts.yaml   # Stage 2 prompts + JSON schemas
│   └── lexicon.json              # Legacy (v0.1)
├── data/
│   ├── raw_emails.db             # SQLite raw store (gitignored)
│   ├── raw/                      # Legacy v0.1 HTML files (gitignored)
│   └── ...                       # Legacy v0.1 outputs
├── src/
│   ├── ingestion/                # NEW (v0.2) — Gmail → SQLite
│   │   ├── gmail_client.py       # OAuth API client
│   │   ├── newsletter_registry.py
│   │   ├── parser_base.py        # Section-aware preprocessing
│   │   ├── raw_store.py          # SQLite raw_emails table
│   │   └── runner.py             # CLI: backfill / incremental / inventory / extract
│   ├── llm/                      # NEW (v0.2) — Model-agnostic
│   │   └── openrouter_client.py  # OpenAI SDK → OpenRouter base URL
│   ├── processing/
│   │   ├── section_extractor.py  # NEW (v0.2) — Stage 2 via OpenRouter
│   │   ├── claude_nlp_processor.py   # DEPRECATED (v0.1)
│   │   ├── database_normalizer.py    # Stage 3 (file-based, not yet ported)
│   │   ├── temporal_analyzer.py      # Stage 4 (file-based, not yet ported)
│   │   ├── html_to_json.py
│   │   └── nlp_processor.py
│   ├── extraction/               # DEPRECATED (v0.1) — IMAP path
│   │   ├── email_client.py
│   │   └── html_parser.py
│   ├── models/schemas.py         # JSON schemas (legacy v0.1)
│   ├── pipeline_orchestrator.py  # Legacy v0.1 orchestrator
│   └── utils/
└── tests/
```

### Root Level Files
- `.env` / `.env.example` — OAuth and OpenRouter credentials
- `.gitignore` — Excludes `*.db`, OAuth secrets, scratch files
- `requirements.txt` — Updated with `google-api-python-client`, `openai`, `pyyaml`
- `docs/superpowers/specs/2026-05-05-multi-newsletter-ingestion-design.md` —
  Active design doc for the v0.2 architecture

## Key Development Commands

### Environment setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### One-time Gmail OAuth setup
1. Go to https://console.cloud.google.com/apis/credentials
2. Create an OAuth 2.0 Client ID (type: Desktop app)
3. Download the client JSON to `~/.config/politico-pipeline/oauth_client.json`
   (path configurable via `GOOGLE_OAUTH_CLIENT_SECRETS` env var)
4. Enable the Gmail API for your project
5. First `backfill` run will open a browser tab to complete consent; the
   resulting token is cached at `GOOGLE_OAUTH_TOKEN_PATH`.

### One-time OpenRouter setup
1. Sign up at https://openrouter.ai/ and grab a key from `/keys`
2. Set `OPENROUTER_API_KEY` and `MODEL_ID` in `.env` (see `.env.example`)

### Pipeline commands
All operations go through one CLI runner:

```bash
# Pull all matching messages from Gmail (idempotent — safe to re-run)
python -m politico_playbook.src.ingestion.runner backfill

# Pull only messages newer than the last stored message
python -m politico_playbook.src.ingestion.runner incremental

# Restrict to a single newsletter
python -m politico_playbook.src.ingestion.runner backfill --newsletter politicoplaybook

# Cap fetched messages (testing)
python -m politico_playbook.src.ingestion.runner backfill --limit 50

# Show what's currently in the local DB
python -m politico_playbook.src.ingestion.runner inventory

# Run Stage 2 entity extraction on all 'pending' messages
python -m politico_playbook.src.ingestion.runner extract

# Process only N pending (testing — keeps spend low)
python -m politico_playbook.src.ingestion.runner extract --limit 5
```

### Querying the raw store directly
```bash
sqlite3 data/raw_emails.db "SELECT newsletter_slug, COUNT(*) FROM raw_emails GROUP BY newsletter_slug ORDER BY 2 DESC"
sqlite3 data/raw_emails.db "SELECT section_type, COUNT(*) FROM extractions GROUP BY section_type"
```

### Code quality
```bash
black politico_playbook/
flake8 politico_playbook/
pytest tests/
```

## Subagent Integration Points

### 1. Database Schema Architect (`database-schema-architect`)
**When to use**: Designing the SQLite database schema for storing extracted data
**Tasks**:
- Design normalized schema for entities, relationships, and events
- Create migration scripts for database updates
- Optimize queries for relationship traversal
- Implement indexing strategy for performance

### 2. Python Code Architect (`python-code-architect`)
**When to use**: Reviewing and refactoring the extraction/processing pipeline
**Tasks**:
- Review current code architecture and suggest improvements
- Design proper abstraction layers for the extraction pipeline
- Implement design patterns for extensibility
- Refactor duplicate code and improve modularity

### 3. Test Suite Engineer (`test-suite-engineer`)
**When to use**: Creating comprehensive test coverage
**Tasks**:
- Write unit tests for each extraction module
- Create integration tests for the full pipeline
- Develop fixtures for newsletter test data
- Implement continuous testing strategy

### 4. NLP Processor (`nlp-processor`)
**When to use**: Analyzing newsletter text and extracting entities/relationships
**Tasks**:
- Extract key personnel and organizations from text
- Identify relationship patterns in newsletters
- Perform similarity analysis between newsletters
- Extract keywords and themes from content

### 5. AI Service Integrator (`ai-service-integrator`)
**When to use**: If advanced text analysis beyond spaCy is needed
**Tasks**:
- Integrate Claude API for complex relationship extraction
- Implement prompt engineering for political context understanding
- Design fallback strategies for API failures
- Optimize API usage for cost efficiency

### 6. Documentation Auditor (`codebase-doc-auditor`)
**When to use**: After major refactoring to ensure documentation is current
**Tasks**:
- Update all docstrings and comments
- Ensure README accurately reflects new structure
- Document API endpoints and data formats
- Create user guides for the extraction pipeline

## Priority Tasks (Next Steps)

1. **DONE (v0.2)**: Multi-newsletter Gmail API ingestion, SQLite raw store,
   section-aware parser, OpenRouter Stage 2 with section-typed prompts.
2. **NEXT**: Run a real backfill — requires user to set up Google OAuth
   credentials and `OPENROUTER_API_KEY`. Validate the model
   `tencent/hy3-preview:free` slug against OpenRouter's catalog (if invalid,
   swap to `anthropic/claude-haiku-4-5` or `google/gemini-2.5-flash`).
3. **MEDIUM**: Port Stage 3 (entity normalization/dedup) to consume the
   `extractions` SQLite table instead of file-based JSON in
   `data/structured/`.
4. **MEDIUM**: Port Stage 4 (graph + temporal) similarly.
5. **MEDIUM**: Add fuzzy section header matching for Politico format drift
   over the 15-month backfill window.
6. **LOW**: Visualization layer (network graphs, timeline views).

## v0.2 Architecture Notes

### Model layer — OpenRouter (model-agnostic)
The pipeline does not depend on any provider's SDK. `MODEL_ID` env var
selects the model; the OpenAI SDK pointed at `https://openrouter.ai/api/v1`
handles routing. Anthropic prompt caching is passed through via
`extra_body` when `MODEL_ID` starts with `anthropic/`.

Tradeoff: OpenRouter does not proxy Anthropic's Message Batches API (50%
discount), so cost reduction vs. v0.1 is ~5x (caching only) rather than
~10x (caching + batches). Optionality of swapping providers is the win.

### Section taxonomy
The same semantic concept appears under different labels across newsletters
— `TRANSITIONS` in flagship Playbook, `Names in the News` in Pulse,
`WHITE HOUSE SHAKE-UP` as inline callouts in Weekly Score. The YAML
taxonomy in `config/section_taxonomy.yaml` resolves these to a small set
of types (`personnel_change`, `social_graph`, `lead_story`, `campaign_news`,
`news_brief`, `state_news`, `financial`, `links_only`, `ignore`) that
Stage 2 prompts specialize on.

### Idempotency
- Ingestion is keyed on `gmail_message_id` (Gmail's stable message ID).
  Re-running `backfill` is a no-op for already-stored messages.
- Extraction is keyed on `(gmail_message_id, section_index, model_id)`.
  Re-running `extract` skips already-processed messages via
  `processing_status` and re-running for the same model writes idempotently.
  Switching `MODEL_ID` produces a fresh extraction row, useful for A/B
  comparison.

## Outstanding Issues

- **Stage 3 / 4 not yet wired to v0.2**: `database_normalizer.py` and
  `temporal_analyzer.py` still consume file-based JSON from
  `data/structured/`. They need to be ported to read from the
  `extractions` SQLite table.
- **`tencent/hy3-preview:free` slug**: Free-tier model with aggressive rate
  limits (~20-200 req/day). Verify exact slug against
  https://openrouter.ai/models before a real run; expect to swap to a paid
  model for production-volume backfill.
- **Politico Pro multi-vertical sender**: `newsletter@email.politicopro.com`
  represents many sub-newsletters disambiguated by subject. The
  `pro_multi_vertical` parser is currently a stub (falls through to
  default); a subject-pattern dispatcher needs to be added once Pro
  newsletters are in the DB.

## Updated Dependencies

```txt
# Core dependencies
requests==2.31.0
beautifulsoup4==4.12.2
python-dotenv==1.0.0
pandas==2.1.4
lxml==4.9.3

# NLP and text processing
spacy>=3.7.0
nltk>=3.8.0

# Database
sqlalchemy>=2.0.0

# Visualization and analysis
networkx>=3.2.0
matplotlib>=3.8.0
plotly>=5.17.0

# Web interface (for future development)
streamlit>=1.29.0
flask>=3.0.0

# Development tools
pytest==7.4.3
black==23.11.0
flake8==6.1.0
```

## Security Notes ✅ IMPLEMENTED

- ✅ Gmail credentials now stored in `.env` file (not committed to git)
- ✅ `.env.example` provides template for new developers
- ✅ `email_client.py` updated to use `os.getenv()` for credentials
- ✅ `.gitignore` properly configured to ignore sensitive files
- ✅ Removed hardcoded passwords from all source code

## Testing Strategy

1. **Unit Tests**: Test individual extraction functions
2. **Integration Tests**: Test full pipeline with sample data
3. **Regression Tests**: Ensure changes don't break existing functionality
4. **Performance Tests**: Monitor processing speed for large datasets

## Notes for Development

- Always use environment variables for sensitive data ✅
- Follow PEP 8 style guidelines
- Write tests for new functionality
- Document complex extraction patterns
- Use type hints for better code clarity
- Implement logging for debugging
- Consider rate limiting for email extraction
- Plan for incremental/resumable processing

## Migration Summary

### v0.1 → v0.2 (2026-05-05) — Multi-newsletter ingestion redesign

**What changed**:
- IMAP App Password → Gmail API + OAuth (`src/ingestion/gmail_client.py`)
- File-based raw HTML → SQLite `raw_emails.db` keyed on `gmail_message_id`
- Single newsletter (Playbook) → 27 newsletters across the Politico landscape,
  driven by `config/newsletters.yaml`
- Hardcoded date window (Aug 1-4 2025) → configurable via CLI / incremental mode
- Direct Anthropic SDK → OpenRouter via OpenAI-compatible client
  (model-agnostic; swap providers via `MODEL_ID` env var)
- Whole-body LLM extraction → section-aware extraction with section-typed
  prompts and JSON schemas
- Multiple scripts → single CLI runner: `python -m politico_playbook.src.ingestion.runner <mode>`

**What was kept**:
- `src/processing/database_normalizer.py` and `temporal_analyzer.py`
  (Stages 3-4) — still file-based, to be ported.
- `src/extraction/` — kept as a v0.1 reference path. Marked deprecated.
- `src/processing/claude_nlp_processor.py` — kept for v0.1 compatibility.

**Recovery**: `git checkout v0.1-poc-single-source` returns to the original
single-source POC state.

### Pre-v0.1 → v0.1 (legacy) — Initial reorganization

- `src/data/newsletters/` → `politico_playbook/data/raw/`
- `src/data/text/` → `politico_playbook/data/processed/`
- `src/email_extractor.py` → `politico_playbook/src/extraction/email_client.py`
- `src/html_formatter.py` → `politico_playbook/src/extraction/html_parser.py`
- `src/main.py` → `politico_playbook/main.py`
- `lexicon.json` → `politico_playbook/config/lexicon.json`