# Registertegnet »÷« i almanakregistrene — aflæsning og brug ved samkøringen med Dagbøgerne

*2026-11-24. Optisk kontrol udført; samkøringen (§5) er en plan.*

## 1. Hvad tegnet betyder

1990-udgaven af almanakkerne (Topsøe-Jensen, DSL) har to registre, og begge bruger divisionstegnet **»÷«**
(ikke »%« eller »+«; se gengivelsen af forklaringerne på PDF s. 340 og 351):

| register | forklaring i udgaven (ordret) | kolonne |
|---|---|---|
| Personregister (PDF s. 351–400) | »For navne uden oplysninger henvises til personregisteret i H.C. Andersens Dagbøger, bd. XI, 1977. ÷ efter et navn, med eller uden oplysninger, betegner, at personen ikke forekommer i ovennævnte register, eller ikke er identificeret.« | `almanak_register_persons.csv` → `not_in_xi` |
| Værkregister (PDF s. 340–350) | »Titlerne er så vidt muligt formuleret som i Birger Frank Nielsen: H. C. Andersen Bibliografi. Digterens danske Værker 1822-1875. 1942. ÷ ved en titel betegner, at den ikke findes i bibliografien.« | `almanak_register_works.csv` → `not_in_bfn` |

Projektets personregister (`Reg…`-id'er i `data/normalized/entities.csv`) bygger på netop Dagbøger bd. XI. Tegnet
fortæller altså, om et almanakopslag *skal* have et modstykke i vores register eller ej.

Placering: i personregistret står »÷.« lige før henvisningerne (»Moltke, grevinde. ÷. *1845* 21.7.«). I værkregistret
står det oftest *efter* henvisningerne (»Sang til Bregentved. *1845* 18.9. ÷«), og ét opslag har det foran flere
årstalsgrupper (»Til Jonas Collin«, 4 gange); vi antager, at tegnet dækker alle titler i opslaget (beslutning 2026-11-24).

**Det ægte »+«** (kun i værkregistret, 9 steder; ikke forklaret i udgaven) står *altid* foran en henvisning uden dato —
»Bagsiden af <måned>« eller »Bag i almanakken« — og knytter den til den foregående årstalsgruppe: »*1860* 16.11.
+ Bagsiden af Februar« = i almanakken for 1860 dels 16.11., dels bagsiden af februarbladet. Hvor stedet står lige
efter et årstal, er der intet »+« (»*1845* Bag i almanakken«). »+« betyder altså »samt, i samme årgang«. De 9 steder:
Fjerde Samling (1859, »+ Bagsiden af October og December«), Bispen paa Børglum (1860, februar), Nytaarsmorgen
(1860, februar), Lidén Kirsten (1859, »+ Bagsiden af Maj og N…«), en titel på s. 348 (1845, bag i almanakken), Nøkken (1845),
en oversættelsesliste på s. 349 (1860), Improvisatoren (1845) og Bertel Thorvaldsen (1845). Parseren gør det samme:
stedhenvisningen arver årstallet fra gruppen foran (`kind` = `bagside`/`bag`). OCR læser det som »+« eller »-I-«; det er
ikke divisionstegnet og påvirker ikke `not_in_bfn`.

## 2. Hvad OCR'en har gjort ved tegnet

Tekstlaget kender ikke »÷«. Ved optisk kontrol (§3) står der følgende i tekstlaget, hvor billedet har »÷«:

| OCR-form | personregister | værkregister |
|---|---:|---:|
| `4-.` / `4-` / `4-,` | 198 / 15 / 28 | 5 / 17 / – |
| `-r.` / `-r` | 24 / 8 | – / 6 |
| `+.` / `+` | 16 / 17 | – / 7 |
| `-5-.` | 18 | – |
| `-4-.` / `-4-` / `-4.` / `4"` / `-i-.` / `-i-` | 8 / 1 / 2 / 1 / 4 / – | – / 2 / – / – / – / 1 |
| **intet** (tegnet tabt, kun punktummet står: `sproglærer. . 1843`) | **25** | **13** |
| andet (`1843`, `7:`, `—.`, `-.`, `y`, `6.1.—`) | 4 | 2 |
| **i alt** | **369** | **53** |

Mønsteret `\s\.{1,3}\s*18\d` (et løst punktum foran årstallet) er den tabte form; den kan ikke skelnes fra et
almindeligt punktum i tekstlaget alene. Tekstlagets gæt (den gamle regel i `parse_register.py`) fandt 341 af de
369 personer, gav 1 falsk (`Weis, Ernst. 1844 …-4-`: dato-støj) og fandt kun 2 af de 50 værker.

## 3. Metode: tegnet aflæses i billedet

`almanak/scripts/register_glyphs.py` (kræver PDF'en, PyMuPDF og OpenCV):

1. Siderne gengives i 400 dpi gråtoner.
2. Ét »÷« klippes fra PDF s. 369 (foran »1842 30.10.«, Løssøe) og beskæres til blækket (25 × 29 px).
3. Normaliseret krydskorrelation (`cv2.matchTemplate`, `TM_CCOEFF_NORMED`) over alle 61 sider; nabotræf slås sammen.
4. **Tærskel 0,86.** Scorerne skiller skarpt: 422 træf ≥ 0,88 og **ingen** mellem 0,85 og 0,88. Mellem 0,80 og 0,85
   ligger 21: vandrette streger (sidernes linjer) og forklaringens »÷« i større skrift (0,847). Under 0,80 rammer
   skabelonen punktummer og bindestreger.
5. Hvert tegn knyttes til den linje i samme spalte, hvis lodrette midte er nærmest (≤ 4 pt) — ikke efter x, for når OCR
   har tabt tegnet, begynder linjens boks først ved årstallet. Står tegnet alene på en linje, som tekstlaget ikke har,
   gives det til linjen ovenover (≤ 12 pt). Alle 422 tegn blev knyttet til et opslag.
6. Resultatet committes i `almanak/data/register/register_divsign.csv` (side, boks, score, tekstlagets læsning), så
   `parse_register.py` kan bruge det uden PDF'en. `divsign_ocr` i registrene viser tekstlagets gæt til kontrol.

**Kontrol, som er udført:**
- Træf, hvor tekstlaget har tegnet tabt eller læst det som noget andet end de kendte former: 20 af 29 i
  personregistret og 12 af 15 i værkregistret er set ved øjesyn; alle er »÷«. Det samme gælder et tilfældigt udsnit
  på 10 træf lige over tærsklen (0,88–0,92) og 5 af værkregistrets træf, som tekstlaget læser som »+«.
- Linjer, hvor tekstlaget har en ÷-lignende form, men billedet intet »÷« (16): 14 er set; de er ægte »+« i
  værkregistret (10) eller dato-støj i personregistret (4). Skabelonen skelner altså »÷« fra »+«.

**Resultat:** 369 personopslag med »÷« (før 341), 50 værkopslag (før 2). OCR-resterne (`4-.`, `-5-.`, `. .` …)
fjernes nu fra `description`/`label` (305 beskrivelser og 10 etiketter blev renere, fx »Moltke, grevinde. 4-« → »Moltke, grevinde«).

**Fordeling i personregistret** (uden henvisningsopslag):

| | uden oplysninger | med oplysninger |
|---|---:|---:|
| uden ÷ (står i Dagbøger XI) | 999 | 393 |
| med ÷ (ikke i XI, eller ikke identificeret) | 73 | 296 |

**»Ikke i XI« og »ikke identificeret« skelnes** (beslutning 2026-11-24) i kolonnerne `xi_status` og `xi_basis`:

| `xi_status` | regel | antal |
|---|---|---:|
| `i_xi` | intet ÷ | 1.653 |
| `ikke_i_xi` | ÷ og identificeret: levetid/dødsår i parentes (`xi_basis` = `levetid`, 217) eller et fornavn/initial efter efternavnet, ikke en titel eller rolle (`fornavn`, 46: »Balling, Jonathan«, »Palm, A.«) | 263 |
| `uidentificeret` | ÷ uden noget af det: »Blome, frøken«, »Schmidt, grosserer«, »Wulff, »Kunstnerne W.«« | 106 |

Reglen er en tolkning af udgavens »eller ikke er identificeret«; grænsetilfælde som »Poulsen, brygger (død 1838)«
(identificeret via dødsår) og »Meyer, A., Glücksborg« (via initial) står på `xi_basis`, så de kan sorteres.

## 4. Fund ved den optiske kontrol: årstallene er også fejllæst — og ikke kun, hvor året er umuligt

Henvisningernes årstal står i *kursiv med gammeldags tal*, hvor 3, 5 og 9 går under linjen og ligner hinanden.
Udsnittene viser OCR »1843« for trykkets *1845*, »1838« for *1858*, »1833« for *1853*/*1855*. §3.15 i
`docs/plan-streng-grounding.md` rettede de 974 tilfælde, hvor det forkerte år ikke har en almanakpost på dagen. Men
fejlen rammer også år, der *har* en post: **719 henvisninger** peger på en dag, hvor personens navn ikke står, mens
præcis ét andet 3/5/8/9-år har navnet på samme dag (1843→1845: 361, 1838→1858: 189, 1833→1853/1855: 90 …).

Metode til at rette dem (ikke udført): genlæs 3. og 4. ciffer i hvert kursivt årstal i billedet.
- En hurtig prøve (klyngedeling af 3.326 ciffer-udsnit, ukontrollerede klynger som facit) ramte kun halvdelen af de
  kontrollerede tilfælde. Kursivens 3/5/9 kræver *håndmærkede* skabeloner: ca. 30 udsnit pr. ciffer, udvalgt og
  bekræftet ved øjesyn, og klassifikation af hvert ciffer med en sikkerhed; usikre tilfælde til øjesyn.
- Tre vidner pr. henvisning: tekstlaget, ciffer-genlæsningen og navnekontrollen i almanakposten. Rettes kun, hvor
  billedet og navnet er enige; uenighed til øjesyn.

## 5. Plan: tegnet ved samkøringen af almanakregistret med Dagbøgernes register (bd. XI)

Målet er en kobling `ALMP… → Reg…` (personer) og `ALMW… → værk` (værker), som nævnt i `kombineret-version.md` og
`implementeringsplan.md`. Tegnet bruges som **hård regel og som facit**:

### 5.1 Personer

| klasse | regel | bevis for koblingen |
|---|---|---|
| uden ÷, uden oplysninger (999) | *skal* have netop én `Reg` i XI; navnet er nøglen («For navne uden oplysninger henvises til …») | efternavn + fornavne mod XI-etiketten; **datosammenfald**: personen står i XI på den dagbogsside, der dækker almanakdatoen |
| uden ÷, med oplysninger (393) | *skal* have én `Reg`; oplysningerne (levetid, titel, slægtskab) skærper | som ovenfor + levetid mod XI |
| `ikke_i_xi` (263) | *må ikke* kobles til `Reg`; ny person med eget id (`ALMP…`); Wikidata/VIAF efter skill `wikidata-verify` | — |
| `uidentificeret` (106) | ingen identitet; intet id ud over `ALMP…`; kan senere identificeres (crowdsourcing) | — |

- **Kontrol af koblingen:** et ÷-opslag, som matcheren alligevel vil koble til en `Reg`, er en fejl i matcheren —
  eller en navnebror, Topsøe-Jensen har skilt fra. Det samme gælder et opslag *uden* ÷, som ikke får en `Reg`: OCR i
  navnet, en navneform, XI staver anderledes. Begge går på en adjudikeringsliste; de tæller som falske koblinger
  og manglende koblinger. Tegnet giver altså facit for alle 1.761 opslag uden menneskelig mærkning.
- **Datosammenfald er stærkt bevis:** XI henviser til dagbogssider; siderne har datoer (`data/normalized/diary.csv`).
  En `Reg`-kandidat, der står på dagbogssiden for samme dag som almanakhenvisningen, er næsten sikker. Derfor skal
  årstallene rettes først (§4); ellers rammer datoerne forbi.
- **Rækkefølge:** (1) entydige koblinger uden ÷ med datosammenfald, (2) resten uden ÷ efter navn og levetid,
  (3) liste over uløste og ÷-konflikter til gennemsyn, (4) ÷-personer med oplysninger: nye entiteter.
- **I gennemsynssiden:** `not_in_xi` vises allerede på registerkortet (`x` i `build_annotation_page.py`); når
  koblingen findes, peger forslag for ikke-÷-personer på `Reg`-id'et, så almanak og dagbog deler identitet.

### 5.2 Værker

- Uden ÷ (283): titlen findes hos Birger Frank Nielsen (BFN) → koble til værkets BFN-nummer/vores værkpost på titel.
- Med ÷ (50): ikke i BFN; titlen beholdes som egen post. Står tegnet flere gange i et opslag (»Til Jonas Collin«),
  gælder det alle titler i opslaget.
- Det ægte »+« (§1) er en stedhenvisning i samme årgang og bruges som henvisning, ikke som tegn.

### 5.3 Åbne spørgsmål

1. Skal ÷-personer med oplysninger have `Reg`-lignende id'er i hovedregistret eller blive i `ALMP…`-rummet?
2. Rækkefølge: genlæsning af årstal (§4) før samkøringen anbefales.
