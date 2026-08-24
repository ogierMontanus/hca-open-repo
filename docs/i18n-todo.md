# English translation — status and remaining work

Status: current · 2026-08-24

Tracks progress on `docs/i18n-policy.md`'s architecture decision (full
duplicate `_en.html` files per page, not a shared runtime lang-toggle).
See also `docs/i18n-index-en-divergence.md` for `index_en.html`
specifically.

## Done: the five highest-traffic pages, plus the landing page

Chosen by grepping `index_en.html`'s own landing-card/nav hrefs — these
are the pages a reader reaches directly from the front door.

| Page | English twin | Notes |
|---|---|---|
| `index.html` | `index_en.html` | Regenerated from the current Danish structure; original English "W W W" hero title concept kept, not re-translated |
| `works.html` | `works_en.html` | Register overview — static, no live JS |
| `search.html` | `search_en.html` | Static demo results page |
| `places.html` | `places_en.html` | Full JS: FacetEngine, alphabet bar, list/table switcher |
| `persons.html` | `persons_en.html` | Full JS, including the `?reg=` detail view and its sidebar restructuring |
| `diaries.html` | `diaries_en.html` | Largest: List/Table/Calendar/Timeline switcher + the calendar-grid widget |

All six cross-link to each other's `_en.html` twin; the DA lang-switch
link on each page intentionally still points at the Danish original.

## Not yet translated

### Individual entity detail pages

These render one register entry (`?reg=Reg0…`) and are linked to from
*everywhere* — every result card, chip, and search hit across the whole
site, Danish and English pages alike.

| Page | Lines | Live JS | Priority reasoning |
|---|---|---|---|
| `work.html` | 689 | yes | Linked from every work-related card/chip on every translated page today |
| `place.html` | 402 | yes | Same, for places — including places_en.html's own card links |
| `person.html` | 351 | yes | Note: `persons_en.html` already self-hosts an English `?reg=` detail view, so this is the *secondary/legacy* detail page — lower urgency than work.html/place.html, which have no such duplicate |
| `entry.html` | 194 | no (static) | One diary-page detail view; linked from every diary result card |

**Recommended next priority: `work.html` and `place.html`.** A reader
clicking through from `works_en.html`/`places_en.html`/`diaries_en.html`
today lands on a fully Danish detail page — the single biggest remaining
seam in the English experience, since these two have no partial
workaround the way `person.html` does.

### Wing / category pages (Work Register sub-divisions)

| Page | Lines | Live JS |
|---|---|---|
| `billedkunst.html` | 282 | yes — plus `js/hero-examples.js`, image-driven |
| `teater-musik.html` | 248 | yes |
| `bibliotek.html` | 376 | yes |

Linked from every `works_en.html` wing card. Similar JS complexity to
`places_en.html`; same copy-then-verified-substitution approach applies.

### Utility / tool pages

| Page | Lines | Live JS | Notes |
|---|---|---|---|
| `nation.html` | 643 | yes | Person+place mashup per nation; largest of this group |
| `cart.html` | 432 | yes | Shopping-cart equivalent; shared `js/cart.js` state, no data translation needed |
| `kort.html` | 206 | yes | Map view |
| `om.html` | 189 | no | "Our sources" — footer link target from every page, Danish and English alike today |

`om.html` is worth doing early despite its low traffic: it's the one
Danish page every single `_en.html` footer links to right now.

### Explicitly out of scope: generated diary pages

`mockup/diary-pages/*.html` — **4,544 auto-generated files**, one per
diary page, built by `scripts/build_mockup/build_diary_pages.py` (or
equivalent). Hand-translating these is not viable; this needs an English
mode added to the generating script instead (e.g. an `--lang en` flag
producing a parallel `diary-pages-en/` tree, or an `_en` suffix per
file — an actual choice to make when this is picked up, not decided
here). Not attempted in this pass.

## Explicitly out of scope: `mockup/irrelevant/`

Per `CLAUDE.md`, everything under `mockup/irrelevant/` (including the
retired `romaner.html`) is frozen history and excluded from all
processing, translation included.

## Known cross-cutting limitations (apply to every `_en.html` page, not just one)

- **`js/site-search.js` is shared and not language-aware.** Typeahead
  chrome strings and result links stay Danish even on English pages —
  documented in detail in `docs/i18n-index-en-divergence.md`.
- **`js/diary-wire.js`'s undated-page fallback heading** ("Bind X, s. Y")
  is shared and untranslated. Any English page rendering diary
  references for an undated page (most of them — only vols. VI–VII are
  dated today) will show that Danish fragment as the heading. Seen and
  documented directly in `diaries_en.html`'s calendar-view code.
- **Underlying register data stays Danish** per `docs/i18n-policy.md`
  (person/place names, nationality vocabulary, etc.) until a
  machine-translation procedure is chosen. Only UI chrome and static/
  illustrative demo text get translated.

## When picking this back up

1. Recheck this file's "remaining" list against the actual repo state
   first — pages get added/renamed over time and this snapshot will
   drift, the same way the now-superseded assumption that `works_en.html`
   etc. already existed did earlier in this effort.
2. Re-run the cross-link sweep (grep every `_en.html` for
   `href="X.html"` where an `X_en.html` twin exists) after adding any
   new page — each new translated page potentially un-staleifies links
   on every *earlier* one, as happened when `diaries_en.html` landed
   last and several earlier pages still pointed at Danish `diaries.html`.
