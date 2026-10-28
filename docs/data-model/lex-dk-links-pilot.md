# Lex.dk-links til personer — pilot på 50 kendte personer

Status: kørt 2026-10-28 · plan for opskalering: [`../plan-lex-dk-links.md`](../plan-lex-dk-links.md) ·
resultatfil: `data/curated/lex/persons_lex_links.csv` (forslag, ikke promoverede) ·
værktøjer: `scripts/parsers/lex_chatbot_query.js`, `scripts/parsers/lex_link_candidates.py`

## Hvad blev gjort

1. **Stikprøve:** 100 kendte personer fra personregistret (`data/curated/lex/persons_sample100.csv`;
   håndplukket blandt de mest omtalte i dagbøgerne plus en række kendte navne som Thorvaldsen,
   Kierkegaard, Liszt, Mozart). Kørslen blev stoppet efter 50 personer, som aftalt.
2. **Spørgsmål til Lex' chatbot** (`https://spoerg.lex.dk/`, «testversion», «AI kan lave fejl»):
   ét spørgsmål pr. person i en ny samtale, 6 s pause mellem samtaler, ikke-nødvendige
   cookies afvist: *«Hvem var {navn (år), erhverv}? Giv link til artiklen i Dansk Biografisk
   Leksikon og til andre udførlige leksikonartikler om personen.»*
3. **Kun links gemmes** fra chatbottens *kilde-kort*. Svarteksten (som citerer Lex' artikler) er ikke
   committet.
4. **Verifikation** (`lex_link_candidates.py`): artiklens URL-slug skal indeholde personens
   navneled; derefter hentes siden **én gang** (1 forespørgsel/sek., cache), og sidens egen
   titel/indledning skal indeholde registerets fødsels- **og** dødsår.

## Resultater (n = 50, hvoraf 1 ekstra forespørgsel blev afbrudt og er udeladt)

| Mål | Resultat |
|---|---|
| Mindst ét **bekræftet** lex.dk-link (navn i slug + begge årstal på siden) | **46 af 50 (92 %)** |
| Bekræftet **Dansk Biografisk Leksikon**-artikel | **31 af 50 (62 %)** |
| Bekræftet kun i andre værker (lex.dk-artikel, Den Store Danske, Danmarkshistorien, kvindebiografisk) | 15 |
| Ingen bekræftet | 4 (Napoleon, Bernhard von Beskow, Elisabeth Jerichau-Baumann, Andreas Munch) |
| Døde links (HTTP-fejl) | 0 |
| Kandidater i alt / pr. person | 95 / ca. 1,9 (48 personer har ≥ 1 kandidat efter navnefilteret) |
| Verdikter: bekræftet · sandsynlig · uoverensstemmelse | 87 · 3 · 5 |
| Bekræftede links pr. værk | lex.dk 43 · DBL 31 · Danmarkshistorien 11 · Dansk Kvindebiografisk 1 · Den Store Danske 1 |

**Tid og omfang:** ca. 33 sek. pr. person inkl. pause (≈ 28 min for 50). Ingen 429-fejl eller
blokeringer observeret, men Lex har ikke offentliggjort en grænse (ikke undersøgt). Rå svar fylder
gennemsnitligt 9,7 kB pr. person (≈ 490 kB for 50) — de må **ikke** læses ind i modelkonteksten;
kun de aggregerede CSV'er.

## Vigtige fund

1. **Chatbotten opfinder URL'er.** Bedt om kun et «link» producerer den slugs, der ligner de rigtige,
   men ikke findes (`J.P.E.Hartmann`, `Niels_W.Gade`; de rigtige er `J.P.E._Hartmann`, `Niels_W._Gade`).
   Stilles et almindeligt spørgsmål, citerer den i stedet *rigtige* artikler som kilde-kort. **Kun
   kilde-kort-links accepteres; URL'er kun i svarteksten afvises.**
2. **Et kilde-kort kan høre til en nabo-artikel** (artiklen *nævner* personen). Derfor afgøres
   identiteten af URL-sluggen og af artiklens egne årstal, ikke af kortets tekst. Nabo-fund
   (fx `Carl_Dahlén` som kilde for Johanne Luise Heiberg) forkastes automatisk.
3. **Navnebrødre er reelle:** `J.L._Heiberg_-_dramatiker` (Johan Ludvig, 1791–1860) dukkede op for
   Johanne Luise Heiberg (1812–1890) → «sandsynlig» ved at kun ét af to årstal passer.
   `Peter_Andreas_Munch` → «uoverensstemmelse» for Andreas Munch (1811–1884).
4. **15 personer har bekræftede links, men intet i DBL:** 11 udlændinge (Jenny Lind, Bjørnson, Goethe,
   Schiller, Dickens, Shakespeare, Beethoven, Rubens, Rafael, Canova, Fredrika Bremer — som forventet,
   DBL er et dansk værk) og 4 **danskere** (C.E. Fenger, J.A. Jerichau, C.C. Hall, J.L. Heiberg), hvor
   DBL-artiklen sandsynligvis findes, men chatbotten ikke citerede den (for Hall peger det fundne
   DBL-link `Carl_Hall` på en anden/ukonfirmeret person). **Chatbottens recall for DBL er altså lavere end 100 %** → en deterministisk
   slug-søgning i lex.dk's sitemap bør supplere (se planen).
5. **Navnevarianter** vælter chatbot og matching: *Napoleon 1.* (lex: `Napoleon_Bonaparte`),
   *Fr. Paludan-Müller* (DBL: `Fr._Paludan-Müller`), *Elisabeth Jerichau-Baumann* (`…Jerichau_Baumann`).
   Matcheren tåler nu bindestreg, forkortelser (Fr. ↔ Frederik) og initialer (C. E. ↔ Carl Emil);
   kongelige og skrivemåder må have manuelt *søgenavn*.
6. **Registerfejl opdaget:** «Bjørnstjeme» (OCR af *Bjørnstjerne*) i `Reg0039030` — retsættes ikke
   her, men bør tilføjes til `person-register-ocr-typos.md`.
7. **Informationen er ikke licensfri.** `lex.dk/robots.txt` udelukker AI-crawlere (anthropic-ai,
   GPTBot, CCBot …) og kræver godkendelse til AI-brug af indholdet. Piloten stiller små, sekventielle
   spørgsmål og gemmer kun links; en opskalering bør aftales med Lex (`chatbot@lex.dk` fremgår af
   chatbottens side).

## Begrænsninger ved piloten

* n = 50 af en udvælgelse, der er **skæv mod kendte og hyppigt omtalte** personer; hitraten
  gælder ikke de perifere personer (se planens screening).
* Verifikationen af «bekræftet» betyder: navn i slug + begge registerårstal på artiklens side.
  Det udelukker ikke en navnebror med samme levetid; stikprøvekontrol anbefales (planen: 10 %).
* Ingen af resultaterne er skrevet til personregistret eller vist på siden.
