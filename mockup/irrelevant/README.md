# `mockup/irrelevant/` — retired files, excluded from all processing

> **Exclude everything in this folder from future processing.**
>
> Nothing here is part of the live mockup. Files in `mockup/irrelevant/`
> must be skipped by:
>
> - **Build scripts** — `scripts/build_mockup/*`, `scripts/build_all.py`,
>   and anything else that globs `mockup/**`. (As of this writing none of
>   them read `mockup/*.html` at all — they only *write* to `mockup/data/`.
>   `scripts/design_sync/apply_component.py`'s `--list-usages` scan is the
>   one that reads pages, and its `glob('*.html')` is non-recursive, so it
>   already skips this folder by construction. A future `**` glob would not.)
> - **Lint and test passes** — `tests/*.py`. `test_no_stale_person_refs.py`
>   excludes this folder via `_SKIP_DIRS`; any new lint should do the same.
> - **Link checking and audits** — these pages are intentionally unlinked;
>   an unreferenced file here is the expected state, not a finding to report.
> - **Design/documentation sweeps** — do not propagate CSS, markup, label
>   or rebrand changes into this folder. It is frozen, not maintained.
> - **Any future AI-assisted editing pass** — treat this folder as read-only
>   history. If a file here becomes relevant again, move it back out first
>   and rewire it deliberately, rather than editing it in place.
>
> The folder is kept in git (rather than deleted) so the design work isn't
> lost and the reasoning stays reviewable.

---

## Contents

### `romaner.html` — retired 2026-08-09

A full-page design mockup for a dedicated "Romaner og Noveller" register,
grouping novels by author (Dickens, Scott, Hugo, Goethe) across two
author-group tabs (H. C. Andersen / Andre Forfattere).

**Why it was retired.** It was the only page still linked from a wing that
had no connection to the real register: it loads **no data file at all** —
no `WORKS_EXTRA`, no `<script src="data/…">` anywhere in its 1.221 lines.
Every entry, count and author grouping in it is hand-authored static HTML.
That meant:

- It could never reflect register updates — its numbers were frozen at
  whatever was true when they were typed.
- It was the only work-listing page without cart/checkbox support, because
  its rows correspond to no `WORKS_EXTRA` entity and therefore have no
  `rid` to put in a cart.
- Its content was already duplicated, live and data-driven, by
  `bibliotek.html` filtered to the two Romaner H3 facets.

**What replaced it.** The three links that pointed here (two H2/H3 overview
rows and the "Åbn Romaner-register →" shortcut, all in `bibliotek.html`)
now tick the corresponding facet on `bibliotek.html`'s own live catalogue
and scroll to it — 33 HCA, 229 Andre, 262 combined, matching the counts
those rows advertise.

**What was preserved.** Its one genuinely distinct feature — browsing novels
by author — is now a real facet: `bibliotek.html` gained a **Forfatter**
facet (`data-facet-source="author"`, the same mechanism behind
`teater-musik.html`'s "Komponist / Forfatter"), listing all 331 distinct
authors in the wing, ranked by works.

**Known limitation, worth being explicit about:** the facet does *not*
fully reproduce this page's hand-curated grouping, because the underlying
data is sparser than the hand-authored mockup implied. Only 455 of
`bibliotek.html`'s 1.510 works (30 %) name an individual author; the rest
carry `author` == their H2 group. Concretely, of the four authors this page
grouped by, the live data has W. Scott (10 works) and V. Hugo (4), but only
one Dickens title in this wing and no Goethe at all. Improving that is a
data problem (`person_derived` coverage in the source register), not a UI
one — see `docs/data-model/cart-and-export.md` and the facet's own comment
in `bibliotek.html`.
