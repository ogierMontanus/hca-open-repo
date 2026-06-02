#!/usr/bin/env python3
"""
build_web_data.py
-----------------
Stage 2 of the October mockup pipeline (see docs/data-model/october-pipeline.md).

Reads star-shaped CSVs from data/normalized/ and emits denormalised JSON
artifacts to web/data/ that the static mockup can fetch directly.

Inputs (produced by scripts/normalization/hca_xlsx_to_csv.py):
  data/normalized/entities.csv
  data/normalized/diary.csv
  data/normalized/references.csv

Outputs:
  web/data/manifest.json         pipeline + source provenance
  web/data/places.json           Places dimension + visit counts
  web/data/places_visits.json    per-Place diary entries
  web/data/places_timeline.json  per-Place year histogram
  web/data/places_works.json     per-Place co-occurring Works
                                  (page-level co-occurrence; placeholder
                                   until Sørens 2. register lands)

This skeleton implements the shapes; refine the per-query semantics once
the 3-5 Places demo queries are pinned down.
"""

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
NORMALIZED_DIR = os.path.join(ROOT, "data", "normalized")
RAW_DIR = os.path.join(ROOT, "data", "raw")
OUT_DIR = os.path.join(ROOT, "web", "data")

SNIPPET_CHARS = 220


def load_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def latest_xlsx(raw_dir):
    candidates = []
    if not os.path.isdir(raw_dir):
        return None
    for fn in os.listdir(raw_dir):
        if fn.lower().endswith(".xlsx") and "hca-repository" in fn.lower():
            candidates.append(fn)
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1]


def write_json(name, payload):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=False)
    print(f"  Wrote {os.path.relpath(path, ROOT)}  ({os.path.getsize(path):,} bytes)")


def build(verbose=False):
    warnings = []

    print("Loading normalised CSVs...")
    entities = load_csv(os.path.join(NORMALIZED_DIR, "entities.csv"))
    diary = load_csv(os.path.join(NORMALIZED_DIR, "diary.csv"))
    refs = load_csv(os.path.join(NORMALIZED_DIR, "references.csv"))
    print(f"  {len(entities):,} entities, {len(diary):,} diary rows, {len(refs):,} refs")

    places = [e for e in entities if e["entity_type"] == "place"]
    works = {e["entity_id"]: e for e in entities if e["entity_type"] == "work"}
    place_ids = {p["entity_id"] for p in places}
    print(f"  {len(places):,} places, {len(works):,} works")

    diary_by_volpage = {}
    for d in diary:
        key = (d["vol"], d["page"])
        diary_by_volpage.setdefault(key, []).append(d)

    refs_for_places = [r for r in refs if r["entity_id"] in place_ids]
    print(f"  {len(refs_for_places):,} place-references")

    visits = defaultdict(list)
    timeline = defaultdict(lambda: defaultdict(int))
    refs_by_page = defaultdict(list)

    for r in refs:
        refs_by_page[(r["vol"], r["page"])].append(r["entity_id"])

    for r in refs_for_places:
        pid = r["entity_id"]
        key = (r["vol"], r["page"])
        diary_rows = diary_by_volpage.get(key, [])
        if not diary_rows:
            continue
        first = diary_rows[0]
        date = first.get("date") or ""
        year = (first.get("year") or "").strip()
        text = (first.get("text") or "").strip()
        snippet = text[:SNIPPET_CHARS] + ("…" if len(text) > SNIPPET_CHARS else "")
        visits[pid].append({
            "vol": r["vol"],
            "page": r["page"],
            "date": date,
            "year": year,
            "snippet": snippet,
        })
        if year and year.isdigit():
            timeline[pid][int(year)] += 1

    work_cooccurrence = defaultdict(lambda: defaultdict(int))
    for r in refs_for_places:
        pid = r["entity_id"]
        page_entities = refs_by_page.get((r["vol"], r["page"]), [])
        for eid in page_entities:
            if eid in works and eid != pid:
                work_cooccurrence[pid][eid] += 1

    places_payload = []
    for p in places:
        pid = p["entity_id"]
        places_payload.append({
            "id": pid,
            "label": p["label"],
            "visit_count": len(visits.get(pid, [])),
            "lat": None,
            "lon": None,
        })
    places_payload.sort(key=lambda x: x["label"].lower())
    warnings.append("Places dimension has no coordinates — geocoding pass TBD.")

    visits_payload = {
        pid: sorted(rows, key=lambda v: (v["year"] or "", v["date"] or ""))
        for pid, rows in visits.items()
    }

    timeline_payload = {
        pid: dict(sorted(years.items()))
        for pid, years in timeline.items()
    }

    works_payload = {}
    for pid, work_counts in work_cooccurrence.items():
        ranked = sorted(work_counts.items(), key=lambda kv: -kv[1])
        works_payload[pid] = [
            {
                "work_id": wid,
                "work_label": works[wid]["label"],
                "page_count": count,
            }
            for wid, count in ranked[:25]
        ]
    warnings.append(
        "places_works.json uses page-level co-occurrence as a placeholder for "
        "the Work↔Place M-M edge from Sørens 2. register (pending)."
    )

    xlsx_fn = latest_xlsx(RAW_DIR)
    source_xlsx_path = os.path.join(RAW_DIR, xlsx_fn) if xlsx_fn else None
    manifest = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_xlsx": xlsx_fn,
        "source_xlsx_sha256": sha256_of(source_xlsx_path) if source_xlsx_path else None,
        "counts": {
            "places": len(places_payload),
            "places_with_visits": len(visits_payload),
            "diary_entries": len(diary),
            "references": len(refs),
            "place_references": len(refs_for_places),
        },
        "warnings": warnings,
    }

    print("Writing JSON artifacts...")
    write_json("manifest.json", manifest)
    write_json("places.json", places_payload)
    write_json("places_visits.json", visits_payload)
    write_json("places_timeline.json", timeline_payload)
    write_json("places_works.json", works_payload)
    print("Done.")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()
    try:
        build(verbose=args.verbose)
    except FileNotFoundError as e:
        sys.exit(
            f"Missing input: {e.filename}\n"
            f"Run scripts/normalization/hca_xlsx_to_csv.py first."
        )


if __name__ == "__main__":
    main()
