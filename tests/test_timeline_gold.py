"""Plan 1.3: the name linking is measured against a hand-annotated gold sample
(data/curated/timeline_gold.csv, see scripts/qa/timeline_gold.py). Until rows
carry done=ja the threshold tests skip; the sample itself is always checked."""
import csv
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "scripts" / "qa"))
sys.path.insert(0, str(REPO / "scripts" / "build_mockup"))

import timeline_gold as tg  # noqa: E402
import build_timeline as bt  # noqa: E402

# Precision floor per type. Set when the first gold run exists; start strict on
# precision (the matcher is documented as conservative) and loose on nothing
# else — recall is reported, not enforced, until the aliases work is done.
PRECISION_MIN = {"persons": 0.9, "places": 0.9, "works": 0.9}
MIN_ANNOTATED = 30


def test_sample_is_stratified_and_reproducible():
    rows = tg.read()
    assert rows and len({r["tidstavle_id"] for r in rows}) == len(rows)
    ids = {r["id"] for r in bt.read_workbook(bt.find_workbook())}
    assert {r["tidstavle_id"] for r in rows} <= ids
    cells = {(r["vol"], r["kind"]) for r in rows}
    assert len({v for v, _ in cells}) == 10 and {k for _, k in cells} == {"rejse", "ophold", "begivenhed"}
    assert all(r["date"] <= "1875-12-31" for r in rows)


def test_annotated_rows_are_complete():
    for r in tg.read():
        if r["done"] == "ja":
            assert r["annotator"], r["tidstavle_id"]


@pytest.mark.parametrize("etype", tg.TYPES)
def test_precision_floor(etype):
    rows = [r for r in tg.read() if r["done"] == "ja"]
    if len(rows) < MIN_ANNOTATED:
        pytest.skip(f"only {len(rows)} annotated rows (need {MIN_ANNOTATED})")
    m = tg.score(rows)[etype]
    if m["precision"] is None:
        pytest.skip("no predicted links of this type in the annotated rows")
    assert m["precision"] >= PRECISION_MIN[etype], m
