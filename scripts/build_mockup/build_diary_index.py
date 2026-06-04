#!/usr/bin/env python3
"""
Build compact JS index files that wire the register pages to diary pages.

The mockup is opened from the file:// protocol (see CLAUDE.md, the CARTO
tile note), where fetch() of JSON is blocked by the browser. So — exactly
like mockup/data/works-extra.js — this emits *.js files that define global
constants loaded with a plain <script> tag.

Reads:
  data/normalized/references.csv  — entity occurrences per diary page
  data/normalized/diary.csv       — transcribed text (vols VI + VII): dates
  data/normalized/entities.csv    — entity type + label

Writes (gitignored — generated locally, like mockup/diary-pages/):
  mockup/data/diary-index.js  — const DIARY_INDEX = [ {h,v,p,d,y,pl,c}, ... ]
                                one row per diary page → powers diaries.html
  mockup/data/diary-refs.js   — const DIARY_META = { pag: {v,p,d,y,pl}, ... }
                                const DIARY_REFS = { regId: {n, e:[pag,...]}, }
                                reverse index → powers the "Dagbogsreferencer"
                                section on place.html / person.html / work.html

Run from the repo root:
  python3 scripts/build_mockup/build_diary_index.py
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REFS_CSV  = REPO_ROOT / "data" / "normalized" / "references.csv"
DIARY_CSV = REPO_ROOT / "data" / "normalized" / "diary.csv"
ENTS_CSV  = REPO_ROOT / "data" / "normalized" / "entities.csv"
OUT_DIR   = REPO_ROOT / "mockup" / "data"

# Max diary pages stored per entity. The full count is kept in `.n` so the UI
# can show "viser N af M". Caps the few huge entities (e.g. Eventyr ~1500).
REFS_CAP = 60

VOL_NUM = {"I":1,"II":2,"III":3,"IV":4,"V":5,"VI":6,
           "VII":7,"VIII":8,"IX":9,"X":10,"XI":11}

# Entity-type → chip class hint used by the front-end renderers.
TYPE_CHIP = {"person": "person", "place": "place", "work": "work"}


def pid(vol: str, page: str) -> str:
    vn = VOL_NUM.get(vol, 0)
    try:
        pn = int(page)
    except ValueError:
        pn = 0
    return f"Pag{vn:02d}{pn:04d}"


def vp_sort_key(vp):
    vol, page = vp
    return (VOL_NUM.get(vol, 99), int(page) if str(page).isdigit() else 0)


def load_entities():
    ents = {}
    with ENTS_CSV.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ents[r["entity_id"]] = (r["entity_type"], r["label"])
    return ents


def load_dates():
    """vol+page → (date, year) from the transcribed vols (VI + VII only)."""
    dates = {}
    with DIARY_CSV.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (r["vol"], r["page"])
            d = r.get("date", "")
            y = r.get("year", "")
            # First dated row on the page wins; prefer a fully-specified date.
            if key not in dates or ("XX" in dates[key][0] and "XX" not in d):
                dates[key] = (d, y)
    return dates


def short_date(d: str) -> str:
    """1866-01-30 → 30-01-1866 ; drop XX placeholders gracefully."""
    if not d:
        return ""
    parts = d.split("-")
    if len(parts) == 3:
        y, m, day = parts
        if "XX" in day and "XX" in m:
            return y
        if "XX" in day:
            return f"{m}-{y}"
        return f"{day}-{m}-{y}"
    return d


def main():
    print("Loading…")
    ents  = load_entities()
    dates = load_dates()

    # Per page: ordered, de-duplicated entity ids. Per entity: pages.
    page_ents   = defaultdict(list)   # pag -> [entity_id]  (seq order)
    page_volpg  = {}                  # pag -> (vol, page)
    ent_pages   = defaultdict(list)   # entity_id -> [pag]  (vol/page order)

    rows = []
    with REFS_CSV.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r["vol"] or not r["page"]:
                continue
            rows.append(r)

    # Order rows by (vol, page, seq) so generated lists are stable + readable.
    def row_key(r):
        try:
            seq = int(r["seq"])
        except (ValueError, KeyError):
            seq = 0
        return (*vp_sort_key((r["vol"], r["page"])), seq)
    rows.sort(key=row_key)

    seen_on_page = defaultdict(set)
    ent_seen     = defaultdict(set)
    for r in rows:
        p = pid(r["vol"], r["page"])
        page_volpg[p] = (r["vol"], r["page"])
        eid = r["entity_id"]
        if eid not in seen_on_page[p]:
            seen_on_page[p].add(eid)
            page_ents[p].append(eid)
        if p not in ent_seen[eid]:
            ent_seen[eid].add(p)
            ent_pages[eid].append(p)

    all_pages = sorted(page_volpg.keys(), key=lambda p: vp_sort_key(page_volpg[p]))
    print(f"  {len(all_pages)} diary pages · {len(ent_pages)} entities with refs")

    # --- DIARY_META: pag -> {v,p,d,y,pl} ----------------------------------
    meta = {}
    page_place_label = {}
    for p in all_pages:
        vol, page = page_volpg[p]
        d, y = dates.get((vol, page), ("", ""))
        # Place label = first place entity referenced on the page.
        pl = ""
        for eid in page_ents[p]:
            t, lab = ents.get(eid, ("", ""))
            if t == "place":
                pl = lab
                break
        page_place_label[p] = pl
        m = {"v": vol, "p": page}
        sd = short_date(d)
        if sd:
            m["d"] = sd
        if y:
            m["y"] = y
        if pl:
            m["pl"] = pl
        meta[p] = m

    # --- DIARY_INDEX: one row per page, with up to 3 chips -----------------
    index = []
    for p in all_pages:
        chips = []
        place_done = False
        for eid in page_ents[p]:
            t, lab = ents.get(eid, ("", ""))
            if not lab:
                continue
            if t == "place":
                if place_done:
                    continue
                place_done = True
            chips.append({"t": TYPE_CHIP.get(t, "work"), "l": lab, "r": eid})
            if len(chips) >= 3:
                break
        row = dict(meta[p])
        row["h"] = p
        row["c"] = chips
        index.append(row)

    # --- DIARY_REFS: entity_id -> {n: total, e: [pag,...] capped} ----------
    refs = {}
    for eid, pages in ent_pages.items():
        ordered = sorted(pages, key=lambda p: vp_sort_key(page_volpg[p]))
        refs[eid] = {"n": len(ordered), "e": ordered[:REFS_CAP]}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    header = ("// Auto-generated by scripts/build_mockup/build_diary_index.py "
              "— do not hand-edit.\n"
              "// Loaded via <script> tag (file://-safe, mirrors works-extra.js).\n"
              "// Diary page bodies live in mockup/diary-pages/ (also generated).\n")

    idx_js = OUT_DIR / "diary-index.js"
    idx_js.write_text(
        header
        + "const DIARY_INDEX = "
        + json.dumps(index, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )

    refs_js = OUT_DIR / "diary-refs.js"
    refs_js.write_text(
        header
        + "const DIARY_META = "
        + json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
        + "const DIARY_REFS = "
        + json.dumps(refs, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )

    print(f"  wrote {idx_js.relative_to(REPO_ROOT)}  "
          f"({idx_js.stat().st_size/1024:.0f} KB, {len(index)} pages)")
    print(f"  wrote {refs_js.relative_to(REPO_ROOT)}  "
          f"({refs_js.stat().st_size/1024:.0f} KB, {len(refs)} entities)")
    print("Done.")


if __name__ == "__main__":
    main()
