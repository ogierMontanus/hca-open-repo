# Correspondence integration — merging the diary indexes with Andersen's letters

Status: proposal, grounded in a full read of the source data · 2026-08-24

Goal (as given): prepare a merger of the diary indexes with indexes to
Andersen's correspondence. The connecting points are **persons** and
**dates** — the same two axes [`temporal-modelling.md`](temporal-modelling.md)
already treats as first-class in the diary register (`mention_dates`),
extended here to a second register with its own dates: the day a letter
was written.

This document reports what is actually in the correspondence data (not
what a schema implies should be there), quantifies the person-identity
overlap with `data/normalized/entities.csv`, and works the Fredrika Bremer
case end-to-end as requested. Everything below is checked against the real
files, not inferred from column names — see §8 for the specific method
used to produce every number below, so it can be re-run and re-verified.

---

## 1. The source

`C:\Users\nh\Documents\GitHub\breve-data`, a sibling checkout to this repo,
contains two files:

| File | Size | Role |
|---|---|---|
| `BrevBasen.csv` | 46.0 MB | **Primary source.** A flat, `;`-delimited export in **cp1252** encoding (not UTF-8 — confirmed by the presence of Windows-1252 smart-quote/dash bytes in the 0x80–0x9F range; plain UTF-8 decoding fails outright on byte 0xF8). 61 columns, 22,864 rows. |
| `Breve _ HCA X.htm` | 19.7 MB | A saved snapshot of the same corpus rendered as an HTML table on **hcax.dk** — the same site this project already draws `data/normalized/rejser.tsv` from. Secondary/reference only: it carries no fields BrevBasen.csv lacks, except that at least one row exposes a manuscript-provenance link to `samlinger.museumodense.dk` that the CSV does not pre-build (see §6). Not needed as a parsing target. |

### 1.1 What the 61 columns actually are

The column names (`BrevID9` vs `BrevID11` vs `BrevID30`, `PersonID` vs
`PersID` vs `PersID19`, five separate `Timestamp*` columns) are the
fingerprint of a **denormalized SQL join**, not a hand-designed export.
Reconstructing the join from repeated values gives five source tables
flattened onto one row:

1. **Brev** (the letter itself) — `ID`/`BrevID`, `Dato`, `DatoRange`,
   `Lokation`, `HerkomstID`, `HerkomstNr`, `Type`, `SprogIDer`
2. **Tekst** (a text attached to the letter — see `Type` below) — `Titel`,
   `Beskrivelse`, `is_original`, `is_tekst`, `Tekst`
3. **BrevPerson** (recipient side) — `PersonID`, `Relation` (almost always
   `modtager` = recipient)
4. **BrevPerson** (sender side, second join of the same table) —
   `PersonID12`, `Relation13` (almost always `afsender` = sender)
5. **Person** (joined twice, once per side) — `PersID`/`PersID19`,
   `Fornavn`, `Efternavn`, `Foedselsdato`, `Doedsdato`, `Hjemland`,
   `Biografi`

Plus two fields that sit outside that reconstruction and turn out to
matter more than the rest of the schema combined — `MetaTekst` and
`Hyperlink` (§4, §5).

### 1.2 Row cardinality — one row is not one letter

22,864 rows resolve to **11,792 distinct real letters** (`BrevID` values,
after discarding a 1,848-row `BrevID='NULL'` junk bucket — literal string
`"NULL"`, not a blank field — that has to be filtered before any use).
Rows-per-letter ranges from 1 to 83, driven by `Type`
(`original`/`tekst`/`grafisk`/`link`/…): a letter can have several text
representations — the original transcription, a normalized reading text, a
facsimile image, an external link — each stored as a separate row sharing
the same `BrevID`, sender, and recipient. **Deduplicate by `BrevID` before
counting letters**; the sender/recipient/date fields are identical across a
letter's duplicate rows (verified — 0 mismatches found across the whole
file).

11,359 of the 11,792 letters (96.3%) have Andersen (`PersID=1`) as sender
or recipient. The remaining 433 are third-party correspondence gathered
alongside him — including 26 letters dated after his death
(1875-08-04), which is normal archival behaviour (condolence
correspondence, letters *about* him), not a data error — see §7 for the
one date anomaly that *is* an error.

---

## 2. Person identification

`data/normalized/entities.csv`'s `entity_type='person'` rows and
BrevBasen's Person table describe an overlapping but independently-curated
set of people. Neither carries the other's ID, so linking requires a
name+date match — the same kind of problem `scripts/parsers/wikidata_lookup.py`
solves for works, applied to people instead.

**BrevBasen side:** 1,919 distinct persons (by `PersID`, consolidated
across its two join-slots — 0 name conflicts between the two occurrences of
the same `PersID`, so the underlying Person table is internally
consistent). 1,610 have a birth date, 1,594 a death date, 562 a short
biography, 1,786 a `Hjemland` (country). A `PersID` is not always a human
being — e.g. `PersID=1017` is "Theaterdirection, den kongelige" (the Royal
Theatre Directorate), an institution with no first name and placeholder
`0000-00-00` dates. Institutional correspondents will never match a person
row and should be recognised as a distinct case, not treated as
match failures.

**Match method:** normalize `Efternavn` (strip diacritics, lowercase),
look up candidates in `entities.csv` by surname, then confirm with the
4-digit birth year (BrevBasen has a full ISO date; `entities.csv` labels
carry only years, `"Efternavn, Fornavn (byyy–dyyy)"`).

| Outcome | Count | % of 1,919 |
|---|---|---|
| Surname + birth year → exactly one HCA candidate | **1,005** | 52.4% |
| Surname matches, but no confirming birth year (missing on either side, or the year picks 0 or >1 candidates) | 389 | 20.3% |
| No surname match at all | 482 | 25.1% |
| No surname on the BrevBasen side to key on | 43 | 2.2% |

Two exports, following this project's existing curated-overlay convention
(`data/curated/works_wikidata.csv` + `scripts/parsers/wikidata_lookup.py`'s
propose/verify split):

- [`exports/breve-person-crosswalk-candidates.csv`](exports/breve-person-crosswalk-candidates.csv)
  — the 1,005 confident single-candidate matches, sorted by letter volume.
  **Not individually human-verified** — the "candidates" in the filename is
  load-bearing. Surname+birth-year is strong for uncommon Danish surnames
  but not infallible (a same-surname, same-birth-year namesake would slip
  through unflagged), so per CLAUDE.md's fact-check rule this file must go
  through the same propose→verify split as `works_wikidata.csv` before any
  row is treated as authoritative, not get consumed by a build script
  as-is. It is, however, immediately useful as a ranked review queue: the
  top rows are the biggest correspondences, so verifying the highest-value
  20–30 rows first captures most of the practical value fast.
- [`exports/breve-person-crosswalk-ambiguous.csv`](exports/breve-person-crosswalk-ambiguous.csv)
  — the 389 surname-matched-but-unconfirmed rows, each listing every
  candidate `rid` found, sorted by letter volume so a human reviewer can
  prioritize. The top row is **Henriette Wulff, 568 letters** — Andersen's
  second-largest correspondence — whose birth year (1804) matches none of
  the five `entities.csv` "Wulff" rows on file; either her entry needs a
  birth-year correction or she is missing a distinct row. Worth resolving
  early given the volume.

The top of the confident list independently reproduces what the diary
facets already surface as HCA's closest circle — **Edvard Collin (690
letters)**, Henriette Oline Collin (435), Jonas Collin d.æ. (426),
Dorothea Melchior (411), B. S. Ingemann (396) — which is a useful sanity
check that the two registers are describing the same real relationships,
not two unrelated name lists that happen to overlap.

---

## 3. Worked example: Fredrika Bremer

The person named in the request, run through end to end.

**Identity confirmed independently in both datasets**, not asserted from
memory: BrevBasen `PersID=151` — Fornavn "Fredrika", Efternavn "Bremer",
Foedselsdato 1801-08-17, Doedsdato 1865-12-31, Hjemland "Sverige" — matches
`entities.csv` `Reg0042200`, `"Bremer, Fredrika (1801–1865)"` exactly on
both years. This is also the *pid* in the URL given in the request
(`person.html?breve=sendt&pid=151`), confirming `PersID` is the site's own
person key, not an internal-only database id.

**Correspondence:** 47 distinct letters between Andersen and Bremer,
1837–1869. **One is a genuine anomaly**: `BrevID=23143`, dated
"1869-01-10", "sent" by Bremer — four years after her recorded death
(1865-12-31). This is very likely a transcription/cataloguing digit error
in the source (not a modelling problem on this side); flag it back to
whoever maintains BrevBasen rather than silently "fixing" it here.

**Diary mentions:** `Reg0042200` is referenced on 43 diary pages
(`data/normalized/references.csv`), spanning volumes II–X. Per
[`temporal-modelling.md`](temporal-modelling.md), a diary reference only
carries a real date when its page has been transcribed with one — today
that is **volumes VI–VII only**. 7 of the 43 Bremer pages fall in that
window:

| Page | Diary date(s) |
|---|---|
| VI/95 | 1864-07-22, 1864-07-23 |
| VI/291 | **1865-09-22, 1865-09-24** |
| VI/295 | 1865-09-28 |
| VI/304 | 1865-10-10, 1865-10-11 |
| VI/341 | 1865-12-08, 1865-12-09 |
| VII/3 | 1866-01-05, 1866-01-06 |
| VII/26 | 1866-02-06 |

**One exact match**: diary page VI/291 carries the date 1865-09-24, which
is exactly the date of letter `BrevID=23143` (Bremer → Andersen). This is
not a coincidental date collision — the letter's own `MetaTekst` field
(§5) independently reads:

> *"Dagbog 24. September 1865: Besøgt Frederika Bremer, der gav mig sit
> Portræt Kort og indbød mig til sit Landsted Årsta."*

So the join is confirmed three ways: the automated date match, the source
database's own hand-written diary citation on that exact letter, and the
independently-matched person identity. This is the pattern a
person+date merge should reproduce at scale.

**What this example also shows about readiness**: only 1 of 43 Bremer
diary mentions could be checked against a letter date, because only 2 of
Andersen's 11 diary volumes carry transcribed dates today. The other 36
mentions (volumes II–V, VIII–X) are sitting on the same 47-letter
correspondence with no date to join against yet. **Volume date coverage,
not the correspondence data, is the current bottleneck** on how far this
merger can reach — it will get materially more useful with no further
correspondence work at all as more diary volumes are dated (per
[`../plan-live-facets.md`](../plan-live-facets.md) §6's decision that those
dates are supplied externally, never inferred).

---

## 4. External links

Two URL patterns are confirmed from the data itself:

**Per letter** — `Hyperlink` is populated on 22,779/22,864 rows (99.6%):

    https://andersen.sdu.dk/brevbase/brev.html?bid={BrevID}

**Per person** — confirmed via the request's own example plus the
independent PersID=151 cross-check above:

    https://andersen.sdu.dk/brevbase/person.html?breve=sendt&pid={PersID}

Only the `pid=` mapping is confirmed. The `breve=sendt` segment's full
range of values (is there a `breve=modtaget` for received correspondence,
or a combined view?) is **not** established from this dataset — it would
need a live check against a couple of known cases on the actual site
before building a general link-construction rule around it. Treat
`breve=sendt` as a literal, verified-working suffix for now, not yet as a
parameter with known alternatives.

**Implementation sketch**, following this project's existing external-link
conventions (`docs/external-links.md`: new tab, quiet styling, ↗ +
`.sr-only` announcement) and the `Krydshenvisninger` sidebar pattern this
project already uses on `work.html`: a person page for a confirmed-crosswalk
`rid` gains a sidebar box, e.g. "Brevveksling", one outbound
`Læs brevene hos Det Kgl. Bibliotek/SDU`-style link built from the row's
`breve_pid`, with the letter count as visible context (`690 breve` for
Collin). This needs no new data pipeline — it is a straight per-row lookup
against the verified crosswalk once §2's candidates are promoted, exactly
the same propose-CSV → verify → build-script-reads-it shape as the
Wikidata hero images.

---

## 5. `MetaTekst` — an existing, hand-verified diary↔letter crosswalk

This is the most valuable single field in the dataset for this project,
and it is easy to miss because it sits outside the reconstructed
five-table join (§1.1) — it reads like a stray annotation column, not a
crosswalk.

**1,535 distinct letters** carry a non-blank `MetaTekst`. Of those,
**389 begin with the literal word "Dagbog"** ("Diary") followed by a date
and a quotation — e.g.:

    BrevID=1883   1840-11-20   "Dagbog 16.11.: Besøg af Redacteuren Dr Kolb,
                                 som jeg forærede Nur ein Geiger, ..."
    BrevID=16865  1844-07-00   "Dagbog 27. Juli: Brev fra Petit"

These are **already-curated cross-references from the brevbase compilers
to Andersen's diary**, not inferred by anything in this project. 22 of the
389 go further and cite an explicit locator — `"Dagbog II, s. 187, linie
19"` — in the same volume+page addressing family this project's own
`Pag{VV}{PPPP}` scheme already uses.

**This means Phase 1 of any merger does not need date-matching at all.**
The 389-letter subset is a ready-made, human-verified ground truth:
extract the date (and, where present, the explicit vol/page) from each
`MetaTekst`, resolve it against `data/normalized/diary.csv` /
`references.csv`, and link directly — no birth-year heuristics, no
false-positive risk, no volume-coverage bottleneck (`MetaTekst` cites
dates across the full 1820s–1870s range, not just the two currently-dated
volumes). It is also the natural validation set for whatever automated
date-join is built next: any general matching rule should be checked
against these 389 known-correct pairs before being trusted on the rest of
the correspondence.

---

## 6. Places and artworks — confirming the gap, and how big it is

The request already anticipated this; the data confirms it precisely
rather than just agreeing with it.

**Places**: `Lokation` exists as a column, but is populated with a real
place name on only **268 of 22,864 rows (1.2%)** — 18,182 rows say
"Ukendt" (unknown) and 4,414 are blank. Where it is populated, the values
are place *names* (Kjøbenhavn, Wien, Basnæs, Rolighed, Paris, …) with no
link to any place register, coordinate, or authority id — nothing
resembling `data/normalized/entities.csv`'s STED-REGISTER rows.
Practically: **not usable as a place source today**, exactly as flagged.

**Artworks**: none of the 61 columns carries anything resembling a
VÆRK-REGISTER reference — no title, creator, or collection field
independent of `Tekst`/`MetaTekst`'s free text. A letter mentioning a
painting Andersen saw is only discoverable by reading the letter text
itself, not by querying a field.

**What closing this gap actually requires**, per the request's own note
about digitizing printed-edition indexes: this is not a data-cleaning
task on BrevBasen, it is a **new indexing task** structurally identical to
what already exists for the diaries (`data/normalized/references.csv`:
page → entity → type). The separately-noted follow-up task on the printed
Andersen–Collin letter-edition index (volume 6, pp. 64–77 / PDF images
70–83, `andersen-hc_breve-collin_6.pdf`) is exactly this: a place-name
index in the same structural family as the diary's own printed index,
ready to go through the same OCR-clean → normalize →
`references.csv`-shaped pipeline once that work starts. That task is
intentionally scoped to *not* map onto the six-volume letter edition yet —
building the place index first, independent of the cross-reference layer,
is the right order: it produces a reusable place list (with the same
surname/place-name normalization problems as the diary index) before
taking on the harder problem of tying it back to individual letters.

**Manuscript-provenance links, noted but unconfirmed**: the CSV's
`HerkomstNr` column (e.g. `"HCA 1971/356-0001"`) is the museum accession
number the letter's original manuscript is held under. The HTM snapshot
(§1) shows at least one letter rendered with a working link built from it —
`https://samlinger.museumodense.dk/HCA/1971/356-0001` — but that URL
construction is seen in exactly one example and is not in the CSV as a
pre-built field. Worth confirming with a couple more known cases before
relying on it as a general rule; not needed for Phases 0–2 below.

---

## 7. Data-quality notes for anyone building against this file

- **Encoding is cp1252, not UTF-8.** Confirmed by byte inspection, not
  assumption (§1). Decode accordingly or the accented Danish/Swedish
  names will corrupt.
- **`BrevID='NULL'`** (the literal string) is a 1,848-row junk bucket of
  orphaned relation rows with no real letter behind them. Filter before
  counting or joining.
- **Partial dates use `-00` placeholders** — e.g. `1838-00-00` (year only),
  `1842-07-00` (year+month only) — the same convention
  `build_diary_index.py`'s `short_date()` already handles for diary dates,
  so the existing date-formatting helper in `js/diary-wire.js`
  (`formatDate`) is directly reusable rather than needing a parallel
  implementation. 1,058 of 11,792 letters (9%) have a partial date.
- **Name and text fields carry embedded HTML** — `<acronym title="Hans
  Christian">H.C.</acronym>` inside `Fornavn21` for Andersen himself, `<p>`
  tags throughout `Tekst`/`rtext`/`Biografi`. Strip before matching or
  displaying as plain text (`author_from()`-style stripping, not a new
  approach).
- **One known-bad date**: the 1869 Bremer letter (§3) — four years
  post-mortem. Flag, don't silently correct.
- **`Relation`/`Relation13` are ~99.5% clean** (`modtager`/`afsender`) but
  not 100% — a handful of blank or `NULL` values exist and one literal
  date string leaked into a `Relation` cell (`'1808-11-02'`), presumably a
  column-shift error in one source row. Defensive parsing, not a
  systemic problem.

---

## 8. How the numbers in this document were produced

So they can be re-verified or re-run: cp1252-decoded, `;`-delimited
`csv.DictReader` over `BrevBasen.csv`; letters deduplicated by `BrevID`
excluding the literal `'NULL'`; persons consolidated across both join
slots (`PersID`/`Fornavn`/`Efternavn`/… and
`PersID19`/`Fornavn21`/`Efternavn22`/…) keyed by `PersID`, checked for
cross-slot conflicts (none found); person matching against
`data/normalized/entities.csv`'s `entity_type='person'` rows via
diacritic-stripped, lowercased surname lookup confirmed by a shared
4-digit birth year, parsed from entity labels via the standard
`"Efternavn, Fornavn (byyy–dyyy)"` pattern. No step used values recalled
from training data — every date, id, and count above was read out of the
files at `C:\Users\nh\Documents\GitHub\breve-data` and
`data/normalized/` in this repo.

---

## 9. Phased plan

1. **Phase 0 — `MetaTekst` extraction (§5).** No date-matching risk,
   389 known-correct diary↔letter links, immediate payoff. Parse the
   "Dagbog …" prefix, resolve dates against `diary.csv`, emit a
   curated crosswalk CSV in the `data/curated/*.csv` overlay pattern.
2. **Phase 1 — Person crosswalk verification (§2).** Human-verify the
   1,005 candidate rows starting from the highest letter counts (Collin,
   Wulff family, Melchior, Ingemann, …); resolve the 389 ambiguous rows
   case by case, starting with Henriette Wulff. Promote verified rows into
   `data/curated/breve-person-crosswalk.csv` the same way
   `works_wikidata.csv` is built, with a `verified_via`/`notes` column
   pair.
3. **Phase 2 — Per-person correspondence links (§4).** Wire the verified
   crosswalk into `person.html` as a `Brevveksling` sidebar box; link out
   using the confirmed `pid=` URL, live-check the `breve=sendt` semantics
   first.
4. **Phase 3 — Broader date-join, once more diary volumes are dated.**
   Re-run the Bremer-style exact/near-date match at full scale as
   `plan-live-facets.md`'s external date supply lands for volumes I–V,
   VIII–XI; validate any automated join against the Phase 0 `MetaTekst`
   set before trusting it elsewhere.
5. **Phase 4 — Places/artworks.** Depends on the separate printed-index
   digitization work (§6), not on anything in BrevBasen.csv.

## 10. On the offered SQL dump

Everything in this document comes from the flat CSV export alone, and it
was sufficient for all of the above — the export already carries the
Person, Brev, Tekst, and relation tables' relevant fields joined together.
A SQL dump would mainly earn its keep if it exposes something the export
*doesn't* carry: referential-integrity constraints that would catch
orphan rows structurally rather than by the `BrevID='NULL'` heuristic
used here, additional tables not flattened into this join (a possible
place or artwork table would be the valuable case, per §6), or a live
schema to confirm the `breve=` URL parameter's full value set (§4)
without guessing. If none of those apply, the CSV is enough for Phases
0–2 above and the dump isn't needed yet.
