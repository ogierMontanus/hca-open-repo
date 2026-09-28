#!/usr/bin/env python3
"""
epub_diary_to_csv.py — build diary.csv from the XHTML page files of the
digital edition of H.C. Andersens Dagbøger I–X.

Source: the unzipped EPUB folder raw/hcadag-20240911 - Copy.epub/ (the
packed .epub is accepted too via --epub). Replaces the earlier diary-text
sources: DiaryTextLines in the V0.82/V0.92 workbooks, which only covered
vols VI + VII, and the DiaryVol*.docx files. hca_v092_to_csv.py imports
build_rows() from here, so both pipelines share one parser.

The EPUB has one XHTML file per printed page, named
hcadag{VV}_{seq}_{page}.xhtml. Only pages with an Arabic page number are
diary text — Roman-numbered pages are introductions, time lines and
manuscript descriptions. The printed page numbers match the register's
PageRef, so vol+page joins straight onto references.csv.

Inside a page:
  - an element with id="dYYYY-MM-DD" starts a dated entry
  - <header class="div1"> is a year heading, other <header>s month/other
  - <i n="N"> / <br n="N"> / <header n="N"> mark printed line numbers
  - <aside role="note"> holds the text-critical apparatus (→ notes column)
  - <figure><figcaption> and the #illusModal panel (drawings, portraits,
    manuscript facsimiles on img.kb.dk) → illustrations column: a JSON
    list of {"caption", "url"} on the page's first row

Output keeps the existing diary.csv shape — one row per entry segment per
page, text lines stamped "PPP-LL" — plus `notes` and `illustrations`.
A page without text (a full-page drawing) still gets one row.

Usage (PowerShell on Windows):
  python scripts/normalization/epub_diary_to_csv.py
  python scripts/normalization/epub_diary_to_csv.py --epub raw/hcadag-20240911.epub
  python scripts/normalization/epub_diary_to_csv.py --out data/normalized_v092/diary.csv
"""

import argparse
import csv
import html
import json
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EPUB = ROOT / "raw" / "hcadag-20240911 - Copy.epub"
DEFAULT_OUT = ROOT / "data" / "normalized" / "diary.csv"

FIELDS = ["vol", "page", "date", "month", "year", "heading", "text",
          "notes", "illustrations"]

ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]

MONTHS = ["Januar", "Februar", "Marts", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "December"]
MONTH_PREFIX = {m[:3].lower(): i + 1 for i, m in enumerate(MONTHS)}
MONTH_PREFIX["maj"] = 5
MONTH_PREFIX["okt"] = MONTH_PREFIX["oct"] = 10

PAGE_FILE = re.compile(r"(?:^|/)hcadag(\d\d)_\d+_(\d+)\.xhtml$")
MODAL_ITEM = re.compile(r'<div>([^<]*)</div>\s*<a href="([^"]+)"')
DATE_ID = re.compile(r"^d(\d{4})-(\d\d)-(\d\d)$")
BLOCKS = {"p", "header", "div", "li", "tr", "ul", "table", "figcaption"}


def _date_parts(y, m, d):
    m = m if m and m != "00" else "XX"
    d = d if d and d != "00" else "XX"
    return f"{y}-{m}-{d}"


class DateState:
    """Current date + entry heading, carried from page to page within a volume."""

    def __init__(self):
        self.date = ""
        self.heading = ""

    @property
    def year(self):
        return self.date[:4] if self.date else ""

    def from_header(self, text, is_year):
        years = re.findall(r"1[89]\d\d", text)
        if is_year and years:
            self.date = _date_parts(years[0], None, None)
            return
        word = re.sub(r"[^\wæøå]", " ", text.lower()).split()
        for w in word:
            if w[:3] in MONTH_PREFIX and self.year:
                self.date = _date_parts(self.year, f"{MONTH_PREFIX[w[:3]]:02d}", None)
                return


class PageParser(HTMLParser):
    def __init__(self, page, state):
        super().__init__(convert_charrefs=True)
        self.page = page
        self.state = state
        self.segments = []          # dicts: date, heading, lines, notes
        self.buf = []
        self.line_no = 1             # number the next flushed line gets
        self.marker_mismatch = 0
        self.skip = 0               # depth inside <figure>
        self.figures = []           # figcaption texts
        self.caption = None         # list while inside <figcaption>
        self.note = None            # list while inside <aside>
        self.in_main = False
        self.header = None          # (is_year, [text]) while inside <header>
        self.heading_capture = None  # list while capturing a leading <i>
        self.await_heading = False
        self.i_depth = 0

    # ── segments / lines ────────────────────────────────────────────────
    def _new_segment(self, heading=""):
        self._flush()
        self.segments.append({"date": self.state.date, "heading": heading,
                              "lines": [], "notes": []})

    def _seg(self):
        if not self.segments:
            self._new_segment()
        return self.segments[-1]

    def _flush(self):
        text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        self.buf = []
        if text:
            self._seg()["lines"].append((self.line_no, text))
            self.line_no += 1

    def _mark(self, n):
        try:
            n = int(str(n).strip())
        except ValueError:
            return
        if n != self.line_no:
            self.marker_mismatch += 1
            self.line_no = n

    # ── parser callbacks ────────────────────────────────────────────────
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "main":
            self.in_main = True
            return
        if not self.in_main:
            return
        if tag == "figure":
            self.skip += 1
            return
        if self.skip:
            if tag == "figcaption":
                self.caption = []
            elif tag == "br" and self.caption is not None:
                self.caption.append(" ")
            return
        if tag == "aside":
            self._flush()
            self.note = []
            return

        if tag in BLOCKS or tag == "br":
            self._flush()
        if tag == "td":
            self.buf.append(" ")

        m = DATE_ID.match(a.get("id", "") or "")
        if tag == "header":
            if m:
                self.state.date = _date_parts(*m.groups())
            self._new_segment()
            self.header = (a.get("class") == "div1", [])
        elif m:
            date = _date_parts(*m.groups())
            # The edition repeats the entry's date id on the first paragraph
            # of a page when the entry runs over from the previous page.
            if not self.segments and date == self.state.date:
                self._new_segment(self.state.heading)
            else:
                self.state.date = date
                self.state.heading = ""
                self._new_segment()
                self.await_heading = True

        if tag in ("br", "header") and a.get("n"):
            self._mark(a["n"])
        if tag == "i":
            if a.get("n") is not None:
                self._mark(a["n"])
                self.i_depth += 1
                return
            self.i_depth += 1
            if self.await_heading and not "".join(self.buf).strip():
                self.heading_capture = []
            self.await_heading = False

    def handle_endtag(self, tag):
        if not self.in_main:
            return
        if tag == "main":
            self._flush()
            self.in_main = False
            return
        if tag == "figure":
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            if tag == "figcaption" and self.caption is not None:
                txt = re.sub(r"\s+", " ", "".join(self.caption)).strip()
                if txt:
                    self.figures.append(txt)
                self.caption = None
            return
        if tag == "aside":
            if self.note is not None:
                txt = re.sub(r"\s+", " ", "".join(self.note)).strip()
                if txt:
                    self._seg()["notes"].append(txt)
            self.note = None
            return
        if tag == "i":
            self.i_depth = max(0, self.i_depth - 1)
            if self.heading_capture is not None and self.i_depth == 0:
                h = re.sub(r"\s+", " ", "".join(self.heading_capture)).strip()
                self._seg()["heading"] = self.state.heading = h
                self.heading_capture = None
            return
        if tag == "header" and self.header is not None:
            is_year, parts = self.header
            text = re.sub(r"\s+", " ", "".join(parts)).strip()
            seg = self._seg()
            seg["heading"] = self.state.heading = text
            if not seg["date"] or not DATE_ID.match("d" + seg["date"]):
                self.state.from_header(text, is_year)
                seg["date"] = self.state.date
            self.header = None
        if tag in BLOCKS:
            self._flush()
            self.await_heading = False

    def handle_data(self, data):
        if not self.in_main:
            return
        if self.skip:
            if self.caption is not None:
                self.caption.append(data)
            return
        if self.note is not None:
            self.note.append(data)
            return
        if data.strip() and self.i_depth == 0:
            self.await_heading = False
        self.buf.append(data)
        if self.header is not None:
            self.header[1].append(data)
        if self.heading_capture is not None:
            self.heading_capture.append(data)


def _month_name(date):
    m = date[5:7]
    return MONTHS[int(m) - 1] if m.isdigit() and 1 <= int(m) <= 12 else ""


def _illustrations(parser, xhtml):
    items = [{"caption": c, "url": ""} for c in parser.figures]
    if 'id="illusModal"' in xhtml:
        modal = xhtml.split('id="illusModal"', 1)[1]
        items += [{"caption": html.unescape(c).strip(), "url": u}
                  for c, u in MODAL_ITEM.findall(modal)]
    return items


def page_rows(vol, page, xhtml, state, stats):
    p = PageParser(page, state)
    p.feed(xhtml)
    p.close()
    stats["mismatch"] += p.marker_mismatch
    rows = []
    for seg in p.segments:
        if not seg["lines"]:
            if seg["notes"] and rows:
                rows[-1]["notes"] += " | " + " | ".join(seg["notes"])
            continue
        date = seg["date"]
        rows.append({
            "vol": ROMAN[vol],
            "page": str(page),
            "date": date,
            "month": _month_name(date),
            "year": date[:4],
            "heading": seg["heading"],
            "text": "\n".join(f"{page:03d}-{ln:02d}     {t}" for ln, t in seg["lines"]),
            "notes": " | ".join(seg["notes"]),
            "illustrations": "",
        })
    if not rows:
        rows.append({"vol": ROMAN[vol], "page": str(page), "date": state.date,
                     "month": _month_name(state.date), "year": state.year,
                     "heading": state.heading, "text": "", "notes": "",
                     "illustrations": ""})
        stats["textless"].append(f"{ROMAN[vol]}/{page}")
    illus = _illustrations(p, xhtml)
    if illus:
        rows[0]["illustrations"] = json.dumps(illus, ensure_ascii=False)
    return rows


def _page_files(source: Path):
    """[(vol, page, read)] for every Arabic-numbered page in book order.
    `source` is the unzipped EPUB folder or the packed .epub file."""
    if source.is_dir():
        found = [(PAGE_FILE.search(f.as_posix()), f) for f in source.rglob("*.xhtml")]
        return sorted((int(m.group(1)), int(m.group(2)),
                       lambda f=f: f.read_text(encoding="utf-8"))
                      for m, f in found if m)
    z = zipfile.ZipFile(source)
    found = [(PAGE_FILE.search(n), n) for n in z.namelist()]
    return sorted((int(m.group(1)), int(m.group(2)),
                   lambda n=n: z.read(n).decode("utf-8"))
                  for m, n in found if m)


def build_rows(source: Path = DEFAULT_EPUB):
    """Parse every diary page of the edition → (rows, stats)."""
    if not source.exists():
        sys.exit(f"EPUB not found: {source}")
    rows = []
    stats = {"pages": 0, "mismatch": 0, "textless": []}
    state, cur_vol = None, None
    for vol, page, read in _page_files(source):
        if vol != cur_vol:
            state, cur_vol = DateState(), vol
        rows.extend(page_rows(vol, page, read(), state, stats))
        stats["pages"] += 1
    return rows, stats


def write_rows(rows, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--epub", type=Path, default=DEFAULT_EPUB,
                    help="unzipped EPUB folder or packed .epub file")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows, stats = build_rows(args.epub)
    write_rows(rows, args.out)

    pages = {(r["vol"], r["page"]) for r in rows}
    print(f"Read {stats['pages']} pages from {args.epub.name}")
    print(f"  diary.csv: {len(rows)} rows on {len(pages)} pages")
    print(f"  pages with illustrations only (no text): {', '.join(stats['textless']) or '-'}")
    print(f"  line-number markers that forced a resync: {stats['mismatch']}")
    try:
        print(f"Wrote {args.out.relative_to(ROOT)}")
    except ValueError:
        print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
