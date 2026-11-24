#!/usr/bin/env python3
"""
build_titles.py — liste over herskertitler, der sammen med »af« + stednavn betegner en PERSON (omtale), ikke et sted.

»Hertuginden af Augustenborg«, »Arvehertugen af Weimar«, »Prindsessen af Preusen« er omtaler af en bestemt person.
Stednavnet i dem er ikke et sted i teksten. Titlerne udledes (ikke gættes) af to kilder:

1. Personregistret til Dagbøgerne (`data/normalized/entities.csv`, 10.228 personer). Etiketterne har formen
   »Berri, Louise, Prinsesse af – (1819–1864)« / »Augustenborg, Christian August, Hertug af Slesvig-…«. Titlen er ordet
   foran »af«. Kun poster, hvis rolle er `Adel/Kongelig/Hof` (kolonnen `roller` i `data/normalized/person_role.csv`
   og `person_role_manual.csv`, 1.528 personer), tæller; en titel optages, hvis ≥ 2 sådanne personer har den, og de er
   i overtal (så »Søn af«, »Datter af«, »Plejedatter af« falder fra).
2. Sørens og Holgers markeringer (`almanak/annotation/Opmærkning til Holger.json`): strenge af formen »Titel af Sted«,
   typet Person (»Prindsessen af Preusen«, »Hertugen af Weimar«, »Dronningen af Sardinien«).

Til de udledte grundtitler føjes bøjede former (bestemt form, genitiv) og tidens stavemåder (prinds, keiser) mekanisk,
samt nogle få håndholdte (Arvehertug, Erkehertug, Kong), som står i `HAND` herunder og i uddatafilen med kilden »hånd«.

Uddata (committes; ingen numpy/register ved kørsel):
  almanak/ner/data/ruler_titles.tsv   form <TAB> grundtitel <TAB> kilde <TAB> n_register <TAB> n_gold <TAB> eksempel

  python almanak/ner/build_titles.py
"""
from __future__ import annotations

import collections
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import gold as G  # noqa: E402

OUT = HERE / "data" / "ruler_titles.tsv"
NORM = REPO / "data" / "normalized"
ROLE = "Adel/Kongelig/Hof"
HAND = {"arvehertug": "Arvehertug (hånd: tidens form)", "erkehertug": "Erkehertug (1 post)", "kong": "Kong (forkortet »Konge«)",
        "arvestorhertug": "Arvestorhertug (i dagbogens tekst)", "kronprinds": "Kronprinds (tidens stavemåde)",
        "kronprindsesse": "Kronprindsesse (tidens stavemåde)", "arveprinds": "Arveprinds (tidens stavemåde)"}
NOT_TITLE = {"søn", "datter", "plejedatter", "adoptivdatter", "broderdatter", "gotfred", "maria", "catarina", "eremitten",
             "jarl"}   # Jarl er også fornavn


def forms_of(base):
    """Grundtitel -> {former}: grundform, bestemt form, genitiv, tidens stavemåder (prins->prinds, kejser->keiser)."""
    b = base.lower()
    vars_ = {b}
    if "prins" in b:
        vars_.add(b.replace("prins", "prinds"))
    if "kejser" in b:
        vars_.add(b.replace("kejser", "keiser"))
    out = set()
    for v in vars_:
        out.add(v)
        out.add(v + ("n" if v.endswith("e") else "en"))
        out.add(v + "s")
        out.add(v + ("ns" if v.endswith("e") else "ens"))
    return out


def derive_from_register():
    role = {}
    for f in ("person_role.csv", "person_role_manual.csv"):
        for r in csv.DictReader(open(NORM / f, encoding="utf-8")):
            if r["roller"]:
                role[r["entity_id"]] = role.get(r["entity_id"], "") + ";" + r["roller"]
    pat = re.compile(r",\s*([A-ZÆØÅ][\wæøåÆØÅ]+)\s+af\b")
    royal, other, ex = collections.Counter(), collections.Counter(), {}
    for e in csv.DictReader(open(NORM / "entities.csv", encoding="utf-8")):
        if e["entity_type"] != "person":
            continue
        for m in pat.finditer(e["label"]):
            t = m.group(1).lower()
            (royal if ROLE in role.get(e["entity_id"], "") else other)[t] += 1
            ex.setdefault(t, e["label"][:60])
    return {t: (royal[t], other[t], ex[t]) for t in set(royal) | set(other)
            if royal[t] >= 2 and royal[t] > other[t] and t not in NOT_TITLE}


def base_of(word, known):
    """Bestemt form -> grundform ud fra de kendte grundtitler: hertugen -> hertug, kongen -> konge, prindsessen -> prindsesse."""
    w = word.lower()
    forms = {k: k for k in known}
    for k in known:
        for f in forms_of(k):
            forms.setdefault(f, k)
    if w in forms:
        return forms[w]
    for cand in (w[:-2], w[:-1], w[:-2] + "e"):
        if cand in known:
            return cand
    return w[:-2] if w.endswith("en") else w


def derive_from_gold():
    """{første ord (lille bogstav): (antal, eksempel)} for guldstrenge af formen »Titel af Sted« typet Person."""
    c, ex = collections.Counter(), {}
    for a in G.load_gold():
        m = re.match(r"^([A-ZÆØÅ][a-zæøå]+)\s+af\s+[A-ZÆØÅ]", a["string"]) if a["type"] == "Person" else None
        if m:
            w = m.group(1).lower()
            c[w] += 1
            ex.setdefault(w, a["string"])
    return c, ex


def main():
    reg = derive_from_register()
    gold_c, gold_ex = derive_from_gold()
    rows = {}
    for base, (n_r, n_o, ex) in reg.items():
        for f in forms_of(base):
            rows[f] = (base, "register", n_r, 0, ex)
    for w, n in gold_c.items():
        base = base_of(w, set(reg) | set(HAND))
        if base not in reg and base not in HAND:
            print(f"guldstreng ikke optaget som titel (ikke herskertitel i registret): {gold_ex[w]!r}")
            continue
        for f in forms_of(base) | {w}:
            b0, src, n_r, n_g, ex = rows.get(f, (base, "guld", 0, 0, gold_ex[w]))
            rows[f] = (b0, "register+guld" if src == "register" else src, n_r, n_g + (n if f == w else 0), ex)
    for base, ex in HAND.items():
        for f in forms_of(base):
            rows.setdefault(f, (base, "hånd", 0, 0, ex))
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        for f in sorted(rows):
            b, src, n_r, n_g, ex = rows[f]
            fh.write(f"{f}\t{b}\t{src}\t{n_r}\t{n_g}\t{ex}\n")
    bases = sorted({r[0] for r in rows.values()})
    print(f"{len(rows)} former af {len(bases)} grundtitler -> {OUT}")
    print(", ".join(bases))


if __name__ == "__main__":
    main()
