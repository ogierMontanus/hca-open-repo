#!/usr/bin/env python3
"""
build_web_data.py
-----------------
Stage 2 of the October mockup pipeline (see docs/data-model/october-pipeline.md).

Reads star-shaped CSVs from data/normalized/ and emits denormalised JSON
artifacts to web/data/ that the static mockup can fetch directly.

Inputs (produced by scripts/normalization/hca_xlsx_to_csv.py and
scripts/build_web/parse_rejser_htm.py):
  data/normalized/entities.csv
  data/normalized/diary.csv
  data/normalized/references.csv
  data/normalized/rejser.tsv            (optional, geocoded add-on)
  data/normalized/rejser_journeys.tsv   (optional)

Outputs:
  web/data/manifest.json         pipeline + source provenance
  web/data/places.json           Places dimension + visit counts + coords
                                  (lat/lon populated where the place name
                                   matches the hcax.dk Rejser add-on)
  web/data/places_visits.json    per-Place diary entries
  web/data/places_timeline.json  per-Place year histogram
  web/data/places_works.json     per-Place co-occurring Works
                                  (page-level co-occurrence; placeholder
                                   until Sørens 2. register lands)
  web/data/rejser.json           geocoded travel add-on, kept separate
                                  from the Excel-derived data
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


def load_tsv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


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

    print("Loading Rejser add-on (hcax.dk)…")
    rejser_legs = load_tsv(os.path.join(NORMALIZED_DIR, "rejser.tsv"))
    rejser_journeys = load_tsv(os.path.join(NORMALIZED_DIR, "rejser_journeys.tsv"))
    print(f"  {len(rejser_legs):,} legs, {len(rejser_journeys):,} journeys")

    rejser_by_da = {}
    for leg in rejser_legs:
        da = (leg.get("Destination_DA") or "").strip()
        lat = (leg.get("Latitude") or "").strip()
        lon = (leg.get("Longitude") or "").strip()
        if not da or not lat or not lon:
            continue
        key = da.casefold()
        entry = rejser_by_da.setdefault(key, {
            "da": da,
            "en": (leg.get("Destination_EN") or "").strip(),
            "lat": float(lat),
            "lon": float(lon),
            "journeys": set(),
            "leg_count": 0,
        })
        entry["journeys"].add(leg["RejseID"])
        entry["leg_count"] += 1

    journey_titles = {j["RejseID"]: j.get("Title", "") for j in rejser_journeys}

    places_payload = []
    matched = 0
    legs_by_place_id = {}
    for p in places:
        pid = p["entity_id"]
        label = p["label"]
        rec = {
            "id": pid,
            "label": label,
            "visit_count": len(visits.get(pid, [])),
            "lat": None,
            "lon": None,
            "geocoded": False,
        }
        match = rejser_by_da.get(label.casefold().strip())
        if match:
            matched += 1
            rec["lat"] = match["lat"]
            rec["lon"] = match["lon"]
            rec["geocoded"] = True
            rec["destination_en"] = match["en"]
            rec["journey_count"] = len(match["journeys"])
            rec["leg_count"] = match["leg_count"]
            legs_by_place_id[pid] = [
                {
                    "rejse_id": leg["RejseID"],
                    "journey_title": journey_titles.get(leg["RejseID"], ""),
                    "destination_type": leg["DestinationType"],
                    "arrival_date": leg["ArrivalDate"],
                    "departure_date": leg["DepartureDate"],
                    "arrival_method": leg["ArrivalMethod"],
                    "lat": float(leg["Latitude"]) if leg["Latitude"] else None,
                    "lon": float(leg["Longitude"]) if leg["Longitude"] else None,
                }
                for leg in rejser_legs
                if leg["Destination_DA"].casefold().strip() == label.casefold().strip()
            ]
        places_payload.append(rec)
    places_payload.sort(key=lambda x: x["label"].lower())
    print(f"  matched {matched} of {len(places_payload)} places against Rejser DA names")
    warnings.append(
        f"Coordinates available for {matched}/{len(places_payload)} places via the "
        "hcax.dk Rejser add-on; the remaining majority is not geocoded for the October demo."
    )

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

    rejser_payload = {
        "source": "hcax.dk Rejser (data/raw/Rejser_HCA_X.htm)",
        "journeys": [
            {
                "rejse_id": j["RejseID"],
                "title": j["Title"],
                "year_range": j["YearRange"],
                "departure": j["Departure"],
                "return": j["Return"],
                "description": j["Description"],
                "countries": j["Countries"],
                "cost": j["Cost"],
            }
            for j in rejser_journeys
        ],
        "legs_by_place_id": legs_by_place_id,
    }

    xlsx_fn = latest_xlsx(RAW_DIR)
    source_xlsx_path = os.path.join(RAW_DIR, xlsx_fn) if xlsx_fn else None
    rejser_htm_path = os.path.join(RAW_DIR, "Rejser_HCA_X.htm")
    manifest = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_xlsx": xlsx_fn,
        "source_xlsx_sha256": sha256_of(source_xlsx_path) if source_xlsx_path else None,
        "source_rejser_htm": "Rejser_HCA_X.htm" if os.path.exists(rejser_htm_path) else None,
        "source_rejser_sha256": sha256_of(rejser_htm_path) if os.path.exists(rejser_htm_path) else None,
        "counts": {
            "places": len(places_payload),
            "places_geocoded": matched,
            "places_with_visits": len(visits_payload),
            "diary_entries": len(diary),
            "references": len(refs),
            "place_references": len(refs_for_places),
            "rejser_legs": len(rejser_legs),
            "rejser_journeys": len(rejser_journeys),
        },
        "warnings": warnings,
    }

    print("Writing JSON artifacts...")
    write_json("manifest.json", manifest)
    write_json("places.json", places_payload)
    write_json("places_visits.json", visits_payload)
    write_json("places_timeline.json", timeline_payload)
    write_json("places_works.json", works_payload)
    write_json("rejser.json", rejser_payload)
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
