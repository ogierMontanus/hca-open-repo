#!/usr/bin/env python3
"""
name_matching.py — fælles, regelbaseret navnesøgning i dagbogs- og almanaktekst.

Bruges af `scripts/parsers/ner_page_grounding.py` (dagbogen) og
`almanak/ner/` (almanakken). Kun standardbiblioteket.

Indhold:
  fold()          længdebevarende foldning: små bogstaver, accenter væk, ö→ø, ä→æ, ’→'
  TextView        rå tekst → løbende tekst (linjetag »038-03 « fjernet, orddeling ved linjeskift
                  samlet før lille bogstav, mellemrum samlet) med tegn-for-tegn-kort tilbage til rå
                  offsets. Svarer til tekstversionen `diary.csv-2026-11-linjetags-fjernet-orddeling-samlet`.
  variant_regex() søgeform → regex på foldet tekst, der tåler aa/å, kj/k/c, w/v, ph/f, th/t,
                  apostrof/mellemrum (»O’Neill« ~ »O Neill«) og genitiv-s
  person_forms(), place_forms()   søgeformer fra en registeretiket, inkl. varianter i parentes
                  (»Ahrens (Arenz)«, »Galatz (Galati)«) og »X, Y«-steder
  find(), fuzzy_find()            helordsfund (stort begyndelsesbogstav krævet; fanger ikke
                  pronomenet »hans« som fornavnet Hans) og fund med én tegnforskel (navne ≥ 5 bogstaver)
  extend_title()  udvid et fund med titel/rolle lige foran (»Fru«, »Etatsraad«, »Prof:«), jf.
                  annoteringsvejledningen »titel og rang medtages«
"""

from __future__ import annotations

import re
import unicodedata

_PRE = str.maketrans({"ö": "ø", "Ö": "Ø", "ä": "æ", "Ä": "Æ", "’": "'", "‘": "'", "`": "'", "´": "'"})
LETTERS = "a-zæøå0-9"
LINE_TAG = re.compile(r"^\s*\d{3}-\d{2}\s+")

TITLES = {
    "fru", "frue", "hr", "herr", "monsieur", "madame", "mad", "mme", "mamsel", "jomfru", "jomf", "jfr",
    "frøken", "frk", "pastor", "prof", "professor", "etatsraad", "etatsråd", "conferentsraad",
    "justitsraad", "kancelliraad", "kammerherre", "kammerjunker", "grev", "greve", "grevinde",
    "comtesse", "baron", "baronesse", "baroninde", "capt", "capitain", "kaptajn", "lieutenant", "dr",
    "doctor", "biskop", "provst", "skuespiller", "skuespillerinde", "skuespillerinden", "maleren",
    "digteren", "billedhuggeren", "componisten", "faderen", "moderen", "fader", "moder", "tante",
    "onkel", "lille", "gamle", "unge", "fyrst", "fürst", "fyrstinde", "prinds", "prindsesse",
    "prinsesse", "hertug", "hertuginde", "general", "generalinde", "oberst", "admiral", "minister",
    "ministeren", "consul", "agent", "assessor", "kammerraad", "kammerråd", "cand", "student",
}
# ord, der står i et register som navn, men i teksten næsten altid er noget andet
COMMON_WORDS = {"hans", "hun", "han", "den", "det", "med", "som", "til", "fra", "paa", "efter", "under"}


def fold_char(c: str) -> str:
    c = c.translate(_PRE)
    if c in "æøåÆØÅ":
        return c.lower()
    d = unicodedata.normalize("NFD", c)
    return d[0].lower() if d else c


def fold(s: str) -> str:
    return "".join(fold_char(c) for c in s)


class TextView:
    """Løbende tekst med kort tilbage til rå offsets."""

    def __init__(self, raw: str, line_tags: bool = True):
        self.raw = raw
        out, idx = [], []
        pos = 0
        for line in raw.split("\n"):
            ls = pos
            pos += len(line) + 1
            m = LINE_TAG.match(line) if line_tags else None
            cs = ls + (m.end() if m else 0)
            content = raw[cs:ls + len(line)].rstrip()
            lead = len(content) - len(content.lstrip())
            cs += lead
            content = content.strip()
            if not content:
                continue
            if out:
                if out[-1] == "-" and re.match(r"[a-zæøåäöü]", content):
                    out.pop(); idx.pop()
                elif out[-1] != "-":
                    out.append(" "); idx.append(cs - 1)
            for i, ch in enumerate(content):
                if ch.isspace():
                    if out and out[-1] == " ":
                        continue
                    ch = " "
                out.append(ch); idx.append(cs + i)
        self.text = "".join(out)
        self.idx = idx
        self.fold = fold(self.text)

    def raw_span(self, s: int, e: int) -> tuple[int, int]:
        return self.idx[s], self.idx[e - 1] + 1


def variant_regex(form: str, genitive: bool = True) -> "re.Pattern[str]":
    f = fold(form).strip()
    out, i = [], 0
    while i < len(f):
        two = f[i:i + 2]
        if two == "aa":
            out.append("(?:aa|å)"); i += 2; continue
        if two == "kj":
            out.append("(?:kj?|c)"); i += 2; continue
        if two == "ph":
            out.append("(?:ph|f)"); i += 2; continue
        if two == "th":
            out.append("th?"); i += 2; continue
        c = f[i]
        out.append({"å": "(?:å|aa)", "k": "(?:kj?|c)", "c": "(?:c|kj?)", "w": "[wv]", "v": "[wv]",
                    "f": "(?:f|ph)", "'": "['\\s]?", " ": "[\\s']+", ".": "\\.?\\s*", "-": "[-\\s]?"}
                   .get(c, re.escape(c)))
        i += 1
    suf = "(?:s|'s)?" if genitive else ""
    return re.compile(rf"(?<![{LETTERS}]){''.join(out)}{suf}(?![{LETTERS}])")


def _paren_variants(main: str, inner: str) -> list[str]:
    """Varianter i parentes: ét ord med samme forbogstav som hovedformen (»Ahrens (Arenz)«)."""
    out = []
    for part in re.split(r"[,;/]|\beller:?", inner):
        w = part.strip(" ?.")
        if re.fullmatch(r"[A-ZÆØÅÄÖÜ][\w'’-]{2,}", w) and main and fold(w)[0] == fold(main)[0]:
            out.append(w)
    return out


def strip_trailing_years(label: str) -> str:
    return re.sub(r"\s*\([^)]*\d[^)]*\)\s*$", "", label).strip()


def person_forms(label: str) -> tuple[list[str], list[str]]:
    """(efternavneformer, fornavneformer) fra »Efternavn (Variant), Fornavn (Kaldenavn) (årstal)«."""
    core = strip_trailing_years(label)
    core = re.split(r",?\s*se:\s*", core)[0]
    sur, _, rest = core.partition(",")
    surnames, given = [], []
    m = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", sur.strip())
    sur_main = (m.group(1) if m else sur).strip()
    if len(sur_main) >= 3:
        surnames.append(sur_main)
    if m:
        surnames += _paren_variants(sur_main, m.group(2))
    rest = re.sub(r",.*$", "", rest)   # »Fornavn, f. Pigenavn« -> Fornavn
    for g in re.findall(r"\(([^)]*)\)", rest):
        given += [w for w in re.findall(r"[A-ZÆØÅ][a-zæøåäöüé]{2,}", g)]
    rest = re.sub(r"\([^)]*\)", "", rest)
    toks = [t for t in re.split(r"[\s.]+", rest.strip()) if t]
    if toks and len(toks[0]) >= 3 and toks[0][0].isupper() and toks[0].isalpha():
        given.insert(0, toks[0])
    return surnames, [g for g in given if fold(g) not in COMMON_WORDS or g[0].isupper()]


def place_forms(label: str) -> tuple[list[str], str | None]:
    core = strip_trailing_years(label)
    forms = []
    m = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", core)
    main = (m.group(1) if m else core).strip()
    for part in main.split(","):
        p = part.strip()
        if len(p) >= 3 and p[0].isupper():
            forms.append(p)
    if m:
        forms += _paren_variants(main, m.group(2))
    words = main.split(",")[0].split()
    fallback = words[0] if len(words) > 1 and len(words[0]) >= 3 else None
    return list(dict.fromkeys(forms)), fallback


def find(view: TextView, form: str, require_upper: bool = True) -> list[tuple[int, int]]:
    if not form or len(fold(form)) < 3:
        return []
    upper = require_upper and form[:1].isupper()
    hits = []
    for m in variant_regex(form).finditer(view.fold):
        if upper and not view.text[m.start()].isupper():
            continue
        hits.append((m.start(), m.end()))
    return hits


def edit1(a: str, b: str) -> bool:
    """Levenshtein-afstand ≤ 1."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la > lb:
        a, b, la, lb = b, a, lb, la
    i = 0
    while i < la and a[i] == b[i]:
        i += 1
    return a[i + (la == lb):] == b[i + 1:]


_TOKEN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ'’]+")


def fuzzy_find(view: TextView, form: str, exclude: list[tuple[int, int]] = (),
               reject: "set[str] | frozenset[str]" = frozenset()) -> list[tuple[int, int]]:
    """Ét-ords-fund med én tegnforskel (navne ≥ 5 bogstaver), genitiv-s tilladt.
    `reject`: foldede ord, der aldrig må tages som variant (almindelige navneord som »Billet«,
    eller andre ord, kalderen vil udelukke)."""
    f = fold(form)
    if " " in f or len(f) < 5:
        return []
    hits = []
    for m in _TOKEN.finditer(view.text):
        w = m.group(0)
        if not w[0].isupper() or abs(len(w) - len(f)) > 2 or len(w) < 5:
            continue
        s, e = m.start(), m.end()
        if any(s < xe and xs < e for xs, xe in exclude):
            continue
        fw = view.fold[s:e]
        if fw in reject or (fw.endswith("s") and fw[:-1] in reject):
            continue
        if fw == f or fw == f + "s":
            continue  # eksakte fund tages af find()
        if edit1(fw, f) or (fw.endswith("s") and edit1(fw[:-1], f)):
            if fw[0] == f[0] or fw[1:] == f[1:]:
                hits.append((s, e))
    return hits


_NOUN_CUE = re.compile(r"(?<![A-Za-zÆØÅæøå])(?:en|et|min|mit|sin|sit|din|dit|vor|vort|hver|nogle|mange|"
                       r"denne|dette|hans|hendes|deres|ingen|intet)\s+([A-ZÆØÅ][a-zæøåäöü]+)")


def corpus_nouns(texts, min_count: int = 2) -> set[str]:
    """Ord med stort begyndelsesbogstav, der i korpusset står efter artikel/stedord (»en Billet«,
    »min Stambog«): i 1800-tals-retskrivningen er de navneord, ikke navne. Foldede former."""
    from collections import Counter
    c = Counter()
    for t in texts:
        for m in _NOUN_CUE.finditer(t):
            c[fold(m.group(1))] += 1
    return {w for w, n in c.items() if n >= min_count}


def extend_title(view: TextView, s: int, max_tokens: int = 2) -> int:
    """Flyt start bagud over op til to titler/roller lige foran (»Skuespillerinden Frøken Hagen«)."""
    for _ in range(max_tokens):
        m = re.search(r"([A-Za-zÀ-ÖØ-öø-ÿ]+)[.:]?\s$", view.text[max(0, s - 25):s])
        if not m or fold(m.group(1)) not in TITLES:
            break
        s = s - (len(m.group(0)))
    return s
