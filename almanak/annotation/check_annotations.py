#!/usr/bin/env python3
"""
check_annotations.py — kontrollér en returneret annotering mod den side, den blev lavet på.

Hver markering er (post_id, start, end, string). Den er kun meningsfuld mod netop den tekst, den blev
lavet på; skriptet henter teksterne fra selve HTML-siden (ENTRIES) og kontrollerer, at
  * text[start:end] == string            (offsets passer, slut eksklusiv)
  * markeringer i samme post ikke overlapper
  * type er en af Person/Sted/Værk/Lokalitet/Andet (Institution kun i ældre resultater)
  * (JSON fra overlap-siden) hvilke dage der er gennemgået, og aktiv tid pr. blok

Brug (PowerShell, fra repo-roden):
  python almanak/annotation/check_annotations.py almanak/annotation/out/overlap-annotering.html resultat.json
  python almanak/annotation/check_annotations.py almanak/annotation/out/almanak-annotering.html soren.tsv

Filen er enten JSON (»Kopiér resultat (JSON)«) eller TSV (»Kopiér som tabel«). Exit-kode 0 = alt i orden.
"""
import csv
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

TYPES = {"Person", "Sted", "Værk", "Lokalitet", "Institution", "Andet"}  # Institution: kun ældre resultater


def load_entries(html_path):
    html = Path(html_path).read_text(encoding="utf-8")
    m = re.search(r"const ENTRIES = (\[.*?\]);\n", html, re.S)
    if not m:
        sys.exit("Fandt ingen ENTRIES i siden")
    return {e["id"]: e for e in json.loads(m.group(1))}


def load_result(path):
    raw = Path(path).read_text(encoding="utf-8-sig")
    if raw.lstrip().startswith("{"):
        j = json.loads(raw)
        return j["annotations"], j
    rows = []
    for r in csv.DictReader(io.StringIO(raw), delimiter="\t"):
        rows.append({"post_id": r["post_id"], "start": int(r["start"]), "end": int(r["end"]), "string": r["string"],
                     "type": r["type"], "unsure": r.get("unsure", ""), "annotator": r.get("annotator", ""),
                     "block": r.get("block", ""), "source": r.get("source", "")})
    return rows, None


def main(argv):
    if len(argv) != 3:
        sys.exit(__doc__)
    entries = load_entries(argv[1])
    rows, meta = load_result(argv[2])
    errors = []
    for i, a in enumerate(rows, 1):
        e = entries.get(a["post_id"])
        if not e:
            errors.append(f"række {i}: ukendt post {a['post_id']}")
            continue
        s, en = int(a["start"]), int(a["end"])
        if e["text"][s:en] != a["string"]:
            errors.append(f"række {i} {a['post_id']}: text[{s}:{en}] = {e['text'][s:en]!r}, men string = {a['string']!r}")
        if a["type"] not in TYPES:
            errors.append(f"række {i} {a['post_id']}: ukendt type {a['type']!r}")
    by = {}
    for a in rows:
        by.setdefault(a["post_id"], []).append((int(a["start"]), int(a["end"]), a["string"]))
    for pid, spans in by.items():
        spans.sort()
        for (s1, e1, t1), (s2, e2, t2) in zip(spans, spans[1:]):
            if s2 < e1:
                errors.append(f"{pid}: {t1!r} ({s1}-{e1}) overlapper {t2!r} ({s2}-{e2})")
    print(f"{len(rows)} markeringer i {len(by)} poster; typer: {dict(Counter(a['type'] for a in rows))}")
    if meta:
        days = meta.get("reviewed_days", [])
        all_days = sorted({e['date'] for e in entries.values()})
        print(f"gennemgåede dage: {len(days)} af {len(all_days)}; ikke gennemgået: {sorted(set(all_days) - set(days)) or 'ingen'}")
        act = meta["meta"].get("active_seconds_by_block", {})
        if act:
            print("aktiv tid pr. blok (min): " + ", ".join(f"{k}: {round(v / 60)}" for k, v in sorted(act.items())))
        ids_wo = sorted({e['date'] for e in entries.values()} - {a['post_id'][-10:] for a in rows})
        if ids_wo:
            print(f"dage helt uden markeringer: {len(ids_wo)} (tjek, at de er markeret som gennemgået)")
    for e in errors:
        print("FEJL", e)
    print("OK" if not errors else f"{len(errors)} fejl")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
