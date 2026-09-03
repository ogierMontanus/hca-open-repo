# Konsolidering, anden kørsel — 2026-09-03

Opfølgning på `person-consolidation-run-2026-09-03.md`. Rækkefølgen var
aftalt: versionsstyr `datacleaning` → reparér de 22 defekte rækker →
indfør gaten. Alle tre er behandlet.

## 1. Versionsstyring — anbefalingen var bygget på en fejlmåling

**`diaries_datacleaning` var allerede under versionsstyring.** Repoet har
sin egen `.git` (45 MB pack), ligger på
`github.com/ogierMontanus/Data-cleaning`, står på branchen
`claude/split-artists-artwork-registry-gnxq9l` og har en aktiv historik —
de seneste commits er netop berigelsesarbejdet (`Add crossReference
entityType…`, `Add report-entityType.md and inverse spouse-office gender
rule`).

Min måling i forrige rapport kørte `git rev-parse` mod den overliggende
mappe `datacleaning/`, som blot er en uversioneret container om fire
selvstændige repoer. Konklusionen »master2 ligger uden historik« var
derfor forkert, og den præmis, der gjorde trin 3 risikabelt, holder ikke.

**Konsekvens for planen:** blokeringen af trin 3 (afvikl dubletscripts) er
ikke længere begrundet i manglende versionsstyring. Den bør genovervejes
på sine egne meritter.

Sessionens arbejde er committet i det repo:

```
8c10bd8  Run enrichment chain on master1 (10,081 rows) and merge entityType
         12 filer, +71.416 / −53.868
```

Commit'en er **lokal, ikke pushet** — `origin` er et delt GitHub-repo, og
push er ikke aftalt.

## 2. De 22 defekte krydshenvisninger

Nyt script: `scripts/parsers/suggest_malformed_xref_splits.py`
(suggest/apply, som de øvrige i mappen).

Mønstret er en krydshenvisning limet sammen med den efterfølgende post, så
begge havner i ét felt:

```
03_surname      = "Jonas"
04_given_names  = "se: Collin, Jonas d. Y. Jonas, Emil"
09_description  = "tysk Litterat og Oversætter, 1852-54 …"
10_references_raw = "IV 158. X 329."
```

Beskrivelsen og henvisningerne tilhører **den anden** person; selve
krydshenvisningen har ingen af delene.

**Resultat: 21 splittet, 4 til manuel gennemgang.**

| | Antal |
|---|---:|
| Splittet automatisk | 21 |
| Efterladt til gennemgang | 4 |
| Rækker | 10.081 → 10.102 |
| Dubletter fjernet bagefter | 8 |
| **Slutstand** | **10.094** |

Flaget `fused_entry:see_reference` i gennemsynsarket faldt **8 → 1**.

### To fejl i min egen grænselogik, fundet undervejs

Første forsøg skar ved »første punktum efterfulgt af stort bogstav«. Det
gav 12 splits, hvoraf flere var forkerte:

* `Arnaud` → målet blev `Reybaud`, men personen blev
  `Fanny. Arndt, Ernst Moritz` — målets eget fornavn røg med over i
  personen.
* `Talis Qualis` → personen blev `C.V.A. Talleyrand-`, klippet midt i
  navnet.

Samtidig faldt 12 *gyldige* rækker til MANUAL, fordi målet slutter på
initialer (`Collin, Jonas d. Y.`, `Møller, A. C. A. From`) — punktummet
dér er ikke en grænse.

Rettet til at skære ved et **registeropslag**: et stort forbogstav
efterfulgt af komma eller parentes, hvilket er den form en ny post altid
har. Det bragte 21 igennem med korrekte personnavne
(`Talleyrand-Périgord, Charles-Angelique, Baron`,
`Krarup, Nicolai Edinger`).

### 8 dubletter opstod og blev fjernet

Otte af de 21 personer fandtes allerede i registret (importeret tidligere
fra referencekilden), så splittet genskabte dem: Arndt, Bouffé, Nathansen,
Ostade, Schenk, Talleyrand-Périgord, Theresia, Trane. Fjernet med samme
regel som tidligere (identisk efternavn + fornavn + henvisningssignatur +
årstal).

Det er tredje gang i dette forløb, at en split- eller importoperation
skaber dubletter, som først opdages bagefter. Se forslag 3 nedenfor.

### De 4 til gennemgang

| Post | Hvorfor |
|---|---|
| `Treibien, vist: Dreibein, se denne. Trémolières, Pierre` | »se denne« peger på posten selv — der er intet mål at splitte på, men en tredje person (Trémolières) hænger stadig ved |
| `Elton, se: Salter, Miss.` | ren krydshenvisning uden efterfølgende post — burde omtypes til `krydshenvisning`, ikke splittes |
| `Ludvig, se: Meisling, Peter Ludvig` | samme |
| `Temerin, se: Szécses von Temerin. ten Kate` | målet og den følgende post deler navnestamme; grænsen er reelt tvetydig |

### Kosmetisk restproblem

Målene i `12_see_also` bærer stadig småfejl fra OCR'ens punktummer:
`Beutner. C`, `Møller, A. C. A, From`, manglende afsluttende punktum. Det
påvirker en linktekst, ikke en identitet, og er ikke rettet.

## 3. Gaten er indført

`scripts/build_mockup/build_persons_extra.py` udelukker nu poster, der
ikke er individer, fra personfacetterne.

Da `entities.csv` (`Reg…`) og master2 (`PerXI…`) har **uforenelige
id-rum, og begge omnummereres**, matches der på normaliseret label —
årstal fjernes, fordi de to transskriptioner sætter tegn forskelligt.

Berigelsens resultat er kopieret ind som kurateret data i dette repo:

```
data/curated/person_entity_types.tsv     102 ikke-individ-poster
```

Det følger mønstret fra `ethnic_adjectives_da.csv` og undgår en absolut
sti på tværs af repoer.

**Virkning: 82 af de 102 matcher og udelukkes.** Verificeret i outputtet:
`Collin, Familien`, `Behrens` og `Barberini, Familien` er ikke længere i
`persons-extra.js`; 10.146 rigtige personer er der stadig. Udelukket er
bl.a. 30+ familier, 13 firmaer, registrets ene dyr (`Balám`), de
legendariske (`Curtius, Marcus`) og de relationelle underposter.

Mangler master2-filen, degraderer trinnet — men **siger det højlydt**, i
stedet for at lade en manglende gate ligne en virkende:

```
[!] no entityType data — non-individuals are NOT gated
```

De 20, der ikke matcher, skyldes at labels afviger mellem de to kilder ud
over årstal. Det er en øvre grænse for gatens dækning, ikke en fejl i den.

## Begrænsninger

1. **Push er ikke sket.** Commit'en i `diaries_datacleaning` er lokal.
   `origin` er delt, og push var ikke aftalt.
2. **`persons-extra.js` er ikke versionsstyret**, så gatens virkning kunne
   ikke diffes mod en tidligere kørsel — kun verificeres direkte i
   outputtet. Det lykkedes, men gør fremtidige regressioner sværere at
   opdage.
3. **Gaten dækker 82 af 102.** De resterende 20 kræver enten en bedre
   matchnøgle eller en manuel kobling.
4. **Trin 2, 3 og 5 er stadig ikke udført.** Præmissen for at udskyde trin
   3 (manglende versionsstyring) er nu bortfaldet; trin 2's risiko
   (rollefacet vs. personside) står ved magt.
5. **De 4 resterende defekte rækker** kræver en menneskelig afgørelse, ikke
   en bedre regel.

## Forslag

1. **Genovervej trin 3 nu.** Den eneste anførte blokering var
   versionsstyringen, og den var en fejlmåling. Diffen viste allerede
   1.387 gevinster mod 19 tab i master2's favør.
2. **Versionsstyr `persons-extra.js`, eller læg en optælling i en test.**
   Uden en baseline kan næste utilsigtede udelukkelse ikke ses.
3. **Gør deduplikering til et fast efterled i split-scripts.** Tre gange nu
   har en split skabt dubletter, der først blev fundet ved en separat
   kørsel bagefter. Kontrollen bør ligge i `--apply` selv.
4. **Afgør de 4 rækker manuelt** — tre af dem er formentlig blot
   `krydshenvisning`-poster, der er fejltypet som `standardpost`.
5. **Ryd `12_see_also`-målene op** med samme punktum-som-komma-regel, der
   allerede bruges i splitteren.
6. **Push, når det er aftalt** — begge repoer har nu committed arbejde, der
   hænger sammen på tværs.

## Filer ændret

**`hca-open-repo`** (ikke committet)

| Fil | Status |
|---|---|
| `scripts/parsers/suggest_malformed_xref_splits.py` | ny |
| `scripts/build_mockup/build_persons_extra.py` | gate tilføjet |
| `data/curated/person_entity_types.tsv` | ny (102 rækker fra master2) |
| `data/curated/personregister_xi_malformed_xref_review.tsv` | ny |
| `data/parsed/personregister_xi_parsed.tsv` | 10.081 → 10.094 |
| `data/curated/personregister_xi_review_full.{tsv,xlsx}` | regenereret |
| `mockup/data/persons-extra.js` | regenereret med gate |
| `docs/data-model/person-consolidation-run-2026-09-03b.md` | dette dokument |

**`datacleaning/diaries_datacleaning`** — committet lokalt som `8c10bd8`.

13/13 tests grønne.
