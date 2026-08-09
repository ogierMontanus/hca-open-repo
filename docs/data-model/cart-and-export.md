# Selection cart and PDF export

`mockup/js/cart.js` lets a reader tick individual entries on a list page
and collect them into a cart, reviewed and downloaded from `mockup/cart.html`.
Wired into `persons.html`, `places.html`, and — via the shared
`js/category-catalogue.js` — `bibliotek.html`, `billedkunst.html` and
`teater-musik.html` (works, including every H2/H3 genre subform: novels,
paintings, operas, and the rest). See "Not wired in yet" below for what
remains.

## What was actually asked for, and the two decisions made to answer it

The request bundled a feature spec with two open evaluation questions:
what storage mechanism keeps a selection alive across a browsing session
without a login system, and what "download as PDF" should actually mean
for this project. Both were tested empirically against this project's
real constraints rather than assumed.

### Why sessionStorage, not cookies

Cookies were evaluated and ruled out on a concrete test, not a general
preference: on a page opened via `file://` — this mockup's primary
deployment mode — `document.cookie` comes back **empty immediately
after being set**, in Chromium. Cookies do not work at all under
`file://`. Since the mockup has to work there, a cookie-based cart was
never viable regardless of its other trade-offs (4 KB size limit, sent
needlessly on every request on a real server, cross-session persistence
by default unless carefully scoped).

`sessionStorage` was tested the same way and holds up:

- **Persists correctly across navigation** between different `file://`
  pages in the same tab — round-tripped a value containing `æøå`
  correctly persons.html → places.html → cart.html.
- **Does NOT carry over to a new tab** — confirmed directly (a second
  tab opened to persons.html shows an empty cart badge). This is
  `sessionStorage`'s normal, spec-defined behaviour (tab-scoped, not
  origin-scoped), and it happens to be exactly the boundary the request
  asked for: "remember my selection for this visit" without drifting
  into "remember it forever" or needing an account. The cart follows
  one browser tab's navigation history, not a login identity — worth
  knowing, not a bug.

No user system, no login, no server round-trip. `Cart` degrades to a
no-op (checkboxes still render, nothing persists) if `sessionStorage`
throws — some privacy-mode configurations disable it — rather than
breaking the page; see `Cart.storageAvailable`.

### Why "download as PDF" means the browser's print dialog, not a JS PDF library

Researched three client-side options (jsPDF, pdfmake, html2pdf.js) before
picking. The blocking finding: **the 14 standard PDF fonts jsPDF/pdfmake
ship with are ASCII-only** — anything outside that (æ, ø, å included)
needs a custom font embedded as a base64-encoded TTF. That is a real,
non-trivial cost for a register whose entire content is Danish.
`html2pdf.js` sidesteps the font problem by rasterising the page to an
image via `html2canvas` first, but the trade-off is a PDF with no
selectable/searchable text — a bad fit for a reference register people
will want to search or copy from.

`cart.html`'s "Download som PDF" button instead calls `window.print()`
against a `@media print` stylesheet that hides site chrome and formats
the list cleanly. The reader picks "Save as PDF" as the print
destination — built into Chrome/Edge/Firefox's print dialog on every
major OS. This produces a **real text PDF**, rendered by the browser's
own font stack (so æøå are simply correct, no embedding needed), with
zero new dependencies — consistent with this project's existing
"stdlib only / no dependencies" convention (`facet-engine.js`'s own
docstring states the same preference for the mockup's JS). The one
real cost, stated plainly in-page rather than glossed over: it's one
extra click (choosing "Save as PDF" in the dialog) instead of an
instant automatic file download.

**Upgrade path, if a literal one-click `.pdf` download is wanted
later:** jsPDF via CDN (this project already loads Leaflet from
`unpkg.com`, so a CDN dependency is precedented) with a Danish-capable
embedded font — DejaVu Sans covers Latin Extended-A, which includes
æøå. Convert once with jsPDF's own `fontconverter.html`, commit the
resulting base64 JS file alongside `cart.js`. Not built now because it
adds a real asset and a real dependency for a capability the browser's
own print dialog already provides "at first," per the request's own
framing.

## Architecture

```
mockup/js/cart.js          shared module — window.Cart
mockup/cart.html            review / remove / download page
mockup/persons.html         checkbox per row + "Vælg alle"
mockup/places.html          checkbox per row + "Vælg alle"
mockup/css/style.css        .result-row / .result-card__select /
                             .result-row--in-cart / .cart-badge (shared)
```

### Storage shape

`sessionStorage['hca-cart-v1']` — a JSON array of `{type, rid, label}`,
insertion order. `label` is cached at add-time so `cart.html` can list
entries without every `*_EXTRA` data file loaded. Versioned key name so
the format can change later without needing to migrate old carts (a
version bump would just start a fresh cart, quietly — matching sessionStorage's
own "these are all disposable" nature).

### Markup contract: checkbox as a sibling, not nested inside the card link

```html
<div class="result-row">
  <label class="result-card__select">
    <input type="checkbox" data-cart-type="person" data-cart-rid="Reg…" data-cart-label="…">
  </label>
  <a class="result-card" href="…">…</a>
</div>
```

The checkbox sits **beside** `.result-card`'s `<a>`, not inside it. An
`<input>` nested inside an `<a>` is valid HTML, but clicking it also
fires the ancestor link's own click handling unless that's explicitly
cancelled — a real, easy-to-miss source of "checking a box navigates
me away" bugs. Keeping them siblings sidesteps the problem instead of
working around it: verified directly that clicking a checkbox never
navigates (`page.url` unchanged after the click) — a check made
because the fix is easy to get subtly wrong and worth confirming
rather than assuming from the markup shape alone.

### Wiring per page (persons.html / places.html)

1. `<script src="js/cart.js"></script>`, after the page's other
   optional data/helper scripts.
2. `Cart.mountBadge(document.getElementById('js-cart-badge'))` — once,
   near the top of the page's script, **before** any early return that
   depends on the page's own data being loaded (`typeof PERSONS_EXTRA
   === 'undefined'`, etc.) — the cart badge should reflect the cart
   even if this page's own list can't render, since the cart may hold
   items added from a different page.
3. `card(p)` wraps its existing `<a class="result-card">` output in the
   `.result-row` / `.result-card__select` markup above.
4. `renderMore()` calls `Cart.syncCheckboxes(grid)` after inserting new
   cards, so a card that gets (re-)rendered after a filter change shows
   its true cart state rather than defaulting to unchecked.
5. `render(rows, st)` (the FacetEngine `onChange` callback) calls a
   page-local `updateSelectAll()` after every re-render, in both the
   populated and empty-state branches.
6. `Cart.wireCheckboxes()` and `Cart.subscribe(updateSelectAll)`, once,
   at page-script setup.

### "Vælg alle" semantics

The select-all checkbox means "every currently **filtered** entry," not
"every currently **rendered** entry" — persons.html and places.html
both paginate ("Vis flere," 60 at a time), so a reader filtering to 223
French persons and ticking "Vælg alle" should get all 223, not the 60
on screen. Implemented against the page's own `filtered` array, with a
confirmation dialog above 100 items (tested: declining leaves the cart
and the checkbox both untouched) so an accidental click on an
unfiltered 10,228-row list can't silently balloon the cart. The
checkbox's own state is tri-state — checked / unchecked /
indeterminate — reflecting how much of the filtered set is already in
the cart, recomputed via `Cart.subscribe()` after every cart mutation
from any source (including a checkbox ticked individually).

## Verified (Playwright, against `file://` — the real deployment mode)

- Checking/unchecking a card checkbox updates the cart badge live and
  toggles the `.result-row--in-cart` highlight; never navigates.
- Cart persists correctly navigating persons.html → places.html →
  cart.html in one tab; a **second tab** starts with an empty cart
  (expected `sessionStorage` tab-scoping, not a bug).
- "Vælg alle" adds every filtered entry (not just the rendered page);
  the >100 confirmation, when declined, leaves everything unchanged —
  re-verified specifically on billedkunst.html with an H3 facet active
  (587 works, real accept/decline dialog handling, not just the
  single-page-of-persons case).
- Cart accumulates correctly across all five wired pages in one tab —
  checked entries on bibliotek.html, billedkunst.html and
  teater-musik.html in sequence and watched the badge climb 2 → 4 → 6.
- `cart.html` groups by type, lets individual items be removed, and its
  "Download som PDF" button calls `window.print()` (verified by
  stubbing `window.print` and asserting it was invoked). With one of
  each type in the cart, groups render in the correct fixed order
  ("Personer (1)", "Værker (587)", "Steder (1)") and each item's href
  points at the right detail page (`work.html?reg=…` for a work).
- Empty-cart state renders correctly with links back to the two list
  pages.

## Works: one shared file covers three pages and every genre subform

`bibliotek.html`, `billedkunst.html` and `teater-musik.html` don't each
build their own card-rendering logic the way `persons.html`/`places.html`
do — they share `mockup/js/category-catalogue.js`, one module reading
`WORKS_EXTRA` and filtering by the H2/H3 facets each page declares.
Wiring the cart into that ONE file (checkbox in `card()`, `Vælg alle`
against the page's own `filtered` array, `Cart.mountBadge()`) put it on
all three at once, which is exactly what "works incl. its genre
subitems" needs: `bibliotek.html`'s H3 facets are the individual genres
(Eventyr, Digte, *Romaner og Noveller*, Skuespiltekster, Faglitteratur,
…), `billedkunst.html`'s are *Malerier og Tegninger*, Skulptur, Museer,
and `teater-musik.html`'s are Operaer, Skuespil, Balletter,
Vokal-/Instrumentalmusik — the checkbox and `Vælg alle` work identically
across every one of them, filtered or not, because they're all the same
`filtered` array underneath.

`cart.html` groups a `work` entry under **Værker**, in the same
Hvem·Hvad·Hvor order the rest of the site uses for the three entity
types (side-acc accordion, `nation.html`).

One real bug this surfaced: `Cart.mountBadge()` is called from inside
`category-catalogue.js` itself (unlike `persons.html`/`places.html`,
where the equivalent call sits in the page's *own* inline script,
already after every `<script src>` tag). `cart.js` has to be loaded
**before** `category-catalogue.js` for that call to see `window.Cart`
as anything but `undefined` — got the include order backwards on the
first pass, and the failure was silent (the `typeof Cart !== 'undefined'`
guard just skipped the mount, no error, badge quietly stayed empty).
Caught by checking the badge's actual `outerHTML` after load rather
than trusting that "no console errors" meant "it worked."

## Not wired in yet

- **`romaner.html`** — looked like an obvious fourth target (it's
  linked from `bibliotek.html` as "Åbn Romaner-register →" for the full
  Romaner og Noveller listing) but turned out not to be one: it loads no
  `WORKS_EXTRA` or other data file at all — no `<script src="data/…">`
  anywhere in it. Its author-tabbed sections (H.C. Andersen / Andre
  Forfattere) and every entry in them are hand-authored static HTML, not
  generated from the register. Adding checkboxes would mean hand-adding
  correct `data-cart-rid` values to a page that isn't a real "list of
  hits" in the sense the other pages are — it's a design mockup for a
  page concept, and the actual Romaner og Noveller data already has a
  wired, real, data-driven listing: `bibliotek.html` filtered to that H3.
  Bringing `romaner.html` onto real data (or retiring it in favour of the
  `bibliotek.html` filter) is a separate, larger job than adding a
  checkbox to markup that doesn't correspond to `WORKS_EXTRA` entities.
- **`diaries.html` / `entry.html` / `search.html`** — also render
  `.result-card` grids (diary pages, free-text search hits) but are a
  different kind of "hit" (a diary page, not a register entity with its
  own `?reg=` page) and were out of scope for this pass, which was about
  the three register types. `Cart`'s `type` field is a free string, not
  hardcoded to `person`/`place`/`work`, so wiring a fourth type later is
  the same six-step pattern — plus adding its label/href to `cart.html`'s
  `TYPE_LABEL`/`TYPE_HREF` maps, which an unlisted type survives missing
  (renders grouped under its raw type string rather than being silently
  dropped).
