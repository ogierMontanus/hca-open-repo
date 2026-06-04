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

All five outputs are fully derived from the normalised CSVs, so they
are excluded from git. The committed mockup pages **degrade
gracefully**: when the generated data is absent they fall back to the
hand-curated `WORKS` / `PERSONS` / `PLACES` dicts in
`mockup/{work,person,place}.html` and the static sample cards on the
listing pages.

## One-time local build

Run all five generators from the repo root after `data/normalized/`
exists (Stage 1a of the CI workflow puts the CSVs there). The
commands below use `python` (the Windows / PowerShell launcher); on
Linux/macOS substitute `python3` if your `python` still points at
Python 2.

```powershell
# Prereq: the normalised CSVs must exist first.
python scripts/normalization/hca_xlsx_to_csv.py    # Stage 1a
python scripts/build_web/parse_rejser_htm.py       # Stage 1b (geocodes)

# Then the five mockup builders, in any order:
python scripts/build_mockup/build_diary_pages.py
python scripts/build_mockup/build_diary_index.py
python scripts/build_mockup/build_works_extra.py
python scripts/build_mockup/build_persons_extra.py
python scripts/build_mockup/build_places_extra.py
```

Or in one go — PowerShell:

```powershell
foreach ($s in 'build_diary_pages','build_diary_index',
               'build_works_extra','build_persons_extra','build_places_extra') {
  python "scripts/build_mockup/$s.py"
}
```

Or in one go — bash / zsh:

```bash
for s in build_diary_pages build_diary_index \
         build_works_extra build_persons_extra build_places_extra; do
  python3 scripts/build_mockup/$s.py
done
```

Then open `mockup/diaries.html`, `mockup/work.html?reg=Reg001260`,
`mockup/person.html?reg=Reg0052440`, `mockup/place.html?reg=Reg0017430`,
etc. from disk.

## How the data flows

```
data/normalized/*.csv
        │
        ├── diary-pages/Pag*.html       (build_diary_pages.py)
        ├── diary-index.js              (build_diary_index.py)
        ├── diary-refs.js               (build_diary_index.py)
        ├── works-extra.js              (build_works_extra.py)
        ├── persons-extra.js            (build_persons_extra.py)
        └── places-extra.js             (build_places_extra.py)
                │
                ▼
        ┌───────────────────────────────────────────────────────┐
        │ ?reg=… detail pages   ← read ALL_{WORKS|PERSONS|PLACES} │
        │   work.html, person.html, place.html                  │
        │ Diary cards (DiaryWire) ← read DIARY_INDEX/DIARY_REFS │
        │   diaries.html + the sections embedded in work/person/place │
        │ Diary pages (static HTML) ← link to ?reg=… per entity │
        └───────────────────────────────────────────────────────┘
```

`ALL_WORKS`, `ALL_PERSONS`, `ALL_PLACES` are `Object.assign({},
*_EXTRA, *)` — generated data first, then any hand-curated entry from
the curated dict at the top of the page overrides it. So a 3,717-work
catalog comes "for free" from the CSV, and bespoke entries (Sixtinske
Madonna, Dickens, Rom …) still control the rich card content.

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
