# Inventar af SQL-databasen `hca_db` (plan trin 1.0)

Status: målt 2026-10-28 · hører til [`../plan-tidstavle-data.md`](../plan-tidstavle-data.md)
trin 1.0 og [`events-data-audit.md`](events-data-audit.md) §7 spørgsmål 1 ·
genskabes med `python scripts/qa/sql_inventory.py` (valgfrit `--json ud.json`)

## 1. Kilden

| | |
|---|---|
| Fil | `raw/hca_db.sql` (66.511.734 byte; **gitignoreret** via `.gitignore`, ikke i git) |
| Motor | MySQL 5.7.24, dumpet med phpMyAdmin 5.1.2 den 29. juni 2023 (`Database: hca_db`) |
| Tabeller | 80 (MyISAM; 1.434 `INSERT`-blokke; 167.434 rækker i alt) — 56 egne tabeller + 24 WordPress-tabeller |
| Tegnsæt | Deklareret `latin1` i `CREATE TABLE`, men indholdet er UTF-8 (`SET NAMES utf8mb4`); læs filen som `utf-8` |
| Indeholder | det ældre `andersen.sdu.dk`-system: værkregister (`vaerktitler`), bibliografi, breve (13.585), tidstavle, almanak |

**Afvigelse fra planen:** planen (og `migrate_tidstavle_sql.py`) forventer
`..\hca_db_export\hca_db.sql`; filen ligger faktisk i `raw/hca_db.sql`. Brug
`--sql raw\hca_db.sql`. `sitetekster` er tom; `sted`, `arrangement` og `metaoplysninger`
har 1–2 rækker.

## 2. Resultat i korte træk

* **Bruges i dag af 8 af 80 tabeller:** `tidstavle_aar/_data/_emner/_rel`
  (`migrate_tidstavle_sql.py`), `brev`, `brev_person`, `person`
  (`match_collin_letter_ids.py`) og `almanak` (`almanak/scripts/analysis/extract_db.py`).
* **`vid`-crosswalken findes ikke som tabel.** Databasen har intet felt med `Reg…`-id'er.
  `vid` er nøglen til det ældre værkregister, og tabellen **`vaerktitler`**
  (`ID, VID, TID, Titel, TitelgruppeID`; 3.916 rækker, 1.508 forskellige `vid`)
  oversætter `vid` → værktitler (`TitelgruppeID = 15` er hovedtitlen, én pr. `vid`;
  de øvrige er oversættelsestitler: *Dryaden · Die Dryade · The Dryad …* for `vid=178`).
  `Reg…` skal derfor bygges **via titel**, ikke slås op.
* **Titelmatch `vid` → `Reg…`** (hovedtitel, normaliseret: små bogstaver, uden
  tegnsætning og afsluttende parentes) mod de 3.708 værker i
  `data/normalized/entities.csv`:

  | Mængde | 1 kandidat | 0 | 2+ |
  |---|---:|---:|---:|
  | De **196** `vid` i `timeline.csv` | **149** | 35 | 12 |
  | Alle 1.508 `vid` i `vaerktitler` | 248 | 1.235 | 25 |

  Eksempler: `vid=401` *Improvisatoren* → `Reg001737`; `vid=178` *Dryaden* →
  `Reg001003`. De 35 uden match er mest stavevarianter (*Dykker-Klokken* ↔
  *Dykkerklokken*, *Klods-Hans*, *Et Blad fra Himlen*) og kræver aliasliste eller
  manuel afgørelse. De 1.235 uden match er ikke fejl: tabellen dækker også
  oversættelser, bibliografisk materiale og andre ikke-registerværker.
  (Dette er en *første måling*; den er ikke et færdigt crosswalk — trin 1.2.)
* **Største uudnyttede fund for Tidstavle/begivenheder:**
  `bibliografi` + `bibliografi_rel` (udgivelsesdatoer for værker, koblet til `vid`),
  `brev` + `brev_person` (13.585 breve med dato — et fjerde ledsagespor),
  `dagbog` (dato → KB-facsimile), `droemme` (96 daterede drømme),
  `tekststed`/`motiv*` (tekststeder med DSL-reference).

## 3. Alle tabeller

Signatur: **B** = bruges af et script i repoet · **R** = uudnyttet, relevant for
Tidstavle/begivenheder · **I** = irrelevant for Tidstavle/begivenheder.

### 3a. Tidstavle

| Tabel | Rækker | Status | Bruges af / begrundelse |
|---|---:|:-:|---|
| `tidstavle_data` | 1.446 | B | `migrate_tidstavle_sql.py` → `timeline.csv` |
| `tidstavle_aar` | 65 | B | samme → `year_heading_*` |
| `tidstavle_emner` | 213 | B | samme → `timeline_subjects.csv` |
| `tidstavle_rel` | 2.088 | B | samme → `timeline_subject_links.csv` (1 tom række filtreres → 2.087) |

### 3b. Værker og bibliografi (`vid`)

| Tabel | Rækker | Status | Begrundelse |
|---|---:|:-:|---|
| `vaerktitler` | 3.916 | **R** | **`vid` → titler** (se §2); grundlag for `vid` → `Reg…` via titel |
| `vaerktitler_genre` | 2.986 | R | genre pr. `vid` (da/en); kan afstemme `genre_h2`/`form_h3` |
| `vaerktitler_bibliografi` | 28 | R | titelgruppenavne (`TitelgruppeID` → navn; forklarer 15 = hovedtitel) |
| `vaerktitler_url` | 791 | R | eksterne links pr. `vid` (ADL m.fl.) — kilde til trin 2.3 |
| `vaerktitler_manuskripturl` | 55 | R | manuskriptlinks pr. `vid` (tilblivelse, jf. audit §2B) |
| `vaerktitler_dslkommentar` | 172 | I | DSL-kommentarlinks (side + `vid`); lav værdi for tid |
| `kbeventyrkode` | 172 | I | eventyrkoder (`ek2`…) pr. `vid` |
| `bibliografi` | 16.301 | **R** | `UdgivDato` sat på 16.283 (dag/måned/år, `00`-pladsholdere); `UdgivStedID` næsten altid 0 → sted mangler; kilder `hcac` 9.232, `aaj1/2/4`, `bfn`, `imc` … Grundlag for **udgivelsesbegivenheder** |
| `bibliografi_rel` | 5.013 | **R** | `BibliografiID` ↔ `VID` med relation (*førsteudgivelse af* 1.510, *del af* 1.369, *oversættelse af* 206, *anbefalet udgave af* 904, *JdMs nudanske digtudgave af* 917 …). **Eneste strukturerede udgivelse→værk-forbindelse** |
| `bibliografi_genre` | 5.139 | I | genre pr. bibliografipost |
| `bibliografi_person` | 209 | R | person ↔ bibliografipost; `RelationType` (set: *forfatter*) |
| `bibliografi_bibtekst_e` | 31 | I | engelsk bibtekst |
| `bibliografi_konference` | 94 | I | konferencebind/kapitler |
| `konferencebog_kapitel_rækkefølge` | 13 | I | |
| `resumeer` | 26 | I | resuméer |
| `tekster` | 341 | I | tekstuddrag pr. bibliografipost |
| `tekststed` | 693 | R | tekststeder pr. `vid` (da/en, nøgleord, `DSL_EVENT_ref` på 661) — knytter værk til sted i teksten |
| `motiv` | 123 | I | motivkatalog |
| `motiv_rel` | 114 | I | |
| `motiv_tekststed` | 1.847 | I | motiv ↔ tekststed |
| `metaoplysninger` | 1 | R | `ProdStart`/`ProdSlut` (tilblivelse) — kun 1 række, begge `0000-00-00`; ingen reel data |
| `billeder` | 193 | I | billeder pr. `vid` (skoleopgaver m.m.) |
| `billedsamlinger` | 9 | I | |
| `citater` | 26 | I | |

### 3c. Breve

| Tabel | Rækker | Status | Begrundelse |
|---|---:|:-:|---|
| `brev` | 13.585 | B | `match_collin_letter_ids.py`. `Dato` 1807-02-09 – 1932-12-23 (139 uden dato, 231 med `DatoRange`); `Lokation` er **`Ukendt` (10.364) eller tom (3.069)** i 99 % — stedsdata er svag |
| `brev_person` | 27.637 | B | afsender/modtager pr. brev (`Relation`) |
| `person` | 676 | B | breve-persondatabasen (`ID` = `PersonID`), fødsels-/dødsdato; bruges kun til match |
| `brevperson` | 2.018 | R | personer nævnt i breve (`PersID`, titel, fødsels-/dødsdato, hjemland, biografi); forholdet til `person` er ikke afklaret — kandidat til personafstemning |
| `brevudgave` | 20.186 | R | brev ↔ udgave/herkomst (hvilken trykt udgave har brevet) — kobling til Collin-sporet |
| `brevherkomst` | 178 | R | kataloget over udgaver/herkomster (`brevudgave.HerkomstID`) |
| `brevtekst` | 13.907 | I | brevtekster (rettigheder; ikke relevant for dato/sted) |
| `brevmetatekst` | 13.586 | R | metatekst pr. brev (muligt sted/datoafsæt i fritekst) |
| `brevnote` | 7.686 | I | noter |
| `brev_bibid` | 11.907 | R | brev ↔ `bibliografi` (hvilken kilde nævner brevet) |
| `brev_kategori` / `brevkategori` | 1.328 / 5 | I | |
| `brevappetizers` | 145 | I | |
| `personadresser` | 662 | I | adresser til nutidige personer (persondata — **må ikke udgives**) |
| `personkonference` | 50 | I | konferencedeltagere |
| `person_authuser` | 37 | I | **brugerkonti** (e-mail, brugernavn, IP) — følsom, ikke til repoet |

### 3d. Dato-/kalenderkilder

| Tabel | Rækker | Status | Begrundelse |
|---|---:|:-:|---|
| `almanak` | 5.163 | B | `almanak/scripts/analysis/extract_db.py` (Andersens almanak-notater 1833-02-02 – 1873-06-22; ikke i git, se `almanak/README.md`) |
| `dagbog` | 352 | R | `Dato` → KB-dagbogs-URL (`DiaryEntryByDate.xsql`); kandidat til `kb_diary_links.csv`-afstemning (plan 2.3) |
| `droemme` | 96 | R | daterede drømme (`DroemDato`, `DroemKilde`, `DroemSted`) — små daterede begivenheder med dagbogskilde |
| `arrangement` | 2 | I | forskningsarrangementer |
| `wp_hca_dk_event_list` | 9 | I | arrangementer 2015 (Folkeuniversitet) — ikke Andersens liv |

### 3e. Referencetabeller og drift

| Tabel | Rækker | Status | Begrundelse |
|---|---:|:-:|---|
| `landekode` | 238 | R | ISO-landekoder (`Kode`, `Kode3`, da/en) — nyttig til stedskategori/land |
| `sprog` | 58 | R | sprogtabel (`ISO-639-1`) — nøgle til `SprogID` i `bibliografi`/`vaerktitler_url`; kan afstemme `work_languages.csv` |
| `sted` | 1 | I | kun forlaget C.A. Reitzel; `bibliografi.UdgivStedID` peger næsten aldrig herpå |
| `links` | 159 | I | websteds-links |
| `nyheder` | 118 | I | nyheder |
| `sitetekster` | 0 | I | tom |
| `mailudsending` | 2.112 | I | e-mailudsendelse (persondata) |
| `sentemails` | 43 | I | sendte e-mails (persondata) |

### 3f. WordPress (`wp_hca2_*`, `wp_hca_dk_*`) — alle **I**

Indhold/administration af de to WordPress-sites, ikke forskningsdata. Bemærk at
`*_users`, `*_usermeta`, `*_comments` og `*_options` indeholder konti og
adgangsoplysninger og **aldrig** må eksporteres til repoet.

| Tabel | Rækker | | Tabel | Rækker |
|---|---:|---|---|---:|
| `wp_hca2commentmeta` | 0 | | `wp_hca_dk_commentmeta` | 0 |
| `wp_hca2comments` | 0 | | `wp_hca_dk_comments` | 2 |
| `wp_hca2links` | 0 | | `wp_hca_dk_links` | 0 |
| `wp_hca2options` | 403 | | `wp_hca_dk_options` | 224 |
| `wp_hca2postmeta` | 827 | | `wp_hca_dk_postmeta` | 645 |
| `wp_hca2posts` | 319 | | `wp_hca_dk_posts` | 649 |
| `wp_hca2terms` | 11 | | `wp_hca_dk_terms` | 5 |
| `wp_hca2term_relationships` | 47 | | `wp_hca_dk_term_relationships` | 31 |
| `wp_hca2term_taxonomy` | 11 | | `wp_hca_dk_term_taxonomy` | 5 |
| `wp_hca2usermeta` | 27 | | `wp_hca_dk_usermeta` | 170 |
| `wp_hca2users` | 1 | | `wp_hca_dk_users` | 8 |
| | | | `wp_hca_dk_termmeta` | 0 |
| | | | `wp_hca_dk_event_list` | 9 (se 3d) |

## 4. Konsekvenser for planen

1. **Trin 1.2 (krydsforbindelse):** `vid`→`Reg…` kan bygges som kandidatmatch på
   `vaerktitler`-hovedtitler (149 af de 196 `vid` i tidstavlen har straks én
   kandidat). De 12 med flere kandidater og de 35 uden skal i en redaktionel kø.
2. **Udgivelsesbegivenheder:** `bibliografi.UdgivDato` + `bibliografi_rel` (*førsteudgivelse
   af*, 1.510 `vid`) giver en struktureret udgivelsesdato pr. værk — langt bedre end de
   ~77 heuristiske poster i SQL-tidstavlen (audit §3). Sted mangler (`UdgivStedID` = 0).
3. **Breve:** `brev` har dato for 13.446 breve, men sted for under 1 % — brevsporet
   bliver et *dato-/person*spor, ikke et stedsspor, medmindre `brevmetatekst` kan
   udnyttes.
4. **Sikkerhed:** `person_authuser`, `mailudsending`, `sentemails`, `personadresser`
   og alle WordPress-bruger-/indstillingstabeller skal forblive uden for repoet.
   `raw/hca_db.sql` er gitignoreret — behold det sådan.
