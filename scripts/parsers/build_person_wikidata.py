#!/usr/bin/env python3
"""
build_person_wikidata.py
------------------------
Links register persons to Wikidata through the verified direct lex.dk articles
(build_persons_extra.load_lex_direct_links): Wikidata itself records which lex.dk article belongs to
which item, so the join is an identifier equality, not a name guess.

  Lex work                        Wikidata property
  Dansk Biografisk Leksikon       P8341
  Dansk Kvindebiografisk Leks.    P7939
  Weilbachs Kunstnerleksikon      P14992
  Gyldendals Teaterleksikon       P9466
  Den Store Danske (lex.dk)       P8313

A row is written only when ALL hold (CLAUDE.md «Faktakontrol» — live look-up, never memory):
  1. the article slug is the value of that property on exactly ONE human item (Q5),
  2. the item's birth AND death years are within ±1 year of the register label's years (user decision
     2026-10-31; sources disagree by a year often — the exact differences are kept in `year_diff`),
  3. the item is claimed by only one register person (Q-number not shared),
  4. if several lex works give different Q-numbers for one person, the person is left out (conflict).

Input   network: query.wikidata.org (live), cached in data/raw/wikidata/lex_props.json (--refresh to refetch)
Output  data/curated/persons_wikidata.csv   entity_id, wd, wd_label, basis, born, died, year_diff, verified_on
        data/curated/lex/queue_wikidata_review.csv   rejected / conflicting candidates (for inspection)
build_persons_extra.load_person_wikidata() reads the first two columns.
"""

import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "build_mockup"))
import build_persons_extra as B  # noqa: E402

CACHE = REPO / "data" / "raw" / "wikidata" / "lex_props.json"
OUT = REPO / "data" / "curated" / "persons_wikidata.csv"
QUEUE = REPO / "data" / "curated" / "lex" / "queue_wikidata_review.csv"
UA = "hca-open-repo/1.0 (https://github.com/; nh@sdu.dk)"
PROPS = {"dbl": "P8341", "dkbl": "P7939", "weilbach": "P14992", "teater": "P9466", "lex": "P8313"}
LABEL_TO_WORK = {"Dansk Biografisk Leksikon": "dbl", "Dansk Kvindebiografisk Leksikon": "dkbl",
                 "Weilbachs Kunstnerleksikon": "weilbach", "Gyldendals Teaterleksikon": "teater",
                 "Den Store Danske": "lex"}


def sparql(prop):
    q = f"""SELECT ?item ?val ?itemLabel (YEAR(?b) AS ?by) (YEAR(?d) AS ?dy) WHERE {{
      ?item wdt:{prop} ?val ; wdt:P31 wd:Q5 .
      OPTIONAL {{ ?item wdt:P569 ?b }} OPTIONAL {{ ?item wdt:P570 ?d }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "da,en". }} }}"""
    req = urllib.request.Request("https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q),
                                 headers={"User-Agent": UA, "Accept": "application/sparql-results+json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)["results"]["bindings"]
        except Exception as e:                      # transient 5xx / 429 / timeout
            print(f"  {prop}: {e!r} — retry {attempt + 1}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    raise SystemExit(f"{prop}: giving up")


def load_wd(refresh):
    if CACHE.exists() and not refresh:
        return json.load(open(CACHE, encoding="utf-8"))
    data = {}
    for work, prop in PROPS.items():
        rows = sparql(prop)
        data[work] = [{"q": r["item"]["value"].rsplit("/", 1)[-1], "val": r["val"]["value"],
                       "label": r.get("itemLabel", {}).get("value", ""),
                       "by": r.get("by", {}).get("value"), "dy": r.get("dy", {}).get("value")} for r in rows]
        print(f"  {prop} ({work}): {len(rows)} human items")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    json.dump(data, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    return data


TOLERANCE = 1


def near(year, wd_years):
    """Smallest signed difference (Wikidata − register) within ±TOLERANCE, else None."""
    diffs = [int(y) - int(year) for y in wd_years]
    ok = [d for d in diffs if abs(d) <= TOLERANCE]
    return min(ok, key=abs) if ok else None


def slug(url):
    return urllib.parse.unquote(urllib.parse.urlparse(url).path.lstrip("/"))


def main():
    wd = load_wd("--refresh" in sys.argv)
    # one entry per (work, id value, Q); an item with several birth/death statements keeps ALL its years
    index = {w: defaultdict(dict) for w in PROPS}
    for w, rows in wd.items():
        for r in rows:
            h = index[w][r["val"]].setdefault(r["q"], {"q": r["q"], "label": r["label"], "by": set(), "dy": set()})
            if r["by"]:
                h["by"].add(r["by"])
            if r["dy"]:
                h["dy"].add(r["dy"])

    labels = {}
    with open(B.ENTITIES, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["entity_type"] == "person":
                labels[r["entity_id"]] = (r.get("label") or "").strip()

    cands, queue = defaultdict(dict), []        # rid -> {q: info}
    for rid, links in B.load_lex_direct_links().items():
        born, died = B.parse_life(labels.get(rid, ""))
        for l in links:
            work = LABEL_TO_WORK[l["label"]]
            hits = list(index[work].get(slug(l["url"]), {}).values())
            why = None
            if len(hits) != 1:
                why = "no Wikidata item" if not hits else f"{len(hits)} items share the id"
            else:
                h = hits[0]
                if not (born and died and near(born, h["by"]) is not None and near(died, h["dy"]) is not None):
                    why = f"years differ (register {born}–{died}, Wikidata {sorted(h['by'])}–{sorted(h['dy'])})"
            if why:
                if hits:
                    queue.append({"rid": rid, "label": labels.get(rid, ""), "work": work, "url": l["url"],
                                  "q": ";".join(h["q"] for h in hits), "why": why})
                continue
            h = hits[0]
            db, dd = near(born, h["by"]), near(died, h["dy"])
            diff = "" if db == dd == 0 else f"born{db:+d} died{dd:+d}"
            cands[rid].setdefault(h["q"], {"label": h["label"], "basis": [], "born": born, "died": died,
                                           "diff": diff})["basis"].append(
                f"{PROPS[work]}={slug(l['url'])}")

    rows, by_q = [], defaultdict(list)
    for rid, qs in cands.items():
        if len(qs) > 1:
            queue.append({"rid": rid, "label": labels.get(rid, ""), "work": "*", "url": "",
                          "q": ";".join(qs), "why": "lex works point to different Q-numbers"})
            continue
        (q, info), = qs.items()
        by_q[q].append(rid)
        rows.append({"entity_id": rid, "wd": q, "wd_label": info["label"], "basis": " ".join(info["basis"]),
                     "born": info["born"], "died": info["died"], "year_diff": info["diff"], "verified_on": date.today().isoformat()})
    shared = {q for q, rids in by_q.items() if len(rids) > 1}
    for r in rows:
        if r["wd"] in shared:
            queue.append({"rid": r["entity_id"], "label": labels.get(r["entity_id"], ""), "work": "*", "url": "",
                          "q": r["wd"], "why": "Q-number claimed by several register persons"})
    rows = sorted((r for r in rows if r["wd"] not in shared), key=lambda r: r["entity_id"])

    cols = ["entity_id", "wd", "wd_label", "basis", "born", "died", "year_diff", "verified_on"]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    with open(QUEUE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["rid", "label", "work", "url", "q", "why"])
        w.writeheader()
        w.writerows(sorted(queue, key=lambda r: (r["why"][:6], r["rid"])))
    from collections import Counter
    print(f"persons_wikidata.csv: {len(rows)} persons; queue rows: {len(queue)} "
          f"{dict(Counter(re.sub(r' \(.*', '', q['why']) for q in queue))}")


if __name__ == "__main__":
    main()
