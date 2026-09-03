# Plan: saml personefterbehandlingen ét sted

**Mål:** al udledning af personattributter til filterboksene sker i én
kæde — i `datacleaning/diaries_datacleaning` (master2) — og
`hca-open-repo`s byggetrin gør intet andet end at læse resultatet og
forme det til JS.

Baggrund og filnavne: `person-master-files.md` i samme mappe.
Berigelsens indhold: `person-enrichment.md` i diaries-repoet.

## Problemet: de samme attributter udledes to gange

Køn og erhverv udledes i dag uafhængigt i begge repoer, med hver sin
kodebase, hvert sit termsæt og hver sin tærskel — men de fodrer den
samme filterboks.

| Attribut | hca-open-repo | diaries_datacleaning | Status |
|---|---|---|---|
| Køn | `scripts/parsers/parse_person_gender.py` | `volume12/add_gender.py` | **Dublet** — samme tre kategorier, samme »Endnu ubestemt«, samme strukturelle markører |
| Erhverv/rolle | `scripts/parsers/parse_person_role.py` | `profession_markers.md` + `add_gender.py`s termlister | **Overlap** — begge høster erhvervsord fra beskrivelsesfeltet |
| Nationalitet | `scripts/parsers/parse_person_ethnic_descriptors.py` (stage 1e) | `add_nationality.py` | **Dublet** |
| Herskere | — | `add_ruler.py` | Kun master2 |
| entityType | — | `classify_entity_type.py` | Kun master2 — og den gate mangler i hca-open-repo |

Dubletterne er ikke harmløse. De to kønsscripts kan give forskellige svar
på den samme post, og der findes i dag ingen regel for hvem der vinder.
Værre: `classify_entity_type.py`s gate — *tildel ikke personattributter til
familier, firmaer eller en hund* — findes **kun** i master2. Byggetrinnene i
hca-open-repo har den ikke, så `Collin, Familien` og bankierfirmaet
`Behrens` kan i princippet få et køn tildelt i filterboksen.

En detalje der bør afgøre prioriteringen: `parse_person_gender.py` og
`parse_person_role.py` står **ikke** i `build_all.py`s stageliste. De køres
manuelt. Deres output (`person_gender.csv`, `person_role.csv`) læses
alligevel af stage 4b `build_persons_extra.py`. Filerne er altså committet
data, som pipelinen forbruger, men ikke selv genskaber — de kan være
vilkårligt forældede i forhold til registret, uden at noget siger fra.

## Retningen

```
master1 ──► [diaries_datacleaning: én kæde] ──► master2 ──► [hca-open-repo: kun præsentation]
```

Én regel: **hca-open-repo udleder ikke personattributter.** Byggetrinnene
læser master2-kolonner og mapper dem til JS. Al ny logik om køn, erhverv,
nationalitet, herskere og entitetstype hører hjemme i diaries-repoet.

## Trin

### Trin 0 — forudsætning: kør berigelsen på master1

Berigelseskæden kører i dag på `DimPer.tsv` (8.917 rækker) fra det gamle
regneark, mens master1 har 10.081. Alt andet i planen er meningsløst før
det er rettet, fordi ~1.150 poster ellers slet ikke har facetter.

* Lad `extract_dimper.py` (eller en ny indlæser) tage master1 som kilde.
* Flyt `classify_entity_type.py` **forrest** i kæden, så `is_individual()`
  kan gate de følgende trin, som den er beregnet til.
* Genkør og sammenlign tallene i `gender_review.md` og
  `entity_type_and_evidence.md` mod de nye. Særligt: bliver
  `crossReferenceMalformed` tom, som master1 burde have gjort den?

### Trin 1 — fastlæg kontrakten mellem repoerne

Skriv ned hvilke kolonner hca-open-repo må regne med, og hvad de hedder.
Forslag til det minimale sæt der driver filterboksene:

| Master2-kolonne | Bruges til |
|---|---|
| `25_gender` | Kønsfacet |
| `16_nationality`, `18_nationalityCategory` | Nationalitetsfacet |
| `20_isRuler`, `21_territory`, `22_rulerTitle` | Hersker-/territoriefacet |
| `29_entityType` | **Gate** — kun `individual` får personfacetter |
| (ny) `roleFacet` | Rollefacet, hvis den flyttes hertil |

Kontrakten bør også fastlægge join-nøglen. **Hverken `PerID` eller
`01_entry_id` duer** — begge er positionsbestemte og gennemnummereres ved
enhver ændring, hvilket allerede har kostet fejl i dette projekt. Brug
efternavn plus sidehenvisnings-signatur (`11_references_parsed`);
sidetallene er identiske i enhver transskription af det trykte register.

### Trin 2 — flyt rollefacetten til master2

`parse_person_role.py` har to kilder: (A) opslag i værkregistret via
`nameKey()`, og (B) en høst af erhvervsord fra beskrivelsen. Del B
overlapper direkte `profession_markers.md`s termarbejde og bør flyttes.

Del A er straks vanskeligere, fordi den krydser mod værkregistret, som
ligger i hca-open-repo. To muligheder — vælg bevidst:

* **Flyt hele rollefacetten** til master2, og lad diaries-repoet også få
  værkregistret som input. Renest, men udvider det repos ansvar.
* **Del den:** erhvervsord fra beskrivelsen udledes i master2 som
  `roleFacet`; værkbaserede roller (»Kunstner/Billedkunst« osv.) beregnes
  fortsat i hca-open-repo, hvor værkerne bor, og *fletttes* med
  master2-kolonnen i stage 4b. Mindre flytning, men to kilder til én facet
  — dokumentér da præcist hvem der vinder ved uenighed.

Anbefaling: den delte model, netop fordi den værkbaserede rolle bygger på
samme `nameKey()`-matchning som `worksByAuthor()` på personsiden. Flytter
man den, risikerer man at facetten og detaljesiden begynder at være uenige.

### Trin 3 — afvikl dubletterne i hca-open-repo

Når master2 leverer kolonnerne:

* `scripts/parsers/parse_person_gender.py` → **fjernes**. Erstattes af et
  opslag i `25_gender`.
* `scripts/parsers/parse_person_ethnic_descriptors.py` (stage 1e) →
  **fjernes** fra `build_all.py`. Erstattes af `16_nationality`.
* `scripts/parsers/parse_person_role.py` → reduceres til kun den
  værkbaserede del (jf. trin 2), eller fjernes helt.
* `data/normalized/person_gender.csv`, `person_role.csv`,
  `person_ethnic_descriptors.csv` → afløses af én indlæst master2-fil.

Behold `ethnic_adjectives_da.csv` og `person_role_terms_da.csv` som
kuraterede termlister, men flyt dem til diaries-repoet sammen med den kode
der bruger dem. Det er ægte arbejde, der ikke skal kastes væk — kun
flyttes derhen hvor det hører til.

### Trin 4 — indfør gaten

I `build_persons_extra.py` (stage 4b) og alle andre forbrugere:

```python
if row["29_entityType"] != "individual":
    continue      # familier, firmaer, grupper får ingen personfacetter
```

Det er det ene sted i planen, der retter en **synlig** fejl frem for blot
at rydde op: uden gaten kan ikke-personer optræde i personfilterboksene.

### Trin 5 — reducér `build_all.py`

Efter trin 3 falder stage 1e helt bort. `build_all.py` bør derefter kun
have ét persontrin: indlæs master2 → `persons-extra.js`. Overvej samtidig
at lade `build_all.py` **fejle** frem for at fortsætte, hvis master2
mangler. I dag er stage 1e `optional=True` med den begrundelse, at
committet data skal kunne bære en kørsel uden `lingua` osv. Den begrundelse
holder ikke for master2: forsvinder den, står filterboksene tomme, og det
bør ikke ske stille.

## Rækkefølge og risiko

| Trin | Afhænger af | Risiko |
|---|---|---|
| 0 kør på master1 | — | Lav, men afdækker sandsynligvis nye kanttilfælde i de ~1.150 nye poster |
| 1 kontrakt | 0 | Ingen kode ændres |
| 2 rollefacet | 1 | **Højest** — den værkbaserede del kan komme i utakt med personsiden |
| 3 afvikl dubletter | 1, 2 | Middel — facetværdier kan skifte for enkeltposter; diff dem før/efter |
| 4 gate | 1 | Lav, retter en synlig fejl |
| 5 slank build_all | 3 | Lav |

Trin 0 og 4 giver mest for mindst arbejde og kan tages først, uafhængigt
af resten.

## Det der bør verificeres, ikke antages

* Bliver `crossReferenceMalformed` faktisk tom efter master1? Rapporten
  siger de 5 rækker *bør* blive almindelige poster — det er en forudsigelse,
  ikke en måling.
* Hvor mange af master1s ~1.150 ekstra poster får overhovedet et køn?
  Mange af dem er de tyndest beskrevne poster i registret, så andelen
  »Endnu ubestemt« stiger sandsynligvis. Det er ikke en regression.
* Giver de to kønsscripts forskellige svar på de poster, de begge dækker?
  Kør dem mod hinanden **før** dubletten fjernes; uenighederne er den
  billigste liste over kanttilfælde, der findes.
