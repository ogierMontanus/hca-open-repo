# Notat: hvor på dagbogssiden står personen? — vurdering og plan for et lærende grounding-trin

Status: **notat / fremtidig opgave** · 2026-10-29 · hører til
[`crowdsourcing.md`](crowdsourcing.md) og [`data-model/ner-page-task.md`](data-model/ner-page-task.md)

## 1. Baggrund

Registret (`references.csv`) siger, **hvilke** entiteter der er knyttet til en
dagbogsside — ikke **hvor i teksten** de står. Crowdsourcing-grænsefladen
peger bidragyderen ind på siden og, hvor det kan, på den daterede post og
navnestrengen. Spørgsmålet var: hvor godt kan vi egentlig udpege
navnestrengen? Svaret nedenfor er en måling, ikke et skøn.

## 2. Vurdering af den nuværende metode

**Hvad prototypen gør.** Den tager *efternavnet* fra registeretiketten og
slår det op som helt ord i sidens tekst (`entry_anchor()` i
`scripts/build_mockup/build_crowd_queue.py`). Første daterede post med et match
bliver ankeret; samme streng bruges til `#:~:text=`-fremhævning. Det er et
ordmatch, ikke en genkendelse af egennavne.

**Måling over de 5.607 omtaler i arbejdskøen** (2.285 personer;
tekst fra `diary.csv`, linjetags og orddeling over linjeskift fjernet):

| | Omtaler | Andel |
|---|---:|---:|
| Efternavnet findes ordret på siden | 3.193 | 57 % |
| + genitiv (*Rimestads*, *Kraghs*, *Parodis*) | 369 | 7 % |
| + stavevariant, ét tegn fra, navne ≥ 5 bogstaver (*Brun/Bruun*, *Giessing/Giesing*) | 819 | 15 % |
| **Stadig ikke fundet** | **1.226** | **22 %** |

Til sammenligning ankrer prototypen i dag kun 3.174 omtaler til en post (57 %).

**Fejl og svagheder:**

1. *Genitiv-s afvises* af regexen — ren fejl, ikke en afgrænsning.
2. *Aa/Å, ö/ø, diakritika* giver kun 94 omtaler ekstra; det er ikke hovedproblemet.
   Stavevarianter og bøjning er.
3. *Tvetydighed.* 786 af køens personer deler efternavn med mindst én anden; i 171
   omtaler står efternavnet i flere poster på samme side, og første post
   vælges. Ingen skelnen mellem to personer med samme efternavn.
4. *Falsk sikkerhed i teksten.* Grænsefladen skriver »navnet står i posten
   for …«, men har kun fundet et ord. Det bør hedde »efternavnet forekommer i
   posten«.
5. *Fremhævningen* (`#:~:text=`) virker kun, hvis navnet står i én tekstnode
   (3.370 af 5.607), og ikke i alle browsere.
6. *De 22 %* er et blandet restsæt: navnet står kun som forbogstav, titel eller
   pronomen; registerhenvisningen peger måske på nabosiden; eller navnet er
   stavet så frit, at ingen simpel regel finder det. Årsagsfordelingen er
   **ikke** undersøgt.

**Hvad vi burde have genbrugt.** Repoet har opgaven formaliseret:
`data/normalized/ner_page_grounding.csv` (+ `_review.csv`) og
[`ner-page-task.md`](data-model/ner-page-task.md) — tegnposition
(`mention_start`/`mention_end`), `confidence` og `method`
(`full_name_proximity`, `surname_only`, `given_name_only`, `place_full_label`,
`place_first_word`, `no_match`). Filen dækker dog kun **bind VI–VII
(751 sider, 11.581 rækker)**, og 5.145 af rækkerne er `no_match` (44 %). Kun
`full_name_proximity` (491 rækker) har confidence ≥ 0,9. Prototypen bruger den
ikke; den bygger sit eget, grovere match.

## 3. Fremtidig opgave: et lærende grounding-trin med mennesket i løkken

### 3.1 Idé (fra projektleder)

Der trænes en maskinlæringsmodel, der forbedrer præcisionen af genkendelse af
navneord og lærer, **hvilke ord og ordkombinationer der har høj sandsynlighed for
at henvise til en omtalt person**. Som supplement til de regelbaserede metoder
får modellen til opgave at behandle de **resterende ~20 %**, der endnu ikke kan
kategoriseres: for hver (side, entitet) foreslår den **op til tre sandsynlige
strenge** med henvisning til den givne entitet. **Et menneske vælger** den
rigtige streng. Valgene bruges som træningsdata, så modellen iterativt gætter
mere og mere præcist.

(Målingen i §2 giver 22 % ikke-fundne i køen efter eksakt + genitiv +
1-tegns-variant; det er den restmængde, ordningen skal tage. Andelen skal
genmåles, når reglerne er rettet.)

### 3.2 Opgavens præcise form

Entiteten er **givet** (`entity_id` fra `references.csv`); siden er givet
(`vol`, `page`, tekst fra `diary.csv`). Modellen skal *ikke* finde ukendte
personer, kun **rangere kandidat-spans** i sidens tekst:

```
input   (entity_id, label, beskrivelse, vol, page, sidetekst, øvrige entiteter på siden)
output  op til 3 kandidater: {start, slut, streng, score, begrundelse}   (+ »ingen af dem«)
```

1:1-reglen fra `ner-page-task.md` gælder: en streng tilhører højst én entitet på
siden; en reel tvetydighed afspejles i scoren, ikke ved dobbelt tildeling.

### 3.3 Faser

| Fase | Indhold | Mål |
|---|---|---|
| 0. Ret reglerne | genitiv, bøjning, stavevarianter, forbogstaver (»Hr. G.«), titler (»Etatsraad X«); genbrug `ner_page_grounding.py`; udvid det til bind I–V og VIII–X | Genmål restmængden; sænk fra 22 % |
| 1. Guldstandard | Stikprøve (fx 300 sider på tværs af bind og årtier) markeret af mennesker; også *negative* eksempler (»navnet står ikke på siden«) | Evalueringssæt, aldrig brugt til træning |
| 2. Kandidatgenerering | Alle n-grammer (1–4 ord) som kandidater, *uden* at kræve stort begyndelsesbogstav (1800-tals-retskrivning skriver alle navneord med stort, se §3.8); regler som baseline | Recall på guldstandarden |
| 3. Model | Rangering af kandidater; træk: ordform, kapitalisering, position, omgivende ord (titel, »Fru«, »Hr.«, relationsord), afstand til andre kendte navne, entitetens egne attributter (køn, nationalitet, erhverv, beskrivelse), bind/periode, stavevarianter mod registeretiketten. Start simpelt (gradient boosting på træk), før der overvejes sekvensmodeller | Top-3-recall > baseline |
| 4. Aktiv læring | Modellen sender de mest *usikre* og de mest *informative* tilfælde til menneskelig udvælgelse | Færrest mulige menneskelige valg pr. procentpoint forbedring |
| 5. Iteration | Hvert valg → træningsdata; gentræn; mål på guldstandarden | Præcision pr. runde |

### 3.4 Menneskets rolle — og genbrug af crowdsourcing-grænsefladen

Valget er en lille opgave: *vis siden (link, ikke kopi), vis op til tre markerede
strenge, vælg én — eller »ingen«/»jeg markerer selv«.* Den passer ind i
crowdsourcing-prototypen:

* Et nyt bidragsfelt, `mention_span` (side, tegnposition, streng), med samme
  sikkerhedsgrader, kommentar og redaktørgodkendelse som de øvrige felter
  (`taxonomy.py` → `FIELDS`; valideringen skal ændres i `validate.py` **og**
  `crowd-validate.js`, jf. `CLAUDE.md`).
* Redaktøren kan få en hurtig »vælg streng«-kø, adskilt fra identifikationskøen.
* Bidragsydernes manuelle markeringer (»her står hun«) er den eneste *ægte*
  grounding og er de mest værdifulde træningseksempler.
* Valg skal logges med hvem, hvornår og hvilke kandidater der blev vist
  (inkl. den rækkefølge modellen gav), så modellens egne bias kan måles.

### 3.5 Evaluering

* **Primært mål:** top-1- og top-3-præcision og -recall på guldstandarden;
  særskilt for *tvetydige* efternavne og for de ~20 %-restsæt.
* **Kalibrering:** er en score på 0,9 rigtig i 90 % af tilfældene? Det styrer,
  hvornår noget må vises som »fundet« uden menneskelig bekræftelse.
* **Opdelt rapportering** pr. bind/periode, pr. persontype (kongelige, tjenestefolk,
  udlændinge) og pr. nationalitet — modellen vil let lære danske efternavne bedst.
* **Regression:** modellen må ikke forringe den regelbaserede del; kør begge
  på guldstandarden i hver runde.

### 3.6 Risici

| Risiko | Imødegåelse |
|---|---|
| Modellen bekræfter egne fejl (menneskets valg er farvet af, hvad der vises først) | Vis kandidater i tilfældig rækkefølge for en del af opgaverne; mål forskellen |
| Mennesker er uenige | Mindst to vælgere pr. tilfælde i en delmængde; mål inter-annotator-enighed |
| Lille, skæv træningsmængde (kun bind VI–VII har grounding i dag) | Guldstandarden skal dække alle bind, også uden dato |
| Almindelige efternavne (Hansen, Andersen) dominerer | Skelnen mellem personer med samme efternavn er en egen delopgave i evalueringen |
| Falsk sikkerhed i grænsefladen | Vis altid *metode* og *score*; sig »efternavnet forekommer i posten«, ikke »personen står her« |
| Personoplysninger i træningsdata | Registret og dagbøgerne er udgivne kilder; bidragydernes navne og kontakt holdes ude af træningssættet |

### 3.7 Datamodel (forslag)

Genbrug kolonnerne i `ner_page_grounding.csv` og tilføj proveniens:

```
ref_page_id, vol, page, entity_id, mention_text, mention_start, mention_end,
confidence, method,                         ← som i dag
rank (1–3), model_version, candidate_set_id, ← nyt: kandidatlistens identitet
decided_by, decided_at, decision (picked | none | manual), source (model | rule | human)
```

Menneskets valg gemmes i et eget lag (som crowdsourcing-bidragene), ikke ved at
overskrive modellens kandidater, så hver runde kan genskabes.

### 3.8 Første annoteringsdata: almanakken, 26 poster (Søren Dall-Hansen, 2026-11)

Annoteringssiden `almanak/annotation/` (s. 35–36 i 1990-udgaven, 29. jan.–23. feb.
1840) har givet den første håndmarkerede facitliste: 89 spans (58 Person, 21 Værk,
9 Institution, 1 Sted, 0 Andet) i alle 26 poster; kolonnerne `annotator, post_id,
print_page, start, end, string, type, reg_id, reg_label, identification_free,
unsure, note`. Format og indhold passer til §3.2/§3.7.

**Kontrol.** Alle 89 spans stemmer tegn for tegn med postteksten i annoteringssiden
(`text[start:end] == string`, `end` eksklusiv, positioner i den rettede tekst
`TEXT_VERSION = ocr-2023-rettet-mod-sidebillede-2026-10-27`). Offsets er kun gyldige
mod netop den tekstversion og skal gemmes sammen med den.

**Hvad den kan bruges til:** pilot-guldstandard og test af annoteringsvejledning;
facit til at måle regelmatchet (9 af 58 personstrenge, 16 %, er bøjede:
*Collins, Heibergs, Hartmanns, Pallesens, Holsts, Wulffs, Hornemanns* — præcis
det, §2 fandt, at efternavnsmatchet mister).

**Hvad den ikke kan (endnu):** træne en model — 26 poster, én måned, ét stykke
(*Mulatten*s premiere), én annotator, ingen overlap med dagbøgerne (diary.csv har
ingen rækker for jan.–feb. 1840). `reg_id`/`reg_label`/`unsure`/`note` er tomme:
det er spans og typer, ikke identifikation.

**Nye fund.**

* **Stort begyndelsesbogstav er ikke et navnesignal i denne retskrivning:** 131 af 235
  ord med stort (56 %) ligger uden for annoteringerne (*Middag, Prøve, Brev, Billet …*).
  Modellen må lære kontekst (*hos, af, med, Fru, Pastor, Prof:*), ikke kapitalisering.
* **Reglerne dækker ikke alle tilfælde.** Annoteringssiden havde allerede »foreløbige regler« (titel og endelse medtages) og en liste over uafklarede spørgsmål; Søren fulgte dem. Men titel er med i nogle tilfælde (*Fru Colbjørnsen,
  Pastor Boye, Etatsraad Neergaard, Prof: Guldberg*), ikke i andre (*Eduard, Hansen*);
  én streng for to personer (*Carl og Otto Moltke*); forkortelse med
  (*Skues: Holst*); almindelige navneord som Værk (*Roman, Consert, 2 Billeder*);
  rolle som person (*Kongen, Kronprindsessen*); to stavemåder af samme navn
  (*Wilstrup/Vilstrup*, *Fædrenelandet/Fædrelandet*).
* **Sandsynlige huller** (kan gennemgås med annotatoren): *Les Epaves* (02-06),
  *Masaniello* og *Faaborg* (02-20), *Foreningen* (02-17, 02-23).

**Konsekvens:** brug almanakken til at *skrive vejledningen* og afprøve
målemetoden, og få mindst en anden annotator på de samme 26 poster (enighed), før
tallene bruges som mål for modellen.

### 3.9 Næste stikprøve: overlap mellem dagbog og almanak (uden anden annotator)

**Overlap** (`almanak/data/extracted/aligned.csv` mod `diary.csv`, dage med tekst i begge): 1.878 dage
mellem 1833 og 1873; dagbogen har 8.204 dateret dage, almanakken 5.213. Størst i
1841 (175 dage), 1846 (251), 1860 (179), 1861 (148), 1866 (112), 1843–44 (~100 pr. år) og
1855 (87). Længste sammenhængende forløb: 31.10.1840–14.6.1841 (227 dage),
31.10.1845–20.2.1846 (113), 1.5.–13.8.1846 (105), 30.1.–30.4.1843 (91), 17.7.–21.9.1855 (67).
Jan.–feb. 1840 (Sørens første 26 poster) har *intet* overlap; dagbogen starter først
31.10.1840. Almanakposter er korte (median 55 tegn), dagbogsdage ca. 11× længere
(median 629).

**Anbefalet størrelse: 4 blokke × 8 sammenhængende overlapdage = 32 dage**, hver dag med
både almanakpost og dagbogstekst:

| Blok | Dage | Bind | Almanak (tegn) | Dagbog (tegn) | Sider | Personer i registret på siderne |
|---|---|---|---:|---:|---|---:|
| A | 15.–22.2.1841 | II | 813 | 6.874 | 128–133 | 60 |
| B | 1.–8.1.1846 | III | 1.009 | 6.871 | 38–42 | 56 |
| C | 17.–24.7.1855 | IV | 855 | 4.318 | 164–167 | 42 |
| D | 4.–11.7.1866 | VII | 524 | 6.263 | 134–138 | 22 |
| **I alt** | **32** | | **3.201** | **24.326** | | |

Valgt for: tre bindperioder og to retskrivningsperioder (1840'erne, 1850–60'erne);
sammenhængende dage, så samme navn dukker op flere gange (tvetydighed kan måles); blok D ligger i
bind VII, hvor `ner_page_grounding.csv` allerede har en automatisk grounding (28 `no_match`,
15 `surname_only` …), så den kan sammenlignes direkte. Dagbogstekstens længde er holdt på
ca. 4.400–7.000 tegn pr. blok, så ingen blok er tung.

Tegntal efter rensning af teksterne (se nedenfor).

**Annoteringssiden er bygget** (`almanak/annotation/build_overlap_page.py` + `template-overlap.html`; output
`almanak/annotation/out/overlap-annotering.html`, en enkelt fil, der åbnes i en browser):

* fire faner (blok A–D), hver dag viser almanakposten og dagbogsteksten under hinanden, med link til Det Kgl.
  Biblioteks faksimile for hver dagbogsside (ny fane);
* samme markering som Sørens side (type på tasterne 1–5, usikker, note), men **identifikation er flyttet bag en
  foldet »valgfri«-boks**: det er strengene, vi skal bruge;
* siden måler selv **aktiv tid pr. blok** (kun mens fanen er synlig og brugt inden for 60 s) og sender den med
  resultatet; så afgøres »skær til to blokke« på data, ikke på skøn;
* resultatet kopieres som JSON (med gennemgåede dage, også dem uden markeringer) eller TSV (de tolv kendte
  kolonner + `source`, `block`, `text_version`, `block_active_seconds`);
* `check_annotations.py` kontrollerer et resultat mod siden (`text[start:end] == string`, overlap, typer,
  gennemgåede dage, tid), og virker også på Sørens første side.

**Tekstversioner** (skrives i hver række; offsets gælder kun mod dem):
almanak `ocr-2023-ukontrolleret-2026-11` (PDF-tekstlaget, *ikke* kontrolleret mod sidebilledet, i modsætning til
s. 35–36); dagbog `diary.csv-2026-11-linjetags-fjernet-orddeling-samlet` (linjetag fjernet, linjeskift = mellemrum,
bindestreg ved linjeskift fjernet før lille bogstav og ellers bevaret, en dags rækker på flere sider sat sammen).

Nye forslag til reglerne, markeret som sådan i siden: to navne i én frase mærkes hver for sig (*Carl* og *Otto Moltke*);
almindelige navneord er ikke værker (*Roman*, *Concert*).

**Forventet udbytte:** ca. 60 almanakspans + 100–150 dagbogsspans, i alt ca. 150–200 personspans
(skøn, ikke målt). Det er nok til at se forskelle på ≳ 10 procentpoint mellem to metoder
(±5 point ved 90 %) — ikke nok til at træne en model.

**Tidsforbrug.** Volumen er ca. 28.000 tegn, dvs. ca. 6× det, Søren allerede har gjort (4.400 tegn,
89 spans). Tiden er *ikke målt*; mit skøn er 1½–2½ time i alt, delt i fire sessioner på 30–40 min
(en blok ad gangen). **Bed Søren notere tiden på blok A og afgør derefter:** er den over ca. 45 min,
skæres til blokkene B og D (16 dage, ca. halvdelen).

**I stedet for en anden annotator:** *adjudikering af uenigheder.* Reglerne/modellen markerer
selv teksten; kun de steder, hvor de og Søren er uenige (typisk 20–40 tilfælde), lægges
tilbage til ham som »enig/uenig« — få minutter, og det afdækker både hans huller og
reglernes fejl. Det måler ikke annotatorenighed, så tallene må ikke præsenteres som sådan.

## 4. Anbefalet rækkefølge

1. Ret genitiv og de oplagte stavevarianter i `entry_anchor()`; ret formuleringen i
   grænsefladen; vis *metode* (eksakt / efternavn / ikke fundet). *(lille)*
2. Genbrug `ner_page_grounding.csv` hvor den findes; udvid dækningen til alle
   bind. *(mellem)*
3. Analysér årsagerne til de ~22 % (forbogstav, titel, nabo-side, stavning),
   så modellens målgruppe er kendt. *(lille)*
4. Byg guldstandarden. *(mennesketid — afgør, hvor hurtigt resten kan gå)*
5. Kandidatgenerator + første model + »vælg streng«-opgaven. *(stor)*

## 5. Åbne spørgsmål

1. Hvem bygger guldstandarden, og hvor mange sider kan der afsættes?
2. Må modellens forslag vises for bidragydere på de offentlige sider, eller kun
   for redaktører?
3. Skal en streng, et menneske har valgt, kunne rettes bagefter, og hvem må det?
4. Hvilken minimumsscore får et forslag til at stå som »fundet« uden menneskelig
   bekræftelse?
