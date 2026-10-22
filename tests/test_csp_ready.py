"""Guards for the site's Content-Security-Policy (docs/security.md).

CI injects a hash-based CSP into the bundled pages with
scripts/build_mockup/apply_csp.py. That policy only works while the source
stays free of the things it forbids, so this test fails the moment someone
adds one of them:

  - inline event-handler attributes (onclick=, onerror=, onsubmit=, ...)
  - javascript: URLs
  - eval() / new Function() in the site's own scripts
  - scripts, stylesheets or images loaded from a third-party host
    (Leaflet & co. are vendored under mockup/vendor/)

mockup/irrelevant/ is frozen and skipped (CLAUDE.md).
"""
import importlib.util
import re
from pathlib import Path

REPO = Path(__file__).parent.parent
MOCKUP = REPO / "mockup"
SKIP = {"irrelevant", "vendor", "diary-pages", "data"}

# Hosts a page may reference as an *image* (the CC badge in the footer).
IMG_HOSTS = {"licensebuttons.net"}


def _load_apply_csp():
    spec = importlib.util.spec_from_file_location(
        "apply_csp", REPO / "scripts" / "build_mockup" / "apply_csp.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sources(globs):
    for pat in globs:
        for p in sorted(MOCKUP.glob(pat)):
            if not (SKIP & set(p.relative_to(MOCKUP).parts)):
                yield p


def _html():
    return list(_sources(["*.html"]))


def _with_generator_template():
    yield from _html()
    yield REPO / "scripts" / "build_mockup" / "build_diary_pages.py"


_TAG = re.compile(r"<[a-zA-Z][^<>]*>")
_HANDLER = re.compile(r"""\son[a-z]{3,}\s*=""", re.I)


def test_no_inline_event_handlers():
    bad = []
    for p in _with_generator_template():
        text = p.read_text(encoding="utf-8")
        for m in _TAG.finditer(text):
            if _HANDLER.search(m.group(0)):
                bad.append("%s: %s" % (p.relative_to(REPO), m.group(0)[:80]))
    for p in _sources(["js/*.js"]):                  # markup built in JS strings
        for m in re.finditer(r"""<[a-z][^'"`]*?\son[a-z]{3,}=""", p.read_text(encoding="utf-8")):
            bad.append("%s: %s" % (p.relative_to(REPO), m.group(0)[:80]))
    assert not bad, "inline handlers are blocked by the CSP:\n" + "\n".join(bad)


def test_no_javascript_urls():
    bad = [str(p.relative_to(REPO)) for p in _with_generator_template()
           if re.search(r"""(href|src|action)\s*=\s*["']\s*javascript:""", p.read_text(encoding="utf-8"), re.I)]
    assert not bad, "javascript: URLs are blocked by the CSP: %s" % bad


def test_no_eval_in_site_scripts():
    bad = []
    for p in _sources(["js/*.js"]):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("//")[0]
            if re.search(r"(?<![\w.])eval\s*\(|\(\s*0\s*,\s*eval\s*\)|new\s+Function\s*\(", code):
                bad.append("%s:%d" % (p.relative_to(REPO), i))
    assert not bad, "eval/new Function need 'unsafe-eval': %s" % bad


def test_no_third_party_subresources():
    bad = []
    pat = re.compile(r"""<(script|link|img|iframe|source|video|audio)\b[^>]*?\b(?:src|href)\s*=\s*["'](https?:)?//([^/"']+)""", re.I)
    for p in _with_generator_template():
        for m in pat.finditer(p.read_text(encoding="utf-8")):
            tag, host = m.group(1).lower(), m.group(3).lower()
            if tag == "img" and host in IMG_HOSTS:
                continue
            if tag == "link" and "stylesheet" not in m.group(0).lower():
                continue                              # <link rel=canonical/alternate>
            bad.append("%s: <%s> from %s" % (p.relative_to(REPO), tag, host))
    for p in _sources(["js/*.js"]):
        for m in re.finditer(r"""\.(?:src|href)\s*=\s*['"]https?://([^'"/]+)""", p.read_text(encoding="utf-8")):
            bad.append("%s: loads from %s" % (p.relative_to(REPO), m.group(1)))
    assert not bad, "third-party loads break the CSP (vendor them):\n" + "\n".join(bad)


def test_vendored_leaflet_present():
    for name in ("leaflet.js", "leaflet.css", "leaflet.markercluster.js",
                 "MarkerCluster.css", "MarkerCluster.Default.css", "images/marker-icon.png",
                 "LICENSE-leaflet.txt", "LICENSE-markercluster.txt"):
        assert (MOCKUP / "vendor" / "leaflet" / name).is_file(), name


# ── apply_csp.py itself ────────────────────────────────────────────────────

def _directive(policy, name):
    for part in policy.split(";"):
        part = part.strip()
        if part.startswith(name + " "):
            return part
    raise AssertionError("no %s in policy" % name)


def test_apply_csp_hashes_every_inline_script_and_is_idempotent():
    mod = _load_apply_csp()
    page = ('<!DOCTYPE html><html><head><meta charset="UTF-8"><title>t</title></head><body>'
            '<script src="a.js"></script><script>var a = 1;</script>'
            '<script type="application/json">{"x":1}</script></body></html>')
    once = mod.apply_to_html(page)
    assert once.index("Content-Security-Policy") < once.index("<title>")
    assert once.count("sha256-") == 1                  # only the executable inline block
    assert "'unsafe-inline'" not in _directive(mod.policy_for(page), "script-src")
    assert "blob:" not in _directive(mod.policy_for(page), "script-src")
    assert mod.apply_to_html(once) == once


def test_apply_csp_covers_all_real_pages():
    mod = _load_apply_csp()
    for p in _html():
        html = p.read_text(encoding="utf-8")
        out = mod.apply_to_html(html)
        assert "Content-Security-Policy" in out, p.name
        for h in mod.inline_script_hashes(html):
            assert h in out, p.name
        if "cart-pdf.js" in html:
            assert "blob:" in _directive(mod.policy_for(html), "script-src"), p.name
