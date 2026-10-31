#!/usr/bin/env python3
"""
build_person_nationality_added.py
---------------------------------
Phase 2d/2e of docs/plan-lex-dk-links.md §3d: turns DBL look-ups into the ADDED nationality
value «Dansk*» ("Født i Danmark eller bosat der i længere årrække").

Hard criterion (user decision 2026-10-29): only a CONFIRMED Dansk Biografisk Leksikon article
(name compatible with the URL slug AND both register life years in the article's lead) puts a
person in the bucket. The assumption "unmarked = Danish" is abandoned: everybody else with no
nationality simply stays unknown.

Input   data/curated/lex/persons_dbl.csv           from lex_sitemap_match.py --tier all --hosts dbl
        data/curated/lex/persons_lex_sitemap.csv   (tier A, all works; its DBL rows are merged in)
        data/normalized/person_ethnic_descriptors.csv   register nationality (leading, subject)
Output  data/curated/person_nationality_added.csv  ADDED data: one row per person with exactly one
                                                    confirmed DBL article
        data/curated/lex/queue_dbl_review.csv      persons with only "likely" DBL candidates
                                                    (namesake/relative risk) — manual review
        data/curated/lex/qa_dbl_sample.csv         10 % random sample of the added rows for a
                                                    spot check (empty `decision` column)

Nothing here writes to the register's own fields (docs/external-links.md §2a: added data is
kept apart and marked).
"""

import csv
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import quote, unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lex_link_candidates import fetch_check  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
LEX = REPO / "data" / "curated" / "lex"
N = REPO / "data" / "normalized"
OUT = REPO / "data" / "curated" / "person_nationality_added.csv"
DECISIONS = LEX / "dbl_review_decisions.csv"


def main():
    rows = list(csv.DictReader(open(LEX / "persons_dbl.csv", encoding="utf-8")))
    a_path = LEX / "persons_lex_sitemap.csv"
    if a_path.exists():
        seen = {(r["rid"], r["url"]) for r in rows}
        for r in csv.DictReader(open(a_path, encoding="utf-8")):
            if r["work"] == "dbl" and (r["rid"], r["url"]) not in seen:
                rows.append(r)
    tiers = {r["rid"]: r for r in csv.DictReader(open(LEX / "persons_tiers.csv", encoding="utf-8"))}
    reg = defaultdict(set)
    for r in csv.DictReader(open(N / "person_ethnic_descriptors.csv", encoding="utf-8")):
        if r["position_type"] == "leading" and r["referent_hint"] == "subject":
            reg[r["entity_id"]].add(r["nationality_key"])

    by = defaultdict(list)
    for r in rows:
        if r["work"] == "dbl":
            by[r["rid"]].append(r)
    today = date.today().isoformat()
    added, review = [], []
    for rid, rs in by.items():
        conf = [r for r in rs if r["verdict"] == "confirmed"]
        likely = [r for r in rs if r["verdict"] == "likely"]
        if len(conf) == 1:
            c = conf[0]
            foreign = sorted(k for k in reg.get(rid, set()) if k != "dansk")
            added.append({
                "confirmed_by": "auto", "alias_of": "",
                "rid": rid, "label": c["label"], "nationality_key": "dansk", "nat_basis": "dbl_optagelse",
                "source_url": c["url"], "page_title": c["page_title"], "tier": tiers.get(rid, {}).get("tier", ""),
                "verified_on": c.get("queried_on") or today,
                "conflict_with_register": ";".join(foreign),     # foreign register nationality → both values
            })
        elif len(conf) > 1:
            for r in conf:
                review.append({**r, "why": "flere bekræftede DBL-artikler"})
        elif likely:
            for r in likely:
                review.append({**r, "why": "kun «likely» (ét eller intet årstal / mulig navnebror)"})
    # An article claimed by SEVERAL register persons (Jens Baggesen / his son, H.C. Ørsted / his grandson) can
    # only belong to one: keep the claimant whose life years are the FIRST two years on the article (its own
    # dates come first in DBL's meta description); the rest go to the review queue.
    cache_path = REPO / "data" / "raw" / "lex" / "page_cache.json"
    cache = json.load(open(cache_path, encoding="utf-8")) if cache_path.exists() else {}
    by_decoded = {unquote(k[:-3]): k for k in cache if k.endswith("#v3")}
    claims = defaultdict(list)
    for r in added:
        claims[r["source_url"]].append(r)
    fetched = 0
    for url, cl in claims.items():
        if len(cl) < 2:
            continue
        # the cache is keyed by the sitemap's percent-encoded URL; source_url is stored decoded
        ck = by_decoded.get(url) or (quote(url, safe=":/._-~%") + "#v3")
        ent = cache.get(ck)
        if not ent or "yo" not in ent:
            time.sleep(1.0)
            ent = fetch_check(quote(url, safe=":/._-~%"), None, None)
            if ent.get("status") == 200:
                cache[ck] = ent
            fetched += 1
        yo = ent.get("yo", [])
        keep = []
        for r in cl:
            m = re.search(r"\((?:ca\.\s*)?(\d{4})\s*[–-]\s*(\d{4})\)", r["label"])
            if m and len(yo) >= 2 and (m.group(1), m.group(2)) == (yo[0], yo[1]):
                keep.append(r)
        for r in cl:
            if r not in keep:
                added.remove(r)
                review.append({"rid": r["rid"], "label": r["label"], "search_name": "", "tier": r["tier"],
                               "url": r["source_url"], "page_title": r["page_title"], "years_found": "",
                               "verdict": "confirmed", "why": "delt artikel: personens levetid er ikke artiklens egne første årstal"})
    if fetched:
        json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
    # Manual review of the queue (data/curated/lex/dbl_review_decisions.csv, one row per queued
    # (rid, url)): `accept` adds the person (final_url = the article, which for a DBL cross-reference
    # page is the TARGET article); `accept_alias` is the same person under a second register entry
    # (maiden/married name), so the article is deliberately shared and alias_of names the other rid;
    # `reject` / `open` change nothing and `reject` is not queued again.
    decided = {}
    if DECISIONS.exists():
        for d in csv.DictReader(open(DECISIONS, encoding="utf-8")):
            decided[(d["rid"], d["url"])] = d
    have = {r["rid"] for r in added}
    for key, d in decided.items():
        rid = key[0]
        if d["decision"] not in ("accept", "accept_alias") or rid in have or rid not in tiers:
            continue
        fin = d["final_url"] or key[1]
        t = tiers[rid]
        # independent of the live queue: a stub that is no longer queued (it is skipped as a cross-reference)
        # must not lose its reviewed decision
        title = unquote(fin.rsplit("/", 1)[-1]).replace("_", " ") + " – Dansk Biografisk Leksikon | Lex"
        added.append({
            "confirmed_by": "manual_review", "alias_of": d["alias_of"],
            "rid": rid, "label": t["label"], "nationality_key": "dansk", "nat_basis": "dbl_optagelse",
            "source_url": fin, "page_title": title,
            "tier": t.get("tier", ""), "verified_on": today,
            "conflict_with_register": ";".join(sorted(k for k in reg.get(rid, set()) if k != "dansk")),
        })
        have.add(rid)
    review = [r for r in review
              if decided.get((r["rid"], r.get("url", "")), {}).get("decision") not in ("accept", "accept_alias", "reject")]
    added.sort(key=lambda r: (r["tier"], r["rid"]))
    cols = ["rid", "label", "nationality_key", "nat_basis", "source_url", "page_title", "tier",
            "verified_on", "conflict_with_register", "confirmed_by", "alias_of"]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(added)
    if review:
        rcols = ["rid", "label", "search_name", "tier", "url", "page_title", "years_found", "verdict", "why"]
        with open(LEX / "queue_dbl_review.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=rcols, extrasaction="ignore")
            w.writeheader()
            w.writerows(sorted(review, key=lambda r: r["rid"]))
    # The 10 % QA sample is drawn ONCE (seed 2026) and then kept: it carries the reviewer's decisions
    # and a re-run must not overwrite them. Delete the file to draw a fresh sample.
    qa = LEX / "qa_dbl_sample.csv"
    sample = []
    if not qa.exists():
        random.seed(2026)
        sample = random.sample([r for r in added if r["confirmed_by"] == "auto"], max(1, len(added) // 10)) if added else []
        with open(qa, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols + ["decision", "reviewer"])
            w.writeheader()
            for r in sample:
                w.writerow({**r, "decision": "", "reviewer": ""})

    explicit = {k for k, v in reg.items() if "dansk" in v}
    ids = {r["rid"] for r in added}
    tc = Counter(r["tier"] for r in added)
    print(f"added «Dansk*» rows: {len(added)}  by tier {dict(tc)}")
    print(f"  with a foreign register nationality as well: {sum(1 for r in added if r['conflict_with_register'])}")
    print(f"  register-explicit 'dansk' (leading): {len(explicit)}; of them in DBL: {len(explicit & ids)}")
    print(f"  bucket «Dansk*» = DBL ∪ register-explicit: {len(ids | explicit)}")
    print(f"  review queue rows: {len(review)} (persons: {len({r['rid'] for r in review})}); QA sample: {'kept' if not sample else len(sample)}")


if __name__ == "__main__":
    main()
