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

Alongside it, diary_html.csv (vol, page, html) keeps each page's own markup
— indentation classes, verse lines, headings, margin line numbers, notes —
as a sanitised HTML fragment for the diary pages, styled by
mockup/css/edition-text.css. See EditionHTML for the tag mapping.

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
DEFAULT_HTML_OUT = ROOT / "data" / "normalized" / "diary_html.csv"

FIELDS = ["vol", "page", "date", "month", "year", "heading", "text",
          "notes", "illustrations"]

ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]

MONTHS = ["Januar", "Februar", "Marts", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "December"]
MONTH_PREFIX = {m[:3].lower(): i + 1 for i, m in enumerate(MONTHS)}
MONTH_PREFIX["maj"] = 5
MONTH_PREFIX["okt"] = MONTH_PREFIX["oct"] = 10
MONTH_VARIANTS = {"maj", "martz", "october", "oct", "sept"}

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
        """Date a header that carries no date id from its own text.

        An editorial correction ("Mai [ɔ: April]", "1874. [ɔ: 1875.]") wins
        over the manuscript reading; a year or "den 25 August" written in
        the heading wins over the carried-over state."""
        parts = re.split(r"\[\s*[ɔo]:", text, maxsplit=1)
        main, corr = parts[0], (parts[1] if len(parts) > 1 else "")
        y_c, m_c, d_c = _parse_header_date(corr)
        y, m, d = _parse_header_date(main)
        year = y_c or y or self.year
        month, day = (m_c, d_c) if m_c else (m, d)
        # A year alone re-dates only a year heading (div1), not e.g.
        # "Indvielse 1867" inside a running month.
        if not year or not (month or (is_year and (y_c or y))):
            return
        self.date = _date_parts(year, f"{month:02d}" if month else None,
                                f"{day:02d}" if month and day else None)


def _month_of(word):
    """Month number for a Danish month word (incl. Maj/Oct/Martz variants
    and abbreviations), else None — so "Margaretha" is not March."""
    for k, n in MONTH_PREFIX.items():
        if word.startswith(k) and (MONTHS[n - 1].lower().startswith(word)
                                   or word in MONTH_VARIANTS):
            return n
    return None


def _parse_header_date(text):
    """(year, month, day) found in a header text; missing parts are None."""
    words = re.sub(r"[^\wæøå]", " ", text.lower()).split()
    year = next((w for w in words if re.fullmatch(r"1[89]\d\d", w)), None)
    for i, w in enumerate(words):
        month = _month_of(w)
        if month:
            prev = words[i - 1] if i else ""
            day = int(prev) if prev.isdigit() and 1 <= int(prev) <= 31 else None
            return year, month, day
    return year, None, None


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
        self.header = None          # (is_year, has_id, [text]) inside <header>
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
            self.header = (a.get("class") == "div1", bool(m), [])
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
            is_year, has_id, parts = self.header
            text = re.sub(r"\s+", " ", "".join(parts)).strip()
            seg = self._seg()
            seg["heading"] = self.state.heading = text
            # A header without its own date id opens a new period: date it
            # from its text, never from the carried-over state — else a
            # year heading after a gap (IV 157: "1855 Reist til Udlandet")
            # inherits the last entry before the gap (1854-07-01).
            if not has_id:
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
            self.header[2].append(data)
        if self.heading_capture is not None:
            self.heading_capture.append(data)


class EditionHTML(HTMLParser):
    """<main> of one page → an HTML fragment that is safe to embed.

    Allow-list serialiser. The EPUB is XHTML, where <p> may contain <div>,
    <ul> and <aside>; an HTML parser would close the <p> at those and lose
    the indentation class, so every <p> becomes <div class="p …">. <header>
    becomes <div class="hdr …"> (no stray landmarks inside the page), and
    the line-number attribute n becomes data-n. Unknown tags are dropped
    but their text kept.
    """

    RENAME = {"p": ("div", "p"), "header": ("div", "hdr")}
    KEEP = {"div", "i", "br", "ul", "li", "table", "tr", "td", "span",
            "aside", "figure", "figcaption"}
    VOID = {"br"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.in_main = False
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self.in_main = True
            return
        if not self.in_main:
            return
        a = dict(attrs)
        name, base_cls = self.RENAME.get(tag, (tag, ""))
        if name not in self.KEEP:
            self.stack.append(None)
            return
        cls = " ".join(dict.fromkeys(filter(None, [base_cls, *re.findall(r"[\w-]+", a.get("class") or "")])))
        out = []
        if cls:
            out.append(f'class="{cls}"')
        if DATE_ID.match(a.get("id") or ""):
            out.append(f'id="{a["id"]}"')
        n = (a.get("n") or "").strip()
        if n.isdigit() and tag in ("i", "header"):
            out.append(f'data-n="{n}"')
        if tag == "span" and a.get("title"):
            out.append(f'title="{html.escape(a["title"])}" tabindex="0"')
        if tag == "aside" and a.get("role") == "note":
            out.append('role="note"')
        self.out.append(f"<{name}{' ' if out else ''}{' '.join(out)}>")
        if tag not in self.VOID:
            self.stack.append(name)

    def handle_endtag(self, tag):
        if tag == "main":
            self.in_main = False
            return
        if not self.in_main or tag in self.VOID or not self.stack:
            return
        name = self.stack.pop()
        if name:
            self.out.append(f"</{name}>")

    def handle_data(self, data):
        if self.in_main:
            self.out.append(html.escape(data, quote=False))


def page_html(xhtml):
    p = EditionHTML()
    p.feed(xhtml)
    p.close()
    return re.sub(r"\n\s*\n", "\n", "".join(p.out)).strip()


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


def build_page_html(source: Path = DEFAULT_EPUB):
    """[{vol, page, html}] — one sanitised markup fragment per diary page."""
    return [{"vol": ROMAN[vol], "page": str(page), "html": page_html(read())}
            for vol, page, read in _page_files(source)]


def write_rows(rows, out: Path, fields=FIELDS):
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _rel(path: Path):
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--epub", type=Path, default=DEFAULT_EPUB,
                    help="unzipped EPUB folder or packed .epub file")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--html-out", type=Path, default=DEFAULT_HTML_OUT,
                    help="per-page markup fragments for the diary pages")
    args = ap.parse_args()

    rows, stats = build_rows(args.epub)
    write_rows(rows, args.out)
    html_rows = build_page_html(args.epub)
    write_rows(html_rows, args.html_out, ["vol", "page", "html"])

    pages = {(r["vol"], r["page"]) for r in rows}
    print(f"Read {stats['pages']} pages from {args.epub.name}")
    print(f"  diary.csv: {len(rows)} rows on {len(pages)} pages")
    print(f"  diary_html.csv: {len(html_rows)} pages")
    print(f"  pages with illustrations only (no text): {', '.join(stats['textless']) or '-'}")
    print(f"  line-number markers that forced a resync: {stats['mismatch']}")
    print(f"Wrote {_rel(args.out)} and {_rel(args.html_out)}")


if __name__ == "__main__":
    main()
