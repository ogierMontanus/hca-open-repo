#!/usr/bin/env python3
"""
build_places_extra.py
---------------------
Generates mockup/data/places-extra.js — a `PLACES_EXTRA` JS object with
one entry per row in data/normalized/entities.csv where
entity_type == 'place' (the LocationID place register, LOC… ids — see
scripts/normalization/place_register.py).

Category, country, visited/mentioned status and — first choice —
coordinates come from data/normalized/places.csv (written by
hca_xlsx_to_csv.py from the curated data/HCA_Steder_GÆLDENDE_*.xlsx).
Where that workbook has no coordinates (GeocodingStatus "Ikke fundet"),
three older sources fill the gap, in precedence order:

  1. the hcax.dk Rejser add-on (data/normalized/rejser.tsv) when the
     place label matches (Andersen's actual travel legs).
  2. data/normalized/sv14_places_reconciled.csv — produced by
     scripts/build_mockup/reconcile_sv14_geo.py from the TEI place-list
     data/raw/SV14_places.xml.
  3. HERRED_AMT_RE below: a handful of remaining places state their own
     Danish administrative location in the label itself, in the
     abbreviated form "<sted>, <herred> H., <amt> A" (e.g. "Sæby, Løve
     H., Holbæk A"). Herred/Amt are exclusively Danish units, so a match
     infers country_da = "Danmark" with no coordinates.

Rejser/SV14 matches also supply `destination_en` (the English spelling)
even when the coordinates come from the place register.

`geo_source` on each entry records which source supplied the coordinates
("register", "rejser", "sv14" or "herred_amt"). The hand-curated `PLACES`
object inside mockup/place.html (if any) keeps precedence over all of
them; PLACES_EXTRA fills every other gap so any ?reg=… link to place.html
resolves to real metadata instead of a blank page.

Stdlib only. Run after scripts/normalization/hca_xlsx_to_csv.py (which
writes entities.csv, references.csv and places.csv),
scripts/build_web/parse_rejser_htm.py and
scripts/build_mockup/reconcile_sv14_geo.py.
"""

import csv
import json
import os
import re
import sys
from collections import Counter

import _diary_scope  # noqa: E402  (sibling module; scripts run from repo root)

ROOT       = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENTITIES   = os.path.join(ROOT, "data", "normalized", "entities.csv")
REFS       = os.path.join(ROOT, "data", "normalized", "references.csv")
DIARY      = os.path.join(ROOT, "data", "normalized", "diary.csv")
REJSER     = os.path.join(ROOT, "data", "normalized", "rejser.tsv")
SV14       = os.path.join(ROOT, "data", "normalized", "sv14_places_reconciled.csv")
PLACES_CSV = os.path.join(ROOT, "data", "normalized", "places.csv")
OUT        = os.path.join(ROOT, "mockup", "data", "places-extra.js")

# Reuse the 33-country bounding-box gazetteer from build_web_data.py.
# Each entry: (name_da, lat_min, lat_max, lon_min, lon_max). Designed to
# cover the geocoded subset; ties broken by smaller area first.
COUNTRIES = [
    ("Danmark",       54.5, 57.8,   8.0, 15.2),
    ("Tyskland",      47.3, 55.0,   5.9, 15.0),
    ("Storbritannien",49.9, 60.9,  -8.7,  1.8),
    ("Frankrig",      41.4, 51.1,  -5.2,  9.6),
    ("Italien",       36.6, 47.1,   6.6, 18.5),
    ("Schweiz",       45.8, 47.8,   5.9, 10.5),
    ("Østrig",        46.4, 49.0,   9.5, 17.2),
    ("Tjekkiet",      48.5, 51.1,  12.1, 18.9),
    ("Ungarn",        45.7, 48.6,  16.1, 22.9),
    ("Nederlandene",  50.7, 53.6,   3.3,  7.2),
    ("Belgien",       49.5, 51.5,   2.5,  6.4),
    ("Sverige",       55.3, 69.1,  10.9, 24.2),
    ("Norge",         57.9, 71.2,   4.6, 31.1),
    ("Spanien",       35.9, 43.8,  -9.3,  4.3),
    ("Portugal",      36.9, 42.2,  -9.5, -6.2),
    ("Polen",         49.0, 54.8,  14.1, 24.1),
    ("Grækenland",    34.8, 41.7,  19.4, 28.2),
    ("Tyrkiet",       35.8, 42.1,  26.0, 44.8),
    ("Rusland",       41.2, 81.9,  19.6,179.0),
    ("Vatikanstaten", 41.9, 41.91, 12.45,12.46),
    ("Irland",        51.4, 55.4,  -10.5,-5.4),
    ("Luxembourg",    49.4, 50.2,   5.7,  6.5),
    ("Liechtenstein", 47.0, 47.3,   9.4,  9.7),
    ("Monaco",        43.7, 43.8,   7.4,  7.5),
    ("San Marino",    43.8, 44.0,  12.4, 12.5),
    ("Slovakiet",     47.7, 49.6,  16.8, 22.6),
    ("Slovenien",     45.4, 46.9,  13.4, 16.6),
    ("Kroatien",      42.4, 46.6,  13.5, 19.4),
    ("Serbien",       42.2, 46.2,  18.8, 23.0),
    ("Rumænien",      43.6, 48.3,  20.3, 29.7),
    ("Bulgarien",     41.2, 44.2,  22.4, 28.6),
    ("Marokko",       21.3, 35.9, -17.0,  -1.0),
    ("Israel",        29.5, 33.3,  34.3, 35.9),
]


# A handful of STED-REGISTER labels carry no coordinates in either source
# but do state their own administrative location in the abbreviated form
# "<sted>, <herred> H., <amt> A" — e.g. "Sæby, Løve H., Holbæk A"
# (Reg0020710) or "Hundstrup, Salling H., Svendborg A" (Reg0008990).
# Herred ("H.") and Amt ("A") are exclusively Danish administrative units
# (abolished 1970/1793–1970 respectively), so a match is enough to infer
# country_da = "Danmark" even with zero geocoding. The whitespace before
# "H" and before "A" is required so the abbreviation can't fire on a
# label that merely happens to end in the letter A (e.g. "Genova"; note
# this also correctly does NOT match "Beldringe Baarse S., Præstø A" —
# "S." is Sogn, a different unit the caller didn't ask about).
HERRED_AMT_RE = re.compile(r",\s*(?P<herred>[^,]+?)\s+H\.?,\s*(?P<amt>[^,]+?)\s+A\.?\s*$")


def country_for(lat: float, lon: float) -> str | None:
    candidates = [(n, (lat_max - lat_min) * (lon_max - lon_min))
                  for (n, lat_min, lat_max, lon_min, lon_max) in COUNTRIES
                  if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max]
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1])
    return candidates[0][0]


def load_rejser_geocodes() -> dict[str, dict]:
    """Returns {casefolded_label: {lat, lon, country_da, destination_en}}.
    Indexed by both Destination_DA and Destination_EN so case-insensitive
    lookups from STED-REGISTER labels resolve via either spelling."""
    geo: dict[str, dict] = {}
    if not os.path.exists(REJSER):
        return geo
    with open(REJSER, encoding="utf-8", newline="") as f:
        rdr = csv.DictReader(f, delimiter="\t")
        for row in rdr:
            try:
                lat = float(row.get("Latitude") or "")
                lon = float(row.get("Longitude") or "")
            except ValueError:
                continue
            entry = {
                "lat":            round(lat, 5),
                "lon":            round(lon, 5),
                "country_da":     country_for(lat, lon),
                "destination_en": (row.get("Destination_EN") or "").strip() or None,
            }
            for key_field in ("Destination_DA", "Destination_EN", "Destination_ORG"):
                v = (row.get(key_field) or "").strip().casefold()
                if v:
                    geo.setdefault(v, entry)
    return geo


def load_sv14_reconciled() -> dict[str, dict]:
    """Returns {entity_id: {lat, lon, country_da, destination_en}} from
    data/normalized/sv14_places_reconciled.csv (see reconcile_sv14_geo.py).
    Degrades to an empty dict when the file is absent — a fresh clone
    that hasn't run Stage 1c yet still builds, just without this fallback."""
    geo: dict[str, dict] = {}
    if not os.path.exists(SV14):
        return geo
    with open(SV14, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                lat = float(row["lat"])
                lon = float(row["lon"])
            except (KeyError, ValueError):
                continue
            matched_en = (row.get("matched_name_en") or "").strip() or None
            geo[row["entity_id"]] = {
                "lat":            round(lat, 5),
                "lon":            round(lon, 5),
                "country_da":     country_for(lat, lon),
                "destination_en": matched_en,
            }
    return geo


def load_place_register() -> dict[str, dict]:
    """Returns {entity_id: {category, country, lat, lon, visit}} from
    data/normalized/places.csv (see scripts/normalization/place_register.py).
    Degrades to an empty dict when the file is absent (Stage 1a has not
    run yet), same pattern as load_sv14_reconciled() above.

    `category` is the English vocabulary (City/Property/…/Fictional
    place; UI templates translate it for display) and `country` is the
    workbook's RAW Danish country — more granular than the bounding-box
    gazetteer (England and Skotland stay distinct, not folded into one
    "Storbritannien") — see main()'s precedence note."""
    reg: dict[str, dict] = {}
    if not os.path.exists(PLACES_CSV):
        return reg
    with open(PLACES_CSV, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                lat, lon = float(row["lat"]), float(row["lon"])
            except (KeyError, ValueError):
                lat = lon = None
            reg[row["entity_id"]] = {
                "category": row.get("category") or None,
                "country":  row.get("country") or None,
                "lat":      round(lat, 5) if lat is not None else None,
                "lon":      round(lon, 5) if lon is not None else None,
                "visit":    row.get("visit_status") or None,
            }
    return reg


# Register cross-references: "Venedig, se: Venezia." / "Tivoli (...), se Sagregistret."
SEE_RE = re.compile(r"^(?P<from>.+?),?\s+se:?\s+(?P<to>.+?)\.?\s*$")


def resolve_see_refs(generated: dict[str, dict]) -> None:
    """Add rec["see"] = <rid of the main entry> to every cross-reference
    place whose target is found in the register. Target match: exact label,
    else the single entry whose label starts with "<target> (" / "<target>,".
    Unresolvable targets (e.g. "se Sagregistret") get no `see` field."""
    by_label: dict[str, list[str]] = {}
    for rid, rec in generated.items():
        by_label.setdefault(rec["label"], []).append(rid)
    parsed = {rid: SEE_RE.match(rec["label"]) for rid, rec in generated.items()}
    parsed = {rid: m for rid, m in parsed.items() if m}

    def find(target: str) -> str | None:
        hits = [r for r in by_label.get(target, []) if r not in parsed]
        if not hits:
            hits = [rid for rid, rec in generated.items() if rid not in parsed
                    and rec["label"].startswith((target + " (", target + ","))]
        return hits[0] if len(hits) == 1 else None

    n = 0
    for rid, m in parsed.items():
        t = find(m.group("to"))
        if t:
            generated[rid]["see"] = t
            n += 1
    print(f"  {n:,} of {len(parsed):,} 'se:' cross-references resolved to a main entry")


def load_page_years() -> dict[tuple[str, str], set[int]]:
    """(vol, page) -> {year, ...} from the transcribed diary (diary.csv)."""
    out: dict[tuple[str, str], set[int]] = {}
    with open(DIARY, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            y = (r.get("year") or "").strip()
            if y.isdigit():
                out.setdefault((r["vol"], r["page"]), set()).add(int(y))
    return out


def main() -> None:
    if not os.path.exists(ENTITIES):
        sys.exit(f"Missing {ENTITIES} — run scripts/normalization/hca_xlsx_to_csv.py first.")

    print(f"Loading {os.path.relpath(ENTITIES, ROOT)}…")
    places = []
    with open(ENTITIES, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["entity_type"] == "place":
                places.append(r)
    print(f"  {len(places):,} places")

    ref_count: Counter[str] = Counter()
    # Years in which each place is mentioned in the diaries, for the
    # "Omtaleår" facet on places.html. A diary page can span a year change,
    # so a page contributes every distinct year found on its rows.
    page_years = load_page_years()
    mention_years: dict[str, set[int]] = {}
    if os.path.exists(REFS):
        with _diary_scope.open_refs(REFS) as f:
            for r in csv.DictReader(f):
                ref_count[r["entity_id"]] += 1
                yrs = page_years.get((r["vol"], r["page"]))
                if yrs:
                    mention_years.setdefault(r["entity_id"], set()).update(yrs)
        print(f"  reference counts loaded for {len(ref_count):,} entities "
              f"({len(mention_years):,} with dated mentions)")

    geo = load_rejser_geocodes()
    print(f"  rejser gazetteer: {len(geo):,} place-name keys")

    sv14_geo = load_sv14_reconciled()
    print(f"  SV14 reconciliation: {len(sv14_geo):,} entity-id matches")

    register = load_place_register()
    print(f"  place register (places.csv): {len(register):,} places, "
          f"{sum(1 for r in register.values() if r['lat'] is not None):,} with coordinates")
    if not register:
        print("  [!] data/normalized/places.csv missing — run hca_xlsx_to_csv.py; "
              "category/country/coordinates will be empty")

    # Emit one entry per place, INCLUDING IDs that mockup/place.html
    # also curates. place.html's `ALL_PLACES = Object.assign({},
    # PLACES_EXTRA, PLACES)` still gives the hand-curated entries
    # precedence; emitting the extras for them too lets EntityRefs
    # (mockup/js/entity-refs.js) see the full register from any page.
    generated: dict[str, dict] = {}
    rejser_hits = 0
    sv14_hits = 0
    herred_amt_hits = 0
    register_geo_hits = 0
    register_country_hits = 0
    for r in places:
        rid = r["entity_id"]
        label = (r.get("label") or "").strip()
        rec = {
            "label":       label,
            "description": (r.get("description") or "").strip() or None,
            "refs":        ref_count.get(rid, 0),
            "category":    (register.get(rid) or {}).get("category"),
        }
        visit = (register.get(rid) or {}).get("visit")
        if visit:
            rec["visit"] = visit
        if rid in mention_years:
            rec["my"] = sorted(mention_years[rid])
        g = geo.get(label.casefold())
        if g:
            rec.update(g)
            rec["geo_source"] = "rejser"
            rejser_hits += 1
        elif rid in sv14_geo:
            rec.update(sv14_geo[rid])
            rec["geo_source"] = "sv14"
            sv14_hits += 1
        else:
            m = HERRED_AMT_RE.search(label)
            if m:
                rec["country_da"] = "Danmark"
                rec["geo_source"] = "herred_amt"
                rec["herred"] = m.group("herred")
                rec["amt"] = m.group("amt")
                herred_amt_hits += 1

        # The place register is the base: its coordinates replace whatever
        # the fallback sources above set (rejser/sv14 are kept only where the
        # register has none), and its Danish country REPLACES the bounding-box
        # gazetteer's — it is curated and more granular (England/Skotland stay
        # distinct; the COUNTRIES boxes would have folded both into one
        # "Storbritannien"). Rejser/SV14's destination_en is kept either way.
        reg = register.get(rid) or {}
        if reg.get("lat") is not None:
            rec["lat"], rec["lon"] = reg["lat"], reg["lon"]
            rec["geo_source"] = "register"
            register_geo_hits += 1
        if reg.get("country"):
            rec["country_da"] = reg["country"]
            register_country_hits += 1
        generated[rid] = rec

    resolve_see_refs(generated)

    with_coords = sum(1 for g in generated.values() if g.get("lat") is not None)
    print(f"  generated {len(generated):,} entries ({with_coords:,} with coordinates: "
          f"{register_geo_hits:,} from the place register; of the fallbacks "
          f"{rejser_hits:,} rejser / {sv14_hits:,} SV14 matched, "
          f"{herred_amt_hits:,} herred/amt; {register_country_hits:,} with a register country_da)")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// Auto-generated by scripts/build_mockup/build_places_extra.py — do not hand-edit.\n")
        f.write("// One entry per place in STED-REGISTER (LocationID base, LOC… ids). Category,\n")
        f.write("// country, visited/mentioned status and coordinates come from data/normalized/\n")
        f.write("// places.csv (data/HCA_Steder_GÆLDENDE_*.xlsx via hca_xlsx_to_csv.py); where the\n")
        f.write("// workbook has no coordinates, rejser.tsv (hcax.dk), sv14_places_reconciled.csv and\n")
        f.write("// HERRED_AMT_RE (country_da only) fill in. geo_source records which supplied the\n")
        f.write("// coordinates: register | rejser | sv14 | herred_amt.\n")
        f.write("// `category` (City/Property/Region/Point of interest (POI)/River/Mountain/Island/\n")
        f.write("// Lake/Country/Sea/Church/Continent/Fictional place, or null) is the raw English\n")
        f.write("// value; UI templates translate it for display, they don't get it pre-translated.\n")
        f.write("// `visit` = Besøgt | Omtalt (visited / only mentioned).\n")
        f.write("// The hand-curated PLACES object in place.html takes precedence (ALL_PLACES merge).\n")
        f.write("// `my` = sorted list of years in which the place is mentioned on a transcribed diary\n")
        f.write("// page (from diary.csv); absent when no mention is dated. Powers \"Omtaleår\" on places.html.\n")
        f.write("const PLACES_EXTRA = ")
        f.write(json.dumps(generated, ensure_ascii=False, separators=(",", ":")))
        f.write(";\n")
    print(f"  wrote {os.path.relpath(OUT, ROOT)}  "
          f"({os.path.getsize(OUT)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
