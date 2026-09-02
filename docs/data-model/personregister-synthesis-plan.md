# Plan: syntese-fil for Personregistret (Dagbøger XI)

> **Status:** Plan, ikke implementeret. Formålet er en pipeline-egnet
> syntesefil over personopslagene A–Å i H. C. Andersens Dagbøger XI
> (Personregister, DSL 1977, spalte 1–796), bygget ved at flette de to
> OCR-tekstlag i `raw/`.
>
> **Forudsætning:** [`ocr-comparison-dagboeger-XI.md`](../../raw/ocr-comparison-dagboeger-XI.md)
> — fil 2 (`dagbog-bd-11-3408_Claus-OCR test ABBYY.pdf`) er den bedre
> kilde til spaltetal; fil 1 (`andersen-hc_dagboeger_11.pdf`) har
> systematisk 1→7 og 9→0-forveksling i registerteksten.
>
> **Afgrænsning (efter aftale):** kun personopslagene A–Å. Stamtavlerne
> (Collin, Drewsen, Stampe, Wulff/Koch, Henriques, Melchior) og det
> øvrige forstof (Forord, Tidstavle, Bibliografi) er **ude af scope**.

## 1. Formatvalg: TSV

**Anbefaling: TSV**, ikke Markdown.

| Kriterium | TSV | MD |
|---|---|---|
| Præcedens i repoet | `data/parsed/*.tsv`, `data/normalized/rejser.tsv` | kun til dokumentation |
| Maskinlæsbar i byggescripts | ja, `csv.DictReader(delimiter='\t')` | nej |
| Felter med komma (navne!) | uproblematisk | — |
| ~14.000 rækker | fint | uegnet |

Markdown-rapporten fra
[`place-categorization-copilot-report.md`](place-categorization-copilot-report.md)
er forbilledet for **dokumentationen**, ikke for datafilen: den model —
en kort resultatopsummering + fuld tabel + et afsnit om vanskelige
tilfælde — genbruges som ledsagende `*-report.md`, mens selve data
leveres som TSV.

**Filplacering** (følger repoets eksisterende lagdeling):

- `data/parsed/personregister_xi_parsed.tsv` — rå udtræk, ét opslag pr. række
- `data/curated/personregister_xi_review.tsv` — delmængde flagget til manuel gennemgang
- `docs/data-model/personregister-xi-report.md` — rapport i copilot-rapportens form

Rå-PDF'erne bliver i `raw/`; `raw/` er kildemateriale, ikke output.

## 2. Kolonneskema

Navngivning følger `data/parsed/*.tsv`-konventionen (nummereret prefix,
så feltrækkefølgen er stabil og selvdokumenterende).

| Felt | Indhold | Eksempel |
|---|---|---|
| `01_entry_id` | Løbenummer, stabilt id | `Per000412` |
| `02_entry_type` | `standardpost` \| `krydshenvisning` \| `underpost` | `standardpost` |
| `03_surname` | Opslagsord (efternavn/navnedel før komma) | `Auerbach` |
| `04_given_names` | Fornavne/tilnavne efter komma, før parentes | `Nina, f. Landesmann` |
| `05_sort_key` | Efternavn-først nøgle, jf. CLAUDE.md-alfabetiseringsregel | `Auerbach, Nina` |
| `06_birth_year` | Fødeår, tom hvis ikke trykt | `1824` |
| `07_death_year` | Dødsår, tom hvis ikke trykt | `1872` |
| `08_year_note` | `ca.`, `d. 1345`, `?`, enkeltårs-tvetydighed | `død-år kun` |
| `09_description` | Biografisk beskrivelse (stilling, relation, sted) | `f. Landesmann, g. 1849 m. Berthold A.` |
| `10_references_raw` | Henvisningsstrengen som trykt | `IV 52 135 283.` |
| `11_references_parsed` | Normaliseret, `bind:spalte` semikolonsepareret | `IV:52;IV:135;IV:283` |
| `12_see_also` | Mål for `se:` / `Se ogsaa:` | `Collin, Augusta` |
| `13_ocr_agreement` | `identisk` \| `afvigende` \| `kun_fil2` | `afvigende` |
| `14_ocr_conflicts` | Konkrete uenigheder fil1/fil2 | `IV 704→104` |
| `15_review_flag` | Tom, eller årsag til manuel kontrol | `talkonflikt` |

PDF-side og trykte spaltenumre i selve registerbindet føres **ikke** som
egne felter — de er opslagsværktøjets egen pagineringsmetadata, ikke
indhold. Det væsentlige er opslagenes egne henvisninger (`10`/`11`) ind i
dagbogsbindene I–X, og dem bevares fuldt ud.

`11_references_parsed` er den vigtigste afledte kolonne: registret henviser
til **bind + spalte** (romertal + tal), og først når det er splittet i
atomare par kan henvisningerne krydskøres mod resten af pipelinen.
Intervaller (`106-07`) ekspanderes til `X:106;X:107`; bemærk den trykte
forkortelsesform, hvor `398-99` betyder 398–399 og `106-07` betyder
106–107.

## 3. Ekstraktionsstrategi

### 3.1 Sideafgrænsning (målt, ikke gættet)

I fil 2 (`dagbog-bd-11-3408_Claus-OCR test ABBYY.pdf`, 445 sider,
0-indekseret):

- side **46** = `PERSONREGISTER` + brugsanvisning (»Vigtigere henvisninger
  er kursiverede. Aa og Å står forrest i alfabetet«)
- side **47** = første opslag (`Åberg`)
- side **444** = sidste opslag (`Ørsted, Pauline – Oettinger`), ingen kolofon efter

Scope er altså **PDF-side 47–444 i fil 2** = 398 sider. Fil 1 er forskudt
med −1 (side 46–443), jf. OCR-rapporten.

### 3.2 Sidegeometri (målt på side 58)

Sidestørrelse 440,65 × 570,5. To spalter:

- venstre kolonne x ≈ 59–218, højre x ≈ 226–384 (skillelinje ved `W/2`)
- kolonnetitel ved y ≈ 41 (fx »Auerbach, Eugen – Augustenborg,
  Louise-Sophie«) — udelades, ren opslagsværktøjs-metadata
- spaltenumre på registerbindets egne sider ved y ≈ 486 (fx `23\n24`) —
  udelades ligeledes; det er registerbindets egen paginering, ikke en
  del af noget opslags indhold

Filter: behold kun blokke med `55 < y0 < 482` (fjerner topmarginens
kolonnetitel og bundmarginens spaltetal); læs venstre kolonne før højre
(samme strategi som `scripts/correspondence/extract_collin_place_index.py`).

### 3.3 Opslagsgenkendelse

Linjebaseret opdeling **virker ikke** — verificeret: efter reflow klumper
»IV 52. auf der Maur, Agatha (1824-72), Med­indehaver…« tre opslag i én
linje, mens »Augustenborg, Prinsesserne af Slesvig-« brydes midt i ét.
Årsagen er den samme som dokumenteret i
`scripts/correspondence/extract_collin_person_index.py`: danske titler er
selv kapitaliserede, og der er ingen font-/vægtforskel at ankre på.

Brug i stedet Collin-scriptets mønster — reflow hele sektionen til én
streng, og ankr på opslagsformen efter afsluttende tegnsætning:

```python
ENTRY = re.compile(
    r'(?:(?<=[.)]\s)|^)'
    r'(?P<head>(?:[A-ZÆØÅÖÜ][\w\'\-]*|auf|von|van|de|d\')'
    r'(?:[ \-][\w\'\-]+)*?,\s)')
```

Prototypen fandt **82 opslag over 3 sider** (≈14.000 i alt over 398
sider) og fanger — i modsætning til Collin-scriptet — også de **udaterede**
opslag (»Arnholz, Frue og Datter, Hem Præstegaard 2.7.1865«, »Assor, S.,
Privatlehrer, dr. phil., Altona«). Det er en reel udvidelse: her er
fødselsår ikke påkrævet, fordi vi ikke skal år-matche, men digitalisere.

Nødvendige efterbehandlinger, alle set i prototypen:

1. **Blødt bindestreg** (`\xad`) fjernes før reflow, ellers brydes
   »Med­indehaver« og »Præste­gaard«.
2. **Overlappende matches** dedupliceres — samme opslag fanges både i sin
   egen og i forrige opslags haleområde.
3. **Falske positiver fra fortsættelseslinjer** (»Nicolai Kirke i
   Flensborg, 1850-54 Superintendent…«) frafiltreres: et ægte opslagsord
   må ikke stå midt i en sætning, der grammatisk fortsætter forrige
   beskrivelse. Heuristik: forkast match hvor `head` matcher et kendt
   stednavn/institutionsled, eller hvor forrige tegn ikke reelt afslutter
   et opslag.
4. **Krydshenvisninger** (`se:` / `Se ogsaa:` / opslag der kun består af
   »X, se: Y«) markeres `02_entry_type=krydshenvisning`, og målet lægges i
   `12_see_also`; de har ingen egne spaltehenvisninger.
5. **Underposter** — linjer der begynder med tankestreg (»– Hendes Søster
   og dennes Børn. VIII 108.«, »– Se ogsaa: Brøndum, Pauline.«) hører til
   det foregående opslag: `02_entry_type=underpost`, arver `03_surname`.

### 3.4 Kursiv (udeladt)

Registrets brugsanvisning nævner at »vigtigere henvisninger er
kursiverede«, men denne vægtning er ikke en del af opgaven her og
udtrækkes ikke — `get_text()` (uden span-/font-flags) er tilstrækkeligt.

## 4. Fletning af de to OCR-lag

Kernen i »syntese«. Sideparring er fastlagt: **fil1-side = fil2-side − 1**
(verificeret stabil, similaritet 0,96–0,998 hele vejen).

Procedure pr. opslag:

1. Udtræk opslag uafhængigt fra begge filer.
2. Par opslag på tværs af filerne via `05_sort_key` + `06_birth_year`
   (Levenshtein-tolerance på navnet, da OCR kan afvige: »Arnesen Kali« vs.
   »Arnesen Kall«).
3. **Tekstfelter** (`03`–`09`): brug fil 2, men flag afvigelser.
4. **Talfelter** (`10`, `11`): brug fil 2 som primær — dokumenteret bedre —
   men kør konfliktdetektion mod fil 1.
5. Sæt `15_ocr_agreement` og fyld `16_ocr_conflicts`.

### Konfliktklasser og håndtering

| Klasse | Eksempel | Handling |
|---|---|---|
| Fil 1 giver ikke-tal, fil 2 tal | `SOS-OO` vs. `398-99` | tag fil 2, ingen flag |
| Fil 2 giver ikke-tal, fil 1 tal | sjælden | tag fil 1, flag `lav` |
| Begge tal, men forskellige | `11` vs. `77` | **flag `talkonflikt`** |
| Begge identiske | — | `identisk`, højeste tillid |

Kun tredje klasse kræver menneskeøjne. I OCR-sammenligningen var der ca.
**113 sådanne segmenter** i hele bindet (stamtavlesider fraregnet) — en
overkommelig manuel gennemgang, og præcis den delmængde der ryger i
`personregister_xi_review.tsv`.

**Plausibilitetskontrol som ekstra net:** registret dækker spalte 1–796
fordelt på bind I–X. Enhver parset henvisning med spaltetal uden for
bindets reelle spalteinterval er en OCR-fejl uanset om begge filer er
enige. Bindenes spalteintervaller kan udledes af Indholdsfortegnelsen og
bruges som hårdt filter — det fanger fejl som `704` for `104`, selv hvor
begge tekstlag skulle være enige.

## 5. Alfabetisering

Følger CLAUDE.md-reglen (efternavn som primær nøgle) og registrets egen
konvention: **Aa og Å står forrest**, og Ø/Ö sorteres sammen. Brug
`Intl.Collator('da')` i frontend og en tilsvarende `locale`-bevidst
nøgle ved TSV-generering; `05_sort_key` gør sorteringen eksplicit i data,
så downstream ikke skal genudlede den.

Bemærk at registret blander danske og udenlandske navne samt
partikelnavne (`auf der Maur`, `von Arnim`, `van Assen`), der er
alfabetiseret på **partiklen** i denne udgave (`auf der Maur` under A) —
den trykte praksis skal bevares i `05_sort_key`, ikke »rettes«.

## 6. Implementeringstrin

1. `scripts/parsers/parse_personregister_xi.py` — udtræk fra **fil 2**,
   skriv `data/parsed/personregister_xi_parsed.tsv`. Genbrug
   blok-/kolonnelogikken fra `scripts/correspondence/extract_collin_place_index.py`.
2. Samme script med `--source file1` — udtræk fra fil 1 til en midlertidig
   fil, alene til fletning.
3. `scripts/parsers/merge_personregister_ocr.py` — parring, konfliktdetektion,
   spalteinterval-validering; skriver de endelige `parsed`- og `review`-filer.
4. Manuel gennemgang af review-filen (~100–150 rækker forventet).
5. `docs/data-model/personregister-xi-report.md` i copilot-rapportens form:
   kort resultat, statistik, uddrag af tabellen, afsnit om vanskelige
   tilfælde.
6. Test i `tests/` der verificerer: rækkeantal stabilt, alle
   `11_references_parsed` inden for gyldige spalteintervaller, ingen tom
   `03_surname`, alle `12_see_also`-mål findes som eget opslag.

## 7. Kendte forbehold

- **Antal opslag er et estimat** (~14.000) ud fra 3 siders stikprøve;
  det reelle tal kendes først efter fuld kørsel.
- **Falske positiver i opslagsgenkendelsen** er den største usikkerhed.
  Trin 6's test »alle `se:`-mål findes som opslag« er en god
  selvkontrol af netop dette.
- **Fil 1 er ikke værdiløs**: den bruges som andenstemme i fletningen,
  selv om den taber på talkvalitet.
- **Stamtavlerne er bevidst udeladt.** Begge OCR-lag fejler groft på dem
  (β-symbolet læses som `P` hhv. `(3`/`/3`), så de kan ikke digitaliseres
  forsvarligt ad denne vej og ville kræve manuel transskription.
