#!/usr/bin/env python3
"""
Build static diary-page HTML files for the HCA mockup.

Reads:
  data/normalized/references.csv  — entity occurrences per diary page
  data/normalized/diary.csv       — transcribed text (vol VI + VII only)
  data/normalized/entities.csv    — entity metadata (label, type, h1 category)

Writes:
  mockup/diary-pages/Pag{VV}{PPPP}.html  — one file per unique vol+page
    where VV = zero-padded volume number (I=01 … XI=11)
    and PPPP = zero-padded page number

Run from the repo root:
  python3 scripts/build_mockup/build_diary_pages.py
"""

import csv
import html
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REFS_CSV  = REPO_ROOT / "data" / "normalized" / "references.csv"
DIARY_CSV = REPO_ROOT / "data" / "normalized" / "diary.csv"
ENTS_CSV  = REPO_ROOT / "data" / "normalized" / "entities.csv"
KB_CSV    = REPO_ROOT / "data" / "normalized" / "kb_diary_links.csv"
OUT_DIR   = REPO_ROOT / "mockup" / "diary-pages"

VOL_NUM = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6,
    "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11,
}

H1_LABEL = {
    "PERSON-REGISTER": "Person",
    "STED-REGISTER":   "Sted",
    "VÆRK-REGISTER":   "Værk",
}

H1_CHIP = {
    "PERSON-REGISTER": "chip--person",
    "STED-REGISTER":   "chip--place",
    "VÆRK-REGISTER":   "chip--work",
}

H1_LINK = {
    # Per-entity detail pages — the label chip and the Reg ID below both
    # become hyperlinks to ?reg={entity_id} on the appropriate template,
    # mirroring the existing work.html?reg=… pattern.
    "PERSON-REGISTER": "../persons.html",
    "STED-REGISTER":   "../place.html",
    "VÆRK-REGISTER":   "../work.html",
}


def page_id(vol: str, page: str) -> str:
    vn = VOL_NUM.get(vol, 0)
    try:
        pn = int(page)
    except ValueError:
        pn = 0
    return f"Pag{vn:02d}{pn:04d}"


def load_entities() -> dict:
    ents = {}
    with ENTS_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ents[row["entity_id"]] = {
                "label":    row["label"],
                "type":     row["entity_type"],
                "h1":       row["category_h1"],
                "h2":       row["genre_h2"],
            }
    return ents


def load_diary() -> dict:
    """Returns {(vol, page): [row, ...]} sorted by original CSV order."""
    d = defaultdict(list)
    with DIARY_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d[(row["vol"], row["page"])].append(row)
    return d


def load_kb_links() -> dict:
    """pag_id -> permanent Det Kgl. Bibliotek URL.

    Built by scripts/build_mockup/build_kb_links.py from the KB link
    workbook. Optional: if the CSV has not been generated the pages are
    written without the link rather than failing the build. Vol XI is
    absent upstream, so those pages never get one.
    """
    links = {}
    if not KB_CSV.exists():
        return links
    with KB_CSV.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("kb_url"):
                links[r["pag_id"]] = r["kb_url"]
    return links


def load_references() -> dict:
    """Returns {(vol, page): [entity_id, ...]} preserving seq order."""
    refs = defaultdict(list)
    with REFS_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            refs[(row["vol"], row["page"])].append(row["entity_id"])
    return refs


def sorted_pages(refs: dict) -> list:
    """Return all vol+page keys sorted by (vol_num, page_num)."""
    def sort_key(vp):
        vol, pg = vp
        return (VOL_NUM.get(vol, 99), int(pg) if pg.isdigit() else 0)
    return sorted(refs.keys(), key=sort_key)


def diary_text_html(diary_rows: list) -> str:
    if not diary_rows:
        return ""
    paragraphs = []
    for row in diary_rows:
        raw = row.get("text", "").strip()
        if not raw:
            continue
        # Each row may contain multiple newline-separated lines, each prefixed
        # with a line-number stamp like "001-03   " or "<184-01>"
        lines = raw.split("\n")
        clean_lines = []
        for line in lines:
            line = re.sub(r"^<?\d+-\d+>?\s*", "", line).strip()
            if line:
                clean_lines.append(line)
        if clean_lines:
            paragraphs.append(html.escape(" ".join(clean_lines)))
    if not paragraphs:
        return ""
    return "\n".join(f"<p>{p}</p>" for p in paragraphs)


def date_range(diary_rows: list) -> str:
    dates = [r["date"] for r in diary_rows if r.get("date") and "XX" not in r["date"]]
    months = [r["month"] for r in diary_rows if r.get("month")]
    years = [r["year"] for r in diary_rows if r.get("year")]
    if dates:
        return dates[0]
    if months and years:
        return f"{months[0]} {years[0]}"
    if years:
        return years[0]
    return "—"


def render_page(vol: str, page: str, ents: dict, diary: dict, refs: dict,
                all_pages: list, idx: int, kb_links: dict) -> str:
    vp = (vol, page)
    entity_ids = refs.get(vp, [])
    diary_rows = diary.get(vp, [])
    pid = page_id(vol, page)
    date_str = date_range(diary_rows)

    # Permanent link to the page at Det Kgl. Bibliotek. Deliberately quiet:
    # it sits under the title where a reader looks first, but is small and
    # low-contrast so it does not compete with the page's own content. The
    # arrow and the new tab mark it as leaving the site — see
    # docs/external-links.md.
    kb_url = kb_links.get(pid, "")
    kb_link_html = (
        f'<a class="external-link external-link--on-dark" href="{html.escape(kb_url)}" '
        f'target="_blank" rel="noopener noreferrer">'
        f'Læs siden hos Det Kgl. Bibliotek<span class="external-link__icon" aria-hidden="true">↗</span>'
        f'<span class="sr-only"> (åbner i nyt faneblad)</span></a>'
        if kb_url else ""
    )
    has_text = bool(diary_rows)
    # Same heading rule as js/diary-wire.js's headingFor(): the date wins
    # when there is one, otherwise the volume/page reference. Used as the
    # cart label — see Cart.mountToggle() call near the closing </body>.
    heading_str = date_str if date_str != "—" else f"Bind {vol}, s. {page}"

    # Group entities by h1 category, deduplicate preserving order
    by_h1 = defaultdict(list)
    seen = set()
    for eid in entity_ids:
        if eid in seen:
            continue
        seen.add(eid)
        e = ents.get(eid)
        if e:
            by_h1[e["h1"]].append((eid, e))

    # Build entity refs HTML
    ref_blocks = []
    for h1 in ["PERSON-REGISTER", "STED-REGISTER", "VÆRK-REGISTER"]:
        items = by_h1.get(h1, [])
        if not items:
            continue
        chip_cls = H1_CHIP.get(h1, "")
        base = H1_LINK[h1]
        list_html = "\n".join(
            f'<div class="entity-ref-item">'
            f'<a href="{html.escape(base)}?reg={html.escape(eid)}" class="chip {chip_cls}">'
            f'{html.escape(e["label"])}</a>'
            f'<a href="{html.escape(base)}?reg={html.escape(eid)}" class="entity-ref-item__rel">'
            f'{html.escape(eid)}</a>'
            f'</div>'
            for eid, e in items
        )
        ref_blocks.append(
            f'<div class="entity-ref-group">'
            f'<h4>{H1_LABEL[h1]} ({len(items)})</h4>'
            f'<div class="entity-ref-list">{list_html}</div>'
            f'</div>'
        )

    refs_html = "\n".join(ref_blocks) if ref_blocks else '<p class="muted">Ingen registerposter.</p>'

    # Diary text section
    if has_text:
        txt = diary_text_html(diary_rows)
        if txt:
            diary_section = f'''
          <div>
            <h2 class="section-title">Dagbogstext <small style="font-weight:400;font-size:0.75rem;color:var(--color-text-muted)">(bind {html.escape(vol)})</small></h2>
            <div class="entry-text">{txt}</div>
          </div>'''
        else:
            diary_section = ""
    else:
        diary_section = f'''
          <div>
            <p class="muted" style="font-style:italic">Dagbogstekst for bind {html.escape(vol)} er endnu ikke transskriberet i dette projekt.</p>
          </div>'''

    # Prev / next navigation
    prev_link = ""
    next_link = ""
    if idx > 0:
        pv, pp = all_pages[idx - 1]
        prev_id = page_id(pv, pp)
        prev_link = f'<a href="{prev_id}.html">← Bind {html.escape(pv)}, side {html.escape(pp)}</a>'
    if idx < len(all_pages) - 1:
        nv, np_ = all_pages[idx + 1]
        next_id = page_id(nv, np_)
        next_link = f'<a href="{next_id}.html">Bind {html.escape(nv)}, side {html.escape(np_)} →</a>'

    title_str = f"Bind {html.escape(vol)}, side {html.escape(page)} — {html.escape(date_str)}"

    # json.dumps rather than an f-string interpolation here: it produces a
    # properly quoted-and-escaped JS string literal (backslashes, quotes,
    # non-ASCII) with no risk of the value breaking out of the '...' it's
    # embedded in below, unlike hand-escaping pid/heading_str ourselves.
    pid_js = json.dumps(pid)
    heading_js = json.dumps(heading_str)

    return f'''<!DOCTYPE html>
<html lang="da">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_str} — H.C. Andersen Dagbogsregister</title>
  <link rel="stylesheet" href="../css/style.css">
</head>
<body>

<header class="site-header">
  <div class="container">
    <a href="../index.html" class="site-logo">H.C. Andersen Dagbogsregister</a>
    <form class="search-form" role="search" onsubmit="return false">
      <input type="search" placeholder="Søg i registre, dagbøger, steder…" class="search-input">
      <button type="submit" class="search-btn">Søg</button>
    </form>
    <span id="js-cart-badge"></span>
  </div>
</header>

<main>

  <div class="page-hero page-hero--sm">
    <div class="container">
      <nav class="breadcrumb" style="opacity:0.72;margin-bottom:6px">
        <a href="../index.html">Forside</a>
        <span class="breadcrumb__sep">›</span>
        <a href="../diaries.html">Dagbøger</a>
        <span class="breadcrumb__sep">›</span>
        <span class="breadcrumb__current">Bind {html.escape(vol)}, side {html.escape(page)}</span>
      </nav>
      <h1>Bind {html.escape(vol)}, side {html.escape(page)}</h1>
      <p>Dagbogsside · Det Kongelige Bibliotek</p>
      {kb_link_html}
      <div id="js-cart-toggle" style="margin-top:8px"></div>
      <div class="page-hero__meta">
        <span>{html.escape(date_str)}</span>
        <span>Bind {html.escape(vol)} · Side {html.escape(page)}</span>
        <span>{html.escape(pid)}</span>
        <span>{len(entity_ids)} registerposter</span>
      </div>
    </div>
  </div>

  <section class="section">
    <div class="container">
      <div class="entity-layout">

        <div class="entity-main">
{diary_section}

          <div>
            <h2 class="section-title">Dagbogsmetadata</h2>
            <table class="info-table">
              <tr><td>ID</td><td>{html.escape(pid)}</td></tr>
              <tr><td>Bind</td><td>{html.escape(vol)}</td></tr>
              <tr><td>Side</td><td>{html.escape(page)}</td></tr>
              <tr><td>Dato</td><td>{html.escape(date_str)}</td></tr>
              <tr><td>Tekst</td><td>{"Ja" if has_text else "Ikke transskriberet"}</td></tr>
              <tr><td>Registerposter</td><td>{len(entity_ids)}</td></tr>
            </table>
          </div>

          <div>
            <h2 class="section-title">Bladr i dagbøgerne</h2>
            <div style="display:flex;flex-direction:column;gap:8px;font-size:0.83rem">
              {prev_link}
              {next_link}
              <a href="../diaries.html" style="margin-top:6px;font-size:0.8rem;color:var(--color-text-muted)">Alle dagbogsider</a>
            </div>
          </div>

        </div>

        <aside class="entity-sidebar">

          <div class="info-block">
            <div class="info-block__header">Registerposter</div>
            <div class="info-block__body">
              <p style="font-size:0.83rem;color:var(--color-text-muted);margin-bottom:var(--sp4)">
                {len(entity_ids)} registerposter knyttet til {html.escape(pid)}
              </p>
              <div class="entity-refs">
{refs_html}
              </div>
            </div>
          </div>

        </aside>

      </div>
    </div>
  </section>

</main>

<footer class="site-footer">
  <div class="container">
    Prototype v0.2 &nbsp;·&nbsp; Data: H.C. Andersen Dagbogsregister — Det Kongelige Bibliotek &nbsp;·&nbsp; <a href="../om.html" style="color:inherit">Vores kilder</a>
  </div>
</footer>

<script src="../js/cart.js"></script>
<script>
if (typeof Cart !== 'undefined') {{
  Cart.mountBadge(document.getElementById('js-cart-badge'));
  Cart.mountToggle(document.getElementById('js-cart-toggle'), 'diary', {pid_js}, {heading_js});
}}
</script>
<script src="../js/nav.js"></script>
</body>
</html>
'''


def main():
    print("Loading data…")
    ents  = load_entities()
    diary = load_diary()
    refs  = load_references()
    kb    = load_kb_links()

    all_pages = sorted_pages(refs)
    total = len(all_pages)
    print(f"  {total} unique diary pages to generate")
    print(f"  {len([p for p in all_pages if p in diary])} pages with transcribed text")
    have_kb = len([p for p in all_pages if page_id(*p) in kb])
    print(f"  {have_kb} pages with a Det Kgl. Bibliotek link"
          + ("" if kb else "  (kb_diary_links.csv not built — links omitted)"))

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    written = 0
    for idx, (vol, page) in enumerate(all_pages):
        if not vol or not page:
            continue
        pid = page_id(vol, page)
        out_path = OUT_DIR / f"{pid}.html"
        html_content = render_page(vol, page, ents, diary, refs, all_pages, idx, kb)
        out_path.write_text(html_content, encoding="utf-8")
        written += 1
        if written % 500 == 0:
            print(f"  … {written}/{total}", flush=True)

    print(f"Done. {written} files written to {OUT_DIR.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()
