# Stage 2 — CSV → web JSON

Reads star-shaped CSVs from `data/normalized/` and emits denormalised JSON
artifacts to `web/data/` that the static mockup in `web/` fetches directly.

See [`docs/data-model/october-pipeline.md`](../../docs/data-model/october-pipeline.md)
for the full pipeline rationale.

## Usage

```sh
# Stage 1 (existing): xlsx → CSV
python scripts/normalization/hca_xlsx_to_csv.py

# Stage 2 (this script): CSV → JSON
python scripts/build_web/build_web_data.py
```

Stdlib only — no dependencies beyond Python 3.10+.

## Outputs

| File | Shape | Purpose |
|---|---|---|
| `manifest.json` | `{ built_at, source_xlsx, source_xlsx_sha256, counts, warnings }` | Provenance |
| `places.json` | `[ { id, label, visit_count, lat, lon }, … ]` | Places dimension |
| `places_visits.json` | `{ place_id: [ { vol, page, date, year, snippet }, … ] }` | Diary entries per Place |
| `places_timeline.json` | `{ place_id: { year: count, … } }` | Per-Place year histogram |
| `places_works.json` | `{ place_id: [ { work_id, work_label, page_count }, … ] }` | Co-occurring Works (placeholder for Sørens M-M edge) |

## Known placeholders

- `lat` / `lon` are `null` until a geocoding pass is decided (open item).
- `places_works.json` uses page-level co-occurrence as a stand-in for the
  Work↔Place edge expected from Sørens 2. register.
- The per-query shapes above will be refined once the 3–5 Places demo
  queries are pinned down.
