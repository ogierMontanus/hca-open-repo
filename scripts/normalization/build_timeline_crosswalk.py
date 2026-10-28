"""build_timeline_crosswalk.py — plan-tidstavle-data.md step 1.2.

Links every event of the SQL timeline (data/normalized_v092/timeline.csv,
1,446 biographical events, ids T####) to the entries of the printed
Tidstavle workbook (ids TV########, see build_timeline.py), without guessing.

For each SQL event the candidates are the workbook entries whose period
contains the event's date:
  match = samme_dato   the entry starts on the event's day
          indeholdt    the event's day lies inside a longer entry
          ingen        no candidate, or no textual support (see note)
Text support is measured on idf-weighted word stems, two ways:
  score  = shared weight / sqrt(weight_a * weight_b)   (cosine-like; "is it
           the same sentence?" — a lone place name does NOT make a match)
  cover  = shared weight / weight of the entry's text  ("does the event
           mention everything the entry says?" — what a stay entry such as
           "København." needs to be a plausible context)

  status = auto     same-day entry (samme_dato) with score >= AUTO that beats
                    the runner-up by >= MARGIN  -> one row, equivalence claimed
           review   same-day entries with score >= REVIEW but not clear-cut
                    -> one row per candidate (max 5): the visible queue;
                    fill `reviewer` and `decision` (ja / nej) by hand
           kontekst the event happens during an entry (samme_dato or
                    indeholdt) whose text it covers (cover >= COVER) — a
                    stay/trip the event belongs to, NOT the same event
           ingen    nothing usable; `note` says why and `context_xlsx_id`
                    names the closest period the event falls inside (if any)

Imprecise SQL dates (month / year, `00` placeholders) are never matched on
date alone: they get match=ingen, note=upræcis_dato.

Hard limit: nothing after 1875-12-31 enters the mapping
(scripts/normalization/event_bounds.py).

Bibliografi link: when the SQL text links to the old work register
(`…info.html?vid=N`) and publication_events.csv holds a first publication or
edition of that vid (or of a collected work with that vid as member) within ±1 year of the event, its id is added as
`bp_event_id` (+ `bp_diff_days`) — the structured publication date.

`reviewer`/`decision` already filled in an existing output file are carried
over by (xlsx_key, sql_event_id), so reruns never lose editorial work.

Output: data/curated/timeline_crosswalk.csv
Usage:  python scripts/normalization/build_timeline_crosswalk.py [--report]
"""

import argparse
import csv
import html
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "build_mockup"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "normalization"))

import build_timeline as bt  # noqa: E402
import event_bounds  # noqa: E402

SQL_TIMELINE = REPO_ROOT / "data" / "normalized_v092" / "timeline.csv"
PUBLICATIONS = REPO_ROOT / "data" / "normalized_v092" / "publication_events.csv"
OUT = REPO_ROOT / "data" / "curated" / "timeline_crosswalk.csv"

AUTO, REVIEW, MARGIN, COVER, MAX_REVIEW_ROWS = 0.4, 0.25, 0.15, 0.5, 5
BP_WINDOW_DAYS = 366

FIELDS = ["xlsx_id", "sql_event_id", "match", "status", "score", "reviewer",
          "decision", "note", "context_xlsx_id", "bp_event_id", "bp_diff_days",
          "xlsx_key"]

WORD = re.compile(r"[^\W\d_]{4,}")
VID = re.compile(r"info\.html\?vid=(\d+)")
ISO_DAY = re.compile(r"^\d{4}-\d\d-\d\d$")


def plain(h: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", h or ""))


def stems(text: str) -> frozenset:
    return frozenset(bt.fold(w)[:6] for w in WORD.findall(text))


def day_no(iso: str) -> int:
    return date.fromisoformat(iso).toordinal()


def sql_period(date_iso: str):
    """'1835-03-00' -> (start, end, precision); None when undated/invalid."""
    m = re.fullmatch(r"(\d{4})-(\d\d)-(\d\d)", date_iso or "")
    if not m or m.group(1) == "0000":
        return None
    y, mo, d = (int(g) for g in m.groups())
    if mo == 0:
        return f"{y:04d}-01-01", f"{y:04d}-12-31", "y"
    if d == 0:
        return bt.parse_date(f"{y:04d}-{mo:02d}", False)[0], \
            bt.parse_date(f"{y:04d}-{mo:02d}", True)[0], "m"
    try:
        date(y, mo, d)
    except ValueError:
        return None
    return date_iso, date_iso, "d"


def load_previous() -> dict:
    if not OUT.exists():
        return {}
    with OUT.open(encoding="utf-8", newline="") as f:
        return {(r["xlsx_key"], r["sql_event_id"]): (r["reviewer"], r["decision"])
                for r in csv.DictReader(f) if r["reviewer"] or r["decision"]}


def load_publications() -> dict:
    by_vid = defaultdict(list)
    if PUBLICATIONS.exists():
        with PUBLICATIONS.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if r["event_type"] in ("publication_first", "publication_edition"):
                    # collected events answer for their container and all members
                    for vid in {r["vid"], *filter(None, r["member_vids"].split(";"))}:
                        by_vid[vid].append(r)
    return by_vid


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    # ── inputs, with the hard date limit ─────────────────────────────────
    drop = Counter()
    xl = []
    for r in bt.read_workbook(bt.find_workbook()):
        status, end = event_bounds.check(r["a"], r["b"])
        if status == "out":
            drop["xlsx_after_cutoff"] += 1
            continue
        xl.append(dict(r, b=end))
    with SQL_TIMELINE.open(encoding="utf-8-sig", newline="") as f:
        sql = list(csv.DictReader(f))

    docs = [stems(r["text"]) for r in xl]
    sql_docs = [stems(plain(e["text_da"])) for e in sql]
    df = Counter(t for d in docs + sql_docs for t in d)
    n_docs = len(docs) + len(sql_docs)

    def weight(tokens) -> float:
        return sum(math.log(n_docs / df[t]) for t in tokens)

    def scores(a, b) -> tuple[float, float]:
        """(score, cover) of event stems a against entry stems b."""
        shared = a & b
        if not shared:
            return 0.0, 0.0
        ws, wa, wb = weight(shared), weight(a), weight(b)
        return ws / math.sqrt(wa * wb), ws / (wb or 1.0)

    for r, d in zip(xl, docs):
        r["_stems"], r["_a"], r["_b"] = d, day_no(r["a"]), day_no(r["b"])

    pubs = load_publications()
    prev = load_previous()
    out, st = [], Counter()

    def finish(row, e):
        row.setdefault("reviewer", "")
        row.setdefault("decision", "")
        row.setdefault("context_xlsx_id", "")
        row.setdefault("note", "")
        row.setdefault("xlsx_id", "")
        row.setdefault("xlsx_key", "")
        row.setdefault("score", "")
        # bibliografi link
        best = None
        per = sql_period(e["date_iso"])
        if per:
            for vid in dict.fromkeys(VID.findall(e["text_da"] + e["text_en"])):
                for p in pubs.get(vid, ()):
                    lo, hi = day_no(p["date_start"]), day_no(p["date_end"])
                    # 0 when the event's day lies inside the printing period
                    diff = 0 if lo <= day_no(per[0]) <= hi else                         (lo - day_no(per[0]) if lo > day_no(per[0]) else hi - day_no(per[0]))
                    if abs(diff) <= BP_WINDOW_DAYS and (best is None or abs(diff) < abs(best[1])):
                        best = (p["event_id"], diff)
        row["bp_event_id"], row["bp_diff_days"] = best if best else ("", "")
        row["sql_event_id"] = e["event_id"]
        key = (row["xlsx_key"], e["event_id"])
        if key in prev and row["xlsx_key"]:
            row["reviewer"], row["decision"] = prev[key]
        out.append(row)

    for e, es in zip(sql, sql_docs):
        per = sql_period(e["date_iso"])
        if per is None:
            st["ingen:ingen_dato"] += 1
            finish(dict(match="ingen", status="ingen", note="ingen_dato"), e)
            continue
        status, _ = event_bounds.check(per[0], per[1])
        if status == "out":
            drop["sql_after_cutoff"] += 1
            continue
        if per[2] != "d":
            st["ingen:upræcis_dato"] += 1
            finish(dict(match="ingen", status="ingen", note="upræcis_dato"), e)
            continue

        d = day_no(per[0])
        cands = []
        for r in xl:
            if r["_a"] <= d <= r["_b"]:
                sc, cov = scores(es, r["_stems"])
                cands.append((sc, cov, r))
        if not cands:
            st["ingen:ingen_kandidat"] += 1
            finish(dict(match="ingen", status="ingen", note="ingen_kandidat"), e)
            continue

        def rel(r):
            return "samme_dato" if r["a"] == per[0] else "indeholdt"

        def row_for(sc, r, status_):
            return dict(xlsx_id=r["id"], xlsx_key=r["key"], match=rel(r),
                        status=status_, score=f"{sc:.2f}")

        same = sorted((c for c in cands if c[2]["a"] == per[0]),
                      key=lambda c: (-c[0], c[2]["_b"] - c[2]["_a"], c[2]["id"]))
        top = same[0][0] if same else 0.0
        second = same[1][0] if len(same) > 1 else 0.0
        if top >= AUTO and top - second >= MARGIN:
            st["auto"] += 1
            finish(row_for(top, same[0][2], "auto"), e)
            continue
        if top >= REVIEW:
            st["review"] += 1
            for sc, _, r in same[:MAX_REVIEW_ROWS]:
                if sc >= REVIEW:
                    finish(row_for(sc, r, "review"), e)
            continue
        # context: best-covered, then shortest period
        cover = sorted(cands, key=lambda c: (-c[1], c[2]["_b"] - c[2]["_a"], c[2]["id"]))
        if cover[0][1] >= COVER:
            st["kontekst"] += 1
            finish(row_for(cover[0][0], cover[0][2], "kontekst"), e)
        else:
            st["ingen:ingen_tekststøtte"] += 1
            finish(dict(match="ingen", status="ingen", note="ingen_tekststøtte",
                        context_xlsx_id=cover[0][2]["id"]), e)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    n_events = len({r["sql_event_id"] for r in out})
    print(f"wrote {OUT.relative_to(REPO_ROOT)}: {len(out)} rows for {n_events} SQL events "
          f"(cutoff {event_bounds.CUTOFF})")
    for k, v in sorted(st.items()):
        print(f"  {k}: {v}")
    if drop:
        print("  dropped by cutoff:", dict(drop))
    print("  match:", dict(Counter(r["match"] for r in out)))
    print("  bp links:", sum(1 for r in out if r["bp_event_id"]))
    if args.report:
        xl_hit = {r["xlsx_id"] for r in out if r["status"] == "auto"}
        print(f"  xlsx entries with an auto partner: {len(xl_hit)} of {len(xl)}")


if __name__ == "__main__":
    main()
