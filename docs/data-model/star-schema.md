# Star schema — dimensions, facts, and the Excel MVP

The semantic model documented in [`wemi-and-relations.md`](wemi-and-relations.md) is being reshaped into an explicit **star schema**: a small set of dimension tables (Calendar, Diary, Persons, Places, Works, Sørens auxiliary registers) connected through fact tables centred on references in diary pages and sections. This document describes the target shape, the Excel + Power Query + Power Pivot MVP that is being used to validate it, and how it relates to the entity-centric CSV layer already present in the repo.

## Why a star schema

Several drivers — captured in the 2026-06-01 working meeting:

- **Stability of the spine.** Diary entries, dates, persons, places, and works are the long-lived entities. New questions ("which French novels appear on travel days?") should be answerable without restructuring the dimensions.
- **Heterogeneity belongs in facts.** Relations and combinations (work × person × date × place × diary-page) vary entry by entry. Putting them in fact tables, not in the dimension rows, keeps the dimensions narrow.
- **Demonstrability.** A star schema can be loaded into Power Pivot today and exposed through pivot tables and slicers, giving non-technical colleagues a working interface without waiting for a web frontend.
- **Migration path.** The same schema lifts cleanly into a PostgreSQL warehouse later; the column-oriented derived attributes documented in `wemi-and-relations.md` (JSONB on the Work dimension) survive the transition.

## The dimensions (semantic model v0.82 → v0.91)

| Dimension | Source | Notes |
|---|---|---|
| **Gregorian Calendar (1800)** | `Calendar1800` sheet in `raw/HCA-Repository V*.xlsx` | Daily grain. Anchors all date-bearing facts. ~36,890 rows |
| **Diary Repository** | `Diary` + `DiaryOverview` sheets | One row per diary day; volume, page, date, day-heading |
| **Registry (Vol. 11–12)** | `Registry` sheet, filtered by `RegistryCategory (H1)` | Parent dimension for Work / Person / Place sub-types |
| **Work-Registry (Vol. 12)** | `VÆRK-REGISTER` slice of Registry | Subtype dimension; holds `parsed_fields` JSONB-style derived attributes |
| **Person-Registry (Vol. 11)** | `PERSON-REGISTER` slice of Registry | Subtype dimension |
| **Location-Registry (Vol. 12)** | `STED-REGISTER` slice of Registry | Subtype dimension |
| **Sørens Artist register** | Separate input from S. (see Open question 1) | Auxiliary artist authority |
| **Sørens Sted register** | Separate input from S. | Provides the M-M Work × Place edges |
| **Sørens Almanak** | Separate input from S. | Historical-calendar overlay |

The Registry parent + three sub-type dimensions (Work / Person / Place) is the **subtype pattern** marked on slide 1. Sub-types share the `PKRegistryTitelID` key with their parent so a single Registry row can be reached via any of them.

### Derived attributes (JSONB-style payload on Work)

The heterogeneous fields documented in [`wemi-and-relations.md`](wemi-and-relations.md) (`opus`, `incipit`, `adapted_from`, `ultimate_source`, `creator_note`, …) live on the Work dimension as a derived-attributes payload — a JSON column in the Power Pivot model, a JSONB column in the eventual PostgreSQL star schema. Columns that are searched/filtered universally (`main_title`, `creator`, `post_type`) stay as first-class dimension columns.

## The facts

| Fact table | Grain | Dimensions it connects |
|---|---|---|
| **References-In-Diary-Page** | One row per registry-mention on a diary page | Diary × Registry (Work/Person/Place via the sub-type) × Calendar |
| **References-In-Diary-Section** | One row per registry-mention in a finer section of a page | Same dimensions, finer grain |
| **Diary-Section-Text** | Free-text of each section | Diary; carries text-derived attributes |
| **Diary-Section-Text-Foot-Notes** | Footnote rows | Diary-Section-Text |
| **Date-Derived-From-Page-Diary-Section-Text** | Dates extracted from prose | Calendar × Diary-Section-Text |
| **Place-Derived-From-Diary-Section-Text** | Places extracted from prose | Location-Registry × Diary-Section-Text |
| **Work ↔ Place (Sørens 2. register)** | M-M edges between Work and Place | Work-Registry × Location-Registry |

`RefInDiaryPage` (69,406 rows in the V0.82 workbook) is the canonical primary fact: every analytical question that crosses the dimensions runs through this table or one of its finer-grained siblings.

### Relationship cardinalities (slide 1)

The bulk of relationships are **1-to-M** (one Diary-day → many References; one Registry-row → many References). The notable **M-to-M** is **Work-Registry ↔ Location-Registry**, mediated by *Sørens 2. register*: a single work may be associated with multiple places, and a place may be linked to multiple works. The mediating table is itself a fact-style edge list.

## The MVP — Excel + Power Query + Power Pivot

The slides ("Fætter BR-keyboard" → "Orgel med 7+ keyboards") frame the MVP as **ambitious-but-bounded**: build the full star schema, but inside Excel, before moving any of it onto a web stack.

The MVP workbook lives in [`raw/`](../../raw/) alongside the canonical `HCA-Repository V*.xlsx` — the highest-versioned workbook in that folder *is* the MVP (Power Query queries and Power Pivot model embedded directly inside it). Versioning rule from `scripts/parsers/_common.py:resolve_ground_truth_xlsx()` applies: when a new version lands, the rest of the pipeline picks it up automatically.

| Layer | Tool | Role |
|---|---|---|
| Source | `raw/HCA-Repository V*.xlsx` (canonical workbook, highest version wins) | Single file, multiple sheets |
| ETL | **Power Query** | Loads sheets, cleans, splits the parent Registry into Work/Person/Place sub-types, joins Sørens auxiliary registers |
| Model | **Power Pivot Data Model** | Holds the dimensions, facts, and relationships as a star schema |
| Interaction | **Pivot tables + slicers** | Demo / analysis surface — no web frontend required for the first round |
| Optional | **Copilot / chat over the Power Pivot model** | Lowers the threshold for colleagues; tested as an alternative to a bespoke web UI |

This MVP is **a prototype platform, not the endpoint**. Its purpose is:

1. Validate that the star schema answers real research questions (the planned 3–5 demo queries — see Places focus below).
2. Stress-test relationships against the live data at full scale.
3. Give collaborators a clickable surface for early feedback before any web development cost is sunk.

The MVP layer's outputs (cleaned dimension and fact tables) are intended to migrate one-to-one into the eventual web back-end's database.

## Web-facing target: thin layer between data and presentation

The web-facing model is **not yet locked**. The committed direction is:

> Aim for a very thin layer on top of the data layer and before the presentation layer.

Implication: the API surface should expose the star schema close to its physical shape — minimal new abstractions, minimal server-side query construction. Whether the consumer is SQL, a graph store, or both is deferred; the architectural rule is that whatever layer mediates between data and UI stays small and transparent.

A practical consequence for upcoming web work: assume pivot-style queries (filter on dimensions, aggregate on facts) translate one-for-one into the API. Avoid building heavy ORM / domain layers until the data model itself is stable enough that they wouldn't immediately need to change.

## October demo — Places as the focus entity

The first thoroughly modelled and queryable entity through the demo queries is **Places** (`STED-REGISTER`, 2,508 rows in V0.82, extended by Sørens Sted register and the M-M edge to Works). Persons (10,228 rows) and Works are deferred to later rounds.

Reasons for picking Places first:
- Mid-sized, manageable data scale — bigger than Works' most heterogeneous subsets but smaller than Persons.
- Spatial dimension renders naturally — maps, route overlays, calendar-of-places-visited all sit close to the Calendar1800 + Diary join the star schema already supports.
- The Work ↔ Place M-M relationship (via Sørens 2. register) is the most distinctive structural feature in the model; demonstrating it makes the architectural choice visible to non-technical viewers.
- Lower modelling weight than Works (no FRBR/WEMI complexity, fewer parsing edge cases than the literary registers).

The 3–5 demo queries should be drafted around Places — to be specified in a follow-up session.

## How this relates to the existing CSV layer

`data/normalized/entities.csv`, `data/normalized/diary.csv`, and `data/normalized/references.csv` are the early, hand-shaped form of the same model:

| CSV | Becomes |
|---|---|
| `entities.csv` | The Work / Person / Place sub-type dimensions (with `RegistryCategory` driving the split) |
| `diary.csv` | The Diary dimension |
| `references.csv` | The `References-In-Diary-Page` fact table |

The star schema is therefore **not a replacement** for the CSVs; it is the next iteration of the model they already implement. The migration plan: stabilise the dimensions first (calendar + diary), add the registry sub-types, then layer the facts.

## Principles carried into this layer

From the 2026-06-01 meeting, the rules that govern how this layer evolves:

1. **Data quality before interface.** A weak grounding cannot be rescued by a smart frontend or chatbot. Reference fields (volume, page, date) must be reliable before anything is exposed.
2. **Narrow dimensions, rich facts.** Only the most basic and stable attributes belong in dimension rows; combinations and relations go into facts. Avoid early over-modelling.
3. **Reproducible refresh.** Power Query steps and Power Pivot relationships are scripted and reproducible from the canonical workbook; no manual cell edits.
4. **Versioned model.** The semantic model carries its own version (v0.82 today, v0.91 once the dimensions/facts split is complete). It increments with the workbook.
5. **Bounded enrichment.** External contributions (students, partners) arrive in standardised schemas with controlled vocabularies and merge back into the dimensions without rebuilding them.
6. **Demo-driven scoping.** The next demonstration round picks the entity with the best ratio of demonstration value to modelling weight — likely Persons or Places, not Works.

## Open questions

Resolutions from the planning conversation on 2026-06-02:

- **MVP location** — settled: the MVP lives in `raw/` as the highest-versioned `HCA-Repository V*.xlsx`. Power Query and Power Pivot are embedded in the workbook itself.
- **Demo entity** — settled: Places (`STED-REGISTER`). 3–5 demo queries to be drafted next.
- **Web-facing target** — partial: thin layer between data and presentation, but the exact target (SQL only, graph store, both) is deferred.

Still open:

1. **Sørens registers** (Artist, Sted, Almanak): location and ownership pending clarification with Søren. Treat the Power Query joins as placeholders until the files arrive or a reference path is agreed.
2. **October milestone:** does this repo need a deliverable (mockup, prototype API, documentation page) or is the October demo Excel-based only?
3. **Web-facing target:** SQL-served star schema, derived graph layer, or both? Decision needed once the "thin layer" constraint can be measured against concrete query patterns from the Places demo.
4. **3–5 demo queries for Places:** to be drafted — e.g. "places visited on travel days", "works mentioned per visited place", "place-Andersen co-occurrence map by year".
