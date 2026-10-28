"""build_timeline_queues.py — plan-tidstavle-data.md step 1.4.

Three editorial queues from the cross-checks between the printed Tidstavle
and the diary. Each is a CSV in data/curated/ with the columns
`forslag` (machine suggestion), `beslutning` and `beslutter` (filled by hand).
A decided item is corrected in the register, never in the Tidstavle (the
Tidstavle stays the printed source). Reruns keep `beslutning`/`beslutter`.

  queue_timeline_place_deviations.csv   the diary page names places, the stay
        entries of the same day name others, and the two sets are disjoint
  queue_timeline_missing_persontags.csv a person is named in a Tidstavle entry
        but no diary page of the entry's period carries the person's tag.
        kategori: ingen_tag (pages exist; `kandidatsider` = those whose text
        contains the surname) · ingen_dagbogsside (no page in the period) ·
        uden_for_dagbogen (period before the first / after the last diary date)
  queue_timeline_work_mentions.csv      a work linked to a Tidstavle entry is
        not mentioned on any diary page within ±60 days of the entry

Nothing after 1875-12-31 (scripts/normalization/event_bounds.py).

Usage: python scripts/normalization/build_timeline_queues.py
"""

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "normalization"))

import timeline_linked as tl  # noqa: E402

CURATED = REPO_ROOT / "data" / "curated"
WORK_WINDOW = 60
MAX_PERIOD_DAYS = 366          # longer entries are stays/travels, not a day to tag
DECISION = ["beslutning", "beslutter"]


def vp(p) -> str:
    return f"{p[0]}:{p[1]}"


def page_key(p):
    v = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]
    return (v.index(p[0]) if p[0] in v else 99, int(p[1]) if p[1].isdigit() else 0)


def write_queue(name: str, fields: list[str], rows: list[dict], key) -> None:
    path = CURATED / name
    prev = {}
    if path.exists():
        with path.open(encoding="utf-8", newline="") as f:
            prev = {key(r): r for r in csv.DictReader(f) if r["beslutning"] or r["beslutter"]}
    for r in rows:
        old = prev.get(key(r), {})
        r["beslutning"], r["beslutter"] = old.get("beslutning", ""), old.get("beslutter", "")
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields + DECISION)
        w.writeheader()
        w.writerows(rows)


def surname(label: str) -> str:
    return label.split(",")[0].split("(")[0].strip()


def main() -> None:
    CURATED.mkdir(parents=True, exist_ok=True)
    entries = tl.load_entries()
    diary = tl.Diary()
    reg_labels = tl.load_labels()
    with (tl.NORM / "places.csv").open(encoding="utf-8-sig", newline="") as f:
        loc_labels = {r["entity_id"]: r["label"] for r in csv.DictReader(f)}
    place_refs = tl.load_refs("LOC")
    reg_refs = tl.load_refs("Reg")

    stays_on = defaultdict(list)                       # date -> stay entries
    for e in entries:
        if e["kind"] in ("ophold", "rejse") and e["places"]:
            for d in tl.days(e["a"], e["b"]):
                stays_on[d].append(e)

    # ── 1. place deviations ─────────────────────────────────────────────
    rows, comparable = [], 0
    for page in sorted(diary.page_dates, key=page_key):
        page_places = place_refs.get(page, set())
        stay = [e for d in diary.page_dates[page] for e in stays_on.get(d, ())]
        stay_places = {p for e in stay for p in e["places"]}
        if not page_places or not stay_places:
            continue
        comparable += 1
        if page_places & stay_places:
            continue
        rows.append(dict(
            sider=vp(page), datoer=";".join(sorted(diary.page_dates[page])),
            dagbogssted="; ".join(sorted(loc_labels.get(p, p) for p in page_places)),
            dagbogssted_id=";".join(sorted(page_places)),
            tidstavlested="; ".join(sorted(loc_labels.get(p, p) for p in stay_places)),
            tidstavle_id=";".join(sorted({e["id"] for e in stay})),
            forslag="tjek siden mod facsimilen" if len(diary.page_dates[page]) == 1
                    else "flere dage på siden — afgør pr. dag"))
    write_queue("queue_timeline_place_deviations.csv",
                ["sider", "datoer", "dagbogssted", "dagbogssted_id", "tidstavlested",
                 "tidstavle_id", "forslag"], rows, lambda r: r["sider"])
    n1 = len(rows)
    print(f"place deviations: {n1} of {comparable} comparable pages")

    # ── 2. possibly missing person tags ─────────────────────────────────
    rows = []
    seen = set()
    for e in entries:
        if (e["b"] > e["a"]) and len(list(tl.days(e["a"], e["b"]))) > MAX_PERIOD_DAYS:
            continue
        pages = diary.pages_between(e["a"], e["b"])
        for rid in sorted(e["persons"]):
            if (rid, e["id"]) in seen:
                continue
            seen.add((rid, e["id"]))
            label = reg_labels.get(rid, rid)
            if any(rid in reg_refs.get(p, ()) for p in pages):
                continue
            if not pages:
                outside = e["b"] < diary.dates[0] or e["a"] > diary.dates[-1]
                cat, cand = ("uden_for_dagbogen" if outside else "ingen_dagbogsside"), []
            else:
                cat = "ingen_tag"
                sn = tl.bt.fold(surname(label))
                cand = sorted((p for p in pages
                               if len(sn) >= 4 and sn in tl.bt.fold(diary.text[p])), key=page_key)
            rows.append(dict(
                person_id=rid, person=label, tidstavle_id=e["id"], fra=e["a"], til=e["b"],
                tidstavletekst=re.sub(r"\s+", " ", e["text"])[:160], kategori=cat,
                dagbogssider_i_perioden=len(pages),
                kandidatsider=";".join(vp(p) for p in cand[:8]),
                forslag="tag personen på kandidatsiden" if cand else
                        ("ingen dagbogsside i perioden" if not pages else
                         "efternavnet står ikke på siderne — sandsynligvis ikke omtalt")))
    write_queue("queue_timeline_missing_persontags.csv",
                ["person_id", "person", "tidstavle_id", "fra", "til", "tidstavletekst", "kategori",
                 "dagbogssider_i_perioden", "kandidatsider", "forslag"],
                rows, lambda r: (r["person_id"], r["tidstavle_id"]))
    c = Counter(r["kategori"] for r in rows)
    withc = sum(1 for r in rows if r["kandidatsider"])
    print(f"missing person tags: {c['ingen_tag']} (of which {withc} with a surname hit on a "
          f"page of the period) + {c['ingen_dagbogsside']} with no diary page in the period "
          f"+ {c['uden_for_dagbogen']} outside the diary's date range")

    # ── 3. works without a diary mention ±60 days ───────────────────────
    work_dates = defaultdict(set)
    for page, ids in reg_refs.items():
        for rid in ids:
            work_dates[rid] |= diary.page_dates.get(page, set())
    rows, works, linked = [], set(), 0
    for e in entries:
        for rid in sorted(e["works"]):
            works.add(rid)
            near = [d for d in work_dates.get(rid, ())
                    if abs(tl.date.fromisoformat(d).toordinal()
                           - tl.date.fromisoformat(e["a"]).toordinal()) <= WORK_WINDOW]
            if near:
                linked += 1
                continue
            nd, diff = diary.nearest_date(e["a"], work_dates[rid]) if work_dates.get(rid) else ("", "")
            rows.append(dict(
                work_id=rid, værk=reg_labels.get(rid, rid), tidstavle_id=e["id"], dato=e["a"],
                tidstavletekst=re.sub(r"\s+", " ", e["text"])[:160],
                dagbogsomtaler_i_alt=len(work_dates.get(rid, ())),
                nærmeste_omtale=nd, afstand_dage=diff,
                forslag="ingen dagbogsomtale overhovedet — tjek værkets match i registret"
                        if not work_dates.get(rid)
                        else "omtalt i dagbogen, men ikke inden for ±60 dage"))
    write_queue("queue_timeline_work_mentions.csv",
                ["work_id", "værk", "tidstavle_id", "dato", "tidstavletekst",
                 "dagbogsomtaler_i_alt", "nærmeste_omtale", "afstand_dage", "forslag"],
                rows, lambda r: (r["work_id"], r["tidstavle_id"]))
    unmentioned = {r["work_id"] for r in rows} - {
        rid for e in entries for rid in e["works"]
        if any(abs(tl.date.fromisoformat(d).toordinal() - tl.date.fromisoformat(e["a"]).toordinal())
               <= WORK_WINDOW for d in work_dates.get(rid, ()))}
    print(f"works: {len(works)} linked, {len(works) - len(unmentioned)} mentioned within "
          f"±{WORK_WINDOW} days, {len(unmentioned)} not; {len(rows)} queue rows")


if __name__ == "__main__":
    main()
