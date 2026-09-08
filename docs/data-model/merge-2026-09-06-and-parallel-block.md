# Fletning 2026-09-06 + fundet af det parallelle alfabet

## 1. "Forsvundne" poster — falsk alarm, forklaret

`personregister_xi_review_full.xlsx` holder stadig den **gamle**
nummerering (10.094 rækker). Den 4. september blev 15 streg-dubletter
fjernet, **13 af dem øverst i filen**, så alle id fra `PerXI00014` og frem
rykkede 13 pladser ned. Regnearket blev aldrig genopbygget bagefter, fordi
det lå åbent i Excel og var låst.

| xlsx (gammel) | nuværende fil | Efternavn |
|---|---|---|
| PerXI04969–04973 | PerXI04956–04960 | Ipsen ×5 |
| PerXI04974–04977 | PerXI04961–04964 | Irminger ×4 |
| PerXI04978 | PerXI04965 | Irving |
| PerXI04990 | PerXI04977 | Iversen |

Intet er tabt. Oversættelsestabel gammel→ny findes allerede:
`datacleaning/diaries_datacleaning/volume12/person_id_crosswalk_2A_2B.tsv`.

**Regnearket skal genopbygges til sidst**, fra det flettede resultat — ikke
nu, for en genopbygning fra `data/parsed/` ville kaste de manuelle
rettelser væk.

## 2. Fletningen

`scripts/parsers/merge_manual_corrections.py` — trevejsfletning:

* **base**: `personregister_xi_review_full.tsv` (10.079)
* **gren A** (maskine): `_ocr_refined.tsv` — Jósika + 6 regenererede sorteringsnøgler
* **gren B** (manuel): `_2026-09-05-manual-corrections.csv` (10.089)

Gren B vinder på indhold; gren A bidrager kun til rækker B ikke har rørt.
`05_sort_key` flettes aldrig — den er per definition afledt
(`parse_personregister_xi.py:sort_key`) og regenereres til sidst. Det
opløser samtidig de to tilsyneladende konflikter (`PerXI01219`,
`PerXI01920`) uden et skøn: tag B's navnefelter, udled nøglen.

Resultat: `data/curated/personregister_xi_merged_2026-09-06.tsv`, 10.089
rækker, 0 dublet-id, 0 defekte henvisninger.

Udført: 2 genbrugte id fik `B`-suffiks (din egen konvention), 1 defekt
henvisningsstreng rettet, `loannou`→`Ioannou`, 7 felter fra gren A,
23 sorteringsnøgler regenereret.

### Én ufuldendt splitning

`PerXI01608` — `04_given_names` bærer stadig
`'Grevinde, »født i Svendborg«, Paris 19.4.1867. VII 269. Bertall…'`.
Sorteringsnøglen blev **holdt tilbage** her: en regenerering ville have
trukket den sammensmeltede tekst tilbage i en nøgle du allerede havde
renset til `'Berry'`. Feltet skal trimmes manuelt, så nøglen kan udledes.

### Stadig dubleret, kræver din beslutning

`Ioannou` står nu både på `PerXI00391B` og `PerXI04955B`; `Insinger`
både på `PerXI00391` og `PerXI04955`. Kilden havde en 2×2-knude her, og
splitningen løste halvdelen.

## 3. Hovedfundet: et parallelt alfabet i PerXI00001–00929

Registret indeholder **to alfabetiske løb**:

```
  række    3–928   PerXI00004–00929   A → Å   (blok)
  række  929       PerXI00930 'Aman'  A       (alfabetet starter forfra)
  række  929–10078 PerXI00930–10079   A → Å   (hovedløbet)
```

Blokken er 929 rækker mod hovedløbets 9.150. Overlap med hovedløbet:

| | Antal |
|---|---|
| Eksakt tvilling i hovedløbet (efternavn + henvisninger identiske) | 167 |
| Samme efternavn, andre henvisninger | 297 |
| Efternavn findes slet ikke i hovedløbet — reelt unikke | 465 |

**Alle 36 OCR-dubletpar fra 5. september krydser præcis denne grænse
(36/36)** — den ene tvilling i blokken, den anden i hovedløbet. Blokken er
altså den fælles årsag til hele dubletmængden, ikke 36 uafhængige
OCR-uheld. Det samme gælder Ioannou/Insinger-knuden ovenfor.

Blokken er ikke overflødig: 465 af 929 rækker er unikke bidrag. Men 167 er
rene dubletter og 297 er sandsynligvis samme person med henvisningerne
delt mellem to kopier.

Dette er et selvstændigt, større stykke arbejde og er **bevidst ikke rørt**
i fletningen. Det bør afgøres samlet, ikke par for par.
