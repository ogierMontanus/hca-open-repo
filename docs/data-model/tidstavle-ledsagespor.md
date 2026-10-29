# Tidstavle som ledsagespor til dagbøgerne

Status: indarbejdet 2026-10-27 · kilde `data/HCA_Tidstavler_bind_1-10_ Ver_0.9.xlsx`

## Hvad er det

Regnearket er de trykte tidstavler fra dagbogsudgavens bind 1–10 (s. XII–XL i
hvert bind): **1.745 datoerede poster** 1805–1875 med *Fra · Til ·
Opholdssted / beskrivelse*. Hver beskrivelse har en cellenote med trykt
kildeside, Det Kgl. Biblioteks EPUB-link og den originale datoangivelse.

Tidstavlen er **ikke** dagbogsteksten — den er udgiverens kontekstspor: hvor
var Andersen, hvem besøgte han, hvad udkom. Derfor behandles den som et
*ledsagespor* ved siden af dagbogssiderne, aldrig blandet ind i dem.

## Pipeline

`scripts/build_mockup/build_timeline.py` (stage `3b2` i `build_all.py`, CI-trin
«Stage 3b2») → `mockup/data/timeline.js` (gitignoreret).

* **Datoer** normaliseres til fulde ISO-intervaller (`a`/`b`) med præcision
  (`pa`/`pb` = d/m/y) og forbehold (`q`: ca, sommer, ugyldig …). Månedsangivelser
  udvides til månedens første/sidste dag. Den trykte, ugyldige dato
  *29. februar 1841* klemmes til 28. februar og flages `ugyldig`.
* **Navnelinks** (konservativ matchning, se `Matcher` i scriptet):
  steder = eksakt registerlabel + aliaser (`Genève (Genf)`, `Frankfurt a.M.`,
  `Locle, Le` …), homonymer afgøres på bind-forekomst; personer = efternavn +
  fornavne/initialer, afgjort på levetid (født efter datoen udelukkes), forekomst
  i samme bind og tilstrækkelig afstand til næstbedste kandidat; enkelte
  efternavne kræver at kandidaten er bind-bakket og datérbar. Værker = citerede
  `»titler«`. Fornavne alene («Carl»), genitiver af enkeltord («Italiens») og
  **forfatteren selv** linkes aldrig (registerets «Andersen, Hans Christian» er
  en fotograf fra Nykøbing Mors).
* Resultat: 2.756 stedlinks, 206 personlinks, 49 værklinks. `--report` udskriver
  de hyppigste ulinkede ord til næste forbedringsrunde (fx *Genua* — ikke i
  stedregisteret).

## Visning (`diaries.html`, `diaries_en.html`)

* **Kalender (hovedvisning):** søjle under hver dag med et ophold/en rejse,
  prik ved begivenhed på dagen; dagsdetalje og månedsoversigt viser sporet
  *også for dage uden dagbogsside*; kalenderen går nu tilbage til 1805, men
  åbner stadig på første dagbogsår.
* **Liste:** hvert dagbogskort med dato får en «Tidstavle»-linje.
* **Tabel:** ekstra kolonne «Tidstavle».
* Navne i beskrivelserne linker til `persons.html` / `place.html` / `work.html`;
  kildesiden linker (diskret, nyt faneblad) til EPUB'en hos Det Kgl. Bibliotek.

## Rutelag på kortet (`kort.html`, `kort_en.html`)

`js/kort-routes.js` tegner hvert rejseled («Fra X over Y til Z», 584 stk.) som
en linje gennem de linkede steder i tekstens rækkefølge. Valgfrit lag
(afkrydsning «Andersens rejser (Tidstavle)») med årsfilter; farven løber fra
blå (tidligste år) til orange (seneste). Klik på en linje viser dato,
beskrivelse (med stedlinks) og kildeside. Dybe links: `kort.html#routes=all`
eller `#routes=1846`. Spring over-regel: et enkelt hop på over 4.500 km droppes
hele leddet (værn mod homonym-fejl; ingen led er droppet i dag).

## «Tidstavle: hvor og hvornår» på personsider

`persons.html` / `persons_en.html` får en sektion over dagbogsreferencerne for
de 150 personer, tidstavlerne nævner: dato, tekst med links og «Sted: …». Er
stedet ikke nævnt i selve posten, hentes det fra det opholdsled, der dækker
datoen (markeret «ifølge opholdet»). Personer uden poster får ingen sektion.
Samme `TimelineWire.mountEntity(el, 's'|'p'|'w', rid)` kan genbruges til
`place.html` og `work.html`.

## Se også

* [`tidstavle-krydsforbindelser.md`](tidstavle-krydsforbindelser.md) — målte
  krydsforbindelser og kendte begrænsninger.
* [`../plan-tidstavle-data.md`](../plan-tidstavle-data.md) — plan for videre
  arbejde med interne og eksterne data (udføres lokalt).
