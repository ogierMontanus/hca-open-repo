#!/usr/bin/env python3
"""
extract_pdf_entries.py — undersøgelsesværktøj: segmentér ABBYY-tekstlaget
i andersen-hc_almanakker.pdf (Rønlevs digitalisering af H.C. Andersens
Almanakker 1833–1873, udg. Helga Vang Lauridsen og Kirsten Weber, DSL 1990)
i daterede dagsposter.

Formålet er at kunne sammenligne PDF'en med databasetabellen `almanak`
dag for dag (compare_sources.py). Det er IKKE en produktionsparser: den
retter ikke OCR-tekst, og poster den ikke kan placere, havner i
*_other.json til manuel gennemsyn.

Målt layout (PDF 400 s., 387 x 548,75 pt, ét JBIG2-billede + ABBYY-tekst
pr. side):
  * PDF-side 13–339 = trykt s. 1–327 (trykt side = PDF-side − 12).
    PDF 340–350 = Værkregister (s. 328–338), 351–400 = Personregister.
  * Levende kolumnetitel y < 58 ("Februar 1840"); kun årstallet bruges —
    måneden i kolumnetitlen følger ikke sidens første post.
  * Årsoverskrift: kursiv, centreret ("1840."); OCR'en mangler den på
    flere sider (1833, 1838, 1854, 1855), så kolumnetitlens år er reserve.
  * Månedsoverskrift: kursiv, centreret ("Februar.").
  * Dagspost: ugedag (MA TI ON TO FR LØ SØ, kapitæler) + dagnummer i
    venstre kolonne x < 62; ombrudte linjer x ≈ 76–80.
  * 1834 og 1837 har ingen ugedage ("15. forlod Florents.", "den 3die").
  * Januar 1838 har ugedag og dagnummer som separate tekstlinjer.

Dagnummeret er sat med gammeldags tal og fejllæses ofte (1→i, 18→"tå",
11→"ii"). Derfor bruges ugedagen som kontrol: blandt kalenderens datoer
efter forrige post med samme ugedag vælges den, der ligger nærmest
OCR-tallet (Levenshtein). Metoden noteres pr. post i kolonnen `how`:
  ocr+weekday          OCR-tal og ugedag stemmer med kalenderen
  ocr_weekday_mismatch OCR-tallet passer i rækkefølgen, men ikke med
                       ugedagen — trykket kan selv have forkert ugedag
                       (fx "FR 28" for onsdag 28.12.1842)
  weekday_inferred     OCR-tallet var ulæseligt; dato udledt af ugedag
  ocr_no_weekday       1834/1837-format uden ugedag
  order_break          ingen kandidat — rækkefølgen brudt (efterses)

Output (gitignoreret):
  almanak/data/extracted/almanak_pdf_entries.csv
      date, pdf_page, print_page, weekday_print, day_raw, how, text
  almanak/data/extracted/almanak_pdf_entries_other.json
      udaterede linjer (adresser, "Bag i almanakken", vers …) + problemer

Brug (PowerShell, fra repo-roden; tager ~1 min — tekstlaget er langsomt
at læse pga. JBIG2-billederne; --cache gør gentagne kørsler hurtige):
  python almanak/scripts/analysis/extract_pdf_entries.py --pdf "C:\\...\\andersen-hc_almanakker.pdf"
  $env:HCA_ALMANAK_PDF = "C:\\...\\andersen-hc_almanakker.pdf"
  python almanak/scripts/analysis/extract_pdf_entries.py --cache almanak/data/cache/lines.json
"""

import argparse
import calendar
import collections
import csv
import datetime
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = REPO_ROOT / "almanak" / "data" / "extracted" / "almanak_pdf_entries.csv"

BODY_FIRST, BODY_LAST = 13, 339   # 1-baserede PDF-sider med almanakteksten
PAGE_OFFSET = 12                  # trykt side = PDF-side - 12

MONTHS = {m: i + 1 for i, m in enumerate(
    ["januar", "februar", "marts", "april", "maj", "juni", "juli", "august",
     "september", "oktober", "november", "december"])}
MONTHS.update({"mai": 5, "october": 10, "marls": 3})   # trykvarianter og OCR

# Ugedagsforkortelser inkl. målte OCR-varianter (L0/S0 = LØ/SØ i kapitæler,
# "må" = ma, "ro"/"tø" = to, "ri" = ti).
WEEKDAYS = {"ma": 0, "ti": 1, "on": 2, "to": 3, "fr": 4, "lø": 5, "sø": 6,
            "lo": 5, "so": 6, "1ø": 5, "l0": 5, "s0": 6, "lö": 5, "sö": 6,
            "må": 0, "ro": 3, "tø": 3, "ri": 1}

# Gammeldags tal læst som bogstaver
DIGIT = str.maketrans({"i": "1", "I": "1", "l": "1", "!": "1", "o": "0", "O": "0",
                       "’": "1", "'": "1", ">": "1", "‘": "1", "$": "5", "S": "5",
                       "å": "8", "B": "8", "j": "1", "J": "1", "z": "2", "Z": "2",
                       "g": "9", "t": "1", "\ufffd": "1"})
YEAR_DIGIT = str.maketrans({"i": "1", "l": "1", "o": "0", "O": "0", "g": "9", "y": "7",
                            "?": "7", "’": "1", "‘": "1", "\ufffd": "1", "^": "18"})

ENTRY_RE = re.compile(r"^([A-Za-zÆØæøöå01]{2})\s+(\S{1,3}(?:\s\d)?)\s+(.*)$")
NOWEEKDAY_RE = re.compile(r"^(?:den\s+)?(\S{1,3}?)(?:die|de|te)?[.,]\s+(.*)$")


def ocrnum(tok):
    t = re.sub(r"[\s.,:;\-]", "", tok).translate(DIGIT)
    return int(t) if t.isdigit() and 0 < int(t) <= 31 else None


def yearof(t):
    t = re.sub(r"[\s.\-]", "", t).translate(YEAR_DIGIT)
    m = re.search(r"(\d{3,4})$", t)
    if not m:
        return None
    y = m.group(1)
    if len(y) == 3:
        y = "1" + y if y.startswith("8") else "18" + y[-2:]
    return int(y) if 1832 < int(y) < 1874 else None


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def read_lines(pdf_path, cache):
    """{pdf_page: [{bbox, t, font}]} for body pages; cached as JSON if asked."""
    if cache and cache.exists():
        return {int(k): v for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}
    try:
        import fitz  # PyMuPDF
    except ImportError:
        sys.exit("PyMuPDF kræves:  pip install pymupdf")
    doc = fitz.open(pdf_path)
    pages = {}
    for n in range(BODY_FIRST, BODY_LAST + 1):
        lines = []
        for b in doc[n - 1].get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                t = "".join(s["text"] for s in l["spans"]).replace("\xad", "-")
                if t.strip():
                    lines.append({"bbox": list(l["bbox"]), "t": t, "font": l["spans"][0]["font"]})
        pages[n] = lines
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    return pages


def visual_rows(lines):
    """Saml tekstlinjer til visuelle rækker efter grundlinje. Januar 1838 har
    fede ugedagsetiketter på egne linjer lidt forskudt fra posten."""
    ls = []
    for l in lines:
        x0, y0, _, y1 = l["bbox"]
        ls.append(dict(x=x0, y=y1, yc=(y0 + y1) / 2, t=l["t"].strip(),
                       it="-It" in l["font"], bold="-Bo" in l["font"]))
    ls.sort(key=lambda r: (r["y"], r["x"]))
    rows = []
    for ln in ls:
        if rows and (abs(rows[-1][-1]["y"] - ln["y"]) < 5.5 or
                     (ln["x"] > 60 and rows[-1][0]["bold"] and len(rows[-1]) < 3
                      and abs(rows[-1][0]["yc"] - ln["yc"]) < 9)):
            rows[-1].append(ln)
        else:
            rows.append([ln])
    out = []
    for r in rows:
        r.sort(key=lambda z: z["x"])
        out.append(dict(x=r[0]["x"], y=max(z["y"] for z in r),
                        t=" ".join(z["t"] for z in r), it=all(z["it"] for z in r)))
    return out


def segment(pages):
    entries, other, issues = [], [], []
    state = {"year": None, "month": None, "prevday": 0, "cur": None}

    def flush():
        if state["cur"]:
            entries.append(state["cur"])
            state["cur"] = None

    def new_year(y):
        flush()
        state.update(year=y, month=None, prevday=0)

    for pno in sorted(pages):
        rows = visual_rows(pages[pno])
        heading = [yearof(r["t"]) for r in rows
                   if r["it"] and r["y"] >= 58 and r["x"] > 100 and re.fullmatch(r"\S{3,6}", r["t"])]
        head = [yearof(r["t"].split()[-1] if len(r["t"].split()[-1]) >= 3 else r["t"])
                for r in rows if r["y"] < 58]
        head = [h for h in head if h]
        year = state["year"]
        # Kolumnetitlens år bruges kun, hvis siden ikke selv har en årsoverskrift,
        # og kun fremad (≤ +5): OCR læser "1853" som "1833" i kolumnetitlen p. 236.
        if not any(heading) and head and (year is None or year < head[0] <= year + 5):
            new_year(head[0])
        for r in rows:
            t = r["t"]
            if r["y"] < 58 or (r["y"] > 495 and len(t) <= 4):
                continue  # kolumnetitel / folio
            if r["it"] and r["x"] > 100 and re.fullmatch(r"\S{3,6}", t) and yearof(t):
                new_year(yearof(t))
                continue
            mm = re.fullmatch(r"([A-Za-zæøå]+)[.,]?", t)
            if mm and mm.group(1).lower() in MONTHS and r["x"] > 100:
                flush()
                state.update(month=MONTHS[mm.group(1).lower()], prevday=0)
                continue
            if t.startswith("[") and 60 < r["x"] < 200 and t.endswith("]") and len(t) < 70:
                flush()
                other.append(dict(pdf_page=pno, year=state["year"], kind="section_note", text=t))
                state["month"] = None
                continue
            m = ENTRY_RE.match(t) if r["x"] < 62 else None
            if m and m.group(2).isalpha() and len(m.group(2)) > 2:
                m = None
            m2 = NOWEEKDAY_RE.match(t) if r["x"] < 62 else None
            year, month, prevday = state["year"], state["month"], state["prevday"]
            if m and m.group(1).lower() in WEEKDAYS and year and month:
                flush()
                wd = WEEKDAYS[m.group(1).lower()]
                raw, body = m.group(2), m.group(3)
                n = ocrnum(raw)
                last = calendar.monthrange(year, month)[1]
                cands = [d for d in range(prevday + 1, last + 1)
                         if datetime.date(year, month, d).weekday() == wd]
                if n and n in cands:
                    day, how = n, "ocr+weekday"
                elif n and prevday < n <= last and (not cands or n - prevday <= 3 or n < cands[0]):
                    day, how = n, "ocr_weekday_mismatch"
                elif cands:
                    rawt = re.sub(r"[\s.,:;\-]", "", raw).translate(DIGIT)
                    day, how = min(cands, key=lambda d: (lev(str(d), rawt), d)), "weekday_inferred"
                elif n:
                    day, how = n, "order_break"
                    issues.append([pno, how, t])
                else:
                    issues.append([pno, "no_candidate", t])
                    continue
                state["prevday"] = day
                state["cur"] = dict(date=f"{year}-{month:02d}-{day:02d}", pdf_page=pno,
                                    print_page=pno - PAGE_OFFSET, weekday_print=m.group(1),
                                    day_raw=raw, how=how, text=body)
            elif m2 and month and year and ocrnum(m2.group(1)):
                flush()
                n = ocrnum(m2.group(1))
                last = calendar.monthrange(year, month)[1]
                how = "ocr_no_weekday" if prevday < n <= last else "order_break"
                state["prevday"] = n
                state["cur"] = dict(date=f"{year}-{month:02d}-{n:02d}", pdf_page=pno,
                                    print_page=pno - PAGE_OFFSET, weekday_print="",
                                    day_raw=m2.group(1), how=how, text=m2.group(2))
            elif state["cur"] and 60 < r["x"] < 100:
                cur = state["cur"]
                cur["text"] = (cur["text"][:-1] if cur["text"].endswith("-") else cur["text"] + " ") + t
            else:
                flush()
                other.append(dict(pdf_page=pno, year=state["year"], month=state["month"],
                                  kind="unattached", text=t))
    flush()
    return entries, other, issues


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--pdf", type=Path, default=os.environ.get("HCA_ALMANAK_PDF"))
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--cache", type=Path, default=None,
                    help="JSON-cache af tekstlinjerne (genbruges hvis den findes)")
    args = ap.parse_args()
    if not (args.cache and args.cache.exists()) and not (args.pdf and Path(args.pdf).exists()):
        sys.exit("Angiv --pdf eller sæt HCA_ALMANAK_PDF (se almanak/sources/README.md)")

    entries, other, issues = segment(read_lines(args.pdf, args.cache))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(entries[0].keys()))
        w.writeheader()
        w.writerows(entries)
    args.out.with_name(args.out.stem + "_other.json").write_text(
        json.dumps(dict(other=other, issues=issues), ensure_ascii=False, indent=1), encoding="utf-8")

    dates = collections.Counter(e["date"] for e in entries)
    print(f"{len(entries)} poster -> {args.out}")
    print("metode:", dict(collections.Counter(e["how"] for e in entries)))
    print("dubletdatoer:", [d for d, k in dates.items() if k > 1])
    print(f"udaterede linjer: {len(other)}; problemer: {len(issues)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
