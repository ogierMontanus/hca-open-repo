# Collin letter volume+page → Brevbasen BrevID mapping

Source: volumes I–IV of *H. C. Andersens Brevveksling med Edvard og Henriette Collin* (the only 4 of the 6 physical volumes that contain letter text — confirmed from each PDF's own title page, not assumed: **V is "KOMMENTAR"** (line-by-line annotation, not letters) and **VI is "REGISTRE"** (the index volume already digitized in `collin-place-index.md`/`collin-person-index.md`). Both checked directly for the `<N>. Fra/Til <Person>.` heading pattern and found none, as expected.

## Pipeline

1. **`extract_collin_letter_pages.py`** — every letter heading across vols. I–IV (505 letters), with printed page range and a resolved dateline where the printed page shows one (280/505, 55%). Reuses the heading/page-number extraction from `lookup_collin_letter_by_page.py`; two real bugs found and fixed along the way:
   - later volumes spell the dateline out ("den 5te Juni") instead of abbreviating ("d. 8. Febr."), sometimes with no marker at all — the regex only covered the abbreviated form.
   - a bare (unparenthesized) year on a period-marker line matched the same digits-only shape as a page number and was accepted as one — no volume here exceeds ~503 pages, so anything in the plausible-year range is now rejected.

2. **`match_collin_letter_ids.py`** — calibrates the mapping: 5 resolved samples per volume (20 total), matched against `hca_db_export/hca_db.sql`'s `brev` table by **date**, disambiguated by **sender/recipient identity** (`brev_person` → `person`) when a date is shared by more than one row in the wider 13,585-letter database — never by letter text. A per-volume linear fit (letter number → BrevID) is then applied to every remaining letter.

## Result

All 20 calibration slots resolved (13 of the initial picks were ambiguous — a shared date with an unrelated letter elsewhere in the database — and were replaced by trying further sampled letters until 5 resolved per volume; the failed attempts are kept in `collin_letter_id_calibration_review.csv`, not hidden).

The **incremental-numbering assumption holds**: BrevID increases with letter position in every volume, confirmed directly rather than assumed —

| Vol | (letter_no → BrevID), collision-free points used for the fit |
|---|---|
| I | (2→333), (35→454), (82→870) |
| II | (145→3348), (247→6318), (301→9017) |
| III | (411→10831), (448→11443), (494→11991) |
| IV | (579→12789), (591→12885), (696→14675) |

**One genuine ambiguity surfaced, not smoothed over**: 4 pairs of *different* letters (e.g. vol. I letters 7 and 8) share the exact same printed date, and the general `brev` table has only one row for that date — meaning at least one letter in each pair maps to the wrong BrevID even though the date lookup itself was "unique". These pairs are excluded from the linear fit and flagged with a `[COLLISION: ...]` note in `collin_letter_id_calibration.csv`.

## Output

- `data/curated/collin_letter_pages.csv` — the 505 extracted letters (volume, letter_no, direction, person, page range, dateline).
- `data/curated/collin_letter_id_calibration.csv` — the 20 verified samples, with `match_note` recording *how* each was resolved (unique date / disambiguated by person / collision).
- `data/curated/collin_letter_id_calibration_review.csv` — the 13 sampled-but-rejected attempts, for transparency.
- `data/curated/collin_letter_pages_with_ids.csv` — all 505 letters with an `estimated_brevid` (`calibration_sample` for the 20 verified rows, `interpolated` for the rest via the per-volume fit, `no_estimate` for the 1 letter whose number didn't parse as an integer).

**Not done:** the interpolated BrevIDs for the other 485 letters are estimates, not verified — a linear fit across ~70–150 letters per volume assumes no reordering/gaps in Brevbasen's own ID assignment beyond what the 3 collision-free calibration points can see. Treat `estimated_brevid` accordingly; only the 20 `calibration_sample` rows (minus the collision caveat above) are checked against the database directly.
