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
   `query.wikidata.org` — it's stdlib-only (`urllib`), no new dependency,
   but this project's own dev sandbox blocks both hosts at the network-
   egress layer. Run it from a machine with normal internet, or fall back
   to the manual WebSearch procedure below.

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

## Rebuilding

```
python scripts/build_mockup/build_works_extra.py
```

prints how many overlay rows it loaded:

```
7 hand-verified Wikidata entries loaded from data/curated/works_wikidata.csv
```
