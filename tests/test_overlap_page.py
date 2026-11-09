"""Annotation page for the diary/almanac overlap sample (almanak/annotation/build_overlap_page.py,
docs/plan-streng-grounding.md §3.9) and its offset checker."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ANN = ROOT / "almanak" / "annotation"
sys.path.insert(0, str(ANN))

pytestmark = pytest.mark.skipif(
    not (ROOT / "almanak" / "data" / "extracted" / "aligned.csv").exists()
    or not (ROOT / "data" / "normalized" / "diary.csv").exists(),
    reason="almanak/diary data not present")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("ov") / "overlap.html"
    r = subprocess.run([sys.executable, str(ANN / "build_overlap_page.py"), "--out", str(out)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    import check_annotations as chk
    return out, chk.load_entries(out)


def test_four_blocks_of_eight_days_with_both_texts(built):
    _out, entries = built
    assert len(entries) == 64
    for block in "ABCD":
        days = {e["date"] for e in entries.values() if e["block"] == block}
        assert len(days) == 8
        for d in days:
            assert {"ALM-" + d, "DAG-" + d} <= set(entries)
    assert sum(len(e["text"]) for e in entries.values() if e["src"] == "almanak") < 4000


def test_texts_are_clean_and_versioned(built):
    _out, entries = built
    for e in entries.values():
        assert e["text"].strip() == e["text"] and "\n" not in e["text"] and "  " not in e["text"]
        assert e["tv"]
        if e["src"] == "dagbog":
            import re
            assert not re.search(r"\b\d{3}-\d{2}\b", e["text"]), "linjetag er blevet stående"
            assert e["pages"] and all(p["v"] for p in e["pages"])


def test_line_joining_rules():
    import build_overlap_page as b
    assert b.join_lines(["Sommer-", "fugl er", "kommet"]) == "Sommerfugl er kommet"          # lille bogstav: ordet var delt
    assert b.join_lines(["hos Moltke-", "Bregentved i"]) == "hos Moltke-Bregentved i"        # stort bogstav: bindestregen hører til navnet
    assert b.join_lines(["a  ", "", " b"]) == "a b"


def test_checker_accepts_good_and_rejects_bad_offsets(built, tmp_path):
    out, entries = built
    import check_annotations as chk
    e = entries["DAG-1846-01-01"]
    i = e["text"].index("Mügge")
    good = {"meta": {"active_seconds_by_block": {}}, "reviewed_days": [],
            "annotations": [{"post_id": e["id"], "start": i, "end": i + 5, "string": "Mügge", "type": "Person"}]}
    f = tmp_path / "good.json"
    f.write_text(json.dumps(good), encoding="utf-8")
    assert chk.main(["x", str(out), str(f)]) == 0
    good["annotations"][0]["start"] += 1
    f.write_text(json.dumps(good), encoding="utf-8")
    assert chk.main(["x", str(out), str(f)]) == 1
    good["annotations"] = [{"post_id": e["id"], "start": i, "end": i + 5, "string": "Mügge", "type": "Person"},
                           {"post_id": e["id"], "start": i + 2, "end": i + 5, "string": "gge", "type": "Person"}]
    f.write_text(json.dumps(good), encoding="utf-8")
    assert chk.main(["x", str(out), str(f)]) == 1                                            # overlap
