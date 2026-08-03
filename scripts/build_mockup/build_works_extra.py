#!/usr/bin/env python3
"""
build_works_extra.py
--------------------
Generates mockup/data/works-extra.js — a `WORKS_EXTRA` JS object with
one entry per work in data/normalized/entities.csv. The hand-curated
`WORKS` object inside mockup/work.html keeps precedence; WORKS_EXTRA
fills every other gap so any ?reg=… link resolves to real metadata
instead of an "Ukendt værk" page.

Run after `scripts/normalization/hca_xlsx_to_csv.py`. Stdlib only.
"""

import csv
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENTITIES = os.path.join(ROOT, "data", "normalized", "entities.csv")
REFS = os.path.join(ROOT, "data", "normalized", "references.csv")
LANGS = os.path.join(ROOT, "data", "normalized", "work_languages.csv")
OUT = os.path.join(ROOT, "mockup", "data", "works-extra.js")

PUB_PAREN_RE = re.compile(r"\(([^()]+?)\)")
YEAR_RE = re.compile(r"\b(1[5-9]\d{2})\b")

# Strip a "se:" / "Se ogsaa:" redirect tail and surrounding punctuation so a
# cross-reference target ("Krøblingen") can be matched against the head of a
# fuller entry label ("Krøblingen (Eventyrbogen)").
SEE_TAIL_RE = re.compile(r"[Ss]e\s+og[s]?aa\s*:|\bse\s*:")
PUNCT_RE = re.compile(r"[*»«\"'.,!?;:\-()\[\]]")
WS_RE = re.compile(r"\s+")


def norm_label(s):
    s = (s or "").replace("\n", " ").lower()
    s = PUNCT_RE.sub(" ", s)
    return WS_RE.sub(" ", s).strip()


def head_label(label):
    return norm_label(SEE_TAIL_RE.split((label or "").replace("\n", " "))[0])


def wing_for(h2, h3):
    h2u = (h2 or "").upper()
    h3l = (h3 or "").lower()
    if "BILLEDKUNST" in h2u or "malerier" in h3l or "skulptur" in h3l or "museer" in h3l:
        return ("billedkunst.html", "Billedkunst")
    if ("MUSIK" in h2u or "opera" in h3l or "ballet" in h3l
            or "vokal" in h3l or "skuespil" in h3l):
        return ("teater-musik.html", "Teater & Musik")
    return ("bibliotek.html", "Bibliotek")


def parse_year(label):
    for m in PUB_PAREN_RE.finditer(label):
        ym = YEAR_RE.search(m.group(1))
        if ym:
            return ym.group(1)
    return None


def author_from(genre_h2, person_derived):
    if person_derived and person_derived.strip():
        return person_derived.strip()
    if genre_h2 and genre_h2.strip() and genre_h2.upper() not in ("BILLEDKUNST", "MUSIK"):
        return genre_h2.strip()
    return None


def load_languages():
    """{entity_id: (lang, method)} from detect_work_language.py. Empty when
    that stage hasn't run — `lang` then stays None exactly as before."""
    out = {}
    if not os.path.exists(LANGS):
        return out
    with open(LANGS, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out[r["entity_id"]] = (r["lang"], r["method"])
    return out


def main():
    if not os.path.exists(ENTITIES):
        sys.exit(f"Missing {ENTITIES} — run scripts/normalization/hca_xlsx_to_csv.py first.")

    print(f"Loading {os.path.relpath(ENTITIES, ROOT)}…")
    with open(ENTITIES, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["entity_type"] == "work"]
    print(f"  {len(rows):,} works")

    ref_count = defaultdict(int)
    if os.path.exists(REFS):
        with open(REFS, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                ref_count[r["entity_id"]] += 1
        print(f"  reference counts loaded for {len(ref_count):,} entities")

    work_langs = load_languages()
    if work_langs:
        print(f"  languages loaded for {len(work_langs):,} works")
    else:
        print("  no work_languages.csv — lang stays null "
              "(run scripts/build_mockup/detect_work_language.py)")

    # Index work labels for resolving `see` / `see_also` cross-references to
    # real register IDs. Most targets are the head term of a fuller label
    # (e.g. "Krøblingen" -> "Krøblingen (Eventyrbogen)"), so we keep an exact
    # head-label map plus a (head, rid) list for whole-word prefix fallback.
    head_exact = defaultdict(list)
    head_list = []
    for r in rows:
        h = head_label(r["label"])
        if h:
            head_exact[h].append(r["entity_id"])
            head_list.append((h, r["entity_id"]))

    def resolve_ref(target, self_id):
        t = norm_label(target)
        if not t:
            return None
        cands = [rid for rid in head_exact.get(t, []) if rid != self_id]
        if cands:
            return cands[0]
        # Whole-word prefix: shortest label that starts with the target wins,
        # so "Foraarssang" picks the bare poem over a longer derived title.
        prefixed = [(len(h), rid) for h, rid in head_list
                    if rid != self_id and (h == t or h.startswith(t + " "))]
        if prefixed:
            return min(prefixed)[1]
        return None

    def refs_field(raw, self_id):
        raw = (raw or "").strip()
        if not raw:
            return []
        return [{"label": raw, "rid": resolve_ref(raw, self_id)}]

    def best_year(r):
        # Prefer the normalised derived fields over the label regex.
        dd = (r.get("date_derived") or "").strip()
        if dd:
            ym = re.match(r"(1[5-9]\d{2})", dd)
            if ym:
                return ym.group(1)
        yd = (r.get("year_derived") or "").strip()
        if yd:
            ym = YEAR_RE.search(yd)
            if ym:
                return ym.group(1)
        return parse_year(r["label"])

    # Generate one entry per work, INCLUDING IDs that mockup/work.html
    # also curates. work.html's `ALL_WORKS = Object.assign({}, WORKS_EXTRA,
    # WORKS)` still gives the hand-curated entries precedence; emitting the
    # extras for them too makes EntityRefs (mockup/js/entity-refs.js) see
    # the full catalogue from the other detail pages, where the curated
    # `WORKS` object isn't in scope.
    generated = {}
    for r in rows:
        rid = r["entity_id"]
        h2 = (r.get("genre_h2") or "").strip()
        h3 = (r.get("form_h3") or "").strip()
        wing, wing_label = wing_for(h2, h3)
        generated[rid] = {
            "title": r["label"].strip(),
            "h2": h2 or "ANDRE FORFATTERE",
            "h3": h3 or "—",
            "wing": wing,
            "wingLabel": wing_label,
            "author": author_from(h2, r.get("person_derived", "")),
            # Derived, not curated — langMethod carries the provenance so the
            # UI can say so. See detect_work_language.py.
            "lang": work_langs.get(rid, (None, None))[0],
            "langMethod": work_langs.get(rid, (None, None))[1],
            "refs": ref_count.get(rid, 0),
            "year": best_year(r),
            "date": (r.get("date_derived") or "").strip() or None,
            "see": refs_field(r.get("see"), rid),
            "seeAlso": refs_field(r.get("see_also"), rid),
            "diary": [],
            "related": [],
            "coPlaces": [],
            "coWorks": [],
        }

    print(f"  generated {len(generated)} entries across all {len(rows)} works")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// Auto-generated by scripts/build_mockup/build_works_extra.py — do not hand-edit.\n")
        f.write("// Provides minimal placeholder entries so every ?reg=… link from category\n")
        f.write("// pages resolves to real metadata. Hand-curated WORKS in work.html takes\n")
        f.write("// precedence on lookup (see ALL_WORKS merge at the bottom of work.html).\n")
        f.write("const WORKS_EXTRA = ")
        f.write(json.dumps(generated, ensure_ascii=False, indent=2))
        f.write(";\n")
    print(f"  wrote {os.path.relpath(OUT, ROOT)}  "
          f"({os.path.getsize(OUT):,} bytes)")


if __name__ == "__main__":
    main()
