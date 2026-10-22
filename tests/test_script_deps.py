"""Every page that loads a script depending on HcaFilter must load
js/filter-logic.js first.

facet-engine.js and category-catalogue.js call HcaFilter at init time; if the
<script src="js/filter-logic.js"> line is missing (or comes later) the init
throws "HcaFilter is not defined" and the result list never renders. This
happened to persons*.html and places*.html after a merge dropped the line.

mockup/irrelevant/ is frozen and skipped (CLAUDE.md).
"""
import re
from pathlib import Path

MOCKUP = Path(__file__).parent.parent / "mockup"
NEEDS_FILTER_LOGIC = ("facet-engine.js", "category-catalogue.js")
SRC = re.compile(r'<script[^>]+src="js/([^"]+)"')


def _pages():
    for p in sorted(MOCKUP.glob("*.html")):
        yield p


def test_filter_logic_loads_before_its_users():
    problems = []
    for page in _pages():
        srcs = SRC.findall(page.read_text(encoding="utf-8"))
        users = [s for s in srcs if s in NEEDS_FILTER_LOGIC]
        if not users:
            continue
        if "filter-logic.js" not in srcs:
            problems.append(f"{page.name}: loads {users[0]} but not filter-logic.js")
        elif srcs.index("filter-logic.js") > srcs.index(users[0]):
            problems.append(f"{page.name}: filter-logic.js loads after {users[0]}")
    assert not problems, "\n".join(problems)
