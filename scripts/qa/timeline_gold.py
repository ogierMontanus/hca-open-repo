"""timeline_gold.py — plan-tidstavle-data.md step 1.3.

Measures the name linking of build_timeline.py (precision AND recall) against
a hand-annotated gold sample.

  python scripts/qa/timeline_gold.py draw      draw the stratified sample
  python scripts/qa/timeline_gold.py score     precision / recall per entity type

draw  -> data/curated/timeline_gold.csv: 10 entries per (volume × kind) cell
         (all of a cell when it has fewer), fixed seed, so the sample is
         reproducible. Never overwrites existing annotations: rows already in
         the file stay, only missing sample ids are added.
         Per row the annotator fills gold_persons / gold_places / gold_works
         with the register ids of EVERY person / place / work the text names
         (`;`-separated; empty = none) and sets `done` to `ja`. The columns
         pipeline_* show what the pipeline linked — read them AFTER forming
         your own judgement, to avoid anchoring on them.
score -> counts only rows with done=ja; prints micro precision, recall and the
         misses, so the lists of unlinked words (build_timeline.py --report)
         can be targeted.
"""

import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "normalization"))

import timeline_linked as tl  # noqa: E402

GOLD = REPO_ROOT / "data" / "curated" / "timeline_gold.csv"
PER_CELL = 10
SEED = 20261028
TYPES = ("persons", "places", "works")
FIELDS = (["tidstavle_id", "vol", "kind", "date", "text"]
          + [f"pipeline_{t}" for t in TYPES]
          + [f"gold_{t}" for t in TYPES] + ["done", "annotator", "note"])


def ids(cell: str) -> set:
    return {x.strip() for x in cell.split(";") if x.strip()}


def read() -> list[dict]:
    if not GOLD.exists():
        return []
    with GOLD.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def draw() -> None:
    entries = tl.load_entries()
    labels = tl.load_labels()
    with (tl.NORM / "places.csv").open(encoding="utf-8-sig", newline="") as f:
        labels.update({r["entity_id"]: r["label"] for r in csv.DictReader(f)})
    cells = defaultdict(list)
    for e in entries:
        cells[(e["v"], e["kind"])].append(e)
    rng = random.Random(SEED)
    sample = []
    for key in sorted(cells):
        pool = sorted(cells[key], key=lambda e: e["id"])
        sample += rng.sample(pool, min(PER_CELL, len(pool)))
    have = {r["tidstavle_id"]: r for r in read()}
    rows = list(have.values())
    for e in sorted(sample, key=lambda e: e["id"]):
        if e["id"] in have:
            continue
        r = dict(tidstavle_id=e["id"], vol=e["v"], kind=e["kind"], date=e["a"],
                 text=" ".join(e["text"].split()), done="", annotator="", note="")
        for t in TYPES:
            r[f"pipeline_{t}"] = ";".join(f"{i}={labels.get(i, i)}" for i in sorted(e[t]))
            r[f"gold_{t}"] = ""
        rows.append(r)
    rows.sort(key=lambda r: r["tidstavle_id"])
    with GOLD.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows in {GOLD.relative_to(REPO_ROOT)} "
          f"({len(cells)} cells, {sum(1 for r in rows if r['done'] == 'ja')} annotated)")


def score(rows=None) -> dict:
    """{type: dict(tp, fp, fn, precision, recall, n)} over rows with done=ja."""
    rows = [r for r in (rows if rows is not None else read()) if r["done"] == "ja"]
    out = {}
    for t in TYPES:
        tp = fp = fn = 0
        for r in rows:
            pred = {x.split("=")[0] for x in ids(r[f"pipeline_{t}"])}
            gold = ids(r[f"gold_{t}"])
            tp += len(pred & gold)
            fp += len(pred - gold)
            fn += len(gold - pred)
        out[t] = dict(tp=tp, fp=fp, fn=fn, n=len(rows),
                      precision=tp / (tp + fp) if tp + fp else None,
                      recall=tp / (tp + fn) if tp + fn else None)
    return out


def report() -> None:
    res = score()
    n = next(iter(res.values()))["n"]
    print(f"{n} annotated rows")
    if not n:
        print("nothing annotated yet — fill gold_* and done=ja in", GOLD.relative_to(REPO_ROOT))
        return
    for t, m in res.items():
        p = f"{m['precision']:.1%}" if m["precision"] is not None else "–"
        r = f"{m['recall']:.1%}" if m["recall"] is not None else "–"
        print(f"  {t:8} precision {p:>6}  recall {r:>6}   (tp {m['tp']}, fp {m['fp']}, fn {m['fn']})")
    miss = Counter()
    for row in (r for r in read() if r["done"] == "ja"):
        for t in TYPES:
            pred = {x.split("=")[0] for x in ids(row[f"pipeline_{t}"])}
            for g in ids(row[f"gold_{t}"]) - pred:
                miss[(t, g)] += 1
    for (t, g), n in miss.most_common(15):
        print(f"  missed {t}: {g} ×{n}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("draw", "score"):
        sys.exit(__doc__)
    draw() if sys.argv[1] == "draw" else report()
