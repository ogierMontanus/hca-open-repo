#!/usr/bin/env python3
"""Write docs/todo-data-errors.md: register references to pages that have no
transcribed diary text.

These pages are excluded from the mockup (see _diary_scope.py). Run from the
repo root:

    python scripts/build_mockup/report_untranscribed_pages.py
"""
import csv
from collections import defaultdict
from pathlib import Path

import _diary_scope

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "todo-data-errors.md"
VOL_ORDER = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]


def main() -> None:
    ents = {}
    with (ROOT / "data" / "normalized" / "entities.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ents[r["entity_id"]] = r["label"].replace("\n", " ").strip()

    bad = _diary_scope.untranscribed_refs()
    pages = defaultdict(list)
    for r in bad:
        pages[(r["vol"], r["page"])].append(r["entity_id"])
    with _diary_scope.REFS_CSV.open(newline="", encoding="utf-8") as f:
        no_page = sum(1 for r in csv.DictReader(f) if not r["vol"] and not r["page"])

    def key(vp):
        v, p = vp
        return (VOL_ORDER.index(v) if v in VOL_ORDER else 99, int(p) if p.isdigit() else 0)

    n_text = len(_diary_scope.text_pages())
    n_text_da = f"{n_text:,}".replace(",", ".")
    by_vol = defaultdict(list)
    for vp in pages:
        by_vol[vp[0]].append(vp)

    L = []
    L.append("# TODO — datafejl\n")
    L.append("Genereret af `scripts/build_mockup/report_untranscribed_pages.py`. "
             "Ret kilden (eller transskriber siderne) og kør scriptet igen.\n")
    L.append("## FEJL: registerhenvisninger til sider uden transskriberet dagbogstekst\n")
    L.append(f"`data/normalized/references.csv` peger på **{len(pages)} sider** "
             f"(**{sum(len(v) for v in pages.values())} henvisninger**), der ikke findes i "
             f"`data/normalized/diary.csv`. Webstedet viser kun de **{n_text_da} sider** med "
             "transskriberet tekst (bind I–X); de øvrige er udeladt fra dagbogslisten, "
             "dagbogssiderne, kurven, søgeindekset og alle henvisningstal.\n")
    L.append("Mulige årsager at undersøge pr. række: (a) sidetal uden for dagbogsteksten "
             "(kommentar-/registerdel bag teksten i bind I–X, fx VIII s. 704+), (b) bind XI "
             "(Personregister) er ikke en dagbog og skal ikke have dagbogssider, "
             "(c) OCR-/indlæsningsfejl i sidetallet i registeret.\n")
    L.append("| Bind | Sider | Henvisninger |\n|---|---|---|")
    for v in VOL_ORDER:
        if v in by_vol:
            L.append(f"| {v} | {len(by_vol[v])} | {sum(len(pages[vp]) for vp in by_vol[v])} |")
    L.append("")
    L.append(f"Desuden har **{no_page} henvisningsrækker** hverken bind eller side "
             "(registerets «se:»-krydshenvisninger). De er ikke dagbogssider, tælles som før og er ikke ændret.\n")
    L.append("### Alle sider\n")
    L.append("| Bind | Side | Henv. | Poster |\n|---|---|---|---|")
    for vp in sorted(pages, key=key):
        labels = [ents.get(e, e) for e in pages[vp]]
        shown = "; ".join(labels[:4]) + (f" … (+{len(labels) - 4})" if len(labels) > 4 else "")
        L.append(f"| {vp[0]} | {vp[1]} | {len(labels)} | {shown.replace('|', '/')} |")
    L.append("")
    L.append("## Fjernet pladsholderindhold (opgave udført)\n")
    L.append("Håndskrevet eksempelindhold med opfundne bind- og sidetal (bind XII–XXIV findes ikke) "
             "er fjernet:\n")
    L.append("- `mockup/entry.html` (opdigtet dagbogstekst, «Bind XVIII»; linkede til manglende `entry_en.html`)")
    L.append("- `mockup/search.html` / `search_en.html` (statisk demo-søgning på «Rom», «16 resultater»)")
    L.append("- `mockup/data/mock-hca.js` (ubrugt eksempeldatasæt)")
    L.append("- de 7 statiske eksempelkort i `diaries.html` / `diaries_en.html`")
    L.append("- «Søg»-kortet på `works.html` / `works_en.html` (nyt søgeresultatsside: se `docs/plan-fulltext-search.md`)\n")
    OUT.write_text("\n".join(L), encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(pages)} pages, {len(bad)} rows")


if __name__ == "__main__":
    main()
