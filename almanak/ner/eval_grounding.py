#!/usr/bin/env python3
"""
eval_grounding.py — mål en ner_page_grounding.csv mod Sørens dagbogsspans (overlap-stikprøven).

For de 32 dagbogsdage: hvert automatisk fund, der ligger i dagens tekst, er
  korrekt      hvis det overlapper et menneskeligt Person/Sted/Lokalitet-span,
  eksakt       hvis det tilmed har samme grænser,
  fejl         ellers (fundet ord er ikke markeret af annotatoren).
Recall = andel af menneskets Person- og Sted-spans, som et fund overlapper.

Brug (fra repo-roden):
  python almanak/ner/eval_grounding.py data/normalized/ner_page_grounding.csv [gammel.csv ...]
"""
from __future__ import annotations

import collections
import csv
import sys

import gold as G

KEEP = {"Person", "Sted", "Lokalitet"}


def evaluate(csv_path, entries, ann, daymaps):
    by_page = collections.defaultdict(list)
    with open(csv_path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["mention_start"]:
                by_page[(r["vol"], r["page"])].append(r)
    gold_pp = []   # (vol, page, s, e, type, string, block)
    for a in ann:
        if a["source"] != "dagbog" or a["type"] not in KEEP:
            continue
        dm = daymaps[a["post_id"][4:]]
        vol, page, s, e = dm.to_page(a["start"], a["end"])
        gold_pp.append((vol, page, s, e, a["type"], a["string"], a["block"]))
    # dagenes udstrækning pr. side (kun fund inde i de annoterede dage tælles)
    ranges = collections.defaultdict(list)
    for dm in daymaps.values():
        for a, b, vol, page, row_start in dm.segs:
            ranges[(vol, page)].append((row_start, row_start + (b - a)))
    res = collections.Counter()
    per_method = collections.defaultdict(collections.Counter)
    errors = []
    covered = set()
    for key, rows in by_page.items():
        if key not in ranges:
            continue
        for r in rows:
            s, e = int(r["mention_start"]), int(r["mention_end"])
            if not any(a <= s and e <= b for a, b in ranges[key]):
                continue
            hit = [g for g in gold_pp if g[0] == key[0] and g[1] == key[1] and g[2] < e and s < g[3]]
            m = r["method"]
            res["fund"] += 1; per_method[m]["fund"] += 1
            if hit:
                res["korrekt"] += 1; per_method[m]["korrekt"] += 1
                covered.update(hit)
                if any(g[2] == s and g[3] == e for g in hit):
                    res["eksakt"] += 1; per_method[m]["eksakt"] += 1
            else:
                errors.append((key, r["mention_text"], m, r["entity_label"]))
    tot = collections.Counter(g[4] for g in gold_pp if g[4] in ("Person", "Sted"))
    cov = collections.Counter(g[4] for g in covered if g[4] in ("Person", "Sted"))
    return res, per_method, tot, cov, errors


def main(argv):
    entries = G.load_entries()
    ann = G.load_gold()
    rows = G.diary_rows()
    dates = {e["date"] for e in entries.values() if e["src"] == "dagbog"}
    parts = G.diary_day_pages(rows, dates)
    daymaps = {d: G.DayMap(parts[d]) for d in dates}
    bad = [d for d in dates if daymaps[d].view.text != entries["DAG-" + d]["text"]]
    if bad:
        sys.exit(f"Dagstekst afviger fra annoteringssiden: {bad}")
    for path in argv[1:]:
        res, pm, tot, cov, errors = evaluate(path, entries, ann, daymaps)
        print(f"== {path}")
        p = res["korrekt"] / res["fund"] if res["fund"] else 0
        print(f"  fund i dagene: {res['fund']}  præcision {p:.0%}  eksakte grænser {res['eksakt']}")
        for t in ("Person", "Sted"):
            print(f"  recall {t}: {cov[t]}/{tot[t]} = {cov[t] / tot[t]:.0%}")
        for m, c in sorted(pm.items(), key=lambda kv: -kv[1]["fund"]):
            print(f"    {m:18} {c['fund']:4}  korrekt {c['korrekt']:4}  eksakt {c['eksakt']:4}")
        for e in errors:
            print("    FEJL?", e)


if __name__ == "__main__":
    main(sys.argv)
