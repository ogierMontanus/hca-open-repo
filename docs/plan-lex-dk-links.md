# Plan: lex.dk-links til danskere og kendte udlændinge i personregistret

Status: forslag, revideret 2026-10-29 (nationalitet fra Lex-sider; profession-målrettet søgning; beslutninger indarbejdet, se §8) · bygger på pilotens resultater i
[`data-model/lex-dk-links-pilot.md`](data-model/lex-dk-links-pilot.md) og
[`data-model/lex-dk-sitemap-results.md`](data-model/lex-dk-sitemap-results.md) ·
hører sammen med [`plan-tidstavle-data.md`](plan-tidstavle-data.md) (del 2: eksterne data)

**Mål:** en verificeret, diskret ekstern henvisning fra en persons side til den mest udførlige
lex.dk-artikel om vedkommende — *Dansk Biografisk Leksikon* (DBL) først, derefter andre udførlige
værker. **Perifere personer udelades bevidst.** Kun links gemmes; ingen Lex-tekst kopieres.

## 1. Principper og grænser (gælder hele planen)

| Princip | Konkret |
|---|---|
| Faktakontrol (`CLAUDE.md`) | Intet link skrives, før både navn *og* begge levedatoer er set på artiklens egen side. Chatbottens svar er et forslag, aldrig en kilde. |
| Kun kilde-kort, aldrig fritekst-URL'er | Piloten viste, at chatbotten opfinder slugs, når den bedes om et «link». |
| Ingen Lex-indhold i repoet | Rå svar og sidetekst committes ikke. Gem: URL, værk, sidetitel, verifikationsflag, dato — og **afledte fakta-tags** (nationalitet, erhvervsord, fødested-land), aldrig Lex' sætninger. |
| Lex-fakta er «tilføjet» data | Nationalitet/erhverv fra Lex overskriver aldrig registerets egne felter; de gemmes i egne kolonner med kilderegel og konfidens og vises som *tilføjet* (`docs/external-links.md` §2a). **Det gælder også nationalitet udledt af DBL** (brugerbeslutning 2026-10-29). |
| Ingen standardnationalitet | **Antagelsen «umarkeret = dansk» er opgivet** (brugerbeslutning 2026-10-29, ændret samme dag). Et tomt nationalitetsfelt betyder *uoplyst*, ikke dansk. Værdien **«Dansk\*»** er en afgrænset bucket med hård DBL-grænse, se §3d. |
| Teaterleksikon kun som reserve | Gyldendals Teaterleksikon forsøges **kun for personer uden bekræftet DBL-artikel** (brugerbeslutning 2026-10-29); koden springer værket over, når DBL er bekræftet. |
| Værksnavne er ikke fakta om personen | «Dansk Biografisk Leksikon» i titel/brødkrumme er ikke *dansk*; værksnavne og faste sektionsnavne filtreres fra, før et ord tolkes som nationalitet (fanget i test, se §3b). |
| Eksterne links | Nyt faneblad, diskret, `.sr-only`-varsling (`docs/external-links.md`); vises i «Autoritetslinks»-blokken på persons-siden. |
| Hentning ved build, ikke i browseren | Ingen runtime-kald fra siden; resultatet er en committet CSV (som `works_wikidata.csv`). CSP uændret. |
| Tilladelse | `lex.dk/robots.txt` udelukker AI-crawlere og kræver godkendelse til AI-brug. **Fase 0** er at skrive til Lex, før noget kører i stor skala. |
| Licens | Vilkår for genbrug af DBL/Den Store Danske-henvisninger og -titler er **ikke undersøgt**; tjekkes i fase 0. |

## 2. Screening: hvem skal overhovedet slås op?

Tragt beregnet på `data/normalized/*` (10.228 personer):

| Trin | Filter | Tilbage |
|---|---|---:|
| 0 | Alle personposter | 10.228 |
| 1 | Har levetid `(år–år)` | 7.194 |
| 2 | … og har fornavn (ikke kun efternavn) | 7.132 |
| 3 | … og beskrivelse/erhverv antyder en offentlig person (digter, komponist, maler, billedhugger, skuespiller, danser, konge/prins, biskop, politiker, professor, læge, officer …) | 3.977 |
| 4 | … og beskrivelsen er ikke *kun* slægtskab («Søn af …», «Datter af …», «g. m. …») | 3.276 |
| **5** | … og **≥ 5 dagbogsreferencer** eller rolle forfatter/kunstner | **1.287** |
| 6 | Kerne: ≥ 10 referencer | 296 |

Fordeling i trin 5: 1.122 mænd / 164 kvinder; heraf 639 med udenlandsk nationalitetsmarkering,
15 eksplicit danske og 633 uden markering (registrets standard er dansk, nationalitet noteres
typisk kun hvor den afviger — **forudsætning, ikke verificeret**).

**Eksplicitte udelukkelser** (bevidst, jf. «mange perifere personer må udelukkes»):
poster uden levetid (3.034), kun efternavn (909), køn «Andet»/«Endnu ubestemt» (109: firmaer,
slægter, grupper), rene slægtskabsbeskrivelser, rolle «Handel»/«Militær»/«Embedsmand» uden
yderligere signal, mytologiske/bibelske/fiktive navne.

**Tre niveauer:**

| Niveau | Størrelse | Metode | Hvorfor |
|---|---:|---|---|
| **A** | ≈ 1.300 | sitemap-match + chatbot til resten | Høj forventet hitrate |
| **B** | ≈ 2.000 (trin 4 minus A) | *kun* deterministisk sitemap-match, ingen chatbot | Billigt; accepteres kun ved fuld verifikation |
| **C** | resten | ingen opslag | Perifere personer |

**Køn:** screenes ikke *fra*, men *styres*: kvinder (ca. 13 % i trin 5, 443 i trin 4) slås først op i
*Dansk Kvindebiografisk Leksikon* (`kvindebiografiskleksikon.lex.dk`) og DBL; mange danske kvinder
findes ikke i DBL. **Manglende oplysninger** (ingen levetid, intet fornavn, ukendt køn) giver C.

**Nationalitet og profession *styrer* ruten (revideret 2026-10-29).** Hvor et værk kun dækker en
delmængde, spildes forespørgsler på personer, der ikke kan være der:

| Person | Prøv (i rækkefølge) | Spring over |
|---|---|---|
| Dansk/nordisk, kunstner (maler, billedhugger, tegner, grafiker, arkitekt, fotograf) | DBL → **Weilbach** → lex.dk | Teaterleksikon |
| Dansk/nordisk, scene (skuespiller, sanger, danser, balletmester, instruktør, teaterchef, dramatiker, kapelmester) | DBL → **Teaterleksikon, kun hvis ingen bekræftet DBL-artikel** → lex.dk | Weilbach; Teaterleksikon når DBL er bekræftet |
| Dansk kvinde (uanset erhverv) | DBL → **Dansk Kvindebiografisk** → fagværk → lex.dk | — |
| Dansk, øvrige (forfatter, embedsmand, politiker, lærd, officer …) | DBL → lex.dk | Weilbach, Teaterleksikon |
| Udenlandsk (markeret, eller fastlagt af Lex, §3b) | **lex.dk-hoved** (Den Store Danske) → Rute 2 (chatbot) | DBL (9 af 159 bekræftede udlændinge er i DBL), Weilbach |
| Nationalitet uoplyst | **DBL først for alle** (hård grænse for «Dansk\*», §3d) → derefter lex.dk-hoved; ret ruten, når §3b finder en nationalitet | — |

Nationalitet og profession kommer fra registret (`person_ethnic_descriptors.csv`, `person_role.csv`,
beskrivelse) — og **for personer uden nationalitetsmarkering fra selve Lex-siden** (§3b).

Script (ingen netværk): `scripts/parsers/screen_persons_for_lex.py` → `data/curated/lex/persons_tiers.csv`
(`rid, tier, reason, refs, gender, nationality, role, search_name`; nye kolonner `prof_target` og
`nat_lex`, se §3b–c). Kolonnen `search_name` fyldes manuelt
for kongelige og varianter (Napoleon 1. → *Napoleon Bonaparte*).

## 3. Kilder, billigste først

### Rute 1 — lex.dk's sitemap (deterministisk, ingen chatbot) **← primær**

* `https://lex.dk/.sitemap/sitemap.xml` er indeks over **6 filer, i alt ≈ 45 MB**
  (9,3 + 7,0 + 6,0 + 10,8 + 11,2 + 0,8 MB), og *alle* Lex-underdomæner peger på den samme
  (verificeret via `robots.txt` på biografiskleksikon, kvindebiografiskleksikon og denstoredanske).
  Den mindste fil (0,8 MB) indeholder bl.a. 536 `biografiskleksikon.lex.dk`- og 196
  `weilbach.lex.dk`-adresser, så sitemap'et dækker værkerne.
* Hentes **én gang** til `data/raw/lex/` (gitignoreres); genhentes højst månedligt.
  Det er en offentliggjort sitemap, angivet i robots.txt — ikke en crawl.
* `scripts/parsers/lex_sitemap_index.py` (nyt): læser sitemaps, beholder værker i prioritetsrækkefølgen
  *DBL > Dansk Kvindebiografisk > Weilbach > Den Store Danske > Gyldendals Teaterleksikon/Danmarkshistorien > øvrige lex.dk*,
  og matcher slugs mod persons `search_name` med `slug_matches()` fra `lex_link_candidates.py`
  (tåler forkortelser, bindestreger, initialer).
* **Verifikation:** ét sidekald pr. kandidat (1 forespørgsel/sek., cache) — titel + begge årstal.
  Sitemap'et har ingen levetid, så navnebrødre (`A.S._Ørsted_-_jurist`) afgøres kun her.
* **Omkostning:** ≈ 1 download à 45 MB + ca. 2–5 verificeringsforespørgsler pr. person i A/B
  (≈ 3.300 personer × ~3 = ca. 10.000 sidekald ≈ 3 timer ved 1/sek.). Ingen chatbot, ingen tokens.

> **Målt 2026-10-28** ([`data-model/lex-dk-sitemap-results.md`](data-model/lex-dk-sitemap-results.md)):
> hele niveau A (1.315) kørt trinvis 30 → 90 → 270 → 810 → 1.315 mod sitemap'et. **532 bekræftet
> (40 %), DBL 326 (25 %)**, 1.727 sidekald (≈ 40 min), ingen chatbot. Danskere/umarkerede 55 %,
> udlændinge 25 % (Lex staver dem på dansk) — de 683 uden slug (heraf 447 udenlandsk markerede) er
> restmængden til Rute 2. Estimatet «≈ 30 % rest» længere nede er dermed for lavt: **regn med
> ≈ 500–680 personer til chatbotten** (≈ 5–6 timer, 3 dage ved loftet på 200/dag).

### Rute 1b — nationalitet (og erhverv, fødested) udtrukket af siderne vi alligevel henter

**Pointen:** verifikationen henter allerede hver kandidatside. Siden indeholder strukturerede spor
om nationalitet og erhverv, så udtrækket koster **ingen ekstra forespørgsler** for nye kørsler.

Målt 2026-10-29 på en håndfuld sider pr. værk (kun struktur undersøgt, intet citeret):

| Værk | Hvor står nationalitet/erhverv | Eksempel på mønster |
|---|---|---|
| lex.dk-hoved (Den Store Danske) | `<meta name="description">`: «X **var en {adj} {erhverv}** …» · brødkrumme «{Adj} litteratur», «{Adj} litteratur 1770-1832» · nye titler «Navn – {Adj} {erhverv} – Liv og værk» · faktaboks «Født …, **Sted**» | «… var en norsk forfatter», «Tysk litteratur» |
| Gyldendals Teaterleksikon | meta: «Navn, 1791-1860, **dansk** dramatiker, kritiker …» (også *årstal* — se §3c) · brødkrumme «Danske skuespillere» | «dansk dramatiker» |
| Dansk Biografisk Leksikon | meta: «Navn, fulde navne, dd.mm.åååå-dd.mm.åååå, **erhverv**. **Født i {sted}**, død i {sted}» — *ingen* nationalitetsord | «Født i Brunn (Brno), død i Kbh.» |
| Weilbachs Kunstnerleksikon | brødkrumme «Dansk billedkunst 1800-tallet i Weilbach», «Nordens billedkunst 1750-1850»; meta er prosa | «Dansk billedkunst …» |
| Dansk Kvindebiografisk | brødkrumme = erhvervskategori («Forfattere»); ingen nationalitet (værket er dansk) | — |

**Regler, ordnet efter pålidelighed** (adjektiver fra `data/curated/ethnic_adjectives_da.csv`, 92 former,
afbildet på registrets `nationality_key`):

| Regel | Kilde | Konfidens | Kommentar |
|---|---|---|---|
| **R1** | «var en/er en {adj}» eller «, {adj} {erhverv}» i de første ca. 220 tegn af meta (lex.dk-hoved, Teaterleksikon) | høj | Brug *tegnvindue*, ikke «første sætning» — initialer («C.E. Frijs») bryder sætningsdelingen (fanget i test). |
| **R2** | brødkrumme «{Adj} litteratur/billedkunst/…», «Danske {erhverv}» efter fjernelse af værksnavne | middel | «Nordens billedkunst» → *nordisk*, ikke dansk. |
| **R3** | faktaboks «Født …, {sted}» (lex.dk-hoved) | middel | sted → land via stedregisteret/GeoNames; kun forslag. |
| **R4** | DBL-meta «Født i {sted}» (+ «død i {sted}») | lav–middel | fødested ≠ nationalitet (Franz Neruda: født i Brno, død i Kbh.); `fødested`/`fødeland` gemmes som tilføjede data; er fødelandet udenlandsk, flages rækken til gennemgang i stedet for at få nationalitet. |
| **R5** | **forekomst i DBL** (bekræftet: navn + begge levetidsår) | **hård** for «Dansk\*» | Definerer bucketen **«Dansk\*» = født i Danmark eller bosat der i længere årrække** (§3d). DBL-udledt nationalitet angives som **tilføjede data** (`nat_basis = dbl_optagelse`). Forekomst i *andre* værker (DKBL, Weilbach, Teaterleksikon, lex.dk) er **ikke** nok. |

**Målt udbytte** (stikprøve, ikke endeligt): af de **661** personer i niveau A *uden* nationalitetsmarkering
har 366 et bekræftet link: **204** på lex.dk-hoved/Teaterleksikon (→ R1/R2), **135** kun i DBL (→ R4/R5),
**27** kun Weilbach/DKBL (→ R2/R5); **295** har intet bekræftet link og får ingen nationalitet fra Lex.
I en stikprøve på 18 lex.dk-hoved-sider gav R1 eller R2 nationalitet for 13 (72 %) med en for snæver regex
(«første sætning»); på 5 Teaterleksikon-sider 5 af 5. DBL: 17 af 32 sider havde «Født i …». Forventning:
**≈ 200–300 af de 661 får en eksplicit nationalitet** (R1+R2), ≈ 70 yderligere et fødested (R4).

**Antagelsen «umarkeret = dansk» er opgivet** (brugerbeslutning 2026-10-29): 8.259 af 10.228 personer har intet
nationalitetsfelt, og stikprøven viste udlændinge blandt dem (fx *Samuel Johnson*, britisk på Lex). Umarkeret betyder
derfor *uoplyst*. «Dansk» får i stedet en afgrænset betydning med hård kilde (§3d).

**Implementering:**
* `fetch_check()` i `lex_link_candidates.py` udvides til også at returnere `nat_hint`, `nat_rule` (R1–R5),
  `prof_hint` (erhvervsord fra meta), `birth_place`, `breadcrumb_tags` — kun *afledte tags*, ikke tekst.
  Cache-nøgle bumpes til `#v3`.
* Den nuværende cache (`#v2`) har kun verdikter; **én side pr. bekræftet person (≈ 530 sider, ≈ 9 min ved 1/sek.;
  op til ≈ 890 hvis alle bekræftede og sandsynlige sider tages) hentes én gang igen** for at hente tags. Derefter kommer tags gratis.
* Output (forslag): `data/curated/lex/person_nationality_lex.csv` —
  `rid, nationality_key, rule, confidence, source_url, birth_place, verified_on, conflict_with_register`.
  Hvor registret allerede har en markering, gemmes Lex' som kontrol (`conflict_with_register`), aldrig som
  overskrivning.
* Tilbagekobling: `nat_lex` styrer ruten i §2 (udlænding → lex.dk-hoved/chatbot, ikke DBL/Weilbach) og
  kan fodre `person_ethnic_descriptors`/nationalitetsfacetten som *tilføjet* data efter 10 %-stikprøve af R1/R2
  (**godkendt 2026-10-29**); R5 (DBL) definerer «Dansk\*» (§3d).
* Bivirkning at holde øje med: værksnavne i titel/brødkrumme («Dansk Biografisk Leksikon» → «dansk») gav i
  en test **falsk «dansk» på alle DBL-sider**; filteret (`Biografisk|Leksikon|^Lex$|Weilbach|Kunst og kultur`)
  er derfor del af reglen og dækkes af en test.

### Rute 1c — profession-målrettet søgning i specialværker

**Værker i sitemap'et** (19 værter, verificeret; kun de der indeholder personartikler er relevante):

| Vært | Artikler | Indhold | Brug til personer |
|---|---:|---|---|
| `lex.dk` (Den Store Danske m.fl.) | 170.669 | leksikon, alle fag | hoved for udlændinge og øvrige |
| `biografiskleksikon` (DBL) | 14.134 | danske biografier | primær for danskere |
| `weilbach` (Weilbachs Kunstnerleksikon) | 7.827 | danske/nordiske billedkunstnere og arkitekter | **kunstnere** |
| `teaterleksikon` (**Gyldendals** Teaterleksikon, 2007) | 2.072 | teater, skuespillere, instruktører, dramatikere, scenografer | **scenepersoner — kun hvis de ikke findes i DBL** (beslutning 2026-10-29) |
| `kvindebiografiskleksikon` | 1.940 | danske kvinder | **kvinder** |
| `dansklitteraturshistorie` | 1.148 | **kapitler/perioder** (fx «Patos og satire – F. Paludan-Müller») | kun som sekundært «kapitel om forfatterskabet», ikke personartikel |
| `bornelitteratur` | 172 | børnebøger | evt. børnebogsforfattere |
| `danmarkshistorien`, `gyldendalogpolitikensdanmarkshistorie` | 2.724 / 2.556 | kilde-/emnekapitler | sekundært (konge, politiker, hændelse) |
| `naturenidanmark`, `trap`, `pattedyratlas` m.fl. | – | natur, **steder** | ikke personer |
| **musik/komponister** | – | **ingen egen vært** | DBL + lex.dk (komponister findes ikke i et fagleksikon her) |

(Planens og scriptenes tidligere navn «Dansk Teaterleksikon» er forkert; værket hedder **Gyldendals
Teaterleksikon** — rettes i `WORKS`/`HOSTS`-listerne.)

**Profession → mål** udledes af `person_role.csv` (`roller`, `kilde_beskrivelse_termer`) + beskrivelsesord
(`prof_target`): kunstner → Weilbach; scene → Teaterleksikon; kvinde → DKBL; kombineres med nationalitet
(§2-tabellen). Kun mål, der er relevante, får kandidater og sidekald.

**Målt loft** (2026-10-29): af de **783** niveau A-personer uden bekræftet link har **354** et kunstner- eller
sceneerhverv (255 kunstnere, 105 scene), men kun **58** (Weilbach) og **24** (Teaterleksikon) har overhovedet
et slug med deres efternavn; de øvrige findes ikke i de værker. Med den nye Teaterleksikon-regel faldt Teaterleksikon-bekræftelserne i niveau A fra 9 til **3 personer** (ingen
havde DBL); samlet dækning uændret (532). Et forsøg (55 sidekald, kandidater begrænset
til de relevante værter, top 3 pr. person) gav **14 nye bekræftede** (Weilbach og Teaterleksikon; +1 procentpoint
af A: 532 → ≈ 546) — ca. ¼ bekræftelse pr. sidekald. **Konklusion:** målrettet søgning er billig og præcis,
men har lavt loft — dens værdi er (a) de ≈ 15–25 ekstra personer, (b) færre spildte sidekald og mindre støj i
kandidatlisten, ikke et stort hop i dækning. Den store restmængde (≈ 680 uden slug) er navnevarianter og
udlændinge, dvs. Rute 2.

**Justeringer i verifikationen pr. værk** (profil pr. værk i stedet for ét vindue):
* **Teaterleksikon:** årstallene står i `meta description` («1791-1860, dansk dramatiker»), *ikke* i
  indledningen efter første overskrift — det nuværende tjek gav derfor «mismatch» for *J.L. Heiberg*. Brug
  meta + titel.
* **Weilbach, DBL, lex.dk-hoved, DKBL:** nuværende vindue (første 1.500 tegn efter første `<h1>`) virker
  (Weilbach 103 bekræftet).
* **Lempet matching må ikke fjerne sikkerhedsnettet.** I forsøget blev *P. G. Skovgaard* bekræftet mod
  `P.C._Skovgaard` (fornavnsinitial afviger, men begge årstal passer — muligvis OCR-fejl i registret):
  rækker, der kun er bekræftet via den *lempede* første-bogstavs-regel, markeres `relaxed` og
  gennemgås manuelt, ikke automatisk.

**URL-felt:** CSV'erne gemmer i dag URL'en *afkodet* (`Jørgen_V._Sonne`); et script, der henter den, fejler
på ikke-ASCII (fanget i test). Gem **sitemap'ens procent-kodede URL** som `url` (kanonisk) og en læsbar
`url_display` ved siden af.

### Rute 2 — Lex' chatbot, kun til resten i niveau A

* Anvendes for personer, hvor Rute 1 ikke finder en slug (navnevarianter, udlændinge med ikke-
  danske slugs, usikre navnebrødre). **Prompten tilpasses nationaliteten** (§3b): udlændinge spørges efter
  *Den Store Danske/lex.dk* (ikke DBL), kunstnere også efter Weilbach, scenepersoner efter Teaterleksikon,
  kvinder efter Dansk Kvindebiografisk. Registrets stavning (Napoleon 1., Bjørnstjeme) rettes først i
  `search_name`.
* **Måling:** ≈ 33 sek. pr. person incl. pause, 62 % DBL-hit, 92 % bekræftet link i alt (n = 50, skævt
  udvalg); ingen blokering set; ingen offentliggjort grænse.
* **Budget (forslag, ikke Lex' tal):** højst **200 personer/dag**, én ad gangen, ≥ 30 sek. mellem
  spørgsmål, ny samtale pr. spørgsmål, afvis ikke-nødvendige cookies, **stop ved første 429/captcha/
  fejlside**. Forventet rest efter Rute 1: ≈ 30 % af A ≈ 400 personer ≈ **4 timer**, 2 dage ved loftet.
* Prompt som i piloten (almindeligt spørgsmål, så der kommer kilde-kort); kun kilde-kort-links
  accepteres. Kør kun efter fase 0 (tilladelse).

### Rute 3 — archive.org (Wayback) til det gamle denstoredanske.dk-DBL

Formål: (a) **fallback**, når en DBL-artikel ikke kan findes på lex.dk men tydeligt har eksisteret;
(b) en **uforanderlig henvisning** (`archive_url`) ved siden af det levende link.

* **Verificeret URL-struktur** (CDX-opslag 2026-10-28): to former i arkivet —
  `denstoredanske.dk/Dansk_Biografisk_Leksikon/<Kategori>/<Underkategori>/<Rolle>/<Navn>`
  (fx `…/Kunst_og_kultur/Litteratur/Forfatter/A._Andersen_Feldborg`, optaget 2015-06-06) og den korte
  `denstoredanske.dk/Dansk_Biografisk_Leksikon/<Navn>` (fx `…/Aka_Høegh`, 2015-06-16).
  Navnedelen svarer i eksemplerne til nutidens lex-slug (`Aka_Høegh`).
* **Dyb Wayback-URL:** `https://web.archive.org/web/<tidsstempel>/<original-URL>`; tidsstemplet kommer
  fra CDX (`filter=statuscode:200`, `collapse=urlkey`).
* **Faldgruber (set i test):** (1) CDX over hele værtsnavnet med regex-filter giver **504**; brug
  kun snævre præfikser (`…/Dansk_Biografisk_Leksikon/Kunst_og_kultur/Litteratur/Forfatter/Adam_`);
  (2) tjenesten svarede periodisk «Temporarily Offline»/forbindelsen blev nulstillet — kræv retry
  med eksponentiel backoff; (3) arkivet har **dobbelt-kodede dubletter** (`%C3%83%C2%85ge` ↔ `%C3%85ge`):
  normalisér før matching; (4) `www.`/uden `www.` er forskellige nøgler.
* **Budget:** ≤ 1 forespørgsel/sek., cache alle svar, kun for personer fra Rute 1+2 uden DBL-hit
  og som er *danskere* (≈ 100–300 forventet). Wayback-links er **sekundære**: vises kun, hvis det
  levende lex.dk-link mangler eller er dødt, og mærkes «arkiveret».
* Ikke antaget: at indholdet i det arkiverede DBL er identisk med dagens. Levetid og navn
  verificeres også her (arkiv-sidens titel).

### §3d — Nationalitetsværdien «Dansk\*» (DBL som hård grænse)

**Beslutning (2026-10-29):** antagelsen «umarkeret = dansk» opgives. Værdien *dansk* i nationalitetsfacetten
får en **stjerne**, og ved mouseover står: **«Født i Danmark eller bosat der i længere årrække»**
(engelsk: «Born in Denmark or resident there for many years»). **DBL-optagelse er hårdt kriterium** for at
indgå i den bucket.

**Hvem kommer i «Dansk\*»:**

| Basis (`nat_basis`) | Betingelse | Antal (målt) |
|---|---|---:|
| `dbl_optagelse` | bekræftet DBL-artikel (navn + begge levetidsår på artiklens egen metabeskrivelse) | **885** (A 324 · B 333 · C 228) — **målt i fase 2d**, se `lex-dk-dbl-bucket-results.md` |
| `register_beskrivelse` | registrets egen beskrivelse har *dansk* som ledende nationalitetsord (`person_ethnic_descriptors.csv`) | **87** personer (17 i A, heraf 7 også i DBL) — **min læsning, bekræftes** |
| *(ingen)* | Lex-sider siger «dansk» (R1/R2) men personen er ikke i DBL | **ikke** i bucketen; lægges i `data/curated/lex/queue_dansk_uden_dbl.csv` til gennemgang |
| *(ingen)* | umarkeret og ikke i DBL | **uoplyst** — ingen nationalitet |

* **Flere værdier er tilladt.** 8 af DBL-bekræftede i A har en udenlandsk registermarkering (Tullin *norsk*, Wolfhagen
  *tysk*, Denner *tysk*, Bravo *holstensk* …); de får **både** deres egen nationalitet og «Dansk\*» — netop
  «bosat der i længere årrække».
* **Mangler levetid** (3.034 poster): kan ikke verificeres mod DBL (årstalskontrol) og kommer derfor ikke i bucketen.
* **Størrelse (målt 2026-10-29):** i dag 87 personer har *dansk* i facetten. DBL over hele registret gav **885**; med
  registrets egne 87 (15 overlap) er bucketen **957**. 19 af de 885 har også en udenlandsk registermarkering.

**Data:** `data/curated/person_nationality_added.csv` — `rid, nationality_key, nat_basis, source_url, verified_on,
conflict_with_register`. Rækker med `nat_basis = dbl_optagelse` er *tilføjede data* og må kun oprettes ved
bekræftet DBL-link. Registrets egne felter ændres ikke.

**Ændringer i koden (udføres efter fase 2d):**

| Fil | Ændring |
|---|---|
| `scripts/build_mockup/build_persons_extra.py` | `nationalities` = registrets ledende match ∪ `{dansk}` for rækker i `person_nationality_added.csv`; `NATIONALITY_LABELS['dansk'] = 'Dansk*'`; ny `NATIONALITY_NOTES = {'dansk': 'Født i Danmark eller bosat der i længere årrække'}` |
| `mockup/persons.html`, `persons_en.html` | facetrækken «Dansk\*» med `title`-tooltip (mouseover) **og** synlig fodnote i facetgruppen + `.sr-only`-tekst, så touch/tastatur/skærmlæser også får definitionen; facetkommentaren «Uoplyst» opdateres (8.259 → antal efter fase 2d) |
| `mockup/js/facet-engine.js` | understøt en valgfri `data-facet-note-<nøgle>`/`NATIONALITY_NOTES`-tooltip pr. række (i dag findes kun label og antal) |
| `mockup/nation.html`, `nation-index.js`, `nation_umbrellas_da.csv` | paraplyen *dansk* får samme stjerne og tooltip; regionale nøgler (jysk, sjællandsk …) og kolonial (grønlandsk) er allerede under den |
| `build_persons_extra.py` → `bio_search_links()` | kommentaren «uoplyst nationalitet → Lex.dk-søgning» begrundes ikke længere med «dansk-centreret register»; standardlinket til Lex.dk forbliver en *ressourcevalg* (Lex dækker både danske og udenlandske), ikke en nationalitetsantagelse |
| `docs/data-model/person-ethnic-descriptors.md` | note: «umarkeret ≠ dansk»; «Dansk\*»-definitionen |
| tests | ingen person får `dansk` fra DBL uden bekræftet DBL-række; `NATIONALITY_NOTES` findes for alle værdier med stjerne; ingen standardværdi for uoplyst |

## 4. Token- og forespørgselsbudget

| Post | Størrelse | Håndtering |
|---|---|---|
| Rå chatbot-svar | ≈ 9,7 kB/person (≈ 490 kB for 50; ≈ 12,5 MB for 1.287) | **Aldrig ind i modelkonteksten** (≈ 3 mio. tokens). Scripts kører selvstændigt; kun CSV-opsummeringer læses. |
| Sitemap-filer | ≈ 45 MB | Parses af script; kun resultatlister (≤ 200 kB) vises. |
| Verifikations-sidekald | ≈ 10.000 forespørgsler, 1/sek. (niveau A brugte 1.727; ≈ 2.000 i alt hidtil inkl. forsøg, **ingen 429/5xx set**) | Cache i `data/raw/lex/page_cache.json`; aldrig genhent. |
| Genhentning for tags (§3b) | ≈ 530–890 sider, 1/sek. (≈ 9–15 min), **engangs** | Efterfølgende kørsler får tags gratis fra verifikationssiden. |
| Profession-målrettet søgning (§3c) | ≈ 60–150 sidekald | Kun relevante værter og kandidater; cache. |
| Wayback | ≲ 600 forespørgsler | Cache; backoff ved 5xx. |
| Fejlhåndtering | transient 5xx/timeout | Retry med eksponentiel backoff (3 forsøg), gem fejl i cache som `err`, genforsøg først næste kørsel; stop kørslen ved 429/captcha. |
| Modelforbrug pr. fase | ≈ 30–60 k tokens (kun styring og resultatlæsning) | Print aggregeret statistik, ikke rækker; stikprøver à 20 rækker. |
| Chatbot (hvis tilladt) | ≤ 200/dag, ≥ 30 sek. mellem | Kørsel i baggrunden med log; stop ved enhver fejl. |

## 5. Dataflow og filer

```
persons (entities.csv + role + gender + nationality + refs)
   └─ screen_persons_for_lex.py ──► data/curated/lex/persons_tiers.csv   (A/B/C + search_name + prof_target)
         │          ▲  nat_lex (tilbagekobling: udlænding → anden rute)
         │          └──────────── lex_page_facts (§3b: nat/erhverv/fødested-tags fra verifikationssiden)
         │                                         └─► data/curated/lex/person_nationality_lex.csv (forslag)
         │          DBL-bekræftet ──► data/curated/person_nationality_added.csv  («Dansk*», tilføjede data)
         ├─ lex_sitemap_match.py (Rute 1 + 1c: profession-/nationalitetsstyret) ──┐
         ├─ lex_chatbot_query.js (Rute 2) ──┼─► lex_link_candidates.py ──► persons_lex_links.csv (forslag)
         └─ wayback_dbl_lookup.py (Rute 3) ─┘        (slug-filter + 1 sidekald pr. kandidat)
                                                        │  gennemgang (stikprøve 10 %; alle «likely»)
                                                        ▼
                                          data/curated/person_lex.csv  (promoveret)
                                                        ▼
        build_persons_extra.py ► persons-extra.js `lex:[{w,u,a}]` ► persons.html / persons_en.html
```

`person_lex.csv`: `rid, work, url, url_display, archive_url, page_title, verified_on, verified_via, relaxed, reviewer`.
Test (`tests/test_person_lex.py`): ingen dublet-rid+værk; kun whitelistede værter; hver række har
`verified_via`; ingen link uden for niveau A/B; `url` er procent-kodet. Test for tag-udtræk
(`tests/test_lex_page_facts.py`, på gemte HTML-fixtures *uden* Lex-tekst — kun de mønstre, der skal
finde `var en {adj}`, initial-sætningsdeling og værksnavnsfilteret): «Dansk Biografisk Leksikon» giver
aldrig nationalitet, «C.E. Frijs var en dansk …» giver *dansk*.

**Visning:** i «Autoritetslinks» på persons-siden, én linje pr. værk, DBL først: *Dansk Biografisk
Leksikon ↗*, *Den Store Danske ↗* … (`target="_blank" rel="noopener noreferrer"`, `.sr-only`-varsling).
Arkivlink som lille «arkiveret»-tilføjelse. **Ingen** Lex-uddrag på siden.

## 6. Faser og beslutningspunkter

| Fase | Indhold | Færdig når | Afhænger af |
|---|---|---|---|
| **0** | Skriv til Lex (tilladelse til små kørsler + sitemap-brug; vilkår/licens for links og titler) | Skriftligt svar, eller beslutning om kun Rute 1 + manuel | — |
| 1 | `screen_persons_for_lex.py`; manuelle søgenavne for ≈ 60 personer | `persons_tiers.csv` med A/B/C; tjek af 30 tilfældige C (er de rigtigt udeladt?) | — |
| 2 | Rute 1: hent sitemap, byg slug-indeks, match A+B, verificér | Dækningsrapport pr. niveau/køn/nationalitet | 1 (+0 for download-omfang) |
| **2b** | **Nationalitet fra Lex-sider:** udvid `fetch_check`, genhent én side pr. bekræftet person, byg `person_nationality_lex.csv` (R1–R5, alle som *tilføjet*), opgør de umarkerede, der ikke er danske (tilføjede undtagelser), stikprøvetjek 10 % af R1/R2 | tags for alle bekræftede sider; konflikter med registret listet; test grøn | 2 |
| **2c** | **Profession-målrettet søgning:** `prof_target` + nationalitetsstyret rute; Teaterleksikon-profil (meta-årstal) **og kun for personer uden bekræftet DBL** (implementeret i `lex_sitemap_match.py`); kør kun relevante værter | ≈ +15–25 bekræftede; `relaxed`-rækker markeret | 2, 2b |
| **2d** ✔ | **DBL for hele registret** — *udført 2026-10-29:* 7.122 personer slået op, 903 bekræftet, 885 efter delt-artikel-regel, ≈ 2.900 sidekald; fem fejl fundet og rettet (cache pr. URL, slægtninge, pseudo-poster …); 10 %-stikprøve (88 rækker) venter på gennemgang | `person_nationality_added.csv` (885); `queue_dbl_review.csv` (143); `qa_dbl_sample.csv`; resultatnote | 2 |
| **2e** | **Kode og visning:** `build_persons_extra.py`, `facet-engine.js`, `persons*.html`, `nation.html`, tests (§3d-tabellen) | Stjerne + mouseover i facetten; tests grønne | 2d |
| 3 | Rute 2 for rest i A (≤ 200/dag), **nationalitetstilpasset prompt** | A-rest behandlet eller loft nået | 0, 2b, 2c |
| 4 | Rute 3 (Wayback) for danskere (nu også **fastlagt** af §3b) uden DBL | `archive_url` på de relevante rækker | 2–3 |
| 5 | Gennemgang → `person_lex.csv` → build + visning + test | Persons-sider viser links; tests grønne | 2–4 |
| 6 | Evaluering mod pilotens mål (≥ 90 % bekræftet i A, ≥ 95 % præcision i 10 %-stikprøven) | Rapport i `lex-dk-links-pilot.md` | 5 |

## 7. Forventet udbytte (ekstrapolation fra n = 50 — usikker)

* Niveau A (≈ 1.300): ~90 % med mindst ét bekræftet link ≈ 1.150; DBL for ca. halvdelen til
  to tredjedele (**danskere**), resten Den Store Danske/lex.dk-artikler (**udlændinge**).
* Niveau B (≈ 2.000): lavere hitrate (færre i DBL, mere perifere); regn med 30–50 % → 600–1.000.
* Samlet: **ca. 1.800–2.200 personer** med ≥ 1 lex.dk-link, ud af 10.228 — de resterende er
  bevidst udeladt.
  *(Niveau A er nu målt: 532 bekræftet via sitemap alene, se §3; skønnene for A og B er derfor
  forældede — B er ikke kørt og bør estimeres ud fra A's 28 % ved < 5 referencer.)*
* **Nationalitet (§3b):** ≈ 200–300 af de 661 umarkerede i A får en eksplicit nationalitet fra Lex
  (R1/R2), ≈ 70 yderligere et fødested; opgørelsen af, hvor mange umarkerede der er udlændinge, er
  i sig selv et resultat. For B (≈ 2.030 umarkerede) afhænger det af B's linkdækning (ikke målt).
* **«Dansk\*» (§3d):** i dag 87 personer med *dansk*; DBL-grænsen over hele registret gav **885** (957 med registrets egne) — fase 2d udført.
* **Profession-målrettet (§3c):** ≈ +15–25 bekræftede personer (målt +14 på 55 sidekald).

## 8. Åbne beslutninger

1. Skal fase 0 gennemføres *før* Rute 1 (sitemap-download)? (Anbefalet: ja, kort mail; sitemap'et er
   offentligt, men Lex ønsker kontakt om AI-brug.)
2. Må niveau B vises på siden (kun deterministisk match + sideverifikation, uden chatbot)?
3. Skal arkiv-links vises offentligt, eller kun gemmes som provenienssikring?
4. Hvem gennemgår «likely»/«mismatch» (pilot: 8 af 95 kandidater)?
5. Skal links også gælde *værker* og *steder* (lex.dk har artikler om begge)? — samme metode kan
   genbruges, men er ikke omfattet af denne plan.
6. ~~Nationalitet fra Lex~~ — **besluttet, se nedenfor.**
7. ~~Registrets «umarkeret = dansk»~~ — **besluttet, se nedenfor.**
8. ~~Vilkår for afledte fakta~~ — **besluttet, se nedenfor.**

### Besluttet 2026-10-29

| Spørgsmål | Svar | Konsekvens i planen |
|---|---|---|
| Må R1/R2 (eksplicit nationalitetsadjektiv fra Lex) fodre nationalitetsfacetten som *tilføjet* data efter 10 %-stikprøve? | **Ja** | §3b; fase 2b |
| Skal R4/R5 (fødested, DBL-optagelse) vises? | **Ja — nationalitet indhentet fra DBL angives som tilføjede data** | R5 giver «Dansk\*» (`nat_basis = dbl_optagelse`) — **præciseret samme dag**, se §3d; udenlandsk fødeland flages (R4) |
| Må «umarkeret = dansk» opgives? | **Ja — antagelsen er opgivet** (ændret 2026-10-29: først «fastholdes», senere «opgiv») | Umarkeret = *uoplyst*; «Dansk\*» er en afgrænset bucket med DBL som hård grænse, se §3d |
| «Dansk\*»: stjerne + mouseover «Født i Danmark eller bosat der i længere årrække» | **Besluttet** | §3d; kodeændringer i fase 2e |
| DBL som hårdt kriterium for «Dansk\*» | **Besluttet** | Lex-fund af «dansk» uden DBL-artikel kommer ikke i bucketen, men i en gennemgangskø |
| Skal Lex' vilkår for afledte fakta (nationalitet, erhvervsord, fødested-land) afklares ved henvendelsen? | **Ja** | Fase 0 spørger direkte (`chatbot@lex.dk`) |
| *(tillæg)* Gyldendals Teaterleksikon | **Kun for personer uden bekræftet DBL-artikel** | §2, §3c; indbygget i `lex_sitemap_match.py` |

Fortolkninger at bekræfte: (a) registrets egne 87 personer med *dansk* som ledende nationalitetsord regnes med i
«Dansk\*» (`register_beskrivelse`) — er DBL i stedet *eneste* vej ind, skal de ud; (b) personer med udenlandsk
registermarkering, der også står i DBL, får begge værdier. — Øvrigt: «de fire beslutninger» er læst som de fire spørgsmål, der blev tilføjet i revisionen
2026-10-29 (punkt 6 med to delspørgsmål, 7 og 8). De fem ældre punkter (1–5 ovenfor) er stadig åbne.
