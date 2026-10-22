# Filterlogik — AND/OR mellem aktive filtre

Status: implementeret · 2026-10-21 · gælder `persons`, `places`, `bibliotek`,
`billedkunst`, `teater-musik` (+ `_en`)

Læseren kan kombinere de aktive filtre med **AND** og **OR**. AND er standard
mellem to forskellige filtre, så hvert nyt filter som udgangspunkt indsnævrer
resultatet. Operatoren skiftes direkte i chip-linjen over resultaterne.

## 1. Før ændringen

Filtreringen er ren klient-side (ingen backend; data er `window.*`-globals fra
`mockup/data/*.js`). Reglen var hårdkodet og ens alle steder:

> **OR inden for en facet, AND mellem facetter.**

Den lå to steder: `FacetEngine` (`js/facet-engine.js`, bruges af persons og
places) og `js/category-catalogue.js` (bibliotek, billedkunst, teater-musik).
DOM'en — de afkrydsede checkboxes — var den eneste tilstand; chip-linjen
(`js/active-filters.js`) var en ren visning uden rækkefølge. Der var ingen måde
at få fx «svensk ELLER musiker» på tværs af facetter.

## 2. Hvad er ændret

| Fil | Ændring |
|---|---|
| `mockup/js/filter-logic.js` (**ny**) | DOM-fri modul `HcaFilter`: operator-register, udtryksmodel, evaluering, udskrift med parenteser, og `HcaFilter.shared` der husker valgrækkefølge og operatorer. |
| `mockup/js/facet-engine.js` | Beregner resultat og facet-tal via `HcaFilter` i stedet for egen `passes()`. Lytter efter `hca:filters-op-change`. `state()` har fået `expr`. |
| `mockup/js/category-catalogue.js` | Samme: `readFacetModel()` + `passesFacets()` over `HcaFilter`; facet- og bogstavstal bruger samme logik. |
| `mockup/js/active-filters.js` | Tegner AND/OR-dropdowns mellem chips, grupperer chips pr. facet, viser «Søgelogik»-linjen og en `aria-live`-opdatering; fjerner chips via nøgle. |
| `mockup/css/style.css`, `mobile.css` | `.active-filter-cluster`, `.active-filter-op`, `.active-filters__formula`. Ingen `overflow` på sticky-elementer. |
| 10 HTML-filer | `<script src="js/filter-logic.js">` før `facet-overlay.js`. |
| `tests/js/…`, `tests/test_filter_logic_js.py` | Se afsnit 5. |

## 3. Sådan evalueres AND og OR

**Termer og grupper.** Hver afkrydset facetværdi (og hvert udfyldt årsinterval)
er en *term*. Termer i samme facet danner en *gruppe*, der evalueres som om den
stod i parentes. Operatorerne mellem grupper bruges bagefter.

**Standardoperatorer:** OR mellem to værdier i samme facet (som før), AND mellem
to forskellige facetter. Med kun standardoperatorer er resultatet derfor
**identisk med den gamle regel**.

**Præcedens.** På hvert niveau (inden for en gruppe, derefter mellem grupper)
læses en kæde `a op b op c …` med almindelig boolsk præcedens: **AND binder
stærkere end OR**, lige operatorer læses fra venstre.

| Valg (i den rækkefølge de blev valgt) | Evalueres som |
|---|---|
| Nationalitet: Svensk **AND** Erhvervsgren: Musiker | Svensk ∧ Musiker |
| Svensk **OR** Musiker | Svensk ∨ Musiker |
| Svensk **AND** Musiker **OR** Køn: Mand | (Svensk ∧ Musiker) ∨ Mand |
| Svensk **OR** Musiker **AND** Mand | Svensk ∨ (Musiker ∧ Mand) |
| Nationalitet: Svensk **OR** Norsk **AND** Musiker | (Svensk ∨ Norsk) ∧ Musiker — de to nationaliteter er én gruppe |

**Hvorfor grupper (to niveauer)?** AND-binder-stærkere kan ikke udtrykke
`(Svensk OR Norsk) AND Musiker` i en flad kæde: `Svensk OR Norsk AND Musiker`
ville blive `Svensk OR (Norsk AND Musiker)` og bryde alle eksisterende filtre.
Facet-grupperne findes allerede i panelet og i koden, så de er den naturlige
parentes — de bevarer standardadfærden, og de gør en senere, mere avanceret
gruppering til en udvidelse af samme datastruktur frem for en omskrivning.

**Det viste er det anvendte.** Chip-rækkefølge, dropdowns, «Søgelogik»-linjen
(med eksplicitte parenteser, fx `((Nationalitet: Tysk OR Fransk) AND
Erhvervsgren: Kunstner/Billedkunst) OR Køn: Mandlig`) og selve søgningen læser
**samme objekt** (`HcaFilter.shared.expr()`). Der er ingen anden kopi af
operatorerne.

**Rækkefølge og vedligehold.**
- Nye filtre tilføjes sidst; chips af samme facet holdes sammen (facetter
  ordnes efter første valg).
- En operator gemmes på det *senere* element i et par. Fjernes et filter,
  forsvinder dets operator, og efterfølgeren beholder sin egen. Et filter der
  bliver først, viser ingen operator. Tilføjes et fjernet filter igen, starter
  det på standardoperatoren. «Ryd alle»/«Nulstil» nulstiller alt.
- **Bogstavsbjælken (A–Å)** er et sidebredt prefilter og er altid AND; dens chip
  har ingen dropdown (vises med et fast, ikke-klikbart «AND»).
- Et årsinterval (Omtaleår på places) er én term, ligesom en afkrydset værdi.

**Facet-tal.** Tallet ved en værdi er antallet af poster, hvis værdien var den
eneste valgte i sin facet, med alle andre filtre og operatorer som læseren har
sat dem. Med standardoperatorer er det det samme tal som før («poster der
består alle ANDRE facetter og har værdien»). En værdi med 0 deaktiveres (aldrig
en afkrydset). Under AND kan en værdi derfor være deaktiveret, men blive
tilgængelig, når læseren skifter til OR.

## 4. Sådan skifter brugeren operator

Når to eller flere filtre er valgt, står en lille `AND ▾`/`OR ▾` mellem hvert
par chips i chip-linjen (native `<select>`: tastatur og skærmlæser virker, og
den ligger uden for `.facet-panel`, så iOS-faldgruben i `CLAUDE.md` ikke
berøres). Vælg den anden værdi, så genberegnes resultatet og chips straks.
Chips i samme facet står i en stiplet ramme (= parentes). Ingen separat
«avanceret søgning».

Tilgængelighed: hver dropdown har `aria-label` («Operator mellem … og …»),
fokus bevares ved gentegning, og en usynlig `aria-live`-region melder den
samlede logik.

## 5. Tests

| Fil | Indhold | Kører |
|---|---|---|
| `tests/js/filter-logic.test.js` | 23 enhedstests af den rene logik: sandhedstabeller, præcedens, udtømmende test af 3–4 termer × alle operatorkombinationer mod en referenceevaluator, grupper som parenteser, tilføj/fjern/genindsæt, facet-tal (`force`), udskrift, registrering af en ny operator. | `node --test tests/js/filter-logic.test.js`; via `tests/test_filter_logic_js.py` også i `python -m pytest tests` (og dermed CI) |
| `tests/js/filter-ui.test.js` | 11 browser-tests (Playwright + Chromium) mod fixturesiderne `tests/js/fixtures/*.html`, som indlæser de **rigtige** `facet-engine.js`, `category-catalogue.js`, `active-filters.js`: ét filter, AND som standard, svensk AND musiker, skift til OR i UI, tre filtre med blandede operatorer, samme facet, tilføj/ændr/fjern, årsinterval, facet-tal, nulstil, fokus, begge motorer. | `node --test tests/js/filter-ui.test.js` (springes over uden Playwright; **ikke** i CI) |

Fixtures bruges fordi `mockup/data/*.js` er gitignoreret byggeoutput.

Desuden røgtestet manuelt med rigtige data (`build_persons_extra.py`,
`build_works_extra.py`, `build_places_extra.py`) på alle ti sider (DA + EN):
persons «Tysk» = 507, «Tysk AND Kunstner/Billedkunst» = 110, «Tysk OR
Kunstner/Billedkunst» = 978 — begge tal genberegnet uafhængigt direkte fra
`persons-extra.js`. En bevidst sabotage af OR i registret fik 17 af 34 tests til
at fejle.

## 6. Begrænsninger og udestående

- Operatorer og filtervalg **gemmes ikke** og kan ikke deles som URL (det kunne
  filtervalg heller ikke før).
- Kun AND og OR. NOT, vilkårlig nesting og læser-styret parentes er ikke med;
  de kan tilføjes via `HcaFilter.registerOp` / et ekstra gruppeniveau.
- Grupperingen følger facet-strukturen og kan ikke ændres: en læser kan ikke
  oprette `(Svensk OR Musiker) AND Mand` på tværs af tre facetter. Hver
  forbindelse er dog uafhængigt valgbar, og kæden evalueres med AND-før-OR.
- En værdi der giver 0 resultater under de nuværende operatorer er deaktiveret;
  læseren skal først skifte til OR for at vælge den.
- Playwright-testene kører ikke i CI (workflowet installerer hverken Node-pakker
  eller browser); køres lokalt.
- Bogstavsfilteret og de inerte «Omtaleår»-felter på værksiderne er uændrede;
  `diaries*.html` har chip-linjen slået fra (`data-active-filters="off"`).
- Den danske `title` på deaktiverede værdier i `facet-engine.js` er stadig
  hårdkodet dansk (uden for scope).
