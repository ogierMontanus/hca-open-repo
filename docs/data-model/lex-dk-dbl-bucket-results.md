# «Dansk\*»-bucketen via DBL — fase 2d (hele registret)

Status: kørt 2026-10-29 · plan: [`../plan-lex-dk-links.md`](../plan-lex-dk-links.md) §3d ·
resultat: `data/curated/person_nationality_added.csv` (**tilføjede data**, ikke i registrets egne felter) ·
værktøjer: `scripts/parsers/lex_sitemap_match.py --tier all --hosts dbl`,
`scripts/parsers/build_person_nationality_added.py`

**Beslutning bag (2026-10-29):** «umarkeret = dansk» er opgivet. Værdien *dansk* får en stjerne, med mouseover
«Født i Danmark eller bosat der i længere årrække», og **bekræftet DBL-artikel er hårdt kriterium** for at komme
i bucketen. Her er DBL slået op for **alle** personer, der *kan* verificeres (levetid + fornavn).

## Resultat

| | Personer |
|---|---:|
| Personer slået op (levetid + fornavn, uden «–»-henvisninger) | 7.122 |
| … med mindst ét DBL-slug i sitemap'et | 1.964 (28 %) |
| **Bekræftet DBL-artikel** (navn + begge levetidsår på artiklens egen metabeskrivelse) | 903 |
| … heraf fjernet, fordi artiklen deles med en slægtning (se nedenfor) | − 18 |
| **«Dansk\*» via DBL (`person_nationality_added.csv`)** | **885** |
| ↳ niveau A / B / C | 324 / 333 / 228 |
| ↳ med udenlandsk registermarkering *også* (får begge værdier) | 19 |
| Registrets egne *dansk* (ledende nationalitetsord) | 87 (15 også i DBL) |
| **Bucketen «Dansk\*» = DBL ∪ registrets egne** *(min læsning, se plan §8)* | **957** |
| Gennemgangskø (`queue_dbl_review.csv`) | 143 personer (128 «sandsynlig» · 18 delt artikel) |
| Ikke verificérbare (ingen levetid 3.034 · kun «–»-henvisning 265 · intet fornavn) | uden for bucketen |

Skønnet i planen (700–900) holdt: **885**. Det er 12,4 % af de personer, der kan verificeres. De øvrige ca. 9.300
personer er *uoplyst* (ikke «ikke-danske»).

**Omkostning:** ≈ 2.900 sidekald i alt (1/sek., ≈ 75 min) fordelt på tre kørsler (to var genkørsler efter fejl, se
nedenfor) + 12 til at afgøre delte artikler. Ingen chatbot, ingen 429/5xx.

## Fejl fundet og rettet undervejs (hver fanget af stikprøven, ikke af testene)

| # | Fejl | Virkning | Rettelse |
|---|---|---|---|
| 1 | **Pseudo-poster** med etiket «– Se også: Wulff, Ida (…)» / «- Hans Hustru» blev matchet som personer | 265 sådanne poster i registret | ny screeningsårsag «henvisning»; udelukkes |
| 2 | **Cachen gemte verdiktet pr. URL, ikke pr. person.** Slægtninge, der slår samme artikel op, arvede den første persons «bekræftet» (*Jens Baggesen* → søn; *Steen Bille* → to yngre Steen Billes) | **51 falske bekræftelser** i DBL-kørslen (954 → 903); ramte også niveau A (532 → 523) og Dansk Kvindebiografisk (27 → 17) | cachen gemmer nu **artiklens årstal** (`ys`) og verdiktet beregnes pr. person (`judge()`); 271 delte URL'er blev hentet igen |
| 3 | DBL-sidens *indledning* indeholder også **forældrenes årstal** («Forældre: …»), så slægtninge blev bekræftet | relativer som *J. Reinhardt* ↔ *J. Th. Reinhardt* | DBL verificeres mod artiklens **egen** `meta description` (personens datoer står først); ellers markeres rækken `~` (1 række) |
| 4 | Forkortelser i sluggen («J._**Th.**_Reinhardt») blev ikke krævet forklaret | forkert match af en person med færre fornavne | hvert led i sluggens navnedel (≥ 2 tegn) skal kunne forklares af personens fornavne |
| 5 | En artikel kan **kun tilhøre én** registerperson, men flere kunne bekræftes (*H.C. Ørsted* og barnebarnet) | 30 rækker | ved delt artikel beholdes kun den, hvis levetid er artiklens **første to årstal**; resten → gennemgangskø |

## Stikprøvekontrol

* Tilfældige rækker blev læst igennem (etiket mod DBL-titel): 40 + 35 før rettelserne (fandt fejl 1, 3 og 4) og 35 + 25
  efter rettelse 2–5 — i de sidste 60 **ingen kendte fejl** (ét afvigende fornavn: *Ross, Sir John* → «John Ross», titlen «Sir» — ok).
* `data/curated/lex/qa_dbl_sample.csv` er en **tilfældig 10 %-stikprøve (88 rækker)** med tom `decision`-kolonne
  til menneskelig gennemgang; **præcisionen er ikke målt, før den er udfyldt.**

## Begrænsninger

* **Navnebrødre med samme levetid** udelukkes ikke af årstalskontrollen (kun af slug-reglerne og delt-artikel-reglen).
* DBL-meta indeholder personens egne datoer først, men formatet er ikke garanteret; én række bruger reservevinduet.
* **Ingen levetid → ingen verifikation → ikke i bucketen**, selv om personen kan være i DBL (3.034 poster).
* «Dansk\*» er *kun* defineret ved DBL-optagelse (og registrets egne 87); en person, der er dansk men ikke i DBL, er
  **uoplyst** — netop konsekvensen af den hårde grænse.
* Registerdubletter (samme person to gange med forskellig levetid) kan give samme DBL-artikel til én af dem, hvis
  levetiden matcher; den anden går til gennemgangskøen.
