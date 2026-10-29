"""Runs the Node tests of the crowdsourcing front end (mockup/js/crowd-*.js).

Both suites need the taxonomy that scripts/crowdsource/taxonomy.py defines
(the pages get it from the generated data/crowd-queue.js); it is written to a
temp file and handed over in CROWD_TAXONOMY_JSON. Skips without Node.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "crowdsource"))
import taxonomy  # noqa: E402


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_crowd_js_unit_tests(tmp_path):
    tax = tmp_path / "taxonomy.json"
    tax.write_text(json.dumps(taxonomy.taxonomy_for_js(), ensure_ascii=False), encoding="utf-8")
    result = subprocess.run(
        ["node", "--test", "tests/js/crowd-validate.test.js", "tests/js/crowd-store.test.js"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
        env={**os.environ, "CROWD_TAXONOMY_JSON": str(tax)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
