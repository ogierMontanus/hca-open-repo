# Almanakprojektet — H.C. Andersens Almanakker 1833–1873

Delprojekt i HCA Open Repository: digitalisering af Andersens almanakker
(»Skriv- og Reise-Calendere«) som ny dato-nøglet kilde ved siden af
dagbøgerne.

**Status 2026-10-27:** undersøgelse og plan. Intet er bygget ind i
pipelinen eller websitet; kun analyseværktøjer findes. Afklaringerne i
trin 0 er besvaret (se [`sources/README.md`](sources/README.md)); næste skridt
venter på en ny OCR-scanning, der måles mod
[`sources/baseline-2026-10-27.json`](sources/baseline-2026-10-27.json).

## Resultat i korte træk

* Der er to kilder: databasetabellen `almanak` (5.163 dagsposter, kun dato +
  tekst) og PDF'en af 1990-udgaven (OCR-tekstlag, sider, udgivertegn,
  person- og værkregister). Se [`sources/README.md`](sources/README.md).
* Databasen mangler mindst 41 dage, alle udaterede blokke og alle registre,
  har 20 poster på forkert dato og en række tastefejl og
  umarkerede tilføjelser. PDF-tekstlaget har systematiske OCR-fejl, især i
  tal. Trykket har selv 18 ugedagskonflikter.
* **Anbefaling:** en kombineret version med 1990-udgavens sidebillede som
  facit, PDF'en som struktur- og registerkilde og databasen som andet vidne
  i en kollation. Databasens `Dato` bevares som ekstern nøgle.

## Dokumenter

| Fil | Leverance |
|---|---|
| [`docs/kildeanalyse.md`](docs/kildeanalyse.md) | A — kildeanalyse; B — anbefaling af datagrundlag |
| [`docs/kombineret-version.md`](docs/kombineret-version.md) | C — dataenheder, matchning, feltprioritering, proveniens, validering |
| [`docs/pipeline-genbrug.md`](docs/pipeline-genbrug.md) | D — repository- og pipelineanalyse |
| Denne fil, afsnit »Mappestruktur« | E — mappestruktur |
| [`docs/implementeringsplan.md`](docs/implementeringsplan.md) | F — trinvis plan |

## Mappestruktur

```
almanak/
├── README.md              overblik, status, kommandoer
├── .gitignore             holder fuldtekstudtræk ude af git
├── sources/README.md      kilderegister: placering, sha256, sideforskydning, rettigheder, afklaringer
├── sources/baseline-*.json  måletal for OCR-kvalitet (til vurdering af ny scanning)
├── docs/                  analyse, model, plan
├── config/                (trin 1) stier, sideintervaller, OCR-regler — data, ikke kode
├── scripts/
│   ├── analysis/          undersøgelsesværktøjer (findes nu)
│   └── …                  (trin 1–5) almanakspecifik pipeline
└── data/
    ├── extracted/         maskinelt udtræk — reproducerbart, IKKE autoritativt (gitignoreret)
    ├── cache/             PDF-tekstlagscache (gitignoreret)
    ├── review/            (trin 2–5) menneskelige beslutninger — AUTORITATIVT, i git
    └── build/             (trin 3–5) deterministisk byg af udtræk + review
```

Begrundelse:

* **Egen topmappe** frem for at sprede filer i `scripts/`, `data/curated/` og
  `docs/data-model/` (som Collin-brevarbejdet gjorde): almanakken har egne
  kilder, egen nøgle (dato i stedet for bind/side) og egen livscyklus. Det
  holder dagbogspipelinen urørt.
* **Kilder adskilt fra afledte data:** originalerne ligger uden for git og
  registreres kun med sti og sha256 i `sources/`.
* **Autoritet er synlig i mappenavnet:** kun `data/review/` (og reglerne i
  `config/`) indeholder menneskelige afgørelser; `extracted/` og `build/` kan
  altid slettes og genskabes.
* **Fælles logik bliver i `scripts/`:** almanakscripts importerer fra
  `scripts/migration/`, `scripts/correspondence/`, `scripts/parsers/` og
  `scripts/build_mockup/` (se [`docs/pipeline-genbrug.md`](docs/pipeline-genbrug.md));
  de kopierer ikke koden.
* **Overgang til websitet** sker først i trin 6, og da gennem
  `data/normalized/almanac.csv` som søster til `diary.csv` — det sted
  `docs/data-model/temporal-modelling.md` allerede har udpeget.
* **Tests** placeres i repoets `tests/` (`test_almanak_*.py`), så CI finder dem.

## Genkør analysen

PowerShell, fra repo-roden (kræver `raw/hca_db.sql` og PyMuPDF):

```powershell
$env:HCA_ALMANAK_PDF = "C:\Users\nh\Syddansk Universitet\HCA-MS - Documents\forskning_HCA\1990 HCAs almanak\andersen-hc_almanakker.pdf"
python almanak/scripts/analysis/extract_db.py
python almanak/scripts/analysis/extract_pdf_entries.py --cache almanak/data/cache/lines.json
python almanak/scripts/analysis/compare_sources.py
```

Output i `almanak/data/extracted/`: `aligned.csv` (alle datoer side om side
med lighedsmål og side), `date_discrepancies.csv`, `letter_direction.csv`,
`summary.json`. PDF-udtrækket tager ≈1 min første gang.

## Afhængigheder til eksisterende kode

| Bruges af | Eksisterende komponent |
|---|---|
| `scripts/analysis/extract_db.py` | `scripts/migration/migrate_tidstavle_sql.py` → `parse_table()` |
| (planlagt) registermatchning | `scripts/correspondence/name_normalize.py`, metoden i `scripts/parsers/parse_personregister_xi.py` og `scripts/correspondence/match_collin_persons_to_register.py` |
| (planlagt) stedkobling | `scripts/build_mockup/build_timeline.py` → `Matcher` |
| (planlagt) strengplacering | `scripts/parsers/ner_page_grounding.py` |
