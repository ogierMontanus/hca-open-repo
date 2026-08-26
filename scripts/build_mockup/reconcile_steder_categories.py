#!/usr/bin/env python3
"""
reconcile_steder_categories.py
---------------------------------
Joins the human-verified `Category` column from
raw/Steder_i_dagboegerne_verificeret_udfyldt VER 1.0.xlsx (sheet
RawLoc) onto data/normalized/entities.csv's STED-REGISTER places, by
exact case-insensitive RegistryTitle <-> label match — see
docs/data-model/steder-verificeret-category-mapping.md §1 for the
95.8% match-rate finding this reproduces (2,332/2,433 unique titles).

Only entities.csv rows with a name match AND a non-empty Category get
written -- unmatched rows (spelling/punctuation variants, mostly) and
blank-Category rows are logged but not guessed at, same propose-what-
you-can-verify discipline as every other *_reconciled.csv in this
pipeline.

Output: data/normalized/steder_verified_categories.csv (entity_id,
label, category) -- read by build_places_extra.py (kept stdlib-only
itself; this script is the one place openpyxl is needed).

Run before build_places_extra.py:
  python scripts/build_mockup/reconcile_steder_categories.py
"""

import csv
import os
import sys

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl required:  pip install openpyxl")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
XLSX = os.path.join(ROOT, "raw", "Steder_i_dagboegerne_verificeret_udfyldt VER 1.0.xlsx")
ENTITIES = os.path.join(ROOT, "data", "normalized", "entities.csv")
OUT = os.path.join(ROOT, "data", "normalized", "steder_verified_categories.csv")


def main():
    if not os.path.exists(XLSX):
        sys.exit(f"Missing {XLSX}")
    if not os.path.exists(ENTITIES):
        sys.exit(f"Missing {ENTITIES} — run scripts/normalization/hca_xlsx_to_csv.py first.")

    print(f"Loading {os.path.relpath(ENTITIES, ROOT)}…")
    places = []
    with open(ENTITIES, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["entity_type"] == "place":
                places.append(r)
    by_casefold = {}
    for r in places:
        key = (r.get("label") or "").strip().casefold()
        if key:
            by_casefold.setdefault(key, []).append(r)
    print(f"  {len(places):,} places, {len(by_casefold):,} distinct labels")

    print(f"Loading {os.path.relpath(XLSX, ROOT)}…")
    wb = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)
    ws = wb["RawLoc"]
    rows = ws.iter_rows(values_only=True)
    header = next(rows)
    idx = {name: i for i, name in enumerate(header)}

    matched, no_category, no_match, ambiguous = [], 0, [], []
    seen_titles = set()
    for r in rows:
        title = (r[idx["RegistryTitle"]] or "").strip()
        category = (r[idx["Category"]] or "").strip()
        if not title or title.casefold() in seen_titles:
            continue
        seen_titles.add(title.casefold())
        if not category or category.lower() == "none":
            no_category += 1
            continue
        candidates = by_casefold.get(title.casefold())
        if not candidates:
            no_match.append(title)
            continue
        if len(candidates) > 1:
            ambiguous.append(title)
            continue
        matched.append({
            "entity_id": candidates[0]["entity_id"],
            "label": candidates[0]["label"],
            "category": category,
        })

    print(f"  {len(matched):,} matched with a category")
    print(f"  {no_category:,} rows with a blank/None category (skipped)")
    print(f"  {len(no_match):,} rows with no matching register label (skipped)")
    print(f"  {len(ambiguous):,} rows matching more than one register label (skipped)")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["entity_id", "label", "category"])
        w.writeheader()
        w.writerows(matched)
    print(f"wrote {os.path.relpath(OUT, ROOT)}  ({len(matched):,} rows)")


if __name__ == "__main__":
    main()
