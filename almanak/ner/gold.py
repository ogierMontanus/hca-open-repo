#!/usr/bin/env python3
"""
gold.py — indlæs håndannoteringen (overlap-stikprøven, §3.9–3.10) og læg dens spans ind i de
koordinater, de automatiske metoder arbejder i.

  load_entries()        ENTRIES fra annoteringssiden: {post_id: {text, date, src, block, ...}}
  load_gold()           Sørens spans (liste af dicts) fra eksportfilen
  diary_day_pages()     dagbogsdag -> [(vol, page, row_start_in_page_raw, row_raw)] i filens rækkefølge
  gold_to_page_raw()    dagbogsspan (offset i dagsteksten) -> (vol, page, start, end) i sidens rå tekst

Dagsteksten på annoteringssiden er `TextView("\\n".join(rækker)).text` — det kontrolleres.
"""
from __future__ import annotations

import collections
import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "parsers"))
import name_matching as nm  # noqa: E402

PAGE_HTML = REPO / "almanak" / "annotation" / "out" / "overlap-annotering.html"
GOLD_JSON = REPO / "almanak" / "annotation" / "Opmærkning til Holger.json"
DIARY = REPO / "data" / "normalized" / "diary.csv"


def load_entries(html=PAGE_HTML):
    h = Path(html).read_text(encoding="utf-8")
    return {e["id"]: e for e in json.loads(re.search(r"const ENTRIES = (\[.*?\]);\n", h, re.S).group(1))}


def load_gold(path=GOLD_JSON):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))["annotations"]


def diary_rows():
    with open(DIARY, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def page_texts(rows):
    """{(vol, page): rå sidetekst} — rækkerne samlet med \\n som i ner_page_grounding.py."""
    parts = collections.defaultdict(list)
    for r in rows:
        parts[(r["vol"], r["page"])].append(r["text"])
    return {k: "\n".join(v) for k, v in parts.items()}


def diary_day_pages(rows, dates):
    """{dato: [(vol, page, row_start_in_page_raw, row_text)]}."""
    pos = collections.defaultdict(int)
    out = collections.defaultdict(list)
    for r in rows:
        k = (r["vol"], r["page"])
        if r["date"] in dates:
            out[r["date"]].append((r["vol"], r["page"], pos[k], r["text"]))
        pos[k] += len(r["text"]) + 1
    return out


class DayMap:
    """Dagstekst (TextView over dagens rækker) med kort til (vol, page, rå offset)."""

    def __init__(self, parts):
        raw, self.segs = "", []
        for vol, page, row_start, text in parts:
            if raw:
                raw += "\n"
            self.segs.append((len(raw), len(raw) + len(text), vol, page, row_start))
            raw += text
        self.view = nm.TextView(raw)

    def to_page(self, s, e):
        rs, re_ = self.view.raw_span(s, e)
        for a, b, vol, page, row_start in self.segs:
            if a <= rs < b + 1:
                return vol, page, row_start + (rs - a), row_start + (re_ - a)
        raise ValueError((s, e))
