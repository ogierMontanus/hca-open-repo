#!/usr/bin/env python3
"""
build_annotation_page.py — byg annotationssiden (almanak/annotation/template.html)
for udvalgte trykte sider i almanakudgaven 1990.

Indlæser:
  almanak/data/extracted/aligned.csv        post for post: PDF-tekst + DB-tekst (compare_sources.py)
  almanak/data/register/*.csv               personregister + værkregister (parse_register.py)
  PDF-siderne (sidebilleder, 105 dpi gråtone JPEG)

Pr. post udledes register-kandidater på to måder:
  ref    registret har en henvisning til netop denne dato (år læst som 1840 osv.)
  navn   postens tekst indeholder opslagets efternavn / værktitel, og opslaget har mindst
         én (valid) henvisning samme år — svagere, vist kursivt
Begge dele er forslag til annotatoren, ikke afgørelser; intet kobles automatisk.

Teksten er PDF-tekstlaget (ABBYY 2023) med de få rettelser i TEXT_FIXES, hver kontrolleret
mod sidebilledet. Alle øvrige OCR-afvigelser står uændret.

Output: almanak/annotation/out/almanak-annotering.html (gitignoreret)

Brug (PowerShell, fra repo-roden):
  python almanak/annotation/build_annotation_page.py --pdf "C:\\...\\andersen-hc_almanakker.pdf" --pages 35 36
"""

import argparse
import base64
import collections
import csv
import difflib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PAGE_OFFSET = 12  # PDF-side = trykt side + 12

# (mønster, erstatning, begrundelse) — kontrolleret mod sidebilledet s. 35–36
TEXT_FIXES = [
    (r"gal-$", "gal.", "ombrudt »gal.« læst med bindestreg"),
    (r"\biste\b", "1ste", "gammeldags 1 læst som i"),
    (r"L\. Muller", "L. Müller", "ü"),
    (r"8 B Daase", "8 ß Daase", "ß læst som B"),
]
DMKEY = "{}.{}"


def clean(text):
    t = text.strip()
    for pat, rep, _ in TEXT_FIXES:
        t = re.sub(pat, rep, t)
    return re.sub(r"\s+", " ", t)


def toks(s):
    return re.findall(r"[\wæøåäöüÆØÅ\[\]]+", s.replace("½", "1/2"))


def trivial(a, b):
    f = lambda s: re.sub(r"[\s\[\]]", "", s).lower()
    return f(a) == f(b)


def fold(s):
    return re.sub(r"[^a-zæøåäöü0-9 ]", "", s.lower())


def short(s, n):
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


def load_register():
    rd = lambda n: list(csv.DictReader(open(REPO_ROOT / "almanak" / "data" / "register" / n, encoding="utf-8")))
    persons, works, refs = rd("almanak_register_persons.csv"), rd("almanak_register_works.csv"), rd("almanak_register_refs.csv")
    reg = {}
    for p in persons:
        reg[p["reg_id"]] = dict(k="P", l=p["label"], d=short(p["description"][len(p["label"]):].strip(" ,."), 110), x=int(p["not_in_xi"]),
                                see=p["see"], pp=p["print_page"])
    for w in works:
        reg[w["reg_id"]] = dict(k="W", l=w["label"], d=short(w["section"], 60), x=0, see=w["see"], pp=w["print_page"])
    by_date, year_n = collections.defaultdict(set), collections.defaultdict(lambda: collections.Counter())
    for r in refs:
        if r["kind"] == "date" and r["valid"] == "1":
            by_date[(int(r["year"]), int(r["month"]), int(r["day"]))].add(r["reg_id"])
            year_n[r["reg_id"]][int(r["year"])] += 1
    return reg, by_date, year_n


def keys_of(info):
    """Søgeord, der skal findes i postens tekst: efternavn (personer) eller titel (værker)."""
    lab = re.split(r"\s\(", info["l"])[0]
    if info["k"] == "P":
        sn = lab.split(",")[0].strip()
        return [sn] if len(sn) >= 3 else []
    base = re.sub(r"[»«]", "", lab).strip()
    return [base] if len(base) >= 5 else []


def candidates(entry, reg, by_date, year_n):
    y, m, d = (int(x) for x in entry["date"].split("-"))
    text_f = fold(entry["text"])
    out = {}
    for rid in by_date.get((y, m, d), ()):
        info = reg[rid]
        found = any(re.search(rf"\b{re.escape(fold(k))}s?\b", text_f) for k in keys_of(info))
        out[rid] = "ref+navn" if found else "ref"
    for rid, info in reg.items():
        if rid in out or info["see"] or year_n[rid][y] == 0:
            continue
        if any(re.search(rf"\b{re.escape(fold(k))}s?\b", text_f) for k in keys_of(info)):
            out[rid] = "navn"
    order = {"ref+navn": 0, "ref": 1, "navn": 2}
    return sorted(([rid, b] for rid, b in out.items()), key=lambda c: (order[c[1]], c[0]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--pdf", type=Path, default=os.environ.get("HCA_ALMANAK_PDF"))
    ap.add_argument("--pages", type=int, nargs="+", default=[35, 36], help="trykte sidetal")
    ap.add_argument("--continued", nargs="*", default=["1840-02-09"], help="datoer for poster, der fortsætter på næste side")
    ap.add_argument("--aligned", type=Path, default=REPO_ROOT / "almanak" / "data" / "extracted" / "aligned.csv")
    ap.add_argument("--out", type=Path, default=HERE / "out" / "almanak-annotering.html")
    args = ap.parse_args()
    if not args.pdf or not Path(args.pdf).exists():
        sys.exit("Angiv --pdf eller sæt HCA_ALMANAK_PDF")
    try:
        import fitz
    except ImportError:
        sys.exit("PyMuPDF kræves:  pip install pymupdf")

    reg, by_date, year_n = load_register()
    al = {r["date"]: r for r in csv.DictReader(open(args.aligned, encoding="utf-8"))}
    pdf_pages = {pg + PAGE_OFFSET: pg for pg in args.pages}
    first_pdf = min(pdf_pages)
    entries = []
    for d in sorted(al):
        r = al[d]
        if not (r["pdf_page"].isdigit() and int(r["pdf_page"]) in pdf_pages and r["in_db"] == "True"):
            continue
        text = clean(r["pdf_text"])
        a, b = toks(text), toks(r["db_text"])
        diff = [[" ".join(a[i1:i2]), " ".join(b[j1:j2])]
                for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, [x.lower() for x in a], [x.lower() for x in b], autojunk=False).get_opcodes()
                if op != "equal"]
        diff = [x for x in diff if not trivial(*x)]
        e = dict(id="ALM-" + d, date=d, wd=_weekday(d), page=pdf_pages[int(r["pdf_page"])], cont=0, text=text, dbdiff=diff)
        e["c"] = candidates(e, reg, by_date, year_n)
        entries.append(e)
    for e in entries:  # poster, der fortsætter på næste side (kendes af PDF-segmenteringen ikke, angives)
        if e["date"] in args.continued:
            e["cont"] = e["page"] + 1

    # hele registret (uden krydshenvisninger) følger med, så rullelisten også kan foreslå poster, der ikke har en henvisning til siden
    regpage = {rid: {k: v for k, v in info.items() if k != "see"} for rid, info in reg.items() if not info["see"]}
    doc = fitz.open(str(args.pdf))
    imgs = {}
    for pg in args.pages:
        pix = doc[pg + PAGE_OFFSET - 1].get_pixmap(dpi=105, colorspace=fitz.csGRAY)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "p.jpg"
            pix.save(str(p), jpg_quality=68)
            imgs[pg] = "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode()

    tpl = (HERE / "template.html").read_text(encoding="utf-8")
    html = (tpl.replace("__ENTRIES__", json.dumps(entries, ensure_ascii=False))
               .replace("__REG__", json.dumps(regpage, ensure_ascii=False))
               .replace("__IMGS__", json.dumps(imgs))
               .replace("__PAGES__", json.dumps(args.pages)))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    cnt = collections.Counter(b for e in entries for _, b in e["c"])
    print(f"{len(entries)} poster, {len(regpage)} registerposter, kandidater pr. type: {dict(cnt)}; {len(html) // 1024} KB -> {args.out}")
    return 0


def _weekday(iso):
    import datetime
    return ["ma", "ti", "on", "to", "fr", "lø", "sø"][datetime.date.fromisoformat(iso).weekday()]


if __name__ == "__main__":
    sys.exit(main())
