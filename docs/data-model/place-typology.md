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

## F. Endelig 6-kategori-variant — pragmatisk løsning (Trin 5 godkendt)

Redaktionel afgørelse, baseret på feedback på sektion E: **lav kategorier ned
til 6 i stedet for 5, ved at genoprette "Parker, haver og naturområder" som
egen kategori** (og dermed adskille den fra "Bygninger, anlæg og fortidsminder").
Dette løser det overordnede problem med GeoNames-klasseblanding: hvor
5-kategorivarianten tvang både S (buildings) og L (parks) ind i én kategori,
giver 6-kategorivarianten en klarest mulig struktur uden at blive for granulær.

Samtidig: **pragmatisk sammentrækning af "Lande, regioner og landsdele"** til
én kategori ("Lande, administrative enheder og regioner"), der bevidst
accepterer, at denne kategori blander GeoNames-klasserne A (administrative)
og L (landscape regions) — som et rimeligt trade-off mod at have langt færre,
større kategorier.

### De 6 endelige kategorier

| Nummer | Kategori | GeoNames klasse | Eksempler | Antal poster (SV14) |
|---|---|---|---|---:|
| 1 | **Bebyggede områder** | P | Odense, København, Rom, Berlin, Athen | 209 |
| 2 | **Lande, administrative enheder og regioner** | A + L* | Kongeriget Danmark, Kongeriget Sverige, Tyrol, Peloponnes, Wallakiet, italienske provinser | 15 |
| 3 | **Vandområder** | H | Elbe, Tiberen, Sundet, Bosporus, Dardanellerne, søer | 31 |
| 4 | **Landskabsformer og naturfænomener** (inkl. øer) | T | Vesuvius, Stevns Klint, Baumannshöhle, Acropolis (terrænnet), Sicilien, Malta, Lolland | 72 |
| 5 | **Bygninger, anlæg og fortidsminder** | S | Hagia Sophia, Sankt Knuds Kirke, Kronborg Slot, Colosseum, Parthenon, Peterskirken, Det Kongelige Teater | 153 |
| 6 | **Parker, haver og naturområder** | L | Tiergarten, Villa Borghese, Den Botaniske Have (Odense), Hunderup Skov | 12 |

**I alt:** 492 poster når Falleberthor (uidentificeret) og tvetydighedstilfælde
(se C) medregnes; 491 når der kun tælles entydige klassifikationer.

### Afgrænsning og grænsetilfælde

**Kategori 2: Lande, administrative enheder og regioner.** Denne kategori
er den eneste, der spænder over to GeoNames-hovedklasser (A for stater og
administrativ-hierarki, L for landskabsregioner som Tyrol og Peloponnes).
Det er en pragmatisk ordning: de to typer — suveræne stater, administrative
provinser, og landskabsbaserede regioner — er alle "større stedtyper uden et
enkelt bebygget referencepunkt" og fungerer grammatisk og redaktionelt på
samme niveau i teksten. Samme årsag til sammentrækning gælder Lüneburger Heide
og Leipziger Tieflandsbucht (naturgeografiske landskabstyper, men
GeoNames-kodet som L.RGN). Denne sammentrækning følger opgavens princip om
pragmatisme fremfor akademisk renhed.

**Kategori 5: Bygninger, anlæg og fortidsminder** (uden parker). Denne kategori
dækker alle menneskeskabte bygningsværker og monumenter: kirker, slot/borge,
teatre/museer, fortidsminder, gader/pladser/broer. Ligger entydigt under
GeoNames-klasse S.

**Kategori 6: Parker, haver og naturområder** (egen kategori, ikke indeholdt i 5).
Menneskeligt anlagte eller fredede grønne områder — oprindeligt vurderet til
kun 12 poster i SV14-registret, men en selvstændig og redaktionelt meningsfuld
type. Placeres i GeoNames-klasse L. Adskilt fra både kategori 4 (Landskabsformer,
som er vild natur) og kategori 5 (Bygninger, som ikke er parker).

### Undtagelse: Kanal → Kategori 3 (Vandområder), ikke Kategori 5

**Regel:** Poster af typen *kanal* (menneskeskabt vandvej — sejlkanal,
kanalanlæg, kunstig å) klassificeres som **Kategori 3, Vandområder**, selvom
kanaler er menneskeskabte anlæg og derfor umiddelbart kunne forventes at
høre under Kategori 5 (Bygninger, anlæg og fortidsminder) sammen med andre
konstruktioner (broer, mure, fæstningsværker).

**Begrundelse:** En kanal er funktionelt og fysisk et vandområde — vand
strømmer eller står i den, og den optræder i teksten på linje med floder og
sunde, ikke bygningsværker. GeoNames placerer da også kanaler i
hydrografi-klassen **H**, ikke struktur-klassen **S**, hvilket bekræfter
denne placering. Undtagelsen skal skrives eksplicit, fordi kanalens
menneskeskabte oprindelse ellers er en oplagt fejlkilde for en automatisk
klassifikator, der bruger "menneskeskabt = Kategori 5" som tommelfingerregel
(jf. samme problemstilling for havne, afsnit E).

**Autoritetskoder til automatisk indplacering af høstede poster:**

| Autoritet | Kode | Term | Verificeret |
|---|---|---|---|
| GeoNames Feature Code | `H.CNL` | "canal" — an artificial watercourse | ✓ søgning (download.geonames.org/featureCodes_en.txt) |
| Wikidata | **Q12284** | canal | ✓ søgning — bekræftet af to uafhængige kilder: OpenStreetMap-wikiens `waterway=canal`-tag peger på Q12284, og AGROVOC-konceptet for kanal refererer samme Q-nummer. *Bemærk:* søgning på "canal wikidata" giver også Q8261440 som falsk positiv — dette er et forgrenet Wikidata-item i en sekvens af TV-kanal-numre (Canal 19/28/29/30) og skal **ikke** bruges |

**Praktisk konsekvens for høstningspipelinen:** en høstet post kan
autoklassificeres til Kategori 3, hvis dens kildetype matcher `H.CNL`
(GeoNames) eller er en instans af (P31) Q12284 (Wikidata) — uden manuel
gennemgang, medmindre navnet samtidig indeholder en administrativ markør
(jf. undtagelsesreglen for Kategori 2 vs. 4 ovenfor, som ikke er relevant
for kanaler, men nævnes for konsistens i den automatiske pipeline).

### GeoNames-mapping

| Kategori | Primær GeoNames Feature Class | Typiske Feature Codes | Bemærkning |
|---|---|---|---|
| Bebyggede områder | **P** | P.PPLA, P.PPL, P.PPLC, P.ADM* | Inkluderer de tyske ADM3–ADM5-poster, der reelt er småbyer |
| Lande, administrative enheder og regioner | **A + L*** | A.PCLI, A.ADM1, A.ADM2, L.RGN, L.RGNH | To klasser — pragmatisk løst |
| Vandområder | **H** | H.STM, H.LK, H.SEA, H.STRT, H.BAY, H.HBR, H.CNL | Floder, åer, søer, have, stræder, kanaler |
| Landskabsformer og naturfænomener | **T** | T.HLL, T.ISL, T.MT, T.PK, T.PASS, T.CLF, T.CAVE, T.CAPE, T.VLC | Bjerge, høje, øer, pas, kløfter, grotter, forbjerge, vulkaner |
| Bygninger, anlæg og fortidsminder | **S** | S.CH, S.CSTL, S.PAL, S.THTR, S.MUS, S.ANS, S.MNMT, S.RUIN, S.SQR, S.BDG, R.RD, R.ST | Kirker, slot, teatre, museer, mindesmærker, ruiner, gader, pladser, broer |
| Parker, haver og naturområder | **L** | L.PRK | Byparker, slotshaver, skove, botaniske haver |

### Wikidata-mapping

| Kategori | Primær Wikidata Q-klasse | Eksempler Q-numre |
|---|---|---|
| Bebyggede områder | Q486972 human settlement | Q4016 Odense, Q1748 Athen, Q87 Chicago |
| Lande, administrative enheder og regioner | Q6256 country, Q56061 administrative territorial entity, Q82794 region | Q35 Danmark, Q16 Italien, Q17055 Tyrol |
| Vandområder | Q15324 body of water | Q671 Elbe, Q1029 Bosporus, Q13138 Adriaterhavet |
| Landskabsformer og naturfænomener | Q271669 landform, Q23442 island | Q676 Vesuvius, Q66 Sicilien, Q2061 Parthenon Cliff |
| Bygninger, anlæg og fortidsminder | Q41176 building, Q1371191 structure, Q4989906 monument | Q162 Hagia Sophia, Q34263 Tower of London, Q202054 Colosseum |
| Parker, haver og naturområder | Q22698 park, Q4338161 arboretum, Q1629819 botanical garden | Q670524 Tiergarten, Q1266019 Villa Borghese |

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

---

## G. Opmærkningsinstruktion — kodning af den 6-leddede kategori i TEI-registret

### Formål og princip

Instruktionen beskriver, hvordan den godkendte 6-kategori-taksonomi
(afsnit F) kodes som et **selvstændigt, ikke-destruktivt** klassifikations-
lag oven på det eksisterende GeoNames-baserede `@type`-felt i
`svNames/data/registers/places.xml` (= `data/raw/SV14_places.xml`).
`@type` rører vi ikke — det bliver ved med at bære den granulære
GeoNames-featurekode (`P.PPL`, `S.CH`, `T.ISL` osv.), præcis som i dag.
Vores 6-kategori-taksonomi lægges ved siden af, ikke ovenpå.

**Denne instruktion beskriver skemaet til godkendelse og til brug for
høstningsscripts. Den ændrer endnu ikke selve `places.xml`** — det er et
separat skridt, der kræver eksplicit kørsel af klassifikationsscriptet mod
den levende fil.

### Attribut

Brug `@subtype` på `<place>`-elementet, med et af de 6 faste slug-værdier
nedenfor:

```xml
<place xml:id="geo-2957834" type="P.PPL" subtype="bebygget">
```

**Hvorfor `@subtype` og ikke `@ana`:** TEI's egen anbefaling for en
sekundær, taksonomi-baseret klassifikation er `@ana` (der peger ind i en
`<taxonomy>` i `<classDecl>`, som allerede findes som reference i
`templates/place-types.xml`). Men den *faktiske* praksis i den levende
`places.xml` er allerede at skrive GeoNames-koden som en bar tekststreng i
`@type`, ikke som et `@ana`-pointer-opslag mod classDecl'en. For at følge
etableret praksis frem for teoretisk korrekthed bruges `@subtype` med en
tilsvarende bar slug-værdi — konsistent med, hvordan `@type` allerede
skrives i filen i dag.

### De 6 slug-værdier

| Slug | Kategori | Nummer |
|---|---|:---:|
| `bebygget` | Bebyggede områder | 1 |
| `admreg` | Lande, administrative enheder og regioner | 2 |
| `vand` | Vandområder | 3 |
| `landskab` | Landskabsformer og naturfænomener (inkl. øer) | 4 |
| `anlaeg` | Bygninger, anlæg og fortidsminder | 5 |
| `park` | Parker, haver og naturområder | 6 |

Usikre tilfælde (jf. afsnit C og den anbefalede procedure nedenfor):

| Slug | Betydning |
|---|---|
| `usikker` | Kategori kan ikke afgøres uden forbehold — se `<note>` for begrundelse |

### Beslutningsprocedure (i prioriteret rækkefølge)

En automatisk klassifikator — eller en redaktør, der opmærker manuelt —
skal anvende reglerne i denne rækkefølge og stoppe ved første match:

**1. Navngivne enkelttilfælde (højeste prioritet).** Kendte poster, hvor
`@type` er misvisende eller decideret forkert i forhold til stedets
identitet (se tabellen "Kendte enkelttilfælde med afvigende `@type`"
nedenfor). Disse skal *altid* opmærkes efter deres reelle identitet, ikke
efter den rå GeoNames-kode.

**2. Undtagelsesregler (dokumenteret i afsnit F).**
   - **Kanal** (`H.CNL` og underkoder `H.CNLA/B/D/I/N/Q/SB/X`, samt navne
     med "kanal"/"canal" hvor `@type` mangler) → `vand`, ikke `anlaeg`,
     selvom kanaler er menneskeskabte. Se undtagelsesafsnittet i F.
   - **Grotter/huler** (`S.CAVE`) → `landskab`, ikke `anlaeg`, fordi
     GeoNames placerer naturlige grotter i S-klassen (structure/spot),
     men vores taksonomi følger den oprindelige 11-kategori-analyse
     (afsnit B), hvor grotter hører under Landskabsformer sammen med
     bjerge og klipper. **Undtagelse fra denne undtagelse:** hvis grotten
     er dokumenteret menneskeskabt (fx en antik tunnel, jf. Grotta di
     Pozzuoli i afsnit C, punkt 6) → `anlaeg`.
   - **Haver** (`S.GDN`) → `park`, ikke `anlaeg`, fordi GeoNames'
     "garden(s)" begrebsligt hører under vores kategori 6
     ("Parker, **haver** og naturområder"), selvom S-klassen ellers går
     til `anlaeg`.
   - **Vandfald** (`H.FLLS`, `H.FLLSX`) → `landskab`, ikke `vand`, selvom
     GeoNames placerer vandfald i H-klassen (hydrographic). Fundet ved
     opbygningen af finkategori-laget i afsnit H: både "Helvetes-Faldene
     Trollhätta" (80-cases-rapporten) og "Grande Cascata di Tivoli" (en af
     de individuelt gennemgåede `PPL`-poster) blev allerede konsekvent
     klassificeret som landskab/naturfænomen, ikke vandområde — et
     vandfald er narrativt og perceptuelt et naturskue på linje med en
     klippe eller et bjerg, ikke en sejlbar/gennemstrømmet vandmasse. Ingen
     `H.FLLS`-kodede poster findes i det nuværende SV14-register, så
     undtagelsen ændrer ingen eksisterende klassifikation — den er
     fremtidssikring for høstede poster.
   - **Kategori 2 vs. 4 — administrativ suffiks-regel** (øer, halvøer,
     naturgeografiske enheder): navnet *alene* (uden administrativt
     suffiks) → `landskab`; navnet *med* et administrativt/kirkeligt
     suffiks (stift, sogn, amt, herred, kommune, län, provins, kanton,
     bispedømme, region) → `admreg`. Se den fulde regel med eksempler i
     [`place-categorization-copilot-prompt.md`](place-categorization-copilot-prompt.md).
   - **Tysk/italiensk `A.ADM3`–`A.ADM5`:** klassificeres som `bebygget`
     (småby/landsby), ikke `admreg`, uanset det administrative
     GeoNames-klassepræfiks — se begrundelse i afsnit B og den bekræftede
     stikprøve i afsnit G nedenfor (Elben, Uelzen, Thale, Pozzuoli m.fl.).
     `A.ADM1`–`A.ADM2` går omvendt til `admreg` (større provinser/regioner:
     Lombardia, Calabria, Napoli).

**3. GeoNames Feature Class-opslag** (når intet af ovenstående rammer):
   slå `@type`s klassepræfiks (bogstavet før punktummet) op i tabellen
   nedenfor. Denne tabel er udledt af de koder, der faktisk forekommer i
   SV14-registrets 481 poster — ikke GeoNames' fulde kodeunivers — men
   dækker klasseniveauet generelt, så den kan bruges på ukendte,
   fremtidigt høstede koder inden for samme klasse.

   | GeoNames-klasse | Standard-kategori (slug) | Dokumenterede undtagelser inden for klassen |
   |---|---|---|
   | **P** (populated place) | `bebygget` | — |
   | **A** (administrative) | `admreg` for ADM1–ADM2, PCL*; `bebygget` for ADM3–ADM5 (se regel 2) | — |
   | **H** (hydrographic) | `vand` | `H.FLLS`, `H.FLLSX` (vandfald) → `landskab` |
   | **L** (area/landscape) | `park` for `L.PRK`, `L.RES*` (reservater); `admreg` for `L.RGN`, `L.RGNH` (se regel 2); ellers `landskab` som default for øvrige L-koder | — |
   | **T** (topographic) | `landskab` | — |
   | **S** (spot/structure) | `anlaeg` | `S.CAVE` → `landskab`, `S.GDN` → `park` (se regel 2) |
   | **R** (road/railroad) | `anlaeg` | — |
   | **U** (undersea) | `vand` | (ikke observeret i SV14, men konsistent med H) |
   | **V** (vegetation) | `landskab` | (ikke observeret i SV14) |

**4. Navnemønster** (kun for poster uden brugbar `@type` — fx den
placeholder-værdi `PPL` uden klassepræfiks, eller poster med `@type`
manglende/`null`): anvend de navnemønster-heuristikker, der er dokumenteret
i afsnit E (endelser som "-kirke/-kirche", "-slot/-schloss", "-sø" osv.).
Default ved intet matchende mønster er `bebygget`, jf. den etablerede
konvention for de 90 `PPL`-poster i afsnit A — men **marker resultatet med
lavere sikkerhed** (se format nedenfor), da afsnit E dokumenterer en
estimeret nøjagtighed på kun ~68 % for netop denne default-bøtte, når den
anvendes bredt (STED-REGISTER-testen).

**5. Uafklaret.** Hvis ingen af ovenstående giver et forsvarligt resultat
→ `subtype="usikker"` med en forklarende `<note>`.

### Kendte enkelttilfælde med afvigende `@type`

Fundet ved gennemgang af alle 481 SV14-poster med henblik på denne
opmærkning — ud over de allerede dokumenterede i afsnit C:

| xml:id / navn | `@type` | Hvad koden foreslår | Reel identitet → korrekt subtype |
|---|---|---|---|
| **Lilienstein** (den fejlkoblede post, `geo-982821`) | `S.FRM` (farm) | `anlaeg` | Stedet skal være det tyske bordbjerg i Sachsisk Schweiz (jf. afsnit C, punkt 5), ikke en gård i Mpumalanga, Sydafrika. **`usikker`**, indtil identifikationsfejlen er rettet — herefter `landskab` |
| **Hippodrome of Constantinople** | `S.GDN` (garden) | `park` (jf. regel 2's have-undtagelse) | Det byzantinske hippodrom er et antikt monument/stadion, ikke en have. **`anlaeg`** — regel 1 (navngivet enkelttilfælde) tilsidesætter her regel 2's ellers generelle have-undtagelse |
| **Via Sistina** | `null` (bogstavelig strengværdi, ikke fravær af attribut) | intet | Gadenavn i Rom → `anlaeg` via navnemønster (regel 4: "Via" = gade) |
| **Deya** (Deià, Mallorca) | (intet `@type`, men fyldigt `<note>`) | intet | `<note>` beskriver eksplicit "a small coastal village" → `bebygget` med høj sikkerhed, selvom kilden er noteteksten, ikke en kode |

### Format for usikre eller lavtsikre klassifikationer

```xml
<place xml:id="geo-982821" type="S.FRM" subtype="usikker">
  ...
  <note>Klassifikation usikker: denne post er sandsynligvis fejlkoblet til
  en lokalitet i Mpumalanga, Sydafrika, jf. sv14_places_ambiguous.csv.
  Det tilsigtede Lilienstein (bordbjerg, Sachsisk Schweiz) ville
  klassificeres "landskab".</note>
</place>
```

For poster klassificeret via default-navnemønster (regel 4) med den
dokumenterede lavere nøjagtighed, tilføjes en tilsvarende note, der
navngiver metoden (`"subtype sat via navnemønster-default, ~68% forventet
nøjagtighed, bør stikprøvekontrolleres"`), så efterfølgende gennemgang kan
prioritere disse poster først.

### Anvendelse på høstede poster (nye/eksterne kilder)

For poster, der høstes fra en ekstern kilde med sin egen typekodning
(GeoNames API, Wikidata P31, GND Geografikum-klasse), anvendes samme
firetrins-procedure: slå den indkommende kildekode op mod nærmeste
GeoNames-klasse (de fleste eksterne geo-autoritetsfiler kan mappes til
GeoNames-klassebogstaver), og følg derefter tabellen i regel 3. Kanal- og
kategori-2-vs-4-undtagelserne i regel 2 gælder uændret uafhængigt af
kildesystem, fordi de er defineret på stednavnets semantik, ikke på en
bestemt kildes kodeskema.

---

## H. Finkategori-lag — forslag til andet niveau under de 6 kategorier

> **Status: FORSLAG, afventer godkendelse**, ligesom afsnit F/G indtil de
> blev bekræftet. Testet mod alle 481 SV14-poster (se valideringsafsnittet
> nedenfor), men endnu ikke skrevet til den levende `places.xml`.

### Formål

De 6 kategorier fra afsnit F er bevidst brede — det var selve pointen med
kompressionen fra 11 til 6. Men flere kategorier dækker over stedtyper, der
er tydeligt forskellige for en bruger, der browser eller filtrerer
registret: "Landskabsformer og naturfænomener" rummer både bjerge, øer,
vulkaner og grotter; "Bygninger, anlæg og fortidsminder" rummer både
kirker, slotte, teatre og gader. Et **andet, valgfrit lag** — en
finkategori under hver af de 6 hovedkategorier — giver den detaljering
tilbage uden at gå på kompromis med den brede taksonomi til overbliksbrug
(fx en facet med kun 6 valg).

Finkategorierne er **strengt underordnet** hovedkategorien: en post's
finkategori kan aldrig pege på et andet hovedniveau end den, posten allerede
er tildelt i afsnit F/G. Det gør laget sikkert at tilføje uden at ændre
nogen eksisterende klassifikation.

### Markup — tredje attribut

`@subtype` (afsnit G) bærer fortsat hovedkategorien. Finkategorien kodes i
en **tredje** attribut, `@ana`, efter TEI's egen konvention for et
taksonomi-baseret analyselag (modsat `@subtype`, hvor vi bevidst fulgte den
eksisterende, pragmatiske `@type`-praksis frem for `@ana`). Der er ingen
konflikt: de tre attributter dækker hver sit granularitetsniveau og kan stå
side om side uden indbyrdes afhængighed i selve XML-strukturen (om end
finkategorien indholdsmæssigt altid skal være konsistent med hovedkategorien,
jf. ovenfor).

```xml
<place xml:id="geo-XXX" type="S.CSTL" subtype="anlaeg" ana="#slot_borg">
```

En tilhørende `<classDecl><taxonomy xml:id="place-subgroups">` (parallel til
`templates/place-types.xml`) kan rumme de 32 `<category>`-poster fra
tabellerne nedenfor, hvis `@ana` skal pege ind i en formel taksonomi frem for
blot at bære slug-værdien direkte.

### Finkategorier pr. hovedkategori

Tabellerne er udledt af de GeoNames-koder, der faktisk forekommer i
SV14-registrets 481 poster (samme metode som afsnit G), suppleret med
enkelttilfælde fra de individuelt gennemgåede `PPL`-poster. Antal er talt
ved kørsel mod den fulde register — se valideringsafsnittet.

**Kategori 1 — Bebyggede områder** (209 poster, 5 finkategorier)

| Slug | Navn | GeoNames-koder | Antal (SV14) | Eksempler |
|---|---|---|---:|---|
| `regionssaede` | Regions-/amtssæder | `P.PPLA`, `P.PPLA2–5` | 105 | Palma, Firenze, Helsingør |
| `by_landsby` | Byer og landsbyer | `P.PPL`, `A.ADM3–5` | 63 | Altenberg, Slangerup, Dalum |
| `bydel` | Bydele/sektioner | `P.PPLX` | 28 | Priwall, Travemünde, Wandsbek |
| `hovedstad` | Hovedstæder | `P.PPLC` | 12 | Rom, Berlin, London |
| `historisk_bebyggelse` | Historiske/opgivne bebyggelser | `P.PPLH`, `P.PPLQ`, `P.PPLW` | 1 | Sestos |

*Bemærkning:* `regionssaede` er selv temmelig bred (den slår GeoNames'
egne PPLA–PPLA5-niveauer sammen), fordi disse i praksis alle fungerer som
"en by, der også er administrativt sæde" i registret. En yderligere
opdeling (fx PPLA/PPLA2 = større regionalcentre vs. PPLA3–5 = mindre
sæder) er mulig, hvis facetten viser sig for stor i praksis.

**Kategori 2 — Lande, administrative enheder og regioner** (15 poster, 3 finkategorier)

| Slug | Navn | GeoNames-koder | Antal (SV14) | Eksempler |
|---|---|---|---:|---|
| `landskabsregion` | Landskabsregioner (kultur/natur) | `L.RGN`, `L.RGNH`, `L.RGNE`, `L.RGNL` | 6 | Tyrol, Peloponnes, Böhmen |
| `provins` | Provinser/regionale forvaltningsenheder | `A.ADM1`, `A.ADM2` | 5 | Napoli, Lombardia, Calabria |
| `suveraen_stat` | Suveræne stater | `A.PCLI` | 4 | Kongeriget Danmark, Italien |

**Kategori 3 — Vandområder** (31 poster, 5 finkategorier)

| Slug | Navn | GeoNames-koder | Antal (SV14) | Eksempler |
|---|---|---|---:|---|
| `vandloeb` | Vandløb (floder, åer, kanaler) | `H.STM`, `H.CNL*`, `H.STMC` | 18 | Trave, Alster, Donau-Sortehavskanalen |
| `straede_sund` | Stræder og sunde | `H.STRT`, `H.SD`, `H.NRWS` | 4 | Sundet, Dardanellerne |
| `soe` | Søer | `H.LK`, `H.LKS` | 3 | Lago Maggiore, Lago di Nemi |
| `bugt_havn` | Bugter og havne | `H.BAY`, `H.HBR`, `H.GULF`, `H.COVE` | 3 | Grand Harbour (Valletta) |
| `hav` | Have | `H.SEA`, `H.OCN` | 3 | Sortehavet, Marmarahavet |

**Kategori 4 — Landskabsformer og naturfænomener** (73 poster, 10 finkategorier)
— den kategori brugerens eksempel (bjerge, kontinenter, øer) sigtede mod:

| Slug | Navn | GeoNames-koder | Antal (SV14) | Eksempler |
|---|---|---|---:|---|
| `oe` | Øer | `T.ISL`, `T.ISLS` | 22 | Lolland, Ischia, Capri |
| `bjerg` | Bjerge og høje | `T.MT`, `T.MTS`, `T.HLL`, `T.PK` | 19 | Brocken, Bloksbjerg |
| `forbjerg` | Forbjerge/næs | `T.CAPE`, `T.PROM` | 7 | Kullen, Bastei, Kap Miseno |
| `klippe` | Klipper og klinter | `T.CLF`, `T.RK` | 6 | Stevns Klint, Møns Klint |
| `kloeft_dal` | Kløfter og dale | `T.GRGE`, `T.VAL` | 6 | Ilsedalen, Bodetal |
| `grotte` | Grotter/huler | `S.CAVE` (undtagelse, afsnit G) | 6 | Baumannshöhle, Kuhstall |
| `vulkan` | Vulkaner | `T.VLC` | 4 | Vesuvius, Stromboli |
| `pas` | Bjergpas | `T.PASS` | 2 | Brennerpasset |
| `vandfald` | Vandfald | `H.FLLS*` (undtagelse, afsnit G) | 1 | Grande Cascata di Tivoli |
| `kontinent` | Kontinenter | `L.CONT` | 0 | *(ikke observeret i SV14 — medtaget for STED-REGISTER/fremtidige poster)* |

**Kategori 5 — Bygninger, anlæg og fortidsminder** (139 poster, 6 finkategorier)
— genskaber i praksis den oprindelige 11-kategori-analyse fra afsnit B
inden for denne ene hovedkategori:

| Slug | Navn | GeoNames-koder | Antal (SV14) | Eksempler |
|---|---|---|---:|---|
| `religioes_bygning` | Kirker og andre religiøse bygninger | `S.CH`, `S.MSTY`, `S.MSQE`, `S.TMPL`, `S.CVNT`, `S.HERM` | 38 | Hagia Sophia, Skt. Knuds Kirke |
| `slot_borg` | Slotte, borge, paladser, herregårde | `S.CSTL`, `S.PAL`, `S.EST`, `S.FT` | 26 | Kronborg, Frederiksborg |
| `kulturinstitution` | Teatre, museer, kulturinstitutioner | `S.MUS`, `S.THTR`, `S.OPRA` | 24 | Det Kongelige Teater, La Scala |
| `infrastruktur` | Gader, pladser, broer m.v. | `S.SQR`, `S.BDG`, `S.GATE`, `S.ARCH`, `S.WALLA`, `R.RD`, `R.ST`, `R.TNL` | 22 | Kongens Nytorv, Via di Ripetta |
| `fortidsminde` | Fortidsminder, monumenter, gravsteder | `S.ANS`, `S.MNMT`, `S.RUIN`, `S.CMTY`, `S.GRVE`, `S.AMTH` | 21 | Colosseum, Nonnebakken |
| `bolig_erhverv` | Boliger og erhvervsbygninger | `S.HSE`, `S.FRM`, `S.HTL`, `S.RSRT`, `S.BLDG` | 8 | Hôtel de Bavière |

**Kategori 6 — Parker, haver og naturområder** (12 poster, 4 finkategorier)

| Slug | Navn | GeoNames-koder | Antal (SV14) | Eksempler |
|---|---|---|---:|---|
| `bypark` | Byparker | `L.PRK` | 6 | Tiergarten, Munke-Mose |
| `skov` | Skove (nær bebyggelse) | *(individuel navnegennemgang, ingen dedikeret GeoNames-kode observeret)* | 3 | Hunderup Skov, Næsbyhoved Skov |
| `have` | Haver | `S.GDN` (undtagelse, afsnit G) | 2 | Den Botaniske Have, Villa Comunale |
| `naturreservat` | Naturreservater/fredede områder | `L.RESN`, `L.RES*` | 1 | Liebethaler Grund |

**I alt: 33 finkategorier** fordelt på de 6 hovedkategorier.

### Wikidata-eksempler (finkategori-niveau)

Kun de af brugeren efterspurgte eksempler er verificeret ved live opslag
(jf. CLAUDE.md); fuld verifikation af alle 33 finkategoriers Wikidata-mapping
er et naturligt næste skridt, men ikke udført her.

| Finkategori | Wikidata Q-nummer | Verificeret |
|---|---|---|
| `bjerg` (mountain) | Q8502 | ✓ søgning, krydsbekræftet af Wikidata:WikiProject Mountains |
| `kontinent` (continent) | Q5107 | ✓ søgning |
| `oe` (island) | Q23442 | ✓ søgning (allerede verificeret i afsnit F) |

### Validering mod SV14-registret

Klassificeringsscriptet fra afsnit G blev udvidet med finkategori-opslag og
kørt mod alle 481 poster: **479 af 481 (99,6 %) fik en finkategori.** De
resterende 2 er de samme poster, der allerede er markeret `usikker` på
hovedkategori-niveau (Falleberthor, den fejlkoblede Lilienstein-post) — de
har konsekvent ingen finkategori heller, indtil deres identitet er
afklaret, hvilket er den korrekte adfærd, ikke en fejl.

Under valideringen blev to konsistensfejl fundet og rettet, begge værd at
notere som eksempler på, hvorfor finkategori-laget skal **arve** sine
undtagelser fra hovedkategori-laget og ikke genberegnes uafhængigt af den
rå GeoNames-kode:

1. **Hippodrome of Constantinople** har `@type="S.GDN"`, som ved et rent
   kodeopslag ville give finkategorien `have` (park-gruppen) — men
   hovedkategorien er allerede korrigeret til `anlaeg` i afsnit G (regel 1,
   navngivet enkelttilfælde: hippodromet er et antikt monument, ikke en
   have). En finkategori `have` under hovedkategori `anlaeg` ville være
   selvmodsigende. Rettet til finkategori `fortidsminde`.
2. **Colosseum** (`S.AMTH`, amfiteater) manglede oprindeligt i
   kodeopslagstabellen og ville være faldet ud som "ukategoriseret" —
   tilføjet til `fortidsminde`.

### Anbefaling

Finkategori-laget bør **ikke** implementeres før hovedkategorierne (afsnit
F/G) er formelt godkendt, da laget er meningsløst uden det overordnede
niveau. Når/hvis det godkendes, kan det tilføjes ikke-destruktivt til
`places.xml` i samme arbejdsgang som `@subtype` — de deler samme
klassificeringskilde (GeoNames-koden + de navngivne enkelttilfælde) og kan
udledes i én scriptkørsel.
