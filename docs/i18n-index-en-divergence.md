# index_en.html — regeneration notes and known divergence from index.html

Status: current · 2026-08-24

## What happened

`index_en.html` was created early in the site's history (see
`892dcf8 Add English landing page skin with WWW typographic concept`) and
was never updated as `index.html` (the Danish landing page) gained new
sections. By 2026-08-24 the two had drifted apart structurally, not just
lexically:

- `index_en.html` had **no search wiring** — no `data/search-index.js` /
  `js/site-search.js` script tags, no `#landing-typeahead` container, no
  `id="landing-search-input"` on the search field. The Danish page's
  typeahead (populated as you type, ↑/↓/Enter/Esc) simply did not exist
  on the English one; the search box was a dead `<form onsubmit="return
  false">`.
- It was missing the **"Hvornår"/"When" slim row** below the three cards.
- Its bottom nav strip differed: `Diaries · Search · Timeline (#) · Map (#)
  · Full index` (two dead placeholder links) instead of the current
  Danish `Dagbøger · Kort · Nationer`.
- It had an extra header link ("Full index →") that the current Danish
  header does not have.
- Its footer lacked the "Vores kilder"/"Our sources" → `om.html` link.
- Every count (persons/places/works/diary refs.) was stale relative to
  the current `entities.csv`-derived numbers on `index.html`.

`index_en.html` was regenerated from the **current** `index.html`
structure on 2026-08-24 to close all of the above. This file records
what was deliberately kept, what was translated, and what is still a
known, accepted gap.

## Deliberately kept, not re-translated

Per the request that triggered the regeneration, the **hero title
treatment** — "Andersen's" / a decorative "W  W  W" display line /
"**W**ho — **W**hat — **W**here" subtitle with bold accent-coloured W's,
and each card heading's leading bold "**W**" (Who/What/Where) — is the
original English concept from `892dcf8`, not a literal translation of
the Danish "Hvem — hvad — hvor?". It reads naturally in English in a way
a direct translation wouldn't, so it was carried over as-is along with
its supporting CSS (`.landing-www`, `.landing-subtitle .w`,
`.landing-card__heading .w`), including the taller hero
(`min-height: 48vh` vs. the Danish page's `46vh`) and wider inner column
(`max-width: 660px` vs. `640px`) that make room for the extra WWW line.
The `<title>` tag wording is likewise unchanged.

Everything else — card labels, list items, example chips, nav strip,
footer, counts — was rebuilt to match the current Danish content and
structure, translated fresh rather than patched.

## Translation choices worth recording

- "poster i dagbøgerne" → "diary refs." (abbreviated, matches the
  original EN page's card style, not spelled out as "diary references")
- "registerposter" (Hvad-card count) → "register entries"
- Static/illustrative example chips (not live data) were anglicized per
  the precedent set in `search_en.html`/`places_en.html` earlier in this
  translation effort: Rom → Rome, Nizza → Nice. Person-name examples
  (Edvard Collin, Jenny Lind) were put in natural first-last order
  rather than the register's `Efternavn, Fornavn` form, since these are
  flavour text, not register labels.
- "Improvisatoren" (Andersen's novel, in the search placeholder) →
  "The Improvisatore", its standard published English title.
- "Hvornår" → "When" (not "Timeline", to keep the four-card parallelism
  with Who/What/Where; "Timeline" appears inside the row's own example
  text instead: "Timeline of travels").

## Cross-links: which `_en.html` twins exist today

Only `persons_en.html` exists alongside `index_en.html` as of this
regeneration. Every other link on the page necessarily still points at
the Danish page:

| Card / nav item | Target | Twin exists? |
|---|---|---|
| Who | `persons_en.html` | yes |
| What | `works.html` | no |
| Where | `places.html` | no |
| Diaries | `diaries.html` | no |
| Map | `kort.html` | no |
| Nations | `nation.html` | no |
| Our sources (footer) | `om.html` | no |

As more `_en.html` pages are built, these links need a pass to re-point
at their English twins — see the open-pages "To Do" list.

## Known, accepted gap: search results and the typeahead itself stay Danish

`js/site-search.js` is one shared file loaded by every page, Danish and
English alike. Regenerating `index_en.html` did **not** make it
language-aware, because doing so touches the typeahead on every other
page on the site — out of scope for a landing-page regeneration and
riskier than the benefit justifies right now. Concretely, on
`index_en.html` today:

- The typeahead's own chrome strings are hardcoded Danish:
  `"Populære registerposter"` (populated on focus), `"N forslag"` (as
  you type), `"Ingen registerposter matcher…"` (no matches),
  `"Søgeindekset er ikke bygget endnu."` (index not built), and the
  per-row type badges `Person` / `Sted` / `Værk`.
- Every suggestion links to the **Danish** detail page
  (`TYPE_HREF = { p: 'persons.html', s: 'place.html', w: 'work.html' }`
  in `site-search.js`) regardless of which language page the search was
  started from.

This mirrors the underlying-data rule in `docs/i18n-policy.md` (data and,
by extension, data-driven chrome stays Danish until a machine-translation
procedure is chosen) but is being written down explicitly here since it
is not obvious from reading `index_en.html` alone — the search *box* looks
fully bilingual-ready now that the wiring is fixed, but what drops out of
it is not yet.
