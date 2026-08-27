# Steder_i_dagboegerne VER 1.0 — Category facet + LOD mapping

Status: proposal · 2026-08-26

Source file: `raw/Steder_i_dagboegerne_verificeret_udfyldt VER 1.0.xlsx`
— human-verified by the project's place editor, built from and
superseding the place data in `raw/HCA-Repository V0.82.xlsx`. Sheet
`RawLoc`, 2,435 rows, columns `LocPagID, FKLocID, RegistryTitle,
Category, Country, Years, Book, VolRef, PageRef`.

Distinct from `place-typology.md`, which classifies the **481** places
in the separate SV-udgave register (`data/raw/SV14_places.xml`). This
file classifies the **2,508**-place diary STED-REGISTER this site
actually runs on (`mockup/data/places-extra.js` / `data/normalized/
entities.csv`). Same GeoNames-anchored spirit, different source and
scale — not a replacement for `place-typology.md`, a sibling exercise
for the register the live site uses.

## 1. Fit against the existing register

2,433 of 2,435 rows carry a unique `RegistryTitle`. Matched against
`places-extra.js`'s 2,508 `label`s by exact case-insensitive string:
**2,332 match (95.8%)**. The 101 non-matches are mostly spelling/
punctuation variants (parenthetical alternate names like "Boccano
(Baccano?)", diacritic differences, "Gad's Hill Place" vs. however the
register spells it) rather than genuinely new places — worth a follow-up
pass, not attempted here.

This confirms the file is a clean, near-total re-annotation of the
existing register rather than a partial or differently-scoped list, and
can be joined onto `entities.csv`/`places-extra.js` by name with a
one-time reconciliation of the 101 stragglers.

## 2. Coordinate potential

**The file itself carries no lat/lon columns** — checked directly, not
assumed (`RawLoc`'s 9 columns stop at `PageRef`). Neither does
`HCA-Repository V0.82.xlsx`'s `LocationOverview`, `Registry`, or
`HCA-Repository` sheets, which were checked for the same reason this
file is described as "based on" V0.82: none carry coordinate columns
either. So this is not a source of coordinates by itself.

**What it does enable**: today only 454 of 2,508 register places
(18%) carry a `lat`/`lon` pair in `places-extra.js`. A verified,
13-value controlled-vocabulary `Category` per place is exactly the
missing precondition for a *targeted* reconciliation pass against
Wikidata/GeoNames — search-and-disambiguate-by-name alone is unreliable
at this scale (many place names recur across countries: multiple
"Bregentved"-shaped estate names, rivers and cities sharing a name), but
search constrained by *type* (only match candidates that are P.PPL for
a "City" row, only H.STM for a "River" row, etc.) sharply narrows false
positives. §3 is the type mapping that constraint would run against.

Recommended next step (not executed here, per this task's scope):
pick one category with strong signal-to-noise for a pilot — "Country"
(52 rows, closed set, essentially 1:1 with Wikidata sovereign-state
items) or "Continent" (6 rows) — reconcile those first as a cheap
correctness check on the method, then move to the larger, noisier
categories (City, Property).

## 3. Facet: Category as a new places.html filter

The 13 values are a clean, small, human-verified controlled vocabulary
— exactly the shape `FacetEngine`'s existing facet groups expect
(compare `places.html`'s current `Land`/`Country` facet, or
`persons.html`'s `Rolle / Erhverv`):

| Category | Rows | Share |
|---|---:|---:|
| City | 1,278 | 52.5% |
| Property | 289 | 11.9% |
| Region | 223 | 9.2% |
| Point of interest (POI) | 164 | 6.7% |
| River | 112 | 4.6% |
| Mountain | 98 | 4.0% |
| Island | 72 | 3.0% |
| Lake | 68 | 2.8% |
| Country | 52 | 2.1% |
| Sea | 43 | 1.8% |
| Church | 15 | 0.6% |
| *(none)* | 15 | 0.6% |
| Continent | 6 | 0.2% |

Proposed integration: add `category` as a field on each `places-extra.js`
record (from the 2,332 joined rows; the 176 unjoined/uncategorized
places — 101 name mismatches + 15 blank `Category` + places in the
register that aren't in this file at all — fall to an "Uklassificeret"
bucket, same pattern already used for the `Land` facet's "Uoplyst"
bucket rather than silently dropping them) and a new `data-facet-source="category"`
facet group on `places.html`, positioned near the top alongside `Land`
given it's comparably high-value. Not implemented here — this is the
proposal per the task; wiring it into `build_places_extra.py` and
`places.html` is a follow-up.

## 4. Category → Wikidata / GeoNames mapping

Every Wikidata QID below was confirmed by live lookup against
wikidata.org (not recalled from memory, per this project's
fact-check discipline), resolving to the expected concept in each
case. GeoNames feature codes are from the official reference list
(`http://download.geonames.org/export/dump/featureCodes_en.txt`).

| Category | Wikidata | GeoNames | Notes |
|---|---|---|---|
| City | [city (Q515)](https://www.wikidata.org/wiki/Q515) | `P.PPL` | populated place, generic |
| Country | [country (Q6256)](https://www.wikidata.org/wiki/Q6256) | `A.PCLI` | independent political entity |
| Region | [region (Q82794)](https://www.wikidata.org/wiki/Q82794) | `A.ADM1`/`A.ADM2` or `L.RGN` | ambiguous by design — an administrative region (e.g. a named province) is `A.ADM1`/`ADM2`; a physical/cultural region with no administrative boundary (e.g. "Sachsisk Schweiz") is `L.RGN`. Needs a per-row call, not resolvable from the Category value alone |
| Point of interest (POI) | [point of interest (Q960648)](https://www.wikidata.org/wiki/Q960648) | *(none — S class, varies by what the POI actually is)* | GeoNames has no single POI code; a POI row typically lands on a specific `S.*` code (monument, building, ruin, ...) once identified individually |
| Property | [manor house (Q879050)](https://www.wikidata.org/wiki/Q879050) | `S.EST` | *not* [English country house (Q1343246)](https://www.wikidata.org/wiki/Q1343246) — too England-specific; Q879050 is the general class and its own Wikidata usage already covers Danish estates (Rosenlund, Ormstrup, ...) |
| River | [river (Q4022)](https://www.wikidata.org/wiki/Q4022) | `H.STM` | |
| Mountain | [mountain (Q8502)](https://www.wikidata.org/wiki/Q8502) | `T.MT` | |
| Island | [island (Q23442)](https://www.wikidata.org/wiki/Q23442) | `T.ISL` | |
| Lake | [lake (Q23397)](https://www.wikidata.org/wiki/Q23397) | `H.LK` | |
| Sea | [sea (Q165)](https://www.wikidata.org/wiki/Q165) | `H.SEA` | |
| Church | [church building (Q16970)](https://www.wikidata.org/wiki/Q16970) | `S.CH` | |
| Continent | [continent (Q5107)](https://www.wikidata.org/wiki/Q5107) | `L.CONT` | |
| *(none)* | — | — | 15 rows, unclassified in the source file |

This table is the reconciliation contract for §2's targeted pass: for a
row tagged "River", only accept a Wikidata candidate that is
`instance of` (P31) river (Q4022) or a subclass of it, and/or a GeoNames
candidate with feature code `H.STM` — the same discipline
`scripts/parsers/wikidata_lookup.py` already applies for works (propose
candidates, never auto-write), extended here with a type constraint the
works pipeline didn't need.

## 5. Implementation: Category facet + verified Country override

Status: implemented, 2026-08-26/27.

`scripts/build_mockup/reconcile_steder_categories.py` was rewritten to
extract **both** `Category` and `Country` (not just Category as §3
proposed), using a three-tier match instead of the single exact-match
pass §1 measured:

1. Exact case-insensitive `RegistryTitle` ↔ `label`.
2. Diacritic/orthography-normalized match (æ/ø/å folded, generic accents
   NFD-stripped) — catches spelling-convention drift.
3. Register `"se: X"` / `"se X"` redirect labels, resolved to their
   target `X` and matched (steps 1–2) against that target instead of the
   redirect stub's own label.

This raised the join rate from §1's single-pass 2,332/2,433 (95.8%) to
**2,400/2,433 matched** (2,326 exact + 28 normalized + 46 via redirect),
output to `data/normalized/steder_verified_categories.csv`. Of those
matched rows, 2,394 carry a non-blank `category` and 2,399 a non-blank
`country` (a handful of xlsx rows have one field blank but not the
other).

**Why the xlsx's 2,433 and the register's 2,508 are different numbers,
and why that's expected, not a bug:** the xlsx (`RawLoc`, this file) and
`entities.csv`'s STED-REGISTER are two lists of different size and
provenance — the xlsx is a newer, human-verified re-annotation that
mostly but not entirely overlaps the older, larger register. Matching
by name leaves the register's other **108 places** (2,508 − 2,400) with
no verified `country_da`: the xlsx has no row for them at all (not a
match failure). `places.html`/`kort.html` still list all 2,508 register
places, as before — the join only fills in `country_da` for the 2,400
it can identify, same "Uklassificeret"/"Uoplyst" fallback-bucket pattern
already used for `category` and the older bounding-box `Land` facet.
This 108 (not the 13 places initially expected) was accepted as the
correct, current figure after investigation ruled out a same-scope fix
(a deeper LocID-based ID migration against `raw/HCA REPOSITORY
V0.92/LocationData-PQ-V0.92.xlsx`'s `DimLoc1` sheet could plausibly
close more of the gap, but is out of scope for this pass).

`scripts/build_mockup/build_places_extra.py`'s `load_verified_categories()`
became `load_verified_categories_and_countries()`; the verified
`country` **overrides** whatever `country_da` the existing
rejser.tsv → SV14 → HERRED_AMT-label fallback chain produced (but
coordinates and `geo_source` are left as that chain set them — only
`country_da` is replaced). Effect on the `places.html`/`kort.html`
Country facet: England and Skotland now appear as separate values (46
and 26 places respectively) instead of being folded into one
"Storbritannien" bucket, the bounding-box gazetteer's old behavior.

### Nationality roll-up for nation.html

`nation.html`'s per-nationality "places in this nation" mashup reads
`country_da` through the coarser, pre-existing nationality vocabulary
(`data/curated/ethnic_adjectives_da.csv`,
`nation_place_labels_da.csv`, `nation_umbrellas_da.csv`) — which has no
"Skotland"/"Irland" entries of its own, only a `britisk` umbrella
pointing at "England". Left alone, the newly-granular `country_da`
values would have made Skotland/Irland-tagged places invisible to
`nation.html` (no umbrella member's own label is "Skotland" or
"Irland"). `data/curated/steder_country_to_nation_da.csv` is a new
crosswalk (xlsx country → nation-vocabulary place label) that
`build_nation_index.py` applies **only** when consuming
`places-extra.js` (`load_places_extra(path, country_to_nation)`) —
`country_da` itself stays granular for places.html/kort.html; only
nation.html's aggregation folds Skotland/Irland into the `britisk`
umbrella's England bucket. 34 of the xlsx's ~60 countries have a
nationality-vocabulary counterpart today; the rest (Tjekkiet, Kroatien,
Marokko, the 5 continent values, ...) are left unmapped in the
crosswalk with a documented reason, since no nationality key exists for
them to roll up to.

**Known limitation, not fixed in this pass:** for the `britisk`
umbrella, the aggregate `places_in_country` union is correct (73 places,
England+Skotland+Irland combined) but the *per-member* breakdown
(`engelsk`/`skotsk`/`irsk`/`britisk`/`angelsaksisk`, meant to show which
sub-identity a place came from) attributes all 73 to `engelsk` only,
because each member's own `places_in_country` is still computed from
its *own* individual label (`skotsk` → "Skotland") before umbrella
clustering, and the crosswalk has already remapped every
Skotland/Irland-tagged place's `country_da` to "England" by the time
`build_nation_index.py` reads it — so `skotsk`'s own lookup finds
nothing left under "Skotland". This is not a regression: before this
change, GB places carried the bounding-box value "Storbritannien",
which didn't match any individual member's label either, so the
per-member breakdown was already empty for all of them (0/0/0/0/0
rather than today's 0/73/0/0/0). Fixing it would mean computing
per-member breakdowns after umbrella clustering, using the umbrella's
own crosswalk-aware lookup — deferred as a follow-up.

## Not done here

- The residual 108-place Country gap (§5) and 108/2,508-place Category
  gap (§3) — a LocID-based crosswalk against V0.92's `DimLoc1` sheet is
  a plausible next step, not attempted.
- Any actual Wikidata/GeoNames *entity* lookups for individual places —
  §4 maps the **category vocabulary** to classes, not any of the 2,332
  places to their own Wikidata/GeoNames items. That is the follow-on
  work §2/§4 set up, not attempted in this pass.
- Fixing the `britisk` umbrella per-member attribution limitation (§5).
