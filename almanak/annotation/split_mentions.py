#!/usr/bin/env python3
"""
split_mentions.py — skil navn fra omtale i returnerede personmarkeringer.

Annotatorerne mærker hele omtalen som Person, titel og rolle medregnet (se »Foreløbige
regler« på annoteringssiderne). Dette skript deler bagefter hver personmarkering op:

  navn          kun navn:                     «Hansen», «Collins», «Humbold[t]», «H. C. Ørsted»
  titel+navn    titel/erhverv foran et navn:  «Pastor Boye», «Prof: Guldberg», «Skues: Holst»
  omtale        ingen navn, kun rolle/titel:  «Kongen», «Kronprindsessen», «min Moder»
  flere         flere navne i én streng:      «Carl og Otto Moltke»
  tvivl         kan ikke afgøres med reglerne; gennemgås i hånden (se kolonnen reason)

For navn og titel+navn angives navnekernen (name_start/name_end, samme offsets som
markeringen, slut eksklusiv), så modellen kan trænes på både hele omtalen og selve navnet.

Navnelisten (gazetteer) er for- og efternavne fra personregistret (data/normalized/entities.csv)
og almanakkens personregister. Et navn, der også bruges som almindeligt navneord i dagbøgerne
(efter »en, et, min, den …«), gives som tvivl, fordi stort begyndelsesbogstav ikke skiller
navne fra navneord i denne retskrivning.

Brug (PowerShell, fra repo-roden):
  python almanak/annotation/split_mentions.py resultat.json
  python almanak/annotation/split_mentions.py soren.tsv --out soren_split.tsv

Inddata er JSON eller TSV fra annoteringssiderne (samme formater som check_annotations.py).
Uddata er TSV med de oprindelige kolonner plus mention_kind, name_start, name_end,
name_string, title_string og reason. En opsummering skrives til skærmen.
"""
import argparse
import collections
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
from check_annotations import load_result  # noqa: E402

PERSONS = ROOT / "data" / "normalized" / "entities.csv"
ALM_PERSONS = ROOT / "almanak" / "data" / "register" / "almanak_register_persons.csv"
DIARY = ROOT / "data" / "normalized" / "diary.csv"

# Titler, rang og erhverv, der kan stå foran et navn (sammenlignes uden punktum/kolon, små bogstaver).
TITLES = set("""
hr herr herren fru frue frøken frk jomfru jfr madame mad mme mamsel mademoiselle mlle monsieur mr mrs miss
signor signora sig sgr don donna
pastor past provst biskop bisp kapellan præst sognepræst
professor prof doctor doktor dr doct magister mag candidat cand student stud
etatsraad etatsr etatsråd justitsraad justitsr justitsråd conferentsraad conferentsr konferensraad
kammerraad kammerr cancelliraad kancelliraad statsraad gehejmeraad geheimeraad hofraad
kammerherre kammerh kammerjunker hofmarskal hofjægermester overhofmarskal staldmester
grev greve grevinde comtesse baron baronesse baronnesse friherre lensgreve lord lady sir marquis marquise hertug hertuginde fyrst fyrstinde
prinds prins prindsesse prinsesse kronprinds kronprindsesse arveprinds
general gen oberst obrist major capitain kaptajn kapt capt lieutenant lieut løjtnant admiral commandeur kommandør ritmester
skuespiller skuesp skues skuespillerinde actrice sanger sangerinde componist komponist kapelmester musikus
digter forfatter maler billedhugger bildhauer arkitekt architect kobberstikker bogtrykker boghandler forlægger redacteur
grosserer grossr kjøbmand købmand consul konsul agent fabrikant
amtmand borgemester borgmester byfoged herredsfoged stiftamtmand minister
""".split())

# Ord, der alene kan omtale en bestemt person (rolle, embede, slægtskab).
ROLES = set("""
kongen dronningen enkedronningen kronprindsen kronprindsessen prindsen prindsessen prinsen prinsessen
hertugen hertuginden greven grevinden baronen baronessen fyrsten fyrstinden keiseren kejseren keiserinden kejserinden
paven biskoppen bispen provsten præsten pastoren professoren doctoren doktoren generalen admiralen ministeren
amtmanden borgemesteren digteren maleren componisten komponisten directeuren direktøren chefen
moder mor moer fader far fa broder bror søster søskende tante onkel morbroder farbroder fætter cousine kusine
bedstemoder bedstefader svoger svigerinde svigerfader svigermoder datter søn hustru kone mand enke
ven veninde værten værtinden
""".split())

FUNCTION = set("min mit mine sin sit sine din dit dine vor vort vore hans hendes deres den det de en et "
               "og & von van de del della di da du le la der den af zu von".split())

TOKEN_RE = re.compile(r"[^\s,;()«»\"]+")


def norm(tok):
    """Små bogstaver uden klammer og tegn; ä/æ, ö/ø og aa/å foldes, så stavevarianter mødes."""
    t = tok.replace("[", "").replace("]", "").strip(".:’'").lower()
    return t.replace("ä", "æ").replace("ö", "ø").replace("aa", "å")


def variants(t):
    """Genitiv og familieflertal: Collins -> collin, Heibergs -> heiberg, Holsts -> holst."""
    out = [t]
    for suf in ("'s", "’s", "s", "es", "ske", "ens", "en"):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            out.append(t[: -len(suf)])
    return out


def load_gazetteer():
    names = set()
    labels = []
    if PERSONS.exists():
        with open(PERSONS, encoding="utf-8", newline="") as f:
            labels += [r["label"] for r in csv.DictReader(f) if r["entity_type"] == "person"]
    if ALM_PERSONS.exists():
        with open(ALM_PERSONS, encoding="utf-8", newline="") as f:
            labels += [r["label"] for r in csv.DictReader(f)]
    for lab in labels:
        lab = re.sub(r",?\s*\bse( også)?:?\s.*$", "", lab, flags=re.I)
        lab = re.sub(r"\([^)]*\)", " ", lab)
        lab = re.sub(r"\bf\.\s.*$", "", lab)                       # »f. Hartmann« = pigenavn, behold kun hovednavnet
        parts = [p.strip() for p in lab.split(",")]
        for p in parts[:2]:
            for w in re.split(r"[\s\-]+", p):
                w = norm(w)
                if len(w) >= 2 and w[0].isalpha() and w not in FUNCTION and w not in TITLES and w not in ROLES:
                    names.add(w)
    return names


def load_homonyms(names, min_count=3, min_share=0.2):
    """Navne, der i dagbøgerne også bruges som almindeligt navneord: mindst `min_share` af
    forekomsterne står efter en bestemmer (»en Pige«, »min Svane«). Andersen, Posse og Agnete
    står kun undtagelsesvis sådan og regnes ikke med."""
    if not DIARY.exists():
        return set()
    det = re.compile(r"\b(?:en|et|min|sin|din|den|det|vor|hans|hendes|nogle|mange)\s+$")
    word = re.compile(r"\b[A-ZÆØÅ][a-zæøåäöü]+\b")
    after_det, total = collections.Counter(), collections.Counter()
    with open(DIARY, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            text = r["text"]
            for m in word.finditer(text):
                w = norm(m.group())
                if w in names:
                    total[w] += 1
                    if det.search(text[max(0, m.start() - 12):m.start()]):
                        after_det[w] += 1
    return {w for w, n in after_det.items() if n >= min_count and n / total[w] >= min_share}


def classify(string, names, homonyms):
    """-> (kind, name_offset_start, name_offset_end, title_string, reason); offsets relative til strengen."""
    toks = [(m.start(), m.end(), m.group()) for m in TOKEN_RE.finditer(string)]
    cls = []
    for s, e, t in toks:
        n = norm(t)
        if not n:
            cls.append("F")
        elif re.fullmatch(r"[A-ZÆØÅ]\.?", t.replace("[", "").replace("]", "")):
            cls.append("I")                                       # initial: »H.«
        elif n in FUNCTION or not t[0].isupper() and n not in TITLES and n not in ROLES:
            cls.append("F")
        elif n in TITLES:
            cls.append("T")
        elif n in ROLES:
            cls.append("R")
        elif any(v in names for v in variants(n)):
            cls.append("H" if n in homonyms else "N")
        elif t.endswith((":", ".")) and len(n) <= 6:
            cls.append("T")                                       # ukendt forkortelse foran navn: »Skues:«
        else:
            cls.append("U")
    namey = [i for i, c in enumerate(cls) if c in "NIH"]
    unknown = [toks[i][2] for i, c in enumerate(cls) if c == "U"]
    homon = [toks[i][2] for i, c in enumerate(cls) if c == "H"]

    if not namey and unknown and cls[0] == "T" and all(c in "TF" for c in cls[:cls.index("U")]):
        first = cls.index("U")                                    # »Prof: Schlessinger«: titel foran et navn, registret mangler
        return ("titel+navn", toks[first][0], toks[-1][1], string[: toks[first][0]].strip(),
                "navn ikke i registret: " + ", ".join(unknown))
    if not namey:
        if any(c == "R" for c in cls) and not unknown:
            return "omtale", None, None, "", ""
        if any(c == "T" for c in cls) and not unknown:
            return "omtale", None, None, "", "kun titel"
        return "tvivl", None, None, "", "ukendt ord: " + ", ".join(unknown or [string])
    if " og " in f" {string} " or "&" in string:
        return "flere", None, None, "", "flere navne i én streng"
    first = namey[0]
    lead = cls[:first]
    if any(c in "RU" for c in lead) or "U" in cls[first:]:
        return "tvivl", None, None, "", "ukendt ord: " + ", ".join(unknown) if unknown else "rolle og navn blandet"
    ns, ne = toks[first][0], toks[namey[-1]][1]
    title = string[: toks[first][0]].strip() if any(c == "T" for c in lead) else ""
    kind = "titel+navn" if title else "navn"
    if homon and len(namey) == 1 and not title:
        return "tvivl", ns, ne, "", "navn er også almindeligt navneord: " + ", ".join(homon)
    return kind, ns, ne, title, ""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("result", help="resultat.json eller .tsv fra annoteringssiden")
    ap.add_argument("--out", type=Path, help="TSV-uddata (standard: <resultat>_split.tsv)")
    args = ap.parse_args(argv)
    rows, _meta = load_result(args.result)
    names = load_gazetteer()
    homonyms = load_homonyms(names)
    out = args.out or Path(args.result).with_name(Path(args.result).stem + "_split.tsv")
    persons = [a for a in rows if a["type"] == "Person"]
    cols = ["post_id", "start", "end", "string", "type", "mention_kind",
            "name_start", "name_end", "name_string", "title_string", "reason"]
    kinds = collections.Counter()
    review = []
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(cols)
        for a in persons:
            s = a["string"]
            kind, ns, ne, title, reason = classify(s, names, homonyms)
            kinds[kind] += 1
            st = int(a["start"])
            name = s[ns:ne] if ns is not None else ""
            w.writerow([a["post_id"], st, a["end"], s, a["type"], kind,
                        st + ns if ns is not None else "", st + ne if ne is not None else "", name, title, reason])
            if kind == "tvivl":
                review.append((a["post_id"], s, reason))
    print(f"{len(persons)} personmarkeringer (af {len(rows)}): " +
          ", ".join(f"{k} {kinds[k]}" for k in ("navn", "titel+navn", "omtale", "flere", "tvivl")))
    for pid, s, r in review:
        print(f"  tvivl  {pid}  «{s}»  ({r})")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
