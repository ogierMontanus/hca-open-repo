# Collin person index — extraction + register match

Source: `IV. PERSON-REGISTER`, PDF pp. 84–163 of `andersen-hc_breve-collin_6.pdf`. HCA/Edvard/Henriette Collin excluded (stated on the section's own opening page).

## Extraction (`scripts/correspondence/extract_collin_person_index.py`)

Entries are too structurally varied for the place-index's line-start heuristic (Danish formal titles are themselves capitalized, so a wrapped continuation line looks like a new entry). Instead: regex-anchor on `Surname, Given(s) (birth[-death])`, required to start right after a previous entry's closing punctuation or section-start. Excludes citation volume markers (`I,`/`II,`/…/`VII,`) so they're never read as a surname.

**1,608 dated entries extracted.** Entries with no birth/death year printed at all are out of scope for this method (they carry no matchable year anyway). Citation text is captured only approximately (used for an OCR-noise quality flag, not for matching).

Output: `data/curated/collin_letters_person_index.csv`, review flags in `..._person_index_review.csv` (324 rows, high citation OCR noise).

## Match against this project's PERSON-REGISTER (`match_collin_persons_to_register.py`)

Key: normalized surname (æ/ø/å folded explicitly, not NFD-stripped — same convention as this project's own `initialOf()` helpers) + exact birth year. Matched against `mockup/data/persons-extra.js` (10,228 persons).

| Tier | Count | Meaning |
|---|---|---|
| exact | 1,118 | surname + birth year match exactly one register person |
| ambiguous | 91 | surname + birth year match more than one |
| surname_year_mismatch | 104 | surname matches, but register's recorded birth year differs |
| surname_only | 131 | surname matches a person with no recorded birth year |
| none | 131 | no register person shares the surname |

Output: `data/curated/collin_letters_person_match.csv`. Proposal only — nothing written back to `entities.csv`/`persons-extra.js`. Same propose/verify shape as `works_wikidata.csv`, `breve_person_crosswalk.csv`.

**Not yet done:** human review of the 91 ambiguous + 104 mismatch rows; resolving the `none` tier (may be genuinely absent from the diary register, or a surname-spelling divergence).
