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

## Web-facing target — five candidate architectures

Spanning the spectrum from no-database to NoSQL, evaluated against the "thin layer between data and presentation" constraint and the Places-first demo. Listed cheapest-to-heaviest in infrastructure terms.

### 1. No database — pure structured-file bundle

Export the star schema as a versioned bundle of Parquet (or JSON / CSV) files. Web app loads them directly; in-browser SQL via **DuckDB-WASM** turns the bundle into a queryable star schema without any server.

- **Pros:** zero ops, zero hosting cost, fully static deploy (GitHub Pages / Netlify); the data layer *is* the artifact, reproducible by commit hash; survives long-term archival trivially.
- **Cons:** no write path, no per-user state, no auth beyond static hosting; full dataset shipped client-side (fine at 2.5k Places + 10k Persons, less so as facts grow).
- **Fit for Places demo:** very good — small enough to fit comfortably in DuckDB-WASM; pivot-style queries (filter dimensions, aggregate facts) are exactly DuckDB's strength.

### 2. Single-file embedded database (SQLite / DuckDB)

Same shape as #1 but the file is an actual database. Server-side: a tiny Python / Node API serves `SELECT` statements. Or client-side via `sql.js` / DuckDB-WASM, identically to option 1.

- **Pros:** still essentially file-based — one artifact, one commit-hash version; minimal API surface (literally "execute this SQL"); easiest path to honour the "thin layer" rule because there is barely a layer.
- **Cons:** single-writer (irrelevant for read-only repo data, relevant if mock-up later wants annotation/comments); no concurrent transactional writes; backup story is "copy the file".
- **Fit for Places demo:** excellent — SQLite/DuckDB queries map directly to Power Pivot DAX expressions; quickest port from MVP.

### 3. PostgreSQL — classic relational star schema

Dimensions and facts as normalised tables with explicit FKs and indexes. A thin REST or GraphQL endpoint exposes either parameterised queries or a tiny query-builder over a fixed set of dimensions/facts.

- **Pros:** mature ecosystem, strong consistency, expressive SQL (window functions, CTEs, geo via PostGIS — relevant for Places); standard hosting; clean migration path from SQLite if the project outgrows option 2.
- **Cons:** real infrastructure to run, monitor, back up; schema migrations become a process; the "thin layer" rule is hardest to keep here because Postgres invites ORMs and service layers.
- **Fit for Places demo:** strong long-term, slightly heavy for a *mockup* whose lifetime is October.

### 4. PostgreSQL with JSONB — hybrid relational + document

Relational core for dimensions and facts (Calendar, Diary, Place IDs, fact rows), but heterogeneous attributes — variable Person/Place/Work properties, Sørens overlays, source-specific metadata — live in `JSONB` columns. SQL joins still work; document-shaped fields stay flexible.

- **Pros:** best fit for the WEMI/sub-type heterogeneity already documented (Works' Literary/Musical/Visual subtypes have very different field sets); GIN indexes on JSONB keep ad-hoc queries fast; lets the schema evolve without DDL churn during the still-stabilising modelling phase.
- **Cons:** two query idioms in one engine (relational + JSON path expressions) — easy to misuse; query plans on JSONB need attention; tooling/ORM support for JSONB is weaker than for plain columns.
- **Fit for Places demo:** good — Places themselves are well-typed, but Sørens-Sted overlay attributes and per-place source notes are exactly the kind of variable bag JSONB handles cleanly.

### 5. Dedicated document or graph store (Mongo / Neo4j)

Fully NoSQL. Either a document store (MongoDB / Elasticsearch) optimised for faceted browse and full-text search, or a property graph (Neo4j) that makes the Work↔Place / Person↔Place / Person↔Work edges first-class — matching the project's eventual "graph layer" trajectory.

- **Pros:** Mongo/ES — best-in-class search/facets UX; Neo4j — relationships *are* the query primitive, ideal for the M-M edges the star schema currently models awkwardly; visually compelling for demos (graph viz, search-as-you-type).
- **Cons:** two databases to keep in sync if used alongside the relational warehouse; star-schema aggregations are not the native idiom for either; bigger conceptual jump for collaborators used to spreadsheets / SQL.
- **Fit for Places demo:** Neo4j makes the Place↔Work edge demo-spectacular but locks in a paradigm shift before the relational MVP has fully proven itself; Mongo/ES adds search polish that isn't strictly required for the October mockup.

### Recommendation framing (not yet decided)

Given **October = mockup only** and the **thin-layer** constraint, options 1 or 2 are the most honest match for the milestone — the data layer is the artifact and the presentation layer sits right on top of it. Option 4 (Postgres + JSONB) is the natural next step if the mockup graduates into a longer-lived tool, because it can absorb the WEMI heterogeneity without flattening it. Option 5 (graph) belongs to the post-mockup trajectory hinted at in the original CSV → star → graph plan.

## October milestone — mockup only

This repo's October deliverable is a **mockup**, not a deployed service or production data layer. That means:

- The Excel MVP + Power Pivot model continues as the **analysis surface**.
- The web-facing artifact is a **clickable mockup** of the Places-centred demo queries — wireframes, prototype pages, or a thin static site driven by exported data — sufficient to make the architectural choice (one of the five above) visible to stakeholders.
- No requirement for live API, authentication, hosting infrastructure, or persistence beyond what the mockup needs to render.

Picking between the five web-target candidates is therefore **not blocking the October milestone**; the mockup can be built directly on top of an exported data bundle (option 1) and remain compatible with any of the five long-term choices.

## Open questions

Resolutions from the planning conversation on 2026-06-02:

- **MVP location** — settled: the MVP lives in `raw/` as the highest-versioned `HCA-Repository V*.xlsx`. Power Query and Power Pivot are embedded in the workbook itself.
- **Demo entity** — settled: Places (`STED-REGISTER`). 3–5 demo queries to be drafted next.
- **October milestone** — settled: mockup only (see above).
- **Web-facing target** — five candidate architectures laid out above; choice deferred and not blocking October.

Still open:

1. **Sørens registers** (Artist, Sted, Almanak): location and ownership pending clarification with Søren. Treat the Power Query joins as placeholders until the files arrive or a reference path is agreed.
2. **Web-facing target — final pick** among the five candidates above. Likely deferred until the Places demo has surfaced concrete query patterns.
3. **3–5 demo queries for Places:** to be drafted — e.g. "places visited on travel days", "works mentioned per visited place", "place-Andersen co-occurrence map by year".
