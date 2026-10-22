"""Every page that loads js/facet-engine.js must load js/filter-logic.js first.

facet-engine.js calls HcaFilter.* unguarded (HcaFilter is defined by
js/filter-logic.js). A page that loads the engine without the logic file
throws "HcaFilter is not defined" while wiring the facets, before the first
render, so the result list stays empty although the header count is right.

That happened on persons.html / persons_en.html / places.html /
places_en.html after the AND/OR operators landed (88cac9c): only the category
catalogues had been given the new script tag.

mockup/irrelevant/ is frozen and skipped (CLAUDE.md).
"""
import re
from pathlib import Path

MOCKUP = Path(__file__).parent.parent / "mockup"
SKIP = {"irrelevant", "vendor", "diary-pages"}

_SRC = re.compile(r"""<script\b[^>]*\bsrc\s*=\s*["']([^"']+)["']""", re.I)


def _pages():
    for p in sorted(MOCKUP.rglob("*.html")):
        if not (SKIP & set(p.relative_to(MOCKUP).parts)):
            yield p


def test_filter_logic_precedes_facet_engine():
    bad = []
    for page in _pages():
        srcs = _SRC.findall(page.read_text(encoding="utf-8"))
        if "js/facet-engine.js" not in srcs:
            continue
        if "js/filter-logic.js" not in srcs:
            bad.append("%s: js/filter-logic.js is not loaded" % page.name)
        elif srcs.index("js/filter-logic.js") > srcs.index("js/facet-engine.js"):
            bad.append("%s: js/filter-logic.js loads after js/facet-engine.js" % page.name)
    assert not bad, "facet-engine.js needs HcaFilter:\n  " + "\n  ".join(bad)
