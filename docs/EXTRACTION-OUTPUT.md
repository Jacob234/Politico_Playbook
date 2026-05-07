# Stage 2 Extraction Output Reference

Each row in the `extractions` table holds an LLM's structured output for one
section of one email under one model. This document specifies the JSON shape
of `parsed_json` per `section_type`, with annotated samples pulled from
`data/raw_emails.db`.

The schemas are defined in
[`extraction_prompts.yaml`](../politico_playbook/config/extraction_prompts.yaml)
and passed to OpenRouter as `response_format.json_schema` with `strict: true`,
so a successful row's `parsed_json` is guaranteed to validate against the
schema. (Failures land in `parse_failed` instead — see [Failure modes](#failure-modes).)

## Section types and their schemas

Nine `section_type`s are defined; three of them inherit the same schema from
`unclassified`:

| section_type        | Schema source                       | Top-level keys |
|---------------------|-------------------------------------|----------------|
| `personnel_change`  | own                                 | `personnel_changes[]` |
| `social_graph`      | own                                 | `context{}`, `people[]` |
| `lead_story`        | own                                 | `entities[]`, `actions[]`, `quotes[]` |
| `campaign_news`     | own                                 | `candidates[]`, `endorsements[]`, `fundraising[]` |
| `news_brief`        | inherits `unclassified`             | `entities[]`, `actions[]` |
| `state_news`        | inherits `unclassified`             | `entities[]`, `actions[]` |
| `financial`         | inherits `unclassified`             | `entities[]`, `actions[]` |
| `unclassified`      | own                                 | `entities[]`, `actions[]` |
| `links_only`        | (skip_extraction: true — no rows)   | — |
| `ignore`            | (skip_extraction: true — no rows)   | — |

`links_only` and `ignore` are recognized by the parser but never sent to the
LLM, so they will not appear in `extractions`.

## `personnel_change`

```jsonc
{
  "personnel_changes": [
    {
      "person_name":         "string",                 // required
      "prior_role":          "string | null",
      "prior_organization":  "string | null",
      "new_role":            "string | null",
      "new_organization":    "string | null",
      "effective_date":      "string | null",          // free-form date as written
      "notes":               "string | null"
    }
  ]
}
```

The schema's only required field is `person_name`; the rest are nullable to
accommodate "X is leaving Y" or "Z has joined W" phrasings where only one
side of the move is given.

> No `personnel_change` rows in the live DB yet — every ingested email so far
> happens to have come from `politicoplaybook` on dates without a TRANSITIONS
> section. Schema is defined and prompt is wired; it'll populate the moment
> a Playbook with a TRANSITIONS block lands.

## `social_graph`

```jsonc
{
  "context": {
    "type":              "event_attendance | birthday | transition_callout | other",
    "event_name":        "string | null",
    "host_or_organizer": "string | null",
    "location":          "string | null",
    "date":              "string | null"
  },
  "people": [
    {
      "name":         "string",                       // required
      "affiliation":  "string | null"                 // role, org, or freeform
    }
  ]
}
```

### Real sample (extraction id = 10, "TALK OF THE TOWN", `qwen/qwen3-next-80b-a3b-instruct:free`)

`people` had 25 entries; six are shown:

```json
{
  "context": {
    "type": "event_attendance",
    "event_name": "GRAMMYs On The Hill Awards",
    "host_or_organizer": "The Recording Academy",
    "date": "last night (relative to newsletter publication)"
  },
  "people": [
    {"name": "Sen. Chris Coons",          "affiliation": "honoree (D-Del.)"},
    {"name": "Rep. María Elvira Salazar", "affiliation": "honoree (R-Fla.)"},
    {"name": "Cordae",                    "affiliation": "performer (GRAMMY-winning/nominated artist)"},
    {"name": "Patrick Leahy",             "affiliation": "spotted attendee"},
    {"name": "Sen. John Hickenlooper",    "affiliation": "spotted attendee (D-Colo.)"},
    {"name": "Nancy Pelosi",              "affiliation": "spotted attendee (D-Calif.)"}
  ]
}
```

Notes from this real sample:
- The model converted `last night` into the `date` field as a relative
  description rather than resolving to an ISO date. Don't rely on `date`
  being machine-parseable; the `received_at` column on the parent
  `raw_emails` row is the anchor.
- `affiliation` carries both role labels (`honoree`) and party/state
  modifiers (`(D-Del.)`). Downstream Stage 3 will need to parse these.

## `lead_story`

```jsonc
{
  "entities": [
    {
      "name":                  "string",
      "entity_type":           "person | organization | location | event | policy_topic",
      "role":                  "string | null",
      "party":                 "string | null",
      "state_or_jurisdiction": "string | null"
    }
  ],
  "actions": [
    {
      "actor":   "string",
      "action":  "string",
      "target":  "string | null",
      "summary": "string"
    }
  ],
  "quotes": [
    {
      "speaker": "string",
      "quote":   "string",
      "context": "string | null"
    }
  ]
}
```

### Real sample (extraction id = 39, "DRIVING THE DAY", `deepseek/deepseek-v4-flash`)

```json
{
  "entities": [
    {"name": "Pete Hegseth",     "entity_type": "person", "role": "Defense Secretary"},
    {"name": "Dan \"Razin\" Caine", "entity_type": "person", "role": "Joint Chiefs of Staff Chair"},
    {"name": "Thom Tillis",      "entity_type": "person", "role": "Senator (R-N.C.)"},
    {"name": "Jerome Powell",    "entity_type": "person", "role": "Federal Reserve Chair"},
    {"name": "Kevin Warsh",      "entity_type": "person", "role": "Potential Fed rate-setter"}
  ],
  "actions": [
    {
      "actor": "Pete Hegseth",
      "action": "grilled by Senate Armed Services Committee",
      "target": "Senate Armed Services Committee",
      "summary": "Hegseth and Gen. Caine face questioning from committee members."
    },
    {
      "actor": "Thom Tillis",
      "action": "ended feud with White House over Jerome Powell probe",
      "target": "White House",
      "summary": "Tillis says he is serious about blocking any Jan. 6 apologist from advancing as AG nominee."
    },
    {
      "actor": "Jerome Powell",
      "action": "said he will stay at Fed until investigation into Fed HQ renovations is over",
      "target": "Federal Reserve",
      "summary": "Powell's decision may cause headaches for Kevin Warsh if he seeks to slash rates."
    }
  ]
}
```

The `quotes` array can be empty even when the section contains quoted
material — the model is conservative about attribution. If you need
better recall, tighten the prompt's quote instruction in
`extraction_prompts.yaml`.

## `campaign_news`

```jsonc
{
  "candidates": [
    {
      "name":              "string",
      "office_sought":     "string | null",
      "district_or_state": "string | null",
      "party":             "string | null"
    }
  ],
  "endorsements": [
    {
      "endorser": "string",
      "endorsee": "string",
      "race":     "string | null"
    }
  ],
  "fundraising": [
    {
      "entity":     "string",
      "amount_usd": "number | null",
      "period":     "string | null"
    }
  ]
}
```

> No `campaign_news` rows in the live DB yet (`politicoplaybook` is the
> general flagship; campaign-heavy sections cluster in `weeklyscore`,
> `newyorkplaybook`, `californiaplaybook`).

## `news_brief` / `state_news` / `financial` (inherits `unclassified`)

```jsonc
{
  "entities": [
    {
      "name":         "string",
      "entity_type":  "person | organization | location | event",
      "role":         "string | null",
      "organization": "string | null"
    }
  ],
  "actions": [
    {
      "actor":   "string",
      "action":  "string",
      "target":  "string | null",
      "summary": "string"
    }
  ]
}
```

Note this is a *narrower* `entity_type` enum than `lead_story`'s — no
`policy_topic`, no `party`, no `state_or_jurisdiction`. If you find yourself
wanting those fields for `news_brief`, give it its own schema in
`extraction_prompts.yaml` instead of inheriting.

### Real sample (extraction id = 53, "THE FRONT PAGE", `deepseek/deepseek-v4-flash`)

```json
{
  "entities": [
    {"name": "John Fetterman",    "entity_type": "person", "role": "Senator", "organization": "U.S. Senate"},
    {"name": "Dave McCormick",    "entity_type": "person", "role": "Senator", "organization": "U.S. Senate"},
    {"name": "Jonathan Martin",   "entity_type": "person", "role": "Journalist", "organization": "POLITICO"},
    {"name": "Jackie Speier",     "entity_type": "person", "role": "Former Representative", "organization": "U.S. House of Representatives"}
  ],
  "actions": [
    {
      "actor": "Republican Party",
      "action": "courting",
      "target": "John Fetterman",
      "summary": "Republicans are privately trying to court Senator John Fetterman to either switch parties or become an independent."
    },
    {
      "actor": "House Democrats",
      "action": "developing messaging plan",
      "target": "AI policy",
      "summary": "House Democrats are crafting a midterms messaging plan around AI that emphasizes avoiding higher costs for data centers while winning the global AI competition."
    }
  ]
}
```

A familiar-looking flaw: "Republican Party" is recorded as an `actor` in the
`actions` array but never declared in `entities`. Stage 3 normalization
should not assume one-to-one alignment between `actions[].actor` and
`entities[].name`.

## Failure modes

When `extraction_status != 'ok'`, `parsed_json` is NULL and `raw_response`
holds debug info.

### `parse_failed`

The API call succeeded, the model returned content, but `json.loads()`
choked. This is the dominant failure mode against the current sample —
`DRIVING THE DAY` (the `lead_story` header) parses 7 / 14 of the time. The
`raw_response` lets you inspect what the model actually emitted.

Real example (`raw_response` from extraction id = 9, truncated):

```text
{
  "entities": [
    { "name": "Virginia",         "entity_type": "location" },
    { "name": "Florida",          "entity_type": "location" },
    { "name": "California",       "entity_type": "location" },
    { "name": "Virginia Supreme Court", "entity_type": "organization" },
    ...
```

In this case the model emitted unicode-curly-quotes and trailing whitespace
that the strict JSON-schema validator rejected. Common parse_failed causes
to look for in `raw_response`:

- Curly/smart quotes instead of ASCII.
- Trailing commas in arrays/objects.
- Markdown code-fence wrappers (` ```json ... ``` ` around the payload).
- Truncated output (`finish_reason = length` — see column not yet stored,
  but visible if you re-run with logging).

See [OPERATIONS.md → Diagnosing parse_failed](./OPERATIONS.md#diagnosing-parse_failed)
for triage SQL.

### `api_failed`

The OpenRouter request raised an exception. `raw_response` is the exception
text, `prompt_tokens` and `completion_tokens` are 0, `model_id` is whatever
was configured at the time (the LLM never ran).

Real example (`raw_response` from extraction id = 5):

```text
Error code: 429 - {'error': {'message': 'Rate limit exceeded:
limit_rpm/qwen/qwen3-next-80b-a3b-instruct-2509/.... High demand for
qwen/qwen3-next-80b-a3b-instruct:free on OpenRouter - limited to 8
requests per minute. Please retry shortly.', ...}}
```

Free-tier model rate limits are the single most common `api_failed` cause.
For production-volume backfill, a paid model is functionally required — see
[OPERATIONS.md → Quota management](./OPERATIONS.md#quota-management).

## Consuming `parsed_json` in SQL

SQLite's JSON1 functions work directly on the `parsed_json` text column.

```sql
-- Pull every person named in a social_graph extraction
SELECT
    e.section_header,
    json_extract(p.value, '$.name')        AS person,
    json_extract(p.value, '$.affiliation') AS affiliation
FROM extractions e,
     json_each(json_extract(e.parsed_json, '$.people')) p
WHERE e.section_type = 'social_graph'
  AND e.extraction_status = 'ok';

-- Find lead_stories where Hegseth appeared as an entity
SELECT gmail_message_id, section_header
FROM extractions e,
     json_each(json_extract(e.parsed_json, '$.entities')) ent
WHERE e.section_type = 'lead_story'
  AND e.extraction_status = 'ok'
  AND json_extract(ent.value, '$.name') LIKE '%Hegseth%';
```

For the Stage 3 normalization design that consumes these shapes, see
[ROADMAP.md → Stage 3 port](./ROADMAP.md#stage-3-entity-normalization-port).
