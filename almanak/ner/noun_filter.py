#!/usr/bin/env python3
"""
noun_filter.py — hold åbenlyse fællesnavne ud af forslagene (»Tænderne«, »Fluen«, »Hele«).

Alle navneord er stort begyndt i tidens retskrivning, så store bogstaver siger intet. Navneordslisten
(`data/common_nouns.tsv`, bygget af moderniseringsrepoet, se build_lexicon.py) kender de fleste. Men mange
fællesnavne er alligevel navne på sted, institution eller rolle i dette materiale (»Theatret«, »Kirken«,
»Kongen«, »Corso«): 19 % af Sørens markeringer består kun af kendte navneord. Derfor er filteret ikke
»drop alle navneord«, men:

  et forslag, hvis ord ALLE er kendte fællesnavne, udelades, medmindre
    1. det er bekræftet af et register (spændet kobles til en post, eller formen findes i et af registrene), eller
    2. spændet har titel (»Frøken«, »Grev« ...), eller
    3. ordet er på listen over navnelignende fællesnavne: `data/entity_like_nouns.txt` (håndholdt:
       roller, institutioner, bygninger) plus alle ord, der står alene som markering i de håndannoterede data.

Listen i punkt 3 er et eksplicit, redigerbart valg. I krydsvalideringen bygges den kun af træningsblokkene.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from context import canon, degen  # noqa: E402
import name_matching as nm  # noqa: E402

SEED = HERE / "data" / "entity_like_nouns.txt"
PARTICLES = {"af", "von", "van", "de", "di", "da", "du", "la", "le", "del", "der", "zu", "zum", "im", "i", "og"}   # som features.PARTICLES


def key(word):
    """Opslagsnøgle for et ord: canon uden genitiv-s."""
    return degen(canon(word.rstrip(".:")))


def core_tokens(span):
    return [w for w in span.split() if nm.fold(w.rstrip(".:")) not in PARTICLES and nm.fold(w.rstrip(".:")) not in nm.TITLES]


def seed_words():
    out = set()
    if SEED.exists():
        for line in open(SEED, encoding="utf-8"):
            line = line.split("#")[0].strip()
            if line:
                out.add(key(line))
    return out


class NounFilter:
    def __init__(self, ctx, allow=()):
        self.ctx = ctx
        self.allow = set(allow) | seed_words()

    def common(self, span):
        toks = core_tokens(span)
        en = self.ctx.ext_words
        return bool(toks) and all(canon(w) in en or degen(canon(w)) in en for w in toks)

    def corroborated(self, span, linked=False):
        if linked:
            return True
        words = span.split()
        if any(nm.fold(w.rstrip(".:")) in nm.TITLES for w in words[:-1] if len(words) > 1):
            return True
        core = " ".join(core_tokens(span))
        for g in (self.ctx.alm_gaz, self.ctx.dia_gaz):
            if g.lookup(core, fuzzy=False)[0]:
                return True
        return False

    def keep(self, span, linked=False):
        if not self.common(span):
            return True
        if self.corroborated(span, linked):
            return True
        return all(key(w) in self.allow for w in core_tokens(span))


def allow_from_gold(entries_gold):
    """entries_gold: iterable af (tekst, {(s, e): type}) -> ord, der står alene som markering."""
    out = set()
    for text, gold in entries_gold:
        for (s, e) in gold:
            toks = core_tokens(text[s:e])
            if toks and len(toks) <= 2:
                out |= {key(w) for w in toks}
    return out
