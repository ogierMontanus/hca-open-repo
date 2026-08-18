# Biografiske søgelinks på personregistret

`scripts/build_mockup/build_persons_extra.py`s `bio_search_links()` tilføjer
op til to søgelinks til eksterne biografiske opslagsværker for en person —
**kun** når personen a) ikke allerede har et autoritetslink, og b) har en
registreret nationalitet der udløser en af tre regler. Linkene er
**søgninger, ikke identifikationer** — se princip 3 nedenfor, som er
bindende for både data og UI.

987 af 10.228 personer får mindst ét link ved første kørsel.

## Reglerne

| Betingelse | Kilde | Linktekst |
|---|---|---|
| Dansk nationalitet (Dansk-paraplyen) | Lex.dk | `Søg på Lex.dk` |
| Tysk nationalitet (Tysk-paraplyen) | Deutsche Biographie | `Søg hos Deutsche Biographie` |
| Forfatter/Digter-rolle, nationalitet hverken dansk eller tysk | VIAF | `Søg på VIAF` |

En person med både en dansk- og en tysk-paraply-nationalitet (23 personer —
se nedenfor) får **begge** de to første links, ikke et valgt. VIAF-reglen
gælder kun når hverken den danske eller den tyske regel allerede har
udløst — "nationaliteter der ikke er dækket af de andre regler", ikke en
generel fallback for enhver ukendt nationalitet.

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

## 2. VIAF — kun forfattere, kun når intet andet dækker

Tilføjet efter en opfølgende instruks: *"For writers with nationalities
not covered by other rules link to viaf.org."* "Forfatter" genbruger
`Rolle/Erhverv`-facettens `Forfatter/Digter`-bucket (se
`docs/data-model/person-role-facet.md`) — samme kombination af
VÆRK-REGISTER-optræden og beskrivelses-høst som allerede driver den
facet, ikke en ny "er dette en forfatter"-heuristik. 297 personer
kvalificerer — eksempler: Vittorio Alfieri (italiensk), Arvid August
Afzelius (svensk), William Harrison Ainsworth (engelsk).

## 3. Søgning, ikke identifikation

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

## URL-skabeloner — verificeret, ikke gættet

CLAUDE.md kræver live-verifikation af eksterne fakta før output. Denne
sandbox' netværksproxy blokerer direkte adgang til alle tre mål-domæner
(`lex.dk`, `deutsche-biographie.de`, `viaf.org` gav alle `EGRESS_BLOCKED`
via både `WebFetch` og `curl`), så ingen af URL'erne kunne bekræftes ved
selv at hente og se søgeresultatsiden. I stedet blev hver skabelon
bekræftet indirekte, med forskellig sikkerhedsgrad:

- **Deutsche Biographie** — **moderat sikker.** Google havde selv crawlet
  og indekseret en reel, af sitet selv udsendt søge-URL med de fulde
  parameternavne (`name`, `geburtsjahr`, `todesjahr`, `st=erw` for
  "erweiterte Suche"). Ikke en dokumentations-gæt, men heller ikke en
  URL jeg selv har set rendere resultater.
- **VIAF** — **relativt sikker.** Samme fremgangsmåde gav en reelt
  crawlet eksempel-URL i CQL-form (`local.personalNames all "…"`),
  **og** samme mønster går igen uafhængigt i Ex Libris' udvikler-blog og
  R-pakken wikiTools' dokumentation — tre uafhængige kilder, samme svar.
- **Lex.dk** — **svagest bekræftet af de tre.** Kun `/api/v1/search?query=…`
  (en JSON-API, fundet via kildekoden til et tredjeparts Python-bibliotek
  der forespørger den) er direkte bekræftet. Den menneskevendte søgeside
  (`lex.dk/search?query=…`) er en rimelig, men **ikke uafhængigt
  bekræftet** slutning ud fra samme parameternavn — ingen crawlet
  eksempel-URL blev fundet for selve søgesiden.

**Konsekvens:** Lex.dk-skabelonen bør efterprøves manuelt (fx
`https://lex.dk/search?query=Hans%20Christian%20Andersen%201805%201875` i
en almindelig browser) af nogen med netværksadgang, før den regnes for
lige så sikker som de to andre. Ret kun URL-formen i
`bio_search_links()` — resten af logikken (paraplyer, forfatter-reglen,
navnekonvertering) er upåvirket af hvilken præcis sti/parameter Lex.dk
faktisk bruger.

## Kørsel

```
python scripts/parsers/parse_person_role.py       # forudsætning for VIAF-reglen
python scripts/build_mockup/build_persons_extra.py
```

Udskriver antal personer med et foreslået link ved hver kørsel.
