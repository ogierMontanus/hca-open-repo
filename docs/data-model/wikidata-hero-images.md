# Wikidata Q-numbers and hero images for works

Some works in `mockup/work.html` — the hand-curated `WORKS` entries like
Reg003004 (Sixtinske Madonna) — carry a `wd` (Wikidata Q-number) and an
`image` (Commons hero image URL). Those were typed in by hand, one at a
time, and only exist for the small set of works someone bothered to
curate. There was no path to add the same two fields to a work that's
*not* hand-curated — i.e. the other ~3,700 works that only exist in the
generated `WORKS_EXTRA` (`mockup/data/works-extra.js`).

`data/curated/works_wikidata.csv` + `scripts/parsers/wikidata_lookup.py`
add that path, following the same curated-overlay-CSV shape already used
for `ethnic_adjectives_da.csv` and the two `nation_*.csv` files:
`build_works_extra.py` loads the CSV and merges `wd`/`image` straight into
every `WORKS_EXTRA` entry it covers — `work.html`'s existing rendering
code (hero image, `wd:` badge, LOD callout) already reads those two fields
off `ALL_WORKS[reg]` regardless of whether the entry came from the curated
`WORKS` object or generated `WORKS_EXTRA`, so nothing in `work.html` itself
needed to change.

## Two-step workflow: propose, then verify by hand

1. **Propose** — `wikidata_lookup.py` queries Wikidata for every item
   credited to a given creator, matches each against this register's own
   titles for that author (`WORKS_EXTRA.author`), and writes a review CSV.
   It never writes to `works_wikidata.csv` itself.

   ```
   python scripts/parsers/wikidata_lookup.py "Bartolomé Esteban Murillo" \
       --author-match Murillo --out review_murillo.csv
   ```

   This needs a direct connection to `www.wikidata.org` and
   `query.wikidata.org` — it's stdlib-only (`urllib`), no new dependency.

   **Update 2026-08-12:** both hosts, plus `commons.wikimedia.org`, are
   reachable from the dev sandbox again (verified 200 OK). The note that
   they were blocked at the network-egress layer no longer holds. Querying
   the SPARQL endpoint directly is now the preferred proposal step, because
   it returns `P195` (collection) and `P276` (location) alongside the image,
   which is exactly what the verification below turns on — a WebSearch hit
   gives you a Q-number but not the collection to check it against.

2. **Verify by hand, then promote a row** — open each candidate's
   `wikidata_url`, check the collection actually matches what the local
   title says, and only then add `rid,wd,image_filename` to
   `works_wikidata.csv`. This step is not optional or skippable: CLAUDE.md's
   Faktakontrol rule exists because an earlier session shipped 6 wrong
   Wikidata Q-numbers out of 8 from memory alone, and the failure mode here
   is structurally the same risk in a new shape — a *live* query can still
   return the wrong *specific* painting, not just a wrong Q-number. Murillo
   alone painted 10+ "Immaculate Conception" canvases now in different
   collections (Prado, El Escorial, Aranjuez, the Museo de Bellas Artes de
   Sevilla, …); a title-similarity match can land on a real, correctly-typed
   Wikidata item that just isn't the specific canvas this register's title
   names. The CSV's `notes` column exists to record *how* each row was
   checked (collection cross-referenced, alternate candidates ruled out) —
   not just that it was.

## Doing it without network access (this project's sandbox)

`WebSearch` domain-filtered to `wikidata.org` — the same procedure
CLAUDE.md already documents for verifying person/place Q-numbers — works
here too, plus one extra step: after finding the Wikidata item, a second
unfiltered search for `"<title>" commons.wikimedia.org file` is usually
needed to get the exact Commons filename (Wikidata's own P18 value isn't
visible in a search snippet). This is how the first 7 rows in
`works_wikidata.csv` were verified — no code execution, `WebFetch` on
`wikidata.org` is itself blocked by the same egress policy that blocks
`wikidata_lookup.py`'s direct API calls.

## Current coverage

7 of 19 BILLEDKUNST works credited to Murillo (`author == 'Murillo'` in
`WORKS_EXTRA`, after the extraction fix in
`billedkunst-artist-extraction.md`) have a verified Wikidata entry:

| Reg | Title | Wikidata |
|---|---|---|
| Reg000711 | Den gode Hyrde | [Q11694421](https://www.wikidata.org/wiki/Q11694421) |
| Reg000721 | Den hellige Familie med Fuglen | [Q16627776](https://www.wikidata.org/wiki/Q16627776) |
| Reg000765 | Den ubesmittede Undfangelse (La Colosal) | [Q22120723](https://www.wikidata.org/wiki/Q22120723) |
| Reg001801 | Jeune mendiant | [Q5659824](https://www.wikidata.org/wiki/Q5659824) |
| Reg002011 | La Virgen de la Servilleta | [Q2880218](https://www.wikidata.org/wiki/Q2880218) |
| Reg002435 | Moses slaar Vand af Klippen (La Sed) | [Q109535214](https://www.wikidata.org/wiki/Q109535214) |
| Reg002911 | S. S. Justa y Rufina | [Q6120755](https://www.wikidata.org/wiki/Q6120755) |

The other 12 Murillo works weren't added: several are `"Madonna med
Barnet"`-type titles too generic to confidently pin to one specific
Wikidata item without risking exactly the wrong-specific-painting mistake
described above, and one (`"Visión de San Francisco (Murillo, Academia,
Sevilla)"`) had multiple Wikidata candidates (Getty Museum, Prado) whose
collection didn't match the title's "Academia, Sevilla" at all — better to
leave it unillustrated than guess. `wikidata_lookup.py` run with a lower
`--min-score` will resurface these as low-confidence candidates for a
future pass, same as it did for the 7 that made it in.

23 of 37 works credited to Rafael (Raphael) — see "A third path: outsourcing
the lookup, still verifying the answer" below for how these were found.

## A third path: outsourcing the lookup, still verifying the answer

For a whole artist's catalogue at once, a plain-text export + a copy-paste
prompt for a chatbot with live web access (Copilot, ChatGPT, …) is a
practical third path alongside `wikidata_lookup.py` and manual WebSearch —
*as long as the answer is still independently re-verified before it's
trusted*, not imported as-is. The Rafael batch is the worked example:

1. A **works export** was generated from `WORKS_EXTRA` (id, title, a local
   link for cross-referencing, and hand-added notes flagging known traps —
   duplicate titles resolving to different paintings, a copy mislabeled
   under the original's title, an OCR'd title) and handed to Copilot with
   an explicit prompt: verify live, don't guess from memory, cross-check
   the collection named in the title, and return the answer in the same
   `id | title | link | notes` shape so it could be matched back up.
2. **Copilot did not follow the "keep the id exactly as given" instruction**
   — it returned a full 37-row table with a completely different, invented
   set of ids. The row *order* matched the input exactly, though, so the
   correct `rid` for every row was recovered by position/title match rather
   than trusted from Copilot's own id column. This is exactly the class of
   error the verify-before-import discipline exists to catch — a
   plausible-looking, internally-consistent answer that's simply wrong in
   a way that isn't obvious from reading it.
3. **Every one of Copilot's "Confirmed" Q-numbers was independently
   re-checked** via WebSearch domain-filtered to wikidata.org (fanned out
   across four parallel research agents — 25 Q-numbers total) before any of
   them were added here. That pass caught three more real problems Copilot
   itself had missed or mis-stated:
   - **Reg002447 ("Mysterierne")** — Copilot reused the Oddi Altarpiece's
     main-panel Q-number (Q2344357, correct for Reg001819) for the
     *predella* scenes too. Wikidata models each predella panel as its own
     item (one confirmed: Q116286717 for the Annunciation panel) — reusing
     the parent item for the predella would have been wrong. Left
     unconfirmed rather than guess which predella item(s) apply.
   - **Reg002248 ("Madonna della Tenda")** — the register's title says
     "Madama, Torino," but Wikidata Q2269330 (and the museum record behind
     it) puts the actual Madonna della Tenda in the Alte Pinakothek,
     Munich, since 1819. Collection mismatch — same rule as the Murillo
     "Visión de San Francisco" case: leave it unconfirmed rather than force
     a title-only match onto the wrong location.
   - **Reg000662 ("De tre theologiske Dyder")** — two Wikidata items
     (Q131557878, Q2568776) both describe what looks like the same Vatican
     fresco under near-identical labels; which one is canonical (or
     whether they're genuinely different sub-elements) couldn't be
     resolved from search snippets alone. Left unconfirmed pending a
     manual side-by-side page comparison.

   The other 11 works Copilot itself marked unconfirmed (a Sistine Madonna
   copy, an S. Cecilia copy after Guido Reni, an Uffizi "La Fornarina" that
   turned out to be a *different, unrelated* painting historically
   misattributed under the same nickname, etc.) were left that way — no Q-
   number was proposed for them, so there was nothing to verify or add.

**Caveat carried into the CSV itself:** the re-verification pass confirmed
each accepted row's Wikidata *subject and collection* — it did not
independently re-check every Commons **image filename** Copilot supplied
(that would have meant opening each Commons file page directly, which this
project's sandbox can't do — see below). Those filenames are recorded as
Copilot-sourced, not independently re-verified, in each row's `notes`. Two
rows (Reg002880, Reg002900) have unusually long filenames worth a visual
spot-check on `work.html` before treating the image as final.

## Policy: a diary register isn't a catalogue raisonné (2026-08-09)

The first Rafael pass excluded every work no longer credited to Raphael by
current scholarship — e.g. the Uffizi "La Fornarina" (`Reg001987`), long
catalogued as an autograph Raphael, now recognized as a Sebastiano del
Piombo portrait that happens to share the same traditional nickname as
Raphael's real, autograph "La Fornarina" (Palazzo Barberini — a different
painting, `Reg001986`, unaffected by this). That exclusion was too strict:
the register transcribes what a 19th-century diary said, which is itself a
historical fact worth recording, not a claim this project is making about
who actually painted something.

**Relaxed rule:** a work stays eligible for an entry as long as (a) the
collection/city named in the register title matches where the painting is
or was actually held, and (b) the register's "Rafael" attribution matches
what the painting used to be — or is still popularly — called. Current
scholarly opinion is then recorded in the CSV's `attribution_note` column
rather than treated as a reason to exclude the row, using this exact
phrasing when the current attribution differs from Raphael:

```
Tilskrives i dag ikke længere Rafael — [current attribution], [one-line reasoning/source]
```

**What still isn't relaxed:** a genuine *location* mismatch remains
disqualifying — see `Reg002248` ("Madonna della Tenda," register says
Turin, the actual painting has been in Munich since 1819). That's a
different painting or a transcription error, not a case of attribution
drifting since the 19th century, and the relaxed rule doesn't cover it.

### `attribution_note` is reader-facing; `notes` never is

The CSV has two free-text columns that look similar but go to different
places:

| Column | Audience | Where it ends up |
|---|---|---|
| `attribution_note` | readers of the site | `WORKS_EXTRA[rid].attributionNote`, rendered on `work.html?reg=…`'s detail view |
| `notes` | whoever maintains this CSV | nowhere — `load_wikidata_overlay()` in `build_works_extra.py` never reads it into the generated JS at all |

`work.html` shows `attributionNote` (when set) as a distinct callout — styled
as a caveat, not folded into the upbeat "Linked Open Data" framing — above
the LOD callout, before the reader gets to the "connected to the global
knowledge graph" pitch. **Nowhere else renders it.** List/facet/card views
(`category-catalogue.js`'s cards on `billedkunst.html` etc.), the diary-
reference chips, `entity-refs.js`'s cross-links, `cart.html`, and the search
index all read `title`/`author`/`refs` off `WORKS_EXTRA` without ever
touching `attributionNote` — so there's no explicit suppression logic to
maintain in each of those; the field is simply absent from every template
except the one detail view. Verified directly (Playwright): injecting a
test `attribution_note` and loading `billedkunst.html` confirmed neither
the CSS class nor the note text appear anywhere on that page.

If a future change adds a new work-listing surface, this is the rule to
carry forward: read `attributionNote` only in the single-entity detail
template, never in anything that renders a work as one row among many.

Applying this retroactively to the 14 Rafael rows still without a Wikidata
entry — including two more misattribution cases in the same shape as the
Fornarina (`Reg002518` "Noah og Arken," `Reg003462` "Violinspilleren," both
demoted away from Raphael per RCT/Getty records) — is tracked as a round-2
export, same outsource-then-reverify workflow as the first pass.

## Rebuilding

```
python scripts/build_mockup/build_works_extra.py
```

prints how many overlay rows it loaded:

```
30 hand-verified Wikidata entries loaded from data/curated/works_wikidata.csv
```


## What a Reni pass actually looked like (2026-08-12)

A worked example of why step 2 is not a formality. 28 works in this register
are credited to Guido Reni; a SPARQL query for `wdt:P170 wd:Q109061` with an
image returned 310 items, 333 rows with a collection. Automatic matching on
title tokens plus collection tokens produced candidates for 22 of the 28.

**Three survived verification.** Reg000280 *Aurora* (Palazzo
Pallavicini-Rospigliosi, still in situ), Reg000530 *Cleopatra* (Galleria
Palatina, i.e. Palazzo Pitti), Reg002187 *Lucrezia* (Galleria Spada). In each
case `P195` names the same collection as the register's own title.

**The rest were wrong, and wrong in instructive ways:**

- *Christus paa Korset* matched "Crucifixion of Saint Peter" — a different
  subject that shares a token.
- *La Pietà (Bologna)* and *Madonna della Pietà* both matched a "Pietas" in
  the Nationalmuseum, Stockholm — right word, wrong continent.
- *Maria Magdalene (Durazzo, Genova)* matched Munich copies; Reni's Magdalenes
  exist in at least five collections.
- *Beatrice Cenci (Barberini, Rom)* matched a version in Blackburn.
- *Moses (Sciarra, Rom)* matched one in the National Galleries of Scotland.

The pattern: the register's titles name **historical** collections — Sciarra,
Manfrin, Fesch, Leuchtenberg, Durazzo — most of which were dispersed in the
19th century. Wikidata records where a painting is **now**. So collection
matching cannot be automated for those; it needs someone who knows the
painting moved, and where to. Roughly a 1-in-9 hit rate on candidates that
looked plausible to the matcher.

Two caveats were recorded in `notes` rather than silently accepted:

- The Aurora image file is named "…nelle arti decorative" and may be a
  reproduction rather than a photograph of the fresco; its 2498×995 proportion
  does match the ceiling panel, and it is the `P18` Wikidata itself declares.
  Flagged for a human eye.
- The Spada *Lucrezia* is catalogued by the gallery as anonymous 17th century,
  while Wikidata still gives `P170` = Reni. The *painting* is identified beyond
  doubt (right collection, right subject); only the attribution is contested,
  and the register follows the contemporary attribution Andersen would have
  known. Recorded in `attribution_note`.
