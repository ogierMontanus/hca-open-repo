# Konsolideringskørsel — resultater, 2026-09-03

Kørsel af planen i `person-postprocessing-consolidation.md`. Dette
dokument er resultatet: hvad der blev gjort, hvad målingerne viste, hvor
planen tog fejl, og hvad der bevidst ikke blev udført.

**Kort:** Trin 0 og 1 er gennemført, og master2 findes nu som én fil.
Trin 4 er målt og forberedt, men ikke indført. Trin 2, 3 og 5 er
**ikke** udført — se »Ikke udført« nedenfor for hvorfor.

## Gennemført

### Trin 0 — berigelseskæden kører nu på master1

Ny `volume12/load_master1.py` erstatter `extract_dimper.py` som kædens
indgang. Den læser master1 og skriver de samme fem kolonner, kæden
forventer, så alt nedenstrøms kører uændret.

`RegistryTitle` rekonstrueres fra master1s opsplittede navnefelter til
registrets trykte form (`Efternavn, Fornavn (født–død)`), fordi flere
regler nedenfor læser titlen direkte: `parse_title()`, titel-som-
kønsmarkør, og territorium-i-første-kommafelt i herskerlogikken.

**Kædens omfang: 8.917 → 10.081 poster.**

| Fil | Rækker | Kolonner |
|---|---:|---|
| `DimPer.tsv` (ny, fra master1) | 10.081 | 5 + 4 hjælpekolonner |
| `DimPer_enriched.tsv` | 10.081 | → 15 |
| `DimPer_nationality.tsv` | 10.081 | → 19 |
| `DimPer_ruler.tsv` | 10.081 | → 24 |
| `DimPer_gender.tsv` | 10.081 | → 28 |
| **`DimPer_master2.tsv`** | **10.081** | **31** |

Titelrekonstruktionen blev verificeret mod den gamle udtrækning:
**8.096 titler er tegn-for-tegn identiske**. Resten er dels
mellemrumsnormalisering fra oprydningen (`C.F.` → `C. F.`), dels poster
der reelt er ændret. Én formfejl blev fundet og rettet undervejs:
`dødsår usikkert` skal skrives som registrets `1833–?`, ikke som en note,
ellers ser `parse_title()` et format den ikke kender.

### Trin 0 — entityType flettet ind i kæden

Ny `volume12/merge_entitytype.py`. `classify_entity_type.py` kørte
sideordnet, så dens tre kolonner aldrig nåede kædens slutprodukt, og
gaten `is_individual()` kunne derfor ikke bruges af forbrugerne — selv om
det er præcis det, den er skrevet til.

`DimPer_gender.tsv` + `DimPer_entitytype.tsv` → **`DimPer_master2.tsv`**
(31 kolonner). Det er nu den ene fil, hca-open-repo skal læse.

### Trin 1 — kontrakten

Kolonnerne ligger fast som beskrevet i planen. Join-nøglen er tilføjet
som en egentlig kolonne i stedet for en konvention: `load_master1.py`
skriver `06_refSignature` (efternavn + sorterede sidehenvisninger), så
senere trin kan joine på noget stabilt frem for på et positionsbestemt id.

## Målinger

### Køn: master2 mod hca-open-repos parallelle script

Planens vigtigste krav var at diffe de to kønsscripts **før** dubletten
fjernes. Sammenligning på normaliseret label, kun poster med et entydigt
match (8.957 af dem):

| | Antal |
|---|---:|
| Enige | 7.551 |
| Uenige | 1.406 |
| Uden entydigt match | 1.271 |

Uenighedernes **retning** er det afgørende:

| hca-open-repo | → master2 | Antal |
|---|---|---:|
| Endnu ubestemt | Mandlig | 1.345 |
| Endnu ubestemt | Kvindelig | 42 |
| Kvindelig | Endnu ubestemt | 13 |
| Mandlig | Endnu ubestemt | 6 |

**1.387 gevinster mod 19 tab.** Det er ikke to ligeværdige metoder, der er
uenige — master2 afgør poster, hca-open-repo lader stå åbne. Det er
belægget for at afvikle dubletten.

### Fund undervejs: master2 manglede `Frk.`

Diffen afdækkede et reelt hul, ikke støj: hca-open-repo læste
korrekt `Frk.` som kvindemarkør, master2 gjorde ikke. `gender_markers_da.csv`
havde `Frøken`, `Frue` og `Mrs` — men ikke den forkortelse, registret
faktisk bruger mest (`Achte, Frk.`).

Tilføjet som `label_title,Frk,K,2.6`. Effekt:

| | Før | Efter |
|---|---:|---:|
| Kvindelig | 3.134 | **3.162** |
| Endnu ubestemt | 1.787 | **1.759** |
| Tab mod hca-open-repo (Kvindelig → ubestemt) | 34 | **13** |

Havde dubletten været fjernet uden diffen først, var 28 kvinder gået tabt
i filterboksen uden at nogen opdagede det. Det er argumentet for, at
diff-før-sletning skal være en fast regel, ikke en engangsforanstaltning.

### Køn: fordelingen efter kørsel på master1

| Kategori | Før (8.917) | Efter (10.081) |
|---|---:|---:|
| Mandlig | 4.790 (53,7 %) | 5.160 (51,2 %) |
| Kvindelig | 2.894 (32,5 %) | 3.162 (31,4 %) |
| Endnu ubestemt | 1.233 (13,8 %) | 1.759 (17,4 %) |

Andelen »Endnu ubestemt« stiger, som planen forudsagde. Det er **ikke** en
regression: de ~1.150 nye poster er de tyndest beskrevne i registret.

### entityType

| entityType | Før (8.917) | Efter (10.081) |
|---|---:|---:|
| individual | 8.840 | 9.979 |
| family | 30 | 35 |
| crossReferenceMalformed | 5 | **22** |
| relationalPlaceholder | 14 | 15 |
| organisation | 13 | 13 |
| group | 9 | 9 |
| legendary | 3 | 3 |
| crossReference | 2 | 3 |
| animal | 1 | 2 |
| **Undtaget i alt** | **77** | **102** |

### Trin 4 — gatens faktiske virkning målt

Planen antog, at manglende gate lod ikke-personer få personattributter.
Det er nu målt frem for antaget: af de 98 ikke-individ-poster, der kan
matches, får **4 i dag tildelt et køn** i hca-open-repo:

| Post | Køn i dag | entityType |
|---|---|---|
| `Krause` | Kvindelig | family |
| `Schlichtkrull` | Kvindelig | family |
| `Skibsted` | Kvindelig | family |
| `From-Møller, se: Møller, A. C. A. From…` | Kvindelig | crossReferenceMalformed |

Fejlen er altså **reel, men lille** — fire poster, ikke 77. Det ændrer
prioriteringen: gaten er stadig rigtig, men den er en oprydning, ikke en
hastesag.

## Hvor planen tog fejl

**1. `crossReferenceMalformed` blev ikke tom — den blev firedoblet (5 → 22).**

Planen forudsagde, at master1s oprydning ville gøre de fem defekte rækker
til almindelige poster. Det modsatte skete. Klassifikatoren fungerer
korrekt; master1 indeholder simpelthen flere rækker, og dermed flere af
netop denne fusionstype — en krydshenvisning limet sammen med den
efterfølgende post:

```
Arnaud, H., se: Reybaud. Fanny. Arndt, Ernst Moritz (1769–1860)
Aubert, se ogsaa: d'Aubert. Aubert, Ludvig Cæsar Martin
Jonas, se: Collin, Jonas d. Y. Jonas, Emil (1824–1912)
Orvar Odd, se: Sturzen-Becker, O. P. Ostade, Adriaen van
```

Det er **22 rigtige personer, der i dag er utilgængelige** bag en defekt
række. De skal repareres i master1s parsning — ikke i berigelsen.

**2. Gaten var allerede delvis indført.** `add_gender.py` læser selv
`DimPer_entitytype.tsv` og undtager de 102 poster. Planen beskrev gaten
som fraværende i hele kæden; den mangler kun hos forbrugerne i
hca-open-repo.

## Ikke udført — og hvorfor

**Trin 2 (flyt rollefacetten), Trin 3 (slet dubletscripts), Trin 5
(slank `build_all.py`)** er ikke gennemført.

De tre trin indebærer at slette kørende scripts og omlægge det byggetrin,
der producerer `persons-extra.js` til den live mockup. To forhold taler
imod at gøre det uden aftale:

* **`datacleaning` er ikke under versionsstyring.** `git rev-parse` siger
  *not a git repository*. master2 — som hca-open-repo efter trin 3 ville
  være helt afhængig af — ligger dermed uden historik, uden mulighed for
  at rulle tilbage, og uden at ændringer kan spores. At gøre en
  versionsstyret pipeline afhængig af en uversioneret kilde bytter ét
  konsistensproblem ud med et større.
* **Trin 2 er planens egen højrisikopost.** Den værkbaserede rolle bruger
  samme `nameKey()`-matchning som personsidens `worksByAuthor()`. Flyttes
  den, kan facet og detaljeside blive uenige — præcis den slags
  uoverensstemmelse, konsolideringen skal fjerne.

## Forslag til forbedringer

**Først, og billigst:**

1. **Sæt `datacleaning` under versionsstyring**, før hca-open-repo gøres
   afhængig af master2. Det er forudsætningen for trin 3, ikke en
   sidebemærkning.
2. **Reparér de 22 `crossReferenceMalformed`-rækker i master1.** De er 22
   personer, der i dag mangler helt. Mønstret er velkendt fra denne
   sessions øvrige oprydning: en `se:`-henvisning limet på den følgende
   post. Et `suggest`/`apply`-scriptpar i samme form som de øvrige vil
   kunne tage dem.
3. **Indfør gaten** i `build_persons_extra.py` (fire synligt forkerte
   poster). Lav og isoleret risiko.

**Dernæst:**

4. **Gør diff-før-sletning til en fast regel.** `Frk.`-fundet viser, at
   den parallelle implementering ikke kun er dobbeltarbejde — den er også
   det eneste, der afslører huller i den, man beholder. Kør de to
   implementeringer mod hinanden, og *dokumentér uenighederne*, før den
   ene fjernes.
5. **Kopiér `Frk.`-rettelsen tilbage til hca-open-repos
   `gender_markers_da.csv`**, hvis den fil beholdes indtil trin 3. Ellers
   divergerer de to termlister nu aktivt.
6. **Lad kun `06_refSignature` være join-nøgle.** Den er skrevet, men
   endnu ikke brugt. Så længe noget joiner på `PerID` eller
   `01_entry_id`, er den næste omnummerering en latent fejl.

**Til overvejelse:**

7. **De 1.271 poster uden entydigt label-match** mellem de to kilder er
   ikke undersøgt. De kan skjule både dubletter og reelle huller, og de er
   det oplagte næste sted at kigge efter systematiske fejl.
8. **Overvej om `person_role.csv` overhovedet skal flyttes.** Målingen
   viste, at gevinsten ved konsolidering ligger i køn og nationalitet.
   Rollefacetten er den mest sammenfiltrede og den mindst gevinstgivende —
   den delte model i planens trin 2 er formentlig stadig den rigtige, men
   den bør prioriteres sidst.

## Filer ændret

**`datacleaning/diaries_datacleaning/volume12/`** (uversioneret)

| Fil | Status |
|---|---|
| `load_master1.py` | ny |
| `merge_entitytype.py` | ny |
| `person-enrichment.md` | ny (fra forrige opgave) |
| `gender_markers_da.csv` | `Frk`-markør tilføjet |
| `DimPer*.tsv` | regenereret på master1 (10.081 rækker) |
| `DimPer_master2.tsv` | ny — master2 som én fil |

**`hca-open-repo/`** — kun dokumentation; ingen kode eller data ændret.

| Fil | Status |
|---|---|
| `docs/data-model/person-master-files.md` | ny (forrige opgave) |
| `docs/data-model/person-postprocessing-consolidation.md` | ny (forrige opgave) |
| `docs/data-model/person-consolidation-run-2026-09-03.md` | dette dokument |

Sikkerhedskopier af kædens tilstand før kørslen ligger i sessionens
scratchpad (`before/DimPer*.tsv`, `gender_markers_da.csv.bak`).
