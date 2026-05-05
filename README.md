# Politico Newsletter Intelligence Pipeline

A Python pipeline that ingests the **POLITICO newsletter family** (~27
newsletters: flagship Playbook, state Playbooks, vertical dailies/weeklies,
Politico Pro) from a dedicated Gmail inbox and extracts structured political
intelligence — personnel changes, social-graph signals, campaign data, and
narrative entities.

For full architecture details, see [CLAUDE.md](./CLAUDE.md) and the
[design doc](./docs/superpowers/specs/2026-05-05-multi-newsletter-ingestion-design.md).

## Architecture (v0.2)

```
Gmail (OAuth) → SQLite raw_emails → Section-aware parser → OpenRouter LLM → SQLite extractions
```

- **Ingestion**: Gmail API with OAuth, idempotent on `gmail_message_id`.
- **Parser**: Sponsor-block stripping + section detection driven by
  `config/section_taxonomy.yaml` (sender-slug-aware overrides).
- **Stage 2**: Model-agnostic via OpenRouter — swap providers by changing
  `MODEL_ID` in `.env`. Section-typed prompts in
  `config/extraction_prompts.yaml`.

## Setup

```bash
# 1. Environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Gmail OAuth (one-time)
#    - Create OAuth Desktop client at console.cloud.google.com/apis/credentials
#    - Save JSON to ~/.config/politico-pipeline/oauth_client.json
#    - Enable Gmail API for the project

# 3. OpenRouter
#    - Get a key from openrouter.ai/keys
#    - Copy .env.example -> .env, fill in OPENROUTER_API_KEY and MODEL_ID

cp .env.example .env
# edit .env
```

## Usage

All operations go through one CLI runner:

```bash
# Pull all matching messages from Gmail (idempotent)
python -m politico_playbook.ingestion.runner backfill

# Pull only what's new since the last run
python -m politico_playbook.ingestion.runner incremental

# Show what's in the local DB
python -m politico_playbook.ingestion.runner inventory

# Run section-aware Stage 2 extraction on all 'pending' messages
python -m politico_playbook.ingestion.runner extract --limit 5
```

Subcommand flags: `--newsletter <slug>` to scope to one newsletter,
`--limit N` to cap fetched/processed messages.

## Querying results

```bash
# Counts per newsletter
sqlite3 data/raw_emails.db \
  "SELECT newsletter_slug, COUNT(*) FROM raw_emails GROUP BY newsletter_slug ORDER BY 2 DESC"

# Extraction breakdown by section type
sqlite3 data/raw_emails.db \
  "SELECT section_type, COUNT(*) FROM extractions GROUP BY section_type ORDER BY 2 DESC"

# Latest personnel changes
sqlite3 data/raw_emails.db \
  "SELECT gmail_message_id, parsed_json FROM extractions
   WHERE section_type='personnel_change' AND extraction_status='ok'
   ORDER BY extracted_at DESC LIMIT 10"
```

## Development

```bash
black politico_playbook/
flake8 politico_playbook/
pytest tests/
```

## Migration from v0.1

v0.1 (single-source IMAP, direct Anthropic SDK, file-based pipeline) is
preserved at git tag `v0.1-poc-single-source`. The v0.1 code paths were
deleted from the working tree on 2026-05-05; recover any specific file with
`git checkout v0.1-poc-single-source -- <path>`. Active code lives in
`politico_playbook/ingestion/`, `politico_playbook/llm/`, and
`politico_playbook/processing/section_extractor.py`.
