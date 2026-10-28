# Model for den kombinerede version (leverance C)

Grundlag: [`kildeanalyse.md`](kildeanalyse.md) §5. Denne fil er en
**specifikation**; intet af det er implementeret endnu.

## 1. Principper

1. **Kilderne røres aldrig.** `SRC-DB` og `SRC-PDF` læses; alt andet er afledt.
2. **Tre lag, adskilt i filer og i ansvar:**
   * *udtræk* (`data/extracted/`) — maskinelt, reproducerbart, ikke autoritativt;
   * *beslutninger* (`data/review/`) — menneskelige afgørelser, autoritative,
     versioneret i git, altid med begrundelse;
   * *bygget version* (`data/build/`) — deterministisk resultat af
     udtræk + beslutninger + dokumenterede regler.
3. **Facit er sidebilledet** af 1990-udgaven. DB-tekst og OCR-tekst er vidner
   — og kun vidner til *trykket*: databasens rettelser bygger ikke på
   håndskriftet, og håndskriftet er utilgængeligt (KB offline). Trykkets egne
   fejl gengives derfor som trykt og markeres; de rettes ikke.
   Vidnelisten er åben: den bestilte nye OCR (`SRC-PDF2`) indgår som eget
   vidne (`ocr2`) eller erstatter det gamle, afhængigt af målingen i trin 1.
4. **Intet maskinelt match fremstilles som sikkert**, hvis det ikke er det:
   hver kobling har en `match_type` og en `status`.
5. **Proveniens pr. felt**: hver værdi i den byggede version kan føres tilbage
   til kilde (`pdf`, `db`, `ocr_rule:<id>`, `review:<id>`).

## 2. Dataenheder

Den grundlæggende enhed er **posten**: én dags indførsel *eller* én udateret
blok, sådan som trykket afgrænser den. Siden er en separat dimension, fordi
en post kan krydse et sideskift, og en side rummer mange poster. Dagen er ikke
nok som enhed: der er dage med to poster (1844-11 »27« to gange), intervaller
(»17.-18.«) og udaterede blokke.

### 2.1 `almanak_post.csv` — én række pr. post

| Felt | Indhold | Kilde |
|---|---|---|
| `post_id` | `ALM-1840-02-13` for daterede; `ALM-1840-02-13-b` ved 2. post samme dato; `ALM-1845-BAG-01`, `ALM-1860-BAGSIDE-02-01` for udaterede | afledt, stabil |
| `seq` | løbenummer i trykkets rækkefølge (genskaber ordenen) | PDF |
| `year`, `date_start`, `date_end` | ISO; `date_end` ≠ start ved intervaller; tom for udaterede | PDF (+ review) |
| `date_status` | `print` (trykkets dato, kalender-konsistent) · `print_weekday_conflict` · `inferred` · `undated` | regel/review |
| `weekday_print` | trykkets ugedag (MA … SØ) | PDF |
| `position` | `dagsblad` · `trykt_kalendertekst` · `over_trykt` · `under_trykt` · `bagside` · `foran` · `bag` · `indklaebet` | PDF-markører |
| `print_page_start/_end`, `pdf_page_start/_end` | sider (trykt = PDF − 12) | PDF |
| `text` | etableret læsning (Unicode, udgiverens tegn bevaret: `[…]`, `[ɔ: …]`, †, »«, 1/2) | kollation + review |
| `text_status` | `agreed` (DB og rettet OCR enige) · `rule` (afgjort af OCR-regel) · `verified` (afgjort mod billede) · `single_witness` (kun PDF) · `open` | kollation |
| `db_dato` | DB-nøgle, hvis posten har et modstykke | crosswalk |

### 2.2 `almanak_segment.csv` — positioner *inden for* en post

Trykket skifter position midt i en post (»… Hyldest overalt. [I den trykte
almanaktekst:] Sorg«). Segmenter: `post_id, seg, position, text`. Markøren
selv bevares i `text` som udgiverens ordlyd.

### 2.3 `almanak_db_crosswalk.csv` — én række pr. DB-række

`db_dato, post_id, match_type, ratio, status, review_id`

| `match_type` | Betydning | Automatisk accept? |
|---|---|---|
| `same_date` | samme dato, `ratio_loose` ≥ 0,9 | ja |
| `same_date_divergent` | samme dato, ratio < 0,9 (afkortning, sammenlægning) | nej → review |
| `shifted` | teksten står på anden dato inden for ±7 dage | nej → review |
| `swapped` | to DB-rækker har byttet tekst (1855-01-07/12) | nej → review |
| `interval_part` | DB har opløst et trykt interval | ja, hvis begge dele peger på samme post |
| `invalid_date` | `…-00` matchet på tekst | nej → review |
| `db_only` | intet modstykke i trykket (1833-02-16) | nej → review; bliver aldrig del af teksten, højst en annotation (§2.5) |
| `empty` | tom DB-række | ja (ignoreres, logges) |

Omvendt får PDF-poster uden DB-række `db_dato` tom — det er *ikke* en fejl
i den kombinerede version, men et fund om databasen.

### 2.4 `almanak_variant.csv` — det tekstkritiske apparat

Én række pr. forskelssted mellem vidnerne:
`variant_id, post_id, token_start, token_end, witness_readings (JSON: {"ocr": …, "ocr2": …, "db": …}), chosen, basis, rule_id, review_id`.

`basis` ∈ `agreed` · `ocr_rule` · `image` · `db_editorial` (DB har tilføjet
noget, der ikke er trykkets tekst) · `unresolved`.
Apparatet gør det muligt at genskabe begge vidner og at revidere enhver
afgørelse.

### 2.5 `almanak_annotation.csv` — databasens tilføjelser

DB-indhold, som ikke er trykkets tekst (»[=Edmund von Hartig]«, »[Der skal
stå Africa]«, `<brevlink>18080</brevlink>`, `<em>`), flyttes ud af teksten til
`post_id, kind (gloss|correction|letter_link|emphasis), text, source=hca_db, db_timestamp`.
Det bevares, men blandes ikke ind i 1990-teksten.

### 2.6 `almanak_register_ref.csv` — trykkets registre

`ref_id, register (person|work), headword_raw, headword_id, ref_raw, year, day, month,
target (post_id eller blok), flags (uncertain "(?)", not_in_xi "+"), resolution, entity_id`

* `headword_id`: id for registeropslaget (`ALMP0001`, `ALMW0001`). Prototypen findes (`scripts/parse_register.py`, `data/register/`); id'erne er foreløbige, indtil registret er korrekturlæst og OCR'en endeligt valgt.
* `entity_id`: kandidat i projektets egne registre (`Reg…` for personer og
  værker, via Dagbøger XI-opslaget; nye personer markeret »+« får egne id'er).
* `resolution`: `exact` · `ocr_year_corrected` (fx »1833 11.7« → 1855, fordi
  kun 1855 har en post den 11.7 med navnet) · `ambiguous` · `unresolved`.

### 2.7 Udgang til websitet

Som forudset i `docs/data-model/temporal-modelling.md` bliver almanakken en
**søster-tabel til `diary.csv`** (`data/normalized/almanac.csv`) med egne
referencer (`almanac_references.csv`: `post_id, entity_id, entity_label, date, seq, source`).
`references.csv` er side-nøglet (`page_id, vol, page`) og skal **ikke**
overbelastes med almanakposter.

## 3. Matchning

1. **Dato først.** PDF-poster får dato af trykket (år/måned-overskrift +
   dagnummer, kontrolleret med ugedag). DB-rækker matches på `Dato`.
2. **Tekst som kontrol.** Et datomatch accepteres automatisk kun ved
   `ratio_loose` ≥ 0,9. Under det søges teksten ±7 dage; et bedre match giver
   `shifted`/`swapped`, ellers `same_date_divergent`.
3. **Kæder.** Forskydninger kommer i blokke (1844-06-26…30). En blok
   behandles som én review-opgave, ikke fem.
4. **Trykfejl i ugedag** (op til 18 poster) løses ikke maskinelt. Først
   kontrolleres mod sidebilledet, om konflikten er OCR'ens eller trykkets.
   Er den trykkets, får posten trykkets dagnummer og
   `date_status = print_weekday_conflict` permanent — håndskriftet kan ikke
   konsulteres. En sandsynlig dato kan angives som annotation, aldrig som
   `date_start`.
5. **Registerhenvisninger** matches på dato → post, og bekræftes ved at
   navnet (normaliseret, se `scripts/correspondence/name_normalize.py`)
   forekommer i postens tekst. Uden tekstbekræftelse: `ambiguous`.

## 4. Feltprioritering

| Felt | Primær | Sekundær | Regel |
|---|---|---|---|
| Dato, ugedag, rækkefølge, side, position | PDF | DB (dato) | DB-dato bruges kun som kontrol |
| Tekst, enige steder | begge | — | accepteres |
| Tekst, OCR-mønster (tabel i kildeanalyse §3.2) | DB-læsning eller ny OCR | — | regel med id; stikprøvekontrol |
| Tekst, øvrige uenigheder | sidebillede | — | manuel afgørelse i `review/` |
| Udgivertegn `[…]`, markører | PDF | — | DB's version ignoreres |
| Kommentarer, brevlinks | DB | — | kun som annotation |
| Personer, værker | PDF-registre | projektets registre | via crosswalk, aldrig overskrivende |
| Steder | (ingen register) | `build_timeline.Matcher`-lignende kobling | markeres `source=auto` |

**Tilføjelse uden ukritisk overskrivning:** den byggede tekst er *altid*
resultatet af en regel eller en beslutning. Udtræk og DB-tekst forbliver
uændrede ved siden af, og apparatet viser, hvad der er valgt fra.

## 5. Konflikter, usikkerhed og redaktionelle beslutninger

`data/review/decisions.tsv` (append-only):
`review_id, scope (post|variant|crosswalk|register_ref), target_id, decision,
basis (image|editorial), evidence (fx "s. 139, PDF 151"), who, date, note`.

Beslutninger refererer til mål-id'er, ikke til rækkenumre, så de overlever
en genkørsel af udtrækket. Ændres et udtræk så et mål forsvinder, fejler
bygget (se §6).

## 6. Validering af den sammenførte version

| # | Regel | Fejl ved |
|---|---|---|
| V1 | Hver trykt side 1–327 er dækket: hver OCR-linje tilhører en post/blok eller står på en eksplicit ignoreringsliste (kolumnetitler, folier) | ufordelt linje |
| V2 | Datoer stiger monotont inden for en årgang i trykkets rækkefølge, medmindre posten har `print_weekday_conflict` | brud |
| V3 | Trykt ugedag = kalenderens ugedag, ellers `print_weekday_conflict` med review-id | konflikt uden review |
| V4 | Hver DB-række har præcis én crosswalk-række med status ≠ `pending` | manglende/åben |
| V5 | Hver variant har `chosen` og `basis`; `unresolved` er tilladt men tælles og rapporteres | variant uden basis |
| V6 | Ingen tekst fra DB-annotationer i `text` (»[=«, `<brevlink>`, `<em>`) | fund |
| V7 | Hver registerhenvisning peger på en eksisterende post/blok; `ocr_year_corrected` kun hvis entydig | hængende henvisning |
| V8 | Genkollation af den byggede tekst mod hvert vidne: hver resterende forskel har en variant-række | uforklaret forskel |
| V9 | Stikprøve: ≥ 2 % af posterne pr. årgang (min. 5) korrekturlæses mod billedet; fejlrate ≤ 1 pr. 1.000 ord | over tærskel → årgangen gennemgås |
| V10 | Reproducerbarhed: to byg fra samme kilder (sha256) og samme `review/` giver byte-identisk output | afvigelse |
| V11 | Antal: poster pr. årgang og pr. trykt side rapporteres og sammenholdes med forrige byg | uforklaret ændring |
