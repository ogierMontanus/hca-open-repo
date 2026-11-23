#!/usr/bin/env python3
"""
eval_review.py — mål modellen på en returneret gennemsyns-eksport (build_review_page.py).

For hver gennemgået almanakpost:
  godkendt         forslag står uændret tilbage
  type rettet      forslag står tilbage med anden type
  slettet          forslag slettet (ikke et navn, eller forkert afgrænsning)
  tilføjet         menneskets egne markeringer = det, modellen overså
Præcision = godkendt / forslag; typet præcision = godkendt uden typeskift / forslag;
recall = (godkendt + type rettet) / (godkendt + type rettet + tilføjet).
Med to eksporter (Søren og Ole) måles også enighed om de endelige spænd (exact-F1 mellem dem).

  python almanak/ner/eval_review.py soren.json [ole.json]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path


def load(path):
    j = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    reviewed = set(j.get("reviewed_days", []))
    ann = [a for a in j["annotations"] if a["post_id"][4:] in reviewed and a["source"] == "almanak"]
    rej = [r for r in (j.get("rejected_suggestions") or []) if r["post_id"][4:] in reviewed]
    return j, reviewed, ann, rej


def measure(path):
    j, reviewed, ann, rej = load(path)
    c = collections.Counter()
    by_block = collections.defaultdict(collections.Counter)
    for a in ann:
        blk = a.get("block", "?")
        if a.get("origin") == "model":
            k = "godkendt" if a["type"] == a.get("model_type") else "type rettet"
        else:
            k = "tilføjet"
        c[k] += 1; by_block[blk][k] += 1
    for r in rej:
        c["slettet"] += 1
    sug = c["godkendt"] + c["type rettet"] + c["slettet"]
    found = c["godkendt"] + c["type rettet"]
    res = dict(annotator=j["meta"].get("annotator"), dage=len(reviewed), **c,
               praecision=round(found / sug, 3) if sug else None,
               typet_praecision=round(c["godkendt"] / sug, 3) if sug else None,
               recall=round(found / (found + c["tilføjet"]), 3) if found + c["tilføjet"] else None,
               aktiv_tid_min={k: round(v / 60) for k, v in j["meta"].get("active_seconds_by_block", {}).items()},
               pr_blok={b: dict(v) for b, v in sorted(by_block.items())})
    return res, {(a["post_id"], a["start"], a["end"]): a["type"] for a in ann}, reviewed


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    sets = []
    for p in argv[1:]:
        res, spans, days = measure(p)
        print(json.dumps(res, ensure_ascii=False, indent=1))
        sets.append((spans, days))
    if len(sets) == 2:
        (a, da), (b, db) = sets
        days = da & db
        a = {k: v for k, v in a.items() if k[0][4:] in days}
        b = {k: v for k, v in b.items() if k[0][4:] in days}
        both = set(a) & set(b)
        f1 = 2 * len(both) / (len(a) + len(b)) if a or b else 0
        typed = sum(1 for k in both if a[k] == b[k])
        print(f"enighed på {len(days)} fælles dage: spænd-F1 {f1:.3f}; samme type i {typed}/{len(both)} fælles spænd")


if __name__ == "__main__":
    main(sys.argv)
