---
name: wikidata-verify
description: Verify a Wikidata Q-number (or DBpedia/VIAF ID) for a person, place, or artwork before writing it to a file or presenting it to the user. Use whenever assigning, checking, or citing a Wikidata identifier — never from memory alone.
---

# Wikidata-verificering

**Krav:** Efterprøv altid faktuelle oplysninger hentet fra det semantiske web
(Wikidata, DBpedia, VIAF, osv.) via live opslag inden output. Udfør selvkritik
på egne resultater, før de skrives til en fil eller præsenteres for brugeren.

**Baggrund:** I en tidlig session producerede modellen 6 forkerte Wikidata
Q-numre ud af 8 forsøg (fejlrate 75 %) ved ren hukommelsesbaseret gæt. Kun
Q5686 (Charles Dickens) og Q84 (London) var korrekte.

## Procedure

1. Brug `WebSearch` med domænefilter `wikidata.org` for hvert enkelt entitet.
2. Læs det faktiske URL fra søgeresultatet — det indeholder det korrekte Q-nummer.
3. Verificer at entitetsnavnet i URL-titlen matcher det forventede.
4. Erstat aldrig et bekræftet Q-nummer med et ubekræftet hukommelsesbaseret bud.

For værk-Wikidata/hero-billeder i stor skala: se
`scripts/parsers/wikidata_lookup.py` (foreslår kandidater — skriver aldrig
selv til `data/curated/works_wikidata.csv`) og
`docs/data-model/wikidata-hero-images.md`. Samme regel gælder der: en live
opslag kan stadig ramme det forkerte MALERI af den rigtige kunstner (en
kunstner malede ofte samme motiv flere gange til forskellige samlinger) —
bekræft altid samlingen/lokaliteten, ikke kun Q-nummeret.

## Kendte korrekte Q-numre (verificeret)

| Entitet | Q-nummer | Verificeret |
|---------|----------|-------------|
| Charles Dickens | Q5686 | ✓ søgning |
| London | Q84 | ✓ søgning |
| Bleak House (roman, 1853) | Q883305 | ✓ søgning |
| A Christmas Carol (1843) | Q62879 | ✓ søgning |
| Nicholas Nickleby (roman) | Q847642 | ✓ søgning |
| Little Dorrit (roman) | Q565638 | ✓ søgning |
| Odense (by, Danmark) | Q25331 | ✓ søgning |
| Gad's Hill Place (Dickens' hjem) | Q5516441 | ✓ bruger |
| Den gode Hyrde (Murillo, Prado) | Q11694421 | ✓ søgning |
| Den hellige Familie med Fuglen (Murillo, Prado) | Q16627776 | ✓ søgning |
| Den ubesmittede Undfangelse "La Colosal" (Murillo, Sevilla) | Q22120723 | ✓ søgning |
| Jeune mendiant (Murillo, Louvre) | Q5659824 | ✓ søgning |
| La Virgen de la Servilleta (Murillo) | Q2880218 | ✓ søgning |
| Moses slaar Vand af Klippen "La Sed" (Murillo, Caridad) | Q109535214 | ✓ søgning |
| S. S. Justa y Rufina (Murillo) | Q6120755 | ✓ søgning |

## Kendte forkerte Q-numre (må ikke genbruges)

| Entitet | Forkert Q | Årsag |
|---------|-----------|-------|
| Bleak House | Q219420 | Ukendt entitet |
| A Christmas Carol | Q200773 | Ukendt entitet |
| Nicholas Nickleby | Q527099 | Ukendt entitet |
| Little Dorrit | Q327788 | Ukendt entitet |
| Odense | Q3650 | Ukendt entitet |
| Gad's Hill Place | Q5517152 | Forkert sted |
