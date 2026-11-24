# Plan: et LLM-trin mellem maskinopmærkning og menneskeligt gennemsyn (almanakken)

*Udkast 2026-11-24. Ikke påbegyndt; intet er sendt til en ekstern tjeneste.*

## 1. Hvor trinnet sidder

| trin | hvem | hvad | i dag |
|---|---|---|---|
| 1 | rangeringsmodel (`almanak/ner/`) | foreslår spænd med sandsynlighed *p*, type og registerpost | ja |
| **2** | **LLM** | **placerer de usikre forslag og vurderer dem med lav sikkerhed** | **ny** |
| 3 | menneske (`mockup/almanak-gennemsyn.html`) | godkender, retter, tildeler | ja |

Trin 1 sorterer i dag i tre bånd (`predict.py`, `HIGH`/`LOW`, se `plan-streng-grounding.md` §3.14):

| bånd | *p* | i dag | med trin 2 |
|---|---|---|---|
| sikre | ≥ 0,75 | markeres stiplet i teksten (runde 1) | uændret; LLM'en ser dem kun som kontekst |
| usikre | 0,6–0,75 | liste under posten (runde 3) | **LLM placerer**: navn ja/nej, type, grænser, registerpost |
| lave | 0,3–0,6 | kasseres | **LLM vurderer**: kun dem, LLM'en holder på, går videre til runde 3 |
| (runde 2) | — | registerposter for dagen uden markering | **LLM leder efter omtalen** i posten («Commandeur» → Wulff) |

Målet er at hente de rigtige navne i det lave bånd tilbage (6 af 136 guldspænd forsvandt, da `LOW` blev hævet fra 0,4 til 0,6, bl.a.
«Commandeur Wulff») **uden** at de falske kommer med igen. Mennesket får færre, bedre begrundede valg i runde 3.

## 2. Hvad LLM'en skal gøre (pr. almanakpost, ét kald)

**Input** (alt fra repoet, intet fra nettet):
- postens tekst og dato; nabodagenes tekst som kontekst (kort);
- de sikre forslag (kun til orientering) og de usikre og lave forslag med nummer, offset, streng, modellens type og *p*;
- **den lukkede kandidatliste**: almanakregistrets poster for datoen og dagbogsregistrets poster for dagens dagbogsside(r), med id, etiket,
  levetid og beskrivelse (fra `Context.alm_date_gazetteer` / `page_gazetteer` — de samme, som `predict.link` bruger);
- om ordet står i fællesnavnslisten (`common_nouns.tsv`) og på listen over navnelignende fællesnavne;
- retningslinjerne fra gennemsynssiden og 10–20 eksempler fra Sørens guld (fra *andre* blokke end den, der måles på).

**Output** (struktureret, JSON-skema via `output_config.format`), én dom pr. forslag:

```json
{"id": 3, "dom": "navn" | "omtale" | "ikke_navn",
 "type": "Person" | "Sted" | "Lokalitet" | "Værk" | "Andet",
 "start": 112, "slut": 130,          // kan udvide/indskrænke spændet ("Prindsessen" -> "Prindsessen af Preusen")
 "reg_id": "ALMP0812" | null,         // SKAL være fra kandidatlisten
 "sikkerhed": "høj" | "middel" | "lav",
 "begrundelse": "Commandeur Wulff = Peter Frederik Wulff; registret har ham 29.9.1838"}
```

plus en liste `omtaler` for runde 2: kandidatposter, LLM'en finder omtalt uden navn, med offset og begrundelse.

**Kontrol i koden, før noget vises** (LLM-svar er forslag, ikke data):
- `reg_id` skal stå på kandidatlisten, ellers sættes den til tom;
- `start`/`slut` skal ligge i posten, og den nye streng skal overlappe det oprindelige spænd (ingen nye spænd fra intet i bånd 2–3);
- strengen genlæses fra teksten — LLM'ens egen gengivelse bruges ikke;
- et svar, der ikke validerer mod skemaet, eller en `refusal`, giver ingen dom: forslaget går til runde 3 som i dag.

## 3. Hvad mennesket ser (runde 3)

- **Usikre**, som LLM'en holder for navne: står i listen med LLM'ens type, registerpost og begrundelse forudfyldt («Claude foreslår: Person ·
  Wulff, Peter Frederik»). Ét klik godkender.
- **Usikre**, som LLM'en afviser: står nederst, sammenklappet, med «Claude: ikke et navn (Kjole = fællesnavn)». Mennesket skal stadig tage
  stilling, så vi kan måle LLM'ens afvisninger.
- **Lave**, som LLM'en holder for navne med sikkerhed høj/middel: kommer ind i listen. Øvrige lave forbliver kasserede (men gemmes, se §5).
- Ingen LLM-dom markeres i teksten. Runde 1 (stiplede, sikre) er uændret.

**Forankring (anchoring).** Et forudfyldt forslag trækker mod ja. For at kunne måle det vises LLM-dommen kun i halvdelen af blokkene i den første
runde; i den anden halvdel ser reviewer den først, efter at have valgt. Forskellen i enighed med guldet er LLM'ens reelle bidrag.

## 4. Evaluering før brug — gå/ikke-gå

1. **Offline på Sørens guld** (blok A–D, 136 almanakspænd; dagbogen som ekstra test). Samme blokvise opdeling som `model.py`: eksemplerne i
   prompten kommer fra de andre blokke. Mål pr. bånd: præcision og recall før/efter LLM, rigtige `reg_id`, grænser (eksakt/overlap).
2. **Gå-kriterier** (forslag): i det usikre bånd skal LLM'en hæve præcisionen fra ca. 0,5 til ≥ 0,8 uden at tabe mere end ét rigtigt spænd;
   i det lave bånd skal den hente mindst halvdelen af de rigtige tilbage ved ≤ 1 falsk pr. 2 rigtige. Ellers: ikke i drift.
3. **Gennemsyn E–H** (Holger, Søren, Ole): `eval_review.py` udvides med LLM-dom pr. forslag, så vi ser LLM mod menneske pr. bånd og omtaleform.

Tallene er små (136 spænd); kriterierne er derfor tærskler for at gå videre til næste stikprøve, ikke for at publicere.

## 5. Implementering

Ny fil `almanak/ner/llm_review.py` (Python, Anthropic SDK `anthropic`), kommandoer:

| kommando | gør |
|---|---|
| `prepare --blocks E,F,G,H` / `--all` | bygger én forespørgsel pr. post med usikre/lave forslag → `out/llm_requests.jsonl` (ingen netværk) |
| `eval` | kører forespørgslerne for guldblokkene og skriver tabellen i §4 → `out/llm_eval.json` |
| `submit` / `collect` | hele almanakken via Message Batches (50 % pris, asynkront); resultater nøglet på `custom_id` = post-id |
| (læses af) `build_review_page.py` | fletter `out/llm_verdicts.jsonl` ind i prefill (felterne `llm_dom`, `llm_type`, `llm_reg`, `llm_begrundelse`) |

- **Model:** Claude Opus 5.5 (`claude-opus-5-5`), adaptiv tænkning, effort `medium`; prøv `low` i evalueringen (opgaven er klassifikation med
  lukket kandidatliste). Fast systemprompt (retningslinjer + eksempler) med prompt-caching, så kun postens del betales fuldt pr. kald.
- **Sporbarhed:** hver dom gemmes med model-id, promptversion (hash) og dato; LLM-domme er et lag på samme måde som crowd-bidrag
  (`CLAUDE.md`, «bidrag er et lag»): de skrives aldrig ind i registret, `entities.csv` eller guldet.
- **Fingeraftryk:** gennemsynssiden udskifter urørte forslag på ugennemgåede dage, når prefill ændres (`PREFILL_V`), så LLM-dommene kan
  lægges ind, efter at et gennemsyn er gået i gang.

**Omfang og pris (overslag).** Hele almanakken: 5.213 poster, gennemsnit 70 tegn; 1.013 poster har usikre forslag (1.175 spænd), og det lave
bånd forventes at være af samme størrelse (krydsvalideringen: 18 i 0,3–0,6 mod 17 i 0,6–0,75). Altså ca. 2.000 poster à ca. 1.500 input-
og 300 output-tokens oven på en cachet systemprompt: med Opus 5.5 (4 $/20 $ pr. mio. tokens) omkring 25 $ uden batch og det halve med
Message Batches — plus tænkningen, der faktureres som output og kan fordoble beløbet. Offline-evalueringen på guldet koster få dollars. Tallene skal bekræftes med `count_tokens` på `llm_requests.jsonl`, før noget sendes.

**Forudsætninger:** en API-nøgle (`ANTHROPIC_API_KEY` eller `ant auth login`) og din godkendelse af hvert kørsel, der koster penge.
Almanakteksten er fri (1800-tallet); crowd-data (`data/crowdsource/`) sendes aldrig.

## 6. Åbne beslutninger (før kodning)

1. **Grænsekonvention:** skal «Chamissos Børn», «Lucien Bonapartes Datter», «Prindsessen af Preusen» markeres som én omtale (Sørens praksis),
   eller navnet alene? Halvdelen af de falske sikre forslag er grænsefejl af denne slags (§3.14). Svaret bestemmer, om LLM'en må udvide spænd.
2. **Skal LLM'en også se de sikre forslag kritisk?** (11 falske blandt 109 i krydsvalideringen.) Det koster ca. 4.500 poster mere; foreslået
   først, når trin 2 har vist sig i de to nederste bånd.
3. **Rækkefølge:** offline-evaluering → blok E–H med halvdelen uden LLM-visning → hele almanakken. Dagbogen bagefter med samme kode.

## 7. Faser

| fase | indhold | afhænger af |
|---|---|---|
| 0 | `prepare` + `eval` på guldet; skema, kontrol, tabel i §4 | API-nøgle, godkendelse (få dollars) |
| 1 | gennemsynssiden viser LLM-domme (runde 3), med A/B pr. blok | gå-kriterierne i §4 |
| 2 | Message Batches for hele almanakken; `predict.py all` får LLM-laget | fase 1 + svar på §6.1 |
| 3 | dagbogen | fase 2 |
