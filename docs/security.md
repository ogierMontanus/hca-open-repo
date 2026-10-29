# Security notes

The site is a static bundle on GitHub Pages: no server, no accounts, no
cookies. The attack surface is therefore (1) what the pages load and run in
the visitor's browser, and (2) the build pipeline that produces the bundle.

## Browser side

### No third-party code

Every script, stylesheet, font and image the pages use is served from the
site itself. Leaflet 1.9.4 and Leaflet.markercluster 1.5.3 are vendored in
`mockup/vendor/leaflet/` (byte-identical to the unpkg releases; licences sit
next to them), alongside the basemap and pdfmake. Do not add a `<script>` or
`<link>` pointing at a CDN — `tests/test_csp_ready.py` fails if you do.
The only remote resource is the Creative Commons badge image in the footer
(`licensebuttons.net`); outbound `<a href>` links are unaffected.

To upgrade Leaflet: download the new `dist/` files from the release, replace
the files in `mockup/vendor/leaflet/`, and check the map pages in a browser.

### Content-Security-Policy

GitHub Pages cannot set response headers, so `scripts/build_mockup/apply_csp.py`
injects a `<meta http-equiv="Content-Security-Policy">` into every page of the
**CI output** (`_site/mockup`). The source pages carry no policy, so local
`file://` development is unaffected and hashes can never go stale.

| Directive | Value | Why |
|---|---|---|
| `script-src` | `'self'` + `sha256-…` of each page's inline scripts (+ `blob:` on the cart pages) | an injected `<script>`, inline handler or `eval` does not run |
| `connect-src` | `'self'` | scripts cannot send data anywhere else |
| `img-src` | `'self' data: blob: https://licensebuttons.net` | no tracking pixels / image exfiltration |
| `worker-src` | `'self' blob:` | the cart PDF is built in a Blob worker |
| `style-src` | `'self' 'unsafe-inline'` | pages use inline `style=`; CSS cannot execute code |
| `object-src`, `base-uri`, `form-action` | `'none'`, `'self'`, `'self'` | no plugins, no `<base>` hijack, no form redirect |

`frame-ancestors` is ignored in a `<meta>` policy, so clickjacking protection
is not provided (nothing on the site is sensitive to it).

Rules that follow from the policy — enforced by `tests/test_csp_ready.py`:

* No inline event handlers (`onclick=`, `onerror=`, `onsubmit=` …). Attach
  listeners in script. Search forms use `data-no-submit` + `js/no-submit.js`.
* No `javascript:` URLs, no `eval()` / `new Function()`. The cart's no-worker
  PDF fallback runs pdfmake from a `blob:` script instead of `eval`.
* No scripts/styles/images from other hosts.

Edits to an inline `<script>` need no extra step: CI recomputes the hash.

### Rendering data

HTML built in script escapes every value taken from data or from the URL
(`esc()` / `escapeHtml()` helpers). Values from `location.search` /
`location.hash` that go into a CSS attribute selector use `CSS.escape()`.

## Build side

* **Hash-locked installs.** CI installs `scripts/ci/requirements.txt` with
  `pip install --require-hashes`. Regenerate it after changing
  `scripts/parsers/requirements.txt` or `scripts/requirements-ci.txt`:

  ```powershell
  python -m pip install pip-tools
  pip-compile --generate-hashes --strip-extras `
      --output-file scripts/ci/requirements.txt scripts/ci/requirements.in
  ```

  Use the same Python minor version as `build-mockup.yml` (3.12). Dependabot
  opens weekly PRs that bump the lock.
* **Local installs** keep using the plain range files
  (`scripts/parsers/requirements.txt`, `scripts/build_mockup/requirements-pdf.txt`,
  `scripts/requirements-dev.txt`), which work on Windows/PowerShell as before.
* **Vulnerability audit.** `.github/workflows/security-audit.yml` runs
  `pip-audit` on every requirements file weekly, on `main` pushes and on PRs
  that touch them.
* **Workflows.** Actions are pinned to commit SHAs (Dependabot bumps them),
  the build job has a read-only token, and only the separate `deploy` job
  holds the Pages/OIDC write scopes and runs no repository code.

## Crowdsourcing server (optional)

The static site stays as described above. `scripts/crowdsource/server.py`
is an *optional*, separately run process (docs/crowdsourcing.md §8–9) that
serves `mockup/` and a JSON API under `/api/crowd/` — it is not part of the
Pages deployment, and without it the crowd pages fall back to a browser-local
mode. The pages remain CSP-clean: same-origin `fetch` only (`connect-src 'self'`),
no inline handlers, all data through `esc()`.

* Contributions are validated server-side (`validate.py`): schema, lengths,
  `http(s)`-only URLs, whitelisted attachment types and size, sanitised file
  names; ids are matched against a fixed pattern before touching the file system.
* Review and export endpoints need the editor key (`HCA_CROWD_ADMIN_TOKEN`,
  compared in constant time); contributor tokens are stored only as SHA-256.
* The prototype binds to `127.0.0.1`, speaks plain HTTP, runs one process and
  has no rate limiting: **put TLS, an identity provider and a rate limit in
  front of it before exposing it.**
* `data/crowdsource/` holds names, contact details and unreviewed claims and is
  git-ignored; only editor-approved rows reach `data/curated/`.

### GitHub-login Worker (optional, `workers/crowd-api/`)

An alternative back-end for the same API (docs/crowdsourcing-login-plan.md). The
pages then call one extra origin: `scripts/build_mockup/apply_csp.py` reads
`apiBase` from `mockup/js/crowd-config.js` and adds exactly that **https** origin
to `connect-src` on pages that load `crowd-store.js` (anything else in the file —
`http:`, paths, extra directives — is ignored). The rest of the policy is unchanged.

* OAuth `client secret`, the data-repo token and the session-signing key live only
  as Worker secrets. The GitHub access token is used once for `GET /user` and discarded.
* Login: signed `state` bound to a `HttpOnly; Secure; SameSite=Lax` nonce cookie (login CSRF),
  return URL restricted to the configured origin + path prefix (no open redirect), session handed
  back in the URL **fragment** (never sent to a server or logged), 7-day HMAC-signed token.
* Authorisation: bearer token only (no cookies on the API, so no CSRF); the editor role is derived
  from `ADMINS` on every request, never from the token; contributors can read and change only their
  own submissions; 30 open submissions per account, 256 kB per request.
* Storage: a **private** repository — the branches of a public repository are public — written only
  with the Worker's fine-grained token (Contents, that one repository).
* The session token sits in `localStorage` (like the reference server's contributor token); an XSS
  would expose it, which is why the script/CSP rules above matter for these pages.

## Not covered

* `web/` is the original prototype; its `index.html` is replaced by the
  redirect in the bundle and is not part of the live site. It still loads
  Leaflet from unpkg (with SRI) and OpenStreetMap tiles.
* Clickjacking (see above) and HTTP response headers in general: would need a
  host that can set headers (e.g. Cloudflare Pages / Netlify `_headers`).
