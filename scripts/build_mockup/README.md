# Mockup build scripts

Generators that turn the normalized CSVs in `data/normalized/` into the
data the static mockup under `mockup/` consumes. The mockup is designed to
open straight from the filesystem (`file://`), where the browser blocks
`fetch()` of JSON — so every generated artifact is either a static HTML
file or a `*.js` file that defines a global via a plain `<script>` tag
(the same pattern as the committed `mockup/data/works-extra.js`).

## Scripts

| Script | Reads | Writes | Committed? |
|--------|-------|--------|------------|
| `build_works_extra.py` | `entities.csv` | `mockup/data/works-extra.js` | yes (small) |
| `build_diary_pages.py` | `references.csv`, `diary.csv`, `entities.csv` | `mockup/diary-pages/Pag*.html` (one per diary page) | **no — gitignored** |
| `build_diary_index.py` | `references.csv`, `diary.csv`, `entities.csv` | `mockup/data/diary-index.js`, `mockup/data/diary-refs.js` | **no — gitignored** |

The diary outputs are large (≈4,500 HTML pages, ≈29 MB; ≈2 MB of index
JS) and fully derived, so they are excluded from git via `.gitignore`.
The committed mockup pages **degrade gracefully**: when the generated
data is absent they keep their hand-written sample cards; when it is
present, JavaScript replaces those samples with the full dataset.

## One-time local build

Run from the repo root, after `data/normalized/` exists:

```bash
python3 scripts/build_mockup/build_diary_pages.py   # per-page HTML bodies
python3 scripts/build_mockup/build_diary_index.py   # index + reverse-index JS
```

Then open `mockup/diaries.html` (or any register page) from disk.

## How the wiring fits together

- `build_diary_pages.py` emits one page per unique diary `vol`+`page`,
  named `Pag{VV}{PPPP}.html` (volume number `I→01 … XI→11`, zero-padded
  page). Each page shows the transcribed text (vols VI+VII only),
  the register entries that occur on it, and prev/next navigation.
- `build_diary_index.py` emits two globals:
  - `DIARY_INDEX` — one row per diary page (handle, vol, page, date,
    year, place, up to three entity chips) → powers the live listing,
    year facet and text filter on `diaries.html`.
  - `DIARY_META` + `DIARY_REFS` — page metadata and a reverse index
    `registerId → {n: total, e: [pag, …]}` (capped at 60 pages per
    entity) → powers the "Dagbogsreferencer" section on `place.html`,
    `person.html` and `work.html`.
- `mockup/js/diary-wire.js` (committed) reads those globals and renders
  the cards, with pagination and a "Vis flere" button. It is a no-op
  when the data files are missing.

## Follow-ups

- Dates/years currently exist only for the transcribed volumes
  (VI + VII, 751 of 4,544 pages). The remaining pages list vol/page
  only until more volumes are transcribed.
- Deployment (e.g. GitHub Pages) should run both diary builders in CI so
  the generated pages ship in the published `_site`, mirroring the
  existing `web/` data build.
