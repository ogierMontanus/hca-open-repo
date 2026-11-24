#!/usr/bin/env python3
"""
titles.py — »Titel (+ navn) af Sted« er en PERSON (omtale), ikke et sted.

»Hertuginden af Augustenborg«, »Arvehertugen af Weimar«, »Dronning Victoria af Storbritannien«: strengen omtaler én
person; stednavnet i den er ikke et sted i teksten. Reglen (data: `data/ruler_titles.tsv`, udledt af personregistret til
Dagbøgerne og af Sørens guld, se `build_titles.py`):

  <herskertitel> [1-2 egennavne eller romertal] af <Stednavn med stort>   ->  ét spænd, type Person, omtaleform »omtale«

og `apply` lægger spændet ind i modellens forslag: modellens spænd, der ligger *inde i* strengen (stednavnet alene,
titlen alene), erstattes af det ene spænd, som markeres som sikkert (p ≥ høj grænse). Ingen numpy, så CI kan importere den.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "ruler_titles.tsv"
CAP = r"[A-ZÆØÅ][\wæøåÆØÅ'’]*"
PLACE = rf"{CAP}(?:-{CAP})*"
NAME = rf"(?:{CAP}(?:-{CAP})*|[IVX]{{1,5}}\.?)"


@lru_cache(maxsize=1)
def title_forms():
    forms = set()
    if DATA.exists():
        for line in open(DATA, encoding="utf-8"):
            f, base = line.split("\t")[:2]
            variants = {base, base.replace("prins", "prinds"), base.replace("kejser", "keiser")}
            gen = {v + x for v in variants for x in ("s", "ns", "ens")}
            if f and f not in gen:
                forms.add(f)                       # genitiv (hertugs, hertugens) ved »af« er ikke relevant
    return forms


@lru_cache(maxsize=1)
def _pattern():
    forms = title_forms()
    if not forms:
        return None
    alt = "|".join(sorted((re.escape(f) for f in forms), key=len, reverse=True))
    # titlen må stå med stort eller lille begyndelsesbogstav (tidens retskrivning: »hertugen af Weimar«)
    return re.compile(rf"(?<![\wæøå])((?i:{alt}))(?:\s+{NAME}){{0,2}}\s+af\s+({PLACE})")


def is_title(word):
    return word.lower().strip(".,") in title_forms()


def ruler_spans(text):
    """[(start, end)] for alle »Titel [navn] af Sted« i teksten (uden overlap; længste først)."""
    pat = _pattern()
    if pat is None:
        return []
    out = []
    for m in pat.finditer(text):
        out.append((m.start(1), m.end(2)))
    return out


def apply(text, conf, unc, high, p_floor=None):
    """Lægger herskerspænd ind i (conf, unc) = lister af (start, slut, type, p).
    Modellens spænd, der overlapper et herskerspænd, udgår; herskerspændet kommer ind i conf med type Person og
    p = max(modellens p for netop dette spænd, high). -> (conf, unc, antal_herskerspænd)."""
    spans = ruler_spans(text)
    if not spans:
        return conf, unc, 0
    exact = {(s, e): p for s, e, _, p in list(conf) + list(unc)}
    drop = lambda items: [x for x in items if not any(x[0] < e and s < x[1] for s, e in spans)]
    conf, unc = drop(conf), drop(unc)
    conf = conf + [(s, e, "Person", max(exact.get((s, e), 0.0), high)) for s, e in spans]
    return sorted(conf), unc, len(spans)
