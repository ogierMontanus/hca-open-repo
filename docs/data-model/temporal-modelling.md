# Temporal modelling — entity dates vs. mention dates

The diary indexes contain two fundamentally different categories of temporal
information, and they must not be conflated. This document defines the
conceptual model and how it shapes filtering, timelines, search, and entity
pages. UI requirements that flow from it are mirrored in
[`ai-context/coding_agent_plan.md`](../../ai-context/coding_agent_plan.md) §11.

## Why this matters

> **Show all persons born between 1800 and 1820.**
> **Show all persons mentioned between 1840 and 1845.**

These are not equivalent queries. A person born in 1780 may be mentioned in
1855; a book published in 1820 may be referenced in 1860. The chronology of
the world being described and the chronology of Andersen's observation and
recording of that world are different research questions, and the system
must answer them independently.

## Two top-level date families

### `entity_dates` — events in the life cycle of the entity itself

Subtype-specific labels are preserved internally; the UI groups them under
one "Entity Dates" concept so a reader is not faced with dozens of
near-identical filters.

| Entity type | Event labels |
|---|---|
| Person | birth · death · (later: education, first publication, …) |
| Book / printed work | publication · reprint · composition |
| Theatre play / opera / ballet | composition · premiere · performance |
| Painting / sculpture / drawing | creation · first exhibition |
| Musical work | composition · first performance |
| Place | foundation · destruction · renaming (sparse, optional) |
| Institution | foundation · closure |

### `mention_dates` — dates derived from the diary material itself

When Andersen referred to the entity in writing.

| Source | Description |
|---|---|
| Diary mention | the entity appears in a dated diary page |
| Almanac mention | the entity appears in an almanac entry (future source) |
| Notebook mention | the entity appears in a notebook (future source) |
| Letter mention | the entity appears in a letter (future source) |

Diary mentions are the only family currently populated, but the schema
treats this as one source under a general `mention_dates` umbrella so the
others can be added without UI rework.

## How this maps to current source data

| Concept | Current column | File | Fill | Notes |
|---|---|---|---|---|
| Person — birth / death | inside `label` (e.g. `(1804–1876)`) | `entities.csv` | ~22% of persons | needs a parser pass to split into a structured `entity_event` table |
| Book — publication / reprint | `year_derived`, `date_derived` | `entities.csv` | 2.9% / 1.4% of all works | already a structured column; surfaced on work pages (Step 4) |
| Theatre — premiere | inside `label` (parenthetical year) | `entities.csv` | partial | same parser pass as books |
| Other entity events | not yet captured | — | 0% | requires a `entity_event` table (see below) |
| Diary mention date | `vol` + `page` + `seq` → `diary.date` / `diary.year` | `references.csv` ⋈ `diary.csv` | 100% | the join already works; the date facet on diaries.html uses it |

## Recommended schema evolution

The current `entities.csv` flattens entity-level dates into denormalised
columns (`year_derived`, `date_derived`). That is enough for the mockup's
first pass but cannot represent the full family — a person has two dates
(birth, death), a book may have many (composition, publication, several
reprints), and labels should be type-aware (premiere ≠ publication).

Introduce a separate `entity_event.csv` (and matching star-schema fact in
the eventual warehouse — see [`star-schema.md`](star-schema.md)):

```
entity_event.csv
  event_id      — surrogate key
  entity_id     — FK → entities.entity_id
  event_type    — birth | death | publication | reprint | composition |
                  premiere | performance | creation | exhibition | …
  date_start    — ISO-8601, day-precision or coarser (1873, 1873-09, 1873-09-04)
  date_end      — same shape; equals date_start for point events
  precision     — day | month | year | decade | century
  source        — short citation / footnote (optional)
```

Mention dates do **not** go in this table. They are already represented by
`references.csv ⋈ diary.csv` (a reference's date = the date of the diary
page it appears on). The query model for "all persons mentioned in 1844"
is a join, not a column on `entities`.

When a new mention source arrives (almanacs, notebooks), it gets its own
sibling join table (`almanac.csv`, `notebook.csv` …) with the same shape as
`diary.csv`. The UI's "Mention Dates" filter unions across them.

### Mapping the existing flat columns

The `year_derived` / `date_derived` columns on `entities.csv` translate into
`entity_event` rows like:

```
entity_id=Reg003545, event_type=composition, date_start=1854-06-20,
                    date_end=1854-06-20, precision=day
entity_id=Reg001445, event_type=publication, date_start=1847-01-01,
                    date_end=1872-12-31, precision=year      # "1847–72"
```

The denormalised columns can stay on `entities.csv` as a convenience cache
during the transition, but the `entity_event` table is the source of truth
once it exists.

## Five rules the rest of the system must follow

1. **Two families, never merged.** Every temporal filter, slider, facet,
   or timeline operates on exactly one of `entity_dates` or `mention_dates`
   at a time. Combined views are explicit overlays, not silent unions.

2. **Default behaviour is explicit.** The active family is always
   visible to the reader. Switching mode changes the URL / state so a
   shared link reproduces the same view.

3. **Entity-type-aware labels.** When `entity_dates` is active, the filter
   labels match the type: persons see "Født / Død", books see "Udgivet /
   Genoptryk", theatre sees "Premiere / Opførelse". One implementation, one
   label vocabulary table.

4. **Preserve subtype detail internally.** Group entity events under one
   "Entity Dates" concept in the primary UI, but keep the typed
   `event_type` in the underlying data so an advanced query (or a future
   visualisation) can still ask "show only premieres."

5. **Mention dates are first-class data.** They are queryable, facetable,
   plottable on a timeline in their own right — not annotations attached
   to an entity event.

## Where this surfaces today

The mockup currently shows the seam without yet honouring the distinction:

- **Work pages (`work.html`)** show `Dateret` / `År` in the sidebar
  (entity date) and a `dagbogsside(r) omtaler …` list (mention dates) in
  the main column. The labels are correct but the two are not selectable
  as filters yet — that comes with the temporal-mode selector.
- **`diaries.html`** has an "Årstal" facet that filters by diary year =
  mention date. It already operates in the right family; it just needs to
  be labelled as such once the dual model is exposed.
- **`persons.html` / `places.html`** have year sliders in the mock that
  are not yet wired. When they are, they default to mention dates (since
  person birth/death lives inside `label` strings for now) and the
  mode-selector lets a reader switch when `entity_event` lands.

See §11 of `ai-context/coding_agent_plan.md` for the UI requirements that
follow from this model.
