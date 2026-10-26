# Place register — `HCA_Steder_GÆLDENDE_21102026_LocationID_alle_2433_steder.xlsx`

Status: **implemented**, 2026-10-26. The workbook (in `data/`) is the base
of the place register (STED-REGISTER). It supersedes, for places:

| Replaced | Was used for |
|---|---|
| `HCA-Repository V0.82.xlsx` → `Registry` place rows (`Reg…` ids, 2,508 rows) | place identity, label, page references |
| `raw/Steder_i_dagboegerne_verificeret_udfyldt VER 1.0.xlsx` → `steder-verificeret-category-mapping.md` | category, country |
| `data/raw/4-LOCATION-V0.97.xlsx` | LocationIDs, labels, coordinates (still read for the page lists, see §3) |
| `rejser.tsv` / SV14 as the *first-choice* geocode | coordinates (now fallback, see §4) |

## 1. The file

Sheet `Ark1`, 2,433 places, one row each. Columns: `Løbenummer` (order of
first appearance in the diaries), `LocationID*` (`LOC…`, unique, **the same
2,433 ids as V0.97**), `RegistryTitle`, `Category` (Danish), `Country`,
`Book` + `PageRef` (the place's **first** diary page), `Latitude`,
`Longitude`, `GeocodingStatus` (`Fundet` 2,422 / `Ikke fundet` 11), `Besøgt
eller omtalt` (`Besøgt` 1,789 / `Omtalt` 644). 2,421 places carry
coordinates.

It is a *clean* register: no `se:` redirect stubs (the old register had
77, none with diary references), no OCR-corrupted labels (173 old
`Reg…` labels had no counterpart), no duplicate labels.

## 2. Pipeline

```
data/HCA_Steder_GÆLDENDE_*.xlsx ─┐
data/raw/4-LOCATION-V0.97.xlsx ──┼─► scripts/normalization/place_register.py
  (FKDiaryPageID = all pages)    │      ▲ used by
HCA-Repository V0.82.xlsx ───────┘      │
   (persons + works only)          hca_xlsx_to_csv.py ─► data/normalized/
                                                           entities.csv   (places: LOC… ids)
                                                           references.csv (place rows rebuilt)
                                                           places.csv     (NEW: category, country, lat/lon, status)
                                                              │
                  build_places_extra.py ◄─────────────────────┘ ─► mockup/data/places-extra.js
                  build_nation_index.py (country → nation bucket) ─► nation-index.js
                  build_web_data.py (web/data/places.json)
                  place_v097_crosswalk.py + hca_v092_to_csv.py (V0.92 side, normalized_v092/)
```

* `place_register.py` finds the **newest** `HCA_Steder_G*LDENDE_*.xlsx` by
  the `DDMMYYYY` in its name (searching `data/`, then `data/raw/`), so a
  later drop with the same naming convention is picked up automatically.
  `hca_xlsx_to_csv.py --places <file>` overrides; `--no-place-base` keeps
  the V0.82 places.
* `build_all.py` runs the V0.82 ingester as stage `1a2` when the picked
  source folder is V0.92, so `data/normalized/` gets the new places in
  either flow.
* Places are written in ascending LocationID order = alphabetical (the ids
  are allocated in alphabetical slots), i.e. the printed-index order the
  `Reg…` ids had. `references.csv.seq` follows that order; `page_id` is a
  per-row key `PagL######`.
* `entities.csv.description` stays **empty** for places on purpose —
  `place.html` prints it as a prose paragraph.
* Retired: `scripts/build_mockup/reconcile_steder_categories.py` and
  `data/normalized/steder_verified_categories.csv` (keyed on dead `Reg…`
  ids; category + country now come straight from the workbook).

## 3. Diary page references

The workbook only has the **first** page per place. The full list is
`FKDiaryPageID` of `4-LOCATION-V0.97.xlsx`, joined on the identical
`LocationID` (no fuzzy matching). Check: for 2,428 of 2,433 places the
earliest V0.97 page *is* Book/PageRef. The five exceptions are corrections
made in the new workbook; the corrected first page replaces the V0.97
earliest page:

| LocationID | Place | V0.97 first page | Workbook first page |
|---|---|---|---|
| LOC1024500 | Dornburg | II-177 | III-177 |
| LOC1045650 | Høgebjerg, Als | II-448 | II-445 |
| LOC1021800 | Cuxhaven | III-162 | III-164 |
| LOC1036600 | Glücksborg | IV-14 | IV-44 |
| LOC1058250 | Lipariske Øer, de | IV-146 | II-146 |

Result: **18,737 place references** (V0.82: 18,849 rows / 18,832 distinct),
4,403 diary pages carrying a place (V0.82: 4,342). Non-place references
and entities are byte-identical to before. Ask the data owner to put the
full page list into the next workbook version and the V0.97 dependency
disappears (`load_v097_pages()` is the only reader).

## 4. Fields in `places-extra.js`

| Field | Source |
|---|---|
| `category` | workbook `Category`, mapped to the English UI vocabulary by `CATEGORY_DA_TO_EN` (By→City, Ejendom→Property, Område→Region, Point of interest→Point of interest (POI), Flod→River, Bjerg→Mountain, Ø→Island, Sø→Lake, Land→Country, Hav→Sea, Kirke→Church, Kontinent→Continent, **Fiktivt sted→Fictional place (new)**) |
| `country_da` | workbook `Country`, verbatim (England/Skotland/Wales stay distinct) |
| `lat`, `lon`, `geo_source:"register"` | workbook coordinates; where absent, rejser → SV14 → herred/amt as before |
| `visit` | `Besøgt` / `Omtalt` (new; not yet shown in the UI) |
| `destination_en` | still from rejser / SV14 name matches (the "a.k.a." line on `place.html`) |

Coordinates went from 456 to **2,421** geocoded places, so `kort.html` and
the web demo now plot the whole register.

## 5. Open items for the editor

See the hand-over summary in the session that introduced this file; the
short list: the `Smyrna`/`LOC1087400` row (looks like an overwritten
`Ronco all' Adige`), new countries without a nation mapping
(`data/curated/steder_country_to_nation_da.csv`, rows tagged `NEW
2026-10-21`), the `Fiktivt sted` category (3 places), 4 places with blank
Category/Country, and the ids of old bookmarks (`place.html?reg=Reg…` no
longer resolves; use the `LOC…` id).

Not regenerated because they are task-specific snapshots keyed on `Reg…`
ids: `data/normalized/ner_page_grounding*.csv` (vols VI–VII, see
`ner-page-task.md`). Re-running `scripts/parsers/ner_page_grounding.py`
rewrites them for all volumes (≈63k rows instead of ≈11.6k).
