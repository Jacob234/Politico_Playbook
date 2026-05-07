# Politico Playbook — Documentation

Reference docs for the v0.2 multi-newsletter ingestion + extraction
pipeline. The root [`README.md`](../README.md) covers setup; the docs here
cover everything else.

## Quick reference

| Doc                                                                                                   | Answers                                                                                                | For                  |
|-------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|----------------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md)                                                                  | "How does the pipeline work end-to-end? Which file does which job?"                                    | Onboarder, dev       |
| [SCHEMA.md](./SCHEMA.md)                                                                              | "What columns are in `raw_emails` / `extractions`? What do their values mean?"                         | Dev, query author    |
| [CONFIGURATION.md](./CONFIGURATION.md)                                                                | "How do `newsletters.yaml`, `section_taxonomy.yaml`, `extraction_prompts.yaml` interact? How do I add a newsletter?" | Dev, operator        |
| [EXTRACTION-OUTPUT.md](./EXTRACTION-OUTPUT.md)                                                        | "What's the JSON shape of `parsed_json` for each section type? Show me real samples."                  | Dev, downstream consumer |
| [OPERATIONS.md](./OPERATIONS.md)                                                                      | "How do I run the pipeline daily? Diagnose `parse_failed`? Switch models safely?"                      | Operator             |
| [ROADMAP.md](./ROADMAP.md)                                                                            | "What's next? When will Stage 3/4 be ported? What's blocking visualization?"                            | Dev, planning        |
| [oauth-setup.md](./oauth-setup.md)                                                                    | "How do I set up Google OAuth for the Gmail client the first time?"                                    | Onboarder            |
| [superpowers/specs/2026-05-05-multi-newsletter-ingestion-design.md](./superpowers/specs/2026-05-05-multi-newsletter-ingestion-design.md) | "Why was v0.2 designed this way? What was rejected?"                                                    | Historical context   |

## Conventions used in these docs

- **Status badges**: ✅ shipped · ⏳ designed but not built · 🚧 not yet
  designed. Used in stage maturity tables and in [ROADMAP.md](./ROADMAP.md).
- **File-path links**: every code path mentioned (e.g.,
  `politico_playbook/ingestion/runner.py`) is a clickable link to the
  actual file. Verified by the link-integrity check in
  [Verification](#verification).
- **SQL examples**: every SQL block in these docs runs cleanly against
  `data/raw_emails.db` as of 2026-05-05. Re-run them at any time to
  confirm they still match current state.
- **Real samples over abstract schemas**: where possible, examples in
  these docs are pulled from the live DB and anonymized only where needed.
  This is intentional — schemas describe what *should* exist; samples
  describe what *does*.

## Where to start

- **First time on the project**: root [README.md](../README.md) →
  [oauth-setup.md](./oauth-setup.md) → [ARCHITECTURE.md](./ARCHITECTURE.md).
- **About to write a query**: [SCHEMA.md](./SCHEMA.md) →
  [EXTRACTION-OUTPUT.md](./EXTRACTION-OUTPUT.md) for `parsed_json` shapes.
- **Operating the pipeline**: [OPERATIONS.md](./OPERATIONS.md) is the
  runbook.
- **Adding a newsletter or changing a prompt**:
  [CONFIGURATION.md](./CONFIGURATION.md).
- **Planning what's next**: [ROADMAP.md](./ROADMAP.md).

## Verification

These docs were verified against the live codebase and database on
2026-05-05. To re-verify after changes:

```bash
# 1. Schema doc still matches the actual DB schema
sqlite3 data/raw_emails.db ".schema" > /tmp/actual.sql
diff <(grep -E '^(CREATE|raw_emails|extractions|gmail_message_id)' docs/SCHEMA.md) /tmp/actual.sql

# 2. SQL examples in OPERATIONS.md and SCHEMA.md still execute
grep -A 20 '```sql' docs/OPERATIONS.md docs/SCHEMA.md | \
    sqlite3 data/raw_emails.db
# (Manual review — non-trivial to extract just the SQL fences cleanly.)

# 3. File-path links still resolve
grep -hoE '\.\./politico_playbook/[a-zA-Z_/]+\.py' docs/*.md | sort -u | \
    while read p; do test -e "${p#../}" || echo "MISSING: $p"; done
```

## Versioning

These docs target **v0.2** of the pipeline. The v0.1 POC is preserved at
git tag `v0.1-poc-single-source` but is not documented here. To recover any
v0.1 file: `git checkout v0.1-poc-single-source -- <path>`.
