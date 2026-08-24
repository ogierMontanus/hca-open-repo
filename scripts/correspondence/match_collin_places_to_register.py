#!/usr/bin/env python3
"""
match_collin_places_to_register.py
-------------------------------------
Maps data/curated/collin_letters_place_index.csv (see
extract_collin_place_index.py / docs/data-model/collin-place-index.md)
against this project's own PLACE-REGISTER (mockup/data/places-extra.js),
matching on normalized place name -- places have no birth-year-like
disambiguator, so name is the only simple key available; ambiguous
same-name matches (distinct real-world places sharing a name) are
surfaced, not silently resolved.

Run from the repo root:
  python scripts/correspondence/match_collin_places_to_register.py
"""

import csv
import json
import os
import re
import unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COLLIN_CSV = os.path.join(ROOT, "data", "curated", "collin_letters_place_index.csv")
PLACES_JS = os.path.join(ROOT, "mockup", "data", "places-extra.js")
OUT_CSV = os.path.join(ROOT, "data", "curated", "collin_letters_place_match.csv")


def load_json_object(path):
    text = open(path, encoding="utf-8").read()
    start = text.index("{")
    depth, in_str, esc, end = 0, False, False, None
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': in_str = False
            continue
        if c == '"': in_str = True
        elif c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return json.loads(text[start:end])


def _base(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^A-Za-z]", "", s)
    return s.upper()


def normalize_keys(s):
    """Two candidate keys, not one: oe/ae folding is unconditionally
    applied (empirically +4/-0 exact matches on this index -- ø/ö have no
    shared NFD decomposition otherwise and would silently collide or
    vanish), but aa<->å is tried BOTH ways rather than committed to a
    single doubled form. Pre-1948 Danish orthography prints "aa" where a
    modern label has "å" (Aabenraa/Åbenrå) -- but unconditionally
    replacing å with "aa" also collapses it onto the wrong letter when a
    name instead varies by å vs ä (Håckeberga vs the register's
    Häckeberga, an unrelated OCR-adjacent variant): NFD already reduces
    both å and ä to bare "a", and doubling å to "aa" breaks that shared
    reduction for no matching gain -- measured directly against this
    index: aa-doubling alone found 0 new exact matches and broke 1
    (Håckeberga/Häckeberga); trying both forms keeps the 0 upside
    available for names that do need it while not paying that cost.
    See docs/data-model/collin-place-index.md for the numbers."""
    s = (s or "").strip()
    s = s.replace("æ", "ae").replace("Æ", "AE")
    s = s.replace("ø", "o").replace("Ø", "O")
    doubled = s.replace("å", "aa").replace("Å", "AA")
    return {_base(doubled), _base(s)}


def main():
    print("Loading places-extra.js …")
    places = load_json_object(PLACES_JS)
    print(f"  {len(places)} register places loaded")

    by_name = {}
    for reg_id, p in places.items():
        for key in normalize_keys(p.get("label")):
            if key:
                by_name.setdefault(key, []).append((reg_id, p.get("label"), p.get("country_da")))

    with open(COLLIN_CSV, encoding="utf-8") as f:
        collin_rows = list(csv.DictReader(f))
    print(f"  {len(collin_rows)} Collin place entries")

    out_rows = []
    tiers = {}
    for row in collin_rows:
        if row.get("see_also"):
            continue  # redirect rows carry no citation of their own to match
        name = row["place_name_clean"] or row["place_name_raw"]
        matches_by_id = {}
        for key in normalize_keys(name):
            for m in by_name.get(key, []):
                matches_by_id[m[0]] = m
        matches = list(matches_by_id.values())
        tier = "exact" if len(matches) == 1 else "ambiguous" if len(matches) > 1 else "none"
        tiers[tier] = tiers.get(tier, 0) + 1
        out_rows.append({
            "collin_place_name": name,
            "match_tier": tier,
            "match_count": len(matches),
            "match_reg_ids": ";".join(m[0] for m in matches),
            "match_labels": " | ".join(m[1] for m in matches),
            "match_countries": " | ".join((m[2] or "") for m in matches),
        })

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    print(f"wrote {os.path.relpath(OUT_CSV, ROOT)}  ({len(out_rows)} rows)")
    print("Tiers:", tiers)


if __name__ == "__main__":
    main()
