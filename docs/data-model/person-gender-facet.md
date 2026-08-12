# Automatisk kønsfacettering af personregistret

`scripts/parsers/parse_person_gender.py` gennemgår de 10.228 poster i
PERSON-REGISTRET og foreslår **Mandlig**, **Kvindelig** eller **Endnu
ubestemt** for hver, med en confidence score og en eksplicit liste over de
indikatorer, resultatet bygger på.

Resultatet eksponeres som en **facet** på `persons.html` og skriver ikke
til registrets øvrige datafelter. Kategoriseringen er en afledt,
evaluerbar arbejdshypotese om posten — ikke en påstand om den enkelte
persons identitet.

**"Endnu ubestemt" er en gyldig kategori, ikke en fejl.** Den markerer, at
grundlaget ikke rækker til en pålidelig kategorisering, og er dermed
prioriteringssignalet til den menneskelige redaktør.

## Resultat efter første kørsel

| Kategori | Antal | Andel |
|---|---:|---:|
| Mandlig | 3.714 | 36,3 % |
| Kvindelig | 3.287 | 32,1 % |
| Endnu ubestemt | 3.227 | 31,6 % |

Dækning ved forskellige cutoffs: 68,4 % af registret afgøres ved ≥ 0,70,
44,4 % ved ≥ 0,90.

## Metode: navneviden udledes af registret, ikke af en indbygget liste

Opgaven forbyder en simpel universel navneliste og kræver kontekstafhængig
vurdering af fornavne. Parseren har derfor **ingen indbygget navneliste**.
Den kører i tre gennemløb:

1. **Strukturelle markører uden navneviden** — titler i label
   (Grevinde/Greve, Komtesse, Dronning …), `Datter af …`/`Søn af …` som
   beskrivelsens indledning, `f. <Efternavn>` (pigenavn) i label,
   `-inde`-professioner, civilstand, slægtsord og pronominer. Dette gav
   **4.388 poster med høj sikkerhed**.
2. **Navnestatistik udledes af de 4.388 sikre poster**, bucket'et efter
   personens egen nationalitet (fra `person_ethnic_descriptors.csv`, kun
   `leading`+`subject`) plus en generel bucket. Et fornavn bliver først
   brugbart ved tilstrækkelig dækning (≥3 i en nationalitetsbucket, ≥5 i
   den generelle) og ≥85 % skævhed. **189 (navn, kontekst)-par** opfylder
   tærsklerne. Statistikken skrives til
   `data/normalized/given_name_gender_stats.csv`, så den kan inspiceres.
3. **Kombineret scoring** af alle indikatorer.

Fordelen frem for en hardkodet liste: statistikken er per konstruktion
tilpasset dette registers navneskik og periode (dansk 1800-tal med tysk,
fransk og svensk islæt), den er inspicerbar, og den genberegnes automatisk,
når markørvægtene justeres.

Et fornavn kan **aldrig alene** nå høj sikkerhed (`NAME_MAX_WEIGHT = 1,7`
→ confidence 0,85). Det kræver mindst én uafhængig indikator mere.

### Krydskulturelle navne

`data/curated/given_name_gender_overrides.csv` overstyrer statistikken pr.
(navn, nationalitet). Opgavens eksempel — spansk `Juan María` — håndteres
ved at **neutralisere** María i spansk/italiensk kontekst (vægt 0) frem for
at vende den til mandlig: María som *eneste* fornavn er stadig oftest
kvindeligt i spansk, og det er kombinationen `Juan`+`María`, der er
mandlig. Den fanges af det ledende fornavn, som bærer signalet.

## Scoringsmodel

```
score      = Σ(kvindelige vægte) − Σ(mandlige vægte)
konflikt   = min(Σ kvindelige, Σ mandlige)
confidence = logistisk(|score|)
```

Ved reel modstrid (konflikt ≥ 1,5) **dæmpes confidence eksplicit**
(faktor 0,45), så posten kan ende som "Endnu ubestemt", selv om en enkelt
indikator isoleret set var stærk. Confidence skal ikke skjule usikkerhed.

Tærskler (eksperimentelle): ≥ 0,90 høj sikkerhed · 0,70–0,89 sandsynlig ·
< 0,70 Endnu ubestemt.

Vægtene ligger i `data/curated/gender_markers_da.csv` og kan justeres uden
kodeændring — det er kravet i opgavens punkt 11.

## Fire fejlkilder fundet ved intern revision — og rettet

Alle fire blev fundet ved at inspicere faktiske resultater, ikke ved at
formode dem. De er værd at kende, fordi de er registrets egne mønstre:

**1. Titler i fornavnspositionen.** 264 poster har ingen fornavn, men en
titel: `Ahlefeldt, Frøken`, `Aldridge, Mrs.`, `Ahlefeldt, Greve`. Uden
særbehandling blev "Frøken" talt som et *fornavn* — kategorien blev
tilfældigvis rigtig, men af den forkerte grund, indikatorteksten løj, og
navnestatistikken fik titelord som selvstændige "navne". Nu flyttes de til
titel-segmenterne. Titel-indikatorer steg fra 1.138 til 1.450.

**2. "Vor Frue Kirke" er et sted, ikke en kvinde.** 12 poster — alle
mandlige sognepræster — fik en kvindelig `Fru`-markør fra deres
embedsbeskrivelse. Frasen fjernes nu før markørsøgningen.

**3. Referent-problemet: markøren beskriver en pårørende.** Den alvorligste
fejlkilde. Mønstret i registret er `Broder til Fru Therese Henriques` —
*relationsordet* beskriver posten, mens `Fru X` navngiver **slægtningen**.
Uden skelnen blev korrekt bestemte mænd trukket i konflikt af et "Fru", der
slet ikke handlede om dem. To regler følger:

- Slægtsord tæller kun som `X til …` eller som beskrivelsens indledning —
  og ikke efter et ejestedord (`hans Moder` = tredjepart).
- Titler tæller kun **prædikativt**, altså når de ikke står foran et
  egennavn. `Frue i Aarhus, hos hvem …` beskriver posten; `Fru Therese
  Henriques` gør ikke.

**4. Samme referent-problem i `-inde`.** `Fader til Fyrstinde Caroline` og
`Søn af Ærkehertuginde Sophie` handler begge om en **mand**. `-inde`-ord
umiddelbart efterfulgt af et egennavn tæller derfor ikke. Bemærk `\s+`
frem for `\s*` i den regel: efter `Forfatterinde. Datter af …` står der
punktum før det store bogstav, og dér er `-inde`-ordet netop posten selv.

Samlet effekt af rettelse 3 og 4: modstridende poster faldt fra **22 til
5**, og grundlaget for navnestatistikken voksede fra 3.869 til 4.388.

Én kendt, ikke-rettet rest: `hans Moder var Søster til William Howitt` —
ejestedords-værnet ser kun umiddelbart før *det matchede* ord, så `Søster
til` slipper igennem, selv om det er moderen, der er søster. Posten ender
som "Endnu ubestemt" frem for forkert kategoriseret, hvilket er den rigtige
fejlretning at fejle i.

## Andre observationer fra korpuset

- **Pronominer er næsten fraværende.** Kun 5 poster indeholder
  `hun`/`hendes` og 93 `han`/`hans` — mod 1.404 med `f.` (pigenavn) og
  2.052 med `Datter af`/`Søn af`. Pronominer bidrager til blot 19 afgjorte
  poster. Opgaven nævner dem som en stærk feature; i *dette* register er de
  marginale.
- **Dækningen varierer stærkt med nationalitet**: østrigsk 90 %, tysk
  78 %, men italiensk 18 % og hollandsk 28 %. Årsagen er, at de sikre
  poster (og dermed navnestatistikken) er domineret af dansk/tysk
  navneskik. Det er den mest oplagte kilde til forbedring i næste runde.

## Menneskelig kontrol

`data/normalized/person_gender_review.csv` er en prioriteret kø. Sortering:
modstridende evidens først, derefter poster med indikatorer men for lav
score, derefter poster i 0,70–0,89-båndet, hvor en lille vægtjustering
flytter kategorien. To tomme kolonner — `menneskelig_vurdering` og
`kommentar` — udfyldes i hånden og bliver evalueringsgrundlaget for
opgavens punkt 12.

Bemærk, at en høj confidence score ikke i sig selv er bevis på
korrekthed. Ved stikprøve af poster ≥ 0,95 blev fejlkilde 1 ovenfor fundet
netop dér — i den gruppe, tallene så bedst ud.

## Kørsel

```
python scripts/parsers/parse_person_gender.py
python scripts/build_mockup/build_persons_extra.py
```

Første kommando skriver `person_gender.csv`, review-køen og
navnestatistikken og printer den interne revision (opgavens punkt 11).
Anden kommando lægger `gender` og `genderConf` på `PERSONS_EXTRA`, hvorfra
`persons.html`s Køn-facet henter værdierne via FacetEngine.

Kører parseren ikke, står `gender` som `null`, og facetten viser blot ingen
rækker — resten af siden er upåvirket.
