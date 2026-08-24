#!/usr/bin/env python3
"""
match_collin_works_to_register.py
------------------------------------
Maps data/curated/collin_letters_work_index.csv against this project's
own WORK-REGISTER (mockup/data/works-extra.js), matching on normalized
title -- works-extra.js titles already embed a publication year in the
same "(YYYY)" convention as the printed edition (e.g. "Aus Herz und
Welt (1860)"), so title match doubles as a year check for most entries.

Run from the repo root:
  python scripts/correspondence/match_collin_works_to_register.py
"""

import csv
import json
import os
import re
import unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COLLIN_CSV = os.path.join(ROOT, "data", "curated", "collin_letters_work_index.csv")
WORKS_JS = os.path.join(ROOT, "mockup", "data", "works-extra.js")
OUT_CSV = os.path.join(ROOT, "data", "curated", "collin_letters_work_match.csv")


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


def normalize_title(s):
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def strip_year(s):
    return re.sub(r"\s*\(\d{4}[^)]*\)\s*", " ", s or "").strip()


def main():
    print("Loading works-extra.js …")
    works = load_json_object(WORKS_JS)
    print(f"  {len(works)} register works loaded")

    by_title = {}          # full title (year embedded), normalized
    by_title_noyear = {}   # title with any "(YYYY...)" stripped, normalized
    for reg_id, w in works.items():
        title = w.get("title")
        key = normalize_title(title)
        if key:
            by_title.setdefault(key, []).append((reg_id, title, w.get("h3")))
        key2 = normalize_title(strip_year(title))
        if key2:
            by_title_noyear.setdefault(key2, []).append((reg_id, title, w.get("h3")))

    with open(COLLIN_CSV, encoding="utf-8") as f:
        collin_rows = list(csv.DictReader(f))
    print(f"  {len(collin_rows)} Collin work entries")

    out_rows = []
    tiers = {}
    for row in collin_rows:
        title, year = row["title"], row["year"]
        matches = []
        matched_on = ""
        if year:
            combo_key = normalize_title(f"{title} ({year})")
            matches = by_title.get(combo_key, [])
            matched_on = "title+year" if matches else ""
        if not matches:
            key2 = normalize_title(title)
            matches = by_title_noyear.get(key2, [])
            matched_on = "title_only" if matches else matched_on
        tier = ("exact" if len(matches) == 1 else "ambiguous" if len(matches) > 1 else "none")
        tiers[tier] = tiers.get(tier, 0) + 1
        out_rows.append({
            "collin_title": row["title"],
            "collin_year": row["year"],
            "collin_category": row["category"],
            "match_tier": tier,
            "match_count": len(matches),
            "matched_on": matched_on,
            "match_reg_ids": ";".join(m[0] for m in matches),
            "match_titles": " | ".join(m[1] for m in matches),
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
