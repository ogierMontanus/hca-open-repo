# Håndovering — UI declutter (branch `claude/ui-declutter-fixes`)

Status ved afslutning: 2 commits, begge pushet, working tree ren, 19/19
tests grønne. Branchet fra `main` (commit `2b8fa68`), **uafhængigt** af
pipeline-separationsarbejdet på `claude/hca-preprocessing-separation-iobj59`
— ingen data-/pipeline-filer rørt her, og omvendt.

```
git fetch origin
git checkout claude/ui-declutter-fixes
python -m pytest tests/ -q   # 19 passed
```

## Baggrund

Opgaven startede som en klik-igennem af hele mockup'en (Playwright, ikke
kun kodelæsning) for at finde gentagelser og rod. Reviewet fandt en lang
liste — se "Ting der IKKE er lavet endnu" nedenfor for den fulde,
uafkortede liste. Denne branch implementerer kun den første, mest
velbegrundede delmængde: fire konkrete UI-fejl plus én filsletning, alle
verificeret ved rigtig navigation og genopbygget output, ikke kun
kodelæsning.

**Den vigtigste arbejdsmetode-lektie fra denne branch:** det første udkast
til reviewet klikkede sig frem via gættede URL'er (`person.html?reg=…`)
snarere end ved at klikke på rigtige links. Det viste sig at være en
**død, ubrugt legacy-side** — intet i det levende site linker til den.
Al efterfølgende verifikation i denne branch skete derfor via
Playwright-klik fra `index.html` og fremad, aldrig ved at skrive en URL i
adresselinjen, og ved at genopbygge og inspicere det faktiske output
(HTML/JS), ikke kun ved at læse kildekoden.

## Commit 1 — `91b35a1`: fire bekræftede fejl

**1. Dublerede kolonner i dagbogsreference-tabellen** (`mockup/js/diary-wire.js`).
`headingFor()` falder allerede tilbage til bind/side-strengen når en side
ikke har en dato — sandt for 83 % af siderne (kun bind VI–VII er daterede
i dag) — så "Dato / reference" og "Bind, side" var identisk tekst på de
fleste rækker. Slået sammen til én kolonne; bind/side vises kun som
underlinje når den faktisk siger noget datoen ikke gør, samme mønster
`cardList()` allerede brugte.

**2. Selv-chip i egen referencetabel** (samme fil). `chipsFor(pag)` lister
alle entiteter på en dagbogsside, inklusive den entitet hvis egen
referencetabel bliver vist — så en persons eget navn optrådte i deres
egne rækker, bekræftet på ~20 % af rækkerne i det oprindelige review,
og optog altid en af kun tre synlige chip-pladser. Filtreret via en ny
`chipsForOther(pag)`-wrapper, scopet til `refs()` (den generelle
dagbogsgennemsyning i `list()` viser fortsat alle — der er intet "selv"
der).

**3. Gammelt projektnavn** ("H.C. Andersen(s) Dagbogsregister") erstattet
med "HCA Open Repository" på `works.html`/`works_en.html` (nås fra
forsidens "Hvad"-kort) og `cart.html` (nås fra kurv-badge'n i headeren på
enhver side) — begge viste det aktuelle header-logo og det forældede navn
i samme viewport. Rettet også i `build_diary_pages.py`s side-skabelon, så
alle 4.544 genererede dagbogssider bærer det korrekte navn (titel,
header-logo, footer-attribution).

**4. Dødt "Hvornår"-link** (`index.html`/`index_en.html`), fundet
undervejs ved rigtig navigation: pegede på `href="#"`. Peget nu på
`diaries.html?layout=timeline` / `diaries_en.html?layout=timeline`, med
en lille deep-link-bootstrap tilføjet til begge dagbogssider, der læser
`?layout=` ved indlæsning og klikker den matchende
layout-switcher-knap — genbruger dens eksisterende pane-skift-logik
frem for at duplikere den. End-to-end-verificeret: lander på
Tidslinje/Timeline-fanen med både fanen og navigations-rebet markeret
aktivt, og med 1.446 rigtige begivenheder rendered når
`build_timeline_index.py`s data er til stede.

**Én planlagt fix blev droppet efter verifikation:** `person.html`s
"Registerdata"-sidebar-kort duplikerer sin hero, men rigtig navigation
når aldrig `person.html` — se næste afsnit.

## Commit 2 — `7fbdf8c`: sletning af `mockup/person.html`

Bekræftet død ved klik-igennem: intet i det levende site linker til den.
`entity-refs.js`s `personHref()` peger altid på `persons.html?reg=…`,
aldrig `person.html?reg=…`; `persons.html` overtog både liste- og
detaljevisning (`?reg=`), og havde allerede siden's eneste reelle
forskel (Autoritetslinks/Biografiske opslag-sidebaren) implementeret
uafhængigt. Brugeren godkendte sletningen eksplicit ("I will restore
from git history if need be").

Derudover rettet **hver** reference i repoet der beskrev filen som
levende, så intet peger en fremtidig læser eller build mod en side der
ikke længere findes:

- `tests/test_no_stale_person_refs.py` — fjernet den nu-overflødige
  skip-undtagelse; testen bevarer sit formål, skærpet: enhver
  `href`/streng-literal der nævner `person.html` er nu nødvendigvis et
  dødt link, ikke bare et forældet-men-virkende ét.
- `scripts/build_mockup/build_persons_extra.py`,
  `build_cooccurrence.py` — to af de rettede kommentarer skrives
  ordret ind i genererede artefakter (`persons-extra.js`,
  `cooccurrence.js`); efterladt urettet ville hver build fortsat
  udsende en falsk påstand om det levende sites egen mekanik. Begge
  regenereret og inspiceret direkte for at bekræfte rettelsen slår
  igennem.
- `scripts/build_mockup/README.md` — tre indholdsmæssige fejl rettet,
  ikke kun filnavnet: fallback-beskrivelsen ("hand-curated dicts i
  `mockup/{work,person,place}.html`" — `persons.html` har ingen sådan
  dict), `ALL_WORKS`/`ALL_PERSONS`/`ALL_PLACES`-forklaringen (kun
  `work.html` og `place.html` har det mønster), og data-flow-diagrammet
  (tegnet om og talt tegn-for-tegn så boksen stadig flugter efter
  rettelsen — et naivt filnavns-bytte havde efterladt den én kolonne
  skæv).
- `.github/workflows/build-mockup.yml`, `mockup/js/entity-refs.js`,
  `mockup/persons_en.html` — kommentarer der navngav `person.html` som
  forbruger eller søskende, rettet til `persons.html`.
- 7 dokumenter under `docs/` — opdateret hvor de beskrev siden som
  aktuel, eller foreslog at koble en fremtidig funktion til den
  (`correspondence-integration.md`s roadmap-punkt peger nu på
  `persons.html` i stedet). **Bevidst urørt:** to træf i
  `correspondence-integration.md` og ét i `docs/data-model/README.md`
  der navngiver den **eksterne** `andersen.sdu.dk/brevbase/person.html`
  — et andet websteds URL-mønster, ikke vores.

## Verifikation udført

- 19/19 tests grønne efter begge commits.
- Playwright-smoke-test over 14 sider (desktop, alle fire registre,
  begge sprog, én genereret dagbogsside, søgning, kurv) — nul
  konsol-/side-fejl, både før og efter sletningen.
- Kolonnesammenlægning og selv-chip-filter bekræftet direkte mod
  rigtigt renderet output (Collin, Edvard, `Reg0048570`), ikke kun
  kodelæsning.
- `GET /person.html` → 404 bekræftet direkte; `GET
  /persons.html?reg=…` → 200 uændret.
- Repo-bred grep efter `\bperson\.html\b` efter commit 2 viser intet
  tilbage der beskriver filen som levende (bortset fra de bevidst
  urørte eksterne Brevbase-referencer og denne håndoverings egen
  historik-tekst).
- En util­sigtet side-effekt blev fanget og reverteret undervejs:
  `python scripts/build_all.py` (kørt for smoke-test) regenererede også
  fire `data/normalized*`-filer med CRLF-/lingua-konfidens-støj — reverteret
  før commit, så branchen holdes strengt UI-scoped.

## Ting der IKKE er lavet endnu (fra det oprindelige review)

Disse blev identificeret i det første klik-igennem-review, men er
bevidst ikke rørt i denne branch — enten fordi de er større,
designkrævende ændringer, eller fordi de ligger uden for "fjern
gentagelser og rod":

1. **Søgefeltet virker ikke.** Både landing-søgefeltet
   (`onsubmit="return false"`) og header-søgefeltet på indersider gør
   intet ved Enter. Typeahead'en (klik på et forslag) virker fint og er
   bygget over hele `SEARCH_INDEX` (16.444 poster) — men der er ingen
   søgeresultat-side bag et almindeligt tekst-Enter. `search.html` er i
   dag 190 linjer hardcoded markup for netop forespørgslen "Rom".
2. **Tre overlappende facetter på samme taksonomi** på `search.html`:
   *Kildetype* (Stedregister, Dagbogsider, …), *Registertype (H1)*
   (PERSON-REGISTER, STED-REGISTER, VÆRK-REGISTER), og *Kategori
   (H2/H3)* samtidig — "Stedregister" og "STED-REGISTER" er samme filter
   under to stavemåder.
3. **Interne skemanavne i brugerfladen**: `H1 = PERSON-REGISTER — …` på
   `persons.html`/`persons_en.html`/`places.html`/`places_en.html`;
   `Registertype (H1)`/`Kategori (H2/H3)` på begge søgesider; "Ikke
   geokodet — dette sted findes ikke i hcax.dk Rejser-tabellen" på
   `place.html` nævner en intern pipeline-kilde direkte.
4. **To forsider**: `index.html` og `works.html`s "Registeroversigt" er
   reelt to udgaver af samme landingsside/navigation
   (Hvem/Hvad/Hvor/Hvornår findes tre steder: landingskortene,
   `works.html`s egen nav-blok, og den lodrette sticky-rail på
   `persons.html`).
5. **Hardcodede totaler gentaget i ti filer** — `10.228` (18 forekomster
   i 10 filer), `2.508` (21 i 11 filer), `39.361` (14 i 10 filer).
   `persons.html` viser selv `10.228` fire steder, mens JS'en (den
   korrekte entityType-gate) faktisk renderer **10.103** — samme skærm,
   modstridende tal fire gange.
6. **Facet-panel "Vis alle"-overlap-bug**: "Vis alle (68)" renderes
   oven på sidste synlige facet-række, skjuler fx "Hollandsk 55" — på
   begge navneregistre.
7. **Intet kollapser på mobil.** Ved 390 px bredde: `persons.html`
   (listevisning) 1147 px bred; den nu slettede `person.html?reg=…`
   målte 1475 px, men det tal er ikke genmålt på den faktiske
   `persons.html?reg=…`-detaljevisning. Hver side scroller sidelæns,
   inklusive forsiden.
8. **Ingen paginering nogen steder** — `persons.html` renderer alle
   10.103 rækker i én 774.219 px høj DOM; `places.html` 121.704 px;
   `bibliotek.html` 116.758 px.
9. **Landingskortenes selvmodsigende navngivning** — *Hvad*-kortet
   lister "Teater & Musik / Malerier & Billedkunst / Bøger & Digte",
   footeren under lister samme tre destinationer under tre andre navne
   ("Billedkunst · Teater & Musik · Bibliotek").

Punkt 5–6 er småfixes i samme stil som denne branch og et naturligt
næste skridt. Punkt 1–2 og 7–8 er reelle funktions-/designopgaver, ikke
oprydning, og bør nok diskuteres separat før implementering.

## Relation til pipeline-branchen

`claude/hca-preprocessing-separation-iobj59` (repo-separation,
`data/`-flytning til `HCA-Diary-data-cleaning`) er en separat linje fra
samme `main`-punkt. De to branches **overlapper på 3 filer**:
`.github/workflows/build-mockup.yml`, `scripts/build_mockup/README.md`,
`scripts/build_mockup/build_persons_extra.py` — pipeline-branchen
omskriver dem substantielt (fjerner ingest-/enrichment-stadier,
tilføjer prepared-data-forklaringer), denne branch retter kun
`person.html`-referencer i dem.

**Testet i en isoleret klon** (`git merge --no-commit --no-ff` fra
`ui-declutter-fixes` mod pipeline-branchen): alle tre filer
auto-merger rent, ingen konfliktmarkører. De kan altså merges i
vilkårlig rækkefølge — men efter et faktisk merge bør
`build_persons_extra.py`s to person.html-relaterede kommentarrettelser
fra denne branch tjekkes mod pipeline-branchens egne ændringer i samme
fil, da et rent auto-merge ikke er det samme som at begge sæt hensigter
stadig giver mening sammen.
