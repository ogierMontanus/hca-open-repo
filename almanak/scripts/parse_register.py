#!/usr/bin/env python3
"""
parse_register.py — konvertér Værkregister (trykt s. 328–338) og
Personregister (s. 339–388) i H.C. Andersens Almanakker 1833–1873
(DSL 1990) fra PDF'ens ABBYY-tekstlag til tre CSV-filer med
almanak-lokale registernøgler.

Nøgler (lokale for almanakken, ikke Reg-id'er fra dagbogsregistrene):
  ALMP0001 …   personregisteropslag, i trykkets rækkefølge
  ALMW0001 …   værkregisteropslag, i trykkets rækkefølge
Nøglerne er FORELØBIGE: de følger rækkefølgen i dette OCR-lag. Når en ny OCR
erstatter det (almanak/docs/implementeringsplan.md, trin 1), skal nøglerne
frigives først efter en crosswalk, så annotationer, der henviser til dem,
ikke mister deres mål.

Målt layout (PDF-side = trykt side + 12; PDF 340–400):
  * Begge registre har to spalter pr. side: venstre x≈46, højre x≈199.
  * Et opslag begynder ved spaltens grundlinje (≤ +3 pt); fortsættelseslinjer
    er indrykket ≈ 8–10 pt. Linjer indrykket mere end det er overskrifter
    i værkregistret (»Eventyr«, »Enkelte eventyr alfabetisk« …).
  * Levende kolumnetitel (y0 < 52) og folio (y1 > 495) udelades.

Et opslag er: overskriftsord, evt. beskrivelse, derefter henvisninger
»år d.m, d.m. år d.m …« (også »Bagsiden af <måned>«, »Bag i almanakken«,
»Foran i almanakken«). »+« foran henvisningerne (OCR: »4-«, »-I-«, »-r«)
betyder, at personen ikke findes i Dagbøgernes personregister (bd. XI).

OCR-forvekslinger i tal håndteres, men ikke gættes: et årstal eller en dato,
der ikke kan læses entydigt, får `valid=0` og beholdes i `raw`.

Output (committes; foreløbige og ikke korrekturlæst):
  almanak/data/register/almanak_register_persons.csv
  almanak/data/register/almanak_register_works.csv
  almanak/data/register/almanak_register_refs.csv

Brug (PowerShell, fra repo-roden):
  python almanak/scripts/parse_register.py --pdf "C:\\...\\andersen-hc_almanakker.pdf" --cache almanak/data/cache/register_lines.json
"""

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "almanak" / "data" / "register"
WORK_PAGES = range(340, 351)      # 1-baserede PDF-sider
PERSON_PAGES = range(351, 401)
PAGE_OFFSET = 12

MONTHS = {"januar": 1, "februar": 2, "marts": 3, "april": 4, "maj": 5, "juni": 6, "juli": 7, "august": 8,
          "september": 9, "oktober": 10, "november": 11, "december": 12}
MONTH_RE = "|".join(MONTHS)

# OCR-forvekslinger i tal
DIG = str.maketrans({"i": "1", "I": "1", "l": "1", "j": "1", "h": "1", "o": "0", "O": "0", "g": "9", "q": "9", "z": "2", "Z": "2", "&": "8"})
YEAR_CHARS = "0-9iIljhoOgqzZ&"
YEAR_TOK = re.compile(rf"^[{YEAR_CHARS}]{{4}}$")
DM_TOK = re.compile(rf"^([{YEAR_CHARS}]{{1,2}})[.,\-]\s?([{YEAR_CHARS}]{{1,2}})[.,]?$")
PLUS = re.compile(r"(?<!\w)(?:4-|-I-|-r|-i-|\+)(?=[\s.]|$)")


def read_lines(pdf, cache):
    if cache and Path(cache).exists():
        return {int(k): v for k, v in json.loads(Path(cache).read_text(encoding="utf-8")).items()}
    try:
        import fitz
    except ImportError:
        sys.exit("PyMuPDF kræves:  pip install pymupdf")
    doc = fitz.open(pdf)
    pages = {}
    for n in list(WORK_PAGES) + list(PERSON_PAGES):
        L = []
        for b in doc[n - 1].get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                t = "".join(s["text"] for s in l["spans"])
                if t.strip():
                    L.append({"bbox": [round(x, 1) for x in l["bbox"]], "t": t})
        pages[n] = L
    if cache:
        Path(cache).parent.mkdir(parents=True, exist_ok=True)
        Path(cache).write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    return pages


def join_lines(parts):
    out = ""
    for p in parts:
        p = p.rstrip()
        if not out:
            out = p
        elif out.endswith("\xad"):
            out = out[:-1] + p.lstrip()
        elif out.endswith("-") and p[:1].islower() and not out.endswith(" -"):
            out = out[:-1] + p.lstrip()
        else:
            out += " " + p.lstrip()
    return re.sub(r"\s+", " ", out.replace("\xad", "")).strip()


def starts_with_ref(t):
    tk = t.split()
    return len(tk) >= 2 and bool(YEAR_TOK.match(tk[0].rstrip(",."))) and bool(DM_TOK.match(tk[1].rstrip(",")))


def entries_of(pages, page_range, headings):
    """[(pdf_page, section, text)] i trykkets rækkefølge. `headings`: værkregistret har
    centrerede overskrifter; en linje der begynder med et årstal + dato hører til
    det foregående opslag (eller til overskriften, hvis intet opslag er åbent)."""
    ents, section = [], ""
    cur, prev_heading = None, False
    for n in page_range:
        lines = [l for l in pages.get(n, []) if l["bbox"][1] > 52 and l["bbox"][3] < 495]
        if n == 351:  # indledning til personregistret
            lines = [l for l in lines if l["bbox"][1] > 190]
        if n == 340:  # titel og forklaring til værkregistret
            lines = [l for l in lines if l["bbox"][1] > 140]
        cols = [[l for l in lines if l["bbox"][0] < 190], [l for l in lines if l["bbox"][0] >= 190]]
        for ci, col in enumerate(cols):
            base = 46.0 if ci == 0 else 199.6
            col.sort(key=lambda l: l["bbox"][1])
            for l in col:
                x, t = l["bbox"][0], l["t"].strip()
                ref_line = starts_with_ref(t)
                if x <= base + 3.5 and not ref_line and (t[:1].isalpha() or t[:1] in "»«(\"'"):
                    if cur:
                        ents.append(cur)
                    cur, prev_heading = {"pdf_page": n, "section": section, "parts": [t]}, False
                elif x > base + 13 and headings and not ref_line and re.fullmatch(r"[/ ]*[A-Za-zÆØÅæøå .,\-]{3,45}", t):
                    if cur:
                        ents.append(cur)
                        cur = None
                    section = (section + " " + t) if prev_heading else t
                    prev_heading = True
                elif cur:
                    cur["parts"].append(t)
                    prev_heading = False
                elif ref_line and headings:  # henvisninger direkte under en overskrift
                    cur, prev_heading = {"pdf_page": n, "section": section, "parts": [section.replace("/ ", "").strip() + ".", t]}, False
    if cur:
        ents.append(cur)
    return [(e["pdf_page"], e["section"], join_lines(e["parts"])) for e in ents]


def to_int(tok, hi):
    t = re.sub(r"[\s]", "", tok).translate(DIG)
    return int(t) if t.isdigit() and 1 <= int(t) <= hi else None


def parse_year(tok):
    t = tok.translate(DIG)
    if t.isdigit() and 1833 <= int(t) <= 1873:
        return int(t)
    return None


def split_refs(text):
    """-> (head, not_in_xi, [ref dicts]). Henvisningerne begynder ved første årstal
    efterfulgt af en dato, eller ved »Bagsiden af«, »Bag i almanakken«, »Foran i almanakken«."""
    toks = text.split(" ")
    start = None
    for i, t in enumerate(toks):
        tt = t.rstrip(",.")
        nxt = toks[i + 1] if i + 1 < len(toks) else ""
        if YEAR_TOK.match(tt) and DM_TOK.match(nxt.rstrip(",")) and (parse_year(tt) or tt[:2].lower() in ("18", "i8", "l8", "&8")):
            start = i
            break
        if tt.lower() in ("bagsiden", "bag", "foran") and re.match(r"(?i)(af|i)$", nxt.rstrip(".,")):
            start = i
            break
        if DM_TOK.match(tt) and i > 0 and YEAR_TOK.match(toks[i - 1].rstrip(",.")):
            start = i - 1
            break
    head = " ".join(toks[:start]) if start is not None else text
    tail = " ".join(toks[start:]) if start is not None else ""
    not_in_xi = bool(PLUS.search(head)) or bool(PLUS.search(tail[:6]))
    head = PLUS.sub("", head).strip(" ,;")
    refs, year, year_raw = [], None, ""
    tl = tail.replace("\xad", "")
    for m in re.finditer(
            rf"(?i)(?P<pos>(?:bagsiden af|bag i almanakken+|foran i almanakken)\s*(?P<mon>{MONTH_RE})?)"
            rf"|(?P<yr>(?<![\w.]){'[' + YEAR_CHARS + ']'}{{4}})(?![\w])"
            rf"|(?P<dm>(?<![\w])[{YEAR_CHARS}]{{1,2}}\s?[.,\-]\s?[{YEAR_CHARS}]{{1,2}}(?![\w]))", tl):
        if m.group("yr"):
            year_raw = m.group("yr")
            year = parse_year(year_raw)
        elif m.group("pos"):
            p = m.group("pos").lower()
            kind = "bagside" if p.startswith("bagsiden") else "bag" if p.startswith("bag i") else "foran"
            refs.append(dict(year=year, year_raw=year_raw, day="", month=MONTHS.get((m.group("mon") or "").lower(), ""), kind=kind,
                             raw=m.group("pos"), valid=int(year is not None)))
        else:
            raw = m.group("dm")
            a, b = re.split(r"[.,\-]\s?", raw.strip(" ."), maxsplit=1)
            d, mo = to_int(a, 31), to_int(b, 12)
            refs.append(dict(year=year, year_raw=year_raw, day=d or "", month=mo or "", kind="date", raw=raw,
                             valid=int(bool(year and d and mo))))
    return head, not_in_xi, refs


def label_of(head):
    h = head
    h = re.split(r"\s\(", h, maxsplit=1)[0]
    parts = h.split(", ")
    if len(parts) > 2 and "," in parts[0] + ",":
        h = ", ".join(parts[:2])
    return h.strip(" ,.;")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--pdf", type=Path, default=os.environ.get("HCA_ALMANAK_PDF"))
    ap.add_argument("--cache", type=Path, default=REPO_ROOT / "almanak" / "data" / "cache" / "register_lines.json")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    if not args.cache.exists() and not (args.pdf and Path(args.pdf).exists()):
        sys.exit("Angiv --pdf eller sæt HCA_ALMANAK_PDF")
    pages = read_lines(args.pdf, args.cache)
    args.out.mkdir(parents=True, exist_ok=True)

    persons, works, refs_out = [], [], []
    for kind, rng, two_col, prefix in (("person", PERSON_PAGES, False, "ALMP"), ("work", WORK_PAGES, True, "ALMW")):
        for i, (pg, section, text) in enumerate(entries_of(pages, rng, two_col), 1):
            head, not_in_xi, refs = split_refs(text)
            see = ""
            m = re.search(r"(?:,|\.)?\s*s[ec](?: i reglen| også)?\s*:\s*(.*)$", head)
            if m:
                see = m.group(1).strip(" .")
                head = head[:m.start()].strip(" ,.")
            m2 = re.search(r"\((?:ca\.\s*)?(\d{4})\s*[-–—]\s*(\d{4})\)", head)
            rid = f"{prefix}{i:04d}"
            row = dict(reg_id=rid, label=label_of(head), description=head, see=see, not_in_xi=int(not_in_xi),
                       birth=m2.group(1) if m2 else "", death=m2.group(2) if m2 else "",
                       n_refs=len(refs), pdf_page=pg, print_page=pg - PAGE_OFFSET, raw=text)
            if kind == "work":
                row["section"] = section
                works.append(row)
            else:
                persons.append(row)
            for r in refs:
                refs_out.append(dict(reg_id=rid, register=kind, **r))

    def dump(name, rows):
        with open(args.out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    dump("almanak_register_persons.csv", persons)
    dump("almanak_register_works.csv", works)
    dump("almanak_register_refs.csv", refs_out)
    valid = sum(r["valid"] for r in refs_out)
    print(f"personopslag: {len(persons)}, værkopslag: {len(works)}, henvisninger: {len(refs_out)} (valide: {valid})")
    print(f"opslag uden henvisning: personer {sum(1 for p in persons if not p['n_refs'])}, værker {sum(1 for w in works if not w['n_refs'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
