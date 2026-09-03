# Personregistret — masterfiler og pipelinekæde

Dette dokument fastlægger **hvilken fil der er kilden** for persondata, og
hvad de aftalte navne `master1` og `master2` dækker. Det er skrevet fordi
persondata i dag berøres af to repositorier og af mindst tre parallelle
efterbehandlings-scripts, og fordi det tidligere ikke fremgik hvilken fil
der vandt ved uenighed.

## master1 — det rensede personregister

```
hca-open-repo : data/curated/personregister_xi_review_full.tsv
```

**`master1` er den nye masterfil for personer.** 10.081 poster (plus
header). Den er resultatet af den OCR- og segmenteringsoprydning der er
gennemført på registret til dagbøgernes bind XI, og den afløser tidligere
brug af regnearket i `data/raw/HCA REPOSITORY V*/` som direkte kilde til
personattributter.

### Kolonner

| Kolonne | Indhold |
|---|---|
| `01_entry_id` | `PerXI#####` — **positionsbestemt**, se advarsel nedenfor |
| `02_entry_type` | `standardpost` / `krydshenvisning` / `underpost` |
| `03_surname` | Efternavn (kan være flerleddet: `auf der Maur`, `de la Rosa`) |
| `04_given_names` | Fornavn(e), inkl. pigenavn (`Elisa, f. Hallady`) og titel |
| `05_sort_key` | `Efternavn, Fornavn` |
| `06_birth_year` / `07_death_year` | Årstal, rene tal |
| `08_year_note` | Kvalifikation: `ca.`, `f. Kr. (BC)`, `74 Aar gl.`, `1476/77` |
| `09_description` | Erhverv/biografi — den tidligere »profession«-kolonne |
| `10_references_raw` | Sidehenvisninger som trykt: `II 422 424. IV 127.` |
| `11_references_parsed` | Normaliseret: `II:422;II:424;IV:127` |
| `12_see_also` | Krydshenvisningsmål |
| `13_raw_text` | Uændret OCR-linje — revisionsspor, må aldrig redigeres |
| `review_flags` | Maskingenererede advarsler, se `build_review_workbook.py` |

`personregister_xi_review_full.xlsx` er den samme tabel med farvekodning
og kommentarer til manuel gennemgang. TSV'en er den maskinlæsbare kilde;
XLSX'en er gennemsynsfladen.

### Advarsel: `01_entry_id` er ikke stabil

Id'erne tildeles efter **position** i filen og gennemnummereres hver gang
rækker tilføjes, fjernes eller splittes. Et id fra en tidligere kørsel
peger derfor ikke nødvendigvis på den samme person i dag. Det har allerede
forårsaget mindst to konkrete fejl i dette projekt: et split-script
overskrev en urelateret Wedell-Wedellsborg-post, fordi det slog op på et
forældet id, og en batch af gennemsyns-id'er fra et ældre ark pegede på
helt andre poster efter en deduplikering.

**Regel:** slå aldrig en post op på `01_entry_id` på tværs af kørsler.
Match på indhold — efternavn plus `11_references_parsed`-signatur er den
stabile nøgle, fordi sidetallene er de samme i enhver transskription af
det trykte register.

## master2 — det berigede personregister

```
datacleaning/diaries_datacleaning : DimPer_*.tsv (beriget)
```

**`master2` er master1 beriget med facetattributter** — køn, erhverv,
entitetstype og herskerstatus — produceret i repoet
`datacleaning/diaries_datacleaning`. Beriget, ikke ændret: originale
kolonner røres ikke, der lægges kun kolonner til (projektets regel
*originaldata må aldrig gå tabt, kun suppleres*).

Se `volume12/person-enrichment.md` i det repo for hvad hver kolonne
betyder, hvilken evidens den bygger på, og hvilke poster der bevidst
undtages.

## Kæden

```
   trykt register (OCR)
        │
        ▼
   hca-open-repo/scripts/parsers/…          ← segmentering, dedup, OCR-fix
        │
        ▼
   master1  personregister_xi_review_full.tsv
        │
        ▼
   datacleaning/diaries_datacleaning/…      ← køn, erhverv, entityType, herskere
        │
        ▼
   master2  DimPer_*.tsv  (beriget)
        │
        ▼
   hca-open-repo/scripts/build_*            ← kun præsentation, ingen ny udledning
        │
        ▼
   mockup/data/persons-extra.js  →  filterbokse
```

Retningen er envejs. Beriget data flyder **fra** master2 **til**
byggetrinnene — aldrig omvendt, og byggetrinnene må ikke udlede
personattributter på egen hånd. Se
`docs/data-model/person-postprocessing-consolidation.md` for hvorfor det
i dag ikke holder, og planen for at rette op.
