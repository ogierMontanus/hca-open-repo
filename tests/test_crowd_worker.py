"""The GitHub-login Worker (workers/crowd-api, docs/crowdsourcing-login-plan.md).

* its copy of the taxonomy must equal taxonomy.py (the Worker bundles it);
* its Node tests (OAuth flow, roles, round trip, GitHub storage) run here;
* apply_csp.py widens connect-src to exactly the origin in crowd-config.js.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WORKER = ROOT / "workers" / "crowd-api"
sys.path.insert(0, str(ROOT / "scripts" / "crowdsource"))
sys.path.insert(0, str(ROOT / "scripts" / "build_mockup"))
import apply_csp  # noqa: E402
import taxonomy  # noqa: E402


def test_worker_taxonomy_is_in_sync():
    mine = json.loads((WORKER / "src" / "taxonomy.json").read_text(encoding="utf-8"))
    assert mine == json.loads(json.dumps(taxonomy.taxonomy_for_js())), \
        "run: python workers/crowd-api/scripts/sync_taxonomy.py"


def _node_major():
    out = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout
    return int(re.match(r"v(\d+)", out).group(1))


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_worker_node_tests():
    if _node_major() < 22:
        pytest.skip("the Worker tests use JSON import attributes (Node 22+)")
    r = subprocess.run(["node", "--test", "test/worker.test.js"], cwd=WORKER, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-1000:]


@pytest.mark.parametrize("config,page,expected", [
    ("window.CROWD_CONFIG = { apiBase: '' };", "crowd-store.js", "connect-src 'self'"),
    ("window.CROWD_CONFIG = { apiBase: 'https://hca.example.workers.dev/' };", "crowd-store.js",
     "connect-src 'self' https://hca.example.workers.dev"),
    ("window.CROWD_CONFIG = { apiBase: 'https://hca.example.workers.dev' };", "index page",
     "connect-src 'self'"),                                                      # only the crowd pages
    ("window.CROWD_CONFIG = { apiBase: 'http://insecure.example' };", "crowd-store.js", "connect-src 'self'"),
    ("window.CROWD_CONFIG = { apiBase: 'https://a.example; script-src *' };", "crowd-store.js", "connect-src 'self'"),
])
def test_csp_connect_src_follows_crowd_config(tmp_path, monkeypatch, config, page, expected):
    cfg = tmp_path / "crowd-config.js"
    cfg.write_text(config, encoding="utf-8")
    monkeypatch.setattr(apply_csp, "_CROWD_CONFIG", cfg)
    directives = apply_csp.policy_for(f"<html><head></head><body>{page}</body></html>").split("; ")
    assert [d for d in directives if d.startswith("connect-src")] == [expected]


def test_committed_config_is_valid_and_csp_clean():
    text = (ROOT / "mockup" / "js" / "crowd-config.js").read_text(encoding="utf-8")
    assert "window.CROWD_CONFIG" in text
    assert "<" not in text   # no markup; the file is a plain script
