#!/usr/bin/env python3
"""
register_repair.py — rettelser af OCR-fejl i almanakregistret, efter at parse_register.py har læst det.

To trin (begge kaldes fra parse_register.py; begge efterlader sporet i data):

1. Navne: `almanak/data/register/ocr_corrections.tsv` (reg_id, felt, fra, til, begrundelse) rettes i
   `label`, `description` og `see`. `raw` (OCR-teksten) rører vi aldrig; den rettede etiket ligger i
   `label`, den oprindelige i `label_ocr` (kun hvor de er forskellige). Filen er håndholdt og kan læses
   og rettes af en redaktør; `python almanak/scripts/register_repair.py suggest` foreslår nye linjer.

2. Datoer: henvisninger, hvor årstallet ikke kan læses (»1830«, »1899«: OCR har forvekslet 3/5/8/9),
   får det år, som giver et sammenfald i almanakteksten selv: kandidaterne er årstal, der adskiller sig
   fra den læste form med ét ciffer, og et kandidatår accepteres kun, hvis personens (værkets) navn
   står i almanakposten på netop den dato — og kun hvis ét år vinder. `fix` på henvisningen siger,
   hvad der er gjort. Ingenting gættes uden kontrol mod teksten.

3. Datoer, der læses, men ikke findes i almanakken (`repair_unmatched_years`): OCR forveksler 3/5/9/8 i årstallet
   (»1833« for 1853 eller 1855, »1836« for 1856), også når den forkerte form selv er et gyldigt årstal. Almanakken har
   slet ingen årgange for 1835–36, 1839, 1848 m.fl., og 1833 kun feb.–apr.; en henvisning til en dag, der ikke findes,
   er derfor en fejl i år, ikke i dag. Kandidatårene er de, hvor kun cifrene 3/5/8/9 er byttet om; et år vælges, hvis personens
   (værkets) navn står i posten på netop den dato, og ellers ud fra naboerne i samme årstalsgruppe.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "parsers"))
import name_matching as nm  # noqa: E402

CORRECTIONS = REPO / "almanak" / "data" / "register" / "ocr_corrections.tsv"
ALIGNED = REPO / "almanak" / "data" / "extracted" / "aligned.csv"
FIELDS = ("label", "description", "see")


def load_corrections(path=CORRECTIONS):
    out = []
    if Path(path).exists():
        for r in csv.DictReader(open(path, encoding="utf-8"), delimiter="\t"):
            if r["reg_id"] and not r["reg_id"].startswith("#"):
                out.append(r)
    return out


def apply_name_corrections(rows, path=CORRECTIONS):
    """Rets i label/description/see (heltord). reg_id `*` = alle opslag. Returnerer antal ændrede felter."""
    n = 0
    fixes = load_corrections(path)
    for row in rows:
        orig_label = row["label"]
        for c in fixes:
            if c["reg_id"] not in ("*", row["reg_id"]):
                continue
            pat = re.compile(r"(?<![\wÆØÅæøåöäü])" + re.escape(c["fra"]) + r"(?![\wÆØÅæøåöäü])")
            for f in FIELDS:
                new = pat.sub(c["til"], row.get(f, ""))
                if new != row.get(f, ""):
                    row[f] = new
                    n += 1
        row["label_ocr"] = orig_label if row["label"] != orig_label else ""
    return n


# --------------------------------------------------------------------------------------------------
def _entry_texts(aligned=ALIGNED):
    out = {}
    for r in csv.DictReader(open(aligned, encoding="utf-8")):
        out[r["date"]] = [t for t in (r["pdf_text"], r["db_text"]) if t]
    return out


def _forms(row, kind):
    if kind == "person":
        sur, _ = nm.person_forms(row["label"])
        return [f for f in sur if len(nm.fold(f)) >= 4]
    title = re.sub(r"\s*\([^)]*\)", "", re.sub(r"[»«*\"]", "", row["label"]))
    title = re.sub(r"[,.]?\s*\d{1,2}\.\d.*$", "", title).strip(" ,.")
    words = [w for w in re.findall(r"[A-ZÆØÅ][\wæøåöäü\-]+", title) if len(w) >= 5]
    return ([title] if len(title) >= 5 else []) + words[:2]


def _has_name(texts, forms):
    for t in texts:
        v = nm.TextView(t)
        for f in forms:
            if nm.find(v, f) or (len(nm.fold(f)) >= 5 and nm.fuzzy_find(v, f)):
                return True
    return False


def year_candidates(raw):
    """Årstal 1833-1873, der adskiller sig fra den læste form med ét ciffer."""
    out = []
    for y in range(1833, 1874):
        if sum(a != b for a, b in zip(str(y), raw)) == 1:
            out.append(y)
    return out


def repair_years(persons, works, refs, aligned=ALIGNED):
    """Sætter år på henvisninger med ulæseligt årstal, hvor navnekontrollen giver ét entydigt vindende år."""
    texts = _entry_texts(aligned)
    rows = {r["reg_id"]: (r, "person") for r in persons}
    rows.update({r["reg_id"]: (r, "work") for r in works})
    groups = {}
    for r in refs:
        if not r["valid"] and not r["year"] and re.fullmatch(r"1\d{3}", str(r["year_raw"])) and r["kind"] == "date" and r["day"] and r["month"]:
            groups.setdefault((r["reg_id"], r["year_raw"]), []).append(r)
    fixed = unresolved = 0
    for (rid, raw), rs in groups.items():
        row, kind = rows[rid]
        forms = _forms(row, kind)
        if not forms:
            unresolved += len(rs)
            continue
        score = {}
        for y in year_candidates(raw):
            for r in rs:
                d = f"{y:04d}-{int(r['month']):02d}-{int(r['day']):02d}"
                if d in texts and _has_name(texts[d], forms):
                    score[y] = score.get(y, 0) + 1
        if score:
            best = max(score.values())
            win = [y for y, s in score.items() if s == best]
            if len(win) == 1:
                for r in rs:
                    d = f"{win[0]:04d}-{int(r['month']):02d}-{int(r['day']):02d}"
                    if d in texts and _has_name(texts[d], forms):      # kun datoer, der selv bekræfter navnet
                        r["year"], r["valid"], r["fix"] = win[0], 1, f"år-rettet-ved-navnekontrol ({raw}→{win[0]})"
                        fixed += 1
                    else:
                        unresolved += 1
                continue
        unresolved += len(rs)
    return fixed, unresolved


CONFUSABLE = set("3589")


def confusable_years(y):
    """Årstal 1833-1873, der adskiller sig fra y i ét eller to cifre, hvor begge cifre er blandt 3/5/8/9 (OCR-forvekslinger)."""
    s = str(y)
    out = []
    for yy in range(1833, 1874):
        d = [(a, b) for a, b in zip(s, str(yy)) if a != b]
        if 1 <= len(d) <= 2 and all(a in CONFUSABLE and b in CONFUSABLE for a, b in d):
            out.append(yy)
    return out


def repair_unmatched_years(persons, works, refs, aligned=ALIGNED):
    """Gyldige datoer uden almanakpost: ret årstallet (3/5/8/9-forveksling), når navnet bekræfter det eller naboerne peger entydigt.
    Returnerer (rettet ved navn, rettet via gruppe, uløst)."""
    texts = _entry_texts(aligned)
    rows = {r["reg_id"]: (r, "person") for r in persons}
    rows.update({r["reg_id"]: (r, "work") for r in works})

    def key(y, m, d):
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    todo = [r for r in refs if r["valid"] and r["kind"] == "date" and r["src"] == "tail" and r["day"] and r["month"]
            and r["year"] and key(r["year"], r["month"], r["day"]) not in texts]
    todo_ids = {id(r) for r in todo}
    groups, last, cur = [], None, []
    for r in refs:                                   # årstalsgrupper: på hinanden følgende henvisninger med samme årstalsstreng
        k = (r["reg_id"], r["year_raw"], r["src"])
        if k != last:
            if cur:
                groups.append(cur)
            cur, last = [], k
        cur.append(r)
    groups.append(cur)

    name_fixed = group_fixed = 0
    forms_cache = {}
    for g in groups:
        pending = [r for r in g if id(r) in todo_ids]
        if not pending:
            continue
        rid = g[0]["reg_id"]
        if rid not in forms_cache:
            row, kind = rows[rid]
            forms_cache[rid] = _forms(row, kind)
        forms = forms_cache[rid]
        resolved, ambiguous = {}, {}
        for r in pending:
            cands = [yy for yy in confusable_years(r["year"]) if key(yy, r["month"], r["day"]) in texts]
            named = [yy for yy in cands if forms and _has_name(texts[key(yy, r["month"], r["day"])], forms)]
            if len(named) == 1:
                resolved[id(r)] = named[0]
            else:
                ambiguous[id(r)] = (named, cands)
        votes = {}
        for y in resolved.values():
            votes[y] = votes.get(y, 0) + 1
        gy = max(votes, key=votes.get) if votes and list(votes.values()).count(max(votes.values())) == 1 else None
        for r in pending:
            raw = r["year"]
            if id(r) in resolved:
                y, how = resolved[id(r)], "år-rettet-ved-navnekontrol"
            else:
                named, cands = ambiguous[id(r)]
                if gy and gy in (named or cands) and (not named or gy in named):
                    y, how = gy, "år-rettet-via-gruppe"
                else:
                    continue
            r["year"], r["valid"], r["fix"] = y, 1, f"{how} ({raw}→{y})"
            if how == "år-rettet-ved-navnekontrol":
                name_fixed += 1
            else:
                group_fixed += 1
    unresolved = sum(1 for r in todo if key(r["year"], r["month"], r["day"]) not in texts)
    return name_fixed, group_fixed, unresolved


# --------------------------------------------------------------------------------------------------
def suggest(persons_csv=REPO / "almanak" / "data" / "register" / "almanak_register_persons.csv"):
    """Foreslår navnerettelser: sjældne former, der ligger ét OCR-skridt fra en kendt form i andre kilder."""
    import collections
    sys.path.insert(0, str(REPO / "almanak" / "ner"))
    from context import canon
    known = collections.Counter()
    for r in csv.DictReader(open(REPO / "data" / "normalized" / "entities.csv", encoding="utf-8")):
        if r["entity_type"] in ("person", "place"):
            sur, given = nm.person_forms(r["label"]) if r["entity_type"] == "person" else (nm.place_forms(r["label"])[0], [])
            for s in sur + given:
                for w in re.split(r"[\s\-]", s):
                    known[canon(w)] += 1
    for r in csv.DictReader(open(ALIGNED, encoding="utf-8")):
        for t in (r["pdf_text"], r["db_text"]):
            for w in re.findall(r"[A-ZÆØÅ][\wæøåäöü]+", t or ""):
                known[canon(w)] += 1
    for r in csv.DictReader(open(persons_csv, encoding="utf-8")):
        for w in re.split(r"[\s\-,]", r["label"].split("(")[0]):
            if len(w) < 4 or canon(w) in known:
                continue
            for cand in ocr_variants(w):
                if canon(cand) in known and cand != w:
                    print(f"{r['reg_id']}\tlabel\t{w}\t{cand}\tOCR-forveksling")
                    break


def ocr_variants(w):
    """Mulige rigtige stavemåder af et OCR-læst ord (e→c, ff→fT/lT/fl, rn↔m, ii→n ...)."""
    out = []
    subs = [("fT", "ff"), ("lT", "ff"), ("T", "ff"), ("c", "e"), ("fl", "ff"), ("ii", "n"), ("rn", "m")]
    for a, b in subs:
        if a in w:
            out.append(w.replace(a, b))
    if "c" in w:
        for m in re.finditer("c", w):
            out.append(w[:m.start()] + "e" + w[m.end():])
    return out


if __name__ == "__main__":
    if sys.argv[1:] == ["suggest"]:
        suggest()
    else:
        sys.exit(__doc__)
