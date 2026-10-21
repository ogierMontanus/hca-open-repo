"""Runs the JavaScript unit tests of the AND/OR filter logic.

mockup/js/filter-logic.js is DOM-free, so its tests (tests/js/filter-logic.test.js)
run under Node's built-in test runner. This wrapper lets the existing
`python -m pytest tests` (locally and in CI) pick them up; it skips when Node is
not installed. The browser tests (tests/js/filter-ui.test.js, Playwright) are
not run from here — see docs/filter-logic.md.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_filter_logic_js_unit_tests():
    result = subprocess.run(
        ["node", "--test", "tests/js/filter-logic.test.js"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
