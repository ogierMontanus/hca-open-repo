# Maskinforslag til navne i almanakkerne — metode og første resultater

*Kort rapport, 2026-11-24. Detaljer: `docs/plan-streng-grounding.md` §3.10–3.15, `almanak/docs/registertegn.md`,
`docs/plan-llm-trin.md`.*

## Formål

At markere personer, steder og værker i H.C. Andersens almanakker (1833–73) og koble dem til registrene, så et
menneske *retter* forslag i stedet for at markere fra bunden.

## Metoden i fem trin

1. **Kilder gøres pålidelige.** Almanakkens trykte register (Topsøe-Jensen 1990) er OCR-læst. Parseren retter
   dato- og årstalsfejl (OCR forveksler 3/5/8/9 i de kursive årstal), og 70 åbenlyse navnefejl rettes i en håndholdt liste
   (`WulfT` → `Wulff`). Et år rettes kun, hvor personens navn faktisk står i almanakposten på datoen. Resultat: 9.491 af
   9.743 dateringer rammer nu en almanakpost (før 8.517). Registertegnet »÷« (ikke i Dagbøgernes register / ikke
   identificeret / værk ikke i bibliografien) aflæses i billedet, fordi OCR ikke kan læse det.
2. **Kandidater.** Alle strenge med stort begyndelsesbogstav, med titler («Fru», «Etatsraad») og genitiv, er kandidater.
3. **Rangering.** En lille model (logistisk regression) giver hver kandidat en sandsynlighed *p*. Trækkene er bl.a.: står
   navnet i almanakregistret for datoen eller i dagbogsregistret for samme dag, form og kontekst, og om ordet er et
   kendt fællesnavn i samtidig retskrivning (ordlister fra moderniseringsprojektet og ODS). Trænet på Sørens
   markeringer (fire blokke à otte dage).
4. **Filtre og grænser.** Et forslag, der kun består af fællesnavne («Tænderne», «Fluen»), udelades, medmindre et
   register støtter det, eller ordet står på listen over navnelignende fællesnavne («Kongen», «Theatret»).
   - *sikkert* (p ≥ 0,75): markeres stiplet i teksten;
   - *usikkert* (0,6 ≤ p < 0,75, eller 0,3 ≤ p hvis et register støtter det): står i en liste under posten;
   - resten foreslås ikke.
5. **Kobling.** Hvert forslag får en registerpost, hvis navnet entydigt findes blandt dagens poster i almanakregistret
   eller dagbogsregistret. Roller kobles til dagens kongelige: «Kongen» 1.5.1840 → Christian VIII, «Dronningen» →
   Caroline Amalie (ud fra registrets beskrivelse »1839 konge af«).

Gennemsynet sker i tre runder pr. dag: (1) ret de sikre forslag og markér det oversete, (2) markér omtaler af dagens
registerposter, som intet forslag peger på, (3) tag stilling til de usikre forslag.

## Resultater

**Krydsvalidering** (Sørens markeringer, almanakken, 136 navne): sikre forslag har præcision 0,90 og recall 0,71;
med de usikre er recall 0,78 (målt før reglen om registerstøtte nedenfor). Det er små tal; intervallerne er brede.

**Gennemsyn 2** (Holger, blok I: 29.4.–6.5.1840, 8 dage, 6 minutters aktiv tid):

| | antal | resultat |
|---|---:|---|
| sikre forslag | 22 | alle godkendt, ingen typerettelser |
| usikre forslag | 4 | 3 godkendt (»Monrads«, »Baronessen«, »Theatret«), 1 afvist pga. afgrænsning (»Portugiseren G O Neil«) |
| tilføjet af mennesket | 11 | se nedenfor |

De 11 tilføjelser fordeler sig sådan: *Kongen* (3), *Dronningen*, *Thorvaldsen*, *Foreningen* (Studenterforeningen),
værket *En Comedie i det Grønne* omtalt som »Skuespilleren mod sin Villie«, »Skuespilleren« og »Vaudevillen« (3),
*G O Neil* (OCR for O'Neill) og initialen *S.*

## Tilpasninger efter gennemsynet

- **Støtte fra registret sænker grænsen.** »Thorvaldsen« (p 0,53) stod i registret for dagen, men lå under 0,6. Nu er et
  registerstøttet forslag usikkert allerede fra 0,3. (I krydsvalideringen var 3 af 4 sådanne forslag navne mod 4 af 14 uden støtte.)
- **Roller kobles til dagens kongelige** (se trin 5).
- **»Foreningen«** er føjet til listen over navnelignende fællesnavne; »Baronessen«, »Portugiseren« m.fl. regnes som omtaler.

Seks af de elleve tilføjelser foreslås nu (som usikre). I hele almanakken stiger andelen af registrets personhenvisninger,
som et forslag kobler til, fra 0,67 til 0,71.

## Ikke løst — og hvor det hører hjemme

- **Omtaler af værker** (»Skuespilleren«, »Vaudevillen«): registret har værket på dagen, men intet i teksten ligner titlen.
  Runde 2 viser værket, og mennesket markerede det. Det er en opgave for et LLM-trin (`docs/plan-llm-trin.md`).
- **Afgrænsning**: beskrivende ord foran navnet (»Portugiseren G O Neil«) og OCR i navnet (»G O Neil« for O'Neill).
- **Initialer** (»S.«): registret har netop »S., ikke identificeret« på datoen; kandidaterne omfatter ikke enkeltbogstaver endnu.
- **Årstal i registret**: 719 henvisninger, hvor OCR har forvekslet året inden for gyldige år, venter på en optisk genlæsning
  af cifrene (`registertegn.md` §4).

## Næste skridt

1. Gennemsyn af blok J–L og af stikprøve 1 (Søren og Ole), så præcision og recall kan måles på flere end én blok.
2. Koblingen fra almanakregistret til Dagbøgernes register (bd. XI) med »÷« som facit (`registertegn.md` §5).
3. LLM-trinnet til omtaler, afgrænsning og de lave forslag.
