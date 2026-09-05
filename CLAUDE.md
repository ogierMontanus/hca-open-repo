# Claude Code — Projektregler for hca-open-repo

## Faktakontrol — Wikidata/DBpedia/VIAF

**Krav:** Efterprøv altid faktuelle oplysninger hentet fra det semantiske web
(Wikidata, DBpedia, VIAF, osv.) via live opslag inden output — aldrig fra
hukommelsen. Procedure, verificerede Q-numre og kendte forkerte gæt: se
skill `wikidata-verify` (`.claude/skills/wikidata-verify/SKILL.md`).

---

## Verificering af "fix"-commits

**Krav:** Tag ikke en fix-commits egen commit-besked som bevis for at den
virker — genudled fejlens beskrevne mekanisme mod koden som den er efter
ændringen. Procedure og et konkret eksempel (facet-panel/iOS-fælden): se
skill `verify-fix-commit` (`.claude/skills/verify-fix-commit/SKILL.md`).

---

## Projektnavn

**Officielt projektnavn:** HCA Open Repository

Projektet blev tidligere kendt som "H.C. Andersen Dagbogsregister". Fra 2026 refereres til det som **HCA Open Repository** på engelsk og **HCA Åbent Arkiv** på dansk i formelle dokumenter.

---

## Udelukkede mapper — `mockup/irrelevant/`

**Alt i `mockup/irrelevant/` skal udelades fra al videre behandling.**

Mappen indeholder pensionerede filer, som bevidst ikke er en del af det
levende mockup. De er beholdt i git for at bevare designarbejdet og
begrundelsen, ikke for at blive vedligeholdt.

Konkret betyder det:

- **Byggescripts** (`scripts/build_mockup/*`, `scripts/build_all.py`) og
  alt andet, der globber `mockup/**`, skal springe mappen over.
- **Lint og tests** i `tests/` skal ekskludere den — se `_SKIP_DIRS` i
  `tests/test_no_stale_person_refs.py`, som allerede gør det.
- **Linkcheck og audits**: filerne er med vilje aflinket. En ikke-refereret
  fil her er den forventede tilstand, ikke et fund.
- **Design- og dokumentationsgennemgange**: propagér ikke CSS-, markup-,
  label- eller rebranding-ændringer ind i mappen. Den er frosset.
- **Fremtidige AI-assisterede redigeringer**: behandl mappen som skrivebeskyttet
  historik. Hvis en fil bliver relevant igen, så flyt den ud først og
  genkobl den bevidst — rediger den ikke på plads.

Se `mockup/irrelevant/README.md` for indholdet og begrundelsen pr. fil.

---

## Repo-opdeling — bygning her, rensning i det andet repo

**Dette repo bygger og publicerer. Det forbereder ikke sine egne data.**

Rensning, forbehandling, segmentering, normalisering og berigelse hører
hjemme i **HCA-Diary-data-cleaning**, som udgiver de forberedte filer
dette build læser:

```
råkilder → HCA-Diary-data-cleaning → data/normalized/ + data/parsed/
                                     + data/curated/ → dette repo → mockup/ + web/
```

**Følg denne regel i kode:** tilføj ikke et script her, der *udleder en
kendsgerning om data* — en koordinat, et sprog, en nationalitet, en
segmentering, en kategori, et link. Det hører til i renserepoet, også
selvom det ville være bekvemt at lægge det i `scripts/build_mockup/`.
Scripts her må kun forme allerede forberedte data til et
præsentationsartefakt (HTML-side, JS-kortobjekt, denormaliseret JSON).

Filerne under `data/` er **modtagne** data. Ret dem i renserepoet og
genudgiv (`python scripts/publish.py --into ../hca-open-repo`) — aldrig
på plads her. Fuld beskrivelse: `docs/pipeline/README.md`.

Bygget er **kun stdlib**. Tilføj ikke `openpyxl`, `lingua` eller andre
afhængigheder her; de fulgte med de stadier, der flyttede ud.

---

## Arbejdsbranch

Udviklingsarbejde sker på branchen `claude/youthful-carson-XIZ5I`.
Push aldrig direkte til `main` uden eksplicit godkendelse.

---

## Eksterne links — nyt faneblad, diskret placering

**Brugerpræference (2026-08-12):** Links der fører væk fra webstedet
(Det Kgl. Bibliotek, Wikidata, VIAF, GeoNames …) åbnes i et **nyt
faneblad** — `target="_blank"` + `rel="noopener noreferrer"` — så
brugerens søgning eller filtrerede liste ikke går tabt, og så det
signaleres at man forlader registret. Interne links åbner altid i samme
faneblad.

Eksterne links skal være **diskrete**: højt på siden hvor læseren leder
efter kilden, men små og dæmpede, uden ramme eller knap. De er proveniens,
ikke handlingsopfordringer.

Fuld politik med markup, tilgængelighedskrav (↗ + `.sr-only`-varsling) og
faste linktekster: `docs/external-links.md`. Følg den også for
Wikidata-badges.

---

## Kortvisning — kortfliser via CARTO

**Brugerpræference (2026-06-03):** Alle Leaflet-visninger (i `mockup/`,
`web/` og senere implementeringer) bruger **CARTO Voyager** som
flise-leverandør:

```
https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png
```

med `subdomains: 'abcd'`, `maxZoom: 19` og attribution

```
&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>
contributors &copy; <a href="https://carto.com/attributions">CARTO</a>
```

**Begrundelse.** OpenStreetMap's frivilligt-drevne fliseservere
(`tile.openstreetmap.org`) kræver en `Referer`-header per deres
tile-usage-policy og blokerer requests uden en — også fra `file://`
loads — med en 403r "Access blocked"-overlay (se `osm.wiki/Blocked`).
CARTO's CDN leverer de samme OSM-data uden Referer-krav og fungerer
derfor under både `file://` og senere HTTP-hosting.

**Følg denne præference i kode:** brug ikke `tile.openstreetmap.org`
direkte. Hvis en anden flise-leverandør overvejes (Stadia, MapTiler,
Mapbox), bekræft med brugeren først.

---

## Brugerens lokale miljø — Windows / PowerShell

**Brugerpræference (2026-06-04):** Brugeren kører lokalt fra
PowerShell på Windows, hvor Python-launcheren hedder `python` (ikke
`python3`). Når dokumentation eller `README`-filer i dette repo viser
kommandoer beregnet til at blive kørt lokalt:

- Brug `python scripts/.../foo.py` i eksempler, ikke `python3 …`.
- Undgå bash-konstruktioner (`for s in …; do … done`,
  `$VAR`-interpolation, `\`-linjefortsættelse) i lokale eksempler —
  de fejler i PowerShell med fejl som `Missing opening '(' after
  keyword 'for'`. Giv enten en eksplicit liste af kommandoer eller
  en PowerShell-loop (`foreach ($s in 'a','b') { python … }`).
- CI-eksempler (GitHub Actions YAML) må fortsat bruge `python` (ikke
  `python3`) for konsistens med Linux-runneren, hvor `python` peger
  på Python 3.

---

## Alfabetisering — sortér personer efter efternavn

**Brugerpræference (2026-06-09):** Hvor som helst en liste af personer
sorteres alfabetisk (filterfacetter, A–Å-bjælker, droplists, autocomplete-
forslag), skal **efternavnet** være den primære alfabetiske nøgle.

Praktiske regler i kode:

- **Register-etiketter** (`entities.label` for `entity_type='person'`)
  har allerede formen `"Efternavn, Fornavn(e) (årstal)"` for 91 % af
  posterne, så `collator.compare(a.label, b.label)` med dansk collation
  giver automatisk efternavn-først. Ingen ekstra logik nødvendig.
- **WORKS_EXTRA.author** har den løsere form `"Fornavn Efternavn"` /
  `"X. Efternavn"` (V. Pedersen, Lorenz Frølich). Brug en hjælper —
  fx `surnameKey()` i `mockup/js/category-catalogue.js` — der returnerer
  delen før første komma, eller det sidste hvidrum-separerede token,
  før der sorteres.
- **Når en facet sorterer efter optællingstal først** (komponist/forfatter-
  facet på teater-musik, persons co-occurrence), brug efternavnet som
  sekundær nøgle ved uafgjort, ikke hele etiketten.
- **Intl.Collator('da')** bruges som collator overalt — den håndterer
  æ/ø/å og folder `Aa`→`Å` korrekt.

Forskellen er især synlig på `teater-musik.html`s "Komponist /
Forfatter"-facet (~70 navne med flere værker; sekundærsortering på
efternavn), på `bibliotek.html`s "Forfatter"-facet, og på
`billedkunst.html`s "Kunstner"-facet (355 kunstnere; se
`docs/data-model/billedkunst-artist-extraction.md` for hvordan
kunstnernavnet udledes af værktitlens parentes, når `person_derived`
mangler).

---

## Claude Design — komponent-dropzone og pipeline (2026-07-01)

UI-komponenter i `design/` synkroniseres med `mockup/css/style.css` via
Claude Design (projekt "HCA Dagbogsregister") og
`scripts/design_sync/apply_component.py`. Fuld arbejdsgang, projekt-ID,
komponentliste og kendte quirks: se skill `design-sync`
(`.claude/skills/design-sync/SKILL.md`).

---

## CSS-faldgrube: `position: fixed` fanget af `position: sticky` + `overflow` på iOS Safari

**Bekræftet 2026-08-29** (rapporteret direkte fra en iPad): en
`position: fixed`-efterkommer af et `position: sticky`-element bliver på
iOS Safari klippet til det sticky-elementets egne grænser i stedet for
viewport'et, **hvis** det sticky-element også har en `overflow`-værdi
forskellig fra `visible` (selv `hidden`/`auto`). Ramte
`.facet-panel--overlay-open` (den udvidede facet-overlay i
`mockup/js/facet-overlay.js` — se dens egen kommentar i
`mockup/css/style.css`), da `overflow: hidden` blev tilføjet for at skjule
panelets egen scrollbar bag overlayet.

**Følg denne regel i kode:** tilføj aldrig en `overflow`-værdi (heller
ikke `hidden`) til `.facet-panel` eller andre `position: sticky`-elementer,
der har en `position: fixed`-efterkommer et andet sted i koden. Skjul en
scrollbar i stedet via `scrollbar-width: none` +
`::-webkit-scrollbar { display: none }` — det ændrer ikke
`overflow`-værdien og udløser derfor ikke fælden.
