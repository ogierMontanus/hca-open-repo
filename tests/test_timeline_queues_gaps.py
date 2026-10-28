"""Guards for plan-tidstavle-data.md steps 1.4 (editorial queues) and 1.5
(diary gaps). Reads only committed CSVs."""
import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

REPO = Path(__file__).parent.parent
CUTOFF = "1875-12-31"


def _csv(path, enc="utf-8-sig"):
    with Path(path).open(encoding=enc, newline="") as f:
        return list(csv.DictReader(f))


def _queue(name):
    return _csv(REPO / "data" / "curated" / f"queue_timeline_{name}.csv", "utf-8")


def _unique(rows, *keys):
    ks = [tuple(r[k] for k in keys) for r in rows]
    assert len(ks) == len(set(ks))


def test_queues_have_decision_columns_and_unique_keys():
    for name, keys in (("place_deviations", ("sider",)),
                       ("missing_persontags", ("person_id", "tidstavle_id")),
                       ("work_mentions", ("work_id", "tidstavle_id"))):
        rows = _queue(name)
        assert rows, name
        assert {"forslag", "beslutning", "beslutter"} <= set(rows[0]), name
        assert all(r["forslag"] for r in rows), name
        _unique(rows, *keys)


def test_place_deviations_name_both_sides_and_respect_the_cutoff():
    for r in _queue("place_deviations"):
        assert r["dagbogssted_id"] and r["tidstavlested"] and r["tidstavle_id"], r
        assert all(d <= CUTOFF for d in r["datoer"].split(";")), r


def test_missing_persontags_categories_and_cutoff():
    rows = _queue("missing_persontags")
    assert {r["kategori"] for r in rows} <= {"ingen_tag", "ingen_dagbogsside", "uden_for_dagbogen"}
    assert all(r["fra"] <= CUTOFF for r in rows)
    for r in rows:
        if r["kategori"] != "ingen_tag":
            assert r["kandidatsider"] == "" and r["dagbogssider_i_perioden"] == "0"
    assert any(r["kandidatsider"] for r in rows)


def test_work_mentions_rows_are_outside_the_window():
    rows = _queue("work_mentions")
    assert all(r["dato"] <= CUTOFF for r in rows)
    for r in rows:
        if r["nærmeste_omtale"]:
            assert abs(int(r["afstand_dage"])) > 60, r


def test_decisions_are_never_overwritten_on_rerun():
    import sys
    sys.path.insert(0, str(REPO / "scripts" / "normalization"))
    import build_timeline_queues as bq
    assert bq.DECISION == ["beslutning", "beslutter"]


def test_diary_pages_of_volumes_i_to_x_have_no_holes():
    """Basis for the claim in report_timeline_gaps.py that no gap is 'our hole'."""
    pages = defaultdict(set)
    for r in _csv(REPO / "data" / "normalized" / "diary.csv"):
        pages[r["vol"]].add(int(r["page"]))
    assert len(pages) == 10
    for vol, ps in pages.items():
        assert ps == set(range(1, max(ps) + 1)), vol


def test_gap_runs_are_well_formed():
    rows = _csv(REPO / "data" / "normalized" / "timeline_gaps.csv", "utf-8")
    assert rows
    prev_end = ""
    for r in sorted(rows, key=lambda r: r["start"]):
        s, e = date.fromisoformat(r["start"]), date.fromisoformat(r["end"])
        assert r["end"] <= CUTOFF and s <= e
        assert int(r["n_days"]) == (e - s).days + 1
        assert r["start"] > prev_end, "runs overlap"
        prev_end = r["end"]
        assert r["category"] in {"i_bind", "mellem_bind"}
        assert (r["category"] == "i_bind") == bool(r["volume"])
    # a run never contains a day with a diary heading
    diary_days = {r["date"] for r in _csv(REPO / "data" / "normalized" / "diary.csv")}
    for r in rows:
        assert r["start"] not in diary_days and r["end"] not in diary_days


# ── entity_dates (plan 1.5) ──────────────────────────────────────────────

def test_entity_dates_are_well_formed():
    rows = _csv(REPO / "data" / "normalized" / "entity_dates.csv", "utf-8")
    assert rows and len({r["event_id"] for r in rows}) == len(rows)
    assert {r["entity_type"] for r in rows} == {"person", "work"}
    assert {r["precision"] for r in rows} <= {"day", "month", "year", "period"}
    for r in rows:
        assert r["date_start"] <= r["date_end"], r
        if r["entity_type"] == "work" or r["event_type"] == "birth":
            assert r["date_end"] <= CUTOFF, r          # mapped events respect the limit
    births = {r["entity_id"]: r for r in rows if r["event_type"] == "birth"}
    deaths = {r["entity_id"]: r for r in rows if r["event_type"] == "death"}
    for pid, b in births.items():
        assert b["date_start"] <= deaths[pid]["date_start"], pid
    assert {r["event_type"] for r in rows if r["entity_type"] == "work"} <= {
        "publication", "reprint", "premiere", "performance"}
