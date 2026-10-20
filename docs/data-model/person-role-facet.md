# Erhvervsgren-facettering af personregistret

> Facetten hed før 2026-10-20 "Rolle / Erhverv". Omdøbte buckets: "Handel/Erhverv" →
> "Erhverv", "Akademiker/Lærd" → "Lærd/Akademisk uddannelse uden for jura og teologi".

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
| Erhverv | 939 |
| Forfatter/Digter | 931 |
| Lærd/Akademisk uddannelse uden for jura og teologi | 878 |
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
| Erhverv | grosserer, købmand, bankier, direktør, fabrikant |
| Lærd/Akademisk uddannelse uden for jura og teologi | professor, lærer, læge, historiker, ingeniør |
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

## Uklassificerede personer: klynger til manuel bucket-tildeling

De 4.664 personer uden rolle kan gennemgås klyngevis i stedet for én ad
gangen. `scripts/parsers/cluster_unassigned_roles.py` grupperer dem efter
erhvervsord i beskrivelsen i 20 klynger (K01–K20) — bevidst *finere* end de
9 buckets, så hver klynge kan afbildes på én bucket (eller på "Ingen
passende bucket"). Samme referent-rensning som `parse_person_role.py`
(`RELATION_RE`/`MARRIED_RE`), plus: nummererede ægteskaber (`g. 1° 1810
m. …`), genitiv+slægtskab-led (`Grev X's Svigersøn`) og ord efter
`hos/af/til/for/under/efter` (arbejdsgiveren, ikke personens eget erhverv)
udelades.

```
python scripts/parsers/cluster_unassigned_roles.py
```

Skriver `data/normalized/person_role_unassigned_clusters.csv` (én række pr.
klynge, tom `bucket`-kolonne), `…_persons.csv` (én række pr. person) og
`…_annotation.xlsx` (samme to tabeller; `bucket` har en dropdown med de 9
buckets). Personer uden erhvervsord rapporteres som restgrupper R1–R4, ikke
som klynger. Annotatorens svar bør føres tilbage som nye termer i
`data/curated/person_role_terms_da.csv`, ikke som direkte persontildeling.

### Manuel klynge-tildeling (2026-10-20)

Annotationsarket `person_role_unassigned_annotation_,manual.xlsx` (kolonne C
pr. klynge) er ført ud i `data/curated/person_role_cluster_buckets.csv`;
`python scripts/parsers/apply_cluster_roles.py` skriver
`data/normalized/person_role_manual.csv`, som `build_persons_extra.py` lægger
ovenpå (kun for personer uden automatisk rolle). Primære og sekundære klynger
tæller begge. Nye erhvervsgrene: **Håndværk** (K14), **Gæstgiveri** (K15),
**Tjenestefolk/Lavtlønnede** (K16), **Landbrug/Søfart** (K17–K18) og
**Endnu ukategoriseret/Uden for kategori/Intet kendt lønnet erhverv** (K19–K20
+ restkategori for de 3.440 personer uden erhvervsord, R1–R4; en person får
den kun, hvis ingen anden gren passer). K05 og K06 stod tomme/med "," i
arket og er sat til Lærd/Akademisk uddannelse uden for jura og teologi.

**Restgruppe R3** (1.784 personer, kun slægtskab/ægteskab/relation i
beskrivelsen) har sin egen gren, **Kun slægtskab angivet**; kun R1, R2 og R4
(1.656) får "Endnu ukategoriseret/…".

**Flere grene pr. person.** En person må høre til flere erhvervsgrene.
Undtagelse: restkategorierne **Kun slægtskab angivet** og **Endnu
ukategoriseret/…** er eksklusive (kolonnen `eksklusiv` i
`person_role_bucket_order.csv`) — de står aldrig sammen med en anden gren og
falder væk, så snart en reel gren tildeles. `build_persons_extra.py`
(`enforce_exclusive`) håndhæver det ved bygning.

**Køn "Andet" → Ukategoriseret.** En post med køn "Andet (især
firmaer/slægter/øvrige grupper)" får altid erhvervsgrenen "Endnu
ukategoriseret/Uden for kategori/Intet kendt lønnet erhverv" — også hvor
parseren eller klyngerne ellers havde givet en gren (fx et bankfirma →
Erhverv). Reglen ligger i `build_persons_extra.py` (`UNCATEGORISED_ROLE`);
før 2026-10-20 var sådanne poster ikke udelukket fra erhvervsgrenene.

**Visningsrækkefølge.** Facetten vises tematisk, ikke efter antal:
`data/curated/person_role_bucket_order.csv` udsendes som `PERSON_ROLE_ORDER` i
`persons-extra.js` og gives til FacetEngine som `fixedOrder.role`. En gren, der
ikke står i filen, vises sidst (efter antal).

### Adelsarv i R2–R4 (2026-10-20)

Et grådigt forsøg på at placere R2–R4 via fagord, lederstillinger og
efternavne blev kasseret som for grumset. Kun adelsarven er bevaret, i
`apply_cluster_roles.py`: en person i R2–R4 med arvelig titel i etiketten
eller med en adelig slægtning ("g. m. Grev X", "Datter af Baron Y") får
**Adel/Kongelig/Hof** i stedet for "Kun slægtskab angivet"/"Endnu
ukategoriseret". Hofembeder (Kammerherre) tæller ikke.

Reglen er siden udrullet til alle andre poster: personer med en klynge- eller
automatisk rolle får Adel/Kongelig/Hof **som tillæg** (kilde `adel+:…` i
`person_role_manual.csv`; 309 poster med automatisk rolle, 68 i klynger).
Uden for R2–R4 kræves titel og slægtskabsord i samme komma-led.
