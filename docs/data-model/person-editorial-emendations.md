# Post-editorielle rettelser med kildeangivelse

Registret er en trykt kilde fra 1970'erne. Nogle poster er siden blevet
identificeret bedre, end de trykte redaktører kunne. Dette dokument
fastlægger, hvordan sådanne rettelser **føjes til** uden at overskrive
kilden, og hvordan de vises, så en læser altid kan se hvad der står i
bogen, og hvad vi har tilføjet bagefter.

Eksemplet der udløste modellen:

```
Registret:  Oesterling, tysk Maler (Navnet maaske misforstaaet). II 406.
Rettelse:   Osterley, Carl (1805–1891)
Kilde:      HCAC, 2026-09-03
```

Bemærk at registret **selv flager tvivlen** — »(Navnet maaske
misforstaaet)«. Rettelsen løser præcis det, de trykte redaktører markerede
som usikkert. Det er den bedste slags rettelse: den svarer på et spørgsmål,
kilden selv stiller.

## Grundprincippet

Projektets regel gælder også her: *originaldata må aldrig gå tabt, kun
suppleres*. En rettelse er derfor **aldrig** en redigering af
`03_surname`, `04_given_names` eller `09_description` i master1. Den er en
selvstændig påstand med sin egen kilde, som lægges ovenpå ved visning.

Tre grunde til at det ikke bare er pedanteri:

1. **Rettelser kan være forkerte.** »Osterley« er en kvalificeret
   identifikation, ikke en observation. Skrives den ind i navnefeltet, kan
   den ikke længere skelnes fra det, der faktisk står i bogen.
2. **Sidehenvisningerne hører til den trykte post.** `II 406` peger på en
   side, hvor der står »Oesterling«. Ændrer man navnet i selve rækken,
   passer henvisningen ikke længere til det, læseren finder.
3. **Nøglen er ustabil.** `01_entry_id` gennemnummereres ved enhver
   ændring (se `person-master-files.md`), så en rettelse kan ikke
   forankres på id.

## Datamodel

Én kurateret fil, samme mønster som `given_name_gender_overrides.csv`:

```
data/curated/person_emendations.tsv
```

| Kolonne | Indhold |
|---|---|
| `match_surname` | Efternavn i master1, som det står |
| `match_refs` | `11_references_parsed`-signaturen, fx `II:406` |
| `field` | Hvilket felt rettelsen angår: `surname`, `given_names`, `birth_year`, `death_year`, `description` |
| `original` | Værdien i registret — skrives ud, så en utilsigtet ændring i master1 kan opdages |
| `emended` | Den rettede værdi |
| `source` | Kildekode, fx `HCAC` |
| `source_detail` | Præcis henvisning, hvis der er en (bind/side/opslag) |
| `date` | ISO-dato for rettelsen |
| `confidence` | `certain` / `probable` / `proposed` |
| `notes` | Begrundelsen i klartekst — obligatorisk |

### Nøglen: efternavn + henvisningssignatur

Ikke `01_entry_id`, som omnummereres. Ikke label alene, for det er netop
labelen der rettes. Sidehenvisningerne er de eneste stabile: de er de
samme tal i enhver transskription af det trykte register, og de ændrer sig
ikke, når vi retter et navn.

`original` er med som en **vagt**: matcher den ikke længere det, master1
indeholder, er posten under føttterne på rettelsen skiftet, og rettelsen
skal genvurderes frem for at blive anvendt blindt.

### `confidence` er ikke pynt

| Værdi | Betydning | Visning | Ordlyd i krydshenvisning |
|---|---|---|---|
| `certain` | Dokumenteret; ingen rimelig tvivl | Rettelsen vises som den primære form | `se:` |
| `probable` | Stærkt underbygget, men en slutning | Rettelsen vises, originalen med | `sandsynligvis hentydning til:` |
| `proposed` | Kvalificeret forslag | Originalen er primær, rettelsen nævnes | `muligvis hentydning til:` |

Uden gradueringen ville en velbegrundet formodning se ud som en kendsgerning.

### Emendationer grupperes pr. post, ikke pr. felt

En rettelse kan røre ét eller flere felter — Oesterling-sagen rører fire
(efternavn, fornavn, fødselsår, dødsår), fordi identifikationen af personen
medfører dem alle. Datafilen har én række pr. felt, så hver enkelt kan bære
sin egen kilde og sikkerhedsgrad, men **visningen samler dem til én
rettelse pr. post**. Læseren skal se ét rettet opslag med én begrundelse,
ikke fire separate noter om samme person.

Rækker der hører sammen, deler nøgle (`match_surname` + `match_refs`).

## Rettet efternavn kræver en krydshenvisning

Et rettet efternavn flytter posten i alfabetet. Konkret for Oesterling:

```
som trykt:  … Østergaard · Östergötland · [Oesterling] · Oesterreicher · Østrig …
efter:      … Ortwed · Orvar Odd · [Osterley] · Ostermann-Tolstoj · Osterroth …
```

Det er en helt anden del af registret. Slår nogen op på »Oesterling«,
fordi det er det, der står i bogen, findes posten ikke længere dér — med
mindre vi efterlader et spor.

Registret har allerede mekanismen: 410 poster er `krydshenvisning` med
målet i `12_see_also`. En emendation af `surname` skal derfor **også**
frembringe en krydshenvisningspost på den oprindelige plads:

```
03_surname     = "Oesterling"
02_entry_type  = "krydshenvisning"
12_see_also    = "Osterley, Carl"
09_description = "sandsynligvis hentydning til: Osterley, Carl (1805–1891).
                  Registret: »tysk Maler (Navnet maaske misforstaaet)«.
                  Rettet efter HCAC, 2026-09-03."
```

Ordlyden følger sikkerhedsgraden (tabellen ovenfor). `se:` bruges kun ved
`certain` — for det er registrets eget ord for en identitet, der ikke er
til diskussion. Ved `probable`/`proposed` ville `se:` påstå mere, end vi
ved, og derfor bruges »sandsynligvis/muligvis hentydning til«.

Krydshenvisningen er **afledt**, ikke håndskrevet: den genereres af
emendationen, så den ikke kan komme i utakt med den.

## Visning

Læseren skal kunne se tre ting på én gang: hvad bogen siger, hvad vi
mener, og hvem der mener det.

```
Osterley, Carl (1805–1891)
tysk Maler
    Registret: »Oesterling, tysk Maler (Navnet maaske misforstaaet).«
    Rettet efter HCAC, 2026-09-03
```

Regler:

* **Originalen forsvinder aldrig fra siden.** Den er kilden; rettelsen er
  vores lag ovenpå.
* **Kilden står altid ved rettelsen** — aldrig en rettet form uden
  angivelse af hvem der har rettet den og hvornår.
* **Søgning skal finde begge former.** Nogen der leder efter
  »Oesterling«, fordi det er det, der står i bogen, skal finde posten;
  det samme skal nogen, der leder efter »Osterley«.
* **Facetter bruger den rettede værdi** ved `certain`/`probable`, den
  oprindelige ved `proposed`.
* I lister og kort form vises den rettede form med en diskret markør, der
  fører til den fulde begrundelse — ikke hele apparatet hver gang.

## Kildekoder

`source` holdes kort og genbruges. Foreløbig:

| Kode | Betydning |
|---|---|
| `HCAC` | H.C. Andersen Centret |
| `BDA` | Bibliografisk/biografisk opslagsværk (præciseres i `source_detail`) |
| `WD` | Wikidata (Q-nummer i `source_detail`; verificeres jf. `wikidata-verify`-skill) |
| `REG` | Registret selv modsiger sig andetsteds — fx `Asbjømsen` i labelen mod korrekt `Asbjørnsen` i en værktitel i samme datasæt |

`REG` er værd at have, fordi den slags rettelse ikke kræver en ekstern
autoritet: kilden dementerer sig selv, og det kan dokumenteres internt.

## Forholdet til OCR-fejl

De to ligner hinanden, men skal holdes adskilt:

* En **OCR-fejl** er en fejllæsning af trykken. `Asbjømsen` → `Asbjørnsen`
  (`rn` læst som `m`). Bogen siger det rigtige; vores fil siger det
  forkerte. Det er en transskriptionsrettelse — den hører til i
  parsningen, med `REG` som kilde hvis den skal dokumenteres.
* En **emendation** er en rettelse af det, bogen faktisk siger.
  `Oesterling` står der virkelig; det er redaktørerne, der tog fejl (og
  selv var i tvivl). Den hører til her.

Se `person-register-ocr-typos.md` for Asbjørnsen-sagen, som stadig
afventer den transskriptionsoprydning.

## Master2 ser den rettede form

**Besluttet 2026-09-03.** Berigelseskæden læser master1 gennem
emendationslaget, ikke master1 rå.

Begrundelsen er den samme som eksemplet: »Oesterling« har intet fornavn og
ingen årstal, så kæden kan hverken udlede køn eller levetid. »Osterley,
Carl (1805–1891)« giver den alle tre. At lade kæden læse den ukorrigerede
form ville betyde, at vi kender oplysningen, men bevidst afholder
facetterne fra at bruge den.

Konsekvenser, der skal håndteres i `load_master1.py`:

* `RegistryTitle` bygges af den **rettede** form, så `parse_title()`,
  titel-som-kønsmarkør og herskerlogikken ser den.
* Den oprindelige form skal med som en selvstændig kolonne, så
  berigelsens output stadig kan spores tilbage til det trykte.
* Krydshenvisningsposten (ovenfor) er `krydshenvisning` og bliver derfor
  undtaget af `classify_entity_type.py` som ikke-individ — den skal ikke
  tælle med som en ekstra person i facetterne.

## Åbent problem: mockup'en ser ikke emendationerne endnu

Rettelseslaget når **master2**, men ikke `persons-extra.js`. Kæden er:

```
master1 ──► resolved ──► master2                     rettelsen er med
data/raw/HCA REPOSITORY V0.82 ──► entities.csv ──► persons-extra.js   den er IKKE
```

`build_persons_extra.py` bygger på `entities.csv`, som stammer fra det
gamle regneark — ikke fra master1. `Reg0132130 | Oesterling` står der
derfor stadig ukorrigeret, mens master2 har `Osterley, Carl (1805–1891)`
med køn *Mandlig* og nationalitet *Tysk* udledt af rettelsen.

Det er samme grundproblem som konsolideringsplanen adresserer: to kilder
til de samme personer. Emendationerne kan ikke vises for læseren, før
`persons-extra.js` bygger på master2 (planens trin 3), eller før
emendations-JSON'en lægges ovenpå ved visning som et selvstændigt trin.

Indtil da er `data/normalized/person_emendations.json` skrevet og klar,
men uforbrugt.

## Hvad der bevidst ikke er besluttet

* **Om `description` bør emenderes felt-for-felt** eller kun som helhed.
  Beskrivelsen er fri tekst med flere påstande i; en rettelse rammer typisk
  én af dem. Modellen viser altid **hele feltet** (besluttet 2026-09-03),
  så spørgsmålet er alene, om flere delrettelser til samme beskrivelse skal
  kunne registreres hver for sig. Afventer et konkret tilfælde.
* **Flere rettelser til samme felt fra forskellige kilder.** Modellen
  tillader det teknisk (flere rækker), men der er ingen regel for hvem der
  vinder. Første gang det sker, skal reglen skrives — ikke før.
