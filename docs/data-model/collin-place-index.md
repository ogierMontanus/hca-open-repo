# Collin correspondence — printed place-name index (step 1)

Status: place names digitized, standalone (not yet mapped to the letter edition) · 2026-08-24

Step 1 of the task recorded in this project's memory (2026-08-24, "queued
Collin letter index"): digitize the printed **STED-REGISTER** (place-name
index) from the register volume of *H. C. Andersens Brevveksling med
Edvard og Henriette Collin* (ed. H. Topsøe-Jensen), and **stop there** —
do not yet map these entries onto the six volumes of the letter edition
itself. This document covers exactly that first step.

It follows on from [`correspondence-integration.md`](correspondence-integration.md)
§6, which identified that BrevBasen.csv (the flat correspondence database)
carries essentially no place data (1.2% of rows) and that closing that gap
requires digitizing indexes to the printed letter editions — a new
indexing task structurally identical to the diary's own `references.csv`,
not a cleanup of the existing correspondence CSV.

---

## 1. Source and scope

`C:\Users\nh\Documents\GitHub\breve-data\andersen-hc_breve-collin_6.pdf`
(a sibling checkout, 164 pages, ABBYY FineReader PDF 15 OCR layer,
two-column layout, 450×565pt pages).

**Extracted range**: printed index pp. 64–77 = PDF pages 70–83. The
6-page front-matter offset was not assumed — it is confirmed from the
printed page numbers embedded in the OCR text itself: PDF page 71 carries
"65", PDF page 83 carries "77", and PDF page 84 immediately opens with
"IV. PERSON-REGISTER" — so the STED-REGISTER section is exactly and only
these 14 pages. Its own opening line reads "København ikke medtaget."
("Copenhagen not included") — a deliberate editorial omission, not a gap
in the extraction.

**Script**: [`scripts/correspondence/extract_collin_place_index.py`](../../scripts/correspondence/extract_collin_place_index.py),
PyMuPDF (`fitz`), stdlib otherwise.

**Output**: [`data/curated/collin_letters_place_index.csv`](../../data/curated/collin_letters_place_index.csv)
(623 rows) and a companion
[`data/curated/collin_letters_place_index_review.csv`](../../data/curated/collin_letters_place_index_review.csv)
(13 rows flagged for human review — see §5).

---

## 2. Extraction method

### 2.1 Column order

The source is two-column, and PyMuPDF's block detection separates the
columns cleanly (confirmed: block bounding boxes fall into two consistent
x-ranges, ~45–222pt and ~231–409pt on a 451pt-wide page). Reading order is
**left column top-to-bottom, then right column top-to-bottom**, per page —
verified against the real file by checking that a page's last
right-column entry is alphabetically adjacent to the next page's first
left-column entry (page 69's right column ends "Baden-Baden"; page 70's
left column opens "Bamberg").

Two categories of noise block are discarded before column assembly:
page-number footers/headers (narrow, near the top margin) and a printer's
signature mark seen on 2 of the 14 pages — a tiny bottom-margin
annotation (e.g. "VI,5") used for collating printed sheets, not index
content.

### 2.2 Entry boundaries

A printed index entry always opens with the place name flush left,
capital-then-lowercase (e.g. "Aabenraa"); continuation lines of a wrapped
citation list never do — they open with a digit or an all-caps roman
numeral. That distinction is a reliable, almost entirely unambiguous
entry-boundary signal, with two exceptions found and handled:

- A garbled OCR reading of "III" (`Ill`, `HI`, `H1`, `Il`, `IH`) is
  capital-then-lowercase-shaped and would otherwise be mistaken for a new
  entry. One real occurrence was found this way (a continuation of
  "Livorno"); such tokens are explicitly excluded from the entry-start
  check.
- The character class for "lowercase second letter" initially missed six
  accented letters actually used in this index — ö (Göteborg, Jönköping,
  Köln, Königstein, Mönch), ä (Mälaren), î (Nîmes) — each of which
  silently merged into the *previous* entry until added. Found
  systematically, not by inspection: every (capital, second-letter) pair
  that occurs in the source was enumerated and checked against the
  character class, rather than trusting a first pass that looked
  plausible. Fixing it recovered 7 entries (623 vs. 616).

### 2.3 A convention borrowed from this project's own person register

Four entries file a definite article at the *end* of a multi-word name for
alphabetization — `Havre, Le` (Le Havre), `Brenets, Les` (Les Brenets),
`Travers, Val de` (Val de Travers), `Mönch, Der` (Der Mönch) — the exact
same inversion this project's own PERSON-REGISTER uses for
"Efternavn, Fornavn". A naive first-comma split reads the article as the
start of the citation instead (`Mönch` / `Der, IV, 23.`); a small closed
set of known articles (Le, Les, La, Der, Die, Das, Den, Det, Val de) is
checked at that position and re-merged into the name when found.

### 2.4 What was *not* fully solved: this book's own sort order

Danish string sorting elsewhere in this project follows a documented
convention (CLAUDE.md: `Intl.Collator('da')`, "Aa" at word-start folds to
"Å", order a…z·æ·ø·å). Checking every entry's position against its
neighbours (a printed index cannot be out of its own order, so any
violation is a signal) shows this 1950s–60s printed index does **not**
follow that convention uniformly:

- **V and W are treated as one letter for sorting** (Bern before Bex
  before Bex-adjacent W-entries is fine, but e.g. Weimar sorts into the
  same run as Vejle — 8+ instances, entirely consistent throughout).
- Some Å/Aa-initial entries sort as if spelled "Aa" near the start of the
  alphabet (Årsta correctly falls between Aarhus and Aarøsund only if Å is
  read as "Aa"), which resolved 3 of the original 20 flagged positions —
  but **not consistently**: `Sæby` / `Såby` still sits the "wrong" way
  round under that same rule, so this is not a single clean mechanical
  rule that can be safely automated further.

**8 alphabetical-order questions remain unresolved** after applying every
convention that could be confirmed against multiple independent examples;
they are listed in §5 rather than forced into a rule that would silently
mis-sort other entries.

---

## 3. Output columns

`data/curated/collin_letters_place_index.csv`:

| Column | Meaning |
|---|---|
| `place_name_raw` | As extracted, before any correction |
| `place_name_clean` | After the two high-confidence corrections in §4; identical to `place_name_raw` for every other row |
| `name_corrected` | `yes` if a correction was applied |
| `correction_note` | Why, for the 2 corrected rows |
| `parenthetical` | A qualifier printed in parentheses right after the name, e.g. "Baden **(ved Wien)**" — kept separate from the citation |
| `see_also` | The target of a "se X" redirect (4 rows — Aalsgaarde, Ellekilde, Felsenstein, Såby); `citation_raw` is empty for these |
| `citation_raw` | The volume+page citation exactly as extracted (dehyphenated/rejoined across the original line wraps, otherwise untouched) |
| `citation_ocr_quality` | `clean` (575) / `low` (25) / `medium` (9) / `high` (10) / `n/a` (4, the see-also rows) — a heuristic count of characters that cannot be part of a well-formed citation (stray letters, `°'’^»$*`) |
| `citation_ocr_noise_chars` | The specific noise characters found, for triage |

**Citations are preserved as printed, not corrected.** Per the task's own
scope boundary (don't map to the letter edition yet), and because
individual garbled digits inside a long page-number list cannot be
resolved with confidence from the OCR text alone — doing so would mean
guessing a specific corrected number without the source page image to
check it against, which is exactly the failure mode this project's
fact-check discipline (CLAUDE.md) exists to prevent. The `citation_ocr_quality`
flag exists so a later, image-verified pass knows where to start.

---

## 4. Place-name corrections applied

Two, both cross-checked two independent ways before being applied — not
just "this looks plausible":

| Raw | Corrected | Why |
|---|---|---|
| Milona | **Milano** | n/o transposition; the entry's own high, repeated citation count matches Andersen's well-documented, repeated Milan visits; alphabetical position is unaffected by the correction either way |
| Inin | **Irun** | Alphabetical-position proof, not just a plausible guess: as printed, "Inin" would sort *before* "Interlaken" — but it is placed *after* Interlaken and *before* Ischia in the source. "Irun" is the only reading beginning with a letter run that both looks like the OCR output and lands correctly in that exact slot (Int- < Iru- < Isc-) |

Both corrections are visible in the CSV as `place_name_raw` vs.
`place_name_clean`; nothing was silently overwritten.

---

## 5. Flagged for human review (not corrected)

`data/curated/collin_letters_place_index_review.csv` — 13 rows: 3 for a
place name that could not be confidently corrected, plus 10 for citations
whose OCR-noise count crossed the "high" threshold (long, heavily-cited
entries — Bregentved, Hamburg, Hellebæk, Holsteinborg, Korsør, Leipzig,
Odense, Paris, Portugal, Rom — where a single missed digit is more costly
because of how many citations they carry).

**Place names left uncorrected:**

- **Giion** — sorts after "Glasgow" in the source, which no plausible
  reading beginning "Gi-" or "Gl-" explains. The surrounding Spain/Portugal
  citations make "Gijón" plausible, but unlike Irun there is no
  alphabetical-position proof for it, so it is flagged rather than
  corrected.
- **Giommen** — the adjacent entries (Drammen, Kongsvinger, Sandviken) all
  cite the *identical* page "IV, 188", strongly suggesting this is another
  stop on the same 1871 Norway itinerary, but no specific corrected
  spelling could be confirmed.
- **Mysunde-adjacent ordering** — "Mälaren" prints after "Moen" despite
  sorting before it under every convention checked; no OCR misreading was
  found that resolves the inversion, so it may be a genuine ordering slip
  in the source rather than an OCR error.

Plus the 8 unresolved alphabetical-order cases from §2.4, for anyone
later verifying this section against the source page images.

---

## 6. What comes next (out of scope here, by design)

Per the task's own boundary: **not attempted** — resolving these place
names against `data/normalized/entities.csv`'s STED-REGISTER (many will
match existing diary-register places by label: Odense, Paris, Rom, Wien,
… are already there), and mapping the citations onto the six volumes of
the letter edition itself. Both are natural follow-ups once this
standalone place list has been reviewed, not steps taken now.
