#!/usr/bin/env python3
"""
screen_persons_for_lex.py
-------------------------
Screens the person register for lex.dk look-ups (docs/plan-lex-dk-links.md §2).
No network. Writes data/curated/lex/persons_tiers.csv:

  tier A  ≈1.300  public persons with ≥5 diary references or role author/artist
  tier B  ≈2.000  public persons without that signal (deterministic match only)
  tier C  the rest — deliberately NOT looked up (peripheral persons)

Funnel (all must hold to leave tier C):
  1. label carries life dates "(år–år)"
  2. label carries a given name ("Efternavn, Fornavn …")
  3. description or role signals a public person (poet, composer, painter, king …)
  4. description is not ONLY kinship ("Søn af …", "Datter af …", "g. m. …")
Tier A additionally needs ≥5 diary references (transcribed pages only) or role
Forfatter/Digter or Kunstner/Billedkunst.

Gender does not screen persons out; it steers the source (column `gender`):
women are tried first in Dansk Kvindebiografisk Leksikon.

`search_name` is the name as a lex.dk article title would spell it
("Johanne Luise Heiberg", "Frederik 7."). Overrides for royals and spelling
variants are in data/curated/lex/search_name_overrides.csv (rid,search_name).
"""

import csv
import re
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
N = REPO / "data" / "normalized"
OUT = REPO / "data" / "curated" / "lex" / "persons_tiers.csv"
OVR = REPO / "data" / "curated" / "lex" / "search_name_overrides.csv"

KIN = re.compile(r"^(Søn|Datter|Broder|Søster|Enke|g\.|Barn|Plejedatter|Svigerdatter|Svigersøn|Hustru|"
                 r"Fætter|Kusine|Moder|Fader|Gift)", re.I)
NOTABLE = re.compile(
    r"Digter|Komponist|Maler|Billedhugger|Skuespiller|Balletmester|Danser|Konge|Kejser|Dronning|Prins|"
    r"Kronprins|Biskop|Politiker|Minister|Fysiker|Kemiker|Naturforsker|Filosof|Arkitekt|Forfatter|Sanger|"
    r"Historiker|Professor|Dirigent|Violin|Pianist|Kritiker|Teolog|Forlægger|Tegner|Grafiker|Astronom|"
    r"Zoolog|Botaniker|Geolog|Filolog|Redaktør|Instruktør|Dramatiker|Ingeniør|Arkæolog|Læge|Præst|"
    r"General|Admiral|Statsminister|Etatsraad", re.I)
NOTABLE_ROLES = ("Forfatter/Digter", "Musiker/Scenekunst", "Kunstner/Billedkunst")
KIN_BUT_NOTABLE = re.compile(r"Digter|Komponist|Maler|Billedhugger|Skuespiller|Forfatter|Professor|Biskop|"
                             r"Politiker|Konge|Minister", re.I)
# Register "surnames" that are really realms (royals): "Danmark, Frederik (VII), Kronprins af –"
REALMS = {"Danmark", "Sverrig-Norge", "Sverige", "Norge", "Frankrig", "England", "Preussen", "Rusland",
          "Sachsen-Weimar-Eisenach", "Bayern", "Østrig", "Hannover", "Belgien", "Holland", "Italien"}
def roman(s: str) -> int:
    v = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    tot = 0
    for a, b in zip(s, s[1:] + " "):
        tot += -v[a] if b in v and v[b] > v[a] else v[a]
    return tot


def search_name(label: str) -> str:
    head, _, rest = label.partition(",")
    given = re.sub(r"\([^)]*\)", lambda m: m.group(0) if re.fullmatch(r"\([IVX]+\)", m.group(0)) else " ",
                   rest.split(",")[0]).strip() if rest else ""
    m = re.search(r"\(([IVX]+)\)", rest)
    if head.strip() in REALMS and m:
        return re.sub(r"\s*\([IVX]+\)", "", given).strip() + f" {roman(m.group(1))}."
    m2 = re.fullmatch(r"(.+?)\s+([IVX]+)", given.strip())        # "Frederik VI" (no parentheses)
    if head.strip() in REALMS and m2:
        return f"{m2.group(1)} {roman(m2.group(2))}."
    given = re.sub(r"\([IVX]+\)", "", given).strip()
    given = re.sub(r"\s+(von|van|af|de|der|du|la|le|zu)$", "", given)
    sur = re.sub(r"\s*\(.*", "", head).strip()
    return f"{given} {sur}".strip()


def main():
    ents = {r["entity_id"]: r for r in csv.DictReader(open(N / "entities.csv", encoding="utf-8"))
            if r["entity_type"] == "person" and not r["see"]}
    role = {r["entity_id"]: r["roller"] for r in csv.DictReader(open(N / "person_role.csv", encoding="utf-8"))}
    gen = {r["entity_id"]: r for r in csv.DictReader(open(N / "person_gender.csv", encoding="utf-8"))}
    nat = {}
    for r in csv.DictReader(open(N / "person_ethnic_descriptors.csv", encoding="utf-8")):
        if r["position_type"] == "leading" and r["referent_hint"] == "subject":
            nat.setdefault(r["entity_id"], r["nationality_key"])
    pages = {(r["vol"], r["page"]) for r in csv.DictReader(open(N / "diary.csv", encoding="utf-8"))}
    refs = Counter()
    for r in csv.DictReader(open(N / "references.csv", encoding="utf-8")):
        if r["entity_id"] in ents and (r["vol"], r["page"]) in pages:
            refs[r["entity_id"]] += 1
    over = {}
    if OVR.exists():
        over = {r["rid"]: r["search_name"] for r in csv.DictReader(open(OVR, encoding="utf-8"))}

    rows, stats = [], Counter()
    for rid, e in ents.items():
        lab, desc, rl = e["label"], e["description"] or "", role.get(rid, "")
        reason, tier = "", "C"
        if not re.search(r"\((?:ca\.\s*)?\d{4}\s*[–-]\s*\d{4}\)", lab):
            reason = "ingen levetid"
        elif "," not in lab:
            reason = "intet fornavn"
        elif not (NOTABLE.search(desc) or rl in NOTABLE_ROLES or "Adel/Kongelig/Hof" in rl):
            reason = "ingen offentlig rolle"
        elif KIN.match(desc) and not KIN_BUT_NOTABLE.search(desc):
            reason = "kun slægtskab"
        elif gen.get(rid, {}).get("koen", "").startswith(("Andet", "Endnu")):
            reason = "køn: gruppe/ubestemt"
        else:
            strong = refs[rid] >= 5 or rl in ("Forfatter/Digter", "Kunstner/Billedkunst")
            tier = "A" if strong else "B"
            reason = "≥5 refs eller forfatter/kunstner" if strong else "offentlig rolle, få refs"
        stats[tier] += 1
        rows.append({"rid": rid, "tier": tier, "reason": reason, "refs": refs[rid],
                     "gender": gen.get(rid, {}).get("koen", ""), "nationality": nat.get(rid, ""),
                     "role": rl, "search_name": over.get(rid) or search_name(lab), "label": lab})
    rows.sort(key=lambda r: ({"A": 0, "B": 1, "C": 2}[r["tier"]], -r["refs"], r["rid"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT}: {dict(stats)}")


if __name__ == "__main__":
    main()
