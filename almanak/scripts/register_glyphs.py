#!/usr/bin/env python3
"""
register_glyphs.py — optisk aflæsning af tegn i almanakregistrene, som OCR-tekstlaget ikke kan læse.

Divisionstegnet »÷« har to betydninger i 1990-udgavens registre (PDF s. 340–400):
  Værkregister  »÷ ved en titel betegner, at den ikke findes i bibliografien« (Birger Frank Nielsen 1942).
  Personregister »÷ efter et navn, med eller uden oplysninger, betegner, at personen ikke forekommer i
                 [personregistret i H.C. Andersens Dagbøger, bd. XI, 1977], eller ikke er identificeret.«

OCR'en læser tegnet som »4-«, »-r«, »+«, »-5-«, »-4-«, »4"«, »-I-«, »-i-« — eller springer det helt over
(»sproglærer. . 1843 31.7.«). Derfor findes tegnet her i billedet: siderne gengives i 400 dpi, og et
»÷« klippet fra s. 369 (PDF) søges med normaliseret krydskorrelation. Scorerne skiller skarpt: ingen
træf mellem 0,80 og 0,88 i de 61 sider; tærsklen er 0,86 (se docs i almanak/docs/registertegn.md).

Uddata (committes, så parse_register.py kan bruge dem uden PDF'en):
  almanak/data/register/register_divsign.csv   pdf_page, x0, y0, x1, y1 (PDF-punkter), score, ocr (tekstlaget under tegnet)

Brug (PowerShell, fra repo-roden; kræver PyMuPDF og opencv-python):
  python almanak/scripts/register_glyphs.py --pdf $env:HCA_ALMANAK_PDF
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "almanak" / "data" / "register" / "register_divsign.csv"
PAGES = range(340, 401)
DPI = 400
THRESHOLD = 0.86
TEMPLATE = (369, (159.5, 258.9, 166.3, 265.9))   # »÷« foran »1842 30.10.« (Løssøe), PDF-punkter


def _render(pdf, page):
    import fitz
    import numpy as np
    pix = pdf[page - 1].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)


def template(pdf):
    import numpy as np
    z = DPI / 72
    page, (x0, y0, x1, y1) = TEMPLATE
    crop = _render(pdf, page)[int(y0 * z):int(y1 * z), int(x0 * z):int(x1 * z)]
    ys, xs = np.where(crop < 128)
    return crop[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def find_divsigns(pdf, pages=PAGES, threshold=THRESHOLD):
    import cv2
    import numpy as np
    z = DPI / 72
    tpl = 255 - template(pdf).astype(np.float32)
    th, tw = tpl.shape
    out = []
    for p in pages:
        inv = 255 - _render(pdf, p).astype(np.float32)
        r = cv2.matchTemplate(inv, tpl, cv2.TM_CCOEFF_NORMED)
        ys, xs = np.where(r >= threshold)
        taken = []
        words = pdf[p - 1].get_text("words")
        for s, x, y in sorted(zip(r[ys, xs], xs, ys), reverse=True):
            if any(abs(x - a) < tw and abs(y - b) < th for a, b in taken):
                continue
            taken.append((x, y))
            bx = (x / z, y / z, (x + tw) / z, (y + th) / z)
            under = " ".join(w[4] for w in words if w[0] < bx[2] + 1 and bx[0] - 1 < w[2] and w[1] < bx[3] and bx[1] < w[3])
            out.append(dict(pdf_page=p, x0=round(bx[0], 1), y0=round(bx[1], 1), x1=round(bx[2], 1), y1=round(bx[3], 1),
                            score=round(float(s), 3), ocr=under))
    return sorted(out, key=lambda m: (m["pdf_page"], m["x0"] >= 190, m["y0"]))


def load(path=OUT):
    """{pdf_page: [(x0, y0, x1, y1)]} eller None, hvis aflæsningen ikke er kørt."""
    if not Path(path).exists():
        return None
    out = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        out.setdefault(int(r["pdf_page"]), []).append(tuple(float(r[k]) for k in ("x0", "y0", "x1", "y1")))
    return out


def assign(signs, entry_boxes, col_split=190.0, max_dy=4.0):
    """Antal ÷ pr. opslag. entry_boxes: [[(pdf_page, bbox), ...] pr. opslag]. Hvert tegn gives til den linje i samme
    spalte, hvis lodrette midte ligger nærmest (højst max_dy pt) — ikke efter x, for når OCR har tabt tegnet,
    begynder linjens bbox først ved årstallet. Returnerer (tæller pr. opslag, tegn uden linje)."""
    lines = {}
    for i, boxes in enumerate(entry_boxes):
        for page, (x0, y0, x1, y1) in boxes:
            lines.setdefault((page, x0 >= col_split), []).append(((y0 + y1) / 2, i))
    counts, orphans = [0] * len(entry_boxes), []
    for page, ss in (signs or {}).items():
        for a, b, c, d in ss:
            cands = lines.get((page, (a + c) / 2 >= col_split), [])
            cy = (b + d) / 2
            best = min(cands, key=lambda t: abs(t[0] - cy), default=None)
            above = max((t for t in cands if t[0] < cy), key=lambda t: t[0], default=None)
            if best and abs(best[0] - cy) <= max_dy:
                counts[best[1]] += 1
            elif above and cy - above[0] <= 3 * max_dy:     # tegnet står alene på en linje, som tekstlaget ikke har
                counts[above[1]] += 1
            else:
                orphans.append((page, (a, b, c, d)))
    return counts, orphans


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--pdf", type=Path, default=os.environ.get("HCA_ALMANAK_PDF"))
    args = ap.parse_args()
    if not args.pdf or not Path(args.pdf).exists():
        sys.exit("Angiv --pdf eller sæt HCA_ALMANAK_PDF")
    import fitz
    signs = find_divsigns(fitz.open(args.pdf))
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["pdf_page", "x0", "y0", "x1", "y1", "score", "ocr"])
        w.writeheader()
        w.writerows(signs)
    print(f"{len(signs)} divisionstegn fundet (score >= {THRESHOLD}) -> {OUT}")


if __name__ == "__main__":
    main()
