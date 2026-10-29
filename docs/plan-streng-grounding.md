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
| 2. Kandidatgenerering | Alle n-grammer (1–4 ord) med stort begyndelsesbogstav/titel/forbogstaver som kandidater; regler som baseline | Recall på guldstandarden |
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
