# Crowdsourcing — identifikation af flygtigt omtalte personer

Status: **prototype** · 2026-10-29 · branch `crowdsource-ui`

Mange af de personer, Andersen nævner i dagbøgerne, står i Topsøe-Jensens
register med et efternavn og en enkelt linje — nogle gange med et »(?)« som
redaktørerne selv satte. Slægtsforskere og lokalkendte kan ofte gøre det, vi
ikke kan: sætte fornavn, årstal og sted på. Dette dokument beskriver
prototypen, der gør det muligt — og hvorfor den er bygget, som den er.

Hurtig start (til test med én slægtsforsker): [§10](#10-kør-prototypen).

| Del | Fil |
|---|---|
| Arbejdskø (browse og filtrér) | `mockup/crowd.html`, `js/crowd-browse.js` |
| Bidragsformular | `mockup/crowd-contribute.html`, `js/crowd-form.js` |
| Redaktionens gennemgang | `mockup/crowd-review.html`, `js/crowd-review.js` |
| Indgang fra personsiden | `js/crowd-link.js` (på `persons.html?reg=…`) |
| Kategorier, felter, grænser (én kilde) | `scripts/crowdsource/taxonomy.py` |
| Bygger køen | `scripts/build_mockup/build_crowd_queue.py` (trin **4g**) |
| Validering | `scripts/crowdsource/validate.py` ⇄ `mockup/js/crowd-validate.js` |
| Lager + review-regler | `scripts/crowdsource/store.py` ⇄ `mockup/js/crowd-store.js` |
| Server (valgfri) | `scripts/crowdsource/server.py` |
| Overdragelse til autoritativ data | `scripts/crowdsource/export_approved.py` |

---

## 1. Principper

1. **Registret overskrives aldrig.** Et bidrag er en påstand med kilde,
   sikkerhedsgrad og ophavsperson, lagt *ovenpå* det trykte register — samme
   princip som [`person-editorial-emendations.md`](data-model/person-editorial-emendations.md)
   og projektets regel *originaldata må aldrig gå tabt, kun suppleres*.
2. **Ingen oplysning uden kilde.** Hvert felt peger på mindst én kilde; en
   »sikker« eller »sandsynlig« påstand kræver en kilde, der ikke blot er
   personlig viden. Et dokumenteret *negativt* fund (»søgt uden resultat«) er
   et fuldgyldigt bidrag.
3. **Intet går ind uden en redaktør.** Hvert felt godkendes, rettes eller
   afvises for sig. Først efter godkendelse kan data forlade bidragslageret.
4. **Genbrug frem for opfind.** Person-id'er, sikkerhedsgrader, kildekoder,
   entitetstype-gate, nationalitet, køn, erhverv, dagbogssider, KB-faksimile,
   facet-motor og CSP-regler er alle de eksisterende (§2).
5. **Dagbogssiderne duplikeres ikke.** Grænsefladen *linker* til siden — til
   den daterede post, hvor efternavnet findes, og til KB's faksimile.
6. **Motivation uden at trivialisere.** Mærker gives for godkendt, kildebelagt
   kvalitet — aldrig for hastighed eller antal (§7).

## 2. Hvad repoet allerede vidste — og hvad der er genbrugt

| Eksisterende konvention | Hvor den bruges nu |
|---|---|
| Person-id `Reg…` (`entities.csv`, `persons.html?reg=`, `references.csv`) | Eneste person-nøgle i hele laget. Crosswalk til `PER…`-id'erne i `6-PERSON-V0.97(5).xlsx` beregnes ved eksport (§6) |
| `person_entity_types.tsv` (`29_entityType`): krydshenvisning/familie/firma/gruppe/dyr/»Hans Søster« | Gate: kun enkeltpersoner kommer i køen (samme loader som `build_persons_extra.py`) |
| Nationalitet (`person_ethnic_descriptors.csv`, leading), køn (`person_gender.csv`, »Endnu ubestemt«), erhverv (`person_role*.csv`) | Definerer hullerne »nationalitet/køn/erhverv ukendt« — samme data som facetterne på `persons.html`, så de to sider ikke kan blive uenige |
| Emendationsmodellen: `certain / probable / proposed`, `match_surname` + `match_refs`, `original` som vagt, `notes` obligatorisk, kildekoder | Sikkerhedsgrader, eksportformat, `guard`-kolonnen, ny kildekode `CROWD` |
| Efternavn+sidehenvisning som stabil nøgle (`person-master-files.md`) | `match_refs` = `II:422;IV:127`-signatur i eksporten |
| Enriched-data-konventionen (`info-block--enriched` + tag *tilføjet*, `external-links.md` §2a) | Godkendte bidrag og søgehjælp på person- og bidragssiderne |
| Eksterne links: nyt faneblad, `noopener noreferrer`, ↗ + `.sr-only` (`external-links.md`) | Alle links til KB, kilder og søgninger; interne links åbner i samme faneblad |
| `FacetEngine`, `HcaFilter`, aktive filter-chips, mobilfilter | `crowd.html` bruger dem uændret |
| Dagbogsindeks (`DIARY_REFS/META`, `diary-pages/Pag….html`, `kb_diary_links.csv`) | Kontekst-links |
| Alfabetisering efter efternavn, `Intl.Collator('da')` (`CLAUDE.md`) | Standardsortering i køen |
| Ingen CDN, ingen inline-handlers, `connect-src 'self'` (`security.md`, `test_csp_ready.py`) | Alle nye sider overholder det; `/api/crowd/` er same-origin |
| CSV/JSON uden database (`october-pipeline.md`) | Bidragslageret er JSON-filer, ét pr. bidrag |

## 3. Kategorier

### 3.1 Dokumentationsniveau — hvor meget siger registret selv?

Tre uafhængige *ankre* i den trykte post:

* **N** et udskrevet **fornavn** (ikke blot forbogstaver eller en titel som »Mrs.«),
* **L** et **årstal** (fødsel eller død) i parentesen efter navnet,
* **D** en **beskrivelse** på mindst to ord (»Tigger.« tæller ikke).

| Niveau | Ankre | Eksempel | Antal i køen* |
|---|---|---|---:|
| Dokumenteret | 3 | `Aabye, Johan Peter (1818–1880)` + beskrivelse | 181 (kun fordi registret er i tvivl) |
| Delvist dokumenteret | 2 | `Abbott, John` — »Engelsk Ingeniør i Indien.« | 1.266 |
| Fragmentarisk | 1 | `Åberg` — »Svensk rejsende, Italien 1834.« | 818 |
| Navn alene | 0 | `Aaberg` — »Tigger.« | 20 |

\* ved byggedato; køen tæller **2.285** af 8.825 enkeltpersoner med dagbogsomtale
(10.108 enkeltpersoner i alt). Dokumenterede poster står ikke i køen, men kan
rettes fra deres personside.

### 3.2 Flygtig omtale

Et tilfælde er *flygtigt*, hvis navnet står på **højst 2 dagbogssider** og
personen har **højst ét anker**. Det er en egen dimension (filter »Flygtig
omtale«, 731 poster) — den sværeste og for forskningen mest værdifulde gruppe.
Grænsen er `FLEETING_MAX_MENTIONS` i `taxonomy.py`. Antal omtaler kan også
filtreres for sig (1 / 2–3 / 4+).

### 3.3 Manglende oplysninger

Reglerne står i `classify()` i `build_crowd_queue.py` (enhedstestet i
`tests/test_crowd_queue.py`); hver er koblet til de formularfelter, den
inviterer til. En post kan have flere.

| Hul | Regel | Poster |
|---|---|---:|
| Hvem er personen? | højst ét anker | 838 |
| Fornavn mangler | kun efternavn eller forbogstaver/titel | 1.368 |
| Fødselsår / Dødsår mangler | intet (hhv. intet) årstal i etiketten; håndterer `(1835–?)`, `(død 1873)`, `(f. 1812)` | 1.397 / 1.529 |
| Tynd/manglende beskrivelse | under to ord | 253 |
| Erhverv ukendt | ingen rolle i `person_role*` (restkategorien »Endnu ukategoriseret« tæller ikke) | 489 |
| Nationalitet ukendt | ingen *leading* nationalitet | 1.922 |
| Køn ubestemt | »Endnu ubestemt« | 10 |
| **Registret er selv i tvivl** | `(?)`, *maaske, muligvis, formentlig, usikker, misforstaaet, enten, evt.* | 262 |

»Registret er selv i tvivl« er den bedste slags hul: registret stiller selv
spørgsmålet (jf. *Oesterling → Osterley* i emendationsdokumentet), og et
bidrag kan besvare det. Poster med dette hul er i køen, uanset niveau.

### 3.4 Formodet land og lokalitet — og hvad det bygger på

Alle 2.285 poster får en formodning, rangeret efter styrke; **grundlaget**
vises og kan filtreres, så ingen kan tage en pejling for en oplysning:

1. **Nationalitet** i registrets beskrivelse (leading-match, via
   `nation_place_labels_da.csv` → `steder_country_to_nation_da.csv`; dobbelt-
   tilhørende nøgler som *slesvigsk* giver intet land) — 337 poster.
2. **Sted i beskrivelsen** — et entydigt stednavn (by, ø, region, land) fra
   stedregistret findes som helt ord i teksten (»Hotelvært i Toledo«); genitiv-s
   fjernes (*Københavns*) — 824 poster.
3. **Sted på samme dagbogsside** — det sted, siden selv knyttes til
   (`DIARY_META.pl`: første stedpost på siden; i praksis næsten altid hvor
   Andersen var) — 1.124 poster.

Landet er det moderne landenavn fra `places.csv`. Lokaliteten er den, der
gav det mest specifikke grundlag. En lokalekspert kan skrive sine områder i
profilen og få dem som genveje i køen.

**Omtaledato.** Hver omtale har sidens dato (`diary.csv`; 1825–1875) og, hvor
efternavnet findes som helt ord i en dateret post, ankeret til netop den post
(`diary-pages/Pag….html#d1872-05-19`, 3.174 af 5.607 omtaler). Filtre: år fra–til
og årti.

## 4. Datamodel for et bidrag

Ét JSON-dokument pr. bidrag (`schema: hca-crowd-submission/1`):

```
id                 CS-ÅÅÅÅMMDD-xxxxxx
person_id          Reg0030030                        ← registrets eget id
person_label       som registret stod ved indsendelsen
register_snapshot  {label, description, surname, refs_signature, area, doubt, level, gaps}
identification     {status, summary, same_as}
overall_confidence certain | probable | proposed
fields[]           {field, value, confidence, comment, sources:[kildeindeks]}
sources[]          {type, citation, url, locator, accessed, result, note, attachment?}
comment            fri kommentar
contributor        {id, name, public_credit}         (kontakt ligger i contributors.json)
status             submitted | needs_changes | approved | partially_approved | rejected | withdrawn
revision, history[], review, incorporated
```

**Identifikationsstatus:** identificeret · kandidat · kan supplere enkelte
oplysninger · samme person som en anden post (`same_as`) · ikke en
enkeltperson (kræver begrundelse) · *søgt uden resultat* (kræver en kilde
markeret »Søgt, intet fund«).

**Felter** (hver med værdi, sikkerhedsgrad, **kommentar til feltet** og
kildeudvalg): efternavn, fornavn(e), andre stavemåder, fødsels-/dødsdato
(`ÅÅÅÅ`, `ÅÅÅÅ-MM`, `ÅÅÅÅ-MM-DD`, evt. `ca. `) og -sted, køn, nationalitet,
bosted, erhverv, erhvervsgren (registrets buckets), slægtskab, supplerende
beskrivelse, Wikidata-Q, andet autoritets-ID. Kolonnen `emend`/`wb` i
`taxonomy.py` viser hvert felts modsvar i `person_emendations.tsv` og i
6-PERSON-arket.

**Sikkerhedsgrad** er emendationsmodellens tre trin — som vejledning, ikke
som tal: *Sikker* (primær kilde, ≳ 95 %) · *Sandsynlig* (stærkt underbygget
slutning, ≈ 70–95 %) · *Forslag* (kvalificeret gæt, ≈ 30–70 %; under det skrives
en kommentar i stedet for et felt). Ud over feltets grad angiver bidragyderen
en samlet grad for identifikationen.

**Kilder** (mindst én pr. bidrag; mindst én pr. felt):

| Type | Kræver |
|---|---|
| Arkivalie (kirkebog, folketælling, skifte …) · Trykt publikation · Billede/skærmbillede · PDF | link **eller** præcis henvisning (side, folio, opslag, filnavn) |
| Webside/database · Autoritetsregister | link (`http(s)` — andre skemaer afvises) |
| Personlig viden | kildehenvisning; kan ikke bære »sikker«/»sandsynlig« |

Billeder og PDF'er kan vedhæftes (≤ 4 MB, PNG/JPG/WebP/GIF/PDF, højst 5 i alt)
når en server er forbundet; ellers angives filnavn/placering. Vedhæftninger
vises kun for redaktøren.

Validering sker to steder med de samme regler og samme testsæt
(`tests/fixtures/crowd_cases.json`, 46 tilfælde, køres mod både Python og
JavaScript): browseren viser alle fejl, før noget sendes; serveren er
autoriteten og tjekker desuden, at person-id'et findes.

## 5. Arbejdsgang

```
  slægtsforsker                          redaktør                         pipeline
  ─────────────                          ────────                         ────────
  crowd.html  → vælger person
  crowd-contribute.html  → udfylder
        │ submitted
        ▼
  [lager: data/crowdsource/  eller  browserens localStorage]
        │                      ┌── needs_changes ──► bidragyderen retter ("Ret og send igen")
        ▼                      │
  crowd-review.html ◄──────────┘
   pr. felt: godkend / godkend med rettelse / afvis (+ note, + endelig sikkerhedsgrad)
   modstridende bidrag til samme person vises side om side
        │ approved | partially_approved | rejected
        ▼
  export_approved.py --write ─────────────────────────────►  data/curated/person_crowd_approved.tsv  (kilde)
        │ incorporated (låst)                                  data/curated/person_crowd_approved.xlsx (gennemsyn)
        ▼                                                      build_all.py --only 4g → persons.html viser laget
```

Regler i lageret (`store.py`, afspejlet i `crowd-store.js`): alle felter skal
have en afgørelse; status følger afgørelserne (alle godkendt → *approved*, ingen
→ *rejected*, ellers *partially_approved*); »bed om uddybning« kræver en
besked; et indlæst bidrag er låst; kun ejeren kan rette eller trække tilbage,
og kun mens bidraget er åbent; en revision gemmer den foregående (inkl. den
tidligere gennemgang) i `history`.

## 6. Redaktionel godkendelse og indlæsning

Godkendelse flytter intet. Først `export_approved.py --write` skriver til det
sporbare lag:

* **`data/curated/person_crowd_approved.tsv`** — én række pr. godkendt felt, i
  `person_emendations.tsv`'s form (`match_surname`, `match_refs`, `field`,
  `original`, `emended`, `source`, `source_detail`, `date`, `confidence`,
  `notes`) plus `person_id`, `emend_field`, `contributor`, `contributor_id`,
  `submission_id`, `reviewer`, `identification`, `workbook_person_id`, `guard`.
  `source` er ny kode **`CROWD`**; `source_detail` samler de henviste kilder
  (henvisning, side, URL, opslagsdato, bilagsnavn); `confidence` er
  redaktionens endelige grad; `notes` skelner *Bidragyder:* fra *Redaktion:*.
  Nøglen `(submission_id, field)` gør genkørsel sikker.
* **`data/curated/person_crowd_approved.xlsx`** — gennemsynsfladen til
  Excel-arbejdsgangen, parret med TSV'en som master1's TSV/XLSX: fanen
  *Personer* har én række pr. person i 6-PERSON-V0.97-opbygningen (`PersonID*`,
  `Person*`, `Description`, `BirthYear`, `DeathYear`, `Nationality`, `Gender`,
  `Role/Occupation`) plus nye kolonner; cellefarve = sikkerhedsgrad; kilder,
  kommentar og redaktørnote som celle-kommentar; flere godkendte værdier til
  samme felt står i *Conflicts*.
* **`PersonID*`-crosswalk.** `Reg…` (hvad hele siden bruger) og `PER…` (6-PERSON)
  er to id-rum. Crosswalken matcher registeretiketten og tages kun, hvor den
  er entydig på begge sider (9.127 af 10.228 registerposter); resten kobles manuelt via
  `Register-ID`. Intet gættes.
* **`guard`.** Som emendationsmodellens `original`: ændrede registeretiketten
  sig, efter bidraget blev afgivet, står rækken som `register_changed`, og
  `--write` nægter at skrive, før bidraget er vurderet påny.
* **Synligt lag.** `build_crowd_queue.py` læser TSV'en og skriver
  `mockup/data/crowd-approved.js`; `persons.html` viser godkendte oplysninger
  som blokken *Bidrag fra frivillige* (*tilføjet*-markering, grad, bidragyder,
  dato, kilde). Registerteksten står uændret.

**Ikke gjort (bevidst):** bidragene er ikke skrevet ind i `build_persons_extra.py`'s
facetter (køn, nationalitet, erhverv). Konsolideringsplanen
(`person-postprocessing-consolidation.md`) siger, at hca-open-repo ikke udleder
personattributter; indlæsning i master1/master2 sker via Excel-arket og
emendationslaget, ikke ved en genvej i byggetrinnene.

Kilden `CROWD` bør tilføjes til kildekodetabellen i
`person-editorial-emendations.md` (gjort).

## 7. Sporbarhed og motivation

**Tilskrivning.** Hver række i eksporten bærer bidragyder, bidragyder-id,
redaktør og dato; hvert felt har sin egen kommentar og sine kilder. Bidragydere
kan vælge at blive nævnt ved navn, når et bidrag er godkendt (kontaktoplysninger
vises aldrig).

**Optælling.** `contributor_stats()` tæller *gennemgået* arbejde: indsendt,
afventende, godkendte bidrag, godkendte felter, personer. Antal indsendte bidrag vises for
bidragyderen selv, men mærkerne og den offentlige liste bygger kun på godkendt arbejde.

**Beskeden gamification** — hver mekanisme er valgt, så den ikke kan belønne
forkert adfærd:

| Mekanisme | Hvorfor den er forsvarlig |
|---|---|
| *Fremdrift*: »N af 2.285 poster har fået godkendte bidrag« | Fællesskabets fremgang, ikke en konkurrence |
| Mærker, kun af godkendt arbejde: *Første godkendte bidrag* · *Fem godkendte med kilder* · *Dokumenteret negativt fund* · *Lokalkender* (5 godkendte om samme land/lokalitet) · *Besvarede registrets tvivl* | Belønner kildekvalitet, ærlige negative fund og lokal ekspertise — ikke antal |
| *Kendskabsområder* → genveje i køen | Matcher ekspert og materiale |
| Bidragyderlisten er **alfabetisk**, ingen rangliste | Ingen kapløb |
| Ingen tidtagning, striber, point eller daglige mål | Opgaven er videnskabelig, ikke et spil |

## 8. Arkitektur og drift

Sitet er statisk (GitHub Pages) og skal fortsat kunne åbnes fra `file://`.
Derfor har lageret **to udskiftelige bagender** bag samme Promise-API
(`crowd-store.js`):

| | **api** (server) | **local** (ingen server) |
|---|---|---|
| Aktiveres når | `GET api/crowd/health` svarer | ellers (også `file://` og GitHub Pages) |
| Bidrag ligger | `data/crowdsource/submissions/*.json` | browserens `localStorage` |
| Til redaktionen | direkte | bidragyderen henter en JSON-fil (`Mine bidrag → Hent som fil`) |
| Gennemgang | `crowd-review.html` med redaktørnøgle | samme side i den browser, der rummer/importerer bidragene |
| Til pipelinen | `export_approved.py --write` | `export_approved.py --import-json fil.json --write` (genvalideres; status genberegnes fra afgørelserne, ikke den, filen påstår) |
| Vedhæftninger | ja | nej (angiv filnavn/placering) |

Local-tilstanden er den eneste, der kræver nul infrastruktur: den lader én
slægtsforsker afprøve hele flowet — og lader projektlederen gennemgå resultatet
— uden at nogen server er sat op. Den er også prototypens svageste del som
*lager*: `localStorage` kan ryddes; filen er sikkerhedskopien.

**API** (`/api/crowd/`, alt JSON, same-origin):

| Rute | Adgang |
|---|---|
| `GET health`, `GET stats` | offentlig (stats: kun optællinger og bidragydere, der har bedt om at blive nævnt) |
| `POST submissions` · `PUT/POST submissions/<id>[/withdraw]` · `GET mine` | bidragyder-token (udstedes ved første indsendelse; serveren gemmer kun dens hash) |
| `GET admin/submissions[/<id>]` · `POST admin/submissions/<id>/review` · `GET admin/contributors` · `GET admin/attachments/<id>/<fil>` · `GET admin/export?format=tsv\|xlsx\|json` | redaktørnøgle (`HCA_CROWD_ADMIN_TOKEN`; sættes den ikke, genereres én og udskrives) |

Alle felter valideres på serveren; ukendte nøgler droppes; filnavne rengøres;
id'er matches mod et fast mønster, før de rører filsystemet.

## 9. Sikkerhed og privatliv

* Ingen ny tredjepartskode; sider og scripts overholder CSP-reglerne
  (`test_csp_ready.py`): ingen inline-handlers, `connect-src 'self'`.
  Alle værdier fra data, URL og bidragydere gennem `esc()`; eksterne links er
  kun `http(s)`, åbnes i nyt faneblad med `noopener noreferrer`.
* Serveren binder til `127.0.0.1`, kører ren HTTP og én proces: **sæt TLS og en
  rigtig identitetsudbyder foran, før den udstilles.** Redaktørnøglen er en delt
  hemmelighed, ikke en brugerkonto.
* `data/crowdsource/` (navne, e-mail, ikke-godkendte påstande, bilag) er
  `.gitignore`'et. Det, der er godkendt, forlader mappen via eksporten til
  `data/curated/` — som kun rummer navn (hvis bidragyderen ønskede det) og
  kilder.
* Bidragydere accepterer CC BY 4.0 med navngivelse (som resten af materialet)
  ved hver indsendelse.
* **Kendt begrænsning:** `register_snapshot.area` og `doubt` kommer fra klienten
  og bruges kun til et mærke og til redaktørens kontekst; en bidragyder kan i
  princippet pynte dem. Mærker kræver godkendt arbejde, så det er harmløst nu,
  men bør hentes server-side, når mærker får vægt.

## 10. Kør prototypen

Alle kommandoer er til PowerShell (`python`, ikke `python3`).

```powershell
python scripts/build_all.py --only 4b      # persons-extra.js (første gang; bruges af kontekstblokkene)
python scripts/build_all.py --only 3b      # diary-index/diary-refs (første gang)
python scripts/build_all.py --only 3a      # diary-pages (første gang; ~4.400 filer)
python scripts/build_all.py --only 4g      # crowd-queue.js + crowd-approved.js
```

**A. Uden server (nul opsætning).** Åbn `mockup/crowd.html` fra disken (eller på
GitHub Pages). Slægtsforskeren vælger en person, bidrager, og henter sin fil
under *Mine bidrag*. Redaktøren åbner `crowd-review.html`, vælger
*Importér bidragsfil*, gennemgår, og henter afgørelserne. Derefter:

```powershell
python scripts/crowdsource/export_approved.py --import-json afgoerelser.json          # tørkørsel
python scripts/crowdsource/export_approved.py --import-json afgoerelser.json --write  # skriv + lås
python scripts/build_all.py --only 4g                                                 # lag til persons.html
```

**B. Med server.**

```powershell
$env:HCA_CROWD_ADMIN_TOKEN = "vælg-en-lang-nøgle"
python scripts/crowdsource/server.py          # http://127.0.0.1:8765/crowd.html
python scripts/crowdsource/export_approved.py --write
```

Test: `python -m pytest tests -q` (kræver `pip install pytest`; Node bruges til
JS-testene, hvis det er installeret). CI bygger køen som trin 4g og kører
testene. Bemærk: `tests/test_build_diary_pdf.py::test_pdf` fejler allerede på
`main` og er ikke berørt af denne gren.

## 11. Vej til flere bidragydere

Prototypen er bygget, så intet af det følgende kræver omskrivning af
grænsefladen — kun bagenden:

| Behov | Næste skridt |
|---|---|
| Rigtige konti | Erstat bidragyder-token med login (ORCID/SSO/e-mail); `contributor.id` er allerede nøglen til tilskrivning og optælling |
| Flere redaktører, roller | `review.reviewer` er et felt; tilføj roller (bidragyder / redaktør / administrator) og kræv to godkendelser for *Sikker* |
| Samtidighed og skala | Skift `FileStore` ud med PostgreSQL (dokumentformerne svarer til tabeller; se `postgresql-migration.md`); behold API'et |
| Misbrug | Hastighedsbegrænsning, e-mailbekræftelse, spam-filter på fritekst |
| Samarbejde om uenighed | Konfliktvisningen findes; næste: tråd pr. person, hvor bidragydere kan svare på hinandens påstande |
| Tilskrivning i det offentlige register | Vis »Identificeret af …« i personlisten og i citér-som-teksten; offentlig bidragydersiden med DOI-venlig citation |
| Flere registre | Samme model virker for steder (`LOC…`) og værker; kø-bygger og felter parametriseres |
| Engelsk | De tre nye sider findes kun på dansk (jf. `i18n-todo.md`) |

## 12. Åbne beslutninger til H.C. Andersen Centret

1. **Hvem er redaktør?** Prototypen kender én. Skal godkendelsen af *Sikker*
   kræve to personer?
2. **Skal »Registret er selv i tvivl« udløse en emendation automatisk** ved
   godkendt `surname`-bidrag med grad *sikker* (jf. krydshenvisningsposten i
   emendationsdokumentet)? Eksporten producerer i dag kun rækkerne.
3. **Vil man vise bidragydernes navne offentligt**, og i så fald hvor (personside,
   om-side, citation)?
4. **Skal bilag opbevares** (ophavsret: kirkebogsbilleder, skærmbilleder af
   kommercielle databaser) eller kun henvises til?
5. **Hvilken sikkerhedsgrad** kan skubbe en post ud af køen? Nu: ingen —
   køen styres af registrets egne ankre, ikke af bidrag.
