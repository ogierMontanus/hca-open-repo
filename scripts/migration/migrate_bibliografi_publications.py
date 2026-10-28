"""migrate_bibliografi_publications.py — publication events from the
`bibliografi` table of hca_db.sql (plan-tidstavle-data.md; sql-database-inventory.md).

`bibliografi.UdgivDato` is linked to the old work register through
`bibliografi_rel` (BibliografiID -> VID, with a relation type). Each relation
that denotes a publication-like event becomes one row; `vid` is resolved to
the register's Reg… ids by title (`vaerktitler`, TitelgruppeID 15 = main title).

Grouping (decision 2026-10-28): single poems and small prints are collected
per work. A bibliography post that is the first printing of work A and is
also `del af` (part of) a different work B — a poem later gathered in
"Digte, gamle og nye", a tale in "Eventyr. 1850" — is NOT its own event. All
such posts of one B become ONE event (`grouping=collected`, id `BG{B:05d}`,
vid = B): `date_start`/`date_end` span the members' first printings
(`precision` p when they differ), `n_members`, `bib_ids`, `member_vids` keep
the rest. Posts without a container are one event per work
(`grouping=single`, id `BP…`; several posts of the same vid -> the print that
can have appeared earliest gives the date, `n_members` counts them).
Editions, translations and reviews stay one event per bibliography row
(`grouping=single`): they are distinct events with their own dates.

Hard limit: events after 1875-12-31 are dropped (scripts/normalization/event_bounds.py).

Writes to data/normalized_v092/:
  publication_events.csv    one row per bibliografi_rel row that is an event
  vid_reg_candidates.csv    vid -> Reg… candidates (title match), all 1,508 vids

Relation -> event_type (other relations are not events and are skipped):
  førsteudgivelse af, førsteudgave af -> publication_first
  udgave af                           -> publication_edition
  oversættelse af                     -> translation
  Anmeldelse af                       -> review
  (del af / anbefalet udgave af / JdMs nudanske digtudgave af: container or
   modern-edition links — not events)

Usage:
  python scripts/migration/migrate_bibliografi_publications.py [--sql PATH] [--out DIR]
"""

import argparse
import calendar
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "migration"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "normalization"))

from migrate_tidstavle_sql import parse_table  # noqa: E402
import event_bounds  # noqa: E402

DEFAULT_SQL = REPO_ROOT / "raw" / "hca_db.sql"
DEFAULT_OUT = REPO_ROOT / "data" / "normalized_v092"
ENTITIES = REPO_ROOT / "data" / "normalized" / "entities.csv"

MAIN_TITLE_GROUP = "15"

EVENT_TYPE = {
    "førsteudgivelse af": "publication_first",
    "førsteudgave af": "publication_first",
    "udgave af": "publication_edition",
    "oversættelse af": "translation",
    "Anmeldelse af": "review",
}

FIELDS = ["event_id", "bib_id", "bib_source", "vid", "relation", "event_type",
          "title", "date_raw", "date_start", "date_end", "precision", "language",
          "medium", "vid_title", "reg_id", "reg_match",
          "grouping", "n_members", "bib_ids", "member_vids"]

PREC_RANK = {"d": 0, "m": 1, "y": 2}


def _span(rows: list[dict]) -> tuple[str, str, str]:
    start = min(e["date_start"] for e in rows)
    end = max(e["date_end"] for e in rows)
    if len(rows) == 1 or (len({(e["date_start"], e["date_end"]) for e in rows}) == 1):
        return start, end, rows[0]["precision"]
    return start, end, "p"


def group_first_publications(events: list[dict], containers: dict[str, set]) -> list[dict]:
    """Collapse publication_first rows (see module docstring).

    containers: bib_id -> vids the post is `del af` (part of)."""
    collected: dict[str, list[dict]] = defaultdict(list)
    single: dict[str, list[dict]] = defaultdict(list)
    out = []
    for e in events:
        if e["event_type"] != "publication_first":
            out.append(dict(e, grouping="single", n_members=1, bib_ids=e["bib_id"],
                            member_vids=""))
            continue
        parts = containers.get(e["bib_id"], set()) - {e["vid"]}
        if parts and e["vid"] not in containers.get(e["bib_id"], set()):
            collected[min(parts, key=int)].append(e)
        else:
            single[e["vid"]].append(e)
    for vid, rows in single.items():
        rows.sort(key=lambda e: (e["date_end"], PREC_RANK[e["precision"]], e["event_id"]))
        out.append(dict(rows[0], grouping="single", n_members=len(rows),
                        bib_ids=";".join(e["bib_id"] for e in rows), member_vids=""))
    for vid, rows in collected.items():
        rows.sort(key=lambda e: (e["date_start"], e["event_id"]))
        start, end, prec = _span(rows)
        c = rows[0]["_container"]
        out.append(dict(
            rows[0], event_id=f"BG{int(vid):05d}", vid=vid, grouping="collected",
            n_members=len(rows), bib_ids=";".join(e["bib_id"] for e in rows),
            member_vids=";".join(dict.fromkeys(e["vid"] for e in rows)),
            title=c["title"], date_raw="", date_start=start, date_end=end,
            precision=prec, relation="førsteudgivelse af (samlet)",
            vid_title=c["title"], reg_id=c["reg_id"], reg_match=c["reg_match"]))
    return out


def norm_title(s: str) -> str:
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s.strip())
    return re.sub(r"\W+", "", s.lower())


def vid_candidates(vt_rows, works) -> dict[str, dict]:
    """vid -> {title, reg_ids (sorted list)} via main-title match."""
    idx = defaultdict(set)
    for w in works:
        idx[norm_title(w["label"])].add(w["entity_id"])
    titles = defaultdict(list)
    for r in vt_rows:
        if r[4] == MAIN_TITLE_GROUP:
            titles[r[1]].append(r[3].strip())
    out = {}
    for vid, ts in titles.items():
        ids = set()
        for t in ts:
            ids |= idx.get(norm_title(t), set())
        out[vid] = {"title": ts[0], "reg_ids": sorted(ids)}
    return out


def parse_period(raw: str):
    """'1866-12-00' -> ('1866-12-01', '1866-12-31', 'm'); None if unusable."""
    m = re.fullmatch(r"(\d{4})-(\d\d)-(\d\d)", raw or "")
    if not m or m.group(1) == "0000":
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if mo == 0:
        return f"{y:04d}-01-01", f"{y:04d}-12-31", "y"
    last = calendar.monthrange(y, mo)[1]
    if d == 0:
        return f"{y:04d}-{mo:02d}-01", f"{y:04d}-{mo:02d}-{last:02d}", "m"
    if d > last:
        return None
    return f"{y:04d}-{mo:02d}-{d:02d}", f"{y:04d}-{mo:02d}-{d:02d}", "d"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sql", type=Path, default=DEFAULT_SQL)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    text = args.sql.read_text(encoding="utf-8")
    bib = {r[0]: r for r in parse_table(text, "bibliografi")}
    rels = parse_table(text, "bibliografi_rel")
    vt = parse_table(text, "vaerktitler")
    with ENTITIES.open(encoding="utf-8-sig", newline="") as f:
        works = [r for r in csv.DictReader(f) if r["entity_type"] == "work"]

    cands = vid_candidates(vt, works)
    containers: dict[str, set] = defaultdict(set)
    for r in rels:
        if r[2] == "del af":
            containers[r[1]].add(r[3])

    def container_info(vid: str) -> dict:
        c = cands.get(vid, {"title": "", "reg_ids": []})
        n = len(c["reg_ids"])
        return {"title": c["title"], "reg_id": c["reg_ids"][0] if n == 1 else "",
                "reg_match": "unique" if n == 1 else "ambiguous" if n > 1 else "none"}

    st = Counter()
    events = []
    for r in rels:
        rel_id, bib_id, relation, vid = r[0], r[1], r[2], r[3]
        etype = EVENT_TYPE.get(relation)
        if not etype:
            st["not_event:" + relation] += 1
            continue
        b = bib.get(bib_id)
        if not b:
            st["no_bibliografi_row"] += 1
            continue
        period = parse_period(b[7])
        if not period:
            st["undated_or_invalid"] += 1
            continue
        start, end, prec = period
        status, end = event_bounds.check(start, end)
        if status == "out":
            st["after_cutoff"] += 1
            continue
        c = cands.get(vid, {"title": "", "reg_ids": []})
        n = len(c["reg_ids"])
        events.append({
            "event_id": f"BP{int(rel_id):05d}",
            "bib_id": bib_id, "bib_source": b[1], "vid": vid,
            "relation": relation, "event_type": etype,
            "title": b[5].strip(), "date_raw": b[7],
            "date_start": start, "date_end": end, "precision": prec,
            "language": b[9], "medium": b[11],
            "vid_title": c["title"],
            "reg_id": c["reg_ids"][0] if n == 1 else "",
            "reg_match": "unique" if n == 1 else "ambiguous" if n > 1 else "none",
            "_container": None,
        })
        parts = containers.get(bib_id, set()) - {vid}
        if parts:
            events[-1]["_container"] = container_info(min(parts, key=int))
        if status == "clamped":
            st["clamped"] += 1

    n_rows = len(events)
    events = group_first_publications(events, containers)
    st["grouped_away"] = n_rows - len(events)

    args.out.mkdir(parents=True, exist_ok=True)
    events.sort(key=lambda e: (e["date_start"], e["event_id"]))
    with (args.out / "publication_events.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(events)

    with (args.out / "vid_reg_candidates.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["vid", "vid_title", "reg_match", "reg_ids"])
        for vid, c in sorted(cands.items(), key=lambda kv: int(kv[0])):
            n = len(c["reg_ids"])
            w.writerow([vid, c["title"],
                        "unique" if n == 1 else "ambiguous" if n > 1 else "none",
                        ";".join(c["reg_ids"])])

    for e in events:
        st[f"kept:{e['event_type']}:{e['grouping']}"] += 1
    print(f"publication_events.csv: {len(events)} rows (cutoff {event_bounds.CUTOFF})")
    for k, v in sorted(st.items()):
        print(f"  {k}: {v}")
    print("  reg_match:", dict(Counter(e["reg_match"] for e in events)))
    print(f"vid_reg_candidates.csv: {len(cands)} vids,",
          dict(Counter("unique" if len(c["reg_ids"]) == 1 else "ambiguous"
                       if c["reg_ids"] else "none" for c in cands.values())))


if __name__ == "__main__":
    main()
