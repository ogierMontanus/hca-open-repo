# Stedtypologi for SV-udgavens stedregister — forslag til godkendelse

> **Status: UDKAST — afventer faglig/redaktionel godkendelse.**
> Dette dokument dækker Trin 1–4 af opgaven "Klassifikation af stednavne i
> H.C. Andersens stedregister": grundlag, kategoriforslag, test mod
> registret og en foreløbig endelig liste. Trin 5 (GeoNames-mapping)
> er bevidst **ikke** udført endnu — det kræver først godkendelse af
> kategorilisten i afsnit D.

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
Classes/Codes) igangsættes først, når denne liste er godkendt.**
