#!/usr/bin/env python3
"""
compare_sources.py — undersøgelsesværktøj: sammenlign databasens
almanakposter (extract_db.py) med PDF'ens dagsposter
(extract_pdf_entries.py) dato for dato.

Sammenligningen er en kollation af to vidner til samme tekst — den trykte
udgave 1990, set gennem henholdsvis et manuelt indtastet lag (databasen,
importeret 2006) og et maskinelt OCR-lag (ABBYY, 2023). Ingen af dem er
facit; facit er sidebilledet. Scriptet finder derfor kun steder, hvor de
to lag er uenige, og klassificerer dem grovt.

Ligheden måles to gange:
  ratio_strict  efter Unicode-normalisering, ½ -> 1/2, † -> f, citationstegn
  ratio_loose   desuden små bogstaver, uden tegnsætning og med 1/i, 0/o
                foldet (de hyppigste OCR-forvekslinger af gammeldags tal)

Output (gitignoreret):
  almanak/data/extracted/aligned.csv            én række pr. dato i en af kilderne
  almanak/data/extracted/date_discrepancies.csv DB-poster hvis tekst står på en
                                                anden dato i PDF'en (±7 dage)
  almanak/data/extracted/letter_direction.csv   "Brev til" i den ene kilde,
                                                "Brev fra" i den anden
  almanak/data/extracted/summary.json           tællinger brugt i kildeanalysen

Brug (PowerShell, fra repo-roden):
  python almanak/scripts/analysis/compare_sources.py
"""

import argparse
import collections
import csv
import datetime
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EXTRACTED = REPO_ROOT / "almanak" / "data" / "extracted"


def norm(s):
    s = unicodedata.normalize("NFC", s).replace("\xad", "")
    s = s.replace("½", "1/2").replace("ß", "B").replace("†", "f")
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[»«”“\"]", '"', s)
    return re.sub(r"\s+", " ", s).strip()


def loose(s):
    s = re.sub(r"[^\wæøåäöü ]", "", norm(s).lower())
    return re.sub(r"\s+", " ", s.replace("1", "i").replace("0", "o")).strip()


def ratio(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def tokens(s):
    s = norm(s).replace("–", "-")
    return re.findall(r"\w+|[^\w\s]", s)


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--db", type=Path, default=EXTRACTED / "almanak_db.csv")
    ap.add_argument("--pdf", type=Path, default=EXTRACTED / "almanak_pdf_entries.csv")
    ap.add_argument("--outdir", type=Path, default=EXTRACTED)
    args = ap.parse_args()
    db = {r["Dato"]: r for r in csv.DictReader(open(args.db, encoding="utf-8"))}
    pdf = {}
    for r in csv.DictReader(open(args.pdf, encoding="utf-8")):
        pdf.setdefault(r["date"], r)  # første forekomst ved (sjældne) dubletter

    aligned = []
    for d in sorted(set(db) | set(pdf)):
        a, b = db.get(d), pdf.get(d)
        row = dict(date=d, in_db=bool(a), in_pdf=bool(b),
                   pdf_page=b["pdf_page"] if b else "", print_page=b["print_page"] if b else "",
                   how=b["how"] if b else "", ratio_strict="", ratio_loose="", token_diff_ops="",
                   db_text=a["Tekst"] if a else "", pdf_text=b["text"] if b else "",
                   db_timestamp=a["Timestamp"] if a else "")
        if a and b:
            row["ratio_strict"] = round(ratio(norm(a["Tekst"]), norm(b["text"])), 3)
            row["ratio_loose"] = round(ratio(loose(a["Tekst"]), loose(b["text"])), 3)
            ops = difflib.SequenceMatcher(None, tokens(a["Tekst"]), tokens(b["text"]),
                                          autojunk=False).get_opcodes()
            row["token_diff_ops"] = sum(1 for o in ops if o[0] != "equal")
        aligned.append(row)
    write_csv(args.outdir / "aligned.csv", aligned)

    # DB-tekst der står på en anden dato i PDF'en
    pdf_by_day = {}
    for b in pdf.values():
        try:
            pdf_by_day[datetime.date.fromisoformat(b["date"])] = b
        except ValueError:
            pass
    disc = []
    for a in db.values():
        la = loose(a["Tekst"])
        if not la:
            continue
        same = ratio(la, loose(pdf[a["Dato"]]["text"])) if a["Dato"] in pdf else 0.0
        if same >= 0.9:
            continue
        try:
            d0 = datetime.date.fromisoformat(a["Dato"])
            near = [d0 + datetime.timedelta(k) for k in range(-7, 8) if k]
        except ValueError:  # fx 1849-04-00: søg i hele måneden
            near = [k for k in pdf_by_day if k.strftime("%Y-%m") == a["Dato"][:7]]
        best = None
        for dd in near:
            b = pdf_by_day.get(dd)
            if b:
                rt = ratio(la, loose(b["text"]))
                if rt > max(0.75, same + 0.2) and (best is None or rt > best[1]):
                    best = (b, rt)
        if best or a["Dato"] not in pdf:
            disc.append(dict(db_date=a["Dato"], same_date_ratio=round(same, 2),
                             pdf_date=best[0]["date"] if best else "",
                             pdf_ratio=round(best[1], 2) if best else "",
                             pdf_page=best[0]["pdf_page"] if best else "",
                             print_page=best[0]["print_page"] if best else "",
                             pdf_how=best[0]["how"] if best else "",
                             db_text=a["Tekst"][:80]))
    write_csv(args.outdir / "date_discrepancies.csv", disc)

    swaps = []
    for r in aligned:
        if r["in_db"] and r["in_pdf"]:
            x = re.findall(r"Brev (til|fra)", r["db_text"])
            y = re.findall(r"Brev (til|fra)", r["pdf_text"])
            if len(x) == len(y) and x != y:
                swaps.append(dict(date=r["date"], print_page=r["print_page"],
                                  db=" ".join(x), pdf=" ".join(y), db_text=r["db_text"][:80]))
    write_csv(args.outdir / "letter_direction.csv", swaps)

    both = [r for r in aligned if r["in_db"] and r["in_pdf"]]

    def count(rows, key, pat):
        return sum(len(re.findall(pat, r[key])) for r in rows)

    db_rows = [r for r in aligned if r["in_db"]]
    pdf_rows = [r for r in aligned if r["in_pdf"]]
    summary = {
        "db_rows": len(db), "pdf_entries": len(pdf), "both": len(both),
        "db_only": sum(1 for r in aligned if r["in_db"] and not r["in_pdf"]),
        "pdf_only": sum(1 for r in aligned if r["in_pdf"] and not r["in_db"]),
        "loose_ratio_ge": {str(t): sum(1 for r in both if r["ratio_loose"] >= t)
                           for t in (1.0, 0.98, 0.95, 0.9, 0.8)},
        "strict_identical": sum(1 for r in both if r["ratio_strict"] == 1.0),
        "token_identical": sum(1 for r in both if r["token_diff_ops"] == 0),
        "token_diff_ops_total": sum(r["token_diff_ops"] for r in both),
        "date_discrepancies": len(disc),
        "letter_direction_conflicts": len(swaps),
        "markers": {
            "trykte_almanaktekst_db": count(db_rows, "db_text", r"(?i)\[?\s*i (den )?trykte? al"),
            "trykte_almanaktekst_pdf": count(pdf_rows, "pdf_text", r"(?i)\[(I|Under) (den )?trykte? al"),
            "square_brackets_db": count(db_rows, "db_text", r"\["),
            "square_brackets_pdf": count(pdf_rows, "pdf_text", r"\["),
            "html_in_db": count(db_rows, "db_text", r"<[a-z]+"),
        },
    }
    (args.outdir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
