# Configuration Reference

Three YAML files in
[`politico_playbook/config/`](../politico_playbook/config/) drive the
pipeline's behavior. Together they answer "which newsletters do we ingest,"
"how do we slice each newsletter into sections," and "what should the LLM
extract from each section type." The Python code is intentionally generic —
adding a newsletter or remapping a header is a YAML edit, not a code change.

| File                                                                       | Loaded by                                                                                          | Decides |
|----------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|---------|
| [`newsletters.yaml`](../politico_playbook/config/newsletters.yaml)         | [`NewsletterRegistry`](../politico_playbook/ingestion/newsletter_registry.py)                       | Which senders are in scope; which parser handles each |
| [`section_taxonomy.yaml`](../politico_playbook/config/section_taxonomy.yaml) | [`SectionTaxonomy`](../politico_playbook/ingestion/parser_base.py)                                  | Which section headers exist; how they map to semantic types |
| [`extraction_prompts.yaml`](../politico_playbook/config/extraction_prompts.yaml) | [`PromptRegistry`](../politico_playbook/processing/section_extractor.py)                            | Which prompt + JSON schema to use per section type |

## Lookup precedence (most specific wins)

When the parser hits a header in a newsletter body, it resolves the header to
a `(section_type, skip_extraction)` pair using a four-step ladder, defined in
[`SectionTaxonomy.lookup`](../politico_playbook/ingestion/parser_base.py):

```
1. by_newsletter[<slug>][<header>]   — per-newsletter override
2. shared[<header>]                  — cross-newsletter common label
3. skip_headers                      — recognized but `ignore`-typed
4. (no match) → 'unclassified'       — falls through to generic prompt
```

Header matching is case- and trailing-colon-insensitive
([`_normalize`](../politico_playbook/ingestion/parser_base.py)): `TRANSITIONS`,
`Transitions:`, and `transitions` all match the same key.

## `newsletters.yaml` — sender registry

A flat dict of `slug → { display_name, parser, priority, active, notes? }`,
plus a top-level `allowed_domains` list.

The slug is the unique key. By convention, it's the local-part of the
sender's email address — `politicoplaybook@email.politico.com` →
`politicoplaybook`. Two exceptions:

- **politicopro.com**: a single sender (`newsletter@email.politicopro.com`)
  fans out to many sub-newsletters by subject. It maps to the synthetic slug
  `newsletter_politicopro` and uses the `pro_multi_vertical` parser. See
  [`NewsletterRegistry.slug_from_sender`](../politico_playbook/ingestion/newsletter_registry.py).
- **AM/PM editions**: when the same sender publishes twice a day with the
  same address (e.g., Playbook AM and PM both come from
  `politicoplaybook@email.politico.com`), they share the slug and are
  disambiguated downstream by subject or received time.

### Field reference

| Field          | Type     | Required | Default | Notes |
|----------------|----------|:--------:|---------|-------|
| `display_name` | string   | no       | slug    | Used in `inventory` reports. |
| `parser`       | string   | no       | `default` | Parser identifier. Currently `default` or `pro_multi_vertical`; see [parser registry](../politico_playbook/ingestion/parser_base.py). |
| `priority`     | int 1–5  | no       | 3       | Hint for budget throttling — 1 is highest. Not currently consumed by the runner; reserved. |
| `active`       | bool     | no       | true    | If false, slug stays in registry but ingestion skips it (and stage 2 won't see it because it never lands in `raw_emails`). |
| `notes`        | string   | no       | ""      | Free-form. |

### Top-level `allowed_domains`

The Gmail query is built as `from:<domain1> OR from:<domain2> ...` over this
list. Anything outside it is filtered server-side. Currently:

```yaml
allowed_domains:
  - email.politico.com
  - email.politicopro.com
```

### Worked example: adding a 28th newsletter

Suppose Politico launches "POLITICO Energy Daily" from
`energydaily@email.politico.com`. Add this entry:

```yaml
newsletters:
  energydaily:
    display_name: "POLITICO Energy Daily"
    parser: default
    priority: 2
    active: true
    notes: "Launched 2026-06; verify sender on first run."
```

Run `python -m politico_playbook.ingestion.runner backfill --newsletter energydaily`
to test before turning it loose on the broader fetch. No code change.

If the sender uses an unfamiliar domain (e.g., `email.politicoenergy.com`),
also add it under `allowed_domains` — otherwise the Gmail query won't catch
it and the registry's `is_allowed_domain()` check will reject the message.

## `section_taxonomy.yaml` — header → type map

Three top-level sections plus a `types:` block defining what each semantic
type means.

```yaml
types:           # Definitions of section_type values (description, priority, focus hints)
  personnel_change: { ... }
  social_graph:     { ... }
  ...

shared:          # Cross-newsletter header → type mappings
  TRANSITIONS:                       personnel_change
  HAPPY BIRTHDAY:                    social_graph
  ...

by_newsletter:   # Per-newsletter overrides (newsletter slug → header → type)
  newyorkplaybook:
    MIDTERMOIL:                      campaign_news
  weeklyscore:
    REDISTRICTING ROUNDUP:           campaign_news
    CODA:                            ignore

skip_headers:    # Recognized as section breaks but typed `ignore` (skip_extraction)
  - "Did someone forward this email to you? Sign up here."
  - "TODAY'S TIP"
  ...
```

### `types` block

Defines the universe of `section_type` values. Each type has:

- `description`: human-readable purpose.
- `priority`: `high | medium | low | none` — informational; not currently
  enforced.
- `extraction_focus`: list of fields the LLM should hunt for (mirrors the
  prompt's intent, not enforced).
- `skip_extraction`: optional bool. When `true`, the section is recognized
  as a break but never sent to the LLM (saves tokens). Currently set on
  `links_only` and `ignore`.

### When to use `shared` vs `by_newsletter`

- **`shared`**: the same header carries the same meaning everywhere it
  appears. `TRANSITIONS` and `HAPPY BIRTHDAY` are universally personnel and
  social, so they live here.
- **`by_newsletter`**: a header that only one newsletter uses
  (`MIDTERMOIL`), or one whose meaning differs by publication
  (`Beat Memo` is a `lead_story` in Politico Pro but could be a brief
  elsewhere — override per newsletter).

### Adding a header

1. Spot the header in a real newsletter body. The parser is line-based: the
   header must appear on its own line, surrounded by whitespace.
2. Decide the semantic type. If none of the existing nine fit, add a new
   `types:` entry first, then a corresponding entry in
   `extraction_prompts.yaml`.
3. Add the mapping under `shared:` (universal) or
   `by_newsletter[<slug>]:` (newsletter-specific). Per-newsletter wins on
   conflict.

## `extraction_prompts.yaml` — section_type → prompt + schema

One entry per `section_type`. Each entry has:

- `system`: cached system prompt. Establishes the LLM's role and constraints.
- `user_template`: f-string-style template. Available placeholders:
  `{section_body}`, `{section_header}`, `{section_type}`,
  `{newsletter_slug}`, `{received_date}` (formatted as `YYYY-MM-DD`).
- `json_schema`: a JSON Schema object passed to OpenRouter as
  `response_format.json_schema.schema` with `strict: true`. Stage 2 expects
  the LLM's response to match this exactly.

### `inherit:` — schema reuse

A type can reuse another's prompt with `inherit: <other_type>`:

```yaml
news_brief:
  inherit: unclassified
state_news:
  inherit: unclassified
financial:
  inherit: unclassified
```

The inheriting type takes the parent's `system`, `user_template`, and
`json_schema` unless explicitly overridden. Cycles are caught at load time
([`PromptRegistry._resolve`](../politico_playbook/processing/section_extractor.py)).

### Fallback for unknown types

If a section's resolved type is not a key in this file (most commonly
`unclassified`), the registry falls back to the `unclassified` entry. The
default `unclassified` schema returns `{entities: [...], actions: [...]}`
— a minimal generic shape.

### Modifying an existing prompt

The `extractions` UNIQUE constraint is on `(message_id, section_index, model_id)`
— *not* on the prompt content. If you tighten a prompt and re-run `extract`,
the new output will overwrite the old row for the same model. To keep both
versions for comparison, change `MODEL_ID` between runs (or add a prompt
version field — currently not in the schema; tracked in
[ROADMAP.md](./ROADMAP.md)).

## How the three files compose at runtime

```
Gmail message
  │
  ▼
NewsletterRegistry.slug_from_sender    ← newsletters.yaml (allowed_domains, slug)
  │
  ▼
NewsletterRegistry.get(slug)           ← newsletters.yaml (parser id, active)
  │
  ▼
get_parser(parser_id).parse(body)      ← parser_base.py: walks lines
  │
  │   For each candidate header line:
  │   ├─ SectionTaxonomy.is_known_header?    ← section_taxonomy.yaml
  │   └─ SectionTaxonomy.lookup(header, slug) → (section_type, skip)
  │                                              ← section_taxonomy.yaml
  ▼
For each non-skipped section:
  PromptRegistry.for_section_type(section_type)  ← extraction_prompts.yaml
  │
  ▼
OpenRouterClient.complete(system, user, json_schema)
  │
  ▼
INSERT OR REPLACE into extractions
```

For a worked example of what the LLM produces for each section type, see
[EXTRACTION-OUTPUT.md](./EXTRACTION-OUTPUT.md).
