# Lex.dk-links via sitemap — trinvis opslag for hele niveau A (1.315 personer)

Status: kørt 2026-10-28 · Rute 1 i [`../plan-lex-dk-links.md`](../plan-lex-dk-links.md) ·
forgænger: [`lex-dk-links-pilot.md`](lex-dk-links-pilot.md) (chatbot, n = 50) ·
resultater: `data/curated/lex/persons_lex_sitemap.csv` (forslag, ikke promoveret) ·
værktøjer: `scripts/parsers/screen_persons_for_lex.py`, `scripts/parsers/lex_sitemap_match.py`

## Metode

1. **Screening** (`persons_tiers.csv`): niveau A = 1.315 personer (levetid + fornavn + offentlig rolle,
   ikke kun slægtskab, og ≥ 5 dagbogsreferencer eller rolle forfatter/kunstner); B = 2.030; C = 6.883.
   Niveau A er sorteret efter antal dagbogsreferencer, så rækken 30 → 90 → … går fra de mest til de
   mindst omtalte.
2. **Sitemap** (`https://lex.dk/.sitemap/sitemap.xml`, 6 filer, **45,1 MB**, hentet én gang til
   `data/raw/lex/`, gitignoreret): 264.453 adresser, heraf ≈ 200.500 på de 7 værker, der bruges
   (lex.dk-hoved 170.669 · DBL 14.134 · Weilbach 7.827 · Danmarkshistorien 2.724 · Teaterleksikon 2.072
   · Dansk Kvindebiografisk 1.940 · Dansk litteraturs historie 1.148).
3. **Slug-match** (ingen netværk): personens søgenavn mod URL-slugs, i prioritetsrækkefølgen DBL >
   Dansk Kvindebiografisk > Weilbach > lex.dk > øvrige (kvinder: Kvindebiografisk før Weilbach/lex.dk).
4. **Verifikation:** ét sidekald pr. kandidat (1 forespørgsel/sek., cache), og artiklens egen titel +
   indledning (første 1.500 tegn efter første `<h1>`) skal indeholde registerets fødsels- **og**
   dødsår. Højst 3 kandidater pr. værk og 7 i alt pr. person. Kun titel, årstalsflag og HTTP-status gemmes.

## Resultat pr. trin (tredobling)

Hver kørsel dækker de første N personer i niveau A; tallene er fra kørslen med den kode, der gjaldt da:

| N | Slug-kandidat | **Bekræftet** (andel) | Heraf DBL | Nye sidekald | Tid |
|---:|---:|---:|---:|---:|---:|
| 30 | 24 | **23 (77 %)** | 21 | ≈ 160 (inkl. 3 justeringsrunder) | ≈ 4 min |
| 90 | 77 | **68 (76 %)** | 58 | 146 | 3,7 min |
| 270 | 213 | **186 (69 %)** | 150 | 346 | 8,6 min |
| 810 | 538 | **439 (54 %)** | 293 | 764 | 18 min |
| 1.315 (alle) | 741 | **594 (45 %)** | 346 | 320 | 8 min |
| 1.315, efter stramning* | 632 | **532 (40 %)** | **326** | 74 | 2 min |

\* Stikprøvekontrol af 60 bekræftede links afslørede relationer/navnebrødre (se «Justeringer»); de
fjernes af de stramme regler. Det endelige tal er **532 af 1.315 (40,5 %)**, DBL 326 (24,8 %).
Samlet **1.727 sidekald** (≈ 40 min ved 1/sek.) + én download à 45 MB. **Ingen chatbot, ingen tokens
til opslag.** Andelen falder jævnt med faldende dagbogs-omtale (73 % ved ≥ 20 referencer → 28 % ved < 5).

## Endeligt resultat for niveau A (n = 1.315)

| Status | Personer |
|---|---:|
| Bekræftet i DBL (evt. også andre værker) | 326 |
| Bekræftet kun i andet værk (lex.dk, Weilbach, Kvindebiografisk, Teaterleksikon) | 206 |
| **Bekræftet i alt** | **532** |
| «Sandsynlig» (navn passer, kun ét eller intet årstal) — manuel gennemgang | 55 |
| Kun «uoverensstemmelse» (navnebror med andre år) — manuel gennemgang/afvis | 45 |
| Ingen slug i sitemap'et | 683 |

Bekræftede personer pr. værk: lex.dk 352 · DBL 326 · Weilbach 103 · Dansk Kvindebiografisk 27 ·
Gyldendals Teaterleksikon 3 (kun personer uden bekræftet DBL-artikel — brugerbeslutning 2026-10-29; tidligere 9).

| Opdeling | n | Bekræftet | DBL | Ingen slug |
|---|---:|---:|---:|---:|
| Dansk / ingen nationalitetsmarkering | 676 | **373 (55 %)** | 317 | 236 |
| Udenlandsk markeret | 639 | 159 (25 %) | 9 | 447 |
| Mænd | 1.148 | 484 (42 %) | 296 | 579 |
| Kvinder | 166 | 48 (29 %) | 30 | 103 |
| ≥ 20 dagbogsreferencer | 131 | 96 (73 %) | 82 | 23 |
| 10–19 | 178 | 101 (57 %) | 73 | 60 |
| 5–9 | 383 | 162 (42 %) | 111 | 187 |
| < 5 (forfatter/kunstner) | 623 | 173 (28 %) | 60 | 413 |

27 af 166 kvinder har en bekræftet Dansk Kvindebiografisk-artikel (48 har et bekræftet link i alt).

## Justeringer undervejs (efter hvert trin)

| Efter | Problem | Rettelse |
|---|---|---|
| 30 | `Jonas d.Æ. Collin` → slugs har disambiguator («Jonas_Collin_-_finansdeputeret») | generationsmærker fjernes fra søgenavn |
| 30 | DBL udelader mellemnavne («Frederik_Høedt» for F. L. Høedt) | kun første fornavn skal passe |
| 30 | Sammensatte efternavne («Adam_Gottlob_Moltke» for Moltke-Hvitfeldt) | ét efternavnsled er nok; postinglister forenes |
| 30 | Kongelige: «Christian 9.» | tal-led kræver begge dele |
| 30 | **Falsk positiv:** `H. P. Holst` bekræftet mod *Ida Holst* (initial «H» matchede efternavnet; årstal stod et vilkårligt sted) | initialer må ikke matche efternavnet; årstal kun i artiklens indledning |
| 90 | Søgenavne: Napoleon (→ *Napoleon Bonaparte*), Bjørnson (OCR-fejlen «Bjørnstjeme»), «Frederik VI» uden parentes | `search_name_overrides.csv` + screeningsregel |
| 270 | «Sir Walter Scott», «Lord …» | titler ignoreres |
| 1.315 | **Slægtninge bekræftet** (*Emil Hartmann* ↔ J.P.E. Hartmann; *H.V. Bissen* ↔ Vilhelm Bissen): lempet fornavnsregel | første fornavn skal passe; slug med initialer skal have alle initialer dækket |
| 1.315 | To bekræftede artikler for samme person/værk (`J.L._Heiberg_-_dramatiker` for Johanne Luise Heiberg) | behold slug med fornavne skrevet ud; resten → «likely» (markeret `*`) |
| 1.315 | *Carl Julius Lorck* ↔ *Carl Berendt Lorck* (fremmed fornavn i slug) | hvert fornavnsord i slugs navnedel skal kunne forklares af personens fornavne |
| 1.315 | *Carl Hall (1848–1908)* ↔ `C.C._Hall` (to initialer, ét fornavn) | antal initialer i slug ≤ antal fornavne |

## Hvad tallene betyder (og ikke betyder)

* **Dækningen ved sitemap alene er 40 %** af niveau A — langt under chatbottens 92 % i pilotens 50
  *meget kendte* personer. Forskellen er stikprøven (pilotens var de mest omtalte) og navneformer:
  **udlændinge** får kun 25 %, fordi Lex staver dem på dansk («Ludvig_1.», «Gioacchino_Rossini»,
  «Lord_Byron») eller registret staver dem anderledes. Danskere/umarkerede får 55 % (DBL 317).
* De 683 uden slug er en **blanding af ægte fravær** (periferiske danske kunstnere/skuespillere uden
  artikel, fx Heinke, Piesner, Scudder) og **navnevarianter**, som chatbotten eller manuelle
  søgenavne kan løse. 447 er udenlandsk markerede — det er den naturlige restmængde til Rute 2.
* **Præcision:** gennemlæsning af første kørsel og tre tilfældige stikprøver (25 + 30 + 30 bekræftede
  links) fandt fire fejltyper (Holst/Ida Holst, Hartmann- og Bissen-slægtninge, Lorck, Hall), der alle er
  lukket af reglerne ovenfor; efter dem er ingen kendt, men et par snese tilfælde er ikke nok til at
  love > 97 %. Planen anbefaler 10 %-gennemgang. «Bekræftet» betyder: slug-navn forenelig + begge registerårstal i
  artiklens indledning — ikke at en navnebror med *samme* levetid er udelukket.
* **Sitemap'et mangler ikke noget vi ved af:** `denstoredanske.lex.dk` findes ikke som vært; Den Store
  Danske ligger på `lex.dk`. Weilbach (7.827 artikler) giver 103 ekstra bekræftede kunstnere.

## Reproducér

```powershell
python scripts/parsers/screen_persons_for_lex.py
# hent sitemap én gang (se plan-lex-dk-links.md §3), derefter:
python scripts/parsers/lex_sitemap_match.py --tier A --limit 30
python scripts/parsers/lex_sitemap_match.py --tier A --limit 1315
```

Sitemap-filer og `page_cache.json` ligger i `data/raw/lex/` (gitignoreret). Et genkør bruger cachen og
laver ingen gentagne forespørgsler.
