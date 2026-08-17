# Rolle / Erhverv-facettering af personregistret

`scripts/parsers/parse_person_role.py` gennemgår de 10.228 poster i
PERSON-REGISTRET og tildeler hver person nul, én eller flere af 9
erhvervs-/rolle-buckets, fra to uafhængige kilder:

- **a) VÆRK-REGISTER-optræden** — en person der har skabt et registreret
  værk får den bucket, værkets fløj svarer til (BILLEDKUNST →
  Kunstner/Billedkunst, BIBLIOTEK → Forfatter/Digter, TEATER & MUSIK →
  Musiker/Scenekunst).
- **b) En høst af beskrivelsesfeltet** — se metodeafsnittet nedenfor.

Resultatet eksponeres som en **facet** på `persons.html` og skriver ikke
til registrets øvrige datafelter — samme princip som Køn-facetten. En
person uden match i nogen af de to kilder får en tom rolleliste; det er
**ikke en fejl**, det er den samme "ingen pålidelig kategorisering endnu"-
holdning som "Endnu ubestemt" på Køn-facetten.

## Resultat efter første kørsel

| Kilde | Antal personer |
|---|---:|
| Kun VÆRK-REGISTER | 49 |
| Kun beskrivelses-høst | 5.132 |
| Begge kilder | 383 |
| **I alt med mindst én rolle** | **5.564 (54 %)** |
| Uden rolle (uklassificeret) | 4.664 (46 %) |

Fordeling pr. bucket (en person kan tælle i flere buckets):

| Bucket | Antal |
|---|---:|
| Embedsmand/Jura/Politik | 1.065 |
| Handel/Erhverv | 939 |
| Forfatter/Digter | 931 |
| Akademiker/Lærd | 878 |
| Adel/Kongelig/Hof | 832 |
| Musiker/Scenekunst | 821 |
| Militær | 699 |
| Kunstner/Billedkunst | 526 |
| Gejstlig | 361 |

## Kilde A: VÆRK-REGISTER-optræden

`WORKS_EXTRA.author` (bygget af `build_works_extra.py`) matches mod
personregistrets labels via **samme `nameKey()`-funktion som
`mockup/js/entity-refs.js`s `worksByAuthor()`** — porteret 1:1 til Python
(surname+initialer, foldet for danske tegn). Dette er bevidst: en anden
matching-logik ville kunne give en anden persons-rolle end den, læseren
allerede ser på personens egen side (VÆRK-REGISTER-krydshenvisningen) eller
på `nation.html` ("Af kunstnere fra denne nation").

## Kilde B: høst af beskrivelsesfeltet — to trin, som opgaven bad om

**Trin 1 — klynge efter hyppighed.** Hvert stort forbogstavs-ord i alle
9.466 udfyldte beskrivelser (92,5 % af registret) blev talt, efter at
kendte ikke-erhvervsord (nationalitetsadjektiver, månedsnavne,
strukturord) var frasorteret. 6.175 distinkte kandidatord kom ud af det;
de hyppigste: `professor` 323, `forfatter` 304, `kammerherre` 263,
`maler` 248, `sognepræst` 240, `digter` 238, `teater` 224, `skuespiller`
184, `student` 183, `kaptajn` 164, `komponist` 161, `etatsraad` 149 …

**Trin 2 — klynget i buckets til filterpanelet.** De ~185 hyppigste,
reelt erhvervsbetegnende ord er hånd-klynget i
`data/curated/person_role_terms_da.csv` (kolonner `term,bucket,notes`) i
9 buckets:

| Bucket | Eksempler på termer |
|---|---|
| Gejstlig | sognepræst, biskop, provst, kapellan, theolog |
| Militær | kaptajn, oberst, løjtnant, general, søofficer |
| Adel/Kongelig/Hof | kammerherre, konge, dronning, greve, hofdame |
| Embedsmand/Jura/Politik | etatsraad, amtmand, borgmester, konsul, advokat |
| Handel/Erhverv | grosserer, købmand, bankier, direktør, fabrikant |
| Akademiker/Lærd | professor, lærer, læge, historiker, ingeniør |
| Kunstner/Billedkunst | maler, billedhugger, arkitekt, tegner, fotograf |
| Musiker/Scenekunst | skuespiller, komponist, operasanger, dirigent |
| Forfatter/Digter | forfatter, digter, oversætter, redaktør, journalist |

Et term der ikke er i CSV'en bidrager ikke til nogen bucket — hverken
sikkert eller usikkert, det tælles bare ikke. Efter hver kørsel udskriver
scriptet hvilke CSV-termer der **aldrig** ramte noget i korpusset (0 i
skrivende stund) — et signal om stavefejl eller termer der reelt ikke
forekommer, der ellers ville stå ubemærket i filen.

## Referent-sikring: hvem beskriver en slægtningsklausul?

Samme problemklasse som `parse_person_gender.py` måtte løse for Køn: et
erhvervsord lige efter en slægtningsklausul kan beskrive SLÆGTNINGEN, ikke
personen selv. `RELATION_RE` fjerner en indledende klausul som `Søn af
X,`/`Datter af X,`/`Broder til X,`/`Enke efter X,` (og videre grader:
adoptiv-, sted-, sønnesøn- osv.) før høsten kører, og `MARRIED_RE` gør det
samme for `g. m. X,`-klausuler (inkl. årstalsintervaller som `g.
1846–1870 m. …`, ellers matcher klausulen ikke og en ægtefælles titel
lækker ind — set og rettet på Isabella II af Spaniens post).

**Verificeret empirisk, ikke antaget:** stikprøver på poster med dateret
karriereforløb efter en slægtningsklausul (fx "Søn af Carl T., …,
1876–1894 Direktør for Københavns Sporvejsselskab" på en person der døde
1894) viser, at det resterende forløb efter slægtningens navn beskriver
**personen selv**, ikke slægtningen — det er derfor scriptet kun fjerner
selve slægtningens navn (frem til første komma), og lader resten stå som
personens egen beskrivelse.

**Kendte resterende huller**, dokumenteret frem for gættet væk:

1. **Apposition efter en fjernet ægtefælle-klausul.** `MARRIED_RE` fjerner
   kun frem til næste komma/punktum efter ægtefællens navn — en videre
   apposition ("m. Hertug Francisco de Asis, **titulær Konge af S.**") kan
   stadig beskrive ægtefællen og lække ind. Sjældent (kongelige/adelige
   ægteskabsbeskrivelser med en medregerende titel), ikke forsøgt løst
   generelt.
2. **Erhverv-før-navn i en slægtningsklausul.** Det langt hyppigste mønster
   er `Søn af [Navn], [erhverv]` (erhvervet beskriver personen selv, efter
   navnet) — men et mindretal skrives omvendt, `Søn af [Erhverv], [Navn]`
   (fx "Søn af Apoteker, Assessor pharm. Marx B."), hvor erhvervet reelt
   beskriver FORÆLDEREN. Scriptet skelner ikke mellem de to ordener.
3. **Udaterede, korte slægtningsklausuler uden ankerpunkt.** Uden et
   levetidsinterval at holde et erhvervsord op imod (som Sporvejsselskab-
   eksemplet ovenfor) er der ingen tekstintern måde at afgøre, om et enkelt
   erhvervsord efter et forældrenavn beskriver forælderen eller personen —
   begge læsninger er sproglig gyldige.

Disse er dokumenterede usikkerheder i en facet, ikke krav om
manuel gennemgang af hver post — samme standard som Køn-facettens
"Endnu ubestemt".

## Kørsel

```
python scripts/build_mockup/build_works_extra.py   # forudsætning for kilde A
python scripts/parsers/parse_person_role.py
python scripts/build_mockup/build_persons_extra.py
```

Første script udskriver dækningsrapporten ovenfor samt hvilke CSV-termer
der aldrig ramte noget. For at udvide bucket-dækningen: kør
`parse_person_role.py`, se rapportens uudnyttede høst (høje `word_counts`-
tal, der endnu ikke er i CSV'en — kør frekvenstællingen i scriptets egen
udviklingshistorik, eller filtrer `kilde_beskrivelse_termer`-kolonnen i
`data/normalized/person_role.csv` mod termer der IKKE optræder i
`data/curated/person_role_terms_da.csv`), og tilføj dem til CSV'en.
