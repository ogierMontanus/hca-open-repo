#!/usr/bin/env python3
"""
adjudication_queue.py — byg adjudikeringslisten til en returneret overlap-annotering
(docs/plan-streng-grounding.md §3.9 »I stedet for en anden annotator« og §3.10).

Reglerne og annoteringen er uenige, eller annoteringen er uenig med sig selv; hvert tilfælde
lægges tilbage til annotatoren som »enig/uenig«. Det måler IKKE annotatorenighed.

Fire kategorier:
  UMARKERET    en streng, der er markeret et andet sted i sættet, eller et registernavn
               (dagbogsregistret for dagens side; navnet står i teksten), står umarkeret
  TYPEKONFLIKT samme streng har fået forskellige typer; mindretalsforekomsterne foreslås ændret
  AFGRÆNSNING  spændet ender på et lille ord (»og«, verbum) eller samler to navne med »og«
  REGEL        afvigelse fra vejledningen: rolle alene mærket som andet end Person; almindeligt
               navneord (GENERIC) mærket som Værk/Andet. GENERIC-ord foreslås aldrig som UMARKERET.

Brug (PowerShell, fra repo-roden):
  python almanak/annotation/adjudication_queue.py almanak/annotation/out/overlap-annotering.html resultat.json -o kø.tsv
"""
import argparse
import collections
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

ROLES = {"kongen", "dronningen", "kronprindsen", "kronprindsessen", "prindsen", "prindsessen", "hertugen",
         "fyrsten", "maleren", "faderen", "moderen", "verten", "ministeren"}
GENERIC = {"bog", "vers", "rimbrev", "roman", "concert", "consert", "billeder", "digt", "portræt", "stambog",
           "eventyr", "brev", "album"}   # vejledningen: »almindelige navneord er ikke værker«
WORDCH = r"\wÆØÅæøå"


def fold(s):
    """Længdebevarende foldning: små bogstaver, accenter fjernet (æ/ø/å bevares, ö→ø, ä→æ)."""
    s = s.translate(str.maketrans("öÖäÄ", "øØæÆ"))
    return "".join(c.lower() if c in "æøåÆØÅ" else unicodedata.normalize("NFD", c)[0].lower() for c in s)


def word_re(s):
    k = re.escape(fold(s)).replace("å", "(?:å|aa)").replace("k", "(?:kj?|c)")
    return re.compile(rf"(?<![{WORDCH}]){k}s?(?![{WORDCH}])")


def reg_keys(r):
    lbl = re.sub(r"\(.*?\)", "", r["l"]).strip()
    if r["k"] == "P":
        return [lbl.split(",")[0].strip().split()[-1]]
    return [x.strip() for x in lbl.split(",") if x.strip()]


def load_page(html_path):
    html = Path(html_path).read_text(encoding="utf-8")
    entries = json.loads(re.search(r"const ENTRIES = (\[.*?\]);\n", html, re.S).group(1))
    reg = json.loads(re.search(r"const REG = (\{.*?\});\n", html, re.S).group(1))
    return {e["id"]: e for e in entries}, reg


def build(entries, reg, ann):
    spans = collections.defaultdict(list)
    for a in ann:
        spans[a["post_id"]].append(a)

    def covered(pid, s, e):
        return any(a["start"] < e and a["end"] > s for a in spans[pid])

    def ctx(pid, s, e, n=45):
        t = entries[pid]["text"]
        return (t[max(0, s - n):s] + "⟦" + t[s:e] + "⟧" + t[e:e + n]).strip()

    out, seen = [], set()

    def add(cat, pid, s, e, proposal):
        key = (cat, pid, s, e)
        if key in seen:
            return
        seen.add(key)
        out.append({"kategori": cat, "post_id": pid, "start": s, "end": e, "streng": entries[pid]["text"][s:e],
                    "kontekst": ctx(pid, s, e), "forslag": proposal})

    # UMARKERET — strenge markeret andetsteds (majoritetstype)
    types_by = collections.defaultdict(collections.Counter)
    for a in ann:
        types_by[fold(a["string"])][a["type"]] += 1
    for f, cnt in types_by.items():
        if len(f) < 3 or f in GENERIC:
            continue
        ty = cnt.most_common(1)[0][0]
        pat = word_re(f)
        for pid, e in entries.items():
            for m in pat.finditer(fold(e["text"])):
                if not covered(pid, m.start(), m.end()):
                    add("UMARKERET", pid, m.start(), m.end(), f"mærk som {ty} (markeret {sum(cnt.values())}× andetsteds)")
    # UMARKERET — registernavn står i teksten
    for pid, e in entries.items():
        t = fold(e["text"])
        for rid, how in e["c"]:
            r = reg.get(rid)
            if not r or "navn" not in how:
                continue
            ty = {"P": "Person", "S": "Sted", "W": "Værk"}[r["k"]]
            for k in reg_keys(r):
                if fold(k) in GENERIC:
                    continue
                for m in word_re(k).finditer(t):
                    if not covered(pid, m.start(), m.end()):
                        add("UMARKERET", pid, m.start(), m.end(), f"mærk som {ty} (register: {r['l']})")
    # TYPEKONFLIKT
    for a in ann:
        cnt = types_by[fold(a["string"])]
        if len(cnt) > 1:
            top, n = cnt.most_common(1)[0]
            if a["type"] != top or list(cnt.values()).count(n) > 1:
                add("TYPEKONFLIKT", a["post_id"], a["start"], a["end"],
                    f"er {a['type']}; samme streng ellers " + ", ".join(f"{k} {v}×" for k, v in cnt.items()))
    # AFGRÆNSNING
    for a in ann:
        w = a["string"].split()
        if len(w) > 1 and (w[-1] in {"og", "i", "af", "med", "til"} or (a["type"] == "Person" and w[-1][:1].islower()
                                                                          and w[-1] not in {"af", "von", "de"})):
            add("AFGRÆNSNING", a["post_id"], a["start"], a["end"], f"fjern »{w[-1]}« fra spændet")
        elif a["type"] == "Person" and re.search(r"\s(og|&)\s", a["string"]):
            add("AFGRÆNSNING", a["post_id"], a["start"], a["end"], "to personer/grupper i ét spænd: mærk hver for sig")
    # REGEL
    for a in ann:
        f = fold(a["string"])
        if f in ROLES and a["type"] != "Person":
            add("REGEL", a["post_id"], a["start"], a["end"], f"rolle alene: Person, ikke {a['type']}")
        if f in GENERIC and a["type"] in ("Værk", "Andet"):
            add("REGEL", a["post_id"], a["start"], a["end"], f"almindeligt navneord: ingen markering (er {a['type']})")
    order = {"UMARKERET": 0, "TYPEKONFLIKT": 1, "AFGRÆNSNING": 2, "REGEL": 3}
    out.sort(key=lambda r: (order[r["kategori"]], r["post_id"][4:], r["post_id"], r["start"]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page")
    ap.add_argument("result")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args(argv)
    entries, reg = load_page(a.page)
    ann = json.loads(Path(a.result).read_text(encoding="utf-8-sig"))["annotations"]
    rows = build(entries, reg, ann)
    cols = ["nr", "kategori", "post_id", "start", "end", "streng", "kontekst", "forslag", "svar (enig/uenig)", "kommentar"]
    with open(a.out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, cols, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for i, r in enumerate(rows, 1):
            w.writerow({"nr": i, **r, "svar (enig/uenig)": "", "kommentar": ""})
    print(f"{len(rows)} tilfælde: {dict(collections.Counter(r['kategori'] for r in rows))} -> {a.out}")


if __name__ == "__main__":
    sys.exit(main())
