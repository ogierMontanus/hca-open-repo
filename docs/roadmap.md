# Roadmap

Status: current · 2026-09-07 — rewritten after the preprocessing/build
split landed (see `docs/pipeline/README.md` and `HANDOVER.md`). The
previous version of this file was written before the repository existed
and described a generic, hypothetical bootstrap (creating the repo,
choosing CSV vs. RDF, writing a `CONTRIBUTING.md`). None of that reflects
where the project actually is now, so it has been replaced rather than
amended.

## Where the project actually stands

- **Two repositories, one pipeline.** Cleaning, segmentation,
  normalisation and enrichment live in
  [HCA-Diary-data-cleaning](https://github.com/ogierMontanus/HCA-Diary-data-cleaning).
  This repo only builds and publishes: it reads the prepared files under
  `data/normalized/`, `data/parsed/` and `data/curated/`, and turns them
  into `mockup/` and `web/`. The full contract is
  `docs/pipeline/README.md`; the rule for where new code goes is in
  `CLAUDE.md`.
- **The build is stdlib-only** and produces, from committed prepared
  data: 4,544 diary detail pages plus 8 generated `*.js` view artifacts
  and 6 `*.json` artifacts (`scripts/build_all.py`, stages 2–4f).
  `scripts/build_all.py --check-inputs` reports what prepared data is
  present without running a build.
- **The live site** covers persons, places, works (three wings:
  billedkunst, teater-musik, bibliotek), diaries, and a nation mashup,
  with cross-linking and a working co-occurrence index
  (`mockup/data/cooccurrence.js`).
- **English translation** is partial by design (full duplicate `_en.html`
  pages, not a runtime toggle — `docs/i18n-policy.md`). Six high-traffic
  pages are done; the entity detail pages (`work.html`, `place.html`,
  `entry.html`) and the three wing pages are not. Tracked in
  `docs/i18n-todo.md`.
- **Facet filtering** is live and data-backed on the three wing pages via
  `mockup/js/category-catalogue.js`. It is not yet wired on `persons.html`,
  `places.html`, `diaries.html`, `search.html` or `romaner.html` — and for
  several of those pages the blocker is missing source data, not missing
  JavaScript. Full page-by-page state and data-coverage numbers:
  `docs/plan-live-facets.md`.

## Quick items — resolved 2026-09-07

The two decisions from the previous pass, closed out:

- **`timeline-index.js`: wired in.** Added as build stage 4g in
  `scripts/build_all.py` and as its own `continue-on-error` step in
  `.github/workflows/build-mockup.yml`, matching how 4f (nation-index.js)
  is already optional. The frontend (`mockup/js/timeline-wire.js`,
  `diaries.html`) already handled the file's absence gracefully, so this
  was purely additive. Verified: `build_all.py --only 4g` produces 1,446
  events; a full `--skip-pages` build and the test suite pass; loaded
  `diaries.html` in a headless browser and confirmed `TIMELINE_INDEX` is
  populated and the Tidslinje tab renders real data.
- **`persons_wikidata.csv`: no code change needed.** Inspected
  `build_persons_extra.py`'s `load_person_wikidata()` — it already
  degrades correctly when the file is absent. Authoring the actual
  Wikidata IDs is enrichment work (deriving a fact about the data), which
  per the repo split belongs in HCA-Diary-data-cleaning, not here.
  Nothing to stub out locally.

## Design choices for the larger items

These three remain open. Each already has enough documented investigation
to start from — the point of this section is to name the concrete design
each would follow, not to re-litigate whether to do them.

### 1. English parity for the detail pages

**Approach:** continue the pattern already used for the six done pages —
a full duplicate `_en.html` file per page (`docs/i18n-policy.md`'s
decision, not a runtime lang-toggle), translating UI chrome and static
copy while leaving register data (names, nationality vocabulary) Danish
per policy. Order: `work.html` and `place.html` first — every translated
list page already links to them, so they're the biggest live seam — then
the three wing pages, then the utility pages (`om.html` earliest among
those, since every `_en.html` footer links to it today regardless of
language). The 4,544 generated diary pages are explicitly out of scope
for hand translation; an English mode belongs in
`build_diary_pages.py` (e.g. `--lang en`) as a separate decision on
output shape (parallel tree vs. `_en` suffix) when that's picked up.
Full page inventory and rationale: `docs/i18n-todo.md`.

### 2. Extending live faceting past the wing pages

**Approach:** extract `mockup/js/category-catalogue.js`'s existing
faceting logic (already correct: OR-within-group, AND-across-groups,
adaptive availability, alphabet-bar sync) into a standalone
`mockup/js/facet-engine.js`, then wire pages to it in order of data
coverage rather than UI familiarity — diaries first (100% coverage on
place/person/work mentions and volume), not persons/places/search where
the underlying facets are currently invented or absent. Standardise
markup on the `data-facet`/`data-match` convention `romaner.html` already
uses. Two additions beyond what `category-catalogue.js` has today:
multi-valued fields (a diary page mentions many places) and a defined
"awaiting data" facet state — visible, disabled, dimmed, with a `title`
explaining what will switch it on — generalised from the existing
disabled "Begivenhedsdatoer" pill, for facets like nationality that are
correct in concept but have no backing data yet. No new dependency: the
mockup is opened over `file://`, which already rules out `fetch()`, hence
plain `<script>`-tag globals over an in-memory array. Full architecture,
including the `FacetEngine.create()` API shape: `docs/plan-live-facets.md`.

### 3. Closing the data-coverage gaps that block faceting

**Approach:** this is HCA-Diary-data-cleaning's work, not this repo's —
nationality and role/profession for persons (0/10,228 today), work
language (0/3,708), and place country (18% today) are all derived facts,
which the repo split assigns there. The one design choice that is this
repo's to make once that data lands is how to *not* ship it as fabricated
in the meantime: `docs/plan-live-facets.md` §2 already flags that the
nationality counts currently on `persons.html` (e.g. "Dansk 4.218") are
invented and must come off before any live facet ships, per the
fact-check rule in `CLAUDE.md` — visible-but-inert beats
plausible-but-wrong.

## Ongoing hygiene

- `mockup/irrelevant/` stays frozen — see `CLAUDE.md` and
  `mockup/irrelevant/README.md`. Don't propagate design, i18n, or
  facet-panel changes into it.
- External links keep following `docs/external-links.md` (new tab,
  discreet placement) as new pages gain provenance links.
- Any new script that derives a fact about the data (a coordinate, a
  language, a nationality, a segmentation, a category, a link) belongs in
  HCA-Diary-data-cleaning, not here — see the repo-split rule in
  `CLAUDE.md`. Only presentation-shaping code (HTML pages, JS card
  objects, denormalised JSON) belongs in this repo's `scripts/`.

## Longer-term direction

The two-repo split is the structural decision the earlier version of this
document was gesturing at (separating editorial data from transformation
scripts from application code) — it has now actually happened, driven by
what the pipeline needed rather than decided up front. From here, the
platform's growth is additive within that shape: more entity coverage,
more live facets, full bilingual parity, and — as `docs/onboarding-ole.md`
and `docs/genAi-query.md` anticipate — easier collaborator onboarding and
richer query surfaces on top of the same normalized star schema
(`docs/data-model/star-schema.md`). No architectural rework is anticipated
unless the data model itself needs to change.
