# Plan: Full-text search — a working search bar + fields inside an entry

Status: proposal · 2026-09-08 · scoped, not started

Goal: turn the search bar from a label-only typeahead into something that
also finds matches inside an entry — person/place descriptions and, where
transcribed, the diary text itself — and give `search.html` a real results
page to land on instead of its current static mockup.

---

## 1. Where we actually stand

| Piece | Live today? |
|-------|-------------|
| Header/landing typeahead (`js/site-search.js` + `data/search-index.js`) | **yes** — substring match on register **labels only** (persons/places/works, ~16,400 rows), ranked by ref count, keyboard nav, `?reg=` deep-links |
| `search.html` / `search_en.html` (dedicated results page) | **no** — static markup hand-typed for one example query ("Rom"), fake facet counts, not wired to any data |
| The search form itself | **doesn't navigate anywhere** — `onsubmit="return false"` on every page, so there is currently no way to reach `search.html` from the UI at all |
| Full text *inside* an entry (description, diary prose) | **not indexed anywhere** |

The important finding, same shape as `docs/plan-live-facets.md`'s: **the
typeahead engine already works and doesn't need touching.** The gap is (a) no
results page behind it, and (b) no index of anything but titles.

---

## 2. Data coverage — what's actually searchable inside an entry

| Source | Field | Coverage |
|--------|-------|----------|
| `entities.csv` | person `description` | **9,466 / 10,228 (92.5%)** |
| `entities.csv` | place `description` | **0 / 2,508** — column is empty for this entity_type in the source spreadsheet |
| `entities.csv` / `WORKS_EXTRA` | work description/prose | **none** — works carry only structured fields (`h2`/`h3`/`author`/`date`/`place`/`see`), no free text beyond the title itself, which is already indexed |
| `mockup/diary-pages/*.html` (`.entry-text`) | diary transcription | **751 / 4,544 pages (16.5%)** — the rest render the explicit placeholder "Dagbogstekst … er endnu ikke transskriberet i dette projekt" |

So "search inside an entry" concretely means: person descriptions (strong
coverage), and diary prose (weak coverage, vols VI–VII only, same as the
`diary.csv` date gap already documented in `plan-live-facets.md` §2a). Places
and works have nothing beyond their titles to add.

---

## 3. The blocker is data coverage, not JavaScript — again

A full-text index built naively over the diary corpus would look complete
(4,544 "pages") while silently only covering 16.5% of it. Per the fact-check
rule in `CLAUDE.md` and the precedent `plan-live-facets.md` §3.4 already set
for partial data ("visible and inert with an honest note — never fabricated,
never partially-live in a way that silently drops rows"), the same rule
applies here:

**Decision to make before building:** index only the 751 transcribed pages,
and show the coverage gap wherever a diary-text match count is displayed
("full text searched: 751 of 4,544 diary pages — see Vores kilder"). Do not
present diary search as if it covers the whole corpus.

---

## 4. Architecture sketch

Same constraint as everywhere else in this codebase: the mockup is opened
over `file://`, so no `fetch()` of JSON — output has to be a plain `<script>`
tag assigning a global, like every other `data/*.js` file.

- New build step, `scripts/build_mockup/build_fulltext_index.py`, reading
  `entities.csv` (label + description) and `diary-pages/*.html` (`.entry-text`
  where present), emitting `mockup/data/fulltext-index.js` — one row per
  searchable document: `{type, rid|pag, label, text}`.
- v1 matching can stay a linear substring scan client-side, same approach
  `site-search.js` already uses and the same performance argument
  `facet-engine.js` §3.3 makes: tens of thousands of short documents is well
  under a frame, no Lunr/Fuse/bundler needed.
- Size check: 751 diary pages × roughly 1–2 KB of prose each is on the order
  of 1 MB; person descriptions add a few hundred KB more. Comparable to the
  existing 1–4 MB `data/*.js` files already shipped, so no new constraint.
- Gitignored like every other generated `mockup/data/*.js` output.

---

## 5. Making `search.html` real

Currently: static, one hardcoded query, unreachable. To finish:

1. Wire the header search form's submit handler to navigate to
   `search.html?q=…` (currently a no-op everywhere) — this alone is what
   makes "press Enter" do something instead of nothing.
2. On `search.html`, read `?q=` and run it against `SEARCH_INDEX` (labels,
   already live) plus the new `fulltext-index.js` (descriptions/diary text);
   merge and rank — label-exact, then label-substring, then a description or
   diary-text hit.
3. Snippet extraction: ~120 characters around the first match, `<mark>`
   highlighted, reusing `site-search.js`'s existing `highlight()` convention
   rather than inventing a second one.
4. Facets on the results page (Kildetype / Registertype / Kategori) — these
   didn't exist as live options when `search.html` was mocked up, but
   `facet-engine.js` does now (built for `persons.html`/`places.html` this
   session); reuse it instead of hand-rolling new filtering logic.
5. Årstal slider — same call as `plan-live-facets.md` §2a: most diary pages
   are undated, so this either stays inert or becomes a Bind (volume) filter
   instead, not a real year range.

---

## 6. Phases

0. **Wire the search form to navigate** to `search.html?q=…` — small, ships
   alone, and is the prerequisite for everything else being reachable at all.
1. **`build_fulltext_index.py`** — label + person description now; diary
   `entry-text` with the transcribed-coverage disclosure from §3.
2. **Rebuild `search.html`** as a real results page off `SEARCH_INDEX` +
   `fulltext-index.js`: snippets, ranking, working facet counts.
3. **Wire `facet-engine.js`** onto the results page, replacing the static
   hand-typed Kildetype/Registertype/Kategori counts.
4. **`search_en.html` parity pass** once the Danish page is proven — same
   two-page pattern as `kort.html`/`kort_en.html`.

---

## 7. Open decisions for whoever picks this up

- Exact ranking order between a label hit and a description/diary-text hit —
  needs a look at real result sets before committing to a formula.
- Should a diary-text match link straight to that diary page, or also surface
  the entities mentioned on it (the chip row the current `search.html` mockup
  already sketches for its fake "Rom" result)?
- Whether to let a reader filter transcribed-vs-untranscribed volumes
  explicitly via a facet, or just carry the coverage note.
