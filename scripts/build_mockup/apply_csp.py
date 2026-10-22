#!/usr/bin/env python3
"""
Inject a Content-Security-Policy <meta> into every HTML page under a directory.

GitHub Pages cannot send response headers, so the policy is delivered as a
<meta http-equiv="Content-Security-Policy"> placed first in <head>. Inline
<script> blocks are allowed by their SHA-256 hash (no 'unsafe-inline' for
scripts), so the hashes must be computed from the pages as they will be
served: CI runs this on the bundled _site/mockup copy, never on the source
tree, which means an edit to an inline script can never leave a stale hash.

    python scripts/build_mockup/apply_csp.py _site/mockup

Policy (see docs/security.md for the reasoning):
  - scripts:  same-origin files + the pages' own inline blocks (by hash);
              no eval, no inline event handlers, no third-party hosts
  - the cart pages additionally allow blob: (the in-browser PDF export runs
    pdfmake from a Blob worker / Blob script)
  - connect/img/font: same-origin (+ data:/blob:, and the Creative Commons
    badge host for images); nothing can phone home
  - object-src none, base-uri/form-action self

`mockup/irrelevant/` is frozen (CLAUDE.md) and skipped.
"""
import base64
import hashlib
import pathlib
import re
import sys

SKIP_DIRS = {"irrelevant"}
META_MARK = 'http-equiv="Content-Security-Policy"'

# <script ...>body</script> with no src= -> inline code. Data blocks
# (type="application/json", "application/ld+json", ...) are not executed.
_SCRIPT = re.compile(r"<script\b([^>]*)>(.*?)</script\s*>", re.S | re.I)
_EXISTING_META = re.compile(r'\n?[ \t]*<meta\s+http-equiv="Content-Security-Policy"[^>]*>', re.I)
_CHARSET = re.compile(r"<meta\s+charset=[^>]*>", re.I)
_HEAD = re.compile(r"<head\b[^>]*>", re.I)
_JS_TYPES = {"", "text/javascript", "application/javascript", "module"}


def _is_inline_js(attrs):
    if re.search(r"\bsrc\s*=", attrs, re.I):
        return False
    m = re.search(r"\btype\s*=\s*[\"']?([^\"'\s>]*)", attrs, re.I)
    return (m.group(1).lower() if m else "") in _JS_TYPES


def inline_script_hashes(html):
    out = set()
    for m in _SCRIPT.finditer(html):
        if _is_inline_js(m.group(1)) and m.group(2).strip():
            digest = hashlib.sha256(m.group(2).encode("utf-8")).digest()
            out.add("'sha256-" + base64.b64encode(digest).decode("ascii") + "'")
    return sorted(out)


def policy_for(html):
    script_src = ["'self'"] + inline_script_hashes(html)
    if "cart-pdf.js" in html:
        script_src.append("blob:")
    return "; ".join([
        "default-src 'self'",
        "script-src " + " ".join(script_src),
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob: https://licensebuttons.net",
        "font-src 'self' data:",
        "connect-src 'self'",
        "worker-src 'self' blob:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ])


def apply_to_html(html):
    html = _EXISTING_META.sub("", html)
    meta = '<meta %s content="%s">\n' % (META_MARK, policy_for(html).replace('"', "&quot;"))
    m = _CHARSET.search(html)
    if m:                                    # keep charset in the first 1024 bytes
        return html[:m.end()] + "\n  " + meta.rstrip("\n") + html[m.end():]
    m = _HEAD.search(html)
    if not m:
        return html                          # fragment, not a page
    return html[:m.end()] + "\n  " + meta.rstrip("\n") + html[m.end():]


def iter_pages(root):
    for p in sorted(pathlib.Path(root).rglob("*.html")):
        if SKIP_DIRS & set(p.relative_to(root).parts):
            continue
        yield p


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    root = pathlib.Path(argv[1])
    n = 0
    for p in iter_pages(root):
        src = p.read_text(encoding="utf-8")
        new = apply_to_html(src)
        if new != src:
            p.write_text(new, encoding="utf-8")
            n += 1
    print("CSP applied to %d page(s) under %s" % (n, root))


if __name__ == "__main__":
    main(sys.argv)
