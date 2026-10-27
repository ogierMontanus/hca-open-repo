# Repository- og pipelineanalyse (leverance D)

Gennemgået: `docs/pipeline/`, `docs/data-model/`, `scripts/*`, `tests/`,
`data/{raw,parsed,curated,normalized}`. Både hvad koden gør, og hvad
dokumentationen siger.

## 1. Hvad dagbogspipelinen forudsætter

Det, der gør den dagbogsspecifik — og som almanakken ikke har:

| Forudsætning | Hvor | Almanakken |
|---|---|---|
| Nøglen er **bind + side** (`Pag…`, `vol`, `page`) | `references.csv`, `diary.csv`, `kb_diary_links.csv`, `_diary_scope.py`, `diary-wire.js`, alle `build_diary_*` | Nøglen er **dato** (+ løbenummer) i ét bind |
| Registret henviser til **bind:side/kolonne** (`VI 263`) | `parse_personregister_xi.py` (`11_references_parsed` = `VI:263`) | Henviser til **år dag.måned** (`1842 17.2`) eller til en blok (`Bag i almanakken`, `Bagsiden af Februar`) |
| Teksten kommer fra **KB's EPUB** med `id="dYYYY-MM-DD"` og linjenumre | `epub_diary_to_csv.py` | Ingen EPUB; teksten skal etableres fra OCR + DB |
| Registret er **kanonisk regneark** (`raw/HCA-Repository V*.xlsx`, `RegistryCategory` …) | `_common.py`, `parse_*_register.py`, `hca_xlsx_to_csv.py` | Intet regneark; registrene findes kun i PDF'en |
| Stedregister findes (`places.csv`, `LOC…`) | `place_register.py`, kort | Almanakken har **intet** stedregister |
| Personregistret har levetider for de fleste | `match_collin_persons_to_register.py` matcher på efternavn + fødselsår | Almanakkens register udelader levetid for personer, der står i Dagbøger XI — de skal matches på navn + XI-opslag |

## 2. Klassifikation af komponenter

### A. Kan genbruges uændret

| Komponent | Til |
|---|---|
| `scripts/migration/migrate_tidstavle_sql.py` → `parse_table()` | Udtræk af tabellen `almanak` (bruges allerede af `almanak/scripts/analysis/extract_db.py`). NB: scriptets egen `DEFAULT_SQL` peger på `../hca_db_export/`, ikke `raw/` — vi angiver stien eksplicit |
| `scripts/correspondence/name_normalize.py` (`primary_keys`, `edge_case_key`) | Navnefoldning ved matchning af almanakkens personregister mod `entities.csv` |
| `data/normalized/entities.csv`, `places.csv`, `persons-extra`-id'er | Autoritetsmål for person/værk/sted (læses, ændres ikke) |
| `scripts/parsers/wikidata_lookup.py` + skill `wikidata-verify` | Nye personer (»+« = ikke i Dagbøger XI) |
| pytest-opsætningen i `tests/` + CI | Nye `tests/test_almanak_*.py` |
| Projektregler: UTF-8 uden BOM, original orden rekonstruerbar, »originaldata suppleres, overskrives ikke«, »tvetydighed eskaleres« (`docs/pipeline/stages.md`) | Gælder uændret — almanakmodellen er bygget på dem |

### B. Kan genbruges med konfiguration eller mindre tilpasning

| Komponent | Tilpasning |
|---|---|
| `scripts/parsers/parse_personregister_xi.py` | Metoden (reflow af to spalter → split på »slutning af henvisning + begyndelse af nyt opslag«) passer på almanakkens personregister. Kræver: ny sidegrænse/kolonnemål, ny **henvisningsgrammatik** (`år d.m`, `Bag i almanakken`, `Bagsiden af <måned>`, `(?)`, `+`), og OCR-rettelse af årstal mod eksisterende poster. Anbefaling: udskil layout- og splitfunktionerne til et fælles modul frem for at kopiere |
| `scripts/correspondence/match_collin_persons_to_register.py` | Matchtrin-modellen (`exact`, `ambiguous`, `surname_only`, …) og output-formen (forslag til review, intet skrives tilbage) genbruges; nøglen udvides fra efternavn + fødselsår til efternavn + fornavne + XI-opslag |
| `scripts/parsers/ner_page_grounding.py` | Finder forekomst-strenge for *kendte* entiteter pr. side. Til almanakken: samme algoritme pr. **post** (`post_id` i stedet for `vol/page`). Kræver input-adapter, ikke ny algoritme |
| `scripts/build_mockup/build_timeline.py` → `Matcher` (`resolve_place`, `resolve_person`, `link`) | Bedste kandidat til **stedkobling** (almanakken har intet stedregister) og konservativ personkobling med levetidsfilter. `vol`-parameteren bruges til homonymvalg; for almanakken erstattes den af dagbogsbindet for samme år eller fjernes |
| `scripts/normalization/report_missing_page_refs.py` | Mønster for validering af hængende registerhenvisninger (V7) |
| Review-løkken i personregister-arbejdet (`suggest_*` → review-TSV → `apply_*` → `merge_manual_corrections.py`) | Mønstret genbruges for almanakkens `review/decisions.tsv`; de konkrete scripts er knyttet til XI-filerne og genbruges ikke |
| `diaries.html`s kalendervisning + Tidstavle-ledsagesporet (`timeline.js`, stage `3b2`) | Almanakken kan vises som endnu et dato-nøglet spor i kalenderen (1.857 almanakdage har også en dagbogsside). Kræver ny builder (`build_almanac.py`), ikke ændring af de eksisterende |
| `scripts/build_all.py` | Ny valgfri stage, når der er noget at bygge; ingen ændring nu |

### C. Kræver særskilt almanakimplementering

| Komponent | Hvorfor |
|---|---|
| Segmentering af PDF-tekstlaget i daterede poster og udaterede blokke | Intet tilsvarende findes (dagbøgerne kom segmenteret fra EPUB'en). Prototype: `almanak/scripts/analysis/extract_pdf_entries.py` |
| Kollation DB ↔ OCR og variantapparat | Nyt. Prototype: `compare_sources.py` |
| OCR-rettelsesregler for gammeldags tal, †, +, kapitæler | Dagbøgernes OCR-arbejde (`person-register-ocr-typos.md`, `apply_hyphen_linewrap_fixes.py`) gælder andre fejlmønstre |
| Værkregister-parser | Andet layout og andre konventioner end dagbogens værkregister i regnearket; mål er `entities.csv`-værker under `H. C. ANDERSEN` |
| Datovalidering mod kalender/ugedag | Ingen ækvivalent |
| `almanac.csv` / `almanac_references.csv` og deres builder | Dato-nøglet; se [`kombineret-version.md`](kombineret-version.md) §2.7 |

### D. Ikke relevante for almanakken

`epub_diary_to_csv.py` (koden; *outputformen* for `diary.csv` er dog
forbilledet), `hca_xlsx_to_csv.py`, `hca_v092_to_csv.py`,
`parse_music_register.py`, `parse_novels_plays_tales.py`, `parse_non_fiction.py`,
`_common.py` (regnearksslicing), `_diary_scope.py`, `build_diary_pages.py`,
`build_diary_index.py`, `build_diary_print.py`/`build_diary_pdf.py`,
`build_kb_links.py`, personrolle-/køns-/etnicitetsscripts (kører på hele
personregistret og får almanakpersonerne gratis, når de er koblet til `Reg…`),
`scripts/correspondence/*letter*` (brevgrænser), `place_typology/`,
`design_sync/`, `qa/` (kurv-UI).

## 3. Dokumentation vs. kode

* `docs/pipeline/stages.md` beskriver en regneark-baseret pipeline
  (slice → parse → OpenRefine → normalize → star schema). Den beskriver ikke
  de nyere, PDF-baserede registerparsere (`parse_personregister_xi.py`,
  `correspondence/extract_*`), som er de faktisk relevante forbilleder.
* `stages.md` og `star-schema.md` nævner »Sørens Almanak« som hjælperegister
  (»historical-calendar overlay«). Det er uafklaret, om det er dette materiale;
  ingen fil findes i repoet. **Afklar med Søren Dall-Hansen**, før der
  bygges noget parallelt.
* `temporal-modelling.md` forudser `almanac.csv` som søster til `diary.csv` —
  i overensstemmelse med modellen her.

## 4. Foreslåede fælles ændringer (ikke udført)

| Forslag | Gevinst | Konsekvens |
|---|---|---|
| Ret `DEFAULT_SQL` i `migrate_tidstavle_sql.py` til `raw/hca_db.sql` (med fallback) | Ét sted for dumpet | Ingen for eksisterende kørsler, der angiver `--sql` |
| Udskil `flow_page`/split-funktioner fra `parse_personregister_xi.py` til `scripts/parsers/register_layout.py` | Dagbøger XI, Collin og almanak deler PDF-registerlogik | Kræver regressionstest af XI-output (snapshot af `personregister_xi_parsed.tsv`) |
| Gør `build_timeline.Matcher` uafhængig af `vol` (valgfri homonymstrategi) | Stedkobling for almanak og senere kilder | Snapshot-test af `timeline.js`-tællinger (2.756/206/49) før og efter |
| Generalisér »Mention Dates« i UI'et til at unionere `diary.csv` og `almanac.csv` | Som planlagt i `temporal-modelling.md` | UI-ændring; senere fase |
