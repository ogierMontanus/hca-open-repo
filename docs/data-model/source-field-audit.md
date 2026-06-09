# Source-field audit

A column-by-column audit of the three normalized CSVs that feed the mockup,
showing how much of each field is populated and whether the mockup surfaces it
to a reader. Use it to spot data that is collected but never shown (a missed
opportunity) or shown but thinly populated (a coverage caveat).

Generated from `data/normalized/*.csv` on **2026-06-08** (16,444 entities ·
2,177 diary pages · 69,405 references). Re-derive after a data refresh with the
counting snippet at the foot of this file.

**Surfacing legend** — ● shown to readers · ◐ used internally (routing, joins,
ordering) but not displayed · ○ present in the data but not used by the mockup.

## `entities.csv` — 16,444 register entries

One row per distinct register entry (persons, places, works). The primary key
`entity_id` is unique: `normalize_entities` drops exact-duplicate rows (the
source sheet repeats `Reg003600`, `Reg003675`, `Reg001907` 4× each), which is
why this is 16,444 and not 16,453.

| Field | Fill | Distinct | | Where in the mockup / notes |
|---|---|---|---|---|
| `entity_id` | 100.0% | 16,444 | ◐ | `?reg=` key behind every detail-page link |
| `entity_type` | 100.0% | 3 | ◐ | routes to person / place / work pages |
| `category_h1` | 100.0% | 3 | ● | "H1: VÆRK-REGISTER" etc. on detail pages |
| `genre_h2` | 22.5% | 4 | ● | H2 chip on work pages; drives wing routing. Only works carry it |
| `form_h3` | 22.5% | 18 | ● | H3 on work pages and category showcases |
| `subform_h4` | 3.9% | 10 | ○ | parsed into the web JSON (`build_web_data.py`) but **not shown in the mockup** |
| `label` | 100.0% | 16,315 | ● | the title/name on every card and heading |
| `description` | 57.6% | 8,718 | ● | the meta line on person/place/work cards |
| `see` | 0.7% | 113 | ● | **Krydshenvisninger** "Se" link (work.html) — surfaced in Step 4. ⚠ Excel `SeeTitle` is populated for works only; 385 persons + 76 places carry the cross-reference *inline* inside `label` ("L, Frue, se: Læssøe, Signe.") and are not lifted into this column — see [Inline `se:` cross-references](#inline-see-cross-references) |
| `see_also` | 0.5% | 75 | ● | **Krydshenvisninger** "Se også" link (work.html) — surfaced in Step 4 |
| `year_derived` | 2.9% | 96 | ● | sidebar **År** on work.html — surfaced in Step 4 |
| `date_derived` | 1.4% | 206 | ● | sidebar **Dateret** on work.html — surfaced in Step 4 |
| `person_derived` | 8.5% | 766 | ● | the **Forfatter** of a work (author link) |

## `diary.csv` — 2,177 diary pages

One row per diary page. Powers `diaries.html` and the generated
`diary-pages/Pag*.html`.

| Field | Fill | Distinct | | Where in the mockup / notes |
|---|---|---|---|---|
| `vol` | 100.0% | 2 | ● | "Bind X" in the page handle and headings |
| `page` | 100.0% | 398 | ● | page number in the handle (`PagVVPPPP`) and headings |
| `date` | 100.0% | 1,506 | ● | the dateline on diary cards and pages |
| `month` | 99.8% | 25 | ● | composes the "{month} {year}" page heading |
| `year` | 100.0% | 4 | ● | the **Årstal** facet on diaries.html |
| `heading` | 97.2% | 534 | ● | the diary-day heading on generated pages |
| `text` | 100.0% | 2,177 | ● | the transcribed diary text |

## `references.csv` — 69,405 diary mentions

One row per (diary page → register entry) mention. The join table behind every
"poster i dagbøgerne" count, the reciprocal co-occurrence links, and the
register-derived diary lists.

| Field | Fill | Distinct | | Where in the mockup / notes |
|---|---|---|---|---|
| `page_id` | 100.0% | 69,405 | ◐ | row key; join target for co-occurrence |
| `entity_id` | 100.0% | 15,056 | ● | links a diary page to a register entry (15,056 of 16,444 entries are mentioned at least once) |
| `entity_label` | 100.0% | 15,037 | ○ | denormalized label; the mockup uses `label` from the entity record instead, so this copy is unused |
| `vol` | 99.8% | 11 | ◐ | (vol, page) join key for co-occurrence and diary lists |
| `page` | 99.7% | 554 | ◐ | (vol, page) join key |
| `seq` | 100.0% | 39,361 | ◐ | within-page ordering so generated lists are stable |

## Audit takeaways

- **Surfaced in Step 4** — `see`, `see_also`, `year_derived`, `date_derived`
  were collected but never shown; they now appear on work pages. All are
  sparse (≤ 3% fill), so they render only where present.
- **Still unsurfaced** — `subform_h4` (3.9% fill) is parsed into the web JSON
  but not shown anywhere in the mockup; a future H4 breakdown on work pages
  could use it. `entity_label` in `references.csv` is redundant with the
  entity record's `label`.
- **Thin but load-bearing** — `genre_h2` / `form_h3` are only 22.5% filled
  because they exist on works alone (3,708 of 16,444 entries); for works they
  are effectively complete.
- **1,388 entries** (16,444 − 15,056) are never mentioned in the diaries, so
  their detail pages show "Ingen dagbogsomtaler".

## Inline `se:` cross-references

The Excel master file (`raw/HCA-Repository V*.xlsx`) carries two dedicated
columns for cross-references — `SeeTitle` and `SeeAlsoTittle` — which the
normalizer copies verbatim into `entities.see` and `entities.see_also`.

For **works** this works as intended: 117 of 118 inline `se:` markers have a
matching `SeeTitle` value, so the structured link is recoverable.

For **persons (385 entries) and places (76 entries) — 461 total** — the
`SeeTitle` column is empty and the cross-reference exists only as a substring
of `RegistryTitle`:

```
Reg0081650    label = "L, Frue, se: Læssøe, Signe."   see = ""
Reg0030060    label = "Aage, se: Drewsen, Aage."       see = ""
Reg0024320    label = "Able, se: Æble."                see = ""
Reg0024360    label = "Apenrade, se: Aabenraa."        see = ""
```

These are pure aliases — short stub entries whose only purpose is to redirect
a reader from the alternative form (older spelling, exonym, short form, married
name) to the canonical entry. They should appear in search and on a thin alias
page that bounces straight to the canonical card.

### Recommended parser pass (deferred)

Extend `normalize_registry()` in
`scripts/normalization/hca_xlsx_to_csv.py` so that when `SeeTitle` is empty
and `RegistryTitle` matches the inline pattern

```
^(?P<alias>.+?),\s*\n?\s*se:\s*(?P<target>.+?)\.?\s*$
```

the parser splits `alias` (kept as the entry's `label`) and `target` (lifted
into `see`). Resolution of `target` to a target `entity_id` reuses the
`resolve_ref()` head-label + whole-word-prefix matcher from
`scripts/build_mockup/build_works_extra.py` — the same logic that already
resolves the 113 work-side `see` strings to register IDs.

This sits alongside the planned `place_alias` work in
[`place-toponymy.md`](place-toponymy.md): the toponymy doc covers *modern*
spelling aliases that are not in the register (USA, Sverige, København),
while this section covers *existing* register aliases whose link is just
stored in the wrong column.

## Re-deriving these numbers

```
python scripts/normalization/hca_xlsx_to_csv.py   # refresh the CSVs first
```

Then, per file, fill rate = non-empty rows ÷ total rows and distinct = unique
non-empty values, column by column. (The figures above were produced by a
short `csv.DictReader` pass over each file.)
