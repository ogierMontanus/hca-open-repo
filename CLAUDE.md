# Claude Code — Projektregler for hca-open-repo

## Faktakontrol og selvkritik

**Krav:** Efterprøv altid faktuelle oplysninger hentet fra det semantiske web
(Wikidata, DBpedia, VIAF, osv.) via live opslag inden output. Udfør selvkritik
på egne resultater, før de skrives til en fil eller præsenteres for brugeren.

**Baggrund:** I en tidlig session producerede modellen 6 forkerte Wikidata Q-numre
ud af 8 forsøg (fejlrate 75 %) ved ren hukommelsesbaseret gæt. Kun Q5686
(Charles Dickens) og Q84 (London) var korrekte.

### Procedure for Wikidata-opslag

1. Brug `WebSearch` med domænefilter `wikidata.org` for hvert enkelt entitet.
2. Læs det faktiske URL fra søgeresultatet — det indeholder det korrekte Q-nummer.
3. Verificer at entitetsnavnet i URL-titlen matcher det forventede.
4. Erstat aldrig et bekræftet Q-nummer med et ubekræftet hukommelsesbaseret bud.

### Kendte korrekte Q-numre (verificeret)

| Entitet | Q-nummer | Verificeret |
|---------|----------|-------------|
| Charles Dickens | Q5686 | ✓ søgning |
| London | Q84 | ✓ søgning |
| Bleak House (roman, 1853) | Q883305 | ✓ søgning |
| A Christmas Carol (1843) | Q62879 | ✓ søgning |
| Nicholas Nickleby (roman) | Q847642 | ✓ søgning |
| Little Dorrit (roman) | Q565638 | ✓ søgning |
| Odense (by, Danmark) | Q25331 | ✓ søgning |
| Gad's Hill Place (Dickens' hjem) | Q5516441 | ✓ bruger |

### Kendte forkerte Q-numre (må ikke genbruges)

| Entitet | Forkert Q | Årsag |
|---------|-----------|-------|
| Bleak House | Q219420 | Ukendt entitet |
| A Christmas Carol | Q200773 | Ukendt entitet |
| Nicholas Nickleby | Q527099 | Ukendt entitet |
| Little Dorrit | Q327788 | Ukendt entitet |
| Odense | Q3650 | Ukendt entitet |
| Gad's Hill Place | Q5517152 | Forkert sted |

---

## Arbejdsbranch

Udviklingsarbejde sker på branchen `claude/youthful-carson-XIZ5I`.
Push aldrig direkte til `main` uden eksplicit godkendelse.

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
efternavn), og på den fremtidige "Kunstner"-facet på `billedkunst.html`
samt på `bibliotek.html`s "Forfatter"-facet når den ankommer.
