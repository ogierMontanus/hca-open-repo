"""Write workers/crowd-api/src/taxonomy.json from scripts/crowdsource/taxonomy.py.

    python workers/crowd-api/scripts/sync_taxonomy.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "crowdsource"))
import taxonomy  # noqa: E402

OUT = ROOT / "workers" / "crowd-api" / "src" / "taxonomy.json"


def render() -> str:
    return json.dumps(taxonomy.taxonomy_for_js(), ensure_ascii=False, indent=1, sort_keys=True) + "\n"


if __name__ == "__main__":
    OUT.write_text(render(), encoding="utf-8")
    print("wrote", OUT)
