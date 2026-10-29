# scripts/crowdsource — bagenden til crowdsourcing-prototypen

Design, datamodel og arbejdsgang: [`docs/crowdsourcing.md`](../../docs/crowdsourcing.md).

| Fil | Rolle |
|---|---|
| `taxonomy.py` | Kategorier, felter, sikkerhedsgrader, kildetyper, grænser — **én kilde**; udsendes til browseren som `CROWD_TAXONOMY` af `scripts/build_mockup/build_crowd_queue.py` |
| `validate.py` | Server-side validering (autoriteten). Spejles af `mockup/js/crowd-validate.js`; delt testsæt `tests/fixtures/crowd_cases.json` |
| `store.py` | Filbaseret lager (`data/crowdsource/`, git-ignoreret), review-regler, import af browser-lokale bidrag, optælling og mærker |
| `register.py` | Skrivebeskyttede opslag i `data/normalized/*.csv` (label, beskrivelse, sidehenvisnings-signatur) |
| `server.py` | Valgfri server: statisk `mockup/` + `/api/crowd/` |
| `export_approved.py` | Godkendte bidrag → `data/curated/person_crowd_approved.tsv` + `.xlsx`, markerer dem indlæst |

```powershell
python scripts/crowdsource/server.py
python scripts/crowdsource/export_approved.py            # tørkørsel
python scripts/crowdsource/export_approved.py --write
python scripts/crowdsource/export_approved.py --import-json fil.json --write   # fra browser-lokal tilstand
python -m pytest tests/test_crowd_store.py tests/test_crowd_validate.py tests/test_crowd_queue.py tests/test_crowd_js.py -q
```

Kun standardbiblioteket, bortset fra `openpyxl` til Excel-filen (allerede i
`scripts/parsers/requirements.txt`); uden det springes `.xlsx` over.
