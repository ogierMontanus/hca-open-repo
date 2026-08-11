# Stedtypologi for SV-udgavens stedregister — forslag til godkendelse

> **Status: UDKAST — afventer faglig/redaktionel godkendelse.**
> Dette dokument dækker Trin 1–4 af opgaven "Klassifikation af stednavne i
> H.C. Andersens stedregister": grundlag, kategoriforslag, test mod
> registret og en foreløbig endelig liste (11 kategorier, afsnit A–D).
>
> Afsnit E nedenfor er en **redaktionelt anmodet komprimering** af de 11
> kategorier til 6, med foreløbig GeoNames-mapping. Den fulde 11-kategori-
> analyse i afsnit A–D er bevaret som den detaljerede baggrund — de to
> lister lever side om side, indtil den ene er endeligt godkendt.

## Kilde

Primær kilde er `data/raw/SV14_places.xml` i dette repo, som er identisk med
`svNames/data/registers/places.xml` (samme fil, delt mellem den TEI/eXist-db-
baserede redaktionsapplikation og dette repos pipeline). Filen er et TEI
`listPlace`-register med **481 stedposter**, der dækker de stednavne, H.C.
Andersen nævner på tværs af SV-udgavens bind — først og fremmest
rejseskildringerne (bind 14–15), men også barndomsstoffet fra Odense.

## A. Grundlag i stedregistret

### Hvad registret faktisk indeholder

Registrets 481 poster fordeler sig geografisk på nogle klart genkendelige
rejseruter og stofområder: Odense og omegn (barndom), ruten gennem
Slesvig-Holsten og Harzen til Sachsen ("Sachsisk Schweiz"), Berlin/Potsdam,
Italien fra Norditalien til Napolibugten, Malta, Grækenland (Athen og
Kykladerne), det osmanniske rige (Konstantinopel/Istanbul) og
Donau-landene hjem gennem Bulgarien, Serbien og Ungarn. Det er med andre
ord et **rejseregister**: langt de fleste poster er steder, HCA rent
faktisk passerede, boede i, eller besøgte som seværdighed.

### Hvad der reelt bærer klassifikationen

To ting i registret er brugbare som grundlag for en typologi:

1. **Selve stednavnet.** For hovedparten af posterne er navnet i sig selv
   stærkt sigende om stedtypen — endelser og orddele som *-kirke/-kirche*,
   *-slot/-schloss/-burg*, *-teater/-teatro*, *-skov/-wald*, *-torv/-piazza*
   går igen på tværs af sprog og lader sig genkende uden opslag.
2. **Det eksisterende `type`-felt.** 480 af 481 poster har allerede en
   værdi i `@type` — enten en fuldt kvalificeret GeoNames feature-kode
   (fx `P.PPLA3`, `S.CH`, `T.ISL`) for 391 poster, eller den uspecifikke
   placeholder-værdi `PPL` (uden klasse-præfiks) for 90 poster. De 90
   `PPL`-poster er gennemgående lokalt tilføjede — ofte danske
   Odense-lokaliteter eller steder, som en GeoNames-matchning ikke er
   forsøgt eller ikke er lykkedes for — og bærer ingen brugbar
   undertype ud over navnet selv.

`<note>`-feltet, som opgavebeskrivelsen ellers lægger vægt på, er derimod
**tyndt som klassifikationskilde i dette register**: kun 91 af 481 poster
(19 %) har et udfyldt notefelt, og af disse er langt de fleste enten
GPS-koordinater, weblinks (GeoNames, Wikipedia, eller artikler fra
"Danmarks Stednavne") eller redaktørens egne identifikationsbemærkninger
("Holger: dette sted kan jeg ikke finde") — **ikke** beskrivende
stedforklaringer. Kun ét sted (Deià, Mallorca) har egentlig forklarende
brødtekst. De redaktørnoter, der findes, er stadig værdifulde, men til noget
andet end typebestemmelse: de markerer, hvilke poster der har en usikker
eller uafklaret identitet (se afsnit C).

Konklusionen er, at typologien i praksis må bygges på **stednavn +
allerede tildelt type-kode + land/region**, med `<note>` som supplerende
kilde dér, hvor den findes.

### De naturlige grupper, materialet lægger op til

Ved gennemgang af alle 481 poster (navn, evt. note, eksisterende type-kode)
træder følgende grupper tydeligt frem, i faldende størrelse:

| Gruppe der viser sig i materialet | Antal poster (ca.) |
|---|---:|
| Byer, landsbyer, bydele og andre bebyggelser | 209 |
| Naturlige landskabsformer (bjerge, høje, kløfter, grotter, forbjerge, vulkaner) | 50 |
| Kirkelige bygninger (kirker, domkirker, klostre, moskeer) | 36 |
| Vandområder (floder, søer, hav, strædet, kanaler) | 31 |
| Slotte, borge, paladser og herregårde | 29 |
| Gader, pladser, broer og anden bebygget infrastruktur | 26 |
| Fortidsminder, monumenter og gravsteder | 25–26 |
| Teatre, museer og andre kulturinstitutioner | 24–25 |
| Øer | 22 |
| Lande, regioner og landsdele | 15 |
| Parker, haver og naturområder | 12 |

Det svarer til 480 af 481 poster; den sidste (*Falleberthor*) kan slet ikke
identificeres ud fra materialet og er behandlet i afsnit C.

### En vigtig forbeholdsbemærkning om det eksisterende type-felt

Fordi 391 poster allerede har en GeoNames feature-kode, er det fristende at
lade den bære klassifikationen direkte. To konkrete fund viser, hvorfor det
ikke kan gøres ukritisk:

- **Festung Königstein** (en af Europas største fæstningsanlæg) er
  GeoNames-kodet `T.HLL` ("høj") — dvs. terrænnet, ikke bygningsværket.
  Navnet ("Festung" = fæstning) og virkeligheden peger klart på en
  slots-/borgkategori.
- **Lilienstein** findes som to poster med samme navn. Den ene
  (`geo-982821`) peger fejlagtigt på en lokalitet i Mpumalanga, Sydafrika —
  allerede flagget som tvetydig i `data/normalized/sv14_places_ambiguous.csv`.
  Den anden (`geo-2877712`) er det korrekte tyske bordbjerg i Sachsisk
  Schweiz. Et forkert geografisk match gør type-koden værdiløs, uanset hvor
  præcis den ellers er.

Dette er ikke enkeltstående — se den fulde liste i afsnit C. Metodisk regel
7 og 8 i opgavebeskrivelsen ("marker usikre klassifikationer" og "skeln
mellem vores kategori og GeoNames") er direkte relevante her: det
eksisterende type-felt er et **nyttigt signal, ikke en facitliste**.

---

## B. Forslag til overordnet taksonomi

11 kategorier, inden for det ønskede spænd på 8–16.

| Kategori | Definition | Eksempler fra registret |
|---|---|---|
| **Byer, landsbyer og bebyggelser** | Bebyggede steder hvor mennesker bor — fra hovedstæder til landsbyer, bydele og forstæder | Odense, København, Rom, Firenze, Üsküdar (bydel) |
| **Lande, regioner og landsdele** | Politisk-administrative enheder og større geografisk/kulturelt afgrænsede landsdele, uden et enkelt bebygget centrum som referencepunkt | Kongeriget Danmark, Kongeriget Sverige, Tyrol, Peloponnes, Wallakiet |
| **Vandområder** | Alle former for naturligt eller menneskeskabt rindende og stillestående vand — floder, åer, søer, hav, strædet, kanaler | Elbe (floden), Tiberen, Sundet, Bosporus, Dardanellerne |
| **Øer** | Landmasser omgivet af vand, uanset størrelse | Sicilien, Malta, Ischia, Mykonos, Lolland |
| **Landskabsformer og naturfænomener** | Naturligt dannede terrænformer og geologiske fænomener — bjerge, høje, klipper, kløfter, grotter, forbjerge, vulkaner, bjergpas | Vesuvius, Stevns Klint, Brenner-passet, Baumannshöhle (grotte), Acropolis (klippehøjen) |
| **Parker, haver og naturområder** | Menneskeligt anlagte eller fredede grønne områder til rekreation | Tiergarten (Berlin), Villa Borghese (park, Rom), Den Botaniske Have (Odense), Hunderup Skov |
| **Kirker og andre religiøse bygninger** | Bygninger opført til religiøs brug — kirker, domkirker, klostre, moskeer | Hagia Sophia, Sankt Knuds Kirke, Peterskirken, Sultan Ahmed-moskeen ("Blå Moské") |
| **Slotte, borge, paladser og herregårde** | Fyrstelige, adelige eller befæstede residenser og deres anlæg | Kronborg, Frederiksborg Slot, Sanssouci, Topkapı-paladset, Nysø (herregård) |
| **Teatre, museer og andre kulturinstitutioner** | Bygninger/institutioner opført eller indrettet til at opføre eller udstille kunst for et publikum | Det Kongelige Teater, La Scala, Teatro di San Carlo, Konzerthaus Berlin |
| **Fortidsminder, monumenter og gravsteder** | Antikke eller historiske levn, byggede minde­smærker og gravsteder — stedet er interessant, fordi det minder om noget, ikke fordi det bruges i dag | Colosseum, Pompeii, Parthenon, Nonnebakken (vikingeringborg, Odense) |
| **Gader, pladser og anden bebygget infrastruktur** | Byrum og bygningsværker der ikke er bolig, religion, kultur eller fortidsminde — gader, pladser, broer, porte, rådhuse, markeder, hoteller | Kongens Nytorv, Piazza del Popolo, Via del Corso, Brandenburger Tor, Lübeck Rådhus |

### Uddybning pr. kategori: hvad hører under, og hvor er grænserne

**Byer, landsbyer og bebyggelser** (~209 poster, langt den største gruppe).
Dækker alt fra Rom og Berlin til enkeltstående landsbyer og bydele/forstæder
(fx Üsküdar, Beyoğlu, Wandsbek). Omfatter også en række tyske
"administrative" poster (GeoNames `A.ADM3`–`A.ADM5`), som reelt er
landsbyer/småbyer, GeoNames blot har kodet efter deres formelle status som
*Gemeinde* — de er bevidst lagt her og **ikke** under "Lande, regioner og
landsdele", fordi de fungerer som almindelige gennemrejste bebyggelser i
registret, ikke som territoriale enheder. *Grænsetilfælde:* skellet mellem
en meget lille landsby og en bebygget lokalitet uden egentlig bystatus
(fx enkeltstående møller eller stationsbyer) er flydende, men uden praktisk
betydning her.

**Lande, regioner og landsdele** (~15 poster). Suveræne stater
(Kongeriget Danmark, Den Italienske Republik) og større landsdele uden et
enkelt bebygget referencepunkt (Tyrol, Peloponnes, Wallakiet, den
osmanniske provins omkring Ruse). *Grænsetilfælde:* Lüneburger Heide og
Leipziger Tieflandsbucht er GeoNames-kodet som "region" på linje med Tyrol,
men er reelt naturgeografiske landskabstyper (hedeslette, lavland) snarere
end kulturelt/administrativt afgrænsede landsdele — de kunne lige så
rimeligt høre under "Landskabsformer og naturfænomener". Se afsnit C.

**Vandområder** (~31 poster). Bevidst bredt efter opgavens eget
forbillede: floder, åer, søer, hav, strædet/sund og kanaler slås sammen,
uanset størrelse. Havne (fx Grand Harbour i Valletta) er også lagt her, da
de fysisk er naturlige bugter/havbassiner. *Grænsetilfælde:* en havn er
samtidig en menneskeskabt, funktionel installation — den kunne argumenteres
ind under "Gader, pladser og anden bebygget infrastruktur" i stedet. Kun 2
poster er berørt, så det har ingen reel betydning for kategoristørrelsen.

**Øer** (~22 poster). Holdt adskilt fra landskabsformer, dels fordi antallet
er stort nok til at bære en selvstændig kategori (de græske øer fylder
markant i rejseskildringen), dels fordi øer — modsat fx en klippeformation —
ofte selv rummer byer, administration og lokal identitet og derfor
fungerer som en anden slags "sted" i teksten end en bjergtop.

**Landskabsformer og naturfænomener** (~50 poster). Den mest
sammensatte "restkategori" for alt terrænrelateret, der ikke er en ø eller
et vandområde: bjerge, høje, klipper, kløfter, grotter, forbjerge,
vulkaner og bjergpas. Følger opgavens eksempel-princip direkte (ligesom
"Vandløb" samler flod/å/bæk, samler denne kategori bjerg/høj/klippe/kløft
uden at skelne). *Grænsetilfælde:* Acropolis er kodet som selve klippehøjen
i Athen, adskilt fra bygningsværkerne ovenpå (Parthenon, Erechtheion,
Propylaia), som hører under "Fortidsminder". Det er ikke en fejl, men et
eksempel på, at samme fysiske lokalitet kan optræde som to poster med hver
sin stedtype, alt efter om det er terrænnet eller bygningen, der er
omtalt.

**Parker, haver og naturområder** (~12 poster — den mindste kategori,
se overvejelse i afsnit C). Menneskeligt anlagte eller fredede grønne
områder: byparker (Tiergarten, Volksgarten), slotshaver (Villa Borghese),
skove nær Odense (Hunderup Skov, Næsbyhoved Skov) og en botanisk have.
Holdt adskilt fra "Landskabsformer", fordi disse steder er *anlagte* til
rekreation, ikke vild natur.

**Kirker og andre religiøse bygninger** (~36 poster). Kirker, domkirker,
klostre og moskeer på tværs af konfessioner — bevidst én kategori, ikke
opdelt efter trosretning, jf. opgavens princip om at undgå fininddeling.
*Grænsetilfælde:* Galata Mevlevihanesi (et tidligere dervish-kloster/tekke
i Istanbul, i dag museum) ligger på grænsen til "Teatre, museer og andre
kulturinstitutioner" — klassificeret efter bygningens oprindelige religiøse
funktion, ikke dens nuværende brug som museum.

**Slotte, borge, paladser og herregårde** (~29 poster). Fyrstelige og
adelige residenser samt befæstede anlæg — slotte, borge, paladser og
herregårde slået sammen til én kategori, igen efter opgavens
"vandløb"-princip. *Grænsetilfælde:* Taschenbergpalais i Dresden er
GeoNames-kodet som "hotel" (dets nuværende funktion som Kempinski-hotel),
men er historisk et fyrsteligt palads bygget til August den Stærke —
klassificeret efter den historiske bygningstype, som er den relevante for
en HCA-læser, ikke nutidig kommerciel brug.

**Teatre, museer og andre kulturinstitutioner** (~24 poster). Aktivt
fungerende kulturinstitutioner: teatre, operahuse, museer, akademier,
koncertsale. Adskilt fra "Fortidsminder" ved, at stedet er interessant,
fordi det *bruges* til noget i dag (eller på Andersens tid), ikke fordi
det er et levn fra fortiden. Colosseum er *ikke* lagt her på trods af navnet
"amfiteater" — det hører under "Fortidsminder", da det i dag er ruin, ikke
en fungerende scene.

**Fortidsminder, monumenter og gravsteder** (~25 poster). Antikke og
historiske levn, mindesmærker og grave: arkæologiske steder (Pompeji,
Forum Romanum), antikke templer (Parthenon), ruinbyggede monumenter
(Colosseum), gravsteder (Themistokles' grav) og bevidst rejste
mindesmærker (Walhalla, Vendômesøjlen). *Grænsetilfælde:* Grotta di
Pozzuoli — en antik romersk tunnel — ligger på grænsen til
"Landskabsformer" (grotte som naturfænomen) over for denne kategori
(menneskeskabt anlæg fra antikken); og Burg Regenstein/Kız Kulesi (begge
GeoNames-kodet identisk som "ruin(s)") viser, at samme GeoNames-kode kan
dække både en borgruin (→ Slotte/borge) og et tårn/mindesmærke (→ denne
kategori) — "ruin" er ikke i sig selv en stabil stedtype.

**Gader, pladser og anden bebygget infrastruktur** (~26 poster). En bevidst
bred restkategori for byrum og bygningsværker, der ikke er bolig, religion,
kultur eller fortidsminde: gader, pladser, broer, monumentale porte,
rådhuse, markeder og hoteller/værtshuse. *Grænsetilfælde:* kategorien er
den mest heterogene af de 11 og kunne i princippet splittes yderligere
(fx gader/pladser vs. hoteller/markeder), men ingen af undergrupperne når
op på mere end 4–5 poster hver, så en opsplitning ville bryde med
opgavens princip om at undgå fininddeling af små grupper.

---

## C. Tvivlstilfælde

Steder, hvor klassifikationen ikke er entydig, eller hvor selve stedets
identitet er usikker. Ingen af disse er tvunget ind i en kategori uden
forbehold.

1. **Falleberthor** — kan slet ikke identificeres ud fra materialet;
   redaktøren har selv noteret "Holger: Dette sted kan jeg ikke finde."
   Dette er ikke et kategori-valg, men en uafklaret stedidentitet, og bør
   forblive uklassificeret, indtil stedet er identificeret.

2. **Festung Königstein** — GeoNames-kodet som landskabsform (`T.HLL`,
   "høj"), men navn og virkelighed peger på "Slotte, borge, paladser og
   herregårde". Foreslået klassificeret efter navn/virkelighed, ikke
   GeoNames-koden.

3. **Taschenbergpalais Dresden** — GeoNames-kodet som "hotel" (nutidig
   funktion), historisk et fyrsteligt palads. Grænsetilfælde mellem
   nutidig og historisk brug; foreslået klassificeret historisk
   ("Slotte, borge, paladser og herregårde").

4. **Burg Regenstein** og **Kız Kulesi** — begge poster har den identiske
   GeoNames-kode `S.RUIN` ("ruin(s)"), men er reelt to forskellige
   stedtyper: en borgruin i Harzen (→ "Slotte, borge og paladser") og et
   tårn/mindesmærke i Bosporus-strædet (→ "Fortidsminder, monumenter og
   gravsteder"). Viser, at "ruin" alene ikke er en brugbar stedtype uden
   at vide, hvad ruinen var.

5. **Lilienstein** — findes som to separate poster med samme navn.
   `geo-982821` peger fejlagtigt på en lokalitet i Mpumalanga, Sydafrika,
   og er allerede flagget som tvetydig i
   `data/normalized/sv14_places_ambiguous.csv`. `geo-2877712` er det
   korrekte tyske bordbjerg. Dette er et identifikationsproblem, ikke et
   klassifikationsproblem — men indtil identiteten er rettet, er
   type-feltet på den fejlkoblede post værdiløst.

6. **Grotta di Pozzuoli** — en antik romersk tunnel/grotte (Crypta
   Neapolitana). Grænsetilfælde mellem "Landskabsformer og naturfænomener"
   (grotte som naturfænomen) og "Fortidsminder, monumenter og gravsteder"
   (menneskeskabt anlæg fra antikken).

7. **Lüneburger Heide** og **Leipziger Tieflandsbucht** — GeoNames-kodet
   som "region" (`L.RGN`) på linje med Tyrol og Peloponnes, men er reelt
   naturgeografiske landskabstyper (hedeslette, lavland). Grænsetilfælde
   mellem "Lande, regioner og landsdele" og "Landskabsformer og
   naturfænomener".

8. **Acropolis** — kodet som selve klippehøjen, adskilt fra
   bygningsværkerne ovenpå (Parthenon, Erechtheion, Propylaia), som har
   egne poster under "Fortidsminder". Ikke en fejl, men et eksempel på,
   at samme fysiske lokalitet kan give anledning til flere poster med
   forskellig stedtype.

9. **Ni poster med redaktørens egen usikkerhedsmarkering** — *Museet*,
   *det kongelige Theater*, *Königstätisches Theater*, *Klosteret St.
   Antonio*, *Der Kaiser von Rusland*, *Operahuset Webers*, *Teatro
   Pallacorda*, *Teatro Fenise* og *Linchkeschen Bade* har alle en note af
   typen "Holger: ... kan jeg ikke finde" eller "jeg er i tvivl om
   hvilket teater". De er foreløbigt klassificeret efter navnemønster
   (teater, kloster, hotel, bad), men klassifikationen er ikke mere sikker
   end selve stedidentifikationen og bør revurderes, når/hvis stedet
   identificeres endeligt.

10. **De 90 poster med den uspecifikke type-værdi `PPL`** — dette er ikke
    ét sted, men en strukturel usikkerhed, der gælder næsten en femtedel
    af registret: disse poster mangler den mere specifikke GeoNames-kode,
    som findes for resten af registret, og er klassificeret alene ud fra
    navnemønstre (fx "-kirke", "-slot", "-teater"). Fejlrisikoen er højere
    her end for poster med et bekræftet GeoNames-opslag, og bør
    stikprøvekontrolleres, hvis kategorifeltet senere skal indarbejdes i
    registret.

**Kategorier, der er tætte på grænsen for "kun brugt til ganske få
steder":** "Parker, haver og naturområder" (12 poster) er den mindste af
de 11 kategorier. Den er bevaret som selvstændig kategori, fordi den
dækker en tydelig og redaktionelt meningsfuld type (anlagte grønne
områder), men bør holdes under opsyn — falder antallet yderligere ved
fremtidige tilføjelser til registret, er det oplagt at lægge den sammen
med "Landskabsformer og naturfænomener".

---

## D. Forslag til endelig liste (til faglig godkendelse)

1. Byer, landsbyer og bebyggelser
2. Lande, regioner og landsdele
3. Vandområder
4. Øer
5. Landskabsformer og naturfænomener
6. Parker, haver og naturområder
7. Kirker og andre religiøse bygninger
8. Slotte, borge, paladser og herregårde
9. Teatre, museer og andre kulturinstitutioner
10. Fortidsminder, monumenter og gravsteder
11. Gader, pladser og anden bebygget infrastruktur

Denne liste er et **forslag**. Den skal bekræftes — eller justeres — af en
fagkyndig/redaktionel bruger, før den lægges fast. Særligt tre punkter bør
den fagkyndige bruger tage stilling til:

- Om "Parker, haver og naturområder" (12 poster) skal bevares som egen
  kategori eller lægges sammen med "Landskabsformer og naturfænomener".
- Om de tyske `A.ADM3`–`A.ADM5`-poster (småbyer/landsbyer) korrekt hører
  under "Byer, landsbyer og bebyggelser" og ikke under "Lande, regioner og
  landsdele", som deres GeoNames-klasse ellers antyder.
- Om "Gader, pladser og anden bebygget infrastruktur" er for bred, eller
  om den bør splittes (fx gader/pladser vs. hoteller/markeder) på trods af
  de små undergruppestørrelser.

**Trin 5 (GeoNames-mapping af de godkendte kategorier til Feature
Classes/Codes) igangsættes først, når denne liste er godkendt.** — se dog
afsnit E for en foreløbig mapping af den komprimerede 5-kategori-variant,
udført efter direkte redaktionel anmodning, samt en afprøvning mod det
store STED-REGISTER.

---

## E. Komprimeret variant (5 kategorier) med GeoNames-mapping og test mod STED-REGISTER

Redaktionelt ønske, i to omgange: (1) slå de 11 kategorier sammen til
færre — samle *alle* bygninger, inklusive kulturinstitutioner og
fortidsminder, i én kategori, holde bygninger adskilt fra bebyggede
områder, droppe "Øer" som selvstændig kategori; (2) lægge "Parker, haver
og naturområder" ind under bygningskategorien også, så resultatet er
**5** kategorier, ikke 6. Afprøvet først mod de 480 klassificerede poster
fra afsnit A–D, derefter — for at teste generaliserbarheden — mod det
langt større STED-REGISTER i `data/normalized/entities.csv` (2508 poster).

### Sammenlægningen

| Ny kategori | Sammensat af (afsnit B) |
|---|---|
| Bebyggede områder | Byer, landsbyer og bebyggelser |
| Lande, regioner og landsdele | (uændret) |
| Vandområder | (uændret) |
| Landskabsformer og naturfænomener | Landskabsformer og naturfænomener + Øer |
| Bygninger, anlæg, fortidsminder og parker | Kirker og religiøse bygninger + Slotte/borge/paladser/herregårde + Teatre/museer/kulturinstitutioner + Fortidsminder/monumenter/gravsteder + Gader/pladser/bebygget infrastruktur + Parker/haver/naturområder |

Bemærk: at lægge "Øer" ind under landskabsformer matcher GeoNames' egen
klassestruktur — `T.ISL` (island) hører allerede til Feature Class **T**
("mountain, hill, rock, area"). At lægge "Parker, haver og naturområder"
ind under bygningskategorien er derimod en ren redaktionel beslutning
uden tilsvarende GeoNames-begrundelse: parker/haver er GeoNames-klasse
**L**, ikke **S** — sammenlægningen samler altså to forskellige
GeoNames-klasser i én af vores kategorier, mens den efterlader
"Landskabsformer" som den eneste kategori, der stadig falder pænt inden
for én enkelt GeoNames-klasse (bortset fra Vandområder).

### Kategoristørrelser (n=480 klassificerede poster, SV14-registret)

| Kategori | Antal poster | Andel |
|---|---:|---:|
| Bebyggede områder | 209 | 44 % |
| Bygninger, anlæg, fortidsminder og parker | 153 | 32 % |
| Landskabsformer og naturfænomener (inkl. øer) | 72 | 15 % |
| Vandområder | 31 | 6 % |
| Lande, regioner og landsdele | 15 | 3 % |

### GeoNames-mapping

| Vores kategori | GeoNames Feature Class | GeoNames Feature Code | GeoNames-term | Bemærkning |
|---|---|---|---|---|
| Bebyggede områder | **P** | `P.PPL` | populated place | Inkluderer de tyske `A.ADM3`–`A.ADM5`-poster (Elben, Uelzen, Thale m.fl.), der reelt er landsbyer, selvom GeoNames koder dem administrativt |
| Lande, regioner og landsdele | **A** | `A.ADM1` | first-order administrative division | Spænder reelt hele A-klassen (`A.PCLI` for suveræne stater som Kongeriget Danmark, `A.ADM2` for provinser som Napoli) samt to L-klasse "region"-koder (`L.RGN`, `L.RGNH`: Tyrol, Wallakiet, Lüneburger Heide). Ingen enkelt kode dækker kategorien præcist |
| Vandområder | **H** | `H.STM` | stream | Hyppigste enkeltkode (floder/åer, 16 af 31). Klassen dækker desuden søer (`H.LK`), have (`H.SEA`), strædet (`H.STRT`), bugter/havne (`H.BAY`/`H.HBR`), kanaler (`H.CNL`) |
| Landskabsformer og naturfænomener (inkl. øer) | **T** | `T.HLL` | hill | `T.ISL` (island, 22 poster) er faktisk den hyppigste enkeltkode i denne kategori, foran `T.HLL` (hill, 9). `T.HLL` er valgt som sprogligt mest generisk term, men `T.ISL` bør overvejes som alternativ, hvis øer skal kunne genfindes som egen facet |
| Bygninger, anlæg, fortidsminder og parker | **S** (+ **L** for parker) | `S.BLDG` | building(s) | Samlekategori for kirker (`S.CH`), slotte/borge/paladser (`S.CSTL`, `S.PAL`), teatre/museer (`S.THTR`, `S.MUS`), fortidsminder (`S.ANS`, `S.MNMT`, `S.RUIN`), gader/pladser/broer (`S.SQR`, `S.BDG`, samt R-klasse-veje: `R.RD`, `R.ST`) **og** parker/haver (`L.PRK`, klasse L). Denne kategori er nu den eneste, der spænder over to GeoNames-hovedklasser |

**Implementeringsanbefaling, ikke en indvending mod kompressionen:**
`S.BLDG` som repræsentativ kode er nødvendigvis upræcis, fordi kategorien
nu dækker seks tidligere delkategorier. 480 af 481 poster har allerede en
mere præcis undertype i registrets eget `type`-felt. Anbefaling uændret
fra tidligere: gem undertypen som en finere valgfri "subtype"-kolonne ved
siden af den brede kategori.

### Test mod STED-REGISTER (2508 poster) — zero-shot navnemønster

`data/normalized/entities.csv` (`entity_type='place'`, `category_h1=
'STED-REGISTER'`) er hele SV-udgavens printregister på tværs af *alle*
værktyper (eventyr, digte, romaner, skuespil, selvbiografier — ikke kun
rejseskildringerne) — 2508 poster, ca. 5× SV14-registret. Filen har
**ingen** `<note>`/`description` og **intet** eksisterende GeoNames-
`type`-felt. Klassifikationen kan derfor kun ske zero-shot: minimale
navnemønstre (endelser/led som "-kirke", "-slot", "-sø", "-bjerge",
"-rige") ekstraheret fra de samme mønstre, der virkede på SV14-registret.
76 poster er rene krydshenvisninger ("X, se: Y") og indgår ikke i testen.

**Dækning (positivt matchede navnemønstre):**

| Kategori | n | Andel af 2432 |
|---|---:|---:|
| Bebyggede områder *(default — intet mønster matchede)* | 2278 | 93,7 % |
| Vandområder | 67 | 2,8 % |
| Bygninger, anlæg, fortidsminder og parker | 44 | 1,8 % |
| Landskabsformer og naturfænomener | 35 | 1,4 % |
| Lande, regioner og landsdele | 8 | 0,3 % |

**Stikprøvekontrol (håndkontrolleret, ikke automatisk facit):**

- **Vandområder (67):** ~98 % korrekte. Danske/tyske vandords-endelser
  (sø/fjord/kanal/bugt/strædet/flod/elv) er et rent og lavtvetydigt signal.
- **Lande, regioner og landsdele (8):** 100 % korrekte, men meget lille n.
- **Landskabsformer (35):** ~90 % korrekte. Fejlkilde: "Berg, Slot" (et
  slot, ikke et bjerg) og lignende navne, hvor et landskabsord indgår i
  et bygningsnavn.
- **Bygninger m.v. (44):** kun ~70–75 % korrekte. Systematisk fejlkilde:
  tyske/østrigske stednavne, hvor et landskabsord er *frosset ind i selve
  navnet* uden længere at beskrive stedet — **Grindelwald** og
  **Mittenwald** er byer, ikke skove; **Waldheim** er en by (kendt for
  sit fængsel), ikke "hjemme-skoven"; **Saarbrücken** er en storby, ikke
  "en bro"; **Partenkirchen** og **Sieghartskirchen** er byer, ikke
  kirker; **Neumünster** er en by, ikke en domkirke. Et navnemønster kan
  ikke skelne "stedet ER en bro/skov/kirke" fra "stedets navn *indeholder
  ordet for* bro/skov/kirke".
- **Bebyggede områder (default-bucket, 2278 poster, stikprøve n=50):**
  **kun ~68 % vurderet korrekte.** ~28 % er reelt fejlplacerede — slotte
  (Schönbrunn, Wesenstein), bjerge (Pilatus, Halleberg), en flod (Brenta),
  en sø (Kochelsee), øer (Ægina), et fort (Trekroner), et fortidsminde
  (Pompei), en vulkansk lokalitet (Solfatara), lande (Brasilien,
  Connecticut) og en å i førreform-1948-retskrivning (**Storaaen** —
  matcher ikke "å"-mønsteret, fordi det er stavet med dobbelt-a; jf.
  `place-toponymy.md`s pointe om historisk retskrivning) — alle uden et
  matchende navnemønster, fordi de er egennavne uden et generisk
  stedords-led. Resten (~4 %) er usikre/uidentificerbare.

**Samlet akkurathedsestimat:** vægtet efter kategoristørrelse ≈
0,937 × 68 % (default-bucket) + 0,063 × ~88 % (blandet på tværs af de
fire positivt matchede kategorier) ≈ **69–70 % korrekt klassificering af
hele STED-REGISTER**, hvis zero-shot navnemønster-metoden anvendes
ukritisk. Det svarer til, at **omkring 700–750 af de 2432 poster**
sandsynligvis ville få tildelt en forkert kategori.

**Konklusion:** metoden, der fungerede rimeligt på SV14-registret (fordi
et eksisterende GeoNames-`type`-felt kunne bære det meste af arbejdet),
generaliserer **ikke** godt til STED-REGISTER alene ud fra navnet.
Hovedårsagen er strukturel, ikke en løsere regeludformning: kendte
egennavne (Schönbrunn, Pilatus, Ægina) bærer ingen generisk stedords-
markør, og stednavne, der historisk *stammer fra* et landskabsord
(-wald, -kirchen, -brücken), er ikke længere beskrivende for stedets
aktuelle type. En brugbar klassifikation af STED-REGISTER kræver enten
(a) et opslag mod en ekstern autoritetsfil (GeoNames/GND-stil, som for
SV14-registret) for i det mindste de mest befolkningstunge/kendte
poster, eller (b) en kurateret undtagelsesliste over kendte fejlkilder
(tyske -wald/-kirchen/-brücken-stednavne, historiske å/aa-stavemåder),
før feltet kan bruges redaktionelt. Ren zero-shot navnemønster-
klassifikation bør ikke skrives direkte til registret uden denne
verifikation.
