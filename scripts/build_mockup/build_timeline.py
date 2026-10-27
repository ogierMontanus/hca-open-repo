#!/usr/bin/env python3
"""
Build mockup/data/timeline.js — the "Tidstavle" companion track for diaries.html.

Source:
  data/HCA_Tidstavler_bind_1-10_*.xlsx   (newest matching file wins)
      One sheet per diary volume ("Bind 1" … "Bind 10"); columns
      Fra | Til | Opholdssted / beskrivelse. Dates are text (ÅÅÅÅ-MM-DD,
      sometimes only ÅÅÅÅ-MM or ÅÅÅÅ, with "ca." / "(sommer)" qualifiers).
      Each description carries a cell note with the source page, the
      Det Kgl. Bibliotek EPUB link and the original date wording.

Register (for linking names in the descriptions):
  data/normalized/entities.csv    persons (Reg…) and works
  data/normalized/places.csv      places (LOC…)
  data/normalized/references.csv  which volumes an entity occurs in
                                  (used to pick between homonyms)

Writes (gitignored — regenerate with this script, like diary-index.js):
  mockup/data/timeline.js
      const TIMELINE = [ {i, v, a, b, pa, pb, q, k, x, p, u, o, n}, … ]
        i  "T0001"                running id, sheet order
        v  1..10                  diary volume (sheet)
        a  "1845-11-01"           first day  (inclusive, always a full date)
        b  "1845-11-10"           last day   (inclusive, always a full date)
        pa pb  "d"|"m"|"y"        precision of the source date at each end
        q  ["ca","sommer",…]      qualifiers the source put on the date
        k  "ophold"|"rejse"|"begivenhed"   heuristic kind (see classify())
        x  [ "text ", ["Glorup","p","LOC1021300"], …]
                                  description; linked spans are
                                  [text, "p"=place|"s"=person|"w"=work, id]
        p  "XIII"                 source page(s) in the printed timeline
        u  "https://epub3.kb.dk/…"  KB EPUB link of the first source page
        o  "1.—10.11."            original date wording (omitted when none)
        n  "…"                    editorial note from the cell note (omitted)

Matching is deliberately conservative: a name is linked only when the
register gives exactly one best candidate (see resolve_person). Run with
--report to print match statistics and the unresolved capitalised words.

Run from the repo root:
  python scripts/build_mockup/build_timeline.py [--report]
"""

import argparse
import calendar
import csv
import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA      = REPO_ROOT / "data"
NORM      = DATA / "normalized"
OUT       = REPO_ROOT / "mockup" / "data" / "timeline.js"

VOL_NUM = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6,
           "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11}

# Lower-case words that sit inside a name ("Wilhelm von Eisendecher").
PARTICLES = {"von", "van", "af", "de", "der", "den", "du", "la", "le", "zu",
             "di", "da", "v.", "d'", "ten", "ter", "til"}
# …but these also open ordinary sentences, so they may never START a name.
NO_START = PARTICLES

TOKEN_RE = re.compile(r"[A-Za-zÆØÅæøåÄÖÜäöüÉéÈèÁáÀàÓóÇçÑñŠšŽžŁłČčŘřÍíÚúÂâÊêÎîÔôÛû]"
                      r"[A-Za-zÆØÅæøåÄÖÜäöüÉéÈèÁáÀàÓóÇçÑñŠšŽžŁłČčŘřÍíÚúÂâÊêÎîÔôÛû'’\-]*")


# ── helpers ────────────────────────────────────────────────────────────────

def fold(s: str) -> str:
    """Case/diacritic-insensitive key. ä→æ, ö→ø, ü→y first (Danish
    convention, same as entity-refs.js nameKey), then NFD-strip the rest."""
    s = (s.replace("ä", "æ").replace("Ä", "Æ").replace("ö", "ø")
          .replace("Ö", "Ø").replace("ü", "y").replace("Ü", "Y"))
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def is_cap(tok: str) -> bool:
    return tok[:1].isupper()


# ── workbook ───────────────────────────────────────────────────────────────

NOTE_HEAD = re.compile(r"^Bind (\d+), s\. ([IVXLC\d]+): (\S+)$")


def parse_note(text: str):
    """Cell note → (pages, first_url, original_date, editorial_note)."""
    pages, url, orig, notes = [], None, None, []
    for para in [p.strip() for p in text.split("\n\n") if p.strip()]:
        m = NOTE_HEAD.match(para)
        if m:
            pages.append(m.group(2))
            url = url or m.group(3)
        elif para.startswith("Original datoangivelse:"):
            orig = para.split(":", 1)[1].strip()
        else:
            notes.append(para)
    if orig == "Indledende prosatekst":      # date comes from the intro prose
        orig = None
    return pages, url, orig, " ".join(notes) or None


DATE_RE = re.compile(r"(\d{4})(?:-(\d\d)(?:-(\d\d))?)?")


def parse_date(raw: str, end: bool):
    """Source date text → (iso_full, precision, qualifiers).

    Missing month/day are widened to the period's first (start) or last
    (end) day. An impossible day (the printed 29 Feb 1841) is clamped to
    the month's last day and flagged "ugyldig"."""
    q = []
    s = str(raw).strip()
    if s.startswith("ca."):
        q.append("ca")
        s = s[3:].strip()
    paren = re.search(r"\(([^)]*)\)", s)
    if paren:
        q.append(paren.group(1).strip())
    if "[kilden]" in s:
        q.append("ugyldig")
    m = DATE_RE.search(s)
    if not m:
        raise ValueError(f"unparseable date: {raw!r}")
    y, mo, d = int(m.group(1)), m.group(2), m.group(3)
    if mo is None:
        prec, mo_i, d_i = "y", (12 if end else 1), None
    elif d is None:
        prec, mo_i, d_i = "m", int(mo), None
    else:
        prec, mo_i, d_i = "d", int(mo), int(d)
    last = calendar.monthrange(y, mo_i)[1]
    if d_i is None:
        d_i = last if end else 1
    elif d_i > last:
        d_i = last
        if "ugyldig" not in q:
            q.append("ugyldig")
    return f"{y:04d}-{mo_i:02d}-{d_i:02d}", prec, q


def read_workbook(path: Path):
    wb = openpyxl.load_workbook(path)
    out = []
    for ws in wb:
        m = re.match(r"Bind (\d+)", ws.title)
        if not m:
            continue
        vol = int(m.group(1))
        for row in ws.iter_rows(min_row=5):
            fra, til, desc = row[0].value, row[1].value, row[2].value
            if not fra or not desc:
                continue
            note = row[2].comment.text if row[2].comment else ""
            pages, url, orig, edn = parse_note(note)
            a, pa, qa = parse_date(fra, end=False)
            b, pb, qb = parse_date(til or fra, end=True)
            if a > b:
                a, b = b, a
            q = list(dict.fromkeys(qa + qb))
            out.append(dict(v=vol, a=a, b=b, pa=pa, pb=pb, q=q,
                            text=str(desc).strip(), pages=pages, url=url,
                            orig=orig, note=edn))
    return out


# ── register ───────────────────────────────────────────────────────────────

LIFE_RE = re.compile(r"\((?:død\s+)?(\d{4}|\?)?\s*[–-]?\s*(\d{4}|\?)?\)")


# resolve_person() sentinel: "this is the author — consume the words, no link"
# (otherwise a shorter window like "C. Andersen" would match someone else).
AUTHOR = "<author>"


class Person:
    __slots__ = ("rid", "label", "surname", "given", "born", "died", "vols", "n")

    def __init__(self, rid, label):
        self.rid, self.label = rid, label
        head, _, rest = label.partition(",")
        self.surname = head.strip()
        first = rest.split(",")[0] if rest else ""
        first = re.sub(r"\([^)]*\)", " ", first)
        toks = [t for t in re.split(r"\s+", first.strip()) if t]
        while toks and toks[-1].lower() in PARTICLES:   # "Dorothea von"
            toks.pop()
        self.given = [t.rstrip(".") for t in toks]
        self.born = self.died = None
        m = re.search(r"\((?:død\s+)?(\d{4})?\s*[–-]\s*(\d{4})?\??\)", label)
        if m:
            self.born = int(m.group(1)) if m.group(1) else None
            self.died = int(m.group(2)) if m.group(2) else None
        else:
            m = re.search(r"\(død (\d{4})\)", label)
            if m:
                self.died = int(m.group(1))
        self.vols = set()
        self.n = 0


def load_register():
    persons, works, places = {}, {}, {}
    with (NORM / "entities.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["entity_type"] == "person":
                if r.get("see"):             # "se: …" cross-reference rows
                    continue
                persons[r["entity_id"]] = Person(r["entity_id"], r["label"])
            elif r["entity_type"] == "work":
                works[r["entity_id"]] = r["label"]
    with (NORM / "places.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            places[r["entity_id"]] = r["label"]
    place_vols, work_vols = defaultdict(set), defaultdict(set)
    place_n, work_n = Counter(), Counter()
    with (NORM / "references.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            eid, vol = r["entity_id"], VOL_NUM.get(r["vol"])
            if eid in persons:
                persons[eid].n += 1
                if vol:
                    persons[eid].vols.add(vol)
            elif eid in places:
                place_n[eid] += 1
                if vol:
                    place_vols[eid].add(vol)
            elif eid in works:
                work_n[eid] += 1
                if vol:
                    work_vols[eid].add(vol)
    return persons, works, places, place_vols, place_n, work_vols, work_n


def place_aliases(label: str):
    """Extra spellings a text may use for a register label:
    "Genève (Genf)" → Genève, Genf · "Frankfurt a.M." → Frankfurt ·
    "Locle, Le" → Le Locle · "Slesvig (By)" → Slesvig."""
    out = []
    base = re.sub(r"\s*\([^)]*\)", "", label).strip()
    if base and base != label:
        out.append(base)
    for inner in re.findall(r"\(([^)]*)\)", label):
        if re.fullmatch(r"[A-ZÆØÅ][\w\-' ]+", inner):
            out.append(inner)
    m = re.match(r"^(.+?) a\.(?:M|d\.O)\.$", label)
    if m:
        out.append(m.group(1))
    m = re.match(r"^(.+), (Le|La|Les|Den|Det)$", label)
    if m:
        out.append(f"{m.group(2)} {m.group(1)}")
        out.append(m.group(1))
    return out


class Matcher:
    def __init__(self):
        (self.persons, self.works, self.places,
         self.place_vols, self.place_n, self.work_vols, self.work_n) = load_register()
        # Common given names: a lone "Carl"/"Frederik" is a first name, never
        # a surname to link.
        gn = Counter(fold(p.given[0]) for p in self.persons.values() if p.given)
        self.given_names = {k for k, c in gn.items() if c >= 15}
        # surname → [Person]
        self.by_surname = defaultdict(list)
        for p in self.persons.values():
            self.by_surname[fold(p.surname)].append(p)
        # place label → [rid]; parenthetical qualifier dropped as a 2nd key
        # only when that makes the key unique ("Neuhaus (Schweiz)" stays put).
        self.by_place = defaultdict(list)
        self.alias_place = defaultdict(list)    # fallback keys, exact label wins
        for rid, label in self.places.items():
            self.by_place[fold(label)].append(rid)
            for alias in place_aliases(label):
                k = fold(alias)
                if rid not in self.alias_place[k]:
                    self.alias_place[k].append(rid)
        # work title (years/trailing dot stripped) → [rid]
        self.by_work = defaultdict(list)
        for rid, label in self.works.items():
            t = re.sub(r"\s*\(\d{4}[^)]*\)\s*\.?$", "", label).strip(" .*»«")
            if len(t) >= 4:
                self.by_work[fold(t)].append(rid)

    # -- places -------------------------------------------------------------
    def resolve_place(self, key: str, vol: int):
        key = re.sub(r"^st ", "sankt ", key)
        cands = self.by_place.get(key) or self.alias_place.get(key)
        if not cands:
            return None
        if len(cands) == 1:
            return cands[0]
        ranked = sorted(cands, key=lambda r: (vol in self.place_vols[r],
                                              self.place_n[r]), reverse=True)
        top, nxt = ranked[0], ranked[1]
        a = (vol in self.place_vols[top], self.place_n[top])
        b = (vol in self.place_vols[nxt], self.place_n[nxt])
        return top if a > b else None       # a tie stays unlinked

    # -- persons ------------------------------------------------------------
    @staticmethod
    def given_compatible(mention, p: Person) -> int:
        """-1 incompatible, otherwise a score (more matched given names =
        higher). `mention` is the list of given-name tokens before the
        surname, dots stripped."""
        if not mention:
            return 0
        if not p.given:
            return -1
        score = 0
        # first given name must agree (full word, or initial/abbreviation)
        for i, g in enumerate(mention):
            if i >= len(p.given):
                return -1 if i == 0 else score
            r = p.given[i]
            fg, fr = fold(g), fold(r)
            if fg == fr:
                score += 2
            elif len(fg) <= 4 and fr.startswith(fg):
                score += 1                  # "Chr." / "Fr." / "K."
            else:
                return -1
        return score

    def resolve_person(self, given, surname_key, vol: int, year: int):
        cands = self.by_surname.get(surname_key)
        if not cands:
            return None
        # Every row is about H. C. Andersen himself; the register's
        # "Andersen, Hans Christian" is a photographer from Nykøbing Mors,
        # so the author must never be linked.
        if surname_key == "andersen" and [fold(g)[:1] for g in given[:2]] == ["h", "c"]:
            return AUTHOR
        scored = []
        for p in cands:
            g = self.given_compatible(given, p)
            if g < 0:
                continue
            if p.born is not None and p.born > year + 1:
                continue                     # not yet born at that date
            alive = ((p.born is None or p.born <= year + 1) and
                     (p.died is None or p.died >= year - 1))
            invol = vol in p.vols
            s = g * 2 + (3 if invol else 0) + (2 if alive else 0) \
                + min(math.log1p(p.n), 3) * 0.3
            scored.append((s, p, invol, alive))
        if not scored:
            return None
        scored.sort(key=lambda t: -t[0])
        best = scored[0]
        if len(scored) > 1 and best[0] - scored[1][0] < 1.5:
            return None                      # ambiguous homonym
        # A bare surname (no given names) must be backed by the volume —
        # otherwise "Hansen" would link to any Hansen in the register.
        if not given:
            # exactly one candidate that is both in this volume and
            # datable, else "Bull"/"Hansen" would grab any register row
            solid = sorted((t for t in scored if t[2] and t[3] and t[1].born),
                           key=lambda t: -t[1].n)
            if not solid or solid[0][1] is not best[1]:
                return None
            if len(solid) > 1 and solid[0][1].n < 3 * solid[1][1].n:
                return None                  # no clearly dominant bearer
        if given and not best[3] and not best[2]:
            return None
        return best[1].rid

    # -- text → segments ----------------------------------------------------
    def link(self, text: str, vol: int, year: int):
        # same-length copy where a dash between letters is a hyphen
        # ("Beck—Friis" is one name); positions stay valid for slicing `text`
        text_o = text
        text = re.sub(r"(?<=\w)[—–](?=\w)", "-", text)
        toks = [(m.group(), m.start(), m.end()) for m in TOKEN_RE.finditer(text)]
        n = len(toks)
        used = [False] * n
        spans = []            # (start_char, end_char, type, rid)
        i = 0
        while i < n:
            w, s0, e0 = toks[i]
            if not (is_cap(w) or (w[0].islower() and w.lower() in PARTICLES
                                  and False)):
                i += 1
                continue
            hit = None
            # window = consecutive tokens separated only by a space / ". "
            maxn = min(6, n - i)
            for ln in range(maxn, 0, -1):
                win = toks[i:i + ln]
                # tokens must be adjacent (only whitespace or a single '.'
                # between them) so "Hamburg. Otto" is never one name
                ok = True
                for a, b in zip(win, win[1:]):
                    gap = text[a[2]:b[1]]
                    if gap not in (" ", ". ", ".") and not re.fullmatch(r"\.? ?", gap):
                        ok = False
                        break
                    if gap.startswith(".") and len(a[0]) > 4:
                        ok = False
                        break
                if not ok:
                    continue
                words = [t[0] for t in win]
                # name windows: capitalised words with optional inner particles
                if not all(is_cap(x) or x.lower() in PARTICLES for x in words):
                    continue
                if words[-1].lower() in PARTICLES or words[0].lower() in NO_START:
                    continue
                key = fold(" ".join(words))
                # 1) place (exact label)
                rid = self.resolve_place(key, vol)
                if rid:
                    hit = (ln, "p", rid)
                    break
                # 2) person: given names … surname
                if ln >= 2 or True:
                    inner = [x for x in words]
                    # surname = last token; particles right before it belong to it
                    sur = inner[-1]
                    given = [x.rstrip(".") for x in inner[:-1]
                             if x.lower() not in PARTICLES]
                    rid = self.resolve_person(given, fold(sur), vol, year)
                    if not rid and sur.endswith("s") and ln >= 2:   # Franz Liszts
                        rid = self.resolve_person(given, fold(sur[:-1]), vol, year)
                    if rid == AUTHOR:
                        hit = (ln, "x", None)
                        break
                    if rid and (ln >= 2 or self._single_ok(sur, i, toks, text, spans)):
                        hit = (ln, "s", rid)
                        break
            if hit:
                ln, typ, rid = hit
                if typ != "x":
                    spans.append((toks[i][1], toks[i + ln - 1][2], typ, rid))
                i += ln
            else:
                i += 1
        # quoted work titles »…«
        for m in re.finditer(r"»([^«»]{4,}?)«", text):
            title = m.group(1).strip(" .,;:!?")
            cands = self.by_work.get(fold(title))
            if not cands:
                continue
            rid = max(cands, key=lambda r: (vol in self.work_vols[r], self.work_n[r]))
            if len(cands) > 1:
                top = sorted(cands, key=lambda r: (vol in self.work_vols[r], self.work_n[r]),
                             reverse=True)
                if (vol in self.work_vols[top[0]], self.work_n[top[0]]) == \
                   (vol in self.work_vols[top[1]], self.work_n[top[1]]):
                    continue
            if any(not (m.end(1) <= s or m.start(1) >= e) for s, e, _, _ in spans):
                continue
            spans.append((m.start(1), m.start(1) + len(m.group(1).rstrip(" .,;:!?")),
                          "w", rid))
        text = text_o
        spans.sort()
        segs, pos = [], 0
        for s, e, typ, rid in spans:
            if s < pos:
                continue
            if s > pos:
                segs.append(text[pos:s])
            segs.append([text[s:e], typ, rid])
            pos = e
        if pos < len(text):
            segs.append(text[pos:])
        return segs

    def _single_ok(self, sur, i, toks, text, spans) -> bool:
        """A one-word person mention must look like a surname: not a common
        given name, and not the tail of a longer capitalised phrase whose
        full form failed to match ("Marie Stuart" ≠ Egypte Stuart)."""
        if len(sur) < 4 or fold(sur) in self.given_names:
            return False
        if i > 0:
            pw, ps, pe = toks[i - 1]
            before = text[:ps].rstrip()
            sentence_start = (not before) or before[-1] in ".»(:;!?"
            adjacent = text[pe:toks[i][1]] == " "
            linked = any(s0 <= ps < e0 for s0, e0, _, _ in spans)
            if adjacent and is_cap(pw) and not sentence_start and not linked:
                return False
        return True


# ── classification ─────────────────────────────────────────────────────────

# Sentence openers that are never a place name ("Besøgt Victor Hugo.").
NOT_A_PLACE = (r"^(Besøgt|Besøg|Hos|Gæst|Gæster|Aften|Aftenselskab|Middag|Udflugt|Tur|"
               r"Flyttet|Set|Med|Til|Den|Det|De|I|Om|En|Et|Kontrakt|Møde|Første|Anden|"
               r"Ridder|Fik|Modtog)\b")


def classify(text: str, segs) -> str:
    """Heuristic kind, for filtering/colouring only (never for links):
      rejse       "Fra X til Y …" / "Rejse …" — a journey leg
      ophold      the text opens with a place (linked or not) and has no
                  finite-verb sentence: "Weimar. Jenny Lind."
      begivenhed  everything else (publications, deaths, audiences …)"""
    if re.match(r"^(Fra .+ til |Rejse|Tilbage|Afrejse|Hjemrejse|Videre)", text):
        return "rejse"
    first = segs[0] if segs else ""
    if isinstance(first, list) and first[1] == "p":
        return "ophold"
    if re.match(NOT_A_PLACE, text):
        return "begivenhed"
    if re.match(r"^[A-ZÆØÅ][\wæøåäöüé\-]+(?:[ ,][A-ZÆØÅ][\wæøåäöüé\-]+)*[.,]", text) \
       and not re.search(r"\b(blev|er|var|dør|døde|udkom|fik|havde|får|ankom|rejste)\b", text):
        return "ophold"
    return "begivenhed"


# ── main ───────────────────────────────────────────────────────────────────

def find_workbook() -> Path:
    cands = sorted(DATA.glob("HCA_Tidstavler_bind_1-10_*.xlsx"))
    if not cands:
        sys.exit("No data/HCA_Tidstavler_bind_1-10_*.xlsx found")
    return cands[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    src = find_workbook()
    print(f"Reading {src.name} …")
    rows = read_workbook(src)
    mt = Matcher()

    entries, st = [], Counter()
    unresolved = Counter()
    for i, r in enumerate(rows, 1):
        year = int(r["a"][:4])
        segs = mt.link(r["text"], r["v"], year)
        for s in segs:
            if isinstance(s, list):
                st["link_" + s[1]] += 1
        e = dict(i=f"T{i:04d}", v=r["v"], a=r["a"], b=r["b"], pa=r["pa"],
                 pb=r["pb"])
        if r["q"]:
            e["q"] = r["q"]
        e["k"] = classify(r["text"], segs)
        e["x"] = segs if any(isinstance(s, list) for s in segs) else r["text"]
        e["p"] = "–".join(dict.fromkeys(r["pages"]))
        if r["url"]:
            e["u"] = r["url"]
        if r["orig"]:
            e["o"] = r["orig"]
        if r["note"]:
            e["n"] = r["note"]
        entries.append(e)
        st["kind_" + e["k"]] += 1
        if args.report:
            for w in TOKEN_RE.findall(r["text"]):
                if is_cap(w) and not any(isinstance(s, list) and w in s[0] for s in segs):
                    unresolved[w] += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(entries, ensure_ascii=False, separators=(",", ":"))
    OUT.write_text(
        "// Auto-generated by scripts/build_mockup/build_timeline.py — do not hand-edit.\n"
        "// Source: data/HCA_Tidstavler_bind_1-10_*.xlsx (Tidstavler, bind 1-10).\n"
        "// Loaded via <script> tag (file://-safe, mirrors diary-index.js).\n"
        f"const TIMELINE = {body};\n", encoding="utf-8")
    print(f"  wrote {OUT.relative_to(REPO_ROOT)}  ({OUT.stat().st_size // 1024} KB, "
          f"{len(entries):,} entries)")
    print("  ", dict(st))
    if args.report:
        print("Most frequent unlinked capitalised words:")
        for w, n in unresolved.most_common(60):
            print(f"   {n:4d}  {w}")


if __name__ == "__main__":
    main()
