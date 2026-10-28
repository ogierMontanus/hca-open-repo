# Kildeanalyse: database og PDF (leverance A og B)

Status: 2026-10-27 · branch `almanac-extract` · tal genereres af
`almanak/scripts/analysis/` (se [`../README.md`](../README.md)).

Notation: **[billede]** = kontrolleret mod PDF'ens sidebillede, **[OCR]** =
kun belagt af tekstlaget (ikke billedkontrolleret), **[DB]** = kun databasen.
Sidetal er trykte sider (PDF-side = trykt side + 12).

---

## 1. Hvad der faktisk findes

### 1.1 Databasen (`SRC-DB`, tabel `almanak`)

```sql
CREATE TABLE `almanak` (
  `Dato` varchar(20) NOT NULL DEFAULT '0000-00-00',   -- PRIMARY KEY + FULLTEXT
  `Tekst` text NOT NULL,                                -- FULLTEXT
  `Timestamp` timestamp ...
) ENGINE=MyISAM DEFAULT CHARSET=latin1;               -- indholdet er reelt UTF-8
```

| Egenskab | Fund |
|---|---|
| Rækker | **5.163**, én pr. dato, 1833-02-02 – 1873-06-22, 32 årgange (ingen 1835–36, 1839, 1848, 1852, 1864, 1868–69, 1872) |
| Struktur | Kun dato + fritekst. Ingen sidehenvisning, ingen ugedag, ingen markering af position (dagsblad / trykt kalendertekst / bagside / foran-bag i bindet), ingen afsnit eller underafsnit |
| Relationer | Ingen fremmednøgler. Andre tabeller omtaler almanakken kun i fritekst (≈50 noter i `brevnote`, fx »almanak 2.10.: Brev fra .. Frøken Heinke«; flere poster i `tidstavle_data`); `links` peger på KB's almanakudgave |
| Ugyldige nøgler | `1849-04-00`, `1854-12-00` (dag 00) |
| Tomme poster | `1834-07-01`, `1862-01-24` |
| Redigeringsspor | 4.211 rækker har tidsstempel 2006-04-24 (masseimport); ≈950 er ændret 2007–2019 (fx 234 på 2007-07-29, 96 på 2015-10-05/06). Ifølge projektet er det rettelser af indtastningsfejl, højst efter 1990-udgaven — **ikke** efter håndskriftet. Databasen er altså ikke et selvstændigt vidne til håndskriftet |
| Markup | 2 HTML-tags (`<em>`, `<brevlink>18080</brevlink>`), 15 bløde bindestreger (Word-rester) |
| Registrering | Ingen: hverken person-, værk- eller stedregistre er koblet til posterne |

Websitet andersen.sdu.dk/liv/almanak (Lars Bo Jensen 2007, opdateret 2019)
præsenterer databasen som en gengivelse af 1990-udgaven og henviser til KB's
udgave for registre og faksimiler.

### 1.2 PDF'en (`SRC-PDF`)

| Egenskab | Fund |
|---|---|
| Opbygning | 400 sider à 387 × 548,75 pt; hver side ét JBIG2-gråtonebillede + usynligt ABBYY-tekstlag. Ingen bogmærker/indholdsfortegnelse, ingen sidelabels |
| Indhold | Forord (DSL), Introduktion (redaktionelle principper), almanaktekst s. 1–327, **Værkregister** s. 328–338 (kun Andersens egne værker), **Personregister** s. 339–388 |
| Sidelayout | Levende kolumnetitel (måned + år), centrerede kursive års- og månedsoverskrifter, dagsposter med ugedag i kapitæler + dagnummer i venstre margen, hængende indrykning |
| Afvigende formater | 1834 og 1837 uden ugedag (»15. forlod Florents.«, »den 3die«); januar 1838 med ugedag og dagnummer som separate tekstlinjer; datointervaller (»TI-ON 17.-18. Milano«, 1856) |
| Udaterede blokke | »[Foran i almanakken:]« (adresser, vers), »[Bag i almanakken:]« (møntforhold, honorarnotater), »[Over/Under den trykte almanaktekst:]« (månedsmottoer), »[På bagsiden af bladet:]«, »[Indklæbet …]«. Mindst 53 positionsmarkører + 10 over/under-markører |
| Redaktionelle tegn (Introduktion s. xiii) | `[…]` = udgiversupplering; `[...]`/`[konjektur?]` = ulæselig/usikker; `[ɔ: …]` = forklaring; punktum efter hver dags indførsel er udgiverens; overstregninger gengives ikke |
| OCR-kvalitet | God på løbende tekst, systematisk svag på gammeldags tal og enkelte glyffer (afsnit 3.2) |

Segmentering af tekstlaget (`extract_pdf_entries.py`) giver **5.185** daterede
poster. 5.081 har OCR-dagnummer og ugedag i overensstemmelse med kalenderen;
22 er udledt af ugedagen alene; 18 har ugedag i strid med kalenderen; 64 er
1834/1837-poster uden ugedag. 588 tekstlinjer er udaterede (adresser, vers,
registerlignende lister, parserrester).

---

## 2. Udsnit og metode

Sammenligningen er lavet **for hele materialet** maskinelt (alle 5.163 + 5.185
poster, alignet på dato) og **for et repræsentativt udsnit manuelt** mod
sidebilledet. Udsnittet dækker alle formattyper og perioder:

| Trykt side | Periode | Hvorfor |
|---|---|---|
| 1 | feb.–apr. 1833 | Første årgang, mærkedage, †-tegn |
| 7 | apr.–jun. 1834 | Format uden ugedage |
| 34, 36 | jan.–feb. 1840 | Tæt københavnsk tekst |
| 96 | dec. 1842 | Trykt ugedag i strid med kalenderen |
| 130 | jun. 1844 | Datoforskydning i DB |
| 135 | sep.–okt. 1844 | Markøren »[I den trykte almanaktekst:]« |
| 139 | nov. 1844 | Dobbelt dagnummer i trykket |
| 160 | okt.–nov. 1845 | Huller i DB |
| 183 | okt.–nov. 1846 | Weekendposter (parserkontrol) |
| 231 | jan. 1855 | Byttede datoer i DB |
| 264 | jun.–jul. 1858 | Rejseår, stednavne |
| 272 | mar. 1859 | Kursiv og udgiverklammer |
| 296 | dec. 1860 | Brevnotater (sene, sparsomme år) |

Den maskinelle kollation måler lighed efter normalisering (`ratio_loose`
folder store/små bogstaver, tegnsætning og OCR-forvekslingerne 1/i, 0/o) og
tæller ord-/tegnforskelle (`token_diff_ops`).

---

## 3. Sammenligning pr. parameter

### 3.1 Tekstlig fuldstændighed

| | Fund | Omfang |
|---|---|---|
| DB mangler hele dage | 24 dage **1845-10-24 – 11-16** (s. 160–161) [billede]; 8 dage **1847-10-01 – 10-09** (s. 194) [OCR]; enkeltdage 1834-07-21, 1841-06-09, 1841-06-10, 1842-09-29, 1853-07-04, 1854-09-25, 1856-05-16, 1861-03-27, 1871-11-15 [OCR] | **41 daterede poster** uden modstykke |
| DB mangler indhold i en post | Mindst 45 poster er >15 % kortere end trykket, typisk afkortet sidste sætning: 1844-09-21/22 — DB har flyttet slutningen af den 21. over på den 22. og udeladt den 22.'s egen tekst (»Hertugindens Geburtsdag; Væddeløb …«) [billede]; 1840-04-02, 1841-12-16, 1842-09-30, 1859-12-16 [OCR]; 1871-05-23 mangler »Louise Melchior« [OCR] | ≈45 |
| DB mangler udaterede blokke | Alle »Foran/Bag i almanakken«, bagsider, mottoer over trykt tekst, indklæbede notitser. Registrene henviser 29 gange til »Bagsiden af …« | ≈60 blokke |
| DB mangler registre | Intet person- eller værkregister | ≈1.700 personopslag (skøn), ≥3.800 datohenvisninger |
| DB har mere end trykket | 1833-02-16 »brev til Henriette Wulff« findes ikke på s. 1 [billede]. Da DB ikke bygger på håndskriftet, er det en senere tilføjelse af ukendt oprindelse (brevbasen?) — ikke almanaktekst | 1 sikker |
| PDF-tekstlaget mangler | Intet systematisk; årsoverskrifter for 1833, 1838, 1854, 1855 mangler i tekstlaget (ikke i billedet) | — |

**Bedst: PDF** (gælder hele materialet).

### 3.2 Tekstlig korrekthed

Af 5.133 datoer i begge kilder er 2.840 ord-for-ord identiske efter
normalisering; 5.063 (98,6 %) har `ratio_loose` ≥ 0,9. Der er i alt **3.340
forskelssteder** fordelt på ≈2.290 poster. De skyldes fejl i *begge* lag:

**Databasens fejl** (indtastning og redigering):

| Type | Eksempler |
|---|---|
| Tastefejl | »Berneer« for Berner, »Vilstup« for Vilstrup, »selt« for slet, »Hødt« for Høedt (1840, s. 34/36) [billede]; »Brounonvile«, »Beøsg« (1844-10-05/03) [billede]; »Midag«, »Bev«, »Baling«, »Liutenant«, »Igar«, »Solksin«, »Mechiors«, »Fødselsag« [OCR] |
| Modernisering/normalisering | »Ensomhed« for Eensomhed, »Søndagsnummeret« for Søndagnummeret [billede]; »én« for een, »–« for -, »død« for † (1853-07-06, 1860-05-11), ½ for 1/2, ” for » « |
| Tegnsætning der ændrer mening | 1840-01-27 »leverede jeg til Generalprøve« — trykket: »leverede jeg til. Generalprøve« [billede] |
| Ombyttet brevretning | 1860-12-01 »Brev til Clara Heinke« — trykket: »Brev fra« [billede]; 8 andre konflikter til/fra (1858-05-20, 1859-04-22, 1859-06-15, 1859-09-16, 1860-07-27, 1860-10-24, 1862-11-13, 1866-07-17) [OCR] |
| Forkert stednavn | 1858-06-25 »Heidelberg til Frankfurt« — trykket: »Freiburg« [billede] |
| Dobbelttekst | 1846-02-09 gentager 02-08 [OCR]; 1856-12-16 = 12-17; 1866-08-26 »Brev til Robert Watt, Brev til Robert Watt« |
| Tabte udgivertegn | »Galleriet [nær]« → »Galleriet nær«; »Min[e]« → »Mine« (1859-03-24) [billede]; 113 `[` i DB mod 187 i PDF; »[I den trykte almanaktekst:]« 73 mod 88; `[ɔ: …]` gengives inkonsekvent (»[c:«) |
| Umarkerede tilføjelser | »[Der skal stå Africa]« (1853-12-01), »[=Edmund von Hartig]« (1854-03-14), »[Schellings]« (1858-07-05; trykket har kun »Schillers Grav« [billede]), »[er ikke i Scavenius-brevene]« (1860-01-07), `<brevlink>` (1859-03-13). Værdifulde kommentarer, men blandet ind i teksten uden proveniens |

**OCR-lagets fejl** (systematiske, forudsigelige):

| Mønster | Eksempler |
|---|---|
| Gammeldags tal | 1→i (»iste«=1ste, 31 gange), 18→»tå«, 11→»ii«, 10→»IO«, 19→»'9«, 3/5/9 forveksles i årstal (»1833« for 1853 i kolumnetitlen) |
| Glyffer | †→f, +→»4-«/»-I-«, ü→ii (»Voclabriick«), I→l (»laften«), ø→o (»Fløttet«→»Flottet«) |
| Bogstavklynger | lt→k (»Mokke« for Moltke, mindst 11 gange), lc→ic (»Hoicks«) [billede] |
| Kapitæler | LØ/SØ læst som »L0«/»S0«, MA som »må« |

**Trykkets egne problemer** (findes i begge lag):

| Sted | Problem | Kan afgøres? |
|---|---|---|
| 1842-12-28/29 (s. 96) | »FR 28«, »LØ 29«; kalenderen giver onsdag/torsdag [billede] | Nej — kun håndskriftet kunne afgøre det, og KB's faksimiler er offline |
| 1844-11-27 (s. 139) | »ON 27« og »TO 27«, derefter »FR 28 … SØ 30« med ugedage forskudt én dag [billede]. DB har læst dagnumrene bogstaveligt og udeladt »Mat. Middag hos Ørsted med Høyen, Sibbern &.« | Nej — som ovenfor |
| 18 poster i alt | Ugedag ≠ kalender | Nogle er OCR-fejl (afgøres mod billedet); resten er trykkets og forbliver markeret som uafgjort |

**Bedst: ingen alene.** Trykkets *billede* er facit. Databasen er bedst på
de glyffer OCR fejler (tal, ü, †, ½), PDF-tekstlaget er bedst på ordlyd,
fuldstændighed og udgivertegn. Konklusionen gælder hele materialet for de
målte mønstre; de enkelte eksempler er kun billedkontrolleret i udsnittet.

### 3.3 Strukturel korrekthed

| Fund | Kilde |
|---|---|
| **20 DB-poster står på forkert dato** i forhold til trykket: 1833-08-24→25, 1834-04-05→04, 1838-09-10→09, 1844-06-26…30→25…29 (blok på 5) [billede], 1846-02-09, 1846-09-27/28, 1849-04-00→04, 1854-12-30→31, 1855-01-07↔12 (ombyttet) [billede], 1855-03-14→18, 1856-06-20→21, 1856-12-17→16, 1858-12-28→30, 1859-12-04→09. Hertil 1844-11-28/29, som afhænger af den uafklarede trykfejl | DB |
| DB opløser trykkets intervaller (»17.-18. Milano« → to rækker) og placerer udaterede notater på en dato (»28 April Fru Serres Fødselsdag« står i trykket efter 30. april → DB 1857-04-28; mottoet »I Vel og Vee …« → `1854-12-00`) | DB-fortolkning |
| DB har ingen position: tekst skrevet *i den trykte kalendertekst* er kun kendelig, hvor markøren er bevaret (73 af 88) | DB |
| PDF bevarer år → måned → dag → (position) og sidegrænser; strukturen er rekonstruerbar maskinelt for ≈99,5 % af posterne (afsnit 1.2) | PDF |

**Bedst: PDF** (hele materialet). Databasens dato-nøgle er dog den eneste
eksisterende *stabile* identifikator udadtil.

### 3.4 Registreringsdybde

| Oplysning | DB | PDF |
|---|---|---|
| Dato | eksplicit (ISO) | afledt (overskrifter + dagnummer) |
| Trykt ugedag | — | ja (kontrolværdi) |
| Side | — | ja |
| Position i almanakken | — | ja (udgivermarkører) |
| Udgiverens tekstkritiske tegn | delvis | ja |
| Personer (identifikation, levetid, usikkerhed »(?)«, »+« = ikke i Dagbøger XI) | — | ja, i Personregistret |
| Andersens værker (med henvisning til B.F. Nielsens bibliografi) | — | ja, i Værkregistret |
| Steder | — | — (intet stedregister) |
| Senere kommentarer, brevkoblinger | få, umarkerede | — |

**Bedst: PDF** (registrene er den største merværdi). Databasens tilføjelser er
få men unikke.

### 3.5 Søgbarhed og genanvendelighed

Databasen er straks maskinlæsbar (ISO-dato, fritekst, FULLTEXT-indeks).
PDF'en er det først efter segmentering og OCR-rettelse — men segmenteringen
er allerede vist mulig. Registrene kræver parsing svarende til den, repoet
har gjort for Dagbøger XI.

**Bedst i dag: DB. Bedst efter bearbejdning: PDF + registre.**

### 3.6 Kildekontrol

5.133 af 5.163 DB-poster (99,4 %) kan entydigt kobles til en trykt side via
datoen; yderligere 20 via tekstlighed inden for ±7 dage. Resten er tomme,
ugyldige eller fortolkende rækker (1834-rejseoversigten, intervaller,
udaterede notater). DB-posterne har selv ingen sidehenvisning, så kontrol
kræver altid PDF'en.

**Bedst: PDF** (eneste kilde med side). Koblingen DB→side er robust.

### 3.7 Fejl og usikkerhed — sammenfatning

| Kategori | DB | PDF-tekstlag | Trykket selv |
|---|---|---|---|
| Dokumenterede fejl | tastefejl, datoforskydninger, ombyttet til/fra, dobbelttekst, afkortninger | systematiske OCR-fejl | ugedags-/dagnummerfejl |
| Manglende data | 41 dage, ≈60 udaterede blokke, registre | årsoverskrifter i 4 årgange | — |
| Strukturelle forskelle | intervaller opløst, udaterede notater dateret | — | — |
| Uafgørligt (håndskriftet utilgængeligt) | oprindelsen af 1833-02-16 | — | 1842-12-28/29, 1844-11-27ff og øvrige ugedagskonflikter |

---

## 4. Vurdering

| Parameter | Bedst | Grundlag | Gælder | Forbehold |
|---|---|---|---|---|
| Fuldstændighed | PDF | 41 manglende dage, udaterede blokke, registre | hele materialet | PDF-segmenteringen kan selv overse poster i usædvanligt layout (1834) |
| Korrekthed | sidebilledet; DB og OCR som to vidner | 3.340 forskelssteder; fejltyper i begge | mønstre: hele materialet; enkeltfund: udsnit | Tallene gælder den nuværende OCR; en ny scanning er bestilt |
| Struktur | PDF | 20 datoforskydninger i DB; position og side kun i PDF | hele materialet | 18 trykte ugedagskonflikter |
| Registreringsdybde | PDF | person- og værkregister | hele materialet | registrenes årstal er dårligt OCR'et |
| Søgbarhed nu | DB | ISO-datoer, ren tekst | — | forsvinder når PDF er bearbejdet |
| Kildekontrol | PDF | sidetal, markører | hele materialet | — |

## 5. Anbefaling af datagrundlag (leverance B)

Tre strategier er vurderet:

1. **DB som grundlag, PDF som kontrol.** Forkastes: ville arve 41 manglende
   dage, 20 forkerte datoer, tabte udgivertegn og ingen side eller registre.
   Hver eneste post skulle alligevel kontrolleres mod PDF'en.
2. **PDF som grundlag, DB-felter overført.** Næsten rigtig, men databasen har
   kun ét felt (teksten) — der er ingen strukturerede felter at overføre.
   Dens værdi er som *uafhængig læsning* af samme tekst, ikke som felter.
3. **Kombineret tredje version.** **Anbefales.**

**Valg:** En kombineret version, hvor **1990-udgaven, som den står på
sidebilledet, er tekstlig autoritet**, og **struktur, side og registre
hentes fra PDF'en**. Teksten etableres ved **kollation af to vidner** — det
rettede OCR-lag og databasen. Hvor de er enige, accepteres læsningen; hvor de
er uenige, afgøres det mod sidebilledet (mekanisk for kendte OCR-mønstre,
manuelt for resten). Databasens `Dato` bevares som ekstern nøgle, og dens
tilføjelser bevares som et separat, mærket kommentarlag.

Forbehold og afklaringer (opdateret 2026-10-27):

* Databasens ≈950 ændringer efter 2006 er rettelser af indtastningsfejl, højst
  efter 1990-udgaven. Databasen har derfor ingen selvstændig autoritet over for
  trykket: hvor dens *tekst* afviger fra sidebilledet, er det en DB-fejl. Dens
  *tilføjelser* (glosser, brevlinks) er redaktionelle og bevares som
  annotationer.
* Håndskriftet er utilgængeligt (KB's faksimileudgave er offline). Trykkets
  egne fejl (ugedage, dobbelt dagnummer) gengives som trykt og markeres
  uafgjorte; de rettes ikke.
* 1990-teksten må publiceres i repoet.
* En ny OCR-scanning er bestilt. Den ændrer ikke anbefalingen, men forventes
  at gøre en stor del af kollationsarbejdet i trin 3 overflødigt. Den måles mod
  basislinjen i [`../sources/baseline-2026-10-27.json`](../sources/baseline-2026-10-27.json).

Den konkrete model er beskrevet i [`kombineret-version.md`](kombineret-version.md).
