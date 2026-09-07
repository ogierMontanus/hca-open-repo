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

## Near-term (next to pick up)

Ordered by what's both scoped and already documented elsewhere — each
line links to where the detail lives.

1. **Finish English parity for the detail pages.** `work.html` and
   `place.html` are the single biggest remaining seam: every translated
   list page (`works_en.html`, `places_en.html`, `diaries_en.html`) links
   through to a fully Danish detail page today. See `docs/i18n-todo.md`
   for the recommended order.
2. **Extend live faceting past the wing pages**, starting where data
   coverage already supports it (diaries: 100% coverage on place/person/
   work mentions and volume) rather than where the facet already exists
   in hardcoded form. `docs/plan-live-facets.md` has the coverage table
   and names the extraction from `category-catalogue.js` into a
   reusable engine as the actual work, not new design.
3. **Close the data-coverage gaps that block faceting**, in
   HCA-Diary-data-cleaning, not here: nationality and role/profession for
   persons (0/10,228 today), work language (0/3,708), and place country
   (18% today). These are enrichment facts, so per the repo split they
   are that repo's work, published back through `scripts/publish.py`.
4. **Decide on `persons_wikidata.csv`.** The facet it feeds is currently
   empty because the file is absent (`build_all.py --check-inputs`
   reports it as optional-and-missing). Verify any Wikidata IDs added
   for it via the `wikidata-verify` skill before publishing, per
   `CLAUDE.md`.
5. **Decide on `timeline-index.js`.** `build_mockup/build_timeline_index.py`
   already builds it from `data/normalized_v092/timeline.csv`, but it has
   never been wired into `build_all.py` or CI, so the deployed site has
   never carried it (`docs/pipeline/README.md`). Wiring it in is a
   publishing decision, separate from the code already existing.

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
