# NER-opgave pr. dagbogsside (adapteret fra NER4andersen)

## Baggrund

`ner4andersen` definerer en flertrins-berigelsespipeline (harvest →
konsolidering → forsoning → kuratering) der arbejder på tværs af hele
registret, med kilde-provenance pr. kandidat (`sources[]`: bind, side,
type) og en confidence-score pr. forsoningskandidat (§6–§7 i
`plan-v3.md`).

**`data/normalized/references.csv` er facit for opgaven** — den er den
rå entitetsforekomst-tabel: én række pr. dagbogsside↔entitet-link,
udledt af `entities.csv` (`entity_id`/`entity_label` er fremmednøgler
ind i registret) og af `RefInDiaryPage`-arket i kilde-Excel'en
(`raw/HCA-Repository V0.82.xlsx`, se `scripts/normalization/
hca_xlsx_to_csv.py`). Filen fortæller **hvilke** entiteter der er
knyttet til hvilken side — ikke hvor i sidens tekst de faktisk står.
69.405 rækker, én pr. `(vol, page, entity_id)`-kombination (ingen
dubletter); antallet af entiteter pr. side varierer fra 1 til over 200
(fx bind III side 64: 17 forskellige entiteter). `page_id`-feltet i
denne fil er **ikke** en sammensat side-nøgle som i
`data/normalized_v092/references.csv` (`Pag{vol:02d}{page:04d}`) —
her er det et unikt løbenummer pr. række, og `seq` er et globalt
løbenummer, ikke et forekomst-antal. Side-nøglen er derfor `(vol,
page)`, matchet mod `data/normalized/diary.csv`.

Dette dokument definerer opgaven, der supplerer denne kendte
entitetsliste pr. side med **hvor i teksten** hver entitet faktisk
optræder — en **grounding-opgave**, ikke åben NER-udtræk: entitets-
identiteten (`entity_id`) er allerede givet af `references.csv`;
opgaven er at lokalisere og skelne de konkrete forekomst-strenge i
sidens rå tekst.

### Eksempel: en side med mange entiteter på tværs af flere registre

Bind V, side 20, er blandt de sider i `references.csv` med flest
linkede entiteter fordelt på flest registertyper: **38 links i alt —
30 fra PERSON-REGISTRET, 5 fra STED-REGISTRET, 3 fra VÆRK-REGISTRET**
(værk-links er uden for scope for selve grounding-opgaven, jf.
ner4andersen §11, men tælles med her som eksempel på "flere
indekser" på samme side).

Live side hos Det Kgl. Bibliotek (fra `data/normalized/
kb_diary_links.csv`, kolonne `kb_url`, kilde `workbook`):

**<https://epub3.kb.dk/hcadag/epub3/EPUB/hcadag05_040_20.xhtml>**

(Linket kunne ikke verificeres live fra denne session — udgående
adgang til `epub3.kb.dk` er blokeret af sandkassens netværksproxy —
men det er hentet direkte fra repoets egen `kb_diary_links.csv`,
ikke gættet.)

Eksempler på entiteter linket til siden:

| Type | Eksempler (label) |
|---|---|
| person | Bissen, H. V. (1798–1868) · Bournonville, August (1805–1879) · Boye, Maria, f. Birckner (1796–1880) |
| place | Dresden · Haderslev · London · Silkeborg |
| work | Ole Lukøie (Eventyrkomedie) · Minerva (H. V. Bissen, Udg. i Biscuit) |

Bemærk: side V/20 har (som de fleste referencerede sider) endnu
ingen transskriberet tekst i `data/normalized/diary.csv` — den kan
derfor ikke selv groundes af `ner_page_grounding.py` før teksten
findes. Den bruges her udelukkende som illustration af
kandidatlistens bredde pr. side, jf. afsnittet om dæknings-
begrænsning nedenfor.

## Opgavedefinition

Point of departure: **`data/normalized/references.csv`**, ikke sidens
rå tekst. For hver `(vol, page)`, slå det tilhørende sæt af
`entity_id`'er op i `references.csv` — dette er den lukkede
kandidatliste for siden. Slå derefter siden op i
`data/normalized/diary.csv` (tekstfelt `text`, linjetags `NNN-LL`) for
at finde forekomsterne.

1. **For hver entitet i sidens kandidatliste** (fra `references.csv`),
   find den eller de strenge i sidens tekst, der refererer til den
   (person eller sted — samme afgrænsning som ner4andersen §11:
   organisationer/nøgleord er uden for scope for selve NER-opgaven,
   men kan allerede optræde som `entity_type` i `entities.csv` og skal
   i så fald ekskluderes fra grounding-kørslen).
2. **Antagelse om forekomsthyppighed:** hver entitet i sidens
   kandidatliste antages at forekomme **mellem 1 og 5 gange** i
   sidens tekst. Dette er en heuristik til at kalibrere recall-mål
   og sandsynlighedsvurdere kandidat-spans — ikke en hård grænse i
   output, og ikke udledt af `seq`-feltet (som ikke er et
   forekomst-antal, jf. ovenfor).
3. **Mål:** find så mange faktiske tekst-forekomster som muligt for
   entiteterne i sidens kandidatliste (maksimér recall over den
   kendte entitetsliste — ikke over en ukendt/åben entitetsmængde,
   da den allerede er givet af `references.csv`).
4. **1:1-tildeling:** hver forekomst-streng i teksten bør ideelt
   tildeles **præcis én** entitet fra sidens kandidatliste. Hvor en
   streng er reelt tvetydig mellem to entiteter på samme
   kandidatliste (f.eks. et fornavn der matcher flere personer
   nævnt på samme side), skal den bedste kandidat vælges og
   usikkerheden afspejles i confidence-scoren — ikke ved at tildele
   strengen til flere entiteter.
5. **Confidence-score:** hver streng→entitet-grounding får en
   numerisk confidence-score, efter samme mønster som eksisterende
   scorere i repoet (`parse_person_gender.py`,
   `detect_work_language.py`, `add_language_column.py`): en
   scorer/klassifikator producerer en værdi, ingen automatisk
   skrivning til kuraterede filer uden menneskelig gennemgang under
   en tærskel.

## Output-skema

Foreslået udvidelse — et separat forslags-lag ud fra den eksisterende
`references.csv`-række, samme separations-princip som
`wikidata_lookup.py`, der **aldrig** selv skriver til den kuraterede
fil. Hver output-række **udvider** en given `references.csv`-række
med span-oplysninger, den skriver ikke en ny entitet-forbindelse:

```
ref_page_id,vol,page,entity_id,entity_label,mention_text,mention_start,mention_end,confidence,method
Pag100000,III,64,Reg001445,"Gesammelte Werke (1847-72)","Gesammelte Werke",412,428,0.87,ner_grounding_v1
```

| Felt | Betydning |
|---|---|
| `ref_page_id` | Fremmednøgle til kildens `page_id` i `data/normalized/references.csv` (bemærk: løbenummer, ikke side-nøgle) |
| `vol`/`page` | Side-nøglen, matchet mod `diary.csv` |
| `entity_id`/`entity_label` | Kopieret fra den `references.csv`-række, der groundes — **ikke** genfundet af scoreren |
| `mention_text` | Den lokaliserede streng, som den forekommer i `diary.csv.text` |
| `mention_start`/`mention_end` | Tegnposition i sidens `text`-felt (linjetag `NNN-LL` medregnes som en del af teksten, jf. eksisterende OCR-linjetagging) |
| `confidence` | `[0.0, 1.0]`, samme skala som `person_gender.csv` |
| `method` | Scorer-/model-identifikator, til reproducerbarhed (jf. ner4andersen §9's krav om reproducerbare evalueringsrapporter) |

## Kuraterings-tærskel

Følg samme mønster som `add_language_column.py`: rækker under en
tærskel (foreslået `NER_MIN_CONF`, kalibreres senere) flages til
manuel gennemgang. Da `entity_id`/`entity_label` allerede er
kuraterede facts fra `references.csv`, skriver denne opgave **ikke**
tilbage til `references.csv` selv — outputtet er et rent
tilføjelses-lag (span-annotationer), adskilt fra kildetabellen, jf.
den generelle regel i `CLAUDE.md` om faktakontrol og selvkritik: en
confidence-score erstatter aldrig verifikation.

## Forhold til ner4andersen

| ner4andersen (fuldt register, flertrins) | hca-open-repo (denne opgave) |
|---|---|
| Kilder: redaktionelle noter + trykte indekser | Kilde/facit: `data/normalized/references.csv` (kendt side↔entitet-liste) |
| Konsolideret kandidatrecord med `sources[]` | Span-annotationsrække pr. kendt side-entitet-link |
| Åben entitetsopdagelse + ekstern forsoning (Wikidata/GND/VIAF/GeoNames) | Ingen entitetsopdagelse — `entity_id` er allerede givet; opgaven er grounding, ikke forsoning |
| Menneskelig kuratering via OpenRefine + TEI `@ref` | Menneskelig kuratering af span-annotationer før evt. videre brug |
| Entitetstyper: person, place | Samme — person, place (afledt af `entity_type` i `entities.csv` for de linkede entiteter) |

Denne opgave er smallere end ner4andersens Stage 0.5–1: der er ingen
harvest- eller konsolideringsfase, fordi entitetslisten pr. side
allerede er kurateret i `references.csv`. Opgaven svarer nærmest til
den forsonings-/valideringslogik, der i ner4andersen anvendes på
allerede foreslåede kandidater (§7) — men her er kandidatens
`entity_id` fast, og det eneste usikre er placeringen i teksten.

## Implementering (regelbaseret grundlinje)

`scripts/parsers/ner_page_grounding.py` implementerer ovenstående som
en regelbaseret grundlinje (samme stil som `parse_person_gender.py`):
efternavn/fornavn-mønstre for personer, mærkat-match for steder,
grådig ikke-overlappende span-tildeling pr. side, loft på 5 fund pr.
entitet. Output: `data/normalized/ner_page_grounding.csv` (alle
forslagsrækker) og `data/normalized/ner_page_grounding_review.csv`
(rækker under `--min-conf`, default 0,6).

**Dækningsbegrænsning:** `data/normalized/diary.csv` indeholder pt.
kun transskriberet tekst for 751 af de 4.549 sider, der optræder i
`references.csv` — de resterende ~47.500 facit-rækker kan ikke
groundes endnu og springes eksplicit over (rapporteret særskilt i
scriptets opsummering, ikke som `no_match`, da fravær af kildetekst
er en anden situation end et forgæves søgeforsøg).

Ved seneste kørsel på de 751 tilgængelige sider: 11.581 groundede
facit-rækker, heraf 5.145 `no_match` (44 %), 3.912 `surname_only`,
491 `full_name_proximity` (højeste sikkerhed, 0,90), 483
`given_name_only` (laveste sikkerhed, 0,30), og 1.550 sted-match. Den
høje `no_match`-rate afspejler dels OCR-støj, dels at mange
registrerede personer omtales i teksten via titel/pronomen/
kaldenavn frem for efternavn — grundlinjen fanger kun bogstavelige
efternavns-/fornavns-forekomster og er bevidst konservativ frem for
at gætte.
