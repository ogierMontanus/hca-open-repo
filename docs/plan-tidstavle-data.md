# Plan: videre med interne og eksterne data omkring Tidstavlen

Status: forslag 2026-10-28 · udføres **lokalt** (se «Forudsætninger») ·
baggrund: [`data-model/tidstavle-ledsagespor.md`](data-model/tidstavle-ledsagespor.md),
[`data-model/tidstavle-krydsforbindelser.md`](data-model/tidstavle-krydsforbindelser.md)

Formålet er det samme som sidens: at binde **hvem · hvad · hvor · hvornår** sammen,
så en læser kan gå fra en dato i dagbøgerne til personer, steder og værker — og
omvendt. Tidstavlen er den hidtil bedste dato↔sted-kilde; planen gør den
(1) konsistent med de øvrige interne kilder og (2) forankret i eksterne autoriteter.

## Forudsætninger og hvad der *ikke* er tjekket

* **SQL-databasen er ikke tilgængelig fra den cloud-session, der skrev planen.**
  Repoet indeholder ingen database (`*.sql`/`*.db` findes ikke). Den kendte kilde er
  MySQL-dumpet `hca_db.sql`, som `scripts/migration/migrate_tidstavle_sql.py`
  forventer i `..\hca_db_export\hca_db.sql` — uden for repoet. Adgang til brugerens
  maskine blev ikke givet i sessionen. Alle SQL-trin nedenfor er derfor **ikke
  kørt**; de er skrevet til at blive kørt lokalt (af dig, eller af en Claude-session
  knyttet til din mappe).
* Hvilken motor den lokale database er (MySQL-dump → Postgres? SQLite-staging?) er
  uafklaret. SQL i planen er ANSI-agtig og må tilpasses. PostgreSQL-skemaet er
  tegnet i `nosql-hca-open-repo` (se `data-model/postgresql-migration.md`).
* Lokale kommandoer følger `CLAUDE.md`: PowerShell, `python` (ikke `python3`).
* Regler der gælder hele planen: faktakontrol via live opslag
  (`.claude/skills/wikidata-verify`), ingen kortfliser fra fjern-server, ingen
  runtime-kald til eksterne tjenester fra siden (eksterne data hentes ved build og
  committes som CSV), nye eksterne links i nyt faneblad
  (`docs/external-links.md`). `mockup/irrelevant/` røres ikke.

## Udgangspunkt (målt)

| Kilde | Indhold | Status i repoet |
|---|---|---|
| `data/HCA_Tidstavler_bind_1-10_ Ver_0.9.xlsx` | 1.745 poster 1805–1875: opholdssted/rejse/begivenhed, trykt kildeside + KB-EPUB-link | Bygget til `mockup/data/timeline.js` (`build_timeline.py`) og vist i kalender, liste, tabel, kort, personsider |
| `hca_db.sql` (udenfor repo) → `data/normalized_v092/timeline*.csv` | 1.446 biografiske begivenheder (DA+EN, 1.444 har `text_en`), 213 emner, 2.087 begivenhed↔emne-links (1.051 begivenheder har emne) | Udtrukket (`migrate_tidstavle_sql.py`), men **ikke brugt af mockup'en** |
| `hcadag-20240911.epub` → `timeline_epub_*.csv` | 168 kondenserede begivenheder + 5 redaktionelle afsnit | Udtrukket; i det væsentlige dækket af xlsx |
| Registeret (`entities.csv`, `places.csv`, `references.csv`) | 10.228 personer, 2.433 steder, 3.708 værker | Intern autoritet; Wikidata-ID kun for 35 værker (`works_wikidata.csv`) |

Overlap xlsx ↔ SQL-tidstavle: 1.109 af 1.445 daterede SQL-begivenheder falder inden
for en xlsx-posts interval, 660 med samme startdato. De to kilder **supplerer** hinanden
(SQL: biografi, emner, engelsk; xlsx: ophold og rejser).

---

## Del 1 — Interne data

### Trin 1.0 — Inventar af den lokale database *(forudsætning for resten)* — **udført 2026-10-28**, se [`data-model/sql-database-inventory.md`](data-model/sql-database-inventory.md)

1. Find `hca_db.sql` (eller den kørende database). Notér motor, version, tegnsæt
   (filen er UTF-8 trods latin-1-header, jf. scriptet).
2. List alle tabeller med rækkeantal. Sammenlign med det, `migrate_*`-scripts og
   `hca_v092_to_csv.py` allerede bruger — **resten er uudnyttet data**.
3. Skriv resultatet i `docs/data-model/sql-database-inventory.md`
   (tabel · rækker · bruges af · mangler i CSV'erne).

Færdig når: der er en tabel over alle tabeller, og hver er markeret «bruges» / «ikke
brugt, relevant for Tidstavle» / «irrelevant».

### Trin 1.1 — ID-hygiejne *(lille, gør først)* — **udført 2026-10-28**

Problem: `build_timeline.py` giver løbende id'er `T0001…`, som kolliderer med alle 1.446
`event_id` i SQL-tidstavlen, og de er ustabile (ændres, hvis en række indsættes i xlsx).

* Skift til stabil nøgle: `TV{bind:02d}{række:04d}` (række = regnearkets fysiske række) plus hash af `(Fra, Til, tekst)`
  som `content_key` (felt `c` i `timeline.js`), så redigerede rækker kan genkendes på tværs af versioner.
* Behold SQL-id'erne `T####` uændret.
* Test i `tests/test_timeline_build.py`: ingen id i `timeline.js` findes i
  `timeline.csv`; ingen dubletter.

### Trin 1.2 — Krydsforbindelse mellem de to tidstavler — **første pas udført 2026-10-28** (`data/curated/timeline_crosswalk.csv`; dækning i [`tidstavle-krydsforbindelser.md`](data-model/tidstavle-krydsforbindelser.md); reviewer-køen er ikke afgjort). **Hård datogrænse 31.12.1875** gælder hele begivenhedsmapningen (`scripts/normalization/event_bounds.py`)

* Byg `data/curated/timeline_crosswalk.csv`:
  `xlsx_id, sql_event_id, match` (`samme_dato` · `indeholdt` · `ingen`), `reviewer`.
  Automatisk første pas på dato (+ tekstlighed for kandidater på samme dag);
  `reviewer`-kolonnen udfyldes af en person for tvetydige par.
* Brug resultatet til:
  * **Engelsk:** `text_en` (1.444) til de SQL-begivenheder, der matcher — så
    `diaries_en.html`/`persons_en.html` ikke viser danske tidstavletekster.
  * **Emner:** de 213 emner (grupper som «Herregårde i Danmark», «Rejser, udland»,
    «Oversættelser») som filter i kalender og kort.
  * **Biografiske begivenheder** (`bookmark_title`, `year_heading`) som en
    «Livet»-aksel over kalenderen.
* Gem uafgjorte par som en synlig kø; undgå at gætte.

Færdig når: hver SQL-begivenhed har et match eller en dokumenteret «ingen», og dækningen
er opgjort i `tidstavle-krydsforbindelser.md`.

### Trin 1.3 — Mål og forbedr navnelinkningen *(mangler i dag: recall)*

* Træk en stratificeret stikprøve på ca. 300 poster (pr. bind, pr. type:
  rejse/ophold/begivenhed). Annotér *alle* personer, steder og værker i dem manuelt
  → `data/curated/timeline_gold.csv`.
* Mål precision og recall pr. entitetstype; tilføj `tests/test_timeline_gold.py`, der
  fejler, hvis precision falder under en tærskel.
* Forbedringer i prioriteret rækkefølge:
  1. Stedaliaser (`Genua`, `Civita vecchia` …) — udtræk de hyppigste ulinkede ord med
     `build_timeline.py --report` og afklar hvert: manglende i registeret, ny alias
     eller bevidst ulinket.
  2. Personer: titelord (grev, hertug, fru) som kontekst til at afgøre homonymer;
     krydstjek med `ner_page_grounding.csv`.
  3. Værker: genkend titler uden `»«`-citationstegn kun mod eksakt værktitel.
* Gem metode og konfidens pr. link i data (se trin 1.7), ikke kun resultatet.

### Trin 1.4 — Redaktionelle køer fra krydsforbindelserne

Hver kø er en CSV i `data/curated/` med kolonner for *forslag*, *beslutning*, *beslutter*:

| Kø | Størrelse | Kilde |
|---|---|---|
| Sted-afvigelser (dagbogsside vs. tidstavle) | 79 | `tidstavle-krydsforbindelser.md` #1 |
| Mulige manglende persontags | 102 (+ 50 uden dagbogsside) | #2 |
| Værker uden dagbogsforbindelse ±60 dage | 29 af 49 | #6 |

En afgjort post rettes i registret (ikke i tidstavlen), og tidstavlen forbliver den
trykte kilde, som den er.

### Trin 1.5 — Dagbogens huller og temporal modellering

* Skriv `scripts/qa/report_timeline_gaps.py`: dage/perioder med opholdspost men uden
  dagbogsside (5.509 af 10.159 dage), grupperet pr. bind og sammenholdt med
  `report_untranscribed_pages.py`. Skel mellem «dagbog mangler (kilde)» og «side
  ikke transskriberet (vores hul)».
* Efter `data-model/temporal-modelling.md`: tidstavle-datoer er *begivenhedsdatoer*
  (entitetens), ikke *omtaledatoer* (dagbogssidens). Lav
  `data/normalized/entity_dates.csv` (`entity_id, type, date_from, date_to,
  source_ref`) fra de ca. 150 personer og 49 værker, og aktivér først derefter
  «Begivenhedsdatoer»-knappen i `diaries.html`. Aktivér den ikke før datamodellen
  findes.

### Trin 1.6 — Frontend-opfølgning (kan køre parallelt)

* `place.html`/`work.html` (+ `_en`): genbrug `TimelineWire.mountEntity(el, 'p'|'w', rid)`.
* Rutelaget: pile/retning, markér opholdssteder, og bygger `?routes=`-dybe links fra
  personsiden («se Jenny Linds rejser på kortet»).
* Krydscheck mod `rejser.tsv` (454 af 601 ankomster matcher) efter at stednavne er
  normaliseret via aliaser (Hamborg ↔ Hamburg).
* Tidslinje-layout i `diaries.html` (`?layout=timeline`, jf. `HANDOVER.md`) som en
  fjerde visning over de samlede tidstavler, når trin 1.2 er færdigt.

### Trin 1.7 — Flyt linkningen ind i databasen *(når 1.0 er afklaret)*

Tabeller (skitse; afstem med `nosql-hca-open-repo`-skemaet):

```sql
timeline_entry   (entry_id PK, source, volume, date_from, date_to, date_prec_from,
                  date_prec_to, kind, text_da, text_en, kb_page, kb_url, content_key)
timeline_mention (entry_id FK, entity_id, entity_type, span_start, span_end,
                  method, confidence, reviewed_by, reviewed_at)
timeline_subject (subject_id PK, name_da, name_en, group_da, group_en)
timeline_entry_subject (entry_id FK, subject_id FK)
```

Så kan krydsforbindelserne køres som forespørgsler i stedet for engangsscripts, fx:

```sql
-- Dage med opholdspost men uden dagbogsside
SELECT d::date FROM timeline_entry e
JOIN generate_series(e.date_from, e.date_to, interval '1 day') d ON TRUE
LEFT JOIN diary_page p ON p.page_date = d::date
WHERE e.kind IN ('ophold','rejse') AND p.page_date IS NULL;

-- Personer nævnt i tidstavlen i en periode, men ikke tagget på siderne i perioden
SELECT m.entity_id, e.entry_id FROM timeline_mention m
JOIN timeline_entry e USING (entry_id)
WHERE m.entity_type = 'person'
  AND NOT EXISTS (SELECT 1 FROM diary_page p
                  JOIN diary_ref r USING (page_id)
                  WHERE r.entity_id = m.entity_id
                    AND p.page_date BETWEEN e.date_from AND e.date_to);
```

`build_timeline.py` ændres til at *læse* fra databasen (eller en CSV-eksport af den) og
skrive den samme `timeline.js` — frontend uændret. CSV forbliver kilde til sandhed,
indtil `postgresql-migration.md`'s beslutning er truffet.

---

## Del 2 — Eksterne data

Princip: først den del af registeret, Tidstavlen faktisk berører
(≈ 150 personer, ≈ 630 steder, 49 værker), derefter resten. Det giver en lille,
fuldt verificérbar mængde at lære på.

### Trin 2.1 — Autoritets-ID'er (Wikidata, VIAF, GeoNames)

* Mål: `data/curated/persons_authority.csv`, `places_authority.csv` med
  `rid, wikidata, viaf, geonames, verified_via, verified_on, note`.
* **Procedure pr. post** (`wikidata-verify`): live opslag, læs Q-nummeret fra
  resultatet, bekræft navn *og* levetid/type/land; ved steder bekræft
  `Category` (registerets 13 værdier) mod Wikidata-klasse/GeoNames-feature-code;
  skriv aldrig et ID fra hukommelsen.
* Kandidat-værktøj: udvid `scripts/parsers/wikidata_lookup.py` (som kun
  *foreslår*) til personer og steder; output til en review-CSV, aldrig direkte til
  `curated/`. Menneskelig bekræftelse før promovering.
* Steder: koordinater findes allerede for 2.421 af 2.433 — målet er *identitet*
  (GeoNames/Wikidata) og **historiske navnevarianter** (Genua/Genova, Neuchâtel
  (By/Kanton), Slesvig By/Hertugdømme), ikke flere koordinater.
* Færdig-kriterium: ≥ 95 % af de tidstavle-berørte poster har bekræftet ID, resten
  er markeret «ikke fundet» med begrundelse.

### Trin 2.2 — Eksterne dato-/opholdsdata som krydstjek

* Sammenlign tidstavlens ophold med eksterne kilder for Andersens liv
  (Wikidata-udsagn om bopæl/rejser; H.C. Andersen Centrets egne publikationer).
  Brug til at *finde afvigelser*, ikke til at overskrive: tidstavlen er den trykte
  kilde, og afvigelser lægges i en kø som i trin 1.4.
* Breve: undersøg, om H.C. Andersen Centret/KB udstiller breve med dato og sted
  (der findes allerede Collin-brevspor under `data/curated/collin_*`). Ligger der
  maskinlæsbare brevdata, kan «breve skrevet i perioden/på stedet» blive et fjerde
  ledsagespor. **Ikke undersøgt endnu** — første skridt er at afklare adgang og licens.

### Trin 2.3 — Kilde-links (KB) og facsimiler

* De 1.745 poster peger på 92 forskellige EPUB-sider hos Det Kgl. Bibliotek.
  Kør et sjældent link-check (HEAD, høflig rate) og gem status i
  `data/curated/kb_link_status.csv`; lad `build_timeline.py` udelade døde links
  frem for at vise dem.
* Overvej at afstemme med `kb_diary_links.csv` (facsimile pr. dagbogsside), så en
  læser kan gå fra tidstavlepost → dagbogsside → facsimile.

### Trin 2.4 — Licens, proveniens og policy

* For hvert eksternt datasæt: kilde-URL, licens, hentedato, version i
  `data/curated/EXTERNAL_SOURCES.md`. Wikidata er CC0; GeoNames CC BY — kræver
  kreditering på `om.html` («Vores kilder»).
* Ingen runtime-kald: alt hentes lokalt og committes. Dermed forbliver
  CSP'en (`docs/security.md`) uændret.

---

## Rækkefølge og afhængigheder

```
1.0 inventar ─┬─► 1.7 database
              │
1.1 ID-hygiejne ─► 1.2 krydsforbindelse ─► (engelsk · emner · «Livet»-aksel)
1.3 gold-standard ─► 1.4 køer ─► 1.5 huller + entity_dates ─► «Begivenhedsdatoer»
2.1 autoritets-ID'er ─► 2.2 krydstjek · 2.3 link-check
1.6 frontend (parallelt, afhænger af 1.2 for tidslinje-layoutet)
```

Anbefalet første uge: **1.1 → 1.0 → 1.2**. Det er småt, afklarer databasen og
frigør de to største gevinster (engelsk tekst og emnefilter) uden at røre eksterne
kilder. Del 2 starter med en pilot på ca. 50 personer og 50 steder for at måle
tid pr. post, før hele mængden planlægges.

## Åbne spørgsmål til dig

1. Hvilken database-motor ligger lokalt, og hvor ligger `hca_db.sql`?
2. Skal den engelske tidstavletekst (SQL `text_en`) vises i `_en`-siderne, selv hvor
   den kun matcher en xlsx-post ca.? (Skal der være en redaktionel gennemgang først?)
3. Hvem afgør redaktionelle køer (trin 1.4) — og er registerrettelser tilladt ud fra
   en tidstavle-uenighed, eller skal de bekræftes mod dagbogsfacsimilen?
4. Er der licens-/samarbejdsaftaler (SDU/KB) at tage hensyn til ved at hente
   eksterne brevdata (trin 2.2)?

## Se også

* [`data-model/events-research-basis.md`](data-model/events-research-basis.md) og
  [`data-model/events-data-audit.md`](data-model/events-data-audit.md) — begivenhedsmodel
  og datarevision. Revisionens §8 (næste skridt) bygger på trin 1.0 og 1.2 her.
