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
import re
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


# Aggregate dimension: present-day country derived from (lat, lon).
# Hand-coded bounding boxes are accurate enough for HCA's Europe-focused
# travels; smaller / inland countries are listed first so they win the
# lookup when they overlap a larger neighbour.
COUNTRY_BBOXES = [
    # name_da,  name_en,         lat_min, lat_max, lon_min, lon_max
    ("Luxembourg",   "Luxembourg",     49.4, 50.2,  5.7,   6.6),
    ("Schweiz",      "Switzerland",    45.8, 47.9,  5.9,  10.6),
    ("Belgien",      "Belgium",        49.5, 51.6,  2.5,   6.5),
    ("Holland",      "Netherlands",    50.7, 53.7,  3.3,   7.3),
    ("Tjekkiet",     "Czech Republic", 48.5, 51.1, 12.0,  18.9),
    ("Slovakiet",    "Slovakia",       47.7, 49.6, 16.8,  22.6),
    ("Slovenien",    "Slovenia",       45.4, 46.9, 13.4,  16.6),
    ("Kroatien",     "Croatia",        42.4, 46.6, 13.4,  19.4),
    ("Østrig",       "Austria",        46.3, 49.0,  9.5,  17.2),
    ("Ungarn",       "Hungary",        45.7, 48.6, 16.1,  22.9),
    ("Polen",        "Poland",         49.0, 55.0, 14.1,  24.2),
    ("Danmark",      "Denmark",        54.5, 57.8,  8.0,  15.4),
    ("Tyskland",     "Germany",        47.3, 55.0,  5.8,  15.1),
    ("Frankrig",     "France",         41.3, 51.1, -5.2,  10.0),
    ("Italien",      "Italy",          36.5, 47.1,  6.6,  18.6),
    ("Spanien",      "Spain",          36.0, 43.8, -9.3,   4.4),
    ("Portugal",     "Portugal",       36.9, 42.2, -9.6,  -6.2),
    ("Irland",       "Ireland",        51.4, 55.4,-10.6,  -5.9),
    ("Storbritannien","United Kingdom",49.9, 59.5, -8.0,   2.0),
    ("Norge",        "Norway",         57.9, 71.2,  4.4,  31.1),
    ("Sverige",      "Sweden",         55.3, 69.1, 11.0,  24.2),
    ("Finland",      "Finland",        59.7, 70.1, 20.5,  31.6),
    ("Grækenland",   "Greece",         34.8, 41.8, 19.4,  28.3),
    ("Tyrkiet",      "Turkey",         36.0, 42.1, 26.0,  45.0),
    ("Malta",        "Malta",          35.8, 36.1, 14.2,  14.6),
    ("Marokko",      "Morocco",        21.4, 35.9,-17.0,  -1.0),
    ("Serbien",      "Serbia",         42.2, 46.2, 18.9,  23.0),
    ("Rumænien",     "Romania",        43.6, 48.3, 20.3,  29.7),
    ("Bulgarien",    "Bulgaria",       41.2, 44.3, 22.4,  28.6),
    ("Nordmakedonien","North Macedonia",40.8,42.4, 20.5,  23.0),
    ("Bosnien-Hercegovina","Bosnia and Herzegovina",42.5,45.3,15.7,19.6),
    ("Albanien",     "Albania",        39.6, 42.7, 19.3,  21.1),
    ("Montenegro",   "Montenegro",     41.8, 43.6, 18.4,  20.4),
]


def country_for(lat, lon):
    if lat is None or lon is None:
        return None, None
    for name_da, name_en, lat_min, lat_max, lon_min, lon_max in COUNTRY_BBOXES:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return name_da, name_en
    return None, None


# Lazy parsing of Work labels (Rule 1 in october-pipeline.md): publication
# place and year live as parenthetical fragments at the end of the title.
# Language detection is heuristic — falls back to the explicit Danish-prefix
# convention for translations ("Tyske -", "Engelske -", …). Deeper passes
# can later swap in scripts/parsers/add_language_column.py.

PAREN_RE = re.compile(r"\(([^()]+?)\)")
YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")
NOISE_MARKERS = ("ill.", " af ", "oversat", "tr.", "trans.", "ff.", "opl.",
                 "bind", "samling", "række", "oplag", "udgave", "pp.")
LANGUAGE_PREFIX = {
    "tyske": "de", "tysk": "de",
    "engelske": "en", "engelsk": "en",
    "franske": "fr", "fransk": "fr",
    "hollandske": "nl", "hollandsk": "nl",
    "italienske": "it", "italiensk": "it",
    "svenske": "sv", "svensk": "sv",
    "spanske": "es", "spansk": "es",
    "russiske": "ru", "russisk": "ru",
    "norske": "no", "norsk": "no",
    "latinske": "la", "latinsk": "la",
    "portugisiske": "pt", "portugisisk": "pt",
}


def parse_publication(label):
    """Return (place_label, year) extracted from the right-most parens segment
    that contains a year. Skips noise segments like '(Ill. af V. Pedersen)'."""
    for m in reversed(list(PAREN_RE.finditer(label))):
        content = m.group(1).strip()
        ym = YEAR_RE.search(content)
        if not ym:
            continue
        year = ym.group(1)
        before = content[:ym.start()].strip()
        before = re.sub(r"\d+\.\d+\.?\s*$", "", before).strip()
        before = before.rstrip(".,;:- ").strip()
        if any(n in before.lower() for n in NOISE_MARKERS):
            return None, year
        if not before or not re.search(r"[A-Za-zÆØÅæøåüöäß]", before):
            return None, year
        return before, year
    return None, None


def parse_language(label):
    """Return (iso_code, source) — explicit prefix when present, else
    ('und', 'default')."""
    head = re.split(r"[\s\-—]+", label.strip(), maxsplit=1)[0].rstrip(":,.")
    code = LANGUAGE_PREFIX.get(head.lower())
    if code:
        return code, "prefix"
    return "und", "default"


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
            country_da, country_en = country_for(match["lat"], match["lon"])
            rec["country_da"] = country_da
            rec["country_en"] = country_en
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

    country_counts = defaultdict(int)
    uncountried = 0
    for rec in places_payload:
        if rec.get("country_da"):
            country_counts[rec["country_da"]] += 1
        elif rec["geocoded"]:
            uncountried += 1
    print(f"  countries: {dict(sorted(country_counts.items(), key=lambda kv: -kv[1]))}")
    if uncountried:
        print(f"  {uncountried} geocoded places fell outside the bounding-box gazetteer")
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

    place_label_to_id = {}
    for p in places_payload:
        place_label_to_id[p["label"].casefold().strip()] = p["id"]
        if p.get("destination_en"):
            place_label_to_id.setdefault(p["destination_en"].casefold().strip(), p["id"])

    works_payload = []
    form_counts = defaultdict(int)
    lang_counts = defaultdict(int)
    matched_pub = 0
    for w in entities:
        if w["entity_type"] != "work":
            continue
        label = w["label"]
        place_label, year = parse_publication(label)
        lang, lang_src = parse_language(label)
        pub_place_id = None
        if place_label:
            pub_place_id = place_label_to_id.get(place_label.casefold().strip())
            if pub_place_id:
                matched_pub += 1
        rec = {
            "id": w["entity_id"],
            "label": label,
            "form_h3": w["form_h3"],
            "genre_h2": w["genre_h2"],
            "subform_h4": w["subform_h4"],
            "year_derived": w["year_derived"],
            "language": lang,
            "language_source": lang_src,
            "publication_place_label": place_label,
            "publication_place_id": pub_place_id,
            "publication_year": year,
            "description": w["description"],
        }
        works_payload.append(rec)
        if w["form_h3"]:
            form_counts[w["form_h3"]] += 1
        lang_counts[lang] += 1
    works_payload.sort(key=lambda x: x["label"].lower())
    print(f"  works: {len(works_payload):,}  "
          f"with parsed publication place: {sum(1 for w in works_payload if w['publication_place_label']):,}  "
          f"matched to a Place id: {matched_pub:,}")
    print(f"  forms: {dict(sorted(form_counts.items(), key=lambda kv: -kv[1])[:8])}")
    print(f"  languages: {dict(sorted(lang_counts.items(), key=lambda kv: -kv[1]))}")
    warnings.append(
        "Work language is heuristic: explicit Danish-prefix convention "
        "(Tyske/Engelske/…) when present, 'und' otherwise. Deeper detection "
        "via scripts/parsers/add_language_column.py is a separate pass."
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
            "works": len(works_payload),
            "works_with_publication_place": sum(1 for w in works_payload if w["publication_place_label"]),
            "works_publication_place_matched": matched_pub,
        },
        "places_by_country": dict(sorted(country_counts.items(), key=lambda kv: -kv[1])),
        "works_by_form": dict(sorted(form_counts.items(), key=lambda kv: -kv[1])),
        "works_by_language": dict(sorted(lang_counts.items(), key=lambda kv: -kv[1])),
        "warnings": warnings,
    }

    print("Writing JSON artifacts...")
    write_json("manifest.json", manifest)
    write_json("places.json", places_payload)
    write_json("places_visits.json", visits_payload)
    write_json("places_timeline.json", timeline_payload)
    write_json("places_works.json", works_payload)
    write_json("rejser.json", rejser_payload)
    write_json("works.json", works_payload)
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
