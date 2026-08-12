# NER-opgave pr. dagbogsside (adapteret fra NER4andersen)

## Baggrund

`ner4andersen` definerer en flertrins-berigelsespipeline (harvest →
konsolidering → forsoning → kuratering) der arbejder på tværs af hele
registret, med kilde-provenance pr. kandidat (`sources[]`: bind, side,
type) og en confidence-score pr. forsoningskandidat (§6–§7 i
`plan-v3.md`).

I `hca-open-repo` findes allerede en side-skaleret faktatabel for
forekomster (`data/normalized_v092/references.csv`, grain: én række pr.
`entity_id` × `page_id` × `seq`), men ingen NLP-baseret
udtræksopgave, der genererer disse rækker fra dagbogsteksten selv —
lige nu kommer forekomsterne fra de allerede strukturerede Excel-
registre (`raw/HCA-Repository V0.82.xlsx`), ikke fra tekstgenkendelse.

Dette dokument definerer opgaven, der producerer de manglende rækker:
**pr. dagbogsside, identificér navngivne entiteter i sidens rå tekst**.

## Opgavedefinition

For hver side i `data/normalized_v092/diary.csv` (nøgle: `vol` + `page`,
tekstfelt `text` med linjetags `NNN-LL`):

1. **Udtræk** alle strenge i sidens tekst, der udgør en navngiven
   entitet (person eller sted — samme afgrænsning som ner4andersen §11:
   organisationer/nøgleord er uden for scope).
2. **Antagelse om forekomsthyppighed:** hver entitet, der optræder på
   siden, antages at forekomme **mellem 1 og 5 gange** på den side.
   Dette er en heuristik til at kalibrere recall-mål og til at
   sandsynlighedsvurdere kandidatlister — ikke en hård grænse i output.
3. **Mål:** identificér så mange af siden entiteter som muligt (maksimér
   recall over listen af entiteter, der reelt optræder på siden), givet
   antagelsen i punkt 2.
4. **1:1-tildeling:** hver forekomst-streng bør ideelt tildeles **præcis
   én** entitet (samme entydigheds-princip som `person_derived`/
   `entity_id`-kobling i eksisterende data — en streng er ikke delt
   mellem to registerposter). Hvor en streng er reelt tvetydig
   (f.eks. et fornavn der matcher flere registrerede personer), skal
   den bedste kandidat vælges og usikkerheden afspejles i
   confidence-scoren, ikke ved at tildele strengen til flere entiteter.
5. **Confidence-score:** hver streng→entitet-tildeling får en numerisk
   confidence-score, efter samme mønster som eksisterende scorere i
   repoet (`parse_person_gender.py`, `detect_work_language.py`,
   `add_language_column.py`): en scorer/klassifikator producerer en
   værdi, ingen automatisk skrivning til de kuraterede filer uden
   menneskelig gennemgang under en tærskel.

## Output-skema

Foreslået udvidelse af den eksisterende forekomst-model
(`references.csv`-mønsteret), som et separat forslags-lag —
samme separations-princip som `wikidata_lookup.py`, der **aldrig**
selv skriver til den kuraterede fil:

```
page_id,vol,page,mention_text,mention_start,mention_end,entity_id,entity_label,confidence,method
Pag060001,VI,1,"Bentley",12,19,P1324800,"Bentley, Richard (1794–1871)",0.87,ner_candidate_v1
```

| Felt | Betydning |
|---|---|
| `page_id` | Samme nøgle som `references.csv` (`Pag{vol:02d}{page:04d}`) |
| `mention_text` | Den udtrukne streng, som den forekommer i `diary.csv.text` |
| `mention_start`/`mention_end` | Tegnposition i sidens `text`-felt (linjetag `NNN-LL` medregnes som en del af teksten, jf. eksisterende OCR-linjetagging) |
| `entity_id` | Bedste 1:1-kandidat fra `entities.csv` |
| `confidence` | `[0.0, 1.0]`, samme skala som `person_gender.csv` |
| `method` | Scorer-/model-identifikator, til reproducerbarhed (jf. ner4andersen §9's krav om reproducerbare evalueringsrapporter) |

## Kuraterings-tærskel

Følg samme mønster som `add_language_column.py`: rækker under en
tærskel (foreslået `NER_MIN_CONF`, kalibreres senere) flages til manuel
gennemgang og skrives **ikke** direkte til `references.csv`. Kun en
kurator kan flytte en kandidatrække fra forslagslaget til den
kuraterede faktatabel — jf. den generelle regel i `CLAUDE.md` om
faktakontrol og selvkritik: en confidence-score erstatter aldrig
verifikation.

## Forhold til ner4andersen

| ner4andersen (fuldt register, flertrins) | hca-open-repo (denne opgave) |
|---|---|
| Kilder: redaktionelle noter + trykte indekser | Kilde: rå sidetekst (`diary.csv.text`) |
| Konsolideret kandidatrecord med `sources[]` | Forslagsrække pr. side med `mention_start/end` |
| Ekstern forsoning (Wikidata/GND/VIAF/GeoNames) | Intern forsoning mod `entities.csv` (samme repo-registre) |
| Menneskelig kuratering via OpenRefine + TEI `@ref` | Menneskelig kuratering før optag i `references.csv` |
| Entitetstyper: person, place | Samme — person, place |

Denne opgave dækker ner4andersens Stage 0.5–1 (harvest + konsolidering)
i miniature, skaleret til én sides tekst ad gangen, uden den eksterne
forsoningsfase — fordi `hca-open-repo`s entiteter allerede er interne
registerposter.
