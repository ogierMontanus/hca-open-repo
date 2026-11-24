#!/usr/bin/env python3
"""
build_lexicon.py — navneordsliste til NER-modellen, bygget af søsterrepoet hca2modernDanish
(moderniseringsprojektet), og indskrænket til de former, der faktisk står i almanak og dagbog.

Kilder (i søsterrepoet, `resources/`):
  corpora/wordlist_ne_scored.tsv      ordliste over H.C. Andersens 163 eventyr i førsteudgavernes stavning,
                                      hvert ord mærket »noun« / »namedEntity« / ... (DDO-opslag + navneliste).
                                      Samtidig stavemåde, så »Tænderne«, »Fluen«, »Theatret« rammes direkte.
  dictionaries/ods-lemma/ods_lemmas_extracted.tsv
                                      Ordbog over det danske Sprog: opslagsord mærket Noun / Noun/Plural.
                                      Bøjes her mekanisk (bestemt form, flertal, genitiv) til de former, korpus bruger.

Uddata (committes, så modellen kan trænes uden søsterrepoet):
  almanak/ner/data/common_nouns.tsv   form (kanonisk) <TAB> kilde (hca|ods) <TAB> opslagsord
  almanak/ner/data/common_words.tsv   samme format; øvrige fællesord (tillægsord, udsagnsord ...), kun til noun_filter.py

Brug (PowerShell, fra repo-roden):
  python almanak/ner/build_lexicon.py                       # søsterrepo: ../hca2modernDanish
  python almanak/ner/build_lexicon.py --sibling D:\\sti\\til\\hca2modernDanish

Listen er et TRÆK, ikke en afvisningsliste: mange efternavne er også navneord (Bille, Svane, Lund,
Fink). Modellen lærer, hvornår et navneord i teksten er et navn, ved at sammenholde med registrene.
"""
from __future__ import annotations

import argparse
import collections
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from context import canon  # noqa: E402
import gold as G  # noqa: E402

REPO = HERE.parents[1]
OUT = HERE / "data" / "common_nouns.tsv"
ALIGNED = REPO / "almanak" / "data" / "extracted" / "aligned.csv"
WORD = re.compile(r"[A-Za-zÆØÅæøåéèüöäÖÄ]{3,}")

# bøjningsendelser for et opslagsord; ender det på -e tilføjes kun r/n/ne/rne/s osv.
SUF_CONS = ["", "s", "en", "et", "e", "er", "ene", "erne", "ens", "ets", "ers", "ernes", "enes", "ne", "nes"]
SUF_E = ["", "s", "n", "t", "r", "rne", "ns", "ts", "rs", "rnes", "ne", "nes"]


def forms_of(lemma: str):
    l = lemma.lower()
    out = {l}
    for suf in (SUF_E if l.endswith("e") else SUF_CONS):
        out.add(l + suf)
    if l.endswith("e"):
        out |= {l + "ne", l[:-1] + "er", l[:-1] + "erne", l[:-1] + "ens"}
    return out


def corpus_forms():
    """canon(ord) for alle ord (alle former) i almanak og dagbog; kun til indskrænkning af listen."""
    seen = set()
    for r in csv.DictReader(open(ALIGNED, encoding="utf-8")):
        for t in (r["pdf_text"], r["db_text"]):
            seen.update(canon(w) for w in WORD.findall(t or ""))
    for r in G.diary_rows():
        seen.update(canon(w) for w in WORD.findall(r["text"]))
    return seen


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--sibling", type=Path, default=REPO.parent / "hca2modernDanish")
    args = ap.parse_args()
    res = args.sibling / "resources"
    if not res.exists():
        sys.exit(f"Søsterrepoet findes ikke: {args.sibling}")
    seen = corpus_forms()
    out = {}
    n_hca = n_ods = 0
    for r in csv.DictReader(open(res / "corpora" / "wordlist_ne_scored.tsv", encoding="utf-8"), delimiter="\t"):
        if r["ne_label"] == "noun" and float(r["ne_score"] or 1) <= 0.3:
            c = canon(r["word"])
            if c in seen and c not in out:
                out[c] = ("hca", r["word"])
                n_hca += 1
    lemmas = collections.defaultdict(set)
    for r in csv.DictReader(open(res / "dictionaries" / "ods-lemma" / "ods_lemmas_extracted.tsv", encoding="utf-8"), delimiter="\t"):
        if r["char_issue"] in ("Noun", "Noun/Plural") and len(r["word"]) >= 3:
            lemmas[r["word"].lower()].add(r["word"])
    for l in sorted(lemmas):
        for f in forms_of(l):
            c = canon(f)
            if c in seen and c not in out and len(c) >= 3:
                out[c] = ("ods", l)
                n_ods += 1
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        for c in sorted(out):
            fh.write(f"{c}\t{out[c][0]}\t{out[c][1]}\n")
    print(f"{len(out)} former ({n_hca} fra eventyrenes ordliste, {n_ods} fra ODS) -> {OUT}")

    # øvrige fællesord (tillægsord, udsagnsord, biord ...): bruges kun af navneordsfilteret, ikke som træk
    words = {}
    for r in csv.DictReader(open(res / "corpora" / "wordlist_ne_scored.tsv", encoding="utf-8"), delimiter="\t"):
        if r["ne_label"] == "lowercase":          # ordet står med lille begyndelsesbogstav i eventyrene
            c = canon(r["word"])
            if c in seen and c not in out:
                words[c] = ("hca", r["word"])
    adj, verbs = set(), set()
    for r in csv.DictReader(open(res / "dictionaries" / "ods-lemma" / "ods_lemmas_extracted.tsv", encoding="utf-8"), delimiter="\t"):
        w = r["word"].lower()
        if len(w) >= 4 and r["char_issue"] in ("Adjective", "Adverb/Adjective"):
            adj.add(w)
        elif len(w) >= 4 and r["char_issue"] in ("Verb", "Preterite"):
            verbs.add(w)
    for l in sorted(adj):
        for f in {l, l + "t", l + "e", l + "ere", l + "este", l + "st", l + "s"}:
            c = canon(f)
            if c in seen and c not in out and c not in words:
                words[c] = ("ods", l)
    for l in sorted(verbs):
        st = l[:-1] if l.endswith("e") else l
        for f in {l, st, st + "r", st + "et", st + "t", st + "ede", st + "ende", st + "de", st + "te", st + "es"}:
            c = canon(f)
            if c in seen and c not in out and c not in words and len(c) >= 4:
                words[c] = ("ods", l)
    with open(OUT.with_name("common_words.tsv"), "w", encoding="utf-8", newline="") as fh:
        for c in sorted(words):
            fh.write(f"{c}\t{words[c][0]}\t{words[c][1]}\n")
    print(f"{len(words)} øvrige fællesord -> common_words.tsv")


if __name__ == "__main__":
    main()
