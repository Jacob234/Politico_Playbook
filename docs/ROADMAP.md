# Roadmap

Forward-looking work, replacing the "Priority Tasks" section that lived in
[CLAUDE.md](../CLAUDE.md). This is the source of truth for what's next; the
order is a current best guess and will shift as the data shape evolves.

Status legend: ✅ shipped · ⏳ designed, not built · 🚧 not yet designed

## Stage 3: Entity normalization (port)

**Status**: ⏳ designed (legacy file-based code exists at
[`processing/database_normalizer.py`](../politico_playbook/processing/database_normalizer.py)).

The current Stage 3 reads JSON files from `data/structured/` (a v0.1
artifact path) and emits `NormalizedPerson`, `NormalizedRelationship`, and
`NormalizedOrganization` dataclasses with deduplication, alias resolution,
and temporal context. It does not run as part of the v0.2 pipeline.

### Target design

Read from `extractions` (SQLite); write to new SQLite tables in the same
`raw_emails.db` so everything is join-reachable.

Sketch:

```sql
CREATE TABLE entities (
    entity_id          TEXT PRIMARY KEY,        -- deterministic hash of canonical_name + entity_type
    entity_type        TEXT NOT NULL,           -- person | organization | location | event | policy_topic
    canonical_name     TEXT NOT NULL,
    aliases            TEXT,                    -- JSON array of name variants
    first_seen_at      TIMESTAMP NOT NULL,
    last_seen_at       TIMESTAMP NOT NULL,
    mention_count      INTEGER NOT NULL DEFAULT 0,
    attributes         TEXT                     -- JSON: party, state, role, etc.
);

CREATE TABLE relationships (
    relationship_id    TEXT PRIMARY KEY,
    subject_id         TEXT NOT NULL REFERENCES entities(entity_id),
    predicate          TEXT NOT NULL,           -- 'works_for', 'endorsed_by', 'attended', etc.
    object_id          TEXT NOT NULL REFERENCES entities(entity_id),
    first_observed_at  TIMESTAMP NOT NULL,
    last_observed_at   TIMESTAMP NOT NULL,
    observation_count  INTEGER NOT NULL DEFAULT 0,
    confidence         REAL,                    -- 0.0–1.0 average across observations
    UNIQUE (subject_id, predicate, object_id)
);

CREATE TABLE entity_observations (
    observation_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id          TEXT NOT NULL REFERENCES entities(entity_id),
    extraction_id      INTEGER NOT NULL REFERENCES extractions(id),
    role_at_mention    TEXT,
    raw_name           TEXT NOT NULL            -- name as it appeared in the source
);
```

### Build steps

1. Read every `extractions` row with `extraction_status='ok'` and `parsed_json`
   not null.
2. Per `section_type`, walk the schema-known paths
   (`personnel_changes[].person_name`, `people[].name`, `entities[].name`,
   `candidates[].name`, …) to gather raw entity mentions.
3. Canonicalize names (strip honorifics, normalize unicode, collapse
   `Sen. Coons` → `Chris Coons`). Use a deterministic hash of canonical
   name + type as `entity_id` so re-runs produce stable IDs.
4. Upsert into `entities`. Bump `mention_count`, update `last_seen_at`,
   accumulate aliases.
5. For each `actions[]`/`endorsements[]`/`personnel_changes[]` row, derive
   `(subject, predicate, object)` triples and upsert into `relationships`.
6. Append a row to `entity_observations` for traceability — every entity
   should be back-traceable to the section it came from.

### Idempotency

Like Stage 2: the upsert keys on `entity_id` (deterministic from name+type)
and `(subject_id, predicate, object_id)` for relationships. Re-running
Stage 3 against the same extractions should produce zero diffs.

### Estimated effort

~2 days for first pass. The legacy code in `database_normalizer.py` already
has the shape of the dataclasses and the dedup heuristics; this is a port,
not a new design. The hard part is name canonicalization — the existing
samples already show variants like "Sen. Chris Coons", "Chris Coons", and
"Coons" in close proximity.

## Stage 4: Graph + temporal analytics (port)

**Status**: ⏳ designed (legacy file-based code at
[`processing/temporal_analyzer.py`](../politico_playbook/processing/temporal_analyzer.py)).

Consumes Stage 3's normalized entities and relationships to build a
political-network graph and time-series analytics. Legacy code uses
`networkx` for graph construction and pandas for time series; both are
already in `requirements.txt`.

### Target design

Read from `entities` and `relationships` (Stage 3 tables). Two output
shapes:

- **Graph snapshots**: persisted to a new `graph_snapshots` table or to
  on-disk JSON / GraphML for offline analysis (avoid pickle-based formats —
  the snapshots may be checked into the repo or shared, and pickle
  deserialization is a code-execution risk). Each snapshot represents the
  state at a point in time, supporting "show me the network as of date X."
- **Trend events**: persisted to a new `political_trends` table — rising
  influence, new relationships forming, declining activity, etc. Computed
  by sliding-window analysis over `entity_observations`.

The legacy `temporal_analyzer.py` already defines `GraphNode`, `GraphEdge`,
`TimeSeriesPoint`, and `PoliticalTrend` dataclasses with the right shape;
the port is wiring them to the new persistence layer.

### Estimated effort

~2 days after Stage 3 is in place. Hard dependency on Stage 3.

## Politico Pro multi-vertical sender dispatcher

**Status**: 🚧 stub exists (`ProMultiVerticalParser` in
[`parser_base.py:199`](../politico_playbook/ingestion/parser_base.py)).

The `newsletter@email.politicopro.com` sender represents many sub-newsletters
(NY Health Care, NY/NJ Energy, …) disambiguated by subject pattern. The
current parser inherits from `DefaultParser` without overriding anything —
it will work, but every Pro newsletter ends up under a single
`newsletter_politicopro` slug.

### Build

1. Sample Pro subjects after first ingest (`SELECT subject FROM raw_emails
   WHERE newsletter_slug='newsletter_politicopro'`).
2. Identify the subject-line pattern that distinguishes verticals — likely
   a leading `[NY Health Care]` or `New York Health Care:` style prefix.
3. Override `_split_into_sections` (or earlier — at the parser entry point)
   to set a finer-grained `newsletter_slug` like
   `pro_ny_health_care` so per-newsletter section overrides apply.
4. Add the synthetic sub-slugs to `newsletters.yaml` so the registry knows
   about them.

### Estimated effort

~½ day, blocked on having Pro newsletters in the DB to inspect. Today the
DB has zero Pro messages.

## Fuzzy section-header matching

**Status**: 🚧 not designed.

Today, [`SectionTaxonomy.lookup`](../politico_playbook/ingestion/parser_base.py)
matches headers exactly (after case + colon normalization). Politico's
formatting drifts over a 15-month backfill window — `TRANSITIONS` becomes
`TRANSITIONS:` becomes `Transitions →` becomes a new label entirely. Every
unmatched header silently gets `unclassified` and goes through the generic
prompt.

### Build

1. Add a `SELECT section_header, COUNT(*) FROM extractions WHERE section_type='unclassified' GROUP BY 1` report to the `inventory` mode.
2. For high-frequency unclassified headers, decide whether they're new
   sections to add to the taxonomy, or noise to ignore.
3. Optional: add fuzzy matching (Levenshtein distance ≤ 2) as a fallback
   between `shared` lookup and `unclassified` fallback — but only if the
   manual-review report shows it'd actually help.

### Estimated effort

~1 day. Lower priority until we've ingested several months across multiple
newsletters and can see the actual drift pattern.

## Test suite buildout

**Status**: 🚧 stub.
[`politico_playbook/tests/`](../politico_playbook/tests/) contains only an
empty `__init__.py` — the v0.1 tests were removed in commit `f24a2ef`
because they no longer matched the v0.2 surface.

### Highest-leverage tests to add

| Module                                                 | Test type    | Why first |
|--------------------------------------------------------|--------------|-----------|
| `ingestion/parser_base.py` (taxonomy lookup)           | unit         | Pure function, easy fixtures, behavior change here breaks downstream silently. |
| `ingestion/raw_store.py` (idempotent upsert)           | unit + sqlite | Idempotency is load-bearing; a regression would create duplicates. |
| `processing/section_extractor.py` (PromptRegistry)     | unit         | `inherit:` resolution has cycle detection that's untested. |
| Full pipeline integration                              | integration  | Stub Gmail + stub OpenRouter, real SQLite, golden fixtures of newsletter bodies. |

Use `pytest`. Place fixtures of real newsletter plaintext (anonymized if
needed) under `tests/fixtures/`.

### Estimated effort

~1–2 days for the first round (the four cells in the table). Ongoing as
new modules are added.

## Visualization

**Status**: 🚧 not designed.

Mentioned in CLAUDE.md as a future stage. Hangs off Stage 4. Likely shape:

- **Network graph**: `streamlit` or `plotly`-based interactive page over
  the `graph_snapshots` table.
- **Timeline view**: per-entity activity timeline; small-multiples for
  comparing entities.
- **Search**: typeahead over `entities.canonical_name` + `aliases`.

### Estimated effort

Speculative — at least a week. Don't start until Stages 3 and 4 produce
something graphable.

## Schema / config evolution

Smaller items, low priority but worth tracking:

- **Prompt versioning**: today, re-running `extract` with the same
  `MODEL_ID` overwrites the prior row even if the prompt changed. Add a
  `prompt_hash` column to `extractions` and include it in the UNIQUE
  constraint, so prompt changes also produce new rows for A/B comparison.
  (Effort: ~½ day.)
- **`finish_reason` storage**: the OpenRouter response includes
  `finish_reason` (`length`, `stop`, `tool_calls`, etc.); we throw it away.
  Adding it to `extractions` would make truncation-based parse_failed
  cases trivially diagnosable. (Effort: ~½ hour.)
- **Active-newsletter cron coverage check**: a periodic query that flags
  newsletters in `newsletters.yaml` with `active: true` that haven't
  ingested anything in N days — catches both Politico's renamed senders
  and our own subscription lapses. (Effort: ~½ day.)

## Dependency graph

```
Stage 3 port  ──────────────────────┐
                                     │
                                     ▼
Stage 4 port  ───────────────────► Stage 4 needs Stage 3's tables
                                     │
                                     ▼
Visualization ─────────────────────► Visualization needs Stage 4 outputs

Pro dispatcher    ── independent ──► (blocked on having Pro data ingested)
Fuzzy header match ── independent ─► (de-prioritized until drift is visible)
Test suite        ── independent ──► (do alongside any of the above)
Prompt versioning ── independent ──► (small; do whenever prompts change next)
```

The critical path to a working political-intelligence graph is Stage 3 →
Stage 4. Everything else is parallelizable or deferrable.
