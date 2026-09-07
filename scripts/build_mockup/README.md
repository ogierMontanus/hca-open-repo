# Mockup build scripts

Generators that turn the normalized CSVs in `data/normalized/` into the
data the static mockup under `mockup/` consumes. The mockup is designed
to open straight from the filesystem (`file://`), where the browser
blocks `fetch()` of JSON — so every generated artifact is either a
static HTML file or a `*.js` file that defines a global via a plain
`<script>` tag.

## Scripts

| Script | Reads | Writes | Committed output? |
|--------|-------|--------|-------------------|
| `build_diary_pages.py`   | `references.csv`, `diary.csv`, `entities.csv`               | `mockup/diary-pages/Pag*.html` (≈4,500 files) | **no — gitignored** |
| `build_diary_index.py`   | `references.csv`, `diary.csv`, `entities.csv`               | `mockup/data/diary-index.js`, `diary-refs.js` | **no — gitignored** |
| `build_works_extra.py`   | `entities.csv`, `references.csv`                            | `mockup/data/works-extra.js`   (3,677 works)  | **no — gitignored** |
| `build_persons_extra.py` | `entities.csv`, `references.csv`                            | `mockup/data/persons-extra.js` (10,228 persons) | **no — gitignored** |
| `build_places_extra.py`  | `entities.csv`, `references.csv`, `rejser.tsv`              | `mockup/data/places-extra.js`  (2,508 places, ≈391 geocoded) | **no — gitignored** |
| `build_search_index.py`  | `entities.csv`, `references.csv`                            | `mockup/data/search-index.js`  (~16,400 entities, ref-sorted) | **no — gitignored** |
| `build_cooccurrence.py`  | `entities.csv`, `references.csv`                            | `mockup/data/cooccurrence.js` (top-12 peers per person/place, count ≥ 2) | **no — gitignored** |

All six outputs are fully derived from the normalised CSVs, so they
are excluded from git. The committed mockup pages **degrade
gracefully**: `work.html` and `place.html` fall back to their own
hand-curated `WORKS`/`PLACES` dicts when the generated data is absent;
`persons.html` and the listing pages fall back to their static sample
cards instead (`persons.html` has no hand-curated override dict of its
own — see the data-flow diagram below).

## One-time local build

Run the wrapper from the repo root — it executes every stage in the
right order with the same Python interpreter and prints `✓ stage N
done` after each:

```powershell
python scripts/build_all.py
```

Useful flags:

```powershell
python scripts/build_all.py --skip-pages   # skip the slow 4,500-file diary HTML stage
python scripts/build_all.py --only 4b      # rebuild just persons-extra.js
```

The wrapper covers all ten stages — Stage 1a (xlsx → CSV), Stage 1b
(rejser geocodes, optional), Stage 2 (web JSON), Stage 3a/3b (diary
pages + index), Stage 4a/4b/4c (works/persons/places extras), Stage 4d
(search index for the landing typeahead), Stage 4e (co-occurrence
index for the reciprocal-link sections on persons.html / place.html).
Stage 1b's failure is non-fatal, mirroring CI.

Then open `mockup/diaries.html`, `mockup/work.html?reg=Reg001260`,
`mockup/persons.html?reg=Reg0052440`, `mockup/place.html?reg=Reg0017430`,
etc. from disk.

Need to run a single builder by hand? See the script paths in the
table above — they're plain `python scripts/build_mockup/<name>.py`
invocations from the repo root.

## How the data flows

```
data/normalized/*.csv
        │
        ├── diary-pages/Pag*.html       (build_diary_pages.py)
        ├── diary-index.js              (build_diary_index.py)
        ├── diary-refs.js               (build_diary_index.py)
        ├── works-extra.js              (build_works_extra.py)
        ├── persons-extra.js            (build_persons_extra.py)
        ├── places-extra.js             (build_places_extra.py)
        ├── search-index.js             (build_search_index.py)
        └── cooccurrence.js             (build_cooccurrence.py)
                │
                ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │ ?reg=… detail pages                                             │
        │   work.html, place.html ← ALL_{WORKS|PLACES} (hand-curated      │
        │     WORKS/PLACES object takes precedence over the *_EXTRA data) │
        │   persons.html ← PERSONS_EXTRA directly, no override object     │
        │ Diary cards (DiaryWire) ← read DIARY_INDEX/DIARY_REFS           │
        │   diaries.html + the sections embedded in work/persons/place    │
        │ Diary pages (static HTML) ← link to ?reg=… per entity           │
        │ Landing typeahead (js/landing-search.js) ← SEARCH_INDEX         │
        │   index.html — focus-on-load + live ?reg=… autocomplete         │
        └─────────────────────────────────────────────────────────────────┘
```

`ALL_WORKS` and `ALL_PLACES` (work.html, place.html) are
`Object.assign({}, *_EXTRA, *)` — generated data first, then any
hand-curated entry from the curated dict at the top of the page
overrides it. So a 3,717-work catalog comes "for free" from the CSV,
and bespoke entries (Sixtinske Madonna, Rom …) still control the rich
card content. `persons.html` has no equivalent `ALL_PERSONS`/`PERSONS`
pair — that pattern lived only in `person.html`, an unreferenced legacy
page deleted 2026-09-07 (see docs/data-model/detail-page-redundancy.md);
`persons.html` reads `PERSONS_EXTRA` directly.

## Continuous integration

`.github/workflows/build-mockup.yml` runs Stages 1 → 4 on every push
to `main`. Stage 4 contains all three per-entity generators and Stage 3
the two diary generators. The bundled `_site` artifact includes every
generated file so the deployment target receives a fully populated
mockup.

## Follow-ups

- Dates/years for diary pages currently exist only for vols VI + VII
  (751 of 4,544 pages); the other ≈3,800 pages list vol/page only
  until more volumes are transcribed.
- Country attribution for places comes from a 33-country bounding-box
  gazetteer inlined in `build_places_extra.py` (and `build_web_data.py`).
  Replace with a proper reverse-geocoder when the workshop produces one.
- Wikidata Q-numbers and biography text live only in the hand-curated
  `PERSONS` / `PLACES` / `WORKS` dicts; enriching the generated extras
  from an authority file is a separate Phase 2 task.
