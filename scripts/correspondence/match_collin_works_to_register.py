#!/usr/bin/env python3
"""
match_collin_works_to_register.py
------------------------------------
Maps data/curated/collin_letters_work_index.csv against this project's
own WORK-REGISTER (mockup/data/works-extra.js), matching on normalized
title -- works-extra.js titles already embed a publication year in the
same "(YYYY)" convention as the printed edition (e.g. "Aus Herz und
Welt (1860)"), so title match doubles as a year check for most entries.

Rows the extractor already tagged issue_type (omnibus_collection,
serial_installment, possible_fragment) or see_also (a redirect) are NOT
run through matching at all -- they have no 1:1 target on the site by
construction, not because matching failed. Their tier is set directly
from that tag so they stay visibly distinct from a genuine "none" miss,
ready for a later human pass rather than looking like unexplained gaps.

Match attempts, in order, for everything else:
  1. exact title+year
  2. exact title only (year stripped from both sides)
  3. title with a trailing non-year parenthetical also stripped from the
     SITE side (e.g. "Ole Lukøie (Eventyr)" -> "Ole Lukøie") -- catches
     genre-disambiguated site titles the printed index cites bare.
     Multiple site works collapsing to the same stripped key (a title
     shared by two different works, e.g. a tale AND a play of the same
     name) are flagged "ambiguous_genre", never auto-picked.
  4. fuzzy (difflib, cutoff 0.88) against the title-only index -- catches
     spelling-convention drift (e.g. "De røde Sko" vs. site's "De røde
     Skoe"). Flagged with its own tier so a fuzzy hit is never silently
     indistinguishable from an exact one.

Run from the repo root:
  python scripts/correspondence/match_collin_works_to_register.py
"""

import csv
import difflib
import json
import os
import re
import unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COLLIN_CSV = os.path.join(ROOT, "data", "curated", "collin_letters_work_index.csv")
WORKS_JS = os.path.join(ROOT, "mockup", "data", "works-extra.js")
OUT_CSV = os.path.join(ROOT, "data", "curated", "collin_letters_work_match.csv")

FUZZY_CUTOFF = 0.88


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


def strip_trailing_paren(s):
    """Strip ONE trailing non-year parenthetical, e.g. "Ole Lukøie
    (Eventyr)" -> "Ole Lukøie". Only trailing (end-of-string) parens --
    never touches a parenthetical mid-title, which is more likely to be
    load-bearing (a place, a qualifier) than a bare genre tag."""
    return re.sub(r"\s*\([^)0-9][^)]*\)\s*$", "", s or "").strip()


def build_indexes(works):
    by_title, by_title_noyear, by_title_genre_stripped = {}, {}, {}
    for reg_id, w in works.items():
        title = w.get("title")
        key = normalize_title(title)
        if key:
            by_title.setdefault(key, []).append((reg_id, title))
        no_year = strip_year(title)
        key2 = normalize_title(no_year)
        if key2:
            by_title_noyear.setdefault(key2, []).append((reg_id, title))
        key3 = normalize_title(strip_trailing_paren(no_year))
        if key3:
            by_title_genre_stripped.setdefault(key3, []).append((reg_id, title))
    return by_title, by_title_noyear, by_title_genre_stripped


def main():
    print("Loading works-extra.js …")
    works = load_json_object(WORKS_JS)
    print(f"  {len(works)} register works loaded")
    by_title, by_title_noyear, by_title_genre_stripped = build_indexes(works)
    noyear_keys = list(by_title_noyear.keys())

    with open(COLLIN_CSV, encoding="utf-8") as f:
        collin_rows = list(csv.DictReader(f))
    print(f"  {len(collin_rows)} Collin work entries")

    out_rows = []
    tiers = {}
    for row in collin_rows:
        title, year = row["title"], row["year"]
        issue_type = row.get("issue_type", "")
        see_also = row.get("see_also", "")

        if see_also:
            tier, matches, matched_on = "redirect", [], ""
        elif issue_type:
            tier, matches, matched_on = issue_type, [], ""
        else:
            matches, matched_on = [], ""
            if year:
                matches = by_title.get(normalize_title(f"{title} ({year})"), [])
                matched_on = "title+year" if matches else ""
            if not matches:
                key2 = normalize_title(title)
                matches = by_title_noyear.get(key2, [])
                matched_on = "title_only" if matches else matched_on
            if not matches:
                key3 = normalize_title(strip_trailing_paren(title))
                matches = by_title_genre_stripped.get(key3, [])
                matched_on = "genre_stripped" if matches else matched_on
                if len(matches) > 1:
                    tier = "ambiguous_genre"
            if not matches:
                key2 = normalize_title(title)
                close = difflib.get_close_matches(key2, noyear_keys, n=2, cutoff=FUZZY_CUTOFF)
                if len(close) == 1:
                    matches = by_title_noyear[close[0]]
                    matched_on = "fuzzy"

            if matched_on == "genre_stripped" and len(matches) > 1:
                tier = "ambiguous_genre"
            elif matched_on == "fuzzy":
                tier = "fuzzy" if len(matches) == 1 else "ambiguous"
            else:
                tier = "exact" if len(matches) == 1 else "ambiguous" if len(matches) > 1 else "none"

        tiers[tier] = tiers.get(tier, 0) + 1
        out_rows.append({
            "collin_title": row["title"],
            "collin_year": row["year"],
            "collin_category": row["category"],
            "see_also": see_also,
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
