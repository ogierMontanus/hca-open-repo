# Tidstavle — krydsforbindelser og første resultater

Status: målt 2026-10-27 på `data/HCA_Tidstavler_bind_1-10_ Ver_0.9.xlsx` ·
implementering: se [`tidstavle-ledsagespor.md`](tidstavle-ledsagespor.md) ·
fremadrettet plan: [`../plan-tidstavle-data.md`](../plan-tidstavle-data.md)

Tallene er beregnet ved at holde de 1.745 tidstavle-poster (datoer normaliseret,
navne linket til registeret) op mod `diary.csv` (4.413 daterede dagbogssider),
`references.csv`, `places.csv` og `rejser.tsv`. De er målinger af *dækning og
overensstemmelse*, ikke af korrekthed: en uenighed kan lige så vel pege på en
fejl i registeret som i tidstavlen.

## Hvad tidstavlen tilfører, som dagbøgerne ikke har

Tidstavlen er udgiverens kontekstspor — hvor Andersen opholdt sig, hvem han
besøgte, hvad der udkom — ikke dagbogsteksten. Derfor behandles den som et
*ledsagespor* ved siden af dagbogssiderne (aldrig blandet ind i dem).

## Fund

| # | Krydsforbindelse | Resultat | Brug |
|---|---|---|---|
| 1 | **Sted-validering:** dagbogssidens sted ∈ tidstavlens opholdssted samme dag | 4.137 af 4.216 sammenlignelige sider stemmer (98 %); 79 afviger, mest rejsedage (Napoli ↔ Capri/Paestum; Livorno/Pisa ↔ Torino) | Kvalitetskontrol af stedregisteret; afvigelserne er en redaktionel gennemgangsliste |
| 2 | **Manglende persontags (kø, trin 1.4):** person nævnt i tidstavlen i en periode, hvor dagbogssider findes, men ingen side har personen tagget | 102 tilfælde (fx Chamisso 1831-06-12, Spohr 1833-04-30); 50 yderligere uden nogen dagbogsside i perioden | Kandidater til registerrettelser |
| 3 | **Dagbogens huller:** opholds-/rejsedage uden dagbogsindgang | ~~5.509 af 10.159 dage (54 %)~~ **rettet 2026-10-28: 763 af 8.674 dage (9 %)** — se «Dagbogens huller» nedenfor | Kalenderen viser, hvor Andersen var, når dagbogen tier |
| 4 | **Rejseruter:** led med ≥ 2 linkede steder | 584 af 610 rejseled; 628 af de 630 steder i tidstavlen har koordinater | Rutelag på `kort.html` (bygget) |
| 5 | **Hvem × hvor × hvornår:** personer med dateret sted | ca. 150 personer; fx Jenny Lind i Berlin 19. dec. 1845 – 7. jan. 1846, Weimar 8. jan. – 7. feb. 1846, Wien 24.–29. maj 1854 | «Tidstavle: hvor og hvornår» på personsider (bygget); kandidatkilde til «Begivenhedsdatoer»-facetten |
| 6 | **Værker:** citerede `»titler«` mod værkregisteret | 49 værker knyttet til udgivelsesdato; kun 20 af 49 nævnes i dagbogssider inden for ±60 dage | Tynd forbindelse mellem tilblivelse og udgivelse — kræver bedre værkmatchning før den bruges |
| 7 | **`rejser.tsv`-dækning:** ankomst til opholdssted findes i tidstavlen samme dag | 454 af 601 | De fleste af de øvrige 147 er stavning (Hamborg ↔ Hamburg), så tallet siger kun noget om dækning |

## Kendte begrænsninger

* **Linkning er konservativ.** 2.756 stedlinks, 206 personlinks, 49 værklinks.
  Homonymer, fornavne alene og genitiver af enkeltord linkes ikke. Der er ikke
  målt recall mod en gold-standard (se planens trin 1.3).
* **Forfatteren selv linkes aldrig.** Registrets «Andersen, Hans Christian» er en
  fotograf fra Nykøbing Mors.
* **Stedregisteret mangler enkelte steder** (fx Genua), som derfor ikke linkes.
* **Poster med periode > 1 dag** tæller som dækkende hver dag i perioden;
  nøstede poster (et ophold og et delophold med samme tekst) vises begge.
* **ID-kollision (rettet 2026-10-28, plan trin 1.1):** xlsx-tidstavlens id'er var
  løbende `T0001…` og kolliderede med `event_id` i
  `data/normalized_v092/timeline.csv` (alle 1.446). De er nu `TV{bind:02d}{regnearksrække:04d}`
  (fx `TV010005`) med `content_key` (`c`) i `timeline.js`; SQL-id'erne er uændrede.

## Krydsforbindelse SQL-tidstavle ↔ xlsx-tidstavle (plan trin 1.2)

Målt 2026-10-28. Fil: `data/curated/timeline_crosswalk.csv`, bygget af
`python scripts/normalization/build_timeline_crosswalk.py [--report]`; guard:
`tests/test_timeline_crosswalk.py`. **Hård datogrænse 31.12.1875**
(`scripts/normalization/event_bounds.py`): ingen af de to kilder har poster efter
grænsen, så intet blev droppet — men grænsen håndhæves, og testen fejler hvis en ny
kilde bryder den.

Metode: kandidater er xlsx-poster hvis periode indeholder SQL-begivenhedens dag.
Tekststøtte måles på idf-vægtede ordstammer (cosinus-agtig `score`; `cover` =
hvor meget af xlsx-teksten SQL-teksten dækker). Et enkelt stednavn («København.»)
giver derfor *ikke* et match, kun kontekst. Upræcise SQL-datoer (måned/år) matches
aldrig alene på dato.

| `status` | SQL-begivenheder | Betydning |
|---|---:|---|
| `auto` | 212 | samme dag + tydelig tekststøtte + klar vinder; ækvivalens hævdet |
| `review` | 179 | samme dag + delvis tekststøtte, ikke entydig — **synlig kø** (op til 5 rækker pr. begivenhed; udfyld `reviewer` og `decision` = `ja`/`nej`) |
| `kontekst` | 190 | begivenheden finder sted under en xlsx-post (ophold/rejse) hvis tekst den dækker — *ikke* samme begivenhed |
| `ingen` | 865 | dokumenteret i `note`: `ingen_kandidat` 201 · `ingen_tekststøtte` 444 · `upræcis_dato` 219 · `ingen_dato` 1 |

I alt 1.464 rækker for 1.446 begivenheder; xlsx-poster med en `auto`-partner: 212 af
1.745. 178 rækker er desuden koblet til en udgivelsesbegivenhed fra `bibliografi`
(`bp_event_id`, ±1 år; fx T0233 *Improvisatoren* ↔ BP00797 på samme dag; `BG…` = samlet
begivenhed for småtryk, matchet via medlemsværkernes `vid`, 0 dage = datoen ligger i perioden).
`context_xlsx_id` på `ingen`-rækker peger på den xlsx-periode, begivenheden falder i.
Håndvalgte `reviewer`/`decision` bevares ved genkørsel (nøgle: `xlsx_key` + `sql_event_id`).

**Kendt begrænsning:** tærsklerne (`AUTO` 0,4 · `REVIEW` 0,25 · `COVER` 0,5) er
kalibreret ved stikprøve, ikke mod en gold-standard; `auto` ser pålidelig ud, men
andelen af korrekte er ikke målt (jf. trin 1.3). 444 `ingen_tekststøtte` er en
blanding af ægte «ingen» og begivenheder, hvor SQL- og xlsx-teksten er formuleret så
forskelligt, at ordoverlap ikke fanger dem.

## Køer, huller og entitetsdatoer (plan trin 1.4–1.5)

Målt 2026-10-28. Fælles indlæsning: `scripts/normalization/timeline_linked.py`
(tidstavle + links + dagbog). Guard: `tests/test_timeline_queues_gaps.py`.

### Redaktionelle køer (trin 1.4)

`python scripts/normalization/build_timeline_queues.py` → tre CSV'er i `data/curated/`
med `forslag` (maskinens), `beslutning` og `beslutter` (håndfyldt; bevares ved
genkørsel). En afgjort post rettes i registret, aldrig i tidstavlen.

| Kø | Rækker | Tal i fund ovenfor | Bemærkning |
|---|---:|---|---|
| `queue_timeline_place_deviations.csv` | 80 af 4.259 sammenlignelige sider | 79 af 4.216 | genskabt inden for en side; sider med flere dage afgøres pr. dag |
| `queue_timeline_missing_persontags.csv` | 118 `ingen_tag` (82 har efternavnet på en side i perioden → `kandidatsider`) · 6 `ingen_dagbogsside` · 2 `uden_for_dagbogen` | 102 (+ 50) | enhed er nu (person, tidstavlepost), ikke person; poster over 366 dage er udeladt |
| `queue_timeline_work_mentions.csv` | 29 rækker for 27 værker | 29 af 49 | 44 værker er linket; 17 nævnes ±60 dage fra posten |

De gamle tal (102 + 50, 20 af 49) kunne ikke genskabes præcist, fordi
den oprindelige optælling ikke ligger i repoet; ovenstående er genberegnet.

### Dagbogens huller (trin 1.5)

`python scripts/qa/report_timeline_gaps.py` → `data/normalized/timeline_gaps.csv`.
`diary.csv` har **én række pr. dateret overskrift**, ikke pr. side (12.407 rækker,
4.413 sider, 8.204 forskellige datoer). Det tidligere tal «5.509 af 10.159 dage» er
sandsynligvis regnet med én dato pr. side (det giver 4.872 af 8.674, 56 %) og var
derfor et artefakt. Med alle overskrifter:

| Bind | Periode | Opholdsdage | Uden dagbog | Andel |
|---|---|---:|---:|---:|
| I | 1825-09-16 – 1834-07-30 | 486 | 70 | 14 % |
| II | 1836-06-01 – 1844-09-29 | 797 | 208 | 26 % |
| III | 1845-10-31 – 1850-08-21 | 738 | 34 | 5 % |
| IV | 1851-02-02 – 1860-12-31 | 1.190 | 260 | 22 % |
| V | 1861-01-01 – 1863-12-31 | 1.078 | 17 | 2 % |
| VI–X | 1864-01-01 – 1875-08-04 | 4.227 | 16 | < 1 % |
| mellem bind | | 158 | 158 | 100 % |

Største huller: 1836-06-11 – 1836-12-31 (204 dage, bind II), 1859-12-17 – 1860-05-25
(161, bind IV), 1836-01-01 – 1836-05-31 (152, mellem bind I og II), 1833-06-14 – 08-14
(62, bind I). **Kilde eller vores hul?** Sidenumrene 1..N er sammenhængende i alle
ti bind (testet), så ingen trykt side mangler transskription — hullerne er
**kildens**. Registerhenvisninger til sider *uden for* teksten (kommentar, bind XI)
er et andet spørgsmål: `scripts/build_mockup/report_untranscribed_pages.py`.

### Entitetsdatoer (trin 1.5)

`python scripts/normalization/build_entity_dates.py` → `data/normalized/entity_dates.csv`
(324 rækker; kolonner efter [`temporal-modelling.md`](temporal-modelling.md): `event_type`,
`date_start`/`date_end`, `precision`, `source`, `method`). Omfang: de 150
tidstavle-linkede personer (fødsel/død fra etiketten, kun eksakte former — 147 har
dato) og 44 værker (18 har dato: 25 `publication` + 4 `reprint` fra `bibliografi`
og tidstavletekst, 2 `premiere`, 1 `performance`). 60 dødsår ligger efter 1875 og er
beholdt: det er oplysninger om personen, ikke kortlagte begivenheder. **Knappen
«Begivenhedsdatoer» i `diaries.html` er fortsat ikke aktiveret.**

### Navnelinkning (trin 1.3) og KB-links (trin 2.3)

* Stikprøven på 300 poster (10 pr. bind × type) ligger i `data/curated/timeline_gold.csv`
  (`python scripts/qa/timeline_gold.py draw`); **ingen er annoteret endnu**, så
  precision/recall er ikke målt. `score` og `tests/test_timeline_gold.py` er klar.
* `data/curated/kb_link_status.csv`: alle 92 KB-sider svarer 200 (2026-10-28);
  `build_timeline.py` udelader 404/410-links, hvis nogen opstår.
