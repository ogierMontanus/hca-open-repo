#!/usr/bin/env python3
"""
Build a navigable PDF of selected diary pages for the HCA Open Repository.

Reads:
  data/normalized/diary.csv       — transcribed text (vol VI + VII only)
  data/normalized/references.csv  — entity occurrences per diary page
  data/normalized/entities.csv    — entity labels and types

Writes one PDF (default ./hca-dagbog.pdf) in which

  1. every diary page carries a direct, absolute link to that page in the
     diary section of the site (<base-url>diary-pages/Pag{VV}{PPPP}.html) —
     on the page title and in the footer of every PDF page it occupies;
  2. the register entries (persons, places, works) mentioned on each page
     are listed as footnotes at the bottom of that page; the entries you
     searched for / selected are highlighted with a yellow background;
  3. a native PDF outline (the reader's Bookmarks pane) has the dates as
     headings: year > month > day, so a PDF with many entries can be
     navigated without scrolling.

Which pages go in:
  --cart hca-cart.json   the file from cart.html's "Hent kurv til PDF-bygger"
                         button: diary items in the cart are the pages, and
                         person/place/work items are the highlighted entities
  --pages Pag070002 …    explicit diary page ids
  --entity Reg0052440 …  highlighted entities; if no pages are given, every
                         page that mentions them is exported

Run from the repo root (PowerShell):
  python scripts/build_mockup/build_diary_pdf.py --cart hca-cart.json -o dagbog.pdf

Needs reportlab (pip install reportlab).
"""

import argparse
import csv
import datetime
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

try:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.platypus import Paragraph
    import reportlab
except ImportError:  # pragma: no cover - message only
    sys.exit("reportlab mangler — kør: pip install reportlab")

REPO_ROOT = Path(__file__).resolve().parents[2]
REFS_CSV = REPO_ROOT / "data" / "normalized" / "references.csv"
DIARY_CSV = REPO_ROOT / "data" / "normalized" / "diary.csv"
ENTS_CSV = REPO_ROOT / "data" / "normalized" / "entities.csv"

# Where the generated mockup is published. A guess until the real hosting is
# settled — override with --base-url. Must end in "/".
DEFAULT_BASE_URL = "https://ogiermontanus.github.io/hca-open-repo/mockup/"

VOL_NUM = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6,
    "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11,
}
NUM_VOL = {n: v for v, n in VOL_NUM.items()}

# Detail page per entity type — same targets as build_diary_pages.py.
ENTITY_PAGE = {"person": "persons.html", "place": "place.html", "work": "work.html"}
ENTITY_TYPE_DA = {"person": "Person", "place": "Sted", "work": "Værk"}

WEEKDAYS_DA = ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"]
MONTHS_DA = ["januar", "februar", "marts", "april", "maj", "juni", "juli",
             "august", "september", "oktober", "november", "december"]

HIGHLIGHT = "#FFEB3B"   # yellow background for the searched/selected entities
LINK_COLOR = "#1a4f8b"
MUTED = "#666666"

PAGE_W, PAGE_H = A4
MARGIN_X = 54
MARGIN_TOP = 56
FOOTER_BAND = 46          # space reserved at the bottom for the running footer
MAX_FOOTNOTE_H = 330      # footnotes never take more than this per PDF page
MIN_FOOTNOTE_H = 70       # less room than this left: footnotes start a new page
COL_GAP = 16


# ── ids, dates, text ────────────────────────────────────────────────────────

def page_id(vol: str, page: str) -> str:
    """Same id scheme as build_diary_pages.py / build_diary_index.py."""
    try:
        pn = int(page)
    except ValueError:
        pn = 0
    return f"Pag{VOL_NUM.get(vol, 0):02d}{pn:04d}"


def parse_page_id(pid: str):
    m = re.fullmatch(r"Pag(\d{2})(\d{4})", pid)
    if not m or int(m.group(1)) not in NUM_VOL:
        raise ValueError(f"Ukendt dagbogsside-id: {pid!r} (forventet fx Pag070002)")
    return NUM_VOL[int(m.group(1))], str(int(m.group(2)))


def sort_key(vp):
    vol, pg = vp
    return (VOL_NUM.get(vol, 99), int(pg) if pg.isdigit() else 0)


def format_date_da(iso: str):
    """'1866-01-03' -> 'Onsdag 3. januar 1866'; None if not a real date."""
    try:
        d = datetime.date.fromisoformat(iso)
    except ValueError:
        return None
    return f"{WEEKDAYS_DA[d.weekday()]} {d.day}. {MONTHS_DA[d.month - 1]} {d.year}"


def clean_text(raw: str) -> str:
    """Strip the 'NNN-NN' line stamps and join the lines, like the site does."""
    lines = []
    for line in (raw or "").split("\n"):
        line = re.sub(r"^<?\d+-\d+>?\s*", "", line).strip()
        if line:
            lines.append(line)
    return " ".join(lines)


def classify_row(row: dict, vol: str):
    """-> (kind, heading, outline_path) for one diary.csv row.

    outline_path is a list of (key, title) from year down to the row itself;
    key equality between consecutive rows is what keeps the outline from
    repeating a year, month or date it is already inside.
    """
    iso = (row.get("date") or "").strip()
    year = (row.get("year") or "").strip()
    month = (row.get("month") or "").strip()
    m = re.fullmatch(r"(\d{4})-(\d{2}|XX)-(\d{2}|XX)", iso)
    if m:
        y, mo, d = m.groups()
        if d != "XX" and mo != "XX":
            label = format_date_da(iso)
            if label:
                return "day", label, [
                    (f"y{y}", y),
                    (f"m{y}-{mo}", f"{MONTHS_DA[int(mo) - 1].capitalize()} {y}"),
                    (f"d{iso}", label),
                ]
        elif mo != "XX":
            title = f"{(month or MONTHS_DA[int(mo) - 1]).capitalize()} {y}"
            return "month", title, [(f"y{y}", y), (f"m{y}-{mo}", title)]
        else:
            return "year", y, [(f"y{y}", y)]
    heading = (row.get("heading") or "").strip() or iso or year or "Uden dato"
    return "other", heading, None


# ── data ────────────────────────────────────────────────────────────────────

def load_entities() -> dict:
    ents = {}
    with ENTS_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ents[row["entity_id"]] = {"label": row["label"], "type": row["entity_type"]}
    return ents


def load_diary() -> dict:
    d = defaultdict(list)
    with DIARY_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d[(row["vol"], row["page"])].append(row)
    return d


def load_references():
    """-> ({(vol,page): [entity_id, …] in seq order, de-duplicated},
           {entity_id: set((vol,page))})"""
    page_ents = defaultdict(list)
    ent_pages = defaultdict(set)
    with REFS_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            vol, pg, eid = row["vol"], row["page"], row["entity_id"]
            if not vol or not pg:
                continue
            if eid not in page_ents[(vol, pg)]:
                page_ents[(vol, pg)].append(eid)
            ent_pages[eid].add((vol, pg))
    return page_ents, ent_pages


# ── selection ───────────────────────────────────────────────────────────────

def read_cart(path: Path):
    """Cart export -> (diary page ids, entity ids). Accepts the bare array the
    cart keeps in sessionStorage or {"items": [...]} from cart.html."""
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items", []) if isinstance(data, dict) else data
    pages, ents = [], []
    for it in items:
        if it.get("type") == "diary":
            pages.append(it["rid"])
        elif it.get("type") in ENTITY_PAGE:
            ents.append(it["rid"])
    return pages, ents


def select_pages(page_ids, entity_ids, page_ents, ent_pages, max_pages):
    """-> sorted list of (vol, page). Pages named explicitly win; with none,
    every page that mentions one of the entities."""
    if page_ids:
        sel = {parse_page_id(p) for p in page_ids}
    else:
        sel = set()
        for e in entity_ids:
            sel |= ent_pages.get(e, set())
    if len(sel) > max_pages:
        sys.exit(f"{len(sel)} sider overstiger --max-pages {max_pages}. "
                 f"Vælg færre sider, eller hæv grænsen med --max-pages.")
    return sorted(sel, key=sort_key)


# ── fonts ───────────────────────────────────────────────────────────────────

_FONT_DIRS = [
    Path("C:/Windows/Fonts"),
    Path("/usr/share/fonts/truetype/liberation"),
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/Library/Fonts"),
    Path("/System/Library/Fonts/Supplemental"),
    Path.home() / "Library" / "Fonts",
    Path(reportlab.__file__).parent / "fonts",   # Bitstream Vera, always present
]
# (family, regular, bold, italic, bold-italic); the first complete one wins.
_SERIF = [
    ("Georgia", "georgia.ttf", "georgiab.ttf", "georgiai.ttf", "georgiaz.ttf"),
    ("LiberationSerif", "LiberationSerif-Regular.ttf", "LiberationSerif-Bold.ttf",
     "LiberationSerif-Italic.ttf", "LiberationSerif-BoldItalic.ttf"),
    ("DejaVuSerif", "DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf",
     "DejaVuSerif-Italic.ttf", "DejaVuSerif-BoldItalic.ttf"),
    ("Vera", "Vera.ttf", "VeraBd.ttf", "VeraIt.ttf", "VeraBI.ttf"),
]
_SANS = [
    ("Arial", "arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"),
    ("LiberationSans", "LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf",
     "LiberationSans-Italic.ttf", "LiberationSans-BoldItalic.ttf"),
    ("DejaVuSans", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf",
     "DejaVuSans-Oblique.ttf", "DejaVuSans-BoldOblique.ttf"),
    ("Vera", "Vera.ttf", "VeraBd.ttf", "VeraIt.ttf", "VeraBI.ttf"),
]


def register_family(candidates, alias: str, extra_dir=None) -> str:
    """Register the first candidate family whose four files are all found, as
    `alias`, so <b>/<i> in Paragraph markup resolve. TTF, not the built-in PDF
    fonts: those are ASCII-only and would mangle æ/ø/å."""
    dirs = ([Path(extra_dir)] if extra_dir else []) + _FONT_DIRS
    for fam, *files in candidates:
        found = []
        for fn in files:
            hit = next((d / fn for d in dirs if (d / fn).is_file()), None)
            if hit is None:
                break
            found.append(hit)
        else:
            names = [f"{alias}", f"{alias}-Bold", f"{alias}-Italic", f"{alias}-BoldItalic"]
            for n, p in zip(names, found):
                pdfmetrics.registerFont(TTFont(n, str(p)))
            pdfmetrics.registerFontFamily(alias, normal=names[0], bold=names[1],
                                          italic=names[2], boldItalic=names[3])
            return alias
    sys.exit("Fandt ingen skrifttype med æ/ø/å. Angiv mappen med --font-dir.")


# ── the PDF ─────────────────────────────────────────────────────────────────

class DiaryPdf:
    def __init__(self, out, base_url, ents, page_ents, diary, highlight,
                 font_dir=None):
        self.base_url = base_url
        self.ents = ents
        self.page_ents = page_ents
        self.diary = diary
        self.highlight = set(highlight)
        self.c = Canvas(str(out), pagesize=A4, pageCompression=1)
        self.c.setTitle("HCA Open Repository — dagbogsudvalg")
        self.c.setAuthor("HCA Open Repository")
        self.c.setCreator("scripts/build_mockup/build_diary_pdf.py")
        self.c.showOutline()                      # open with Bookmarks pane

        serif = register_family(_SERIF, "HcaSerif", font_dir)
        sans = register_family(_SANS, "HcaSans", font_dir)
        self.st = {
            "title": ParagraphStyle("title", fontName=serif + "-Bold", fontSize=17,
                                    leading=21, textColor=HexColor("#1b2a41")),
            "sub": ParagraphStyle("sub", fontName=sans, fontSize=8.5, leading=11,
                                  textColor=HexColor(MUTED)),
            "cont": ParagraphStyle("cont", fontName=sans, fontSize=8.5, leading=11,
                                   textColor=HexColor(MUTED)),
            "date": ParagraphStyle("date", fontName=serif + "-Bold", fontSize=11.5,
                                   leading=15, spaceBefore=8, spaceAfter=3,
                                   textColor=HexColor("#1b2a41")),
            "label": ParagraphStyle("label", fontName=serif + "-BoldItalic", fontSize=10,
                                    leading=13, spaceBefore=6, spaceAfter=2,
                                    textColor=HexColor(MUTED)),
            "body": ParagraphStyle("body", fontName=serif, fontSize=10.5, leading=15,
                                   spaceAfter=5),
            "note": ParagraphStyle("note", fontName=serif + "-Italic", fontSize=10,
                                   leading=14, textColor=HexColor(MUTED)),
            "fn_title": ParagraphStyle("fn_title", fontName=sans + "-Bold", fontSize=8,
                                       leading=10, textColor=HexColor("#333333")),
            "fn": ParagraphStyle("fn", fontName=sans, fontSize=7.5, leading=9.5,
                                 leftIndent=11, firstLineIndent=-11),
            "h1": ParagraphStyle("h1", fontName=serif + "-Bold", fontSize=22, leading=27,
                                 textColor=HexColor("#1b2a41"), spaceAfter=6),
            "p": ParagraphStyle("p", fontName=serif, fontSize=10.5, leading=15,
                                spaceAfter=6),
        }
        self.sans = sans
        self.width = PAGE_W - 2 * MARGIN_X
        self.body_bottom = FOOTER_BAND
        self.page_no = 0
        self.y = 0.0
        self.cur = None            # (vol, page, pid) of the diary page being drawn
        self.page_open = False
        self.outline_state = []    # keys of the outline entries currently "open"
        self.bm_counter = 0

    # urls
    def page_url(self, pid):
        return f"{self.base_url}diary-pages/{pid}.html"

    def entity_url(self, eid, etype):
        return f"{self.base_url}{ENTITY_PAGE.get(etype, 'persons.html')}?reg={eid}"

    # pages
    def _finish_page(self):
        if not self.page_open:
            return
        c = self.c
        c.setStrokeColor(HexColor("#cccccc"))
        c.setLineWidth(0.5)
        c.line(MARGIN_X, 34, PAGE_W - MARGIN_X, 34)
        c.setFont(self.sans, 7.5)
        c.setFillColor(HexColor(MUTED))
        right = f"PDF-side {self.page_no}"
        c.drawRightString(PAGE_W - MARGIN_X, 22, right)
        if self.cur:
            vol, page, pid = self.cur
            text = f"Bind {vol}, side {page} · {pid} — åbn siden på HCA Open Repository \u2192"
            c.setFillColor(HexColor(LINK_COLOR))
            c.drawString(MARGIN_X, 22, text)
            w = pdfmetrics.stringWidth(text, self.sans, 7.5)
            c.linkURL(self.page_url(pid), (MARGIN_X, 18, MARGIN_X + w, 31),
                      relative=0, thickness=0)
        c.showPage()
        self.page_open = False

    def _new_page(self):
        self._finish_page()
        self.page_no += 1
        self.page_open = True
        self.y = PAGE_H - MARGIN_TOP

    def _draw(self, para, x=MARGIN_X, width=None):
        """Draw a paragraph with its top at self.y; move self.y below it."""
        self.y -= para.style.spaceBefore
        w, h = para.wrap(width or self.width, 1e6)
        para.drawOn(self.c, x, self.y - h)
        self.y -= h + para.style.spaceAfter
        return h

    def _start_diary_page(self, vol, page, pid, continued=False):
        self._finish_page()          # footer still belongs to the previous diary page
        self.cur = (vol, page, pid)
        self._new_page()
        url = self.page_url(pid)
        if continued:
            self._draw(Paragraph(
                f'<a href="{escape(url)}" color="{LINK_COLOR}">Bind {escape(vol)}, '
                f'side {escape(page)}</a> (fortsat)', self.st["cont"]))
            self.y -= 4
            return
        self._draw(Paragraph(
            f'<a href="{escape(url)}" color="#1b2a41">Bind {escape(vol)}, side {escape(page)}</a>',
            self.st["title"]))
        self._draw(Paragraph(
            f'{escape(pid)} · <a href="{escape(url)}" color="{LINK_COLOR}">'
            f'Åbn siden i dagbogsafsnittet på HCA Open Repository \u2192</a>', self.st["sub"]))
        self.y -= 8

    # outline
    def _outline(self, path):
        """Open outline entries for `path` (year > month > date) at the current
        position, skipping the leading levels already open."""
        if not path:
            return
        i = 0
        while (i < len(path) and i < len(self.outline_state)
               and self.outline_state[i] == path[i][0]):
            i += 1
        for lvl in range(i, len(path)):
            self.bm_counter += 1
            name = f"bm{self.bm_counter}"
            self.c.bookmarkHorizontal(name, 0, self.y + 18)
            # years open, months collapsed: overview first, days one click away
            self.c.addOutlineEntry(path[lvl][1], name, level=lvl, closed=(lvl == 1))
        self.outline_state = [k for k, _ in path]

    # body flow
    def _continue_page(self):
        vol, page, pid = self.cur
        self._start_diary_page(vol, page, pid, continued=True)

    def _heading(self, para, path):
        """Draw a date heading; it moves to a fresh page first unless two
        lines of its text fit below it, so the bookmark and the heading always
        land on the same page."""
        w, h = para.wrap(self.width, 1e6)
        need = para.style.spaceBefore + h + para.style.spaceAfter + 2 * 15
        if self.y - need < self.body_bottom:
            self._continue_page()
        self._outline(path)
        self._draw(para)

    def _place(self, para):
        """Draw a text paragraph, splitting it across PDF pages as needed."""
        while True:
            w, h = para.wrap(self.width, 1e6)
            if self.y - para.style.spaceBefore - h - para.style.spaceAfter >= self.body_bottom:
                self._draw(para)
                return
            parts = para.split(self.width, self.y - self.body_bottom)
            if len(parts) >= 2:
                self._draw(parts[0])
                para = parts[1]
            self._continue_page()

    # footnotes
    def _footnote_paras(self, eids):
        paras = []
        for n, eid in enumerate(eids, 1):
            e = self.ents.get(eid, {"label": eid, "type": ""})
            url = self.entity_url(eid, e["type"])
            kind = ENTITY_TYPE_DA.get(e["type"], "")
            inner = (f'<b>{n}</b>\u00a0 <a href="{escape(url)}" color="{LINK_COLOR}">'
                     f'{escape(e["label"])}</a> '
                     f'<font size="6.5" color="{MUTED}">{kind} · {escape(eid)}</font>')
            if eid in self.highlight:
                inner = f'<font backColor="{HIGHLIGHT}">{inner}</font>'
            paras.append(Paragraph(inner, self.st["fn"]))
        return paras

    def _pack_chunk(self, items, cap):
        """Fill two balanced columns, each at most `cap` tall, from the front
        of `items` [(para, height)]. -> (columns, remaining items)."""
        target = min(sum(h for _, h in items), 2 * cap) / 2
        cols, i = [[], []], 0
        for ci in range(2):
            h = 0.0
            while i < len(items) and h + items[i][1] <= cap and (ci == 1 or h < target):
                cols[ci].append(items[i])
                h += items[i][1]
                i += 1
        if not cols[0] and items:                      # one tall entry: still progress
            cols[0].append(items[0])
            i = 1
        return cols, items[i:]

    def _draw_footnote_chunk(self, cols, col_w, total, first, anchor_bottom):
        height = max(sum(h for _, h in col) for col in cols)
        title = (f"Registerposter på siden ({total})" if first
                 else f"Registerposter på siden ({total}) \u2014 fortsat")
        block_h = height + 16
        top = (self.body_bottom + block_h) if anchor_bottom else self.y
        c = self.c
        c.setStrokeColor(HexColor("#999999"))
        c.setLineWidth(0.6)
        c.line(MARGIN_X, top, MARGIN_X + 90, top)
        t = Paragraph(title, self.st["fn_title"])
        t.wrap(self.width, 20)
        t.drawOn(c, MARGIN_X, top - 3 - t.height)
        for ci, col in enumerate(cols):
            x = MARGIN_X + ci * (col_w + COL_GAP)
            y = top - 16
            for para, h in col:
                para.wrap(col_w, 1e6)
                para.drawOn(c, x, y - (h - 1.5))
                y -= h
        self.y = top - block_h

    def _footnotes(self, eids):
        """Footnotes sit at the foot of the last PDF page of the diary page's
        text, in as much room as is left there (at most MAX_FOOTNOTE_H); what
        does not fit continues on following pages."""
        if not eids:
            return
        col_w = (self.width - COL_GAP) / 2
        items = [(p, p.wrap(col_w, 1e6)[1] + 1.5) for p in self._footnote_paras(eids)]
        first = True
        while items:
            cap = min(MAX_FOOTNOTE_H, self.y - self.body_bottom - 16 - 6)
            on_body_page = cap >= MIN_FOOTNOTE_H
            if not on_body_page:
                self._continue_page()
                cap = MAX_FOOTNOTE_H
            cols, items = self._pack_chunk(items, cap)
            self._draw_footnote_chunk(cols, col_w, len(eids), first, anchor_bottom=on_body_page)
            first = False

    # diary page
    def add_diary_page(self, vol, page):
        pid = page_id(vol, page)
        rows = self.diary.get((vol, page), [])
        self._start_diary_page(vol, page, pid)
        undated_path = [(f"u{vol}", f"Bind {vol} — uden dato"), (f"p{pid}", f"Side {page}")]

        if not rows:
            self._outline(undated_path)
            self._place(Paragraph(
                f"Dagbogsteksten for bind {escape(vol)} er endnu ikke transskriberet i "
                f"dette projekt. Siden kendes herfra kun gennem sine registerposter.",
                self.st["note"]))
        for row in rows:
            kind, heading, path = classify_row(row, vol)
            text = clean_text(row.get("text", ""))
            style = "label" if kind == "other" else "date"
            self._heading(Paragraph(escape(heading), self.st[style]),
                          path if path else undated_path)
            if text and not (kind in ("month", "year") and len(text) < 40):
                self._place(Paragraph(escape(text), self.st["body"]))
        self._footnotes(self.page_ents.get((vol, page), []))

    # cover
    def add_cover(self, pages, highlight_ids):
        self.cur = None
        self._new_page()
        st = self.st
        self._draw(Paragraph("Dagbogsudvalg", st["h1"]))
        self._draw(Paragraph("HCA Open Repository \u2014 H.C. Andersens dagbøger", st["sub"]))
        self.y -= 14
        today = datetime.date.today()
        self._draw(Paragraph(
            f"Udvalg på <b>{len(pages)}</b> dagbogssider, dannet {today.day}. "
            f"{MONTHS_DA[today.month - 1]} {today.year}.", st["p"]))
        self._draw(Paragraph(
            "<b>Navigation.</b> Åbn PDF-læserens bogmærker (Bookmarks): datoerne er "
            "overskrifter, ordnet år \u203a måned \u203a dag. Titlen og bundlinjen på hver "
            "side er et direkte link til samme side i dagbogsafsnittet på webstedet.",
            st["p"]))
        self._draw(Paragraph(
            "<b>Fodnoter.</b> Nederst på hver side står de registerposter (personer, "
            "steder, værker), der er knyttet til siden.", st["p"]))
        if highlight_ids:
            self._draw(Paragraph(
                f'<font backColor="{HIGHLIGHT}"> Gul baggrund </font> markerer de '
                f"valgte poster i fodnoterne:", st["p"]))
            for eid in highlight_ids:
                e = self.ents.get(eid, {"label": eid, "type": ""})
                url = self.entity_url(eid, e["type"])
                self._draw(Paragraph(
                    f'<font backColor="{HIGHLIGHT}"><a href="{escape(url)}" color="{LINK_COLOR}">'
                    f'{escape(e["label"])}</a></font> '
                    f'<font size="8" color="{MUTED}">{ENTITY_TYPE_DA.get(e["type"], "")} · '
                    f'{escape(eid)}</font>', st["p"]))

    def save(self):
        self._finish_page()
        self.c.save()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cart", type=Path, help="kurv-fil fra cart.html (JSON)")
    ap.add_argument("--pages", nargs="*", default=[], metavar="PAGID",
                    help="dagbogsside-id'er, fx Pag070002")
    ap.add_argument("--entity", nargs="*", default=[], metavar="REGID",
                    help="registerposter der fremhæves i fodnoterne (gul baggrund)")
    ap.add_argument("-o", "--out", type=Path, default=Path("hca-dagbog.pdf"))
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL,
                    help=f"sidens offentlige adresse, slutter med / (standard {DEFAULT_BASE_URL})")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--font-dir", help="mappe med TTF-skrifttyper (æ/ø/å)")
    args = ap.parse_args(argv)

    page_ids, entity_ids = list(args.pages), list(args.entity)
    if args.cart:
        cp, ce = read_cart(args.cart)
        page_ids += cp
        entity_ids += ce
    entity_ids = list(dict.fromkeys(entity_ids))
    if not page_ids and not entity_ids:
        ap.error("angiv mindst en af --cart, --pages eller --entity")
    base = args.base_url if args.base_url.endswith("/") else args.base_url + "/"

    ents = load_entities()
    page_ents, ent_pages = load_references()
    diary = load_diary()
    unknown = [e for e in entity_ids if e not in ents]
    if unknown:
        print(f"Advarsel: ukendte registerposter ignoreret: {', '.join(unknown)}", file=sys.stderr)
        entity_ids = [e for e in entity_ids if e in ents]

    pages = select_pages(page_ids, entity_ids, page_ents, ent_pages, args.max_pages)
    if not pages:
        sys.exit("Ingen dagbogssider at eksportere.")
    if not entity_ids:
        print("Bemærk: ingen registerposter angivet — intet fremhæves i fodnoterne "
              "(brug --entity eller læg poster i kurven).", file=sys.stderr)

    pdf = DiaryPdf(args.out, base, ents, page_ents, diary, entity_ids, args.font_dir)
    pdf.add_cover(pages, entity_ids)
    for vol, pg in pages:
        pdf.add_diary_page(vol, pg)
    pdf.save()
    print(f"Skrev {args.out} — {len(pages)} dagbogssider, {pdf.page_no} PDF-sider.")


if __name__ == "__main__":
    main()
