# Tidstavle — krydsforbindelser og første resultater

Status: målt 2026-10-27 på `data/HCA_Tidstavler_bind_1-10_ Ver_0.9.xlsx` ·
implementering: se [`tidstavle-ledsagespor.md`](tidstavle-ledsagespor.md) ·
fremadrettet plan: [`../plan-tidstavle-data.md`](../plan-tidstavle-data.md)

Tallene er beregnet ved at holde de 1.745 tidstavle-poster (datoer normaliseret,
navne linket til registeret) op mod `diary.csv` (4.413 daterede dagbogssider),
`references.csv`, `places.csv` og `rejser.tsv`. De er målinger af *dækning og
overensstemmelse*, ikke af korrekthed: en uenighed kan lige så vel pege på en
fejl i registeret som i tidstavlen.

## Hvad tidstavlen tilfører, som dagbøgerne ikke har

Tidstavlen er udgiverens kontekstspor — hvor Andersen opholdt sig, hvem han
besøgte, hvad der udkom — ikke dagbogsteksten. Derfor behandles den som et
*ledsagespor* ved siden af dagbogssiderne (aldrig blandet ind i dem).

## Fund

| # | Krydsforbindelse | Resultat | Brug |
|---|---|---|---|
| 1 | **Sted-validering:** dagbogssidens sted ∈ tidstavlens opholdssted samme dag | 4.137 af 4.216 sammenlignelige sider stemmer (98 %); 79 afviger, mest rejsedage (Napoli ↔ Capri/Paestum; Livorno/Pisa ↔ Torino) | Kvalitetskontrol af stedregisteret; afvigelserne er en redaktionel gennemgangsliste |
| 2 | **Manglende persontags:** person nævnt i tidstavlen i en periode, hvor dagbogssider findes, men ingen side har personen tagget | 102 tilfælde (fx Chamisso 1831-06-12, Spohr 1833-04-30); 50 yderligere uden nogen dagbogsside i perioden | Kandidater til registerrettelser |
| 3 | **Dagbogens huller:** opholds-/rejsedage fra 1825 uden dagbogsside | 5.509 af 10.159 dage (54 %) | Kalenderen viser nu, hvor Andersen var, når dagbogen tier |
| 4 | **Rejseruter:** led med ≥ 2 linkede steder | 584 af 610 rejseled; 628 af de 630 steder i tidstavlen har koordinater | Rutelag på `kort.html` (bygget) |
| 5 | **Hvem × hvor × hvornår:** personer med dateret sted | ca. 150 personer; fx Jenny Lind i Berlin 19. dec. 1845 – 7. jan. 1846, Weimar 8. jan. – 7. feb. 1846, Wien 24.–29. maj 1854 | «Tidstavle: hvor og hvornår» på personsider (bygget); kandidatkilde til «Begivenhedsdatoer»-facetten |
| 6 | **Værker:** citerede `»titler«` mod værkregisteret | 49 værker knyttet til udgivelsesdato; kun 20 af 49 nævnes i dagbogssider inden for ±60 dage | Tynd forbindelse mellem tilblivelse og udgivelse — kræver bedre værkmatchning før den bruges |
| 7 | **`rejser.tsv`-dækning:** ankomst til opholdssted findes i tidstavlen samme dag | 454 af 601 | De fleste af de øvrige 147 er stavning (Hamborg ↔ Hamburg), så tallet siger kun noget om dækning |

## Kendte begrænsninger

* **Linkning er konservativ.** 2.756 stedlinks, 206 personlinks, 49 værklinks.
  Homonymer, fornavne alene og genitiver af enkeltord linkes ikke. Der er ikke
  målt recall mod en gold-standard (se planens trin 1.3).
* **Forfatteren selv linkes aldrig.** Registrets «Andersen, Hans Christian» er en
  fotograf fra Nykøbing Mors.
* **Stedregisteret mangler enkelte steder** (fx Genua), som derfor ikke linkes.
* **Poster med periode > 1 dag** tæller som dækkende hver dag i perioden;
  nøstede poster (et ophold og et delophold med samme tekst) vises begge.
* **ID-kollision (rettet 2026-10-28, plan trin 1.1):** xlsx-tidstavlens id'er var
  løbende `T0001…` og kolliderede med `event_id` i
  `data/normalized_v092/timeline.csv` (alle 1.446). De er nu `TV{bind:02d}{regnearksrække:04d}`
  (fx `TV010005`) med `content_key` (`c`) i `timeline.js`; SQL-id'erne er uændrede.
