# Begivenheder — datarevision (første pas)

Status: målt 2026-10-28 · udført på repoets committede data · hører til
[`events-research-basis.md`](events-research-basis.md) §4 og §6 (trin 1 og 4) ·
foregående: [`temporal-modelling.md`](temporal-modelling.md) (planlagt
`entity_event`-tabel), [`tidstavle-ledsagespor.md`](tidstavle-ledsagespor.md),
[`tidstavle-krydsforbindelser.md`](tidstavle-krydsforbindelser.md)

**Hvad er med, og hvad er ikke.** Revisionen dækker det, der ligger i repoet. SQL-databasen
`hca_db.sql` er *ikke* gennemgået (den ligger uden for repoet; se
[`../plan-tidstavle-data.md`](../plan-tidstavle-data.md) trin 1.0), og
sammenligningen med Schnitzler-projektet, TEI og CIDOC CRM (§6 trin 2–3) er ikke
påbegyndt. «Heuristisk» betyder i tabellerne nedenfor ord-/mønstermatch på fritekst;
tallene er størrelsesordner, ikke en klassifikation.

## 1. Kort: hvad findes hvor

| Gruppe | Kilde | Rækker | Struktureret dato | Struktureret sted | Strukt. personer | Type-felt |
|---|---|---:|---|---|---|---|
| A Liv | `normalized_v092/timeline.csv` (SQL) | 1.446 | `date_iso` (dag/måned/år), kun punkt | nej (prosa) | nej (prosa) | **nej** (kun emner) |
| A Liv | personregister: `(1804–1876)` i label; `personregister_xi_parsed.tsv` | 10.228 / 10.080 | kun *år*: fødsel+død (7.147 med begge; 324 kun død) | nej | — | implicit (fødsel/død) |
| B Værker | `entities.csv` `year_derived`/`date_derived` + år i label | 3.708 | `year_derived` 470 (12,7 %), `date_derived` 228 (6,1 %); 469 labels har et årstal | 13 labels har udgivelsessted i parentes | `person_derived` 1.391 | **nej** |
| B Værker | SQL-tidstavle: udgivelser, påbegyndelser, oversættelser | ~77 heuristiske udgivelses-poster | som ovenfor | prosa | prosa | nej |
| C Rejser/ophold | `rejser.tsv` / `rejser_journeys.tsv` | 1.468 led / 30 rejser | ankomst+afrejse (1.438), 1831–1873 | ja, geokodet (1.468) | nej | `DestinationType`: Stay 601 · Passing through 541 · Overnight stay 266 · Return 31 · Departure 29 |
| C Rejser/ophold | xlsx-tidstavle (`data/HCA_Tidstavler_…xlsx`) | 1.745 | `Fra`/`Til` (1.721 dag, 18 måned, 6 år), perioder | prosa → 2.756 stedlinks (NER) | prosa → 206 personlinks | heuristisk: 663 ophold · 610 rejse · 472 begivenhed |
| C Steder | `places.csv` `visit_status` | 2.433 | — | ja | — | Besøgt 1.789 · Omtalt 644 |
| D Samtid | SQL-tidstavle uden henvisning til Andersen | ≥ 493 (heuristisk) | `date_iso`, bl.a. `1814-00-00` | prosa | prosa | **nej** |

**Hovedresultat:** ingen kilde har et eksplicit begivenhedstype-felt (undtagen
`rejser.tsv`' rejsetype), og kun `rejser.tsv` har strukturerede steder. Alt andet er
dateret prosa. Typer, deltagere og steder skal derfor *udledes* og redaktionelt
bekræftes, ikke blot flyttes.

## 2. Fund pr. datagruppe

### A. Biografiske data

* **SQL-tidstavlen** (1.446 hændelser, DA + EN – 1.444 har engelsk tekst): tekst er HTML
  (`<p>`, `<em>`, `<blockquote>`; 1.432 rækker). Datoen er en tekststreng med `00` som
  pladsholder: **1.226 dag · 139 måned (`1835-03-00`) · 80 år (`1805-00-00`) · 1 uden dato**
  — ikke ISO-gyldig. Kun punkt-datoer (ingen slutdato); varighed ligger i prosaen.
  `ordering` giver rækkefølge inden for en dato; `quarter` er sat for 1.387.
* **Emner:** 213 emner (grupper som «Herregårde i Danmark» 55, «Rejser, udland» 23,
  «Danske værker» 16, «Oversættelser» 13), 2.087 links; **1.051 af 1.446 hændelser har
  mindst ét emne.** Hyppigst: Tyskland 109, Sjælland (og Lolland-Falster) 96, Digte
  59, Skib 57, Forlæggere 56. Emnerne er *tematiske*, ikke begivenhedstyper — der
  findes ikke «fødsel», «udgivelse», «møde».
* **Indlejrede links:** 295 hændelser har ialt 443 hyperlinks til det ældre værksregister
  på `andersen.sdu.dk/vaerk/register/info.html?vid=…` — **196 forskellige `vid`**.
  Der er **ingen krydsreference `vid` ↔ `Reg…`** i `data/` eller `scripts/` (kun `timeline.csv` indeholder `vid=`-links).
  Her ligger den eneste *strukturerede* hændelse→værk-forbindelse i de interne data;
  crosswalken skal findes i SQL-databasen eller bygges på titel.
* **Personer:** fødsels-/dødsår står kun som tekst i `label` (jf. `temporal-modelling.md`,
  som forudsætter en parser-pas). `personregister_xi_parsed.tsv` har `birth_year`/
  `death_year` strukturerede, men kun som år; ingen fødested/dødssted.
* **Dublet-/kollisionsrisiko:** SQL-id'erne `T0001…T1446` er identiske med id'erne i
  `mockup/data/timeline.js` for xlsx-tidstavlen (se plan trin 1.1).

### B. Værkdata

* **Begivenheder er gemt i titlen.** 469 af 3.708 værks-labels indeholder et årstal;
  134 slutter med `(ÅÅÅÅ)`. `year_derived` er sat for 470 (12,7 %) og `date_derived`
  for 228 (6,1 %) — *afviger fra* de 2,9 % / 1,4 %, `temporal-modelling.md` anfører;
  tallene i det dokument skal opdateres eller forklares.
* **Flere årstal i ét felt:** 50 værker har 2–4 årstal i `year_derived`. De dækker
  *forskellige ting*: et interval for et flerbinds værk («1847, 1872» = `Gesammelte
  Werke (1847-72)`), eller flere udgaver («1858, 1865, 1866»). Intervallets to
  endepunkter og de enkelte udgaver er altså kodet ens, men er forskellige
  begivenhedstyper.
* **`Ͻ`-notationen** (22 værker: «1850 Ͻ: 1849») markerer, at trykåret afviger fra det
  faktiske: *to datoer for samme udgivelse*, med forskellig sikkerhed.
* **Oversættelser er egne værksposter** («Tyske - Die Dryade (Leipzig 1868)»,
  «Engelske - … (New York 1873)»): oversættelse = (sprog + sted + år) kodet i
  `form_h3` og labelprosa; `work_languages.csv` (1.154, detektor) giver sprog med
  konfidens. Dermed er «udgivelse i flere lande» i dag *flere værker*, ikke flere
  begivenheder.
* **Udgave-/begivenhedsgrænsen:** «Improvisatoren - 3. Opl. (1866)» er en separat
  registerpost (`Reg001738`), mens 2. oplag (1837) kun findes som SQL-begivenhed
  (T0256). Se `wemi-and-relations.md` for værk/udgave-niveauer.
* **Tilblivelse:** der er næsten ingen manuskript-/skrivefase-data. `date_derived`
  rummer enkelte lejlighedsdigte med dags-dato (fx «…lovet Dronning Maria af Bayern 20…»
  → 1854-06-20), der er *sammensætnings-/lejlighedsdatoer*; ellers findes kun SQL-poster
  som «Påbegynder *Improvisatoren*» (T0207, 1833-12-27). Revision/færdiggørelse er ikke
  registreret. **Fase-modellen kan ikke belægges med nuværende data** — kun spor.

### C. Rejser og ophold

* **`rejser.tsv` er den bedst strukturerede kilde:** 30 rejser (`RejseID`), hver en
  *kæde* af led med type (Departure → Passing through/Overnight stay/Stay → Return),
  ankomst-/afrejsedato, transportmiddel (1.437 af 1.468), koordinater (alle). Dermed
  findes konfiguration 3 («forløb eller kæde») allerede — som tabelrækkefølge inden for
  `RejseID`, ikke som eksplicitte relationer. `rejser_journeys.tsv` har titel,
  årstal, beskrivelse, lande og pris pr. rejse. Dækning 1831–1873, men kun 30 rejser.
* **xlsx-tidstavlen** har 610 rejseled («Fra X over Y til Z») og 663 opholdsposter —
  langt flere end Rejser, men kun som prosa med NER-links. 454 af Rejsers 601
  opholdsankomster ligger på samme dag i xlsx; resten er hovedsagelig stavning.
* **Periode vs. punkt:** xlsx: 823 enkeltdags-, 836 på 2–30 dage, 86 på > 30 dage, 1 > 365.
  Ophold (tilstand) og rejseled (bevægelse) er blandet i samme kolonne; skellet er kun
  heuristisk (`classify()` i `build_timeline.py`).
* **Nøstede/overlappende poster:** et ophold («Weimar. Jenny Lind.») overlapper
  delophold og dagsbegivenheder; 3 identiske dubletter og 1 nøstet par på samme periode
  (kilden har «Berlin.» og «Berlin. Jenny Lind.» for samme periode).
* **Steder:** `visit_status` (Besøgt/Omtalt) er den eneste sted-egenskab, der er en
  *tilstand relateret til begivenheder* — og den er en gruppering, ikke en begivenhed.

### D. Tidstavlens samtidsbegivenheder

* Der er mindst **493 SQL-hændelser uden henvisning til Andersen** (heuristik: ingen
  «Andersen»/«han»/«HCA»), fx «Fredsslutning efter napoleonskrigene» (`1814-00-00`),
  revolutionen i Paris, tronskifter. Nogle er kun pladsholdere («Ukendt»).
* De mangler ethvert eksternt id og enhver struktureret deltager/sted. xlsx-tidstavlen
  har 16 poster med politik-/krigsord (heuristisk); om de er samtidsbegivenheder eller
  Andersens egne oplevelser er ikke gennemgået.
* **Konsekvens:** gruppe D kan ikke udelukkende kobles til eksterne kilder; ca. en
  tredjedel af SQL-hændelserne skal enten afkobles fra Andersen i modellen eller have
  en lokal beskrivelse. Prioritér: først *datoer og betegnelser* som lokale begivenheder,
  derefter Wikidata-forslag med manuel bekræftelse.

## 3. Heuristisk typefordeling (størrelsesorden)

| Type (ord-/mønstermatch) | xlsx-tidstavle (1.745) | SQL-tidstavle (1.446) |
|---|---:|---:|
| rejseled («Fra X til Y …») | 609 | 1 |
| møde/besøg (Besøgt, Gæst, truffet …) | 97 | 123 |
| udgivelse (udkom, udgave, hefte …) | 37 | 77 |
| død | 15 | 61 |
| fødsel | 3 | 13 |
| giftermål/forlovelse | 2 | 36 |
| premiere/opførelse | 8 | 20 |
| orden/udnævnelse | 2 | 10 |
| politik/krig | 16 | 10 |
| ikke genkendt (ikke-ophold) | 339 | – |

SQL-tidstavlen er altså den *biografiske* kilde (liv, udgivelser, møder, dødsfald),
xlsx den *bevægelses*kilde (ophold, rejser). De overlapper i 1.109 af 1.445 daterede
SQL-hændelser (660 med samme startdato) — samme begivenhed i to formuleringer er
reelt forekommende og kræver en ækvivalensrelation (`same_as`), ikke sammenlægning.

## 4. Svar på hjælpespørgsmålene ud fra data

| Spørgsmål | Hvad data viser |
|---|---|
| 1. Én eller flere hændelser? | Udgivelser i forskellige lande er allerede *separate* hændelser i SQL (T0233 dansk, T0234 tysk, T0461 russisk, T0462 engelsk, T1474 fransk) — men ikke i værkregisteret, som kun har én årstalskolonne. |
| 2. Forskellige datoer: varighed eller flere ting? | xlsx er konsekvent *periode* (`Fra`–`Til`); SQL er konsekvent *punkt*. Samme fysiske begivenhed kan optræde som begge. |
| 3. Overordnet begivenhed med underbegivenheder? | `rejser.tsv`' `RejseID` er den eneste eksplicitte forælder (30). xlsx har implicit nesting (ophold ⊃ besøg) uden relation. |
| 4. Begivenhed eller blot tidslig egenskab? | Værker: `year_derived`/`(ÅÅÅÅ)` er egenskab; SQL-poster for samme værk er begivenheder. Det er *samme* oplysning på to niveauer. |

## 5. Afprøvning på repræsentative eksempler (fra de faktiske data)

| Eksempel | Konkret rækkesæt | Bærer modellen? |
|---|---|---|
| Biografisk hændelse | SQL T0002: «H.C. Andersen fødes i Odense. Hjemmedøbt samme dag.» 1805-04-02; xlsx række 1 «Født i Odense.» samme dato | Ja som punkt; **to kilder, samme hændelse** (`same_as`); sted kun i prosa («Odense»), person implicit |
| Længere ophold | xlsx: «Weimar. Carl v. Beaulieu-Marconnay. Arvestorhertug Carl Alexander. Jenny Lind.» 1846-01-08 → 1846-02-07 | Ja som periode; deltagere kun som NER-links (konfidens ukendt); overlapper et delophold |
| Rejse | `rejser.tsv` RejseID 2 (1833-04-22 → 1834-08-03; København → Travemünde → Lübeck → Hamborg (23.–27. apr.) → Harburg → Celle …) + xlsx-led for samme periode | Ja som kæde; **to uafhængige kæder** (Rejser: 30 rejser; xlsx: 610 led) skal forbindes |
| Manuskriptfase | SQL T0207: «Påbegynder *Improvisatoren*. Læser første kapitel op for …» 1833-12-27 | Kun *påbegyndelse*; ingen revision/færdiggørelse. **Utilstrækkeligt belagt** |
| Udgivelse i flere lande | *Improvisatoren* (`Reg001737`; `Reg001738` = 3. opl.): T0233 dansk 1835-04-09 (C.A. Reitzel, København), T0234 tysk «1835-04» (månedspræcision, Kruses oversættelse), T0256 2. oplag 1837-06-28, T0462 engelsk 1845-02 (Mary Howitt), T0461 russisk 1845, T1474 fransk 1847, T0674 *Samlede Skrifter* 1853 | Ja som *flere udgivelsesbegivenheder*; kræver sprog + sted + udgave pr. begivenhed, og værk→oversættelse som relation. `vid=401` i teksten er det eneste strukturerede værk-link |
| Generel historisk begivenhed | SQL: «Fredsslutning efter napoleonskrigene» `1814-00-00` (årspræcision) | Dato og betegnelse kan bevares; deltagere/sted mangler; Wikidata-forslag kræver manuel bekræftelse |

## 6. Krav til modellen udledt af data (ikke en specifikation)

1. **Datoer:** (start, slut, præcision dag/måned/år/kvartal, kvalifikator ca/sommer/årets
   slutning, evt. «ugyldig i kilden») — ikke `00`-pladsholdere. Bevar
   original-dateringsteksten (xlsx har den i cellenoten).
2. **Type som kontrolleret ordforråd** (SKOS-egnet), *udledt* og redaktionelt
   bekræftet; SQL's 213 emner er tematiske og kan ikke genbruges som typer, men
   kan blive en separat dimension (`emne`).
3. **Deltagere/steder som links med metode og konfidens** (NER, manuel, kilde-link),
   ikke som indlejret prosa; `vid`-crosswalken udnytter de 443 eksisterende links.
4. **Relationer:** `del_af` (rejseled → rejse), `samme_som` (xlsx ↔ SQL),
   `oversættelse_af`/`udgave_af` (udgivelse → værk/udgave), og rækkefølge
   (`ordering`).
5. **Status:** begivenhed vs. hypotese; ingen kilde har et sikkerhedsfelt i dag, men
   xlsx har redaktionelle noter (OCR-rettelser, ugyldig dato 1841-02-29) som skal bevares.
6. **Sprog:** SQL er tosproget (EN 1.444), xlsx kun dansk — modellen skal kunne bære
   tekst pr. sprog pr. begivenhed.
7. **Forholdet til `entity_event`** i `temporal-modelling.md`: den planlagte tabel
   (`entity_id`, `event_type`, `date_start`, `date_end`, `precision`, `source`) er en
   *delmængde* — én deltager pr. begivenhed, ingen sted, ingen relationer. En
   begivenhedsentitet med deltagerlinks kan generalisere den uden at bryde reglen om at
   holde `entity_dates` og `mention_dates` adskilt (en begivenhed er et *entitetsdato*-spor).
   Afgør før `entity_event.csv` bygges.

## 7. Åbne spørgsmål

1. SQL-databasen: findes tabeller for personer, værker, steder eller breve med
   begivenheder (fx `vid`-register, udgivelser), som ikke er udtrukket? (plan trin 1.0)
2. Er `date_derived` på værker en *tilblivelses-*, *lejligheds-* eller *udgivelses*dato?
   Betydningen skal afgøres pr. genre, før den bruges som begivenhedstype.
3. Skal gruppe D lagres som egne begivenheder uden Andersen, eller kun som kontekst
   knyttet til tidsperioder? (påvirker, om Wikidata skal bruges som kilde eller kun som
   reference)
4. Hvem må afgøre `samme_som` mellem de to tidstavler, hvor teksterne ikke er identiske?

## 8. Næste skridt

1. Kør plan trin 1.0 (inventar af SQL-databasen) — afgør 1. og `vid`-crosswalken.
2. Byg `data/curated/timeline_crosswalk.csv` (plan trin 1.2) → første `samme_som`.
3. Udfør §6 trin 2–3 i `events-research-basis.md` (Schnitzler/TEI/CIDOC) som *live*
   gennemgang med verificerede kilder.
4. Skriv specifikationen (trin 5) først, når punkterne i §6 er afprøvet på
   mindst de seks eksempler i §5.
