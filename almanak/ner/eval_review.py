#!/usr/bin/env python3
"""
eval_review.py — mål modellen på en returneret gennemsyns-eksport (build_review_page.py).

For hver gennemgået almanakpost, adskilt i sikre forslag (runde 1, markeret i teksten) og usikre (runde 3, tildelt fra en kø):
  godkendt         forslag står uændret tilbage / tildelt med modellens type
  type rettet      forslag står tilbage / tildelt med anden type
  slettet / afvist forslag slettet eller afvist (ikke et navn, eller forkert afgrænsning)
  tilføjet         menneskets egne markeringer (runde 1–2) = det, modellen overså
Præcision (sikre) = (godkendt + type rettet) / forslag; typet præcision = godkendt / forslag;
recall = fundet af modellen / (fundet + tilføjet), også med de usikre medregnet.
pr_omtaleform: samme tælling opdelt i egennavn / omtale / pronomen (menneskets angivelse, ellers heuristikken).
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


def kind_of(a):
    """Menneskets angivelse af omtaleform, ellers heuristikken (candidates.mention_kind)."""
    import candidates
    return a.get("mention_kind") or candidates.mention_kind(a["string"])


def measure(path):
    j, reviewed, ann, rej = load(path)
    c = collections.Counter()
    kinds = collections.defaultdict(collections.Counter)
    by_block = collections.defaultdict(collections.Counter)
    for a in ann:
        blk = a.get("block", "?")
        if a.get("origin") == "model":
            tier = "usikre" if a.get("tier") == "usikker" else "sikre"
            k = f"{tier}: godkendt" if a["type"] == a.get("model_type") else f"{tier}: type rettet"
            found = True
        else:
            k, found = "tilføjet", False
        c[k] += 1; by_block[blk][k] += 1
        kinds[kind_of(a)]["fundet af modellen" if found else "tilføjet"] += 1
    for r in rej:
        c["usikre: afvist" if r.get("uncertain") else "sikre: slettet"] += 1

    def rate(num, den):
        return round(num / den, 3) if den else None
    ok_s = c["sikre: godkendt"] + c["sikre: type rettet"]
    ok_u = c["usikre: godkendt"] + c["usikre: type rettet"]
    n_s, n_u = ok_s + c["sikre: slettet"], ok_u + c["usikre: afvist"]
    res = dict(annotator=j["meta"].get("annotator"), dage=len(reviewed), uafgjorte_usikre=j.get("uncertain_open"),
               tællinger=dict(sorted(c.items())),
               sikre_forslag=dict(n=n_s, praecision=rate(ok_s, n_s), typet_praecision=rate(c["sikre: godkendt"], n_s)),
               usikre_forslag=dict(n=n_u, andel_der_var_navne=rate(ok_u, n_u)),
               recall_sikre=rate(ok_s, ok_s + c["tilføjet"]), recall_med_usikre=rate(ok_s + ok_u, ok_s + ok_u + c["tilføjet"]),
               pr_omtaleform={k: {"fundet af modellen": v["fundet af modellen"], "tilføjet": v["tilføjet"],
                                  "recall": rate(v["fundet af modellen"], v["fundet af modellen"] + v["tilføjet"])}
                              for k, v in sorted(kinds.items())},
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
