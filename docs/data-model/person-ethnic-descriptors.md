# Person ethnic/national descriptors

`scripts/parsers/parse_person_ethnic_descriptors.py` scans the 10,228
PERSON-REGISTER rows in the canonical Repository workbook
(`data/raw/HCA REPOSITORY V0.82/HCA-Repository V0.82.xlsx`, sheet
`Registry`) and identifies ethnic/national adjectives (*svensk*, *tysk*,
*jødisk*, …) in each row's `RegistryDescription` — the free-text subfield
that follows the entry's name/date-range in `RegistryTitle`
("Aabye, Johan Peter (1818–1880). *Distriktslæge i Flensborg…*").

Run it with:

```
python scripts/parsers/parse_person_ethnic_descriptors.py
```

Outputs:

| File | Contents |
|---|---|
| `data/normalized/person_ethnic_descriptors.csv` | Every match: entity, matched word, nationality, category, position, referent hint |
| `data/normalized/person_ethnic_descriptors_review.csv` | Every unmatched `-sk`/`-iske`-shaped word, ranked by frequency, with one example each — the ongoing edge-case queue |

Current run: **2,708 matches on 2,519 of 10,228 rows (24.6 %)**.

## The adjective table

`data/curated/ethnic_adjectives_da.csv` is the compiled list — 94
nationality/ethnicity keys, 221 surface-form spellings, one row per key
with a `category`. It is **hand-curated but corpus-grounded**: every
entry was checked against an actual frequency scan of the register
before being added (see "Method" below), not assembled from memory
alone.

Categories:

| Category | Meaning | Examples |
|---|---|---|
| `national` | modern nation-state demonym | dansk, tysk, fransk, svensk, italiensk, amerikansk |
| `german_state` | pre-1871 German polity (Germany wasn't unified until 1871, well inside the diary period) | preussisk (74 hits — the most frequent single form after the "big five"), sachsisk, bayersk/bayrisk, hannoveransk, oldenburgsk/oldenborgsk, mecklenburgsk, westfalsk, württembergsk, thüringsk |
| `border_region` | the contested Schleswig-Holstein(-Lauenburg) duchies — central to the wars of 1848–51 and 1864 | slesvigsk, nordslesvigsk, sønderjydsk, slesvig-holstensk, holsten-lauenborgsk |
| `regional_danish` | Danish regional/city demonym, not a foreign nationality | jysk/jydsk, sjællandsk, fynsk, københavnsk/kjøbenhavnsk |
| `colonial` | Danish colonial-era territorial demonym | dansk-vestindisk (Danish West Indies), grønlandsk |
| `historical_polity` | a historical (often ancient) polity, not a modern nation | romersk, østromersk, angelsaksisk, attisk/atheniensisk, bøhmisk, veneziansk, neapolitansk |
| `regional_foreign` | a foreign sub-national region/identity | flamsk (Flemish), provencalsk, tyrolsk, katalansk |
| `ethnolinguistic` | defined by language/dialect rather than a state | plattysk (Low German), germansk, slavisk, frisisk |
| `religious_ethnic` | ethnic *and* religious, not tied to one state | jødisk (Jewish) |
| `supranational` | broader than one nation | nordisk, skandinavisk, østerlandsk/orientalsk ("Oriental", archaic catch-all) |
| `minority` | a named minority identity within another nation | finlandssvensk (Swedish-speaking Finland) |

Each key carries every spelling variant seen (or plausible) as a
semicolon-separated `forms` list — base and `-e` plural/definite forms,
and, where the corpus itself is inconsistent, competing spellings
(`sachsisk` — the corpus's German-influenced spelling — vs modern
`saksisk`; `oldenburgsk` vs `oldenborgsk`; `hollandsk` vs `nederlandsk`).

## Method

Matching is **whitelist-only**: a token only counts as an ethnic
adjective if it (or, for compounds, each half) is literally listed in
`ethnic_adjectives_da.csv`. There is no "any word ending in *-sk*"
heuristic — Danish has a large ordinary vocabulary that ends in *-sk*/
*-isk* (*historisk*, *praktisk*, *musikalsk*, *juridisk*, …) that has
nothing to do with ethnicity, so a suffix rule would flood the results
with false positives (see below).

The table itself was built by:

1. Regex-scanning every `RegistryDescription` for words ending in
   `-sk`/`-ske` (284 distinct candidates, out of 10,228 rows).
2. Checking each candidate's actual sentence context in the source
   (not assumed from the word alone) before deciding whether it is a
   genuine ethnic/national descriptor.
3. Adding every genuine one, with the corpus's own spelling.
4. Re-running the parser and reviewing the *unmatched* residue —
   `person_ethnic_descriptors_review.csv` — to catch anything still
   missing. This closed two real gaps on the first pass (`czekisk`,
   `bøhmisk` were both attested but absent from an earlier draft of the
   table) and is meant to be repeated whenever the source register is
   updated: new vocabulary (or a transcription slip) shows up at the top
   of the review file instead of silently vanishing.

## Edge cases

### False-positive families deliberately excluded

The `-sk`/`-ske` candidate scan turns up a lot of Danish vocabulary that
looks like an ethnic plural/adjective but isn't one. All of the
following were checked against their actual sentence context and
excluded on purpose — they are *not* bugs, and the review file is
expected to keep reporting them on every run (that's how you can tell
the whitelist approach, rather than a suffix heuristic, is doing its
job):

- **Academic/professional-field adjectives** — by far the largest
  family: *historisk, klassisk, politisk, polyteknisk, zoologisk,
  filosofisk, botanisk, kirurgisk, theologisk, musikalsk, juridisk,
  diplomatisk, …* ("*romansk* Filolog" = a *Romance*-philology
  professor, "*nyeuropæisk* Lingvistik" = *modern-European*
  linguistics — neither says anything about the *person's* own
  nationality).
- **Religious, not ethnic** — *katolsk/katolske* ("den katolske Liga",
  "Isabella *den Katolske*" — a royal epithet), *luthersk/lutherske*,
  *evangelisk*, *mosaisk* (distinct from `jødisk`, which **is** kept —
  see below).
- **Titles and occupational/agent nouns that happen to end in
  `-sk`/`-erske`** — *marsk* (the medieval Danish office of Marshal,
  not a nationality), *rigsmarsk*, *kusk* (coachman), and the whole
  `-erske` female-agent-noun family: *husholderske* (housekeeper),
  *morderske* (murderess), *tiggerske* (beggar-woman), *syerske*
  (seamstress), *legatstifterske*, …
- **Surname/foundation-derived "-ske" adjectives.** Danish forms an
  adjective from a personal or institutional name the same way it forms
  an ethnic plural — *"det Classenske Fideikommis"* (the Classen family
  trust), *"det Anckerske Legat"*, *"Berlingske Tidende"* (a
  newspaper), *"det Städelske Institut"*. Morphologically these are
  indistinguishable from *"det svenske Gesandtskab"*; the whitelist
  protects against them automatically as long as no surname is ever
  added to the table.
- **Coincidences** — *måske* ("maybe"), *elske* ("to love"), and two
  actual Belarusian **place names** that happen to end in `-sk`
  (*Minsk*, *Bobruisk*) matched as ordinary words by the candidate scan.
- **Two open-ended classes, excluded by design rather than by
  omission** — Danish town/city demonyms (*viborgske*, *kronborgske*)
  and foreign-city demonyms (*parisisk*). Any Danish or foreign place
  name can form one of these; enumerating all of them is a different,
  much larger task than compiling nation/ethnicity adjectives, so only
  the handful with real historical weight for this register
  (`regional_danish`, `border_region`) are included.
- **Genuine transcription artefacts**, surfaced rather than silently
  fixed: `fiansk` (almost certainly a typo for *fransk* — the entry is a
  French art historian), `engçlsk` (garbled *engelsk*), and a mid-word
  space typo — `Chopin`'s entry reads "**polsk-f ransk** Komponist"
  (should be *polsk-fransk*), which splits into two tokens and is
  invisible to the parser as written. All three stay in the review file
  as single-occurrence candidates rather than being auto-corrected.

### Tokenizer: don't hand-enumerate accented letters

An early draft tokenized on a hand-listed set of accented Latin letters
(`æøåé…`). That silently broke on `ü`: *"württembergsk"* tokenized as
`W` + `rttembergsk`, dropping both the `W` and the `ü`. The fix was to
stop enumerating and use Python's general Unicode-letter class
(`[^\W\d_]`) instead, which handles `ü`/`ö`/`ñ`/`ç`/etc. correctly
without needing to know in advance which accents will show up in a
German, French, or Italian name embedded in Danish text.

### Compound nationalities

Dual/mixed-nationality descriptions are common enough (231 matches, ~8.5
% of all matches) to need explicit handling, in three shapes:

- **Hyphenated, genuinely dual** — *"czekisk-dansk Violoncellist"*,
  *"tysk-fransk Komponist"*. Both halves are matched individually
  (`match_type = hyphen_compound`) since both really do describe the
  person.
- **Hyphenated, but a fixed name for ONE polity** — *"tysk-romersk
  Kejser"* means Holy Roman Emperor, not "German and Roman"; likewise
  *"dansk-vestindisk"* names the Danish West Indies, and
  *"slesvig-holsten-lauenborgsk"* names the three joint duchies. These
  match as a single whole-token entry (`match_type = fixed_compound`) —
  see the `notes` column in the adjective table for which compounds get
  this treatment and why.
- **Solid (no hyphen)** — *"svensknorsk"*, *"tysksvensk"*,
  *"italienskfransk"*, *"ungarsktysk"*. The parser tries every split
  point of any `-sk`/`-ske`-shaped unmatched token and accepts it
  (`match_type = solid_compound`) if — and only if — *both* halves are
  independently in the whitelist, so this can't accidentally fire on an
  unrelated long word.

### Leading vs. embedded position — point 4: adjectives further into the description

| Position | Count | Share |
|---|---|---|
| Leading (the description's very first word) | 2,018 | 74.5 % |
| Embedded (appears later) | 690 | 25.5 % |

A leading adjective is overwhelmingly the register's own way of opening
a person's entry with their nationality ("*Svensk* rejsende, Italien
1834.") and is tagged `referent_hint = subject` outright. The embedded
quarter is where the adjective may describe someone or something other
than the register person themself — a spouse, a relative, or an
institution — and is exactly what point 4 asked to evaluate. Two
concrete corpus examples:

> **Neruda, Marie (1840–1922)** — *"**Czekisk** Violinvirtuos, Søster
> til Franz N., g. 1° 1864–1869 m. Ludvig Norman, …"* — the leading
> `Czekisk` describes Marie herself; a different row for a relative
> (*Neruda, Marie*, sibling entry) is a **"g. m. svensk** Operasanger
> Fritz Arlberg" — the embedded `svensk` describes her **husband**, not
> her.

> **Afzelius, Augusta** — *"… g. m. **dansk** Premierløjtnant, senere
> **svensk** …"* — two embedded nationalities in one description, both
> describing the person she married, not Augusta.

For every embedded match the parser applies a best-effort triage
heuristic (`referent_hint`) by checking the 1–3 tokens immediately
before the match:

| `referent_hint` | Trigger | Meaning |
|---|---|---|
| `possible_relation` (110 matches) | a preceding marker like *g., gift, m., med, søn, datter, broder, søster, enke, hustru* | the adjective likely describes a relative/spouse, not the register subject |
| `possible_institution` (118 matches) | immediately preceded by the definite article *det/den/de* | likely names an institution ("*Præst for den tyske Menighed*" — pastor **for** the German congregation) rather than the person's own origin |
| `unclear` (462 matches) | neither marker found | genuinely ambiguous from surface form alone — needs a human to read the sentence |

This is explicitly a **triage aid, not a classifier** — it narrows where
a reviewer should look, it doesn't resolve the question. `unclear` is
the largest bucket by design: most embedded mentions are ordinary prose
("*1858 Legationssekretær ved det tyske Gesandtskab i Madrid, senere
spansk …*") that a simple keyword window can't safely disambiguate.

## Wired into the mockup

`persons.html`'s "Nationalitet" facet runs off this data.
`build_persons_extra.py` attaches a `nationalities` array to each
`PERSONS_EXTRA` entry — **leading-position matches only**, so a person
is never claimed as German on the strength of a mention that may
describe their German spouse — plus a `NATIONALITY_LABELS` companion
const. The facet itself is rendered by the shared `js/facet-engine.js`
(`data-facet-source="nationality"`), with an "Uoplyst" bucket for the
8,259 persons carrying no leading match.

`build_nation_index.py` joins the same data to the place register and
emits `mockup/data/nation-index.js`, which powers `nation.html` — one
nation's persons, places, and the nation's own register entry in a
single view.

## Nation cross-links

`js/nation-link.js` offers `nation.html` from wherever the reader is
already looking at exactly one nation. It reads `NATION_INDEX` and
returns nothing when that global is absent, so on a fresh clone the
link simply doesn't appear rather than pointing at an empty page. It
also suppresses itself for a nation with no persons *and* no places.

Placement is the **second block from the top** in all four cases, which
puts it above the "Hyppigste …" sections on the detail pages:

| Page | Trigger | Link |
|---|---|---|
| `place.html` (detail) | place has `country_da` — "Altona ligger i Tyskland" | after the map block |
| `persons.html` (detail) | person has `nationalities` | after Beskrivelse, above Værker / Hyppigste steder |
| `places.html` (list) | reader ticks **one** Land facet value | after the results header, above the list |
| `persons.html` (list) | reader ticks **one** Nationalitet facet value | after the results header, above the list |

Two deliberate restrictions:

- **Single value only.** With two Land or Nationalitet values ticked
  there is no one nation to link to, and `nation.html` shows one at a
  time — so the banner hides rather than picking a winner. The
  "Uoplyst" bucket names no nation and never triggers it.
- **A person may get two links.** A dual nationality
  (`czekisk-dansk`, `tysk-engelsk`) yields one banner per nationality
  rather than a silent choice between them.

Where several nationality keys share one country entry — `hollandsk`
and `nederlandsk` both point at Holland, `finsk` and `finlandssvensk`
both at Finland, and the Danish regional keys sit inside Danmark — the
Land facet only knows the country label, so `byCountry()` prefers a
plain `national` demonym over a regional or minority one, and breaks
ties on person count.

The banner's person count is the `persons_certain` figure only;
`nation.html` additionally shows the `persons_possible` group. The
teaser therefore undercounts slightly, which is the safe direction.

### Scan: where else would a nation link help?

Grepping the mockup for `Tyskland` / `tysk` (outside generated data and
the 4,500 diary pages) turns up five more sites. Only the first two
were worth wiring; the reasoning for the rest:

- **`kort.html`** — marker popups print `country_da`. A link there is
  technically possible but low value: popups are transient, the country
  is already one line of a two-line popup, and the map is itself the
  "see everything geographically" view. *Not wired.*
- **`person.html`** — carries the same "Hyppigste steder" structure and
  would qualify, but it is orphaned: nothing in the mockup links to it
  any more (`persons.html` superseded it, and
  `tests/test_no_stale_person_refs.py` enforces that). Wiring a dead
  page would be misleading maintenance. *Not wired.*
- **`romaner.html` and `work.html`** — both carry a **Sprog** facet
  (`data-facet="lang"`, values `de` / `Tysk`). This is the works-side
  extension point `nation.html` already flags as open, and it stays
  open for two independent reasons. First, **data**: `WORKS_EXTRA.lang`
  is `None` for all 3,717 generated works — only the ~31 hand-curated
  `WORKS` in `work.html` carry a language, and `romaner.html`'s chips
  are hand-written mockup markup. Second, and more important,
  **semantics**: a work's language is not its author's nationality. A
  German-language book by a Danish author is not "German" in the sense
  this register's person descriptors mean, and conflating the two would
  quietly mis-attribute works. If a works-language link is added later
  it should be its own relation, not a reuse of `nationality_key`.
- **`diaries.html`** — one hardcoded sample card reading
  "Weimar, Tyskland" in static mockup markup, not data-driven. *Not
  wired.*

One direction remains unbuilt in the other sense: `nation.html`'s person
and place cards deep-link to the individual `?reg=…` pages, but there is
no "open this as a filtered list" link back to
`persons.html` / `places.html` with the corresponding facet pre-ticked.
That would need the list pages to accept a facet pre-selection from the
query string, which neither does today.
