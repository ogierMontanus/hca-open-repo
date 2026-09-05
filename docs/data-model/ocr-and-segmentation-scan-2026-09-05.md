# OCR- og segmenteringsscan, 2026-09-05

Kilde: `data/curated/personregister_xi_review_full_ocr_refined.tsv` (10.079 rækker).
Fire uafhængige OCR-metoder + to projektspecifikke segmenteringsscanninger.
Intet i denne rapport er anvendt på filen ud over de tidligere aftalte
enkeltrettelser (`J6sika`→`Jósika`, de 6 regenererede `05_sort_key`-værdier).
Alt nedenfor er **forslag til gennemsyn**, leveret som to kandidat-filer.

## Metode 1 — ciffer-for-bogstav (den oprindelige forespørgsel)

Søgning efter cifre midt i ellers alfabetiske navnetokens. **1 fund** i
`03_surname` (`J6sika`, allerede rettet), **0** i `04_given_names`.
Konklusion: denne fejlklasse er stort set udtømt af tidligere sessioner.

## Metode 2 — omvendt OCR-substitution mod en kendt hyppig stavning

Standardteknik: en sjælden efternavnsform testes mod en liste af kendte
OCR-forvekslinger (rn↔m, cl→d, ü↔ii, 0/O, 1/l/I, 6→o/ó, C↔G …); et fund
kræver at substitutionen rammer en stavning der **allerede optræder hyppigt**
i registret, ikke bare at teksten "ser mistænkelig ud". 2 fund:
`Femanda`→`Fernanda`, `Sirnony`→`Simony` — begge viste sig efterfølgende at
være **dubletter** (se Metode 4).

## Metode 3 — fri redigeringsafstand mod hyppige efternavne

243 rå kandidater, men de fleste er ægte, forskellige efternavne der
tilfældigvis ligner hinanden (Andersen/Anderson/Anderssen er tre reelle,
forskellige familier; Hans/Haas/Hass ligeså). **For upræcis alene** —
kun brugbar som kandidatgenerator, filtreret videre af Metode 4.

## Metode 4 — intern dublet-detektion via identisk henvisningssignatur (den afgørende metode)

To rækker der citerer **nøjagtigt de samme sidehenvisninger** og har en
efternavnsafstand på 1-2 tegn, er med meget stor sandsynlighed samme
person registreret to gange under to forskellige OCR-læsninger af det
samme trykte navn. Filtreret mod "travle sider" (hvor en enkelt delt side
er tilfældig, fordi mange personer nævnes der).

**36 dublet-kandidater fundet og skrevet til**
`data/curated/personregister_xi_ocr_duplicate_candidates.tsv`.

Tre kandidater blev udelukket efter inspektion (ægte forskellige personer,
ikke OCR-varianter): `Pius IX`/`Pius V` og `Leo I`/`Leo IV` (forskellige
paver — romertal-forskel betyder forskellig person, ikke fejllæsning),
samt `Philipsen`/`Philips` (forskelligt køn og beskrivelse).

### Systematiske OCR-familier bekræftet i stor skala

| Familie | Antal dubletpar | Eksempel |
|---|---|---|
| **C ↔ G** (dokumenteret tidligere i projektet) | 8 | `Golloredo`/`Colloredo-Mansfeld`, `Gastro`/`Castro`, `Gaus`/`Caus` |
| **ü → "ii"** | 3 par, ét er en hel 4-personers familie | `Lützau`→`Liitzau` (Augusta, Frederik Georg, Hugo, Juliane — 4 ekstra rækker) |
| **Dobbelt-l → "li"/"il"** — **ny, ikke tidligere dokumenteret** | 6 par | `Bull`→`Buli`/`Buil` (hele Ole Bull-familien, 6 rækker), `Kall`→`Kali` (to forskellige familier), `Toll`→`Toli`, `Kullman`→`Kuliman` |
| Ciffer/accent-tab | 2 | `Bétzaris`/`B6tzaris`→`Botzaris`, `Josika`/`Jósika` |
| Enkelt bogstav droppet | flere | `Piessy`/`Plessy`, `Codes`/`Cocles` |
| Mellemrum indsat midt i ord (dokumenteret linjeombrydningsfejl) | 1 | `Sayn-Wittgens tein-Berleburg` |

**Dobbelt-l-familien er det mest værdifulde nye fund**: den var ikke kendt
fra tidligere sessioner og forklarer alene 6 af de 36 par, heriblandt en
hel familie (Ole Bulls børn) duplikeret to gange over.

### Anbefaling

Disse 36 par bør **flettes, ikke bare staveres**. At rette stavefejlen i
den ene tvilling uden at fjerne den anden ville skabe en åbenlys eksakt
dublet i stedet for en skjult en. Sammenlægning kræver samme omhu som
projektets tidligere dedup-scripts (`dedupe_imported_twins.py`,
`merge_particle_and_refless_twins.py`): fjernelse af en række
gennemnummererer alle efterfølgende `01_entry_id`. Foreslår en dedikeret
`merge_ocr_twin_duplicates.py`-kørsel efter gennemsyn af kandidatfilen,
ikke en automatisk fletning her.

## Segmenteringsscan — ny fejlklasse: næste posts navn hænger fast i `04_given_names`

Kendt fra denne sessions arbejde med `PerXI01219` (streghenvisning hvis
`04_given_names` kun indeholdt et dato/stedfragment) og `PerXI01240`
(en løsrevet forbogstav fra en tidligere splitning). Generaliseret til
hele registret:

* **1 streghenvisning med tomt `12_see_also`**: `PerXI01219` (allerede
  kendt).
* **1 løsreven-forbogstav-rest**: `PerXI01240` (allerede kendt).
* **23 rækker med dato/sidehenvisningsmønster i `04_given_names`** — heraf
  4 er uskyldige (et fødsels-/dødsdato-notat der hører hjemme i feltet:
  `PerXI00920`, `PerXI04037`, `PerXI05027`, `PerXI08765`), men **15 er en
  hidtil usporet fejlklasse**: den EFTERFØLGENDE posts hovedord (efternavn
  + fornavn) hænger fast for enden af DENNE posts `04_given_names`, uden
  at være splittet ud i sin egen række.

Skrevet til
`data/curated/personregister_xi_given_names_tail_fusion_candidates.tsv`
(15 rækker).

**Vigtigt fund:** `PerXI08643`s hængende hale er `"Skram (Schram), Gustav"`
— dette er præcis det navn der blev nævnt som et allerede kendt
splitproblem tidligere i projektet (Schram/Skram-krydsreferencen). Det
bekræfter, at mønstret **gentager sig** andre steder i registret end der
hvor det oprindeligt blev fanget, og at en systematisk eftersøgning
(som denne) er nødvendig frem for punktvise rettelser.

Denne fejlklasse er **ny i den forstand at ingen eksisterende
`review_flags`-regel i `build_review_workbook.py` fanger den** — de
eksisterende `fused_entry:*`-mønstre kigger kun i `09_description` og
`13_raw_text`, aldrig specifikt efter dette mønster i `04_given_names`.
Anbefaling: udvid `build_review_workbook.py` med en ny flagklasse
(`fused_entry:given_names_tail`) baseret på dette scans regex, så
fremtidige kørsler fanger det automatisk, plus et dedikeret
splitscript efter model af `suggest_embedded_name_splits.py`.

## Nuværende status for allerede kendte fejlklasser (til reference)

| Flag | Antal |
|---|---|
| `no_refs_no_see` | 184 |
| `hyphen_linewrap:verify_do_not_join` | 100 |
| `fused_entry:description_reference_run` | 61 |
| `fused_entry:embedded_name_year` | 27 |
| `suspect_years:year_left_in_name` | 30 |
| `fused_entry:reference_run` | 16 |
| `paren_unbalanced` | 13 |
| `death_before_birth` | 5 |
| `fused_entry:see_reference` | 1 |

## Leverancer

* `data/curated/personregister_xi_ocr_duplicate_candidates.tsv` — 36 par til gennemsyn/fletning
* `data/curated/personregister_xi_given_names_tail_fusion_candidates.tsv` — 15 rækker til gennemsyn/splitning
* Denne rapport

Intet af dette er anvendt på masterfilen. Alt kræver et eksplicit
næste skridt (flet-script hhv. split-script) efter din godkendelse.
