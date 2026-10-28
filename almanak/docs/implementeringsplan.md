# Trinvis implementeringsplan (leverance F)

Rækkefølgen følger de fund, der styrer risikoen: først skal teksten og
dens struktur være pålidelig (kildeanalysen viste fejl i begge vidner),
derefter registre og kobling, til sidst visning. Hvert trin kræver
særskilt godkendelse, før det implementeres.

Afhængigheder: `0 ✔`; `1` venter på ny OCR; `1 → 2 → 3 → 4`; `5` kan starte efter `1`; `6` efter `3`+`5`; `7` efter `6`; `8` løbende.

---

### Trin 0 — Afklaringer ✔ (2026-10-27)

Besvaret (se `almanak/sources/README.md`): DB-rettelserne bygger ikke på
håndskriftet; teksten må publiceres; KB's faksimiler er offline; ny OCR er
bestilt. Stadig åbent, men ikke blokerende: »Sørens Almanak«
(`star-schema.md`) og de 404 JPG'er.

Konsekvenser for planen: DB-afvigelser fra sidebilledet behandles som
DB-fejl; trykkets egne fejl markeres som uafgjorte i stedet for at vente på
håndskriftet; trin 7 er ikke længere blokeret af rettigheder; trin 1–3
venter på den nye OCR.

### Trin 1 — Modtag ny OCR, mål den, og fastfrys kilder

* **Formål:** vælge det bedste tekstlag og et reproducerbart udgangspunkt.
* **Eksisterende:** `migrate_tidstavle_sql.parse_table`; prototyperne i
  `almanak/scripts/analysis/` (stierne er parametre; PDF'en skiftes med `--pdf`).
* **Nyt:** `almanak/scripts/extract_db.py`, `extract_pdf_lines.py` (sidelinjer
  med koordinater og font → JSON), manifest med sha256.
* **Fremgangsmåde for den nye OCR:** (1) Tjek sidetal og sideforskydning
  (nu PDF = trykt + 12) og om tekstlaget har samme linjeopdeling og fontinfo
  (kursiv/kapitæler bruges til overskrifter og ugedage). (2) Kør de tre
  analysescripts mod den nye PDF. (3) Sammenlign med
  `sources/baseline-2026-10-27.json`.
* **Accept for den nye OCR:** flere ord-identiske poster mod DB end 2.840 af
  5.133; færre forskelssteder end 3.340; færre `weekday_inferred` end 22;
  OCR-artefakterne i basislinjen (`iste`, `4-`, `Mokke` …) tæt på 0;
  ≥ 5.185 segmenterede poster. Hvis den nye OCR er bedre på nogle mønstre og
  dårligere på andre, bruges begge som vidner (`ocr`, `ocr2`).
* **Input → output:** `SRC-DB`, `SRC-PDF2` (evt. også `SRC-PDF`) →
  `data/extracted/almanak_db.csv`, `data/extracted/pdf_lines.json`,
  `*.manifest.json`, ny basislinje.
* **Validering:** 5.163 DB-rækker, 3 felter hver; 327 trykte sider med linjer;
  sha256 stemmer med `sources/README.md`.
* **Afhængighed:** den nye scanning.

### Trin 2 — Segmentering i poster og blokke

* **Formål:** trykkets struktur (år, måned, dag, interval, position, side).
* **Eksisterende:** prototype `extract_pdf_entries.py` (5.185 poster, 99,5 % kalenderkonsistente).
* **Nyt:** produktionsversion med håndtering af 1834-formatet (»den 3die«),
  intervaller (»17.-18.«), udaterede blokke og positionsmarkører som segmenter;
  undtagelsesliste i `data/review/`.
* **Output:** `data/extracted/almanak_post_raw.csv`, `almanak_segment_raw.csv`.
* **Validering:** V1 (alle linjer fordelt), V2 (monotone datoer), V3
  (ugedagskonflikter = de kendte 18 + evt. nye med review). Antal poster pr.
  årgang skal forklares mod DB (`compare_sources.py`).
* **Uafklaret:** om 1834-rejseoversigten (»Hele Tiden i Rom. 6 (kom Brevet)«)
  skal være én blok eller daterede poster.

### Trin 3 — Etablering af teksten (kollation)

* **Formål:** én læsning pr. post med apparat.
* **Eksisterende:** `compare_sources.py` (tokenisering, lighed); `name_normalize.py`.
* **Nyt:** `ocr_rules.tsv` (id'erede rettelsesregler: `iste→1ste`,
  `f→†` i datokontekst, `4-→+`, `Mokke→Moltke` …), `collate.py` →
  `almanak_variant.csv`; review-arbejdsbog (TSV/XLSX med billedlink) for
  `unresolved`.
* **Input → output:** posts + DB + regler + `review/decisions.tsv` →
  `data/build/almanak_post.csv`, `almanak_variant.csv`, `almanak_annotation.csv`.
* **Validering:** V5, V6, V8; V9-stikprøve pr. årgang. Mål og rapportér
  andelen af de 3.340 forskelle, der afgøres af regler vs. manuelt.
* **Afhængigheder:** trin 1 (valg af OCR). **Omfang med nuværende OCR:**
  ≈2.290 poster med forskelle; billedkontrol nødvendig for alt, der ikke
  dækkes af regler. Forventes at falde markant med den nye OCR — tallet
  genberegnes i trin 1.
* **Afgørelsesregel:** DB-tekst, der afviger fra sidebilledet, er en DB-fejl
  (DB bygger ikke på håndskriftet); trykkets egne fejl gengives som trykt.

### Trin 4 — DB-crosswalk

* **Formål:** hver DB-række forklaret; databasens nøgle bevaret.
* **Nyt:** `crosswalk_db.py` → `almanak_db_crosswalk.csv` med de i
  `kombineret-version.md` §2.3 definerede typer; review af de 20
  forskudte/byttede, 41 manglende, 2 ugyldige og 1 ekstra.
* **Validering:** V4. Fejlrapport til databasens ejere (liste over
  datoforskydninger, manglende dage, til/fra-konflikter).
* **Uafklaret:** om rettelserne skal føres tilbage til `hca_db` (uden for repoet).

### Trin 5 — Registre (person og værk)

* **Formål:** trykkets registre som strukturerede data.
* **Eksisterende:** `parse_personregister_xi.py` (metode), `match_collin_persons_to_register.py` (matchtrin), `name_normalize.py`.
* **Prototype findes:** `scripts/parse_register.py` (tovejs-spalter, 2.022 + 333 opslag, ≈9.300 læsbare henvisninger). Mangler: korrekturlæsning, frigivelse af id'er, OCR-rettelse af årstal.
* **Nyt:** produktionsversion af `parse_register_persons.py`, `parse_register_works.py`
  (henvisningsgrammatik `år d.m`, `Bag i almanakken`, `Bagsiden af <måned>`,
  `(?)`, `+`); årstalsrettelse mod eksisterende poster.
* **Output:** `data/build/almanak_register_ref.csv`, registeropslag med `headword_id`.
* **Validering:** V7; alfabetisk orden pr. register (samme kontrol som
  `collin-place-index.md`); hver henvisning bekræftet af navnet i postens tekst
  eller markeret `ambiguous`.
* **Uafklaret:** fyrstelige personer står under landet (»Østrig, Ferdinand I«) — mapping til `Reg…`.

### Trin 6 — Kobling til projektets registre

* **Formål:** almanakken som ny kilde til »mention dates«.
* **Eksisterende:** `entities.csv`, `places.csv`, `build_timeline.Matcher` (steder), `ner_page_grounding.py` (strengplacering).
* **Nyt:** crosswalk almanakregister → `Reg…` (via Dagbøger XI-opslaget),
  stedkobling med `source=auto`, grounding pr. post.
* **Output:** `data/normalized/almanac.csv`, `almanac_references.csv`
  (først nu skrives der uden for `almanak/`).
* **Validering:** ingen ændring af eksisterende `entities.csv`-rækker; nye
  personer kun via review; tællinger af `exact/ambiguous/none` rapporteret.
* **Afhængigheder:** trin 3, 5; evt. fælles ændringer i `pipeline-genbrug.md` §4.

### Trin 7 — Visning

* **Formål:** almanakken i mockup'en.
* **Nyt:** `build_almanac.py` (stage i `build_all.py`), spor i `diaries.html`s
  kalender, »Mention Dates« over begge kilder, almanakomtaler på
  person-/værksider. Eksterne links (KB, andersen.sdu.dk) efter
  `docs/external-links.md`.
* **Validering:** Playwright-klik fra `index.html` (jf. `HANDOVER.md`), ikke
  gættede URL'er.
* **Afhængigheder:** trin 6. Rettighederne er afklaret; der linkes ikke til
  KB's faksimiler (offline).

### Trin 8 — Dokumentation og gentagelse (løbende)

* Hvert trin opdaterer `almanak/README.md` (status, kommandoer) og tallene i
  `kildeanalyse.md`. Tests i `tests/test_almanak_*.py` læser kun committede
  input (som `test_timeline_build.py`), så de kører i CI uden de
  gitignorerede kilder.
* **Accept for hele projektet:** V10 — et byg fra kilder med kendt sha256 og
  `review/` giver byte-identisk resultat.
