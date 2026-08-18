# Eksterne links — politik

Status: gældende · 2026-08-12

Gælder alle links der fører brugeren **væk fra** HCA Open Repository:
Det Kgl. Biblioteks faksimiler, Wikidata, VIAF, GeoNames, museers
samlingsdatabaser og lignende.

---

## 1. Eksterne links åbnes i nyt faneblad

**Regel.** Ethvert link til et andet domæne får `target="_blank"` og
`rel="noopener noreferrer"`.

```html
<a class="external-link" href="https://www.wikidata.org/wiki/Q5686"
   target="_blank" rel="noopener noreferrer">Wikidata<span
   class="external-link__icon" aria-hidden="true">↗</span><span
   class="sr-only"> (åbner i nyt faneblad)</span></a>
```

**Begrundelse.** Registret er et opslagsværk: brugeren er typisk midt i en
søgning eller en filtreret liste, som går tabt ved navigation væk. Et nyt
faneblad bevarer arbejdskonteksten og signalerer samtidig, at man forlader
webstedet.

`rel="noopener"` er ikke valgfrit. Uden det får målsiden en `window.opener`-
reference tilbage til vores side og kan omdirigere den. `noreferrer`
tilføjes, så vi ikke lækker den præcise registerside i `Referer`-headeren.

**Interne links åbnes altid i samme faneblad.** Navigation mellem
registersider, dagbogssider og facetfiltre er almindelig brug og må ikke
sprede sig ud over faneblade.

---

## 2. Eksterne links er diskrete

De er *proveniens*, ikke handlingsopfordringer. En faksimilehenvisning må
ikke konkurrere med sidens eget indhold.

- Placeres **højt på siden**, hvor læseren leder efter kilden — typisk lige
  under titlen i `page-hero`.
- Sættes mindre (`0.8rem`) og i dæmpet farve (`--color-text-muted`, eller
  gennemsigtig hvid på mørk baggrund via `.external-link--on-dark`).
- Ingen ramme, ingen knap, ingen understregning før hover.

Klasserne ligger i `mockup/css/style.css` under `=== External links ===`.

---

## 3. Tilgængelighed

Et nyt faneblad, der åbner uvarslet, desorienterer skærmlæser- og
tastaturbrugere. Derfor:

- **↗** efter linkteksten som visuel markør, `aria-hidden="true"` da den
  ikke skal læses op som tegn.
- **`<span class="sr-only"> (åbner i nyt faneblad)</span>`** inde i linket,
  så varslingen indgår i det oplæste linknavn.
- Linkteksten skal give mening alene — `"Læs siden hos Det Kgl. Bibliotek"`,
  ikke `"læs mere"` eller en rå URL.

---

## 4. Faste linktekster

| Mål | Linktekst |
|-----|-----------|
| Det Kgl. Biblioteks dagbogsfaksimile | `Læs siden hos Det Kgl. Bibliotek` |
| Wikidata-entitet | `wd:Q…` (badge) eller `Wikidata` |
| Lex.dk-søgning (personregister, dansk nationalitet) | `Søg på Lex.dk` |
| Deutsche Biographie-søgning (personregister, tysk nationalitet) | `Søg hos Deutsche Biographie` |
| Store norske leksikon-søgning (personregister, norsk nationalitet) | `Søg på Store norske leksikon` |
| VIAF-søgning (personregister, forfatter uden dansk/tysk/norsk nationalitet) | `Søg på VIAF` |
| GND Explorer-søgning (personregister, øvrig nationalitet, ikke-forfatter) | `Søg i GND Explorer` |

Ny type ekstern kilde: tilføj den her, så teksten er ens på tværs af sider.

De fem søgelinks ovenfor er en anden underkategori end resten af tabellen:
de peger på en SØGNING, ikke en bekræftet post — se
`docs/data-model/person-bio-search-links.md` for hele reglen (hvornår de
tilføjes, hvordan URL'en bygges, og hvorfor de ikke må se ud som
Autoritetslinks-blokken).

---

## 5. Det Kgl. Bibliotek — dagbogslinks

Kilde: `raw/1-KBDiaryLinkData-PQ-links-active.xlsm` →
`data/normalized/kb_diary_links.csv` via
`scripts/build_mockup/build_kb_links.py`.

- Dækker **bind I–X**, 4.413 sider. Bind XI er ikke udgivet hos KB, så
  registrets 56 sider derfra har intet link — siden udelader det blot.
- 4.411 af registrets 4.544 dagbogssider har et link (97,1 %). De
  resterende 133 ligger uden for KB's sidetælling for bindet.
- URL-formen udledes af `OffSetTab` i projektmappen:
  `hcadag{bind}_{offset + side - 1}_{side}.xhtml`. Reglen rammer 4.412 af
  4.413 rækker præcist.
- **Kendt uoverensstemmelse:** bind I side 13 står i projektmappen med side
  32's fil (`hcadag01_072_32.xhtml`) — den eneste dublerede URL i arket,
  mens begge nabosider følger reglen. Byggescriptet skriver den beregnede
  URL (`hcadag01_053_13.xhtml`, verificeret 200 OK) og advarer om
  afvigelsen. Rettes projektmappen, forsvinder advarslen.
