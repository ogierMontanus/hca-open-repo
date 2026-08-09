# BILLEDKUNST artist extraction and the Kunstner facet

`scripts/build_mockup/build_works_extra.py`'s `author_from()` fills the
`author` field of `mockup/data/works-extra.js` for every work. For most
wings that's just `person_derived` (or, failing that, the H2 category as a
weak fallback). BILLEDKUNST is different: person_derived alone covered only
**269 of 941 works (29 %)**, because most BILLEDKUNST titles were entered
as `"Subject (Artist, Collection, City)"` with the real attribution sitting
inside the title's own parenthetical rather than in a separate curated
field. `artist_from_billedkunst_title()` recovers it from there, bringing
coverage to **791/941 (84 %)** — enough for `billedkunst.html`'s "Kunstner"
facet (`data-facet-source="author"`, same mechanism as `bibliotek.html`'s
Forfatter facet and `teater-musik.html`'s Komponist/Forfatter facet) to be
worth adding.

## Why this needed a heuristic, not a straight parse

A first look at the data suggested a simple rule: split the first
parenthetical on commas, take the first piece. Checking it against the
actual 672 person_derived-less BILLEDKUNST titles turned up three ways
that's wrong:

1. **No artist at all.** Some titles read `"(Collection, City)"` with
   nothing to attribute — 27× `"M. borbonico, Napoli"`, 12× `"Capitol,
   Rom"`, etc. Taking piece 0 there promotes an institution to "author".
2. **Multiple parenthetical groups, artist not in the first one.**
   `"Tre Helgener (Benedikt, Flavia og Placidus) (Perugino, Vatikanet,
   Rom)"` lists the depicted saints first; the real artist is in the
   *second* group. 50 of 634 titles carry more than one group.
3. **A single bare piece can be either shape.** `"Aristokrati og
   Fattigfolk (Siegwald Dahl)"` (artist, no collection/city) and
   `"Alexander-Slaget (Pompeji)"` (bare place, no artist) are
   structurally identical — one comma-free parenthetical — and only
   distinguishable by what's *inside* it.

The fix: try every parenthetical group in the title, preferring one whose
**last piece is a real place name** (checked against every `entity_type ==
'place'` label in `entities.csv`, casefolded) — the strongest signal that
group is genuinely `"Artist[, Collection], City"` and not a subject list.
Only when no group has a place-confirmed tail does it fall back to the
first group whose leading piece still looks name-shaped. This is what
recovers "Perugino" from the Tre Helgener example above (group 2 ends in
"Rom", group 1 doesn't) and "Domenichino" from `"Adam og Eva (Arvesynden)
(Domenichino, Rospigliosi, Rom)"` (group 1's `Arvesynden` fails the
stoplist regardless).

## The name-shape screen (`_looks_like_artist`)

A candidate is rejected — returns `None` rather than a guess — if it:

- starts lowercase, starts with a digit, or contains a digit anywhere
  (`"2 Billeder"`, `"Exposición nacional 1862"`)
- contains `?` or `:` (`"la Bella?"`, `"nu: Eirene og Plutos"`)
- exactly matches a place label, or a curated stoplist entry (institution
  abbreviations — `uffizi`, `capitol`, `vatikanet`, `glyptoteket`,
  `m. borbonico` and its OCR-typo variant `m. bonbornico`, `fesch`,
  `libreria piccolomini`, `palazzo della ragione`, `raadhuspladsen`,
  `domkirken`; medium/technique words — `tegning`, `kopi`, `selvportræt`,
  `kultegning`, `fresko`, `karton`; mythological sculpture subjects —
  `pallas`, `hermes`, `satyren`, `hera farnese`, `ilioneus`; museum-room
  names — `aegineter-salen`, `apollo-salen`, `arco clementino`)
- contains one of those institution words as a whole token even inside a
  longer phrase (`"Mercato Nuovo og Uffizi"` → rejected on `uffizi`)
- starts with a Danish (`den`/`det`/`de`) or foreign (`il`/`la`/`le`/
  `das`/`die`/`der`/`el`/…) article, `"Palazzo "`, or `"Kopi "`
- ends in `kirke`/`kirken`, or contains `" fra "` (the `"X fra Y"`
  subject-description pattern, e.g. `"Apollo fra Capua"`)
- runs more than 5 words (real names in this data top out at 4:
  `"Ludwig Schnorr von Carolsfeld"`)

Every rule above exists because a specific title in this register tripped
it during development — none are speculative. The stoplist is small and
literal by design: broader fuzzy matching was tried and rejected once (see
below) for turning correct data into false negatives.

## person_derived can be wrong too — and this script can partially catch it

65 BILLEDKUNST works have a *non-empty* `person_derived` that is a prefix
of their own title — e.g. `person_derived = "S. Cecilia"` on the title
`"S. Cecilia (Carlo Dolci, Manfrin, Venezia)"`. That's the depicted saint,
not the painter; some upstream normalization step copied the subject into
the attribution field. Since `author_from()` checks `person_derived`
first, the parenthetical-extraction logic below never even ran for these
— they looked "already handled", just wrong.

`_person_derived_is_title_subject()` catches the specific, checkable shape
of this bug (title starts with a `person_derived` segment) and, only when
`artist_from_billedkunst_title()` recovers something real from the title's
own parenthetical, uses that instead. All 65 were checked by hand before
shipping this — every one recovers a clean, plausible artist (`"Carlo
Dolci"`, `"Rubens"`, `"H. V. Bissen"`, …), including the trickiest case,
`person_derived = "H. V. Bissen"` on `"H. V. Bissen (Carl Peters)"` — H. V.
Bissen is a real, prolific sculptor elsewhere in this same register (17
other works), so a name-shape check alone couldn't have flagged this one;
only the title-prefix structural check could.

**Known remaining gap:** the prefix check only catches the subject when it
*leads* the title. A subject named mid-title —
`"...Ruinerne af Byen Nymfa (Harald Jerichau)"` with `person_derived =
"Byen Nymfa"` — isn't a title prefix and slips through. 5 such works are
known as of this writing (`Byen Nymfa`, `Dorothea Melchiors` ×2, `H. C.
Andersen` as a gift-recipient mistaken for the artist, `Jupiters Ørn` ×2,
`S. Michaels-Kirken`). Widening the check to "title contains
person_derived anywhere" was tried and reverted: a *correct*
person_derived is, by construction, also a substring of its own title (it
usually came from that same parenthetical originally), so that version
flagged nearly everything as suspect instead of isolating the handful of
real bugs. Fixing these 5 is a data-curation task, not an extraction-logic
one — the same category as the 158 multiline person_derived values
described next.

## Multiline person_derived (all wings, not just BILLEDKUNST)

158 works across every wing carry a `person_derived` with an embedded
newline joining two names from the upstream normalization step — e.g.
`"A. W. Moltke\nH. V. Bissen"` (a portrait bust's subject and its sculptor
both landed in the one field). Which segment is "the" author isn't
reliably position-dependent: it's the first name in some rows, the last in
others. `author_from()` doesn't try to guess a winner — it normalizes the
value to a comma-joined, readable string (`"A. W. Moltke, H. V. Bissen"`)
without dropping either name. This is a straight readability fix, not an
attribution fix; it also improves the pre-existing Forfatter and
Komponist/Forfatter facets on `bibliotek.html` and `teater-musik.html`,
which previously rendered these as broken-looking multi-line facet
entries.

## What's institutionally excluded, not missing

BILLEDKUNST works under H3 "Museer og Samlinger" (museums/collections as
works in their own right — e.g. "Uffizi", "Louvre") are skipped entirely
before extraction even runs: they're not authored works, so `author_from()`
returns `None` for them by design, not as a heuristic failure.

## Verifying a rebuild

```
python3 scripts/build_mockup/build_works_extra.py
```

prints a coverage line:

```
BILLEDKUNST author coverage: 791/941 (84%)
```

To eyeball the full recovered author list (catches regressions a
percentage alone would hide — e.g. a new false positive that happens to
replace an old one, keeping the count identical):

```python
import json
text = open('mockup/data/works-extra.js', encoding='utf-8').read()
data = json.loads(text.split('const WORKS_EXTRA = ', 1)[1].rstrip('\n').rstrip(';'))
billedkunst = {rid: w for rid, w in data.items() if w['h2'].upper() == 'BILLEDKUNST'}
authors = sorted({w['author'] for w in billedkunst.values() if w['author']}, key=str.casefold)
print(len(authors), 'distinct artists')
```
