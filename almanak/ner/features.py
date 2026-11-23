#!/usr/bin/env python3
"""
features.py — træk for et kandidatspænd (»diary2almanac«).

Trækkene er kildesymmetriske, så dagbogsdagene også kan bruges som træningsdata:
  own_idx    kildens eget register for dagen   (almanak: Topsøe-Jensens datohenvisninger;
                                                 dagbog: references.csv for dagens sider)
  other_idx  den anden kildes register for dagen
  other_txt  står strengen i den anden kildes tekst samme dag?
  other_grd  er strengen *forankret af reglerne* i den anden kildes tekst samme dag
             (dagbog: ner_page_grounding.csv; almanak: almanakregistrets navne fundet i posten)
  alm_glob / dia_glob   står strengen nogetsteds i de to registre (navneliste, ingen dato)
plus form (ordantal, titel, genitiv, klammer, sætningsstart), navneordsliste og ordene omkring.
"""
from __future__ import annotations

import re

import numpy as np

import candidates as C
from context import Gazetteer, canon, degen, nm

PREV_CUES = ["hos", "til", "fra", "med", "af", "i", "paa", "for", "og", "besøgt", "besøg", "brev", "ved",
             "over", "mod", "efter", "om", "fru", "hr", "sammen", "seet", "hørt", "læst", "spillede",
             "reist", "kjørt", "kom", "gik", "<start>"]
NEXT_CUES = ["og", "i", "hos", "med", "til", "fra", "som", "der", "har", "var", "kom", "<slut>"]
KINDS = ["person", "place", "work"]
PARTICLES = {"af", "von", "van", "de", "di", "da", "du", "la", "le", "del", "der", "zu", "zum", "im", "i", "og"}
DEF_SUFFIX = re.compile(r"(?:en|et|ne|erne|ene|ets|ens)$")


def _core(span_text):
    """Titler foran og genitiv-s bagved væk; -> (kerne, antal titler)."""
    toks = span_text.split()
    n = 0
    while len(toks) > 1 and nm.fold(toks[0].rstrip(".:")) in nm.TITLES:
        toks = toks[1:]
        n += 1
    return " ".join(toks), n


class DayFeatures:
    """Alt, der er fælles for spændene i én tekst (én kilde, én dato)."""

    def __init__(self, ctx, date, src, text):
        self.ctx, self.date, self.src, self.text = ctx, date, src, text
        alm_text = ctx.alm.get(date, {}).get("text", "")
        dia_text = ctx.diary_text(date)
        self.other_text = dia_text if src == "almanak" else alm_text
        self.other_fold = canon(self.other_text)
        g_date, g_page = ctx.alm_date_gazetteer(date), ctx.page_gazetteer(date)
        self.own_idx, self.other_idx = (g_date, g_page) if src == "almanak" else (g_page, g_date)
        if src == "almanak":
            self.other_grd = ctx.grounded_strings(date)
        else:   # almanakregistrets navne, fundet i almanakposten med reglerne
            self.other_grd = {}
            for c, ents in sorted(g_date.full.items()):
                if re.search(rf"(?<![a-zæøå]){re.escape(c)}s?(?![a-zæøå])", canon(alm_text)):
                    for _, kind, _ in sorted(ents):
                        self.other_grd[degen(c)] = kind
        self.toks = C.tokens(text)

    def _lookup(self, g: Gazetteer, core):
        toks = core.split()
        full, fk = g.lookup(core)
        last, lk = g.lookup(toks[-1]) if toks else (0.0, set())
        anyt = max([g.lookup(t, fuzzy=False)[0] for t in toks] or [0.0])
        kinds = {k for _, k, _ in (fk | lk)}
        return [full, last, anyt] + [1.0 if k in kinds else 0.0 for k in KINDS]

    def _roles(self, w):
        roles = set()
        for g in (self.own_idx, self.other_idx, self.ctx.alm_gaz, self.ctx.dia_gaz):
            sc, ents = g.lookup(w, fuzzy=False)
            if sc:
                roles |= {r for _, _, r in ents}
        return roles

    def _neighbour_cap(self, i_tok, step):
        """Står der et navnelignende ord (stort, ikke navneord) lige ved siden af, som spændet kunne
        være forlænget med?"""
        j = i_tok + step
        if not (0 <= j < len(self.toks)):
            return 0.0
        a, b = (self.toks[i_tok], self.toks[j]) if step > 0 else (self.toks[j], self.toks[i_tok])
        if not C._joinable(self.text, a[2], self.text[a[1]:b[0]]):
            return 0.0
        w = self.toks[j][2]
        if not w[:1].isupper() or canon(w) in self.ctx.nouns:
            return 0.0
        if step < 0 and nm.fold(w.rstrip(".:")) in nm.TITLES:
            return 0.5   # titel foran: spændet burde starte der
        return 1.0

    def vector(self, s, e):
        t = self.text
        span = t[s:e]
        core, ntit = _core(span)
        ctoks = core.split()
        last = ctoks[-1] if ctoks else span
        first = ctoks[0] if ctoks else span
        prev = [w for (a, b, w) in self.toks if b <= s]
        nxt = [w for (a, b, w) in self.toks if a >= e]
        pw = nm.fold(prev[-1]) if prev else "<start>"
        nw = nm.fold(nxt[0]) if nxt else "<slut>"
        before = t[max(0, s - 3):s]
        sent_init = s == 0 or bool(re.search(r"[.!?»]\s*$", before)) and not (prev and nm.fold(prev[-1]) in nm.TITLES)
        i0 = next(i for i, x in enumerate(self.toks) if x[0] == s)
        i1 = next(i for i, x in enumerate(self.toks) if x[1] == e)
        mids = [w for w in span.split()[1:-1] if w[:1].islower()]
        cl0 = canon(last)
        f = [
            len(span.split()), np.log1p(len(span)), float(ntit > 0), ntit,
            float(any(nm.fold(w) not in PARTICLES for w in mids)), float(any(nm.fold(w) in PARTICLES for w in mids)),
            self._neighbour_cap(i0, -1), self._neighbour_cap(i1, +1),
            float(bool(DEF_SUFFIX.search(cl0)) and len(ctoks) == 1),
            float(DEF_SUFFIX.sub("", cl0) in self.ctx.nouns and len(cl0) > 4),
            float(len(ctoks) >= 2 and "given" in self._roles(ctoks[0]) and "sur" in self._roles(last)),
            float(len(ctoks) == 1 and "given" in self._roles(last)),
            float(len(ctoks) == 1 and "sur" in self._roles(last)),
            float(span.split()[0].rstrip(".:").lower() in nm.TITLES and len(span.split()) == 1),
            float("[" in span), float(canon(last).endswith("s")), float(sent_init),
            float(self.src == "almanak"), float(bool(re.search(r"\d", span))),
            float(canon(last) in self.ctx.nouns or degen(canon(last)) in self.ctx.nouns),
            float(canon(first) in self.ctx.nouns), self.ctx.logfreq(last),
            float(len(canon(core)) <= 3),
        ]
        f += [1.0 if pw == c else 0.0 for c in PREV_CUES] + [float(pw not in PREV_CUES)]
        f += [1.0 if nw == c else 0.0 for c in NEXT_CUES]
        for g in (self.own_idx, self.other_idx, self.ctx.alm_gaz, self.ctx.dia_gaz):
            f += self._lookup(g, core)
        cc, cl = degen(canon(core)), degen(canon(last))
        occ = lambda k: bool(k) and re.search(rf"(?<![a-zæøå]){re.escape(k)}s?(?![a-zæøå])", self.other_fold) is not None
        f += [float(occ(cc)), float(occ(cl)),
              float(cc in self.other_grd or cl in self.other_grd)]
        gk = self.other_grd.get(cc) or self.other_grd.get(cl)
        f += [1.0 if gk == k else 0.0 for k in KINDS]
        return f


FEATURE_NAMES = (
    ["ntok", "lognchar", "has_title", "n_title", "lower_mid", "particle_mid", "prev_namelike", "next_namelike",
     "definite_form", "noun_stem", "given_plus_sur", "only_given", "only_sur", "title_alone", "bracket", "ends_s", "sent_init", "is_alm",
     "digit", "last_noun", "first_noun", "logfreq", "short"]
    + [f"prev={c}" for c in PREV_CUES] + ["prev=other"] + [f"next={c}" for c in NEXT_CUES]
    + [f"{g}_{x}" for g in ("own_idx", "other_idx", "alm_glob", "dia_glob")
       for x in ["full", "last", "anytok"] + [f"kind_{k}" for k in KINDS]]
    + ["other_txt_core", "other_txt_last", "other_grd"] + [f"other_grd_{k}" for k in KINDS]
)


def featurize(ctx, date, src, text):
    """-> (spans, X)"""
    df = DayFeatures(ctx, date, src, text)
    spans = C.generate(text)
    X = np.array([df.vector(s, e) for s, e in spans], dtype=float) if spans else np.zeros((0, len(FEATURE_NAMES)))
    assert X.shape[1] == len(FEATURE_NAMES), (X.shape, len(FEATURE_NAMES))
    return spans, X
