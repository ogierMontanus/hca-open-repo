# Plan: Live facet-panel filtering

Status: proposal · 2026-08-03 · revised after review

Goal: turn `<aside class="facet-panel">` from hardcoded demo markup into
filtering that actually narrows the result list, on every page that has one,
without adding external dependencies.

---

## 1. Where we actually stand

Eight pages carry a `.facet-panel`. They are not in the same state.

| Page | Facet groups | Live today? |
|------|--------------|-------------|
| `billedkunst.html` | Underkategori, Kunstner, Gallerier | **yes** — via `category-catalogue.js` |
| `teater-musik.html` | Underkategori, Komponist/Forfatter | **yes** — Komponist is even generated from data |
| `bibliotek.html` | Forfattergruppe, Form | **yes** |
| `billedkunst` / `teater-musik` "Omtalte steder" | — | no — hardcoded, no `data-*` |
| `persons.html` | Nationalitet, Rolle, Tilknytning, Samtidige steder | no |
| `places.html` | Land, Samtidige personer, Omtaleår | no |
| `diaries.html` | Omtaleår, steder, personer, 3× værker | no |
| `search.html` | Kildetype, Årstal, Registertype, Kategori | no |
| `romaner.html` | Posttype, Sprog, Forfatter | no — uses a `data-facet`/`data-match` scheme no JS reads |

**The important finding: we do not need to design a faceting engine — we
already have one.** `mockup/js/category-catalogue.js` implements, in ~200
lines of dependency-free ES5:

- OR within a facet group, AND across groups
- adaptive availability — options that would yield 0 hits are disabled,
  dimmed, and their counts rewritten live (`updateFacetAvailability`)
- alphabet-bar chips dimmed to match the active facet set
- empty state with a working reset
- `Nulstil` wired to clear everything

It is only reachable from the three wing pages, and only recognises four
hardcoded predicate fields (`data-h2`, `data-h3`, `data-author`, `data-rid`).

So the work is **extraction and generalisation**, not invention.

---

## 2. The real blocker is data coverage, not JavaScript

Several existing facets cannot be made live because nothing backs them. This
matters more than the wiring, and it is where the plan should start.

| Facet | Page | Backing field | Coverage |
|-------|------|---------------|----------|
| Omtalte steder / personer / værker | diaries | `DIARY_INDEX[].c[]` | **4544/4544 (100 %)** |
| Bind | diaries | `DIARY_INDEX[].v` | **4544/4544 (100 %)** |
| Underkategori, Forfatter | wing pages | `WORKS_EXTRA.h2/h3/author` | 3708 / 2890 |
| Samtidige personer/steder | places, persons | `cooccurrence.js` | present |
| **Land** | places | `PLACES_EXTRA.country_da` | **454/2508 (18 %)** |
| **Omtaleår** | diaries | `diary.csv` date/year | **751/4544 (16.5 %)** |
| **Sprog** | romaner | `WORKS_EXTRA.lang` | **0/3708 — always null** |
| **Nationalitet** | persons | *nothing* | **0/10228** |
| **Rolle / Erhverv** | persons | *nothing* | **0/10228** |

Three findings deserve to be called out explicitly.

**a) The diary year facet is structurally limited to two volumes.**
`data/normalized/diary.csv` is the transcribed text, and it only covers vols
VI and VII. Every other volume has no date at all:

```
vol  : pages : dated          vol  : pages : dated
  I  :   511 :     0            VII :   400 :   398
  II :   452 :     0            VIII:   489 :     0
  III:   433 :     0            IX  :   419 :     0
  IV :   477 :     0            X   :   485 :     0
  V  :   459 :     0            XI  :    56 :     0
  VI :   363 :   353          TOTAL : 4544 :   751
```

A year slider labelled 1825–1875 over this data would silently hide 83 % of the
corpus the moment a reader touched it.

**Decision:** dates for the remaining volumes will be supplied later in the
same precise `diary.csv` format. Do **not** infer dates from headings or
titles. The Omtaleår facet keeps its full 1825–1875 range and stays inert
until every volume has real dates — see §3.4.

**b) Persons has two facets with zero backing.** `PERSONS_EXTRA` carries only
`label, description, born, died, era, refs`. There is no nationality and no
occupation field, and `entities.csv` has `genre_h2`/`form_h3`/`person_derived`
empty for all 10 228 persons. The counts currently shown (Dansk 4.218, Tysk
1.847, …) are invented, and per the fact-check rule in `CLAUDE.md` they must
not be shipped as if real.

**Decision:** nationality and profession will be supplied later as structured
input, possibly reconciled from Wikidata. So the two groups are **kept**, not
deleted — the fabricated counts come off and the groups go inert until the
data arrives. See §3.4.

**c) `diaries.html` reports the wrong total.** The hero says "2.177
dagbogssider"; `DIARY_INDEX` holds 4 544 pages. 2 177 is the row count of
`diary.csv` (vols VI–VII transcription), not the page count. The facet counts
inherit this confusion.

---

## 3. Architecture

One new file, no new dependencies, everything else is markup and build script.

```
mockup/js/facet-engine.js      NEW — extracted from category-catalogue.js
mockup/js/category-catalogue.js       refactored to consume it
mockup/js/diary-wire.js               gains a facet hook
scripts/build_mockup/build_facets.py  NEW — emits data/facets.js
```

### 3.1 Declarative markup contract

Adopt the `data-facet` / `data-match` pair that `romaner.html` already uses —
it is the more general of the two schemes in the tree, and standardising on it
means one vocabulary everywhere.

```html
<div class="facet-group" data-facet-group="sted">
  <div class="facet-group__header">Omtalte steder <span class="facet-group__toggle">▲</span></div>
  <div class="facet-group__body" data-facet-source="place" data-facet-limit="12">
    <!-- rows generated at runtime from the facet manifest -->
  </div>
</div>
```

A generated row:

```html
<label class="facet-item">
  <input type="checkbox" data-facet="place" data-match="Reg0010880">
  <span class="facet-item__label">København</span>
  <span class="facet-item__count">1564</span>
</label>
```

Rules: `data-facet` names the item field, `data-match` the value (comma-
separated = OR, as `romaner.html` already does for `da,no`). Counts are never
typed by hand — the engine writes them on first render.

### 3.2 Engine API

```js
FacetEngine.create({
  panel:  document.querySelector('.facet-panel'),
  items:  ALL,                    // array of plain objects
  accessors: {                    // field name → value(s) for one item
    place:  it => it.placeRids,   // array ⇒ multi-valued facet
    person: it => it.personRids,
    vol:    it => it.v,
    year:   it => it.y            // undefined ⇒ item excluded from that facet
  },
  onChange: filtered => renderList(filtered)
});
```

Returned controller: `.apply()`, `.reset()`, `.state()`, `.setPrefilter(fn)`
(so the alphabet bar and the diaries free-text box compose with facets rather
than fight them).

Carried over from `category-catalogue.js` unchanged: OR/AND semantics,
`updateFacetAvailability`, empty state, `Nulstil`. Added: multi-valued fields
(a diary page has many places), URL-hash state so a filtered view is linkable,
and two ways to handle an incompletely-covered field —

- **live with an "Uoplyst" bucket**, for fields where the data that exists is
  real and the gap should be visible and selectable, or
- **inert**, for fields awaiting a structured supply (§3.4).

The one thing the engine must never do is filter on a partially-covered field
without showing the gap, because that drops rows the reader has no way to know
about.

### 3.3 Why no external dependency

Everything stays a plain `<script>`-tag IIFE over an in-memory array. That is
forced by the existing constraint — the mockup is opened over `file://`, where
`fetch()` of JSON is blocked, which is why the build already emits `.js` files
that assign globals rather than `.json`. Datasets are 2 508–10 228 rows; a
linear scan per keystroke is well under a frame. No Lunr, no Fuse, no
framework, no bundler.

### 3.4 The "awaiting data" facet state

Both deferred cases — person nationality/profession, and diary dates for vols
I–V and VIII–XI — are the same situation: *the facet is correct, the data is
not here yet.* Rather than handling them ad hoc, define one shared state.

The codebase already has the precedent. The disabled **Begivenhedsdatoer** pill
on `diaries.html`, `places.html` and `billedkunst.html` does exactly this:
visible, `disabled`, dimmed to `opacity:0.45`, with a `title` explaining what
will switch it on. Generalise that to a whole facet group:

```html
<div class="facet-group" data-facet-group="nationalitet" data-facet-pending>
  <div class="facet-group__header">
    Nationalitet <span class="facet-group__toggle">▲</span>
  </div>
  <div class="facet-group__body" data-facet-source="nationality">
    <p class="facet-note">
      Aktiveres når strukturerede nationalitetsdata er indlæst.
    </p>
  </div>
</div>
```

Rules:

- `data-facet-pending` makes `FacetEngine` skip the group entirely — it
  contributes no predicate, so it cannot narrow or silently drop rows.
- The group renders **no checkboxes and no counts**. Fabricated numbers come
  off; nothing takes their place until the build can supply real ones.
- One new CSS class, `.facet-note`, reusing the muted 0.72rem style the
  Datokategori explanation blocks already use.
- Activation is a one-line markup change: drop the attribute, rebuild.

This is why Phase 5 matters more than it first appears. `build_facets.py`
computes coverage per field, so it can print a report at build time:

```
facet 'year'        751/4544  (16.5%)  — group marked pending  ✔ consistent
facet 'nationality'   0/10228 ( 0.0%)  — group marked pending  ✔ consistent
facet 'country_da'  454/2508  (18.1%)  — group LIVE with Uoplyst bucket
```

When the diary dates land and `year` reports 4544/4544, the report flags a
group still marked pending, and someone removes one attribute. No archaeology
needed six months from now to remember which facets were waiting on what.

---

## 4. Phases

### Phase 0 — honesty pass (do first, ships alone)

Fix what is currently misleading, before adding behaviour. Nothing is deleted;
facets awaiting data are held inert per §3.4.

1. Correct the `diaries.html` page count 2.177 → 4.544, and say plainly that
   full text exists for vols VI–VII.
2. Add the `.facet-note` style and `data-facet-pending` handling — small, and
   every later phase depends on it.
3. Mark **pending** and strip the fabricated counts from:
   - `persons.html` → *Nationalitet*, *Rolle / Erhverv* (awaiting structured
     supply, possibly Wikidata)
   - `diaries.html` → *Omtaleår*, keeping the full 1825–1875 range as-is
     (awaiting dates for vols I–V, VIII–XI)
   - `romaner.html` → *Sprog* (`lang` null for all 3 708 works)
4. Add to `persons.html` the facets that *are* backed today, so the panel does
   something real while the rest waits:
   - *Levetid* — from `era` (7 397/10 228) plus an "Uoplyst" bucket
   - *Antal dagbogsomtaler* — buckets over `refs` (100 %)
   - *Skaber af registrerede værker* — computed from `WORKS_EXTRA.author`

### Phase 1 — extract the engine

Move the predicate/availability/reset core out of `category-catalogue.js` into
`facet-engine.js` behind the API above; make `category-catalogue.js` a thin
caller. Success criterion: **the three wing pages behave identically before and
after** — same counts, same dimming, same reset. This is a pure refactor and is
the safety net for everything after it.

### Phase 2 — diaries.html (highest value)

The largest corpus and the only fully-covered facet data.

- Make *Omtalte steder / personer / værker* live off `DIARY_INDEX[].c[]`,
  matching on `r` (the Reg-id) not the label, so spelling variants collapse.
  All three are 100 % covered.
- **Add** a *Bind I–XI* group (100 % covered, and the natural way to navigate
  an undated corpus). This sits **alongside** the inert Omtaleår group — it is
  not a replacement for it, and the year range stays 1825–1875 untouched.
- Compose with the existing free-text box and the new calendar view via
  `setPrefilter`.

When the remaining volume dates arrive, Omtaleår activates against the same
engine with no further work here — one attribute drops off and the year
accessor starts returning values for all 4 544 pages.

### Phase 3 — places.html and persons.html

**places.html is done** (see §8). `mockup/js/facet-engine.js` was written for
it and is the engine Phase 1 will retrofit onto the wing pages; the decision on
Land below was taken as recommended.

- `places.html` **Land**: recommended **live** off `country_da` with an
  explicit "Uoplyst (2.054)" bucket. This is the one partial-coverage field
  proposed to go live, and it differs from the year case in two ways: the
  454 country values are real data already present rather than a supply we are
  waiting on, and the Uoplyst bucket means the 82 % gap is on screen instead of
  silently dropped. If the preference is to hold anything below full coverage
  inert, mark it `data-facet-pending` instead — the mechanism is identical and
  the choice is reversible either way.
- `places.html` **Samtidige personer** / `persons.html` **Samtidige steder**:
  live off `cooccurrence.js`, which already holds top-12 per entity.
- Both pages already have an alphabet bar and a `Vis flere` button; route them
  through `setPrefilter` so letter + facets compose.

### Phase 4 — the stragglers

- `billedkunst` / `teater-musik` "Omtalte steder" — needs a work→place index;
  add it to `build_cooccurrence.py` rather than inventing a new script.
- `search.html` — facets over `SEARCH_INDEX` (`t` and `w` fields are already
  there); this one is close to free once the engine exists.
- `romaner.html` — its markup already uses the canonical `data-facet` /
  `data-match` scheme (§3.1), so it only needs connecting to the engine.
  *Posttype* is derivable from `see` / `seeAlso` (117 / 76 works); *Forfatter*
  from `author`. *Sprog* stays pending from Phase 0.

### Phase 5 — build-time facet manifest

`scripts/build_mockup/build_facets.py` emits `mockup/data/facets.js`:
per page, per field, the distinct values with real counts and coverage
percentages. The engine renders facet rows from it, so no facet label or count
is ever hand-typed again, and coverage gaps surface at build time instead of in
review. Add it to the `build-mockup.yml` workflow and to `.gitignore` beside
the other generated `mockup/data/*.js`.

---

## 5. Sequencing note

Phases 0 and 1 are independent and can land in either order; 0 is
user-visible and 1 is invisible, so 0 first gives the earlier win. Phase 2
depends on 1. Phases 3 and 4 are parallel once 2 is proven. Phase 5 can be
retrofitted at any point after 2 — it replaces hand-written facet rows with
generated ones and is the difference between "live" and "stays live".

## 6. Decisions taken

Recorded so the reasoning survives the next six months.

**Person nationality and profession** will be supplied later as structured
input, possibly reconciled from Wikidata. The two facet groups are therefore
kept in the markup and held inert (§3.4) rather than removed. The invented
counts come off now; real ones arrive with the data.

**Diary dates for vols I–V and VIII–XI** will be supplied in the same precise
format as the existing `diary.csv` columns. Dates must **not** be inferred from
headings, titles, or volume position — an inferred date is indistinguishable
from a real one once it is in the index, and the register's value rests on that
distinction. Omtaleår keeps its full 1825–1875 range and stays inert until all
volumes are dated.

The general rule both cases establish: **a facet awaiting structured data stays
visible and inert with an honest note — never fabricated, and never
partially-live in a way that silently drops rows.**

## 7. Still open

- Nothing blocking. `persons.html` (Phase 3) is the next page in line, and its
  two pending groups are already specified in Phase 0.

## 8. Shipped

**places.html — live** (`facet-engine.js`, `places.html`, `style.css`).

| Group | State | Backing |
|-------|-------|---------|
| Land | live, 12 values + Uoplyst | `PLACES_EXTRA.country_da` |
| Samtidige personer | live, top 20 | `PLACE_TOP_PERSONS` + `PERSONS_EXTRA` |
| Omtaleår | **pending** | awaiting dates for vols I–V, VIII–XI |
| Stedstype | (unchanged, still commented out) | awaiting reconciliation |

Notes from the build:

- The fabricated counts were not merely unbacked, they were wrong by an order
  of magnitude — the old markup claimed *Danmark 612*, the data says **43**.
  Nothing is hand-typed now; `FacetEngine` renders every row and count from
  `data-facet-source`.
- *Samtidige personer* filters on `PLACE_TOP_PERSONS`, which keeps the top 12
  co-occurring persons per place. Ticking a name therefore finds places where
  they are among the most frequent companions, not every place they were ever
  mentioned beside. The group carries a note saying so — without it the filter
  would read as exhaustive.
- Both groups degrade to pending if their generated data is absent (fresh
  clone, no build), so the page never shows bare `Reg…` ids.
- Availability counts are computed against all *other* groups, so the sidebar
  numbers track the live set and zero-reach options dim out.
- Verified end-to-end through jsdom against the real generated data: 18 checks
  covering OR-within-group, AND-across-groups, the Uoplyst bucket, letter ∩
  facet composition, and reset clearing both facets *and* the letter prefilter.
  The three wing pages were re-checked for regression and are unchanged.
- Interaction cost needed work: the first cut re-read DOM attributes inside the
  items × options loop at ~272 ms per toggle. Values are now indexed once at
  construction and predicates compiled once per pass, which took it to ~100 ms
  under jsdom — and jsdom is several times slower than a browser at this.
