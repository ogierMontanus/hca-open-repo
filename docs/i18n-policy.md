# I18n policy — sprogvalg i interfacet

Princip fastlagt 2026-06-03.

## Hovedregel

**Når den danske version af websitet vises, skal danske stavninger
altid foretrækkes frem for engelske.** Reglen gælder især stednavne,
hvor de samme entiteter ofte har et dansk og et engelsk navn:

- København (ikke Copenhagen)
- Hamborg (ikke Hamburg) — hvor registret har den danske form
- Lissabon (ikke Lisbon)
- Wien (ikke Vienna)
- Italien (ikke Italy)

Den primære visningsetiket i interfacet er feltet `label` fra
`STED-REGISTER`, der i kildedata allerede bruger dansk stavning. Felter
som `destination_en` (fra hcax.dk Rejser-add-on) eller `country_en` (fra
landegazetteer) er **understøttende metadata**, ikke primær visning,
og må ikke erstatte den danske form i den danske udgave.

## Engelsk version

Det omvendte krav — at den engelske version udelukkende anvender
engelske navne — kan **fraviges**, indtil vi har valgt en procedure for
maskinoversættelse. Indtil videre er det acceptabelt at vise danske
stavninger som fallback, hvor en engelsk form ikke er tilgængelig.

## Konsekvens for koden

- I `web/app.js` (Places-view) viser detail-panelet kun `country_da` i
  den danske visning. `country_en` bibeholdes i `places.json` som
  data, men injiceres ikke i UI'en.
- I `mockup/place.html` viser Leaflet-popup'en kun den danske
  `label` (fx "Rom", ikke "Rome / Rom").
- Fremtidige feltvalg i UI-skabeloner skal prioritere dansk form når
  flere navne er tilgængelige.

## Data forbliver tosproget

Tabeller og JSON beholder begge sprogformer hvor de findes
(`destination_da` / `destination_en`, `country_da` / `country_en`).
Vejen til en engelsksproget version er derfor allerede åben — det er
kun et spørgsmål om hvilket felt visningsskabelonen vælger.
