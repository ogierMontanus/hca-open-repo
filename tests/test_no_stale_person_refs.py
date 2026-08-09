#!/usr/bin/env python3
"""Lint check: no source file may link to the old person.html detail page.

The singular person.html was superseded by persons.html, which now serves
both the full register list and individual-person detail views (?reg=…).
All href / link targets and JS string literals must use persons.html.

Checked locations:
  mockup/**/*.{html,js}   — source pages and scripts (diary-pages/ excluded:
                            generated; fix the generator instead)
  scripts/**/*.py         — build scripts that emit href strings

The test flags two patterns:
  href="person.html…" / href='person.html…'   in HTML attributes
  'person.html'  /  "person.html"             as JS / Python string literals

Known false positives avoided:
  - The redirect stub mockup/person.html itself
  - Lines whose only content is a code comment (// … or # …)
  - Documentation files (.md, .txt, .yml)

Example violation caught by this test:
  mockup/work.html?reg=Reg003004 rendered a link
  "← Alle værker af Raffael" pointing to person.html?reg=Reg003567 via
  entity-refs.js:personHref(). Fixed in entity-refs.js by renaming the
  target to persons.html.
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent

# Patterns that constitute a real link target (not a comment or doc reference)
_HREF_RE = re.compile(r"""href\s*=\s*['"]person\.html""")
_STR_LIT_RE = re.compile(r"""(['"])person\.html\1""")

# Paths that are allowed to contain "person.html" (the page itself, this test)
_SKIP = {
    REPO / 'mockup' / 'person.html',
    Path(__file__),
}

# Directories to skip entirely (generated output, or retired files)
_SKIP_DIRS = {
    REPO / 'mockup' / 'diary-pages',
    REPO / 'mockup' / 'data',        # generated JS blobs
    REPO / 'mockup' / 'irrelevant',  # retired pages, frozen — see that
                                     # folder's README.md
}

# Source trees and extensions to check
_SOURCES = [
    (REPO / 'mockup', ['.html', '.js']),
    (REPO / 'scripts', ['.py']),
]


def _is_comment_only(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith('//') or stripped.startswith('#')


def _check_file(path: Path) -> list[tuple[int, str]]:
    hits = []
    text = path.read_text(encoding='utf-8', errors='replace')
    for lineno, line in enumerate(text.splitlines(), 1):
        if _is_comment_only(line):
            continue
        if _HREF_RE.search(line) or _STR_LIT_RE.search(line):
            hits.append((lineno, line.rstrip()))
    return hits


def main() -> int:
    violations: list[tuple[Path, int, str]] = []

    for root, exts in _SOURCES:
        if not root.exists():
            continue
        for path in sorted(root.rglob('*')):
            if not path.is_file():
                continue
            if path.suffix not in exts:
                continue
            if path in _SKIP:
                continue
            if any(path.is_relative_to(d) for d in _SKIP_DIRS):
                continue
            for lineno, line in _check_file(path):
                violations.append((path.relative_to(REPO), lineno, line))

    if not violations:
        print('OK — no stale person.html link targets found.')
        return 0

    print(f'FAIL — {len(violations)} stale person.html reference(s):\n')
    for rel, lineno, line in violations:
        print(f'  {rel}:{lineno}')
        print(f'    {line.strip()}')
    print(
        '\nAll links to the person detail page must use persons.html, e.g.'
        '\n  href="persons.html?reg=…"  or  \'persons.html?reg=\' + rid'
    )
    return 1


if __name__ == '__main__':
    sys.exit(main())
