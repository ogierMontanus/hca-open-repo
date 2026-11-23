#!/usr/bin/env python3
"""
candidates.py — kandidatspænd i en almanakpost eller dagbogsdag (§3.3 fase 2).

Et kandidatspænd er 1–5 ord i træk, hvor første og sidste ord har stort begyndelsesbogstav
(eller er en udgiverklamme som »Da[n]mark«), og som ikke krydser tegnsætning — undtagen
punktum/kolon efter en titel eller et forbogstav (»Prof: Schlessinger«, »H. C. Ørsted«).
Kapitalisering er en *nødvendig* betingelse (fanger ~98 % af guldspændene), ikke et navnesignal:
modellen afgør resten.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "parsers"))
import name_matching as nm  # noqa: E402

TOKEN = re.compile(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ\[\]'’]+(?:-[0-9A-Za-zÀ-ÖØ-öø-ÿ\[\]'’]+)*")
MAX_TOK = 5


def tokens(text):
    return [(m.start(), m.end(), m.group(0)) for m in TOKEN.finditer(text)]


def _cap(w):
    w = w.lstrip("[")
    return bool(w) and (w[0].isupper() or (w[0] == "0" and len(w) == 1))   # »0 Neill« (OCR for O)


def _joinable(text, prev_tok, gap):
    """Må et spænd fortsætte hen over mellemrummet `gap` efter `prev_tok`?"""
    if re.fullmatch(r"\s+", gap):
        return True
    if re.fullmatch(r"[.:]\s+", gap):
        w = nm.fold(prev_tok.strip("[]"))
        return len(w) <= 2 or w in nm.TITLES or w in {"st", "sct", "prof", "etatsr"}
    if re.fullmatch(r"-\s*", gap):
        return True
    return False


def generate(text):
    """[(start, end)] for alle kandidatspænd i teksten."""
    toks = tokens(text)
    out = []
    for i, (s, _, w) in enumerate(toks):
        if not _cap(w):
            continue
        for j in range(i, min(i + MAX_TOK, len(toks))):
            if j > i and not _joinable(text, toks[j - 1][2], text[toks[j - 1][1]:toks[j][0]]):
                break
            if _cap(toks[j][2]) and toks[j][2] != "0":
                out.append((s, toks[j][1]))
    return out
