#!/usr/bin/env python3
"""
build_overlap_page.py — byg annotationssiden til stikprøven med OVERLAP mellem dagbog og almanak
(docs/plan-streng-grounding.md §3.9): fire blokke på otte sammenhængende dage, hver dag med både
almanakposten og dagbogsteksten. Én fil, ingen server, intet at installere.

Indlæser:
  almanak/data/extracted/aligned.csv    almanakposter (PDF-tekst + databasens tekst)
  almanak/data/register/*.csv           almanakkens eget register (genbrug fra build_annotation_page.py)
  data/normalized/diary.csv             dagbogstekst (bind I–X)
  data/normalized/references.csv        hvilke registerposter (personer, værker OG steder) der knyttes til hvilke dagbogssider
  data/normalized/entities.csv          etiketter (steder: det gældende stedregister, LOC…-id'er)
  data/normalized/places.csv            kategori og land for stederne
  data/normalized/kb_diary_links.csv    link til Det Kgl. Biblioteks faksimile pr. dagbogsside

Tekstversioner (offsets gælder KUN mod netop disse tekster — de skrives i hver række i resultatet):
  almanak  ocr-2023-ukontrolleret-2026-11   PDF-tekstlaget + TEXT_FIXES; ikke kontrolleret mod sidebilledet
  dagbog   diary.csv-2026-11-linjetags-fjernet-orddeling-samlet
           linjetag (»038-03 «) fjernet, linjeskift = mellemrum; en bindestreg ved linjeskift fjernes
           før et lille bogstav (»Sommer-/fugl« → »Sommerfugl«) og bevares ellers (»Moltke-/Bregentved«
           → »Moltke-Bregentved«); en dags rækker på flere sider sættes sammen i sidernes rækkefølge.

Output: almanak/annotation/out/overlap-annotering.html

Brug (PowerShell, fra repo-roden):
  python almanak/annotation/build_overlap_page.py
"""

import argparse
import collections
import csv
import difflib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import build_annotation_page as bap  # noqa: E402  (genbrug: register, kandidater, tekstrens)

NORM = REPO_ROOT / "data" / "normalized"

# (blok, første dag, sidste dag, bind) — udvalgt i docs/plan-streng-grounding.md §3.9
BLOCKS = [
    ("A", "1841-02-15", "1841-02-22", "II"),
    ("B", "1846-01-01", "1846-01-08", "III"),
    ("C", "1855-07-17", "1855-07-24", "IV"),
    ("D", "1866-07-04", "1866-07-11", "VII"),
]
TV_ALM = "ocr-2023-ukontrolleret-2026-11"
TV_DAG = "diary.csv-2026-11-linjetags-fjernet-orddeling-samlet"
MAX_STRONG_CHIPS = 12

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}
LINE_TAG = re.compile(r"^\d{3}-\d{2}\s+")


def join_lines(lines):
    """Linjer -> løbende tekst (se TV_DAG)."""
    out = ""
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if not out:
            out = ln
        elif out.endswith("-") and re.match(r"[a-zæøåäöü]", ln):
            out = out[:-1] + ln
        elif out.endswith("-"):
            out += ln
        else:
            out += " " + ln
    return re.sub(r"\s+", " ", out).strip()


def load_diary(first, last):
    """{dato: (tekst, [(bind, side)])} for datoer i [first, last]."""
    days = collections.OrderedDict()
    with open(NORM / "diary.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if not (first <= r["date"] <= last):
                continue
            lines = [LINE_TAG.sub("", x) for x in r["text"].split("\n")]
            d = days.setdefault(r["date"], {"lines": [], "pages": []})
            d["lines"] += lines
            d["pages"].append((r["vol"], r["page"]))
    return {k: (join_lines(v["lines"]), v["pages"]) for k, v in days.items()}


def load_kb():
    out = {}
    with open(NORM / "kb_diary_links.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out[(r["vol"], r["page"])] = r["kb_url"]
    return out


def load_page_refs(pages):
    """{(bind, side): [entity_id, ...]} for personer, værker og steder, samt {entity_id: række}.
    Alle tre typer medtages: annotatoren skal kunne se, hvad registret knytter til siden, også når
    ordet står i en anden stavemåde i teksten (Setúbal/Setubal, Kjøbenhavn/København)."""
    ents = {}
    with open(NORM / "entities.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["entity_type"] in ("person", "work", "place"):
                ents[r["entity_id"]] = r
    want = set(pages)
    refs = collections.defaultdict(list)
    with open(NORM / "references.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if (r["vol"], r["page"]) in want and r["entity_id"] in ents and r["entity_id"] not in refs[(r["vol"], r["page"])]:
                refs[(r["vol"], r["page"])].append(r["entity_id"])
    return refs, ents


def load_place_info():
    """{LOC-id: 'By, Italien · besøgt'} fra places.csv (kategori, land, besøgt/omtalt)."""
    out = {}
    with open(NORM / "places.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            bits = [x for x in (r["category_da"], r["country"]) if x]
            vs = (r.get("visit_status") or "").strip().lower()
            out[r["entity_id"]] = ", ".join(bits) + (" · " + vs if vs else "")
    return out


_ACCENT = str.maketrans("áàâãéèêëíìîïóòôõúùûñçšž", "aaaaeeeeiiiioooouuuucsz")


def nfold(s):
    """Som bap.fold, men uden accenter (Setúbal = Setubal); æ, ø, å, ä, ö, ü bevares."""
    return bap.fold(s.lower().translate(_ACCENT))


def name_keys(label, kind):
    """Strenge, der – hvis de står som helt ord i teksten – viser, at registerposten nævnes."""
    if kind == "person":
        return [surname(label)]
    base = title_key(label)
    keys = [base]
    if kind == "place":
        m = re.search(r"\(([^)]*)\)\s*$", label)                 # »Galatz (Galati)«, »Tajo (Tejo)«
        if m:
            keys.append(m.group(1))
        keys += [x.strip() for x in base.split(",")]               # »Rabenhorst, Maxen«
        if base.lower() == "københavn":
            keys.append("Kjøbenhavn")                              # tidens stavemåde
    return keys


def mentioned(label, kind, tf):
    """Står registerpostens navn (eller en variant) i den affoldede tekst tf (nfold)?"""
    need = 3 if kind in ("person", "place") else 5
    return any(len(nfold(k)) >= need and re.search(rf"\b{re.escape(nfold(k))}s?\b", tf) for k in name_keys(label, kind))


def surname(label):
    s = re.sub(r",?\s*\bse\s*:.*$", "", label, flags=re.I)
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()
    return s.split(",")[0].strip()


def title_key(label):
    base = re.sub(r"\s*\([^)]*\)\s*$", "", label)
    base = re.sub(r"[»«*]", "", base).strip()
    return base


def diary_candidates(text, pages, refs, ents):
    """Registerposter (personer, værker, steder) knyttet til dagens sider; 'ref+navn' når navnet også
    står i teksten (med eller uden bøjnings-s, uden hensyn til accenter), ellers 'ref'.
    Forslag til annotatoren, ikke afgørelser."""
    tf = nfold(text)
    out = {}
    for p in pages:
        for eid in refs.get(p, ()):
            e = ents[eid]
            ok = mentioned(e["label"], e["entity_type"], tf)
            if eid not in out or ok:
                out[eid] = "ref+navn" if ok else "ref"
    order = {"ref+navn": 0, "ref": 1}
    return sorted(([k, v] for k, v in out.items()), key=lambda c: (order[c[1]], c[0]))


def build_entries(blocks_spec, al, reg_alm, by_date, year_n, require_diary=True, diary_ctx=False):
    """ENTRIES, BLOCKS og REG for blokkene (id, første, sidste, bind).

    require_diary=True: hver dag skal have både almanak og dagbog (overlap-stikprøven).
    require_diary=False: alle dage med almanaktekst; dagbogen tages med, hvor den findes.
    diary_ctx=True: dagbogsteksten vises kun som kontekst (markeres ikke)."""
    kb = load_kb()
    place_info = load_place_info()
    entries, blocks, REG = [], [], {}
    all_pages = []
    diary_by_block = {}
    for key, a, b, vol in blocks_spec:
        diary_by_block[key] = load_diary(a, b)
        for _, pg in diary_by_block[key].values():
            all_pages += pg
    refs, ents = load_page_refs(all_pages)

    for key, first, last, vol in blocks_spec:
        diary = diary_by_block[key]
        alm_days = {d for d, r in al.items() if first <= d <= last and (r["pdf_text"] or r["db_text"]).strip()}
        days = sorted(set(diary) & alm_days) if require_diary else sorted(alm_days)
        if require_diary and len(days) != 8:
            sys.exit(f"Blok {key}: {len(days)} dage med både dagbog og almanak (forventede 8)")
        blocks.append(dict(id=key, first=first, last=last, vol=vol, n=len(days)))
        for d in days:
            r = al[d]
            text = bap.clean(r["pdf_text"] or r["db_text"])
            diff = []
            if r["pdf_text"] and r["db_text"]:
                a_, b_ = bap.toks(text), bap.toks(r["db_text"])
                diff = [[" ".join(a_[i1:i2]), " ".join(b_[j1:j2])]
                        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, [x.lower() for x in a_], [x.lower() for x in b_], autojunk=False).get_opcodes()
                        if op != "equal"]
                diff = [x for x in diff if not bap.trivial(*x)]
            ea = dict(id="ALM-" + d, date=d, wd=bap._weekday(d), src="almanak", block=key, tv=TV_ALM,
                      page=f"{r['print_page']}", pages=[], text=text, dbdiff=diff)
            ea["c"] = bap.candidates(ea, reg_alm, by_date, year_n)
            entries.append(ea)
            if d not in diary:
                continue
            dtext, dpages = diary[d]
            # Almanakken har intet stedregister, og dens værk-/personregister er ikke dagbogens. Derfor
            # tilføjes dagbogsregistrets poster for dagens dagbogssider, når navnet står i almanakposten.
            ea["c"] += [[eid, "dag+navn"] for eid, b in diary_candidates(text, dpages, refs, ents) if b == "ref+navn"]

            pages = []
            for p in dpages:
                if p not in [(x["v"], x["p"]) for x in pages]:
                    pages.append(dict(v=p[0], p=p[1], kb=kb.get(p, "")))
            ed = dict(id="DAG-" + d, date=d, wd=bap._weekday(d), src="dagbog", block=key, tv=TV_DAG,
                      page=f"{pages[0]['v']}:{pages[0]['p']}" + (f"-{pages[-1]['p']}" if len(pages) > 1 else ""),
                      pages=pages, text=dtext, dbdiff=[])
            ed["c"] = diary_candidates(dtext, [(p["v"], p["p"]) for p in pages], refs, ents)
            if diary_ctx:
                ed["ctx"] = True
            entries.append(ed)

    # registerposter, som valglisten må kende: almanakkens eget + dagbogens poster på blokkenes sider
    for rid, info in reg_alm.items():
        if not info["see"]:
            REG[rid] = {k: v for k, v in info.items() if k != "see"}
    for e in entries:
        if e["src"] != "dagbog":
            continue
        for eid, _ in e["c"]:
            if eid not in REG:
                REG[eid] = reg_entry(ents[eid], e["page"], place_info)
    return entries, blocks, REG, ents, place_info


def reg_entry(en, page, place_info):
    if en["entity_type"] == "person":
        return dict(k="P", l=en["label"], d=bap.short(en["description"], 110), x=0, pp=page)
    if en["entity_type"] == "place":
        return dict(k="S", l=en["label"], d=place_info.get(en["entity_id"], ""), x=0, pp=page)
    return dict(k="W", l=re.sub(r"[*]", "", en["label"]), d="", x=0, pp=page)


OVERLAP_PAGE = dict(
    store="almanak-dagbog-overlap-annotering-v1",
    title="Annotering: dagbog og almanak, samme dage",
    sub="Fire blokke på otte dage (1841, 1846, 1855, 1866). Hver dag har både almanakposten og dagbogsteksten. "
        "Mærk personer, steder og værker i selve teksten.",
    reviewed_label="Dagen gennemgået (almanak og dagbog)",
    guide_extra="",
    mode="overlap",
)


def render(entries, REG, blocks, out, prefill=(), page=OVERLAP_PAGE):
    tpl = (HERE / "template-overlap.html").read_text(encoding="utf-8")
    html = (tpl.replace("__ENTRIES__", json.dumps(entries, ensure_ascii=False))
               .replace("__REG__", json.dumps(REG, ensure_ascii=False))
               .replace("__BLOCKS__", json.dumps(blocks))
               .replace("__PREFILL__", json.dumps(list(prefill), ensure_ascii=False))
               .replace("__STORE__", page["store"]).replace("__MODE__", page["mode"])
               .replace("__TITLE__", page["title"]).replace("__SUB__", page["sub"])
               .replace("__REVIEWED_LABEL__", page["reviewed_label"]).replace("__GUIDE_EXTRA__", page["guide_extra"])
               .replace("__TV_ALM__", TV_ALM).replace("__TV_DAG__", TV_DAG))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return html


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--aligned", type=Path, default=REPO_ROOT / "almanak" / "data" / "extracted" / "aligned.csv")
    ap.add_argument("--out", type=Path, default=HERE / "out" / "overlap-annotering.html")
    args = ap.parse_args()

    reg_alm, by_date, year_n = bap.load_register()
    al = {r["date"]: r for r in csv.DictReader(open(args.aligned, encoding="utf-8"))}
    entries, blocks, REG, _, _ = build_entries(BLOCKS, al, reg_alm, by_date, year_n)
    html = render(entries, REG, blocks, args.out)
    n_a = sum(1 for e in entries if e["src"] == "almanak"); n_d = len(entries) - n_a
    ch_a = sum(len(e["text"]) for e in entries if e["src"] == "almanak"); ch_d = sum(len(e["text"]) for e in entries if e["src"] == "dagbog")
    print(f"{n_a} almanakposter ({ch_a} tegn), {n_d} dagbogsdage ({ch_d} tegn), {len(REG)} registerposter; {len(html) // 1024} KB -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
