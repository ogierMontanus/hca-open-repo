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
├── annotation/            human NER-annoteringsside: template.html + build_annotation_page.py (out/ er gitignoreret)
├── scripts/
│   ├── parse_register.py  person- og værkregister (s. 328–388) -> data/register/, lokale id'er ALMP…/ALMW…
│   ├── analysis/          undersøgelsesværktøjer (findes nu)
│   └── …                  (trin 1–5) almanakspecifik pipeline
└── data/
    ├── extracted/         maskinelt udtræk — reproducerbart, IKKE autoritativt (gitignoreret)
    ├── cache/             PDF-tekstlagscache (gitignoreret)
    ├── register/          almanakkens register som CSV (foreløbigt, maskinlæst, committet — id'erne ALMP/ALMW er lokale)
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

## Register og annotering (prøve)

* `scripts/parse_register.py` læser PDF'ens tekstlag og skriver `data/register/almanak_register_{persons,works,refs}.csv`:
  2.022 personopslag (ALMP0001…), 333 værkopslag (ALMW0001…) og ≈9.500 henvisninger (≈9.300 med læsbar dato).
  Nøglerne følger rækkefølgen i det nuværende OCR-lag og er **foreløbige**: ved ny OCR skal de frigives via en crosswalk.
  **OCR-rettelser (2026-11-23):** (1) `scripts/register_repair.py` + den håndholdte `data/register/ocr_corrections.tsv` retter
  åbenlyse OCR-fejl i navne (`WulfT`→`Wulff`, `Nccrgaard`→`Neergaard`, …) i `label`/`description`/`see`; OCR-teksten ligger uændret i `raw`,
  den oprindelige etiket i `label_ocr`. (2) Parseren læser nu «.» som «-», snavs efter datoen, sammenlimede tal («183825.7.», «17.8.1845»)
  og datoer i selve opslagsordet («Romanen, 26.9. og 29.9.1838»); før blev ca. 170 opslag uden henvisning og mange år arvet fra forrige år.
  (3) Et årstal OCR har ødelagt («1830», «1899») får kun et år, hvis personens/værkets navn står i almanakposten på netop den dato.
  `refs.csv` har to nye kolonner: `src` (tail/label) og `fix` (hvad der er rettet). Resultat: henvisninger, hvor navnet kan ses i
  almanakposten på datoen, 4.974 → 5.529; ulæselige henvisninger 209 → 90; opslag uden henvisning (ikke krydshenvisninger) 177 → 56.
  Kendte svagheder: sammensmeltede tal uden skilletegn, enkelte ulæselige datoer (valid=0, `raw` bevaret), opslag uden dato (krydshenvisninger).
  **Registertegnet »÷« (2026-11-24):** person: ikke i Dagbøger XI / ikke identificeret (`not_in_xi`); værk: ikke i Birger Frank Nielsens
  bibliografi (`not_in_bfn`). OCR læser det som «4-», «-r», «+», «-5-» … eller taber det, så det aflæses i billedet
  (`scripts/register_glyphs.py` → `data/register/register_divsign.csv`): 369 personer (tekstlaget: 341) og 50 værker (tekstlaget: 2).
  Personerne skelnes i `xi_status`: `i_xi` 1.653, `ikke_i_xi` 263 (levetid eller fornavn, `xi_basis`), `uidentificeret` 106.
  Se `docs/registertegn.md`, også for planen for samkøringen med Dagbøgernes register og de 719 årstal, OCR har forvekslet inden for gyldige år.
* `annotation/build_annotation_page.py` bygger annotationssiden (s. 35–36) med registerkandidater pr. dag
  (henvisning til datoen, evt. bekræftet af navnet i teksten) og rulleliste + fritekst i redigeringen af en markering.

```powershell
python almanak/scripts/register_glyphs.py --pdf $env:HCA_ALMANAK_PDF     # kun når PDF'en/OCR'en skifter
python almanak/scripts/parse_register.py --pdf $env:HCA_ALMANAK_PDF
python almanak/annotation/build_annotation_page.py --pdf $env:HCA_ALMANAK_PDF --pages 35 36
```

## Navnegenkendelse (NER) — model og gennemsyn

Håndannoteringen (overlap-stikprøven, `annotation/Opmærkning til Holger.json`) bruges til en lille, lokal
rangeringsmodel i [`ner/`](ner/README.md), der finder navnestrenge i almanakposterne og foreslår registerposter,
og til gennemsynssider med maskinforslag: stikprøve 1 (`mockup/almanak-gennemsyn.html`, blok E–H) og stikprøve 2
(`mockup/almanak-gennemsyn2.html`, blok I–L: 1840, 1844, 1857, 1860), bygget med den nye metode — grænser 0,75/0,6,
fællesnavnsfilter, rettede registerårstal og ÷-mærkningen på registerkortet
(`python almanak/ner/build_review_page.py --sample 2 --out mockup/almanak-gennemsyn2.html`). Målinger og
forbehold: [`docs/plan-streng-grounding.md`](../docs/plan-streng-grounding.md) §3.10–3.15. Kort rapport om metoden: [`docs/metode-maskinforslag.md`](docs/metode-maskinforslag.md).

## Afhængigheder til eksisterende kode

| Bruges af | Eksisterende komponent |
|---|---|
| `scripts/analysis/extract_db.py` | `scripts/migration/migrate_tidstavle_sql.py` → `parse_table()` |
| (planlagt) registermatchning | `scripts/correspondence/name_normalize.py`, metoden i `scripts/parsers/parse_personregister_xi.py` og `scripts/correspondence/match_collin_persons_to_register.py` |
| (planlagt) stedkobling | `scripts/build_mockup/build_timeline.py` → `Matcher` |
| (planlagt) strengplacering | `scripts/parsers/ner_page_grounding.py` |
