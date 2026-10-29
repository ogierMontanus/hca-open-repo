"""Shared vocabulary for the crowdsourcing layer (docs/crowdsourcing.md).

One place defines the categories used by

  - scripts/build_mockup/build_crowd_queue.py  (which persons need help, and why)
  - scripts/crowdsource/validate.py            (what a submission may contain)
  - scripts/crowdsource/export_approved.py     (how approved data is handed on)
  - mockup/js/crowd-*.js                       (via the generated CROWD_TAXONOMY)

so a category can never mean one thing in the queue and another in the form.
Everything here is reused from, or aligned with, an existing repo convention —
the source of each is named next to it.
"""

SCHEMA = "hca-crowd-submission/1"

# ── Documentation level ────────────────────────────────────────────────────
# A register entry is "anchored" by three independent kinds of evidence:
#   N  a full given name   (not only initials, not only a title like "Mrs.")
#   L  a life date         (birth or death year in the label)
#   D  a descriptive text  (two words or more — "Tigger." is not one)
# The level is simply how many anchors the printed register supplies.
# Level 3 is "documented" and is not queued (it can still be corrected from
# the person page); levels 0–2 form the work queue.
LEVELS = [
    # key,            anchors, da,                        en
    ("dokumenteret",   3, "Dokumenteret",           "Documented"),
    ("delvist",        2, "Delvist dokumenteret",   "Partly documented"),
    ("fragmentarisk",  1, "Fragmentarisk",          "Fragmentary"),
    ("navn_alene",     0, "Navn alene",             "Name only"),
]
LEVEL_BY_ANCHORS = {n: key for key, n, _, _ in LEVELS}
QUEUED_LEVELS = ("delvist", "fragmentarisk", "navn_alene")

# "Flygtig omtale" (fleeting mention) is a second, independent dimension:
# the person is mentioned on at most this many diary pages. A fleeting
# mention with level fragmentarisk/navn_alene is the hardest and most
# valuable case — one passing name, nothing to go on.
FLEETING_MAX_MENTIONS = 2

MENTION_BUCKETS = [
    # key,   da,             en,              lo, hi
    ("1",   "1 omtale",      "1 mention",      1, 1),
    ("2-3", "2–3 omtaler",   "2–3 mentions",   2, 3),
    ("4+",  "4 eller flere", "4 or more",      4, 10**6),
]

# ── Missing information ("huller") ─────────────────────────────────────────
# What the queue can say is missing, and which form fields invite filling it.
# `field` keys are those of FIELDS below. The detection rules live in
# build_crowd_queue.py (one function per gap, unit-tested).
GAPS = [
    # key,          da,                                   en,                              fields
    ("identity",    "Hvem er personen? (uidentificeret)", "Identity unknown",              ["given_names", "birth_date", "death_date", "occupation", "description", "wikidata"]),
    ("given_names", "Fornavn mangler",                    "Given name missing",            ["given_names"]),
    ("birth",       "Fødselsår mangler",                  "Birth date missing",            ["birth_date", "birth_place"]),
    ("death",       "Dødsår mangler",                     "Death date missing",            ["death_date", "death_place"]),
    ("description", "Tynd eller manglende beskrivelse",   "Thin or missing description",   ["description", "occupation", "relations"]),
    ("occupation",  "Erhverv ukendt",                     "Occupation unknown",            ["occupation", "role_bucket"]),
    ("nationality", "Nationalitet ukendt",                "Nationality unknown",           ["nationality", "residence"]),
    ("gender",      "Køn ubestemt",                       "Gender undetermined",           ["gender"]),
    ("doubt",       "Registret er selv i tvivl",          "Register itself is unsure",     ["surname", "name_variants", "given_names"]),
]
GAP_KEYS = [g[0] for g in GAPS]

# Words in the printed register that flag the editors' own doubt (cf.
# docs/data-model/person-editorial-emendations.md — "Navnet maaske
# misforstaaet" is the model case: the register asks the question, the
# contributor may answer it).
DOUBT_PATTERNS = [
    r"\(\?\)", r"\?\)", r"\bmaaske\b", r"\bmuligvis\b", r"\bformentlig\b",
    r"\busikker\b", r"\bmisforstaa", r"\benten\b", r"\bevt\.", r"\bantagelig\b",
]

# ── How the presumed country / locality was obtained ───────────────────────
BASES = [
    # key,    da,                                      en
    ("nat",   "Nationalitet i registret",              "Nationality in the register"),
    ("beskr", "Sted i registrets beskrivelse",         "Place in the register description"),
    ("side",  "Sted på samme dagbogsside",             "Place on the same diary page"),
    ("",      "Intet grundlag",                        "No basis"),
]

# ── Confidence ─────────────────────────────────────────────────────────────
# The three grades of person_emendations.tsv (docs/data-model/
# person-editorial-emendations.md). Indicative probabilities are guidance for
# the contributor, not stored numbers.
CONFIDENCE = [
    # key,        da,           en,         guidance_da
    ("certain",   "Sikker",     "Certain",   "Dokumenteret i en primær kilde; ingen rimelig tvivl (omtrent over 95 %)."),
    ("probable",  "Sandsynlig", "Probable",  "Stærkt underbygget, men en slutning — fx navn, sted og tid passer (omtrent 70–95 %)."),
    ("proposed",  "Forslag",    "Proposed",  "Kvalificeret gæt, som andre bør efterprøve (omtrent 30–70 %). Under det: skriv en kommentar i stedet for et felt."),
]
CONFIDENCE_KEYS = [c[0] for c in CONFIDENCE]

# ── Identification status ──────────────────────────────────────────────────
IDENTIFICATION = [
    # key,            da,                                                         en,                         needs
    ("identified",    "Jeg har identificeret personen",                           "I have identified the person",  "fields"),
    ("candidate",     "Jeg har en kandidat, men er ikke sikker",                  "I have a candidate",            "fields"),
    ("partial",       "Jeg kan supplere enkelte oplysninger, ikke identificere",  "I can add some details",        "fields"),
    ("duplicate",     "Samme person som en anden registerpost",                   "Same person as another entry",  "same_as"),
    ("not_individual", "Posten er ikke en enkeltperson (familie, firma, gruppe …)", "Not an individual",           "comment"),
    ("unidentifiable", "Jeg har søgt uden resultat",                              "Searched without result",       "sources"),
]
IDENTIFICATION_KEYS = [i[0] for i in IDENTIFICATION]

# ── Fields a contribution may claim ────────────────────────────────────────
# `emend`  : the `field` value of data/curated/person_emendations.tsv it maps to
# `wb`     : the column of data/raw/6-PERSON-V0.97(5).xlsx it feeds
# `kind`   : text | longtext | date | select | qid | url_or_id
FIELDS = [
    # key,           da,                                           kind,       emend,         wb
    ("surname",      "Efternavn (korrekt stavning)",               "text",     "surname",     None),
    ("given_names",  "Fornavn(e)",                                 "text",     "given_names", None),
    ("name_variants", "Andre stavemåder / navneformer",            "text",     None,          None),
    ("birth_date",   "Fødselsdato (ÅÅÅÅ, ÅÅÅÅ-MM eller ÅÅÅÅ-MM-DD)", "date",   "birth_year",  "BirthYear"),
    ("birth_place",  "Fødested",                                   "text",     None,          None),
    ("death_date",   "Dødsdato (ÅÅÅÅ, ÅÅÅÅ-MM eller ÅÅÅÅ-MM-DD)",  "date",     "death_year",  "DeathYear"),
    ("death_place",  "Dødssted",                                   "text",     None,          None),
    ("gender",       "Køn",                                        "select",   None,          "Gender"),
    ("nationality",  "Nationalitet",                               "text",     None,          "Nationality"),
    ("residence",    "Bosted / lokalitet (sted og land)",          "text",     None,          None),
    ("occupation",   "Erhverv / titel",                            "text",     None,          None),
    ("role_bucket",  "Erhvervsgren",                               "select",   None,          "Role/Occupation"),
    ("relations",    "Slægtskab og relationer",                    "longtext", None,          None),
    ("description",  "Supplerende beskrivelse (kort, i registrets stil)", "longtext", "description", None),
    ("wikidata",     "Wikidata Q-nummer",                          "qid",      None,          None),
    ("authority_other", "Andet autoritetslink / ID (VIAF, GND, DBL, FamilySearch …)", "url_or_id", None, None),
]
FIELD_KEYS = [f[0] for f in FIELDS]
FIELD_BY_KEY = {f[0]: f for f in FIELDS}

GENDER_VALUES = ["Mandlig", "Kvindelig", "Andet"]

# ── Sources ────────────────────────────────────────────────────────────────
# `strong` sources may back a "certain"/"probable" claim; `personal` may not
# (it documents where the contributor's knowledge comes from, which is
# still worth recording).
SOURCE_TYPES = [
    # key,        da,                                              en,                  needs_url, strong
    ("arkiv",    "Arkivalie (kirkebog, folketælling, skifte, ...)", "Archival record",   False, True),
    ("tryk",     "Trykt publikation (bog, tidsskrift, opslagsværk)", "Printed publication", False, True),
    ("web",      "Webside eller database",                         "Web page / database", True,  True),
    ("billede",  "Billede eller skærmbillede",                     "Image / screenshot",  False, True),
    ("pdf",      "PDF",                                            "PDF",                 False, True),
    ("register", "Autoritetsregister (Wikidata, VIAF, GND ...)",   "Authority record",    True,  True),
    ("personlig", "Personlig viden, familietradition, mundtlig",   "Personal knowledge",  False, False),
]
SOURCE_TYPE_KEYS = [s[0] for s in SOURCE_TYPES]
SOURCE_TYPE_BY_KEY = {s[0]: s for s in SOURCE_TYPES}
SOURCE_RESULTS = [("stoetter", "Understøtter oplysningerne"), ("intet_fund", "Søgt, intet fund")]
SOURCE_RESULT_KEYS = [s[0] for s in SOURCE_RESULTS]

# ── Workflow ───────────────────────────────────────────────────────────────
STATUSES = [
    ("submitted",          "Indsendt – afventer redaktionen"),
    ("needs_changes",      "Redaktionen beder om uddybning"),
    ("approved",           "Godkendt"),
    ("partially_approved", "Delvist godkendt"),
    ("rejected",           "Afvist"),
    ("withdrawn",          "Trukket tilbage"),
]
STATUS_KEYS = [s[0] for s in STATUSES]
FIELD_DECISIONS = ["accept", "accept_edited", "reject"]
ACCEPTED_DECISIONS = ("accept", "accept_edited")

# ── Limits (server-side; the browser mirrors them) ─────────────────────────
LIMITS = {
    "text": 200, "longtext": 2000, "comment": 3000, "citation": 600,
    "locator": 200, "url": 500, "summary": 2000, "name": 120, "contact": 200,
    "max_fields": len(FIELDS), "max_sources": 12, "max_attachments": 5,
    "attachment_bytes": 4 * 1024 * 1024,
}
ATTACHMENT_TYPES = {
    "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
    "image/gif": ".gif", "application/pdf": ".pdf",
}

# ── Gamification: quality, not volume ──────────────────────────────────────
# Counted only from reviewed work. No ranking, no timers, no streaks — see
# docs/crowdsourcing.md §7 for the reasoning.
BADGES = [
    # key,           da,                         description_da
    ("first_accepted", "Første godkendte bidrag", "Et bidrag med kildeangivelse er godkendt af redaktionen."),
    ("five_sourced",   "Fem godkendte med kilder", "Fem godkendte bidrag, hver med mindst én stærk kilde."),
    ("negative_result", "Dokumenteret negativt fund", "Et godkendt »søgt uden resultat« — sparer andre for at gentage søgningen."),
    ("local_expert",   "Lokalkender",             "Fem godkendte bidrag om personer knyttet til samme land eller lokalitet."),
    ("resolved_doubt", "Besvarede registrets tvivl", "Et godkendt bidrag til en post, hvor registret selv var i tvivl."),
]


def taxonomy_for_js() -> dict:
    """The JSON-serialisable form emitted as CROWD_TAXONOMY."""
    return {
        "schema": SCHEMA,
        "levels": [{"key": k, "anchors": n, "da": da, "en": en} for k, n, da, en in LEVELS],
        "queuedLevels": list(QUEUED_LEVELS),
        "fleetingMax": FLEETING_MAX_MENTIONS,
        "mentionBuckets": [{"key": k, "da": da, "en": en, "lo": lo, "hi": hi}
                           for k, da, en, lo, hi in MENTION_BUCKETS],
        "gaps": [{"key": k, "da": da, "en": en, "fields": f} for k, da, en, f in GAPS],
        "bases": [{"key": k, "da": da, "en": en} for k, da, en in BASES],
        "confidence": [{"key": k, "da": da, "en": en, "guidance": g} for k, da, en, g in CONFIDENCE],
        "identification": [{"key": k, "da": da, "en": en, "needs": n} for k, da, en, n in IDENTIFICATION],
        "fields": [{"key": k, "da": da, "kind": kind, "emend": em, "wb": wb}
                   for k, da, kind, em, wb in FIELDS],
        "genderValues": GENDER_VALUES,
        "sourceTypes": [{"key": k, "da": da, "en": en, "needsUrl": nu, "strong": st}
                        for k, da, en, nu, st in SOURCE_TYPES],
        "sourceResults": [{"key": k, "da": da} for k, da in SOURCE_RESULTS],
        "statuses": [{"key": k, "da": da} for k, da in STATUSES],
        "limits": LIMITS,
        "attachmentTypes": ATTACHMENT_TYPES,
        "badges": [{"key": k, "da": da, "desc": d} for k, da, d in BADGES],
    }
