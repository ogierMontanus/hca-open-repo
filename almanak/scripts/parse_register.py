#!/usr/bin/env python3
"""
parse_register.py — konvertér Værkregister (trykt s. 328–338) og
Personregister (s. 339–388) i H.C. Andersens Almanakker 1833–1873
(DSL 1990) fra PDF'ens ABBYY-tekstlag til tre CSV-filer med
almanak-lokale registernøgler.

Nøgler (lokale for almanakken, ikke Reg-id'er fra dagbogsregistrene):
  ALMP0001 …   personregisteropslag, i trykkets rækkefølge
  ALMW0001 …   værkregisteropslag, i trykkets rækkefølge
Nøglerne er FORELØBIGE: de følger rækkefølgen i dette OCR-lag. Når en ny OCR
erstatter det (almanak/docs/implementeringsplan.md, trin 1), skal nøglerne
frigives først efter en crosswalk, så annotationer, der henviser til dem,
ikke mister deres mål.

Målt layout (PDF-side = trykt side + 12; PDF 340–400):
  * Begge registre har to spalter pr. side: venstre x≈46, højre x≈199.
  * Et opslag begynder ved spaltens grundlinje (≤ +3 pt); fortsættelseslinjer
    er indrykket ≈ 8–10 pt. Linjer indrykket mere end det er overskrifter
    i værkregistret (»Eventyr«, »Enkelte eventyr alfabetisk« …).
  * Levende kolumnetitel (y0 < 52) og folio (y1 > 495) udelades.

Et opslag er: overskriftsord, evt. beskrivelse, derefter henvisninger
»år d.m, d.m. år d.m …« (også »Bagsiden af <måned>«, »Bag i almanakken«,
»Foran i almanakken«). »÷« (divisionstegn) foran henvisningerne betyder i personregistret, at personen
ikke findes i Dagbøgernes personregister (bd. XI) eller ikke er identificeret (`not_in_xi`); ved en titel i
værkregistret, at værket ikke findes i Birger Frank Nielsens bibliografi (`not_in_bfn`). OCR læser tegnet som
»4-«, »-r«, »+«, »-5-« … eller slet ikke; derfor aflæses det i billedet (`register_glyphs.py`), og tekstlagets
gæt står kun som kontrol i `divsign_ocr`. Se almanak/docs/registertegn.md.

OCR-forvekslinger i tal håndteres, men ikke gættes: et årstal eller en dato,
der ikke kan læses entydigt, får `valid=0` og beholdes i `raw`.

Output (committes; foreløbige og ikke korrekturlæst):
  almanak/data/register/almanak_register_persons.csv
  almanak/data/register/almanak_register_works.csv
  almanak/data/register/almanak_register_refs.csv

Brug (PowerShell, fra repo-roden):
  python almanak/scripts/parse_register.py --pdf "C:\\...\\andersen-hc_almanakker.pdf" --cache almanak/data/cache/register_lines.json
"""

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
OUT = REPO_ROOT / "almanak" / "data" / "register"
WORK_PAGES = range(340, 351)      # 1-baserede PDF-sider
PERSON_PAGES = range(351, 401)
PAGE_OFFSET = 12

MONTHS = {"januar": 1, "februar": 2, "marts": 3, "april": 4, "maj": 5, "juni": 6, "juli": 7, "august": 8,
          "september": 9, "oktober": 10, "november": 11, "december": 12}
MONTH_RE = "|".join(MONTHS)

# OCR-forvekslinger i tal
DIG = str.maketrans({"i": "1", "I": "1", "l": "1", "j": "1", "h": "1", "o": "0", "O": "0", "g": "9", "q": "9", "z": "2", "Z": "2", "&": "8"})
YEAR_CHARS = "0-9iIljhoOgqzZ&"
YEAR_TOK = re.compile(rf"^[{YEAR_CHARS}]{{4}}$")
DM_TOK = re.compile(rf"^([{YEAR_CHARS}]{{1,2}})[.,\-]\s?([{YEAR_CHARS}]{{1,2}})[.,]?$")
PLUS = re.compile(r"(?<![\w-])(?:4-|-I-|-r|-i-|\+|-5-|-4-|-4|4\")(?=[\s.,]|$)")   # OCR-former af »÷«


def read_lines(pdf, cache):
    if cache and Path(cache).exists():
        return {int(k): v for k, v in json.loads(Path(cache).read_text(encoding="utf-8")).items()}
    try:
        import fitz
    except ImportError:
        sys.exit("PyMuPDF kræves:  pip install pymupdf")
    doc = fitz.open(pdf)
    pages = {}
    for n in list(WORK_PAGES) + list(PERSON_PAGES):
        L = []
        for b in doc[n - 1].get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                t = "".join(s["text"] for s in l["spans"])
                if t.strip():
                    L.append({"bbox": [round(x, 1) for x in l["bbox"]], "t": t})
        pages[n] = L
    if cache:
        Path(cache).parent.mkdir(parents=True, exist_ok=True)
        Path(cache).write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    return pages


def join_lines(parts):
    out = ""
    for p in parts:
        p = p.rstrip()
        if not out:
            out = p
        elif out.endswith("\xad"):
            out = out[:-1] + p.lstrip()
        elif out.endswith("-") and p[:1].islower() and not out.endswith(" -"):
            out = out[:-1] + p.lstrip()
        else:
            out += " " + p.lstrip()
    return re.sub(r"\s+", " ", out.replace("\xad", "")).strip()


def starts_with_ref(t):
    tk = t.split()
    return len(tk) >= 2 and bool(YEAR_TOK.match(tk[0].rstrip(",."))) and bool(DM_TOK.match(tk[1].rstrip(",")))


def entries_of(pages, page_range, headings):
    """[(pdf_page, section, text)] i trykkets rækkefølge. `headings`: værkregistret har
    centrerede overskrifter; en linje der begynder med et årstal + dato hører til
    det foregående opslag (eller til overskriften, hvis intet opslag er åbent)."""
    ents, section = [], ""
    cur, prev_heading = None, False
    for n in page_range:
        lines = [l for l in pages.get(n, []) if l["bbox"][1] > 52 and l["bbox"][3] < 495]
        if n == 351:  # indledning til personregistret
            lines = [l for l in lines if l["bbox"][1] > 190]
        if n == 340:  # titel og forklaring til værkregistret
            lines = [l for l in lines if l["bbox"][1] > 140]
        cols = [[l for l in lines if l["bbox"][0] < 190], [l for l in lines if l["bbox"][0] >= 190]]
        for ci, col in enumerate(cols):
            base = 46.0 if ci == 0 else 199.6
            col.sort(key=lambda l: l["bbox"][1])
            for l in col:
                x, t = l["bbox"][0], l["t"].strip()
                ref_line = starts_with_ref(t)
                if x <= base + 3.5 and not ref_line and (t[:1].isalpha() or t[:1] in "»«(\"'"):
                    if cur:
                        ents.append(cur)
                    cur, prev_heading = {"pdf_page": n, "section": section, "parts": [t], "boxes": [(n, l["bbox"])]}, False
                elif x > base + 13 and headings and not ref_line and re.fullmatch(r"[/ ]*[A-Za-zÆØÅæøå .,\-]{3,45}", t):
                    if cur:
                        ents.append(cur)
                        cur = None
                    section = (section + " " + t) if prev_heading else t
                    prev_heading = True
                elif cur:
                    cur["parts"].append(t)
                    cur["boxes"].append((n, l["bbox"]))
                    prev_heading = False
                elif ref_line and headings:  # henvisninger direkte under en overskrift
                    cur, prev_heading = {"pdf_page": n, "section": section, "parts": [section.replace("/ ", "").strip() + ".", t],
                                         "boxes": [(n, l["bbox"])]}, False
    if cur:
        ents.append(cur)
    return [(e["pdf_page"], e["section"], join_lines(e["parts"]), e["boxes"]) for e in ents]


def to_int(tok, hi):
    t = re.sub(r"[\s]", "", tok).translate(DIG)
    return int(t) if t.isdigit() and 1 <= int(t) <= hi else None


def parse_year(tok):
    t = tok.translate(DIG)
    if t.isdigit() and 1833 <= int(t) <= 1873:
        return int(t)
    return None


# --- v2 (2026-11-23): tolerant parsing of references ----------------------------------------------
# OCR reads ».« as »-« (»1843 7-5-«), hangs noise on (»21.3.-«, »27.6$«) and glues numbers together
# (»183825.7.«, »17.8.1845«). Before 2026-11-23 the parser therefore dropped every reference in ~170 entries
# (n_refs=0). Unreadable tokens are kept as valid=0 with `raw`; nothing is guessed beyond what is below.
QUOTES = "‘’'`^/•■*"
DM_MAP = str.maketrans({"i": "1", "I": "1", "l": "1", "L": "1", "!": "1", "|": "1", "o": "0", "O": "0", "°": "0",
                        "g": "9", "q": "9", "z": "2", "Z": "2", "J": "1", "B": "8", "ß": "8"})
DM_OK = re.compile(r"^(?:[0-9iIlL!|oO°gqzZJBß]{1,2}|[nhH])$")
LOOSE_DM = re.compile(r"^[^\s\w]{0,2}([\w!|°^$&#]{1,3})\s?[.\-,]\s?([\w!|°^$&#]{1,3})(?:\(\?\))?[.,\-;>»$*’'‘]*$")
_Q = re.escape(QUOTES)
GLUED_Y_DM = re.compile(rf"^([{_Q}]?[\w!$#&@%£}}{{]{{3,4}}?)([{_Q}]?[0-9iIl!]{{1,2}}[.\-][0-9iIl!]{{1,2}}[.,\-]*)$")
GLUED_DM_Y = re.compile(r"^([0-9iIl!]{1,2}[.\-][0-9iIl!]{1,2})[.,\-]((?:18|i8|l8)[3-7][0-9gGiIlOo])[.,]*$")
POS_RE = re.compile(rf"(?i)(bagsiden af|bag i almanakken+|foran i almanakken)\s*({MONTH_RE})?")
_DAYS = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}


def _num(tok, hi):
    t = tok.strip(QUOTES + " ")
    t = "11" if t in ("n", "h", "H") else t.translate(DM_MAP)
    return int(t) if t.isdigit() and 1 <= int(t) <= hi else None


def _dm(tok):
    """»7-5-«, »19.5,« -> (7, 5); None if not unambiguously readable."""
    m = LOOSE_DM.match(tok)
    if not m:
        return None
    a, b = m.group(1).strip(QUOTES), m.group(2)
    if not (DM_OK.match(a) and DM_OK.match(b)):
        return None
    d, mo = _num(a, 31), _num(b, 12)
    if d and mo and d <= _DAYS[mo]:
        return d, mo
    return None


def _year(tok):
    """-> (year | None, corrected?). Clean 4-digit reading; otherwise the last two digits (»‘845«, »/#70«) if the rest is noise."""
    t = tok.strip(",.;:>»$ ")
    core = t.replace("°", "0").translate(DIG)
    if re.fullmatch(r"[0-9]{4}", core) and 1833 <= int(core) <= 1873:
        return int(core), False
    u = t.strip(QUOTES).replace("'", "")
    if 3 <= len(u) <= 5 and re.fullmatch(r"[0-9iIljhoOgqzZ&]{2}", u[-2:]) and 33 <= int(u[-2:].translate(DIG)) <= 73 \
            and re.fullmatch(r"[^\w]*[\w!$#&@%£}{^/]{1,3}[0-9iIlgoO&]{2}", u):
        return 1800 + int(u[-2:].translate(DIG)), True
    return None, False


def _yearish(tok):
    """4 characters that read as a year but fall outside 1833-1873 (OCR 3/5/8/9 confusions): repaired later by name check."""
    t = tok.strip(",.;:>»$ ").replace("°", "0").translate(DIG)
    return t if re.fullmatch(r"1[0-9]{3}", t) and not (1833 <= int(t) <= 1873) else ""


def _tokens(text):
    out = []
    for tok in re.sub(r"(?<=[0-9iIl!.])[,;](?=[0-9iIl!])", ", ", text.replace("\xad", "")).split():
        m = GLUED_DM_Y.match(tok)
        if m:
            out += [m.group(1), m.group(2)]
            continue
        m = GLUED_Y_DM.match(tok)
        if m and (_year(m.group(1))[0] or re.match(r"^[0-9iIl&]{3,4}$", m.group(1).strip(QUOTES))):
            out += [m.group(1), m.group(2)]
            continue
        out.append(tok)
    # »26.« + »10.«, »i.« + »11,«, »19.« + »i.« (two tokens, one date)
    j, merged = 0, []
    while j < len(out):
        t = out[j]
        n = out[j + 1] if j + 1 < len(out) else ""
        if re.fullmatch(r"[0-9iIlL!|oO°]{1,2}\.", t) and re.fullmatch(r"[0-9iIlL!|oO°]{1,2}[.,]?", n) \
                and not _year(t)[0] and not _year(n)[0] and _dm(t + n):
            merged.append(t + n)
            j += 2
        else:
            merged.append(t)
            j += 1
    return merged


def _first_ref_index(toks):
    for i, t in enumerate(toks):
        nxt = toks[i + 1] if i + 1 < len(toks) else ""
        if (_year(t)[0] or _yearish(t)) and (_dm(nxt) or LOOSE_DM.match(nxt)):
            return i
        if t.startswith("§"):
            return i
        if _dm(t) and i > 0 and _year(toks[i - 1])[0]:
            return i - 1
    return None


_RANGE = re.compile(r"(?<![\w.])(\d{1,2})\.\s?[-–]\s?(\d{1,2})\.(\d{1,2})\.?\s?(1[8][3-7]\d)")
_LIST = re.compile(r"((?:\d{1,2}\.\d{1,2}\.?\s?(?:og|,)?\s?)+?)\s?(1[8][3-7]\d)(?!\d)")


def label_dates(head):
    """Dates in the entry heading itself (»Arrebo, 14.6.1840«, »Romanen, 26.9. og 29.9.1838«, »27.-30.6.1838«)."""
    out, taken = [], []
    for m in _RANGE.finditer(head):
        a, b, mo, y = (int(x) for x in m.groups())
        taken.append(m.span())
        if 1 <= a <= b <= 31 and b - a <= 7 and 1 <= mo <= 12:
            out += [(y, mo, d, m.group(0)) for d in range(a, b + 1)]
    for m in _LIST.finditer(head):
        if any(a <= m.start() < b for a, b in taken):
            continue
        y = int(m.group(2))
        for dm in re.finditer(r"(\d{1,2})\.(\d{1,2})", m.group(1)):
            d, mo = int(dm.group(1)), int(dm.group(2))
            if 1 <= mo <= 12 and 1 <= d <= _DAYS[mo]:
                out.append((y, mo, d, dm.group(0) + "." + m.group(2)))
    return out


def split_refs(text):
    """-> (head, not_in_xi, [ref dicts]). The references begin at the first year followed by a date, or at
    »Bagsiden af«, »Bag i almanakken«, »Foran i almanakken«. Each ref has `src` (tail = the reference series,
    label = date in the heading) and `fix` (empty, or what was read outside the strict form)."""
    text = POS_RE.sub(lambda m: "§" + m.group(1).replace(" ", "_") + ("_" + m.group(2) if m.group(2) else "") + "§", text)
    all_t = _tokens(text)
    start = _first_ref_index(all_t)
    head = " ".join(all_t[:start]) if start is not None else " ".join(all_t)
    head = re.sub(r"(\d{1,2}[.\-]\d{1,2}) (?=(?:18|i8|l8)\d\d\b)", r"\1.", head)     # »2.2.1842« blev delt af _tokens
    tail_toks = all_t[start:] if start is not None else []
    not_in_xi = bool(PLUS.search(head)) or bool(PLUS.search(" ".join(tail_toks)[:6]))
    head = PLUS.sub("", head).strip(" ,;")
    head = re.sub(r"(?:\s*\.){2,}\s*$", ".", head)          # »sproglærer. .«: tegnet er tabt, punktummet efter det står tilbage
    refs, year, year_raw, year_fix = [], None, "", ""
    for t in tail_toks:
        if t.startswith("§"):
            body = t.strip("§").lower()
            kind = "bagside" if body.startswith("bagsiden") else "bag" if body.startswith("bag_i") else "foran"
            mon = next((MONTHS[k] for k in MONTHS if body.endswith(k)), "")
            refs.append(dict(year=year, year_raw=year_raw, day="", month=mon, kind=kind, raw=t.strip("§").replace("_", " "),
                             valid=int(year is not None), src="tail", fix=year_fix))
            continue
        dm = _dm(t)
        if dm:
            refs.append(dict(year=year, year_raw=year_raw, day=dm[0], month=dm[1], kind="date", raw=t.strip(",;>»$"),
                             valid=int(year is not None), src="tail", fix=year_fix))
            continue
        y, fixed = _year(t)
        if y and not re.search(r"[.\-]", t.strip(".,-")):
            year, year_raw, year_fix = y, t, ("år-fra-sidste-to-cifre" if fixed else "")
            continue
        if _yearish(t) and not re.search(r"[.\-]", t.strip(".,-")):
            year, year_raw, year_fix = None, _yearish(t), ""
            continue
        if LOOSE_DM.match(t) and re.search(r"\d", t) and not re.match(r"(?i)^(se|jf)\b", t):
            refs.append(dict(year=year, year_raw=year_raw, day="", month="", kind="date", raw=t, valid=0, src="tail", fix=""))
    # a corrected year that falls backwards in the series is probably misread
    prev = 0
    for r in refs:
        if r["year"] and r["fix"] and r["year"] < prev:
            r["valid"] = 0
        elif r["year"] and not r["fix"]:
            prev = max(prev, r["year"])
    if not any(r["valid"] for r in refs):
        for y, mo, d, raw in label_dates(text):
            refs.append(dict(year=y, year_raw=str(y), day=d, month=mo, kind="date", raw=raw, valid=1, src="label", fix="dato-i-opslagsord"))
    return head, not_in_xi, refs


def label_of(head):
    h = head
    h = re.split(r"\s\(", h, maxsplit=1)[0]
    parts = h.split(", ")
    if len(parts) > 2 and "," in parts[0] + ",":
        h = ", ".join(parts[:2])
    return h.strip(" ,.;")


TITLES = {"fru", "frue", "frøken", "frøknerne", "jomfru", "mad", "madame", "mme", "mlle", "demoiselle", "hr", "herr", "dr",
          "prof", "professor", "baron", "baronesse", "greve", "grevinde", "general", "kaptajn", "pastor", "mr", "mrs", "miss",
          "monsieur", "signor", "signora", "fräulein", "frau", "en", "familien", "brødrene", "søstrene", "sen", "jun"}
LIFE = re.compile(r"\((?:[^()]*?)(?:1[5-9]\d\d|død|f\.\s*1[5-9]\d\d)[^()]*\)|\(død[^)]*\)")


def identification(head, label):
    """-> 'levetid' | 'fornavn' | '' — hvad der gør en person identificeret ud over efternavnet.
    'levetid': levetid eller dødsår i parentes; 'fornavn': et fornavn eller initial efter efternavnet
    (»Balling, Jonathan«, »Palm, A.«), ikke en titel eller rolle (»Blome, frøken«, »Walte, tysk maler«)."""
    if LIFE.search(head):
        return "levetid"
    rest = label.split(",", 1)[1].strip() if "," in label else ""
    tok = re.match(r"([A-ZÆØÅÄÖÜÉ][\wæøåäöüéèçñ\-]*\.?)", rest)
    if tok and tok.group(1).rstrip(".").lower() not in TITLES:
        return "fornavn"
    return ""


def xi_status(sign, head, label):
    """Personregistrets »÷« skelnes: i_xi (intet tegn), ikke_i_xi (tegn, men identificeret), uidentificeret."""
    if not sign:
        return "i_xi", ""
    basis = identification(head, label)
    return ("ikke_i_xi" if basis else "uidentificeret"), basis


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--pdf", type=Path, default=os.environ.get("HCA_ALMANAK_PDF"))
    ap.add_argument("--cache", type=Path, default=REPO_ROOT / "almanak" / "data" / "cache" / "register_lines.json")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    if not args.cache.exists() and not (args.pdf and Path(args.pdf).exists()):
        sys.exit("Angiv --pdf eller sæt HCA_ALMANAK_PDF")
    pages = read_lines(args.pdf, args.cache)
    args.out.mkdir(parents=True, exist_ok=True)

    persons, works, refs_out = [], [], []
    import register_glyphs as rg
    signs = rg.load()          # optisk aflæste »÷« (register_glyphs.py); None: kun tekstlagets gæt
    if signs is None:
        print("Advarsel: register_divsign.csv mangler; ÷ læses af tekstlaget (upålideligt)")
    for kind, rng, two_col, prefix in (("person", PERSON_PAGES, False, "ALMP"), ("work", WORK_PAGES, True, "ALMW")):
        ents = entries_of(pages, rng, two_col)
        n_signs, orphans = rg.assign({p: v for p, v in (signs or {}).items() if p in rng}, [e[3] for e in ents])
        if signs is not None and orphans:
            print(f"Advarsel: {len(orphans)} ÷ i {kind}registret kunne ikke knyttes til en linje: {orphans[:5]}")
        for i, (pg, section, text, boxes) in enumerate(ents, 1):
            head, sign_ocr, refs = split_refs(text)
            sign = n_signs[i - 1] > 0 if signs is not None else sign_ocr
            see = ""
            m = re.search(r"(?:,|\.)?\s*s[ec](?: i reglen| også)?\s*:\s*(.*)$", head)
            if m:
                see = m.group(1).strip(" .")
                head = head[:m.start()].strip(" ,.")
            m2 = re.search(r"\((?:ca\.\s*)?(\d{4})\s*[-–—]\s*(\d{4})\)", head)
            rid = f"{prefix}{i:04d}"
            flag = {"not_in_xi" if kind == "person" else "not_in_bfn": int(sign), "divsign_ocr": int(sign_ocr)}
            if kind == "person":
                flag["xi_status"], flag["xi_basis"] = xi_status(sign, head, label_of(head))
            row = dict(reg_id=rid, label=label_of(head), description=head, see=see, **flag,
                       birth=m2.group(1) if m2 else "", death=m2.group(2) if m2 else "",
                       n_refs=len(refs), pdf_page=pg, print_page=pg - PAGE_OFFSET, raw=text)
            if kind == "work":
                row["section"] = section
                works.append(row)
            else:
                persons.append(row)
            for r in refs:
                refs_out.append(dict(reg_id=rid, register=kind, **r))

    import register_repair as rr
    n_names = rr.apply_name_corrections(persons) + rr.apply_name_corrections(works)
    fixed, unresolved = rr.repair_years(persons, works, refs_out)
    print(f"OCR-rettelser: {n_names} navnefelter; {fixed} henvisninger fik år ved navnekontrol, {unresolved} med ulæseligt år er uløste")
    by_name, by_group, no_entry = rr.repair_unmatched_years(persons, works, refs_out)
    print(f"Årstal 3/5/8/9: {by_name} henvisninger rettet ved navnekontrol, {by_group} via årstalsgruppen; {no_entry} datoer uden almanakpost er uløste")
    for r in refs_out:
        r["valid"] = int(r["valid"])

    def dump(name, rows):
        with open(args.out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    dump("almanak_register_persons.csv", persons)
    dump("almanak_register_works.csv", works)
    dump("almanak_register_refs.csv", refs_out)
    valid = sum(r["valid"] for r in refs_out)
    print(f"personopslag: {len(persons)}, værkopslag: {len(works)}, henvisninger: {len(refs_out)} (valide: {valid})")
    print(f"opslag uden henvisning: personer {sum(1 for p in persons if not p['n_refs'])}, værker {sum(1 for w in works if not w['n_refs'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
