# Per-page NER task (adapted from NER4andersen)

*English translation of `ner-page-task.md`. The Danish file is the
source of record; if the two drift apart, treat the Danish version as
authoritative and re-sync this one.*

## Background

`ner4andersen` defines a multi-stage enrichment pipeline (harvest →
consolidation → reconciliation → curation) that operates across the
whole register, with source provenance per candidate (`sources[]`:
volume, page, type) and a confidence score per reconciliation
candidate (§6–§7 in `plan-v3.md`).

**`data/normalized/references.csv` is the ground truth for this
task** — it is the raw entity-occurrence table: one row per
diary-page↔entity link, derived from `entities.csv` (`entity_id`/
`entity_label` are foreign keys into the register) and from the
`RefInDiaryPage` sheet in the source workbook
(`raw/HCA-Repository V0.82.xlsx`, see
`scripts/normalization/hca_xlsx_to_csv.py`). The file states
**which** entities are linked to which page — not where in the
page's text they actually occur. 69,405 rows, one per `(vol, page,
entity_id)` combination (no duplicates); the number of entities per
page ranges from 1 to over 200 (e.g. vol. III page 64: 17 distinct
entities). The `page_id` field in this file is **not** a composite
page key the way it is in `data/normalized_v092/references.csv`
(`Pag{vol:02d}{page:04d}`) — here it is a unique running number per
row, and `seq` is a global running number, not an occurrence count.
The page key is therefore `(vol, page)`, matched against
`data/normalized/diary.csv`.

This document defines the task that supplements this known per-page
entity list with **where in the text** each entity actually occurs —
a **grounding task**, not open-vocabulary NER: the entity identity
(`entity_id`) is already given by `references.csv`; the task is to
locate and disambiguate the concrete occurrence strings in the raw
page text.

### Example: a page with many entities across several registers

Volume V, page 20, is among the pages in `references.csv` with the
most linked entities spread across the most register types: **38
links total — 30 from PERSON-REGISTER, 5 from STED-REGISTER, 3 from
VÆRK-REGISTER** (work links are out of scope for the grounding task
itself, cf. ner4andersen §11, but are counted here as an example of
"several indexes" on the same page).

Live page at the Royal Danish Library (from
`data/normalized/kb_diary_links.csv`, column `kb_url`, source
`workbook`):

**<https://epub3.kb.dk/hcadag/epub3/EPUB/hcadag05_040_20.xhtml>**

(The link could not be verified live from this session — outbound
access to `epub3.kb.dk` is blocked by the sandbox's network proxy —
but it was pulled directly from the repo's own `kb_diary_links.csv`,
not guessed.)

Example entities linked to the page:

| Type | Examples (label) |
|---|---|
| person | Bissen, H. V. (1798–1868) · Bournonville, August (1805–1879) · Boye, Maria, f. Birckner (1796–1880) |
| place | Dresden · Haderslev · London · Silkeborg |
| work | Ole Lukøie (Eventyrkomedie) · Minerva (H. V. Bissen, Udg. i Biscuit) |

Note: page V/20 (like most referenced pages) has no transcribed text
in `data/normalized/diary.csv` yet — it therefore cannot itself be
grounded by `ner_page_grounding.py` until the text is added. It is
used here purely to illustrate the breadth of the candidate list per
page, cf. the coverage-limitation section below.

## Task definition

Point of departure: **`data/normalized/references.csv`**, not the
page's raw text. For each `(vol, page)`, look up the associated set
of `entity_id`s in `references.csv` — this is the closed candidate
list for the page. Then look up the page in
`data/normalized/diary.csv` (text field `text`, line tags `NNN-LL`)
to find the occurrences.

1. **For each entity in the page's candidate list** (from
   `references.csv`), find the string(s) in the page text that refer
   to it (person or place — the same scope boundary as ner4andersen
   §11: organizations/keywords are out of scope for the NER task
   itself, but may already occur as an `entity_type` in
   `entities.csv` and must in that case be excluded from the
   grounding run).
2. **Occurrence-frequency assumption:** each entity in the page's
   candidate list is assumed to occur **between 1 and 5 times** in
   the page text. This is a heuristic for calibrating recall targets
   and probability-weighting candidate spans — not a hard limit on
   output, and not derived from the `seq` field (which is not an
   occurrence count, as noted above).
3. **Goal:** find as many actual text occurrences as possible for the
   entities in the page's candidate list (maximize recall over the
   known entity list — not over an unknown/open entity set, since it
   is already given by `references.csv`).
4. **1:1 assignment:** each occurrence string in the text should
   ideally be assigned to **exactly one** entity from the page's
   candidate list. Where a string is genuinely ambiguous between two
   entities on the same candidate list (e.g. a given name that
   matches several people mentioned on the same page), the best
   candidate should be chosen and the uncertainty reflected in the
   confidence score — not by assigning the string to multiple
   entities.
5. **Confidence score:** each string→entity grounding gets a
   numeric confidence score, following the same pattern as existing
   scorers in the repo (`parse_person_gender.py`,
   `detect_work_language.py`, `add_language_column.py`): a
   scorer/classifier produces a value, with no automatic write to
   curated files without human review below a threshold.

## Output schema

Proposed extension — a separate proposal layer built from the
existing `references.csv` row, the same separation principle as
`wikidata_lookup.py`, which **never** writes to the curated file
itself. Each output row **extends** a given `references.csv` row
with span information; it does not write a new entity connection:

```
ref_page_id,vol,page,entity_id,entity_label,mention_text,mention_start,mention_end,confidence,method
Pag100000,III,64,Reg001445,"Gesammelte Werke (1847-72)","Gesammelte Werke",412,428,0.87,ner_grounding_v1
```

| Field | Meaning |
|---|---|
| `ref_page_id` | Foreign key to the source `page_id` in `data/normalized/references.csv` (note: a running number, not a page key) |
| `vol`/`page` | The page key, matched against `diary.csv` |
| `entity_id`/`entity_label` | Copied from the `references.csv` row being grounded — **not** re-looked-up by the scorer |
| `mention_text` | The located string, as it occurs in `diary.csv.text` |
| `mention_start`/`mention_end` | Character position in the page's `text` field (the `NNN-LL` line tag counts as part of the text, per the existing OCR line-tagging) |
| `confidence` | `[0.0, 1.0]`, the same scale as `person_gender.csv` |
| `method` | Scorer/model identifier, for reproducibility (cf. ner4andersen §9's requirement for reproducible evaluation reports) |

## Curation threshold

Follow the same pattern as `add_language_column.py`: rows below a
threshold (proposed `NER_MIN_CONF`, to be calibrated later) are
flagged for manual review. Since `entity_id`/`entity_label` are
already curated facts from `references.csv`, this task does **not**
write back to `references.csv` itself — the output is a pure
addition layer (span annotations), kept separate from the source
table, per the general fact-checking / self-critique rule in
`CLAUDE.md`: a confidence score never substitutes for verification.

## Relationship to ner4andersen

| ner4andersen (full register, multi-stage) | hca-open-repo (this task) |
|---|---|
| Sources: editorial notes + printed indexes | Source/ground truth: `data/normalized/references.csv` (known page↔entity list) |
| Consolidated candidate record with `sources[]` | Span-annotation row per known page-entity link |
| Open entity discovery + external reconciliation (Wikidata/GND/VIAF/GeoNames) | No entity discovery — `entity_id` is already given; the task is grounding, not reconciliation |
| Human curation via OpenRefine + TEI `@ref` | Human curation of span annotations before any further use |
| Entity types: person, place | Same — person, place (derived from `entity_type` in `entities.csv` for the linked entities) |

This task is narrower than ner4andersen's Stage 0.5–1: there is no
harvest or consolidation phase, because the per-page entity list is
already curated in `references.csv`. The task corresponds most
closely to the reconciliation/validation logic ner4andersen applies
to already-proposed candidates (§7) — except here the candidate's
`entity_id` is fixed, and the only uncertainty is its location in
the text.

## Implementation (rule-based baseline)

`scripts/parsers/ner_page_grounding.py` implements the above as a
rule-based baseline (same style as `parse_person_gender.py`):
surname/given-name patterns for persons, label matching for places,
greedy non-overlapping span assignment per page, a cap of 5 matches
per entity. Output: `data/normalized/ner_page_grounding.csv` (all
proposal rows) and `data/normalized/ner_page_grounding_review.csv`
(rows below `--min-conf`, default 0.6).

**Coverage limitation:** `data/normalized/diary.csv` currently only
contains transcribed text for 751 of the 4,549 pages that appear in
`references.csv` — the remaining ~47,500 ground-truth rows cannot be
grounded yet and are explicitly skipped (reported separately in the
script's summary, not as `no_match`, since the absence of source
text is a different situation from a failed search attempt).

On the most recent run over the 751 available pages: 11,581 grounded
ground-truth rows, of which 5,145 `no_match` (44%), 3,912
`surname_only`, 491 `full_name_proximity` (highest confidence, 0.90),
483 `given_name_only` (lowest confidence, 0.30), and 1,550 place
matches. The high `no_match` rate reflects both OCR noise and the
fact that many registered people are referred to in the text by
title/pronoun/nickname rather than surname — the baseline only
catches literal surname/given-name occurrences and is deliberately
conservative rather than guessing.

## Entity linking — tasks and targets (authority files)

Grounding (above) only solves **internal** linking: string →
`entity_id` within the repo's own register. ner4andersen's full
architecture (§7 of `plan-v3.md`) goes further and reconciles each
`entity_id` against **external authority files**. In `hca-open-repo`
this step is implemented differently for each of the three entity
types in `entities.csv` — one is running in production, one has
partially run for a subset, one is only planned. Below is the
combined status, so it's explicit which authority targets actually
exist to link against right now, and which are still only a future
column.

| Entity type | Register (`category_h1`) | Count | Internal authority (target 1) | External authority (target 2) | Status | Implementation |
|---|---|---|---|---|---|---|
| `work` | VÆRK-REGISTER | 3,708 | `entities.csv` (`entity_id`, prefix `Reg`) | **Wikidata** (Q-number + Commons image) | Run for an artist-based subset (Murillo works etc.) | `scripts/parsers/wikidata_lookup.py` → proposal; `data/curated/works_wikidata.csv` → curated target |
| `place` | STED-REGISTER | 2,508 | `entities.csv` | **GeoNames** (primary) + Wikidata (secondary column) | Run for the SV14 subset (vol. XIV); the rest of the register not yet reconciled | `scripts/build_mockup/reconcile_sv14_geo.py` → `data/normalized/sv14_places_reconciled.csv` (target) / `..._ambiguous.csv` (unresolved) |
| `person` | PERSON-REGISTER | 10,228 | `entities.csv` | **VIAF** / **GND** (planned) | Not implemented — only mentioned as a future field | `docs/roadmap.md` §1.3 "Authority Integration" (VIAF, Wikidata, Getty ULAN, GeoNames, "Library authority IDs" as "future-compatible fields"); `docs/pipeline/stages.md` mentions OpenRefine reconciliation "against VIAF / Wikidata" as a curation step, not a running pipeline |

### Target 1 — internal authority: `entities.csv`

This is the register itself and applies equally to all three types:
every linking task (grounding as well as external reconciliation) is
anchored on `entity_id`. There is no competing internal id
namespace — all `entity_id` values carry the prefix `Reg`, and it is
`category_h1`/`entity_type`, not the shape of the id, that determines
register type (unlike `normalized_v092`, where person/place had
separate `P`/`L` prefixes — see
`docs/data-model/v0.92-structural-diff.md`).

### Target 2 — external authorities per type

**Works → Wikidata.** `wikidata_lookup.py` reconciles works against
the Wikidata artist's P170-related items and scores title similarity
+ collection (`P195`). The output is a **proposal** CSV, never a
direct write to `works_wikidata.csv` — a curator must confirm the
collection/location before it's admitted (cf. CLAUDE.md's
fact-checking rule: an artist often painted the same subject for
multiple collections, so title similarity alone is insufficient).

**Places → GeoNames (+ Wikidata).** `reconcile_sv14_geo.py` matches
the STED-REGISTER against `raw/SV14_places.xml` (a TEI place list,
already geocoded against GeoNames) via direct name matching and a
DA→EN alias via `rejser.tsv`. Ambiguous hits (same name, different
coordinates — e.g. "Lilienstein" in Saxony vs. a mis-tagged South
African entry) are **never** auto-applied, but are written to
`sv14_places_ambiguous.csv` for manual resolution. This covers only
volume XIV's place list; `place-typology.md` (§ external lookup,
around lines ~586 and ~758) points to the same GeoNames/GND-style
lookup as necessary for the rest of the STED-REGISTER, but it hasn't
been run at scale yet.

**Persons → VIAF / GND.** No running reconciliation exists.
`docs/roadmap.md` §1.3 lists VIAF, Wikidata, Getty ULAN, GeoNames and
"Library authority IDs" as **future-compatible fields** — i.e. an
intended but not-yet-built extension. If/when this is implemented, it
should follow the same proposal/curation separation as the other two
(a separate proposal CSV, never a direct write to `entities.csv`),
and — following ner4andersen's pattern of internal `gnd-*`/`geo-*`
registers ahead of external reconciliation — could usefully cache
candidate hits in a file like
`data/normalized/person_viaf_candidates.csv` rather than calling
VIAF/GND live on every run.

### Provenance target (not an authority, but related)

`data/normalized/kb_diary_links.csv` links each `(vol, page)` to the
corresponding live page at the Royal Danish Library
(`epub3.kb.dk/hcadag/...`). This is not a reconciliation target for
an entity, but a **source-provenance link** for the diary page
itself — the same role as the `sources[]` list in ner4andersen's
consolidated candidate record (§6). A future entity-linking output
(grounding or external reconciliation) should reuse this link as part
of its own provenance, e.g. as a `source_url` column pointing back to
the specific KB page the mention was found on.
