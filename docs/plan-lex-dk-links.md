# Plan: lex.dk-links til danskere og kendte udlændinge i personregistret

Status: forslag 2026-10-28 · bygger på pilotens resultater i
[`data-model/lex-dk-links-pilot.md`](data-model/lex-dk-links-pilot.md) ·
hører sammen med [`plan-tidstavle-data.md`](plan-tidstavle-data.md) (del 2: eksterne data)

**Mål:** en verificeret, diskret ekstern henvisning fra en persons side til den mest udførlige
lex.dk-artikel om vedkommende — *Dansk Biografisk Leksikon* (DBL) først, derefter andre udførlige
værker. **Perifere personer udelades bevidst.** Kun links gemmes; ingen Lex-tekst kopieres.

## 1. Principper og grænser (gælder hele planen)

| Princip | Konkret |
|---|---|
| Faktakontrol (`CLAUDE.md`) | Intet link skrives, før både navn *og* begge levedatoer er set på artiklens egen side. Chatbottens svar er et forslag, aldrig en kilde. |
| Kun kilde-kort, aldrig fritekst-URL'er | Piloten viste, at chatbotten opfinder slugs, når den bedes om et «link». |
| Ingen Lex-indhold i repoet | Rå svar og sidetekst committes ikke. Gem: URL, værk, sidetitel, verifikationsflag, dato. |
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

Script (ingen netværk): `scripts/parsers/screen_persons_for_lex.py` → `data/curated/lex/persons_tiers.csv`
(`rid, tier, reason, refs, gender, nationality, search_name`). Kolonnen `search_name` fyldes manuelt
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
  *DBL > Dansk Kvindebiografisk > Weilbach > Den Store Danske > Danmarkshistorien > øvrige lex.dk*,
  og matcher slugs mod persons `search_name` med `slug_matches()` fra `lex_link_candidates.py`
  (tåler forkortelser, bindestreger, initialer).
* **Verifikation:** ét sidekald pr. kandidat (1 forespørgsel/sek., cache) — titel + begge årstal.
  Sitemap'et har ingen levetid, så navnebrødre (`A.S._Ørsted_-_jurist`) afgøres kun her.
* **Omkostning:** ≈ 1 download à 45 MB + ca. 2–5 verificeringsforespørgsler pr. person i A/B
  (≈ 3.300 personer × ~3 = ca. 10.000 sidekald ≈ 3 timer ved 1/sek.). Ingen chatbot, ingen tokens.

### Rute 2 — Lex' chatbot, kun til resten i niveau A

* Anvendes for personer, hvor Rute 1 ikke finder en slug (navnevarianter, udlændinge med ikke-
  danske slugs, usikre navnebrødre).
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

## 4. Token- og forespørgselsbudget

| Post | Størrelse | Håndtering |
|---|---|---|
| Rå chatbot-svar | ≈ 9,7 kB/person (≈ 490 kB for 50; ≈ 12,5 MB for 1.287) | **Aldrig ind i modelkonteksten** (≈ 3 mio. tokens). Scripts kører selvstændigt; kun CSV-opsummeringer læses. |
| Sitemap-filer | ≈ 45 MB | Parses af script; kun resultatlister (≤ 200 kB) vises. |
| Verifikations-sidekald | ≈ 10.000 forespørgsler, 1/sek. | Cache i `data/raw/lex/page_cache.json`; aldrig genhent. |
| Wayback | ≲ 600 forespørgsler | Cache; backoff ved 5xx. |
| Modelforbrug pr. fase | ≈ 30–60 k tokens (kun styring og resultatlæsning) | Print aggregeret statistik, ikke rækker; stikprøver à 20 rækker. |
| Chatbot (hvis tilladt) | ≤ 200/dag, ≥ 30 sek. mellem | Kørsel i baggrunden med log; stop ved enhver fejl. |

## 5. Dataflow og filer

```
persons (entities.csv + role + gender + nationality + refs)
   └─ screen_persons_for_lex.py ──► data/curated/lex/persons_tiers.csv   (A/B/C + search_name)
         ├─ lex_sitemap_index.py (Rute 1) ──┐
         ├─ lex_chatbot_query.js (Rute 2) ──┼─► lex_link_candidates.py ──► persons_lex_links.csv (forslag)
         └─ wayback_dbl_lookup.py (Rute 3) ─┘        (slug-filter + 1 sidekald pr. kandidat)
                                                        │  gennemgang (stikprøve 10 %; alle «likely»)
                                                        ▼
                                          data/curated/person_lex.csv  (promoveret)
                                                        ▼
        build_persons_extra.py ► persons-extra.js `lex:[{w,u,a}]` ► persons.html / persons_en.html
```

`person_lex.csv`: `rid, work, url, archive_url, page_title, verified_on, verified_via, reviewer`.
Test (`tests/test_person_lex.py`): ingen dublet-rid+værk; kun whitelistede værter; hver række har
`verified_via`; ingen link uden for niveau A/B.

**Visning:** i «Autoritetslinks» på persons-siden, én linje pr. værk, DBL først: *Dansk Biografisk
Leksikon ↗*, *Den Store Danske ↗* … (`target="_blank" rel="noopener noreferrer"`, `.sr-only`-varsling).
Arkivlink som lille «arkiveret»-tilføjelse. **Ingen** Lex-uddrag på siden.

## 6. Faser og beslutningspunkter

| Fase | Indhold | Færdig når | Afhænger af |
|---|---|---|---|
| **0** | Skriv til Lex (tilladelse til små kørsler + sitemap-brug; vilkår/licens for links og titler) | Skriftligt svar, eller beslutning om kun Rute 1 + manuel | — |
| 1 | `screen_persons_for_lex.py`; manuelle søgenavne for ≈ 60 personer | `persons_tiers.csv` med A/B/C; tjek af 30 tilfældige C (er de rigtigt udeladt?) | — |
| 2 | Rute 1: hent sitemap, byg slug-indeks, match A+B, verificér | Dækningsrapport pr. niveau/køn/nationalitet | 1 (+0 for download-omfang) |
| 3 | Rute 2 for rest i A (≤ 200/dag) | A-rest behandlet eller loft nået | 0, 2 |
| 4 | Rute 3 (Wayback) for danskere uden DBL | `archive_url` på de relevante rækker | 2–3 |
| 5 | Gennemgang → `person_lex.csv` → build + visning + test | Persons-sider viser links; tests grønne | 2–4 |
| 6 | Evaluering mod pilotens mål (≥ 90 % bekræftet i A, ≥ 95 % præcision i 10 %-stikprøven) | Rapport i `lex-dk-links-pilot.md` | 5 |

## 7. Forventet udbytte (ekstrapolation fra n = 50 — usikker)

* Niveau A (≈ 1.300): ~90 % med mindst ét bekræftet link ≈ 1.150; DBL for ca. halvdelen til
  to tredjedele (**danskere**), resten Den Store Danske/lex.dk-artikler (**udlændinge**).
* Niveau B (≈ 2.000): lavere hitrate (færre i DBL, mere perifere); regn med 30–50 % → 600–1.000.
* Samlet: **ca. 1.800–2.200 personer** med ≥ 1 lex.dk-link, ud af 10.228 — de resterende er
  bevidst udeladt.

## 8. Åbne beslutninger

1. Skal fase 0 gennemføres *før* Rute 1 (sitemap-download)? (Anbefalet: ja, kort mail; sitemap'et er
   offentligt, men Lex ønsker kontakt om AI-brug.)
2. Må niveau B vises på siden (kun deterministisk match + sideverifikation, uden chatbot)?
3. Skal arkiv-links vises offentligt, eller kun gemmes som provenienssikring?
4. Hvem gennemgår «likely»/«mismatch» (pilot: 8 af 95 kandidater)?
5. Skal links også gælde *værker* og *steder* (lex.dk har artikler om begge)? — samme metode kan
   genbruges, men er ikke omfattet af denne plan.
