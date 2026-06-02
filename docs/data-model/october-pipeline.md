# October mockup — automated CSV + JSON pipeline

A concrete, end-to-end proposal for the October deliverable: an **automated conversion pipeline** that takes the Excel workbook (which embeds the Power Pivot star schema) and produces a deployable static website mockup, with **CSV and JSON as the only data formats**.

This document records the proposal — it is not yet ratified.

## Why CSV + JSON (and nothing else)

Per the constraint "only include SQL/SQLite or other formats if they offer very big gains", the proposal deliberately does **not** introduce SQLite, DuckDB, or Parquet. The reasoning:

| Format | Considered for | Verdict |
|---|---|---|
| **CSV** | Star-schema export from Excel (dimensions + facts) | **Use.** Native Power Query / Power Pivot output. Diff-friendly in git. Re-opens in Excel for collaborators. Already the language of `scripts/normalization/hca_xlsx_to_csv.py`. |
| **JSON** | Web-consumable view artifacts | **Use.** Native to `fetch()`. No parsing dependency. Maps directly to JS data structures. Carries denormalised "view" shapes the UI needs. |
| **SQLite / DuckDB** | Single-file SQL engine in browser | **Skip.** At Places scale (~2.5k rows) a JSON array + `Array.filter` is fast enough; the Power Pivot model already provides the SQL-shaped analysis surface upstream. SQLite would duplicate logic without unlocking new mockup behaviour. |
| **Parquet** | Compact columnar data exchange | **Skip.** Compression / scan-speed advantages are negligible below ~100k rows. Inspectable only via tooling, so collaborators lose the "double-click to read" affordance. |

The door stays open: every intermediate CSV is a clean dimension or fact table, so a future migration to SQLite, Postgres, or Parquet is a `LOAD DATA INFILE` away.

## Pipeline overview

```
┌─────────────────────────────────────────────────────────────┐
│  raw/HCA-Repository V*.xlsx       (canonical source)        │
│  └── Power Query + Power Pivot star schema embedded         │
│  raw/sorens/*.xlsx | *.csv        (optional, when provided) │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
         ┌──────────────────────────────┐
         │ [1] scripts/normalization/   │
         │     hca_xlsx_to_csv.py       │   (exists; extend for star tables)
         │                              │
         │  xlsx → dimension + fact CSV │
         └──────────────────────────────┘
                         │
                         ▼
         ┌──────────────────────────────┐
         │  data/normalized/*.csv       │
         │   dim_place.csv              │
         │   dim_calendar.csv           │
         │   dim_diary.csv              │
         │   fact_reference.csv         │
         │   fact_place_work.csv  (M-M) │
         └──────────────────────────────┘
                         │
                         ▼
         ┌──────────────────────────────┐
         │ [2] scripts/build_web/       │   (new)
         │     build_web_data.py        │
         │                              │
         │  CSV → denormalised JSON     │
         │  per Places-demo query       │
         └──────────────────────────────┘
                         │
                         ▼
         ┌──────────────────────────────┐
         │  web/data/                   │
         │   manifest.json              │
         │   places.json                │
         │   places_visits.json         │
         │   places_works.json          │
         │   places_timeline.json       │
         └──────────────────────────────┘
                         │
                         ▼
         ┌──────────────────────────────┐
         │ [3] web/  — static site      │   (new)
         │     HTML + vanilla JS        │
         │     Leaflet for map          │
         │     fetch() → render         │
         └──────────────────────────────┘
                         │
                         ▼
              GitHub Pages (or any static host)
```

Three stages, two file formats. No server, no database, no build-time JS toolchain required beyond what the chosen mapping library wants.

## Stage 1 — Excel → CSV (star tables)

**Builds on:** `scripts/normalization/hca_xlsx_to_csv.py` (already emits `entities.csv`, `diary.csv`, `references.csv`).

**Extension:** split `entities.csv` along the WEMI sub-type axis and emit explicit star-schema files in `data/normalized/`:

- `dim_place.csv` — `STED-REGISTER` rows + Sørens-Sted overlay (when present)
- `dim_calendar.csv` — Calendar1800 → ISO date, year, month, day, weekday, season
- `dim_diary.csv` — Diary page / section identity
- `dim_person.csv` — deferred for October but emitted as scaffolding
- `dim_work.csv` — deferred for October but emitted as scaffolding
- `fact_reference.csv` — (diary_id, entity_id, entity_type, page, section)
- `fact_place_work.csv` — M-M edges from Sørens 2. register (when present)

**Versioning:** the existing `resolve_ground_truth_xlsx()` rule (highest `V*` wins) picks up new workbook versions automatically. Stage 1 records the source filename and a SHA-256 of the workbook into `data/normalized/_source.json` for downstream traceability.

**Sørens-register handling:** Stage 1 looks for optional inputs under `raw/sorens/`. If the files are absent, the corresponding columns / fact rows are omitted and a `warnings` array in `_source.json` notes which overlays were skipped. The pipeline never fails on missing Sørens data.

## Stage 2 — CSV → web JSON

**New script:** `scripts/build_web/build_web_data.py`.

**Inputs:** `data/normalized/*.csv`.

**Outputs:** `web/data/*.json` — one file per demo query plus a manifest.

**Per-query shapes (proposed, to be confirmed against the actual demo queries):**

- `manifest.json` — `{ "source_xlsx": "...V0.82.xlsx", "source_sha256": "...", "built_at": "...", "warnings": [...] }`
- `places.json` — full Places dimension, denormalised with coords (when available) and Sørens overlay attributes. Array of `{ id, name, lat, lon, type, sorens_notes, ... }`.
- `places_visits.json` — per Place, the diary entries that reference it: `{ place_id, visits: [{ diary_id, iso_date, page, section, snippet }, ...] }`.
- `places_works.json` — Work ↔ Place edges: `{ place_id, works: [{ work_id, title, type }, ...] }`.
- `places_timeline.json` — facet aggregation: `{ place_id, by_year: { "1840": 3, "1841": 7, ... } }`.

These are **denormalised view shapes** — the relational joins are pre-computed in Stage 2 so the browser does no join work. This keeps the front-end thin (the "thin layer between data and presentation" constraint) and makes each JSON file independently usable.

**Implementation:** pure-Python stdlib + `csv` module is enough at this scale; pandas optional. Aim for the script to be readable end-to-end in one screen.

## Stage 3 — Static web mockup

**New folder:** `web/`.

**Stack:** intentionally minimal.

- `web/index.html` — semantic HTML, no framework required.
- `web/app.js` — vanilla ES modules: `fetch('data/places.json')`, render list / map / timeline.
- `web/styles.css` — plain CSS.
- **Map:** Leaflet (no API key, OpenStreetMap tiles) — the right minimum for the Places demo.
- **Timeline:** vanilla CSS bars driven by `places_timeline.json`; upgrade to a small lib only if needed.

If a framework is later wanted (Astro, SvelteKit, etc.), it can sit on top of the same `web/data/*.json` artifacts without changing Stages 1–2.

## Automation

A single GitHub Action makes the pipeline self-running:

```
.github/workflows/build-mockup.yml

on:
  push:
    paths:
      - 'raw/**'
      - 'scripts/normalization/**'
      - 'scripts/build_web/**'
      - 'web/**'
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - checkout
      - setup-python 3.12
      - pip install -r scripts/parsers/requirements.txt
      - python scripts/normalization/hca_xlsx_to_csv.py
      - python scripts/build_web/build_web_data.py
      - upload web/ as Pages artifact
      - deploy to Pages
```

The trigger is "a new workbook lands in `raw/`": the Action re-extracts CSVs, rebuilds JSON, and redeploys the static site. No manual step between Excel and web.

## Concrete file layout (proposed additions only)

```
scripts/
  build_web/
    build_web_data.py        ← new
    README.md                ← new
web/
  index.html                 ← new
  app.js                     ← new
  styles.css                 ← new
  data/                      ← built artifact, .gitignored or committed snapshot
    manifest.json
    places.json
    places_visits.json
    places_works.json
    places_timeline.json
.github/workflows/
  build-mockup.yml           ← new
docs/data-model/
  october-pipeline.md        ← this file
```

Stage 1's CSVs land in the existing `data/normalized/` directory — no new top-level folder for them.

## What it costs to skip SQLite (and what it would unlock)

Skipping SQLite costs:

- No ad-hoc query interface inside the mockup (users can only see what Stage 2 pre-baked).
- Slightly larger JSON payloads than equivalent SQL queries would return on-demand.

For an October mockup demoing 3–5 fixed Places queries, neither cost is real. If the mockup later wants user-driven exploration over the full star schema, swapping in DuckDB-WASM (option 2 from `star-schema.md`) means *adding* a query layer over the same CSVs — no rework of Stage 1.

## Open items before implementation

1. **The 3–5 Places demo queries** — Stage 2 cannot be coded until the query list is fixed. Drafting these is the next planning step.
2. **Coordinates for Places** — are lat/lon already in `STED-REGISTER`, or does Stage 1 need a geocoding fallback? If geocoding, what gazetteer (GeoNames, Wikidata, manual)?
3. **Sørens registers** — schema and arrival date still pending Søren's clarification.
4. **Hosting** — GitHub Pages is the default assumption; confirm or pick an alternative static host before wiring the Action's deploy step.
