#!/usr/bin/env python3
"""
context.py — al viden, modellen må bruge om en dato: almanakposten, samme dags dagbogstekst,
almanakkens eget register (Topsøe-Jensens datohenvisninger), dagbogsregistret for dagens sider,
de regelbaserede forankringer i dagbogen (ner_page_grounding.csv) og globale navnelister.

Ingen af disse kilder er håndannoteringen: modellen kan derfor køres på alle 5.185 almanakposter.
"""
from __future__ import annotations

import collections
import csv
import functools
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "scripts" / "parsers"))
sys.path.insert(0, str(REPO / "almanak" / "annotation"))
import name_matching as nm  # noqa: E402
import build_annotation_page as bap  # noqa: E402  (tekstrens og almanakregister)
import gold as G  # noqa: E402

NORM = REPO / "data" / "normalized"
ALIGNED = REPO / "almanak" / "data" / "extracted" / "aligned.csv"


@functools.lru_cache(maxsize=200_000)
def canon(s: str) -> str:
    """Kanonisk nøgle til opslag: foldet, aa→å, kj/c→k, w→v, ph→f, th→t, klammer og apostrof væk."""
    s = nm.fold(s).replace("[", "").replace("]", "")
    s = re.sub(r"['\s-]+", " ", s).strip()
    for a, b in (("aa", "å"), ("kj", "k"), ("ph", "f"), ("th", "t"), ("c", "k"), ("w", "v")):
        s = s.replace(a, b)
    return s


def degen(s: str) -> str:
    """Uden genitiv-s (canon-form)."""
    return s[:-1] if len(s) > 3 and s.endswith("s") else s


class Gazetteer:
    """Navneformer -> entiteter. Opslag på kanonisk form; enkeltord også med én tegnforskel."""

    def __init__(self):
        self.full = collections.defaultdict(set)    # canon(form) -> {(eid, kind, role)}
        self.by_len = collections.defaultdict(set)  # len -> {canon single-word forms}  (til edit1)

    def add(self, eid, kind, form, role):
        c = canon(form)
        if len(c) < 3:
            return
        self.full[c].add((eid, kind, role))
        if " " not in c and len(c) >= 5:
            self.by_len[len(c)].add(c)

    def lookup(self, s, fuzzy=True):
        """-> (score, {(eid, kind, role)}); 1.0 eksakt/variant, 0.6 én tegnforskel."""
        key = (s, fuzzy)
        cache = self.__dict__.setdefault("_cache", {})
        if key not in cache:
            cache[key] = self._lookup(s, fuzzy)
        return cache[key]

    def _lookup(self, s, fuzzy):
        c = canon(s)
        for k in (c, degen(c)):
            if k in self.full:
                return 1.0, self.full[k]
        if fuzzy and " " not in c and len(c) >= 5:
            for k in (c, degen(c)):
                for L in (len(k) - 1, len(k), len(k) + 1):
                    for f in sorted(self.by_len.get(L, ())):
                        if f[0] == k[0] and nm.edit1(f, k):
                            return 0.6, self.full[f]
        return 0.0, set()


def entity_forms(label, kind):
    """[(form, role)] — role: sur, given, full, label."""
    if kind == "person":
        sur, given = nm.person_forms(label)
        out = [(s, "sur") for s in sur] + [(g, "given") for g in given]
        for g in given:
            for sn in sur[:2]:
                out.append((g + " " + sn, "full"))
        return out
    if kind == "place":
        forms, _ = nm.place_forms(label)
        return [(f, "label") for f in forms]
    # værk: titlen uden parentes og anførselstegn
    t = re.sub(r"\s*\([^)]*\)\s*$", "", label)
    t = re.sub(r"[»«*\"]", "", t).strip()
    return [(t, "label")] if len(t) >= 4 else []


class Context:
    def __init__(self, grounding=NORM / "ner_page_grounding.csv"):
        # almanakposter
        self.alm = {}
        for r in csv.DictReader(open(ALIGNED, encoding="utf-8")):
            t = (r["pdf_text"] or r["db_text"]).strip()
            if t:
                self.alm[r["date"]] = {"text": bap.clean(t), "page": r["print_page"]}
        # almanakregister
        reg, by_date, _ = bap.load_register()
        self.alm_reg = reg
        self.alm_by_date = {f"{y:04d}-{m:02d}-{d:02d}": ids for (y, m, d), ids in by_date.items()}
        self.alm_gaz = Gazetteer()
        for rid, info in reg.items():
            if info.get("see"):
                continue
            kind = "person" if info["k"] == "P" else "work"
            for f, role in entity_forms(info["l"], kind):
                self.alm_gaz.add(rid, kind, f, role)
        # dagbog: tekst pr. dag, sider pr. dag
        rows = G.diary_rows()
        self.diary_dates = {r["date"] for r in rows}
        self._rows = rows
        self._daymaps = {}
        # dagbogsregister
        self.ents = {r["entity_id"]: r for r in csv.DictReader(open(NORM / "entities.csv", encoding="utf-8"))
                     if r["entity_type"] in ("person", "place", "work")}
        self.page_refs = collections.defaultdict(set)
        for r in csv.DictReader(open(NORM / "references.csv", encoding="utf-8")):
            if r["entity_id"] in self.ents:
                self.page_refs[(r["vol"], r["page"])].add(r["entity_id"])
        self.dia_gaz = Gazetteer()
        self.ent_forms = {}
        for eid, r in self.ents.items():
            fs = entity_forms(r["label"], r["entity_type"])
            self.ent_forms[eid] = fs
            for f, role in fs:
                self.dia_gaz.add(eid, r["entity_type"], f, role)
        # regelbaserede forankringer i dagbogen
        self.grounded = collections.defaultdict(list)   # (vol, page) -> [(raw_s, raw_e, eid, type)]
        if Path(grounding).exists():
            for r in csv.DictReader(open(grounding, encoding="utf-8")):
                if r["mention_start"]:
                    self.grounded[(r["vol"], r["page"])].append(
                        (int(r["mention_start"]), int(r["mention_end"]), r["entity_id"],
                         self.ents.get(r["entity_id"], {}).get("entity_type", "")))
        # navneord og ordfrekvens (begge korpora)
        texts = [v["text"] for v in self.alm.values()] + [r["text"] for r in rows]
        self.nouns = {canon(w) for w in nm.corpus_nouns(texts)}
        self.freq = collections.Counter()
        for t in texts:
            for w in re.findall(r"[A-ZÆØÅ][a-zæøåäöü]+", t):
                self.freq[canon(w)] += 1

    # ---- dagbogsdag -------------------------------------------------------------------------
    def daymap(self, date):
        if date not in self._daymaps:
            parts = G.diary_day_pages(self._rows, {date}).get(date)
            self._daymaps[date] = G.DayMap(parts) if parts else None
        return self._daymaps[date]

    def diary_text(self, date):
        dm = self.daymap(date)
        return dm.view.text if dm else ""

    def diary_pages(self, date):
        dm = self.daymap(date)
        return sorted({(v, p) for _, _, v, p, _ in dm.segs}) if dm else []

    def page_gazetteer(self, date):
        g = Gazetteer()
        for pg in self.diary_pages(date):
            for eid in sorted(self.page_refs.get(pg, ())):
                for f, role in self.ent_forms[eid]:
                    g.add(eid, self.ents[eid]["entity_type"], f, role)
        return g

    def alm_date_gazetteer(self, date):
        g = Gazetteer()
        for rid in sorted(self.alm_by_date.get(date, ())):
            info = self.alm_reg[rid]
            kind = "person" if info["k"] == "P" else "work"
            for f, role in entity_forms(info["l"], kind):
                g.add(rid, kind, f, role)
        return g

    def grounded_strings(self, date):
        """{canon(streng): entitetstype} for de regelbaserede forankringer i dagens dagbogstekst."""
        dm = self.daymap(date)
        out = {}
        if not dm:
            return out
        for a, b, vol, page, row_start in dm.segs:
            row_end = row_start + (b - a)
            raw_page = None
            for s, e, eid, typ in self.grounded.get((vol, page), ()):
                if row_start <= s and e <= row_end:
                    seg_raw = dm.view.raw[a + (s - row_start):a + (e - row_start)]
                    st = nm.TextView(seg_raw).text
                    for w in {st, st.split()[-1] if st.split() else st}:
                        out[degen(canon(w))] = typ
        return out

    def logfreq(self, w):
        return math.log1p(self.freq.get(canon(w), 0))
