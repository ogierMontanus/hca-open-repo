"""Server-side validation of a crowd submission (docs/crowdsourcing.md §4).

The browser validates the same rules (mockup/js/crowd-validate.js) so a
contributor sees problems before sending — but this module is the authority:
nothing reaches the store without passing it. tests/fixtures/crowd_cases.json
is run against both implementations so they cannot drift apart.

`validate_submission(payload)` returns (clean, errors). `errors` is a list of
{"path", "code", "msg"}; `clean` is a normalised copy (whitespace collapsed,
unknown keys dropped) and is only meaningful when `errors` is empty.
"""
from __future__ import annotations

import base64
import binascii
import datetime as dt
import re

import taxonomy as tx

PERSON_ID_RE = re.compile(r"^Reg[0-9]{4,9}$")
DATE_RE = re.compile(r"^(?:ca\.\s)?([0-9]{4})(?:-([0-9]{2})(?:-([0-9]{2}))?)?$")
QID_RE = re.compile(r"^Q[1-9][0-9]{0,9}$")
URL_RE = re.compile(r"^https?://[^\s<>\"']{3,}$", re.I)
CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _s(value, *, multiline=False) -> str:
    """Normalise a user string: strip control characters, trim, collapse
    runs of blanks (and, unless multiline, all whitespace)."""
    if value is None:
        return ""
    text = CTRL_RE.sub("", str(value)).replace("\r\n", "\n").replace("\r", "\n")
    if multiline:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
    else:
        text = re.sub(r"\s+", " ", text)
    return text.strip()


class _Errors(list):
    def add(self, path, code, msg):
        self.append({"path": path, "code": code, "msg": msg})


def _check_date(value: str):
    m = DATE_RE.match(value)
    if not m:
        return "invalid_date", "Brug ÅÅÅÅ, ÅÅÅÅ-MM eller ÅÅÅÅ-MM-DD (evt. med »ca. « foran)."
    year = int(m.group(1))
    if not 1000 <= year <= 1950:
        return "implausible_date", "Året ligger uden for det rimelige (1000–1950) for en person i dagbøgerne."
    if m.group(2) and not 1 <= int(m.group(2)) <= 12:
        return "invalid_date", "Måneden skal være 01–12."
    if m.group(3):
        try:
            dt.date(year, int(m.group(2)), int(m.group(3)))
        except ValueError:
            return "invalid_date", "Datoen findes ikke."
    return None


def _year_of(value: str):
    m = DATE_RE.match(value or "")
    return int(m.group(1)) if m else None


def validate_submission(payload: dict, *, today: dt.date | None = None,
                        allow_attachments: bool = True) -> tuple[dict, list]:
    today = today or dt.date.today()
    errs = _Errors()
    L = tx.LIMITS
    if not isinstance(payload, dict):
        errs.add("", "invalid", "Forventede et JSON-objekt.")
        return {}, errs

    person_id = _s(payload.get("person_id"))
    if not PERSON_ID_RE.match(person_id):
        errs.add("person_id", "invalid_person_id", "Mangler et gyldigt person-ID (Reg…).")

    # ── identification ────────────────────────────────────────────────────
    ident_in = payload.get("identification") or {}
    status = _s(ident_in.get("status"))
    summary = _s(ident_in.get("summary"), multiline=True)
    same_as = _s(ident_in.get("same_as"))
    if status not in tx.IDENTIFICATION_KEYS:
        errs.add("identification.status", "required", "Vælg, hvad dit bidrag drejer sig om.")
    if len(summary) > L["summary"]:
        errs.add("identification.summary", "too_long", f"Højst {L['summary']} tegn.")
    if status == "duplicate":
        if not PERSON_ID_RE.match(same_as):
            errs.add("identification.same_as", "required", "Angiv det Reg-ID, posten er identisk med.")
        elif same_as == person_id:
            errs.add("identification.same_as", "invalid", "Posten kan ikke være identisk med sig selv.")
    else:
        same_as = ""
    if status == "not_individual" and len(summary) < 10:
        errs.add("identification.summary", "required", "Forklar kort, hvorfor posten ikke er en enkeltperson.")

    overall = _s(payload.get("overall_confidence"))
    if status in ("identified", "candidate") and overall not in tx.CONFIDENCE_KEYS:
        errs.add("overall_confidence", "required", "Angiv, hvor sikker du er på identifikationen som helhed.")
    if overall and overall not in tx.CONFIDENCE_KEYS:
        errs.add("overall_confidence", "invalid", "Ukendt sikkerhedsgrad.")

    # ── sources ───────────────────────────────────────────────────────────
    sources_in = payload.get("sources")
    sources_in = sources_in if isinstance(sources_in, list) else []
    sources, n_att = [], 0
    if not sources_in:
        errs.add("sources", "required", "Angiv mindst én kilde. Uden kilde kan bidraget ikke vurderes.")
    if len(sources_in) > L["max_sources"]:
        errs.add("sources", "too_many", f"Højst {L['max_sources']} kilder.")
    for i, s in enumerate(sources_in[:L["max_sources"]]):
        p = f"sources[{i}]"
        s = s if isinstance(s, dict) else {}
        stype = _s(s.get("type"))
        citation = _s(s.get("citation"))
        url = _s(s.get("url"))
        locator = _s(s.get("locator"))
        accessed = _s(s.get("accessed"))
        result = _s(s.get("result")) or "stoetter"
        note = _s(s.get("note"), multiline=True)
        if stype not in tx.SOURCE_TYPE_KEYS:
            errs.add(f"{p}.type", "required", "Vælg kildetype.")
        if len(citation) < 5:
            errs.add(f"{p}.citation", "required", "Skriv en kildehenvisning (hvad er kilden, hvem/hvor/hvornår).")
        elif len(citation) > L["citation"]:
            errs.add(f"{p}.citation", "too_long", f"Højst {L['citation']} tegn.")
        if url and not URL_RE.match(url):
            errs.add(f"{p}.url", "invalid_url", "Linket skal begynde med http:// eller https://.")
        if len(url) > L["url"]:
            errs.add(f"{p}.url", "too_long", f"Højst {L['url']} tegn.")
        if len(locator) > L["locator"]:
            errs.add(f"{p}.locator", "too_long", f"Højst {L['locator']} tegn.")
        spec = tx.SOURCE_TYPE_BY_KEY.get(stype)
        if spec and spec[3] and not url:
            errs.add(f"{p}.url", "required", "Denne kildetype kræver et link.")
        if stype in ("arkiv", "tryk", "billede", "pdf") and not url and not locator:
            errs.add(f"{p}.locator", "required",
                     "Angiv enten et link eller en præcis henvisning (side, folio, opslag, filnavn).")
        if accessed:
            try:
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", accessed):
                    raise ValueError
                d = dt.date.fromisoformat(accessed)
                if d > today:
                    errs.add(f"{p}.accessed", "future_date", "Opslagsdatoen ligger i fremtiden.")
            except ValueError:
                errs.add(f"{p}.accessed", "invalid_date", "Brug ÅÅÅÅ-MM-DD.")
        if result not in tx.SOURCE_RESULT_KEYS:
            errs.add(f"{p}.result", "invalid", "Ukendt resultat.")
        att = None
        if s.get("attachment") and allow_attachments:
            att, n_att = _attachment(s["attachment"], p, errs, n_att)
        sources.append({"type": stype, "citation": citation, "url": url, "locator": locator,
                        "accessed": accessed, "result": result, "note": note,
                        **({"attachment": att} if att else {})})

    # ── fields ────────────────────────────────────────────────────────────
    fields_in = payload.get("fields")
    fields_in = fields_in if isinstance(fields_in, list) else []
    fields, seen = [], set()
    if len(fields_in) > L["max_fields"]:
        errs.add("fields", "too_many", "For mange felter.")
    for i, f in enumerate(fields_in[:L["max_fields"]]):
        p = f"fields[{i}]"
        f = f if isinstance(f, dict) else {}
        key = _s(f.get("field"))
        spec = tx.FIELD_BY_KEY.get(key)
        if not spec:
            errs.add(f"{p}.field", "invalid", "Ukendt felt.")
            continue
        if key in seen:
            errs.add(f"{p}.field", "duplicate", "Feltet er angivet to gange.")
        seen.add(key)
        kind = spec[2]
        value = _s(f.get("value"), multiline=(kind == "longtext"))
        conf = _s(f.get("confidence"))
        comment = _s(f.get("comment"), multiline=True)
        refs = f.get("sources")
        refs = [r for r in refs if isinstance(r, int) and not isinstance(r, bool)] if isinstance(refs, list) else []
        if not value:
            errs.add(f"{p}.value", "required", "Udfyld værdien, eller fjern feltet.")
        else:
            limit = L["longtext"] if kind == "longtext" else L["text"]
            if len(value) > limit:
                errs.add(f"{p}.value", "too_long", f"Højst {limit} tegn.")
            if kind == "date":
                bad = _check_date(value)
                if bad:
                    errs.add(f"{p}.value", bad[0], bad[1])
            elif kind == "select":
                allowed = tx.GENDER_VALUES if key == "gender" else None
                if allowed is not None and value not in allowed:
                    errs.add(f"{p}.value", "invalid", "Vælg en af de angivne værdier.")
            elif kind == "qid" and not QID_RE.match(value):
                errs.add(f"{p}.value", "invalid_qid", "Et Wikidata-nummer ser ud som Q12345.")
            elif kind == "url_or_id" and value.lower().startswith(("http", "www")) and not URL_RE.match(value):
                errs.add(f"{p}.value", "invalid_url", "Linket skal begynde med http:// eller https://.")
        if conf not in tx.CONFIDENCE_KEYS:
            errs.add(f"{p}.confidence", "required", "Angiv sikkerhedsgrad for feltet.")
        if len(comment) > L["comment"]:
            errs.add(f"{p}.comment", "too_long", f"Højst {L['comment']} tegn.")
        if not refs:
            errs.add(f"{p}.sources", "required", "Knyt mindst én kilde til feltet.")
        elif any(r < 0 or r >= len(sources) for r in refs):
            errs.add(f"{p}.sources", "invalid", "Henviser til en kilde, der ikke findes.")
        elif conf in ("certain", "probable"):
            backing = [sources[r] for r in set(refs)
                       if tx.SOURCE_TYPE_BY_KEY.get(sources[r]["type"], (0, 0, 0, 0, False))[4]
                       and sources[r]["result"] == "stoetter"]
            if not backing:
                errs.add(f"{p}.sources", "weak_sources",
                         "»Sikker« og »Sandsynlig« kræver en kilde, der understøtter feltet og ikke kun er personlig viden. "
                         "Vælg »Forslag«, eller tilføj en kilde.")
        fields.append({"field": key, "value": value, "confidence": conf, "comment": comment,
                       "sources": sorted(set(refs))})

    by_key = {f["field"]: f for f in fields}
    by, dy = _year_of(by_key.get("birth_date", {}).get("value", "")), _year_of(by_key.get("death_date", {}).get("value", ""))
    if by and dy and dy < by:
        errs.add("fields", "death_before_birth", "Dødsåret ligger før fødselsåret.")

    if status in ("identified", "candidate", "partial") and not fields:
        errs.add("fields", "required", "Udfyld mindst ét felt, eller vælg en anden type bidrag.")
    if status == "unidentifiable" and not any(s["result"] == "intet_fund" for s in sources):
        errs.add("sources", "required_negative",
                 "Et »søgt uden resultat« skal dokumentere, hvor du har søgt: marker mindst én kilde som »Søgt, intet fund«.")

    comment = _s(payload.get("comment"), multiline=True)
    if len(comment) > L["comment"]:
        errs.add("comment", "too_long", f"Højst {L['comment']} tegn.")

    # ── contributor ───────────────────────────────────────────────────────
    c_in = payload.get("contributor") or {}
    contributor = {
        "name": _s(c_in.get("name")),
        "contact": _s(c_in.get("contact")),
        "affiliation": _s(c_in.get("affiliation")),
        "expertise": _s(c_in.get("expertise")),
        "public_credit": bool(c_in.get("public_credit")),
    }
    if len(contributor["name"]) < 2:
        errs.add("contributor.name", "required", "Skriv dit navn, så bidraget kan krediteres.")
    for k, lim in (("name", L["name"]), ("contact", L["contact"]), ("affiliation", L["contact"]), ("expertise", L["contact"])):
        if len(contributor[k]) > lim:
            errs.add(f"contributor.{k}", "too_long", f"Højst {lim} tegn.")
    if payload.get("consent") is not True:
        errs.add("consent", "required", "Du skal acceptere vilkårene (CC BY 4.0 med navngivelse).")

    ctx_in = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    context = {
        "area": _s(ctx_in.get("area"))[:100],          # presumed country / locality from the queue
        "doubt": bool(ctx_in.get("doubt")),            # the register itself flagged doubt
        "level": _s(ctx_in.get("level"))[:30],
        "gaps": [g for g in (ctx_in.get("gaps") or []) if g in tx.GAP_KEYS][:12] if isinstance(ctx_in.get("gaps"), list) else [],
    }

    clean = {
        "schema": tx.SCHEMA,
        "person_id": person_id,
        "person_label": _s(payload.get("person_label")),
        "identification": {"status": status, "summary": summary, "same_as": same_as},
        "overall_confidence": overall,
        "fields": fields,
        "sources": sources,
        "comment": comment,
        "contributor": contributor,
        "consent": True if payload.get("consent") is True else False,
        "context": context,
    }
    return clean, errs


def _attachment(att, path, errs, n_att):
    """Validate an inline attachment {name, type, data} (base64). Returns
    ({name, type, data, bytes}, n_att). Size and type limits are in taxonomy."""
    L = tx.LIMITS
    if not isinstance(att, dict):
        return None, n_att
    ctype = _s(att.get("type")).lower()
    name = re.sub(r"[^\w.\- ]", "_", _s(att.get("name")))[:80] or "bilag"
    if ctype not in tx.ATTACHMENT_TYPES:
        errs.add(f"{path}.attachment", "bad_type", "Kun PNG, JPG, WebP, GIF og PDF kan vedhæftes.")
        return None, n_att
    if n_att >= L["max_attachments"]:
        errs.add(f"{path}.attachment", "too_many", f"Højst {L['max_attachments']} vedhæftninger i alt.")
        return None, n_att
    try:
        raw = base64.b64decode(att.get("data") or "", validate=True)
    except (binascii.Error, ValueError):
        errs.add(f"{path}.attachment", "bad_data", "Vedhæftningen kunne ikke læses.")
        return None, n_att
    if len(raw) > L["attachment_bytes"]:
        errs.add(f"{path}.attachment", "too_big",
                 f"Vedhæftningen er over {L['attachment_bytes'] // (1024 * 1024)} MB. Læg den et sted og angiv linket i stedet.")
        return None, n_att
    if not raw:
        return None, n_att
    return {"name": name, "type": ctype, "data": att.get("data"), "bytes": len(raw)}, n_att + 1
