# Biografiske søgelinks på personregistret

`scripts/build_mockup/build_persons_extra.py`s `bio_search_links()` tilføjer
op til to søgelinks til eksterne biografiske opslagsværker for en person —
**kun** når personen a) ikke allerede har et autoritetslink, og b) har en
registreret nationalitet der udløser en af fem regler. Linkene er
**søgninger, ikke identifikationer** — se princip 3 nedenfor, som er
bindende for både data og UI.

1.969 af 10.228 personer får mindst ét link ved seneste kørsel.

## Reglerne

| Betingelse | Kilde | Linktekst |
|---|---|---|
| Dansk nationalitet (Dansk-paraplyen) | Lex.dk | `Søg på Lex.dk` |
| Tysk nationalitet (Tysk-paraplyen) | Deutsche Biographie | `Søg hos Deutsche Biographie` |
| Norsk nationalitet | Store norske leksikon | `Søg på Store norske leksikon` |
| Forfatter/Digter-rolle, nationalitet hverken dansk, tysk eller norsk | VIAF | `Søg på VIAF` |
| Øvrige, nationalitet hverken dansk, tysk eller norsk, ikke forfatter | GND Explorer | `Søg i GND Explorer` |

En person med både en dansk- og en tysk-paraply-nationalitet (23 personer —
se §1) får **begge** de to første links, ikke et valgt — Dansk, Tysk og
Norsk er uafhængige if-grene, ikke gensidigt udelukkende. De sidste to
regler (VIAF/GND Explorer) er derimod indbyrdes udelukkende og gælder kun
**resten** — dem ingen af de tre nationalitetsregler ramte — delt i to efter
om personen er forfatter eller ej. "Nationalitet hverken dansk, tysk eller
norsk" er ikke en generel fallback for enhver ukendt nationalitet: uden en
registreret nationalitet får ingen af de fem regler noget at arbejde med.

## 0. Forudsætning: intet autoritetslink i forvejen

`load_person_wikidata()` læser en (endnu ikke-eksisterende)
`data/curated/persons_wikidata.csv`, samme facon som
`data/curated/works_wikidata.csv`. Ingen af registrets 10.228 personer har
i dag et `wd`-felt sat via denne vej — kun `mockup/person.html`s egen lille
håndkuraterede demo-post (Dickens, `wd: 'Q5686'`) har ét, og den side er
ikke den, der linkes til fra det levende register (`persons.html?reg=…`
er). Loaderen findes alligevel nu, så reglen er fremtidssikret: tilføjes en
`persons_wikidata.csv` senere, holder `bio_search_links()` automatisk op
med at foreslå et søgelink for de personer — ingen kodeændring nødvendig.

## 1. Dansk / Tysk — paraplyerne fra nation.html, ikke en ny liste

Hvilke nationalitetsnøgler der tæller som "dansk" og "tysk" kommer fra
`data/curated/nation_umbrellas_da.csv` — samme paraply-klynging
`nation.html` selv bruger til at vise "alle tyske personer og steder".
Genbrugt bevidst, frem for at opfinde en snævrere "tyske delstater"-liste:
en person `bio_search_links()` kalder tysk er præcis den samme mængde
personer, `nation.html`s Tyskland-side ville vise.

Det betyder blandt andet, at de før-1871 tyske delstater (`preussisk`,
`sachsisk`, `bayersk`, `hannoveransk`, `oldenburgsk`, `westfalsk`,
`württembergsk`, `hessisk`, `thüringsk`, `badisk`, …) tæller som tysk —
korpusset navngiver dem langt oftere end det samlende "tysk" (Tyskland
blev først samlet i 1871, midt i dagbogsperioden).

**Slesvig-Holsten-nøglerne** (`holstensk`, `slesvigholstensk`,
`holstenlauenborgsk`) er med vilje medlem af **begge** paraplyer —
hertugdømmerne var stridens genstand i 1848–51- og 1864-krigene, og at
tvinge dem ind under én nation ville tage parti på en måde registret
bevidst ikke gør (se `nation_umbrellas_da.csv`s egen note herom). De 23
personer med link til begge kilder er næsten alle netop disse nøgler (plus
2 ægte dansk-tyske dobbeltnationaliteter, fx Friederike Brun).

## 2. Norsk — bar nøgle, ingen paraply

`nation_umbrellas_da.csv` har ingen `norsk`-række (i modsætning til dansk
og tysk har den norske nationalitet ingen regionale/historiske
underidentiteter i `ethnic_adjectives_da.csv`), så `is_norwegian` tjekker
blot om `norsk` selv indgår i personens nationaliteter — ingen klynge at
udvide til. 93 personer kvalificerer.

## 3. VIAF vs. GND Explorer — forfattere vs. alle andre, kun for "resten"

VIAF-reglen blev tilføjet efter en opfølgende instruks: *"For writers with
nationalities not covered by other rules link to viaf.org."* GND
Explorer-reglen efter en senere instruks: *"For other nationals use gnd
explorer."* Sammen dækker de to regler præcis den gruppe, ingen af de tre
nationalitetsregler rammer:

- **Forfattere** (`Rolle/Erhverv`-facettens `Forfatter/Digter`-bucket, se
  `docs/data-model/person-role-facet.md` — samme kombination af
  VÆRK-REGISTER-optræden og beskrivelses-høst som allerede driver den
  facet, ikke en ny "er dette en forfatter"-heuristik) får **VIAF**, hvis
  hele formål er bibliografisk forfatter-autoritet — det bedst egnede af de
  to til netop denne gruppe. 282 personer.
- **Alle andre** i samme "ikke dansk/tysk/norsk"-gruppe — adelige,
  officerer, videnskabsfolk, og enhver anden ikke-forfatter — får **GND
  Explorer**, en bredere person-/institutions-/emne-autoritetssøgning uden
  forfatter-bias. 905 personer.

Rækkefølgen betyder noget: en forfatter fra fx Sverige eller England får
VIAF, ikke GND Explorer, fordi forfatter-tjekket kommer først inden for
"resten"-grenen.

## 4. Søgning, ikke identifikation

Linkene sidder i deres **egen** sidebar-blok, "Biografiske opslag", adskilt
fra den eksisterende "Autoritetslinks"-blok (som kun vises når `wd` er
sat) — de to blokke udelukker hinanden i data, men er bevidst også visuelt
adskilt, så en søgning aldrig ser ud som en bekræftet post. Blokken bærer
sin egen forklarende linje: *"Søgelinks til eksterne opslagsværker ud fra
navn og nationalitet — ikke en bekræftet identifikation af personen."*

Markup følger `docs/external-links.md` fuldt ud: `.external-link`,
`target="_blank"`, `rel="noopener noreferrer"`, ↗-ikon og
`.sr-only`-varsling.

## Navn til søgestreng

`full_name_from_label()` vender registrets `"Efternavn, Fornavn(e)"`-form
om til `"Fornavn(e) Efternavn"` til søgefeltet — bevidst løsere end
`parse_person_gender.py`/`parse_person_role.py`s navne-parsing, siden en
søgestreng kun skal være tæt nok på til, at målsidens egen (fuzzy,
relevans-rangerede) søgning finder personen, ikke strukturelt korrekt. Et
tredje komma-separeret segment (en titel som `, Greve` / `, Baron`)
droppes — det ville kun tilføje støj, ikke hjælpe søgningen. Et label uden
komma (kun efternavn kendt, fx "Fog", "Schytte") bruges som det er; det er
stadig et gyldigt, om end bredt, søgeudgangspunkt.

Fødsels- og dødsår tilføjes til søgestrengen når kendt (kun det ene, hvis
kun det ene er registreret) — "Include the full name and available life
dates to reduce ambiguity" fra selve opgaveformuleringen.

## URL-skabeloner — verificeret, ikke gættet, med forskellig sikkerhedsgrad

CLAUDE.md kræver live-verifikation af eksterne fakta før output. Denne
sandbox' netværksproxy blokerer direkte adgang til alle fem mål-domæner
(`lex.dk`, `snl.no`, `deutsche-biographie.de`, `viaf.org`,
`explore.gnd.network` gav alle `EGRESS_BLOCKED` via både `WebFetch` og
`curl`), så ingen af URL'erne kunne bekræftes ved selv at hente og se
søgeresultatsiden. Hver skabelon er derfor bekræftet forskelligt:

- **Deutsche Biographie** — **moderat sikker.** Google havde selv crawlet
  og indekseret en reel, af sitet selv udsendt søge-URL med de fulde
  parameternavne (`name`, `geburtsjahr`, `todesjahr`, `st=erw` for
  "erweiterte Suche"). Ikke en dokumentations-gæt, men heller ikke en
  URL jeg selv har set rendere resultater.
- **VIAF** — **relativt sikker.** Samme fremgangsmåde gav en reelt
  crawlet eksempel-URL i CQL-form (`local.personalNames all "…"`),
  **og** samme mønster går igen uafhængigt i Ex Libris' udvikler-blog og
  R-pakken wikiTools' dokumentation — tre uafhængige kilder, samme svar.
- **Lex.dk** — **bekræftet ved manuel test.** Den menneskevendte søgeside
  har en usædvanlig sti — et indledende punktum foran "search"
  (`https://lex.dk/.search?query=…`, ikke `/search?query=…`) — som ingen
  af de indirekte kilder denne session kunne nå frem til alene (kun
  `/api/v1/search?query=…`, en separat JSON-API, var direkte bekræftet
  fra kildekode). Brugeren testede selve URL'en i en almindelig browser
  (`https://lex.dk/.search?query=Ingemann`) og bekræftede at den renderer
  søgeresultater.
- **Store norske leksikon** — **antaget ud fra Lex.dk, ikke selvstændigt
  testet.** Brugeren angav URL'en direkte (`https://snl.no/.search?query=…`)
  med samme punktum-præfikserede sti som den bekræftede Lex.dk-adresse —
  SNL og Lex.dk er søsterplatforme (norsk hhv. dansk nationalleksikon på
  formodet fælles infrastruktur), hvilket gør mønstret sandsynligt, men
  denne specifikke URL er ikke selv afprøvet i en browser.
- **GND Explorer** — **ikke uafhængigt verificeret.** URL og begge
  parameternavne (`term`, `rows`) er angivet direkte af brugeren
  (`https://explore.gnd.network/en/search?term=Test&rows=25`), ikke fundet
  eller bekræftet af denne session selv.

**Praktisk konsekvens:** ret kun URL-formen i `bio_search_links()`, hvis en
af de sidste to skabeloner viser sig forkert — resten af logikken
(paraplyer, forfatter-reglen, navnekonvertering) er upåvirket af hvilken
præcis sti/parameter det enkelte site faktisk bruger.

## Kørsel

```
python scripts/parsers/parse_person_role.py       # forudsætning for VIAF/GND-reglen
python scripts/build_mockup/build_persons_extra.py
```

Udskriver antal personer med et foreslået link ved hver kørsel.
