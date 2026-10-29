"""Guards for the event mapping: the 1875-12-31 hard limit, the publication
events from `bibliografi`, and the SQL-timeline <-> Tidstavle crosswalk
(plan-tidstavle-data.md steps 1.0-1.2).

Reads only committed CSVs plus the Tidstavle workbook — no SQL dump needed.
"""
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "scripts" / "normalization"))
sys.path.insert(0, str(REPO / "scripts" / "build_mockup"))
sys.path.insert(0, str(REPO / "scripts" / "migration"))

import build_timeline as bt  # noqa: E402
import event_bounds  # noqa: E402
import migrate_bibliografi_publications as mbp  # noqa: E402

CUTOFF = "1875-12-31"
NORM = REPO / "data" / "normalized_v092"


def _csv(path, enc="utf-8-sig"):
    with Path(path).open(encoding=enc, newline="") as f:
        return list(csv.DictReader(f))


def _crosswalk():
    return _csv(REPO / "data" / "curated" / "timeline_crosswalk.csv", "utf-8")


# ── event_bounds ─────────────────────────────────────────────────────────

def test_cutoff_is_31_december_1875():
    assert event_bounds.CUTOFF == CUTOFF


def test_check_drops_clamps_and_keeps():
    assert event_bounds.check("1875-12-31") == ("in", "1875-12-31")
    assert event_bounds.check("1876-01-01") == ("out", "1876-01-01")
    assert event_bounds.check("1875-06-01", "1876-03-01") == ("clamped", CUTOFF)
    assert event_bounds.check("1800-01-01", "1800-01-02") == ("in", "1800-01-02")


# ── publication events from bibliografi ─────────────────────────────────

def test_publication_events_respect_the_cutoff_and_have_unique_ids():
    rows = _csv(NORM / "publication_events.csv")
    assert rows
    assert len({r["event_id"] for r in rows}) == len(rows)
    assert all(r["date_start"] <= r["date_end"] <= CUTOFF for r in rows)
    assert {r["event_type"] for r in rows} <= {
        "publication_first", "publication_edition", "translation", "review"}
    assert {r["precision"] for r in rows} <= {"d", "m", "y", "p"}
    assert {r["grouping"] for r in rows} <= {"single", "collected"}


def test_small_prints_are_collected_per_work():
    rows = _csv(NORM / "publication_events.csv")
    firsts = [r for r in rows if r["event_type"] == "publication_first"]
    collected = [r for r in firsts if r["grouping"] == "collected"]
    single = [r for r in firsts if r["grouping"] == "single"]
    assert collected and single
    # one event per container work, one first-publication event per single work
    assert len({r["vid"] for r in collected}) == len(collected)
    assert len({r["vid"] for r in single}) == len(single)
    for r in collected:
        assert r["event_id"] == f"BG{int(r['vid']):05d}"
        bibs = r["bib_ids"].split(";")
        assert r["n_members"] == str(len(bibs))
        assert r["member_vids"] and r["vid"] not in r["member_vids"].split(";")
        assert (r["precision"] == "p") == (r["date_start"] != r["date_end"] and
                                           r["precision"] not in "dmy")
    # The source marks a few works (11 on 2026-10-28) as "first printing" in two
    # posts — one inside a collection, one standalone with another date. Both
    # are kept; this bound only catches a grouping bug that multiplies them.
    members = {v for r in collected for v in r["member_vids"].split(";")}
    assert len(members & {r["vid"] for r in single}) <= 15


def test_period_parser_widens_missing_month_and_day():
    assert mbp.parse_period("1866-12-00") == ("1866-12-01", "1866-12-31", "m")
    assert mbp.parse_period("1822-00-00") == ("1822-01-01", "1822-12-31", "y")
    assert mbp.parse_period("1829-01-02") == ("1829-01-02", "1829-01-02", "d")
    assert mbp.parse_period("0000-00-00") is None
    assert mbp.parse_period("1841-02-30") is None


def test_vid_reg_candidates_cover_the_timeline_vids_conservatively():
    import re
    vids = set()
    for r in _csv(NORM / "timeline.csv"):
        vids |= set(re.findall(r"info\.html\?vid=(\d+)", r["text_da"] + r["text_en"]))
    cands = {r["vid"]: r for r in _csv(NORM / "vid_reg_candidates.csv")}
    assert len(vids) == 196 and vids <= set(cands)
    # a Reg id is only asserted when the title match is unique
    for r in cands.values():
        n = len([x for x in r["reg_ids"].split(";") if x])
        assert r["reg_match"] == ("unique" if n == 1 else "ambiguous" if n > 1 else "none")
    assert cands["401"]["reg_ids"] == "Reg001737"      # Improvisatoren


# ── crosswalk ────────────────────────────────────────────────────────────

def test_every_sql_event_has_a_row():
    sql_ids = {r["event_id"] for r in _csv(NORM / "timeline.csv")}
    cw_ids = {r["sql_event_id"] for r in _crosswalk()}
    assert sql_ids == cw_ids and len(sql_ids) == 1446


def test_rows_are_well_formed():
    xl = {r["id"]: r for r in bt.read_workbook(bt.find_workbook())}
    for r in _crosswalk():
        assert r["match"] in {"samme_dato", "indeholdt", "ingen"}
        assert r["status"] in {"auto", "review", "kontekst", "ingen"}
        assert (r["match"] == "ingen") == (r["status"] == "ingen")
        if r["status"] == "ingen":
            assert r["xlsx_id"] == "" and r["note"], r      # documented "ingen"
        else:
            assert r["xlsx_id"] in xl, r
            assert r["xlsx_key"] == xl[r["xlsx_id"]]["key"], r
        if r["context_xlsx_id"]:
            assert r["context_xlsx_id"] in xl, r
        assert r["decision"] in {"", "ja", "nej"}


def test_auto_is_unique_and_same_day():
    by_event = defaultdict(list)
    for r in _crosswalk():
        by_event[r["sql_event_id"]].append(r)
    for rows in by_event.values():
        if any(r["status"] == "auto" for r in rows):
            assert len(rows) == 1 and rows[0]["match"] == "samme_dato", rows
        # one status per event
        assert len({r["status"] for r in rows}) == 1, rows


def test_matched_pairs_agree_with_the_dates():
    xl = {r["id"]: r for r in bt.read_workbook(bt.find_workbook())}
    sql = {r["event_id"]: r for r in _csv(NORM / "timeline.csv")}
    for r in _crosswalk():
        if not r["xlsx_id"]:
            continue
        d, x = sql[r["sql_event_id"]]["date_iso"], xl[r["xlsx_id"]]
        assert x["a"] <= d <= x["b"], r
        assert (x["a"] == d) == (r["match"] == "samme_dato"), r


def test_imprecise_sql_dates_are_never_matched_on_date_alone():
    sql = {r["event_id"]: r for r in _csv(NORM / "timeline.csv")}
    for r in _crosswalk():
        d = sql[r["sql_event_id"]]["date_iso"]
        if d.endswith("-00"):
            assert r["match"] == "ingen" and r["note"] == "upræcis_dato", r


def test_bibliografi_links_point_at_real_publication_events():
    pubs = {r["event_id"] for r in _csv(NORM / "publication_events.csv")}
    linked = [r for r in _crosswalk() if r["bp_event_id"]]
    assert linked and all(r["bp_event_id"] in pubs for r in linked)
    assert all(abs(int(r["bp_diff_days"])) <= 366 for r in linked)


# ── the hard limit holds for every event source ─────────────────────────

def test_nothing_in_the_event_mapping_is_after_the_cutoff():
    assert all(r["b"] <= CUTOFF for r in bt.read_workbook(bt.find_workbook()))
    assert all(r["date_iso"] <= CUTOFF for r in _csv(NORM / "timeline.csv"))
    xl = {r["id"]: r for r in bt.read_workbook(bt.find_workbook())}
    for r in _crosswalk():
        for k in ("xlsx_id", "context_xlsx_id"):
            if r[k]:
                assert xl[r[k]]["a"] <= CUTOFF
    kinds = Counter(r["status"] for r in _crosswalk())
    assert kinds["auto"] and kinds["review"]
