# Stedtypologi-klassifikation: Prompt til copilot/bot

**Opgave:** Klassificer 80 steder fra H.C. Andersens stedregister efter den endelige 6-kategori-taxonomi. Hver klassifikation skal være forsvarlig og utvetydig, eller eksplicit markeret som "usikker".

---

## De 6 kategorier — definitioner og afgrænsninger

### 1. BEBYGGEDE OMRÅDER
**Definition:** Bebyggede steder hvor mennesker bor og arbejder — fra hovedstæder til små landsbyer og bydele.

**Inkluderer:**
- Storbyer (Rom, Berlin, Athen, København)
- Små byer og landsbyer (Lübeck, Firenze, Sorø)
- Bydele og forstæder (Wandsbek, Beyoğlu, Üsküdar)
- Tysktalende "Gemeinde"-poster koderet som administrativ status (ADM3–ADM5 i GeoNames), som reelt fungerer som småbyer i teksten

**Ekskluderer:**
- Større administrativ-/landskabsregioner uden et enkelt bebygget centrum (→ Kategori 2)
- Øer som selvstændig titel (→ Kategori 4)

**Nøglespørgsmål:** *Har stedet et navn, der fungerer som betegnelse for et bebygget sted, hvor mennesker bor?*

**Eksempler fra SV14:**
- ✓ Odense (hovedbyen i Andersens barndom)
- ✓ København (hovedstad)
- ✓ Rom, Firenze, Athen (italienske og græske hovedbyer)
- ✓ Lübeck, Hamburg (tyske handelsbyer)
- ✓ Thale (lille by i Harzen)
- ✓ Constantza (by ved Sortehavet)

**Grænsetilfælde — vejledning:**
- **Theresienstadt:** Både by og befæstet fæstningsanlæg. Klassificer som BEBYGGET OMRÅDE, fordi dens primære karakter i HCA-teksten er stednavnet på en by, ikke på militærværket.
- **Reichenbach:** Både småby og navn på en vandfald (Reichenbachtal-faldet i Gotthard-området). Hvis notekort henviser til vandfaldet som "the Reichenbach falls", markér som **USIKKER**, ellers som BEBYGGET.
- **Elben:** Selv hvis omtalt som både by og flod, klassificer efter kontekst — hvis det er "vi ankom til Elben" (floden), er det VANDOMRÅDE; hvis det er stednavnet på en by ved elben, er det BEBYGGET.

---

### 2. LANDE, ADMINISTRATIVE ENHEDER OG REGIONER
**Definition:** Suveræne stater, stater inden for føderatív struktur, administrative provinser/områder, samt større landskabsregioner uden et enkelt bebygget centrum som referencepunkt.

**Inkluderer:**
- Stater: Kongeriget Danmark, Den Italienske Republik, Det Osmanniske Rige
- Administrative provinser: Napoli (provins), Tyrol, Wallakiet
- Større landskabsregioner (naturgeografiske, ikke administrativt afgrænsede): Peloponnes, Akarnianien, Lüneburger Heide, Leipziger Tieflandsbucht
- Dele af større regioner, når de optræder som selvstændig stedtype: Scotland, Wales, provence (fransk region)

**Ekskluderer:**
- Små småbyer, selv hvis de er administrativt kodet som kommuner (→ Kategori 1)
- Øer (→ Kategori 4)
- Bjerge og naturlige landskabsformer uden menneskelig-politisk afgrænsning (→ Kategori 4)

**Nøglespørgsmål:** *Er stedet et større territorium med eller uden administrativ grænser, eller en naturgeografisk region uden et enkelt bebygget centrum?*

**Eksempler fra SV14:**
- ✓ Kongeriget Danmark
- ✓ Kongeriget Sverige
- ✓ Tyrol (landskabsregion i Alper)
- ✓ Wallakiet (tidligere fyrstedømme/region i Rumænien)
- ✓ Peloponnes (halvø i Grækenland, naturgeografisk enhed)
- ✓ Napoli (italiensk provins)

**Grænsetilfælde — vejledning:**
- **Slesvig-Holsten:** Region der spænder fra Danmark til Tyskland. Klassificer som REGION/LANDSDEL.
- **Lüneburger Heide/Leipziger Tieflandsbucht:** Disse er naturgeografiske landskaber (hede, lavland), ikke administrativt afgrænsede, men GeoNames koder dem som L.RGN. Klassificer som REGION — de er større naturgeografiske enheder.
- **Tyskland/Østrig/Italien som helhed:** Hvis omtalt som lande, klassificer som LAND.

---

### 3. VANDOMRÅDER
**Definition:** Alle former for naturligt eller menneskeskabt vand i alle størrelser — floder, åer, søer, hav, stræder, bugter, kanaler.

**Inkluderer:**
- Floder og åer: Elbe, Tiberen, Donau, danske smååer
- Søer: Comersøen, Genfer Sø
- Have: Atlanterhavet, Middelhavsmidtene
- Stræder, sunde, canaler: Sundet, Bosporus, Dardanellerne, Øresund, Kielerkanalen
- Havne når de benævnes som naturlige basiner: Grand Harbour (Valletta)

**Ekskluderer:**
- Byer ved vand (→ Kategori 1)
- Øer (→ Kategori 4)

**Nøglespørgsmål:** *Er stedet vand eller har ordet hovedsagelig vandordet som betydning?*

**Eksempler fra SV14:**
- ✓ Elbe (floden)
- ✓ Tiberen (Romens flod)
- ✓ Sundet (farvandet mellem Danmark og Sverige)
- ✓ Bosporus (strædet)
- ✓ Genfer Sø
- ✓ Sortehavet

**Grænsetilfælde — vejledning:**
- **Venedig/Venetien:** Venedig er en by (→ BEBYGGET), Veneto er en region (→ REGION). Hvis teksten siger "jeg sejlede ind i Venedig", klassificer stedet som BEBYGGET efter kontekst.
- **Kielerkanalen:** En menneskeskabt kanal. Klassificer som VANDOMRÅDE.
- **Nilen som landgrænse:** Hvis Nilen omtales som "grænsefloden", klassificer stadig som VANDOMRÅDE, ikke som REGION.

---

### 4. LANDSKABSFORMER OG NATURFÆNOMENER (inkl. øer)
**Definition:** Naturligt dannede terrænformer, geologiske fænomener og øer uden menneskeligt boligfokus. Inkluderer bjerge, høje, klipper, kløfter, grotter, forbjerge, vulkaner, bjergpas og øer i alle størrelser.

**Inkluderer:**
- Bjerge og høje: Vesuvius, Rigi, Harz (bjergkæde)
- Klipper, kløfter, grotter: Stevns Klint, Baumannshöhle (Duitse grotte), Brenner-passet
- Øer: Sicilien, Malta, Ischia, Mykonos, Lolland (selvom nogle har byer på dem — klassificer efter øens navn, ikke byens)
- Forbjerge: Kap Matapan
- Geologiske fænomener: Vesuvius (vulkan), Stromboli (vulkanø)

**Ekskluderer:**
- Bebyggede byer på øer, når øen ikke er det centrale tema (→ Kategori 1)
- Administrative regioner (→ Kategori 2)
- Vandområder (→ Kategori 3)

**Nøglespørgsmål:** *Er stedet en naturlig terrænform, geologisk fænomen eller ø?*

**Eksempler fra SV14:**
- ✓ Vesuvius (vulkan)
- ✓ Sicilien (ø)
- ✓ Malta (ø)
- ✓ Rigi (bjerg i Schweiz)
- ✓ Brenner-passet (bjergpas)
- ✓ Mykonos (græsk ø)

**Grænsetilfælde — vejledning:**
- **Acropolis:** Hvis "Acropolis" henviser til selve klippehøjen (terrænnet), klassificer som LANDSKABSFORM. Hvis det henviser til bygningsværkerne ovenpå (Parthenon etc.), klassificer som BYGNING.
- **Øer med større byer:** Sicilien har Palermo, Malta har Valletta. Klassificer øen selv som LANDSKABSFORM, ikke efter byen.
- **Forbjerge:** Naturgeografiske fremspring. Klassificer som LANDSKABSFORM.

---

### 5. BYGNINGER, ANLÆG OG FORTIDSMINDER
**Definition:** Menneskeskabte bygningsværker, anlæg og monumenter fra alle perioder — religiøse bygninger, slot/borge, teatre/museer, fortidsminder, ruiner, gader, pladser, broer.

**Inkluderer:**
- Religiøse bygninger: Hagia Sophia, Sankt Knuds Kirke, Peterskirken, Sultan Ahmed-moskeen
- Slot/borge/paladser/herregårde: Kronborg, Frederiksborg, Sanssouci, Topkapı-paladset, Nysø
- Teatre/operahuse/museer: Det Kongelige Teater, La Scala, Teatro di San Carlo, Konzerthaus Berlin
- Fortidsminder/monumenter/gravsteder: Colosseum, Pompeji, Parthenon (bygningsværket), Forum Romanum, Vendômesøjlen
- Ruiner (når hensigten klart var en tidligere bygning): Burg Regenstein (borgruin)
- Gader/pladser/broer: Kongens Nytorv, Piazza del Popolo, Via del Corso, Brandenburger Tor, Lübeck Rådhus

**Ekskluderer:**
- Parker og grønne områder (→ Kategori 6)
- Bebyggede områder (byer) (→ Kategori 1)
- Naturlige landskabsformer (→ Kategori 4)

**Nøglespørgsmål:** *Er stedet et menneskeskabt bygningsværk, anlæg eller monument?*

**Eksempler fra SV14:**
- ✓ Hagia Sophia (kirke)
- ✓ Kronborg Slot
- ✓ Colosseum (antikt amfiteater, nu ruin)
- ✓ Peterskirken (kirke i Rom)
- ✓ Teatro di San Carlo (operahus)
- ✓ Parthenon (antikt tempel)

**Grænsetilfælde — vejledning:**
- **Theresienstadt som fæstning:** Hvis fokus ligger på fæstningsværkerne (S.CSTL i GeoNames), klassificer som BYGNING.
- **Colosseum:** Selv om det i dag er ruin, var det oprindeligt en fungerende arena. Klassificer som BYGNING/FORTIDSMINDE.
- **Grotta di Pozzuoli:** En antik romersk tunnel (menneskeskabt, ikke naturgrotte). Grænsetilfælde mellem LANDSKABSFORM (grotte som naturligt fænomen) og BYGNING (menneskeskabt anlæg). Klassificer som BYGNING, fordi det er Romertiden-konstruktion.
- **Kız Kulesi (Pigetrnet):** Et tårn i Bosporus — menneskeskabt mindesmærke. Klassificer som BYGNING/MINDESMÆRKE, ikke som naturlig terrænform.
- **Hoteller og værtsshuse:** Klassificer som BYGNING (gader/pladser/anden infrastruktur).

---

### 6. PARKER, HAVER OG NATUROMRÅDER
**Definition:** Menneskeligt anlagte eller fredede grønne områder beregnet til rekreation — byparker, slotshaver, skove nær bebyggelse, botaniske haver.

**Inkluderer:**
- Byparker: Tiergarten (Berlin), Volksgarten (Wien)
- Slotshaver: Villa Borghese (Rom)
- Skove og naturområder nær bebyggelse: Hunderup Skov, Næsbyhoved Skov (begge nær Odense)
- Botaniske haver: Den Botaniske Have (Odense)
- Naturbeskyttelsesarealer/fredede områder

**Ekskluderer:**
- Vildmark og ubeboet natur uden menneskelig anlagsstatus (→ Kategori 4)
- Byer og deres græsplæner generelt (→ Kategori 1)
- Terræn og naturlige bakker selv om inden for bygrænser (→ Kategori 4)

**Nøglespørgsmål:** *Er stedet en menneskeligt anlagt eller fredningsbestemt grøn område?*

**Eksempler fra SV14:**
- ✓ Tiergarten (Berlin — bypark)
- ✓ Villa Borghese (Rom — slot-park)
- ✓ Den Botaniske Have (Odense)
- ✓ Hunderup Skov (skov ved Odense)

**Grænsetilfælde — vejledning:**
- **Villanavn som også er et parknavn (Villa Borghese):** Klassificer som PARK, fordi navnet primært henviser til haven/parkanlægget.
- **Tivoli (København):** Når det omtales som forlystelsespark/have, klassificer som PARK.
- **Vildt skovsterræn uden menneskelig bearbejdning:** Klassificer som LANDSKABSFORM, ikke PARK.

---

## Klassifikationsprocedure

### Trin 1: Læs stednavnet
Notér stednavnet helt som det fremgår af registret.

### Trin 2: Identificer kontekst
Hvis der er en noteord eller marked reference (fx "GeoNames-kode: P.PPL", "en italiensk ø", "elven der…"), læs den.

### Trin 3: Anvend afgrænsningsregler
Gå gennem kategorierne 1–6 og spørg: "Hvilken kategori passer bedst?" Brug nøglespørgsmålene ovenfor.

### Trin 4: Håndter grænsetilfælde
Hvis stedet kunne høre hjemme i to kategorier:
- Prioriter efter stedets **funktion i teksten** — hvad er det vigtigste træk?
- Hvis det stadig er tvetydigt, markér som **USIKKER** og noteér årsagen (fx "både by og fæstning").

### Trin 5: Dokumentér klassifikationen
For hvert sted, skriv:
```
[Stednavn] → KATEGORI NUMMER/NAVN
Begrundelse: [kort forklaring eller "grænsetilfælde - [grund]"]
```

---

## Håndtering af usikkerhed

**Markér som USIKKER hvis:**
1. Stedets identitet er uafklaret eller omstridt (fx "Falleberthor — ukendt")
2. Stednavnet kunne passe mindst to kategorier, og teksten er ambig
3. GeoNames eller andre kilder er modstridende
4. Du ganske enkelt ikke kan afgøre det ud fra navn + kontekst

**Format for usikre klassifikationer:**
```
[Stednavn] → USIKKER
Grund: [forklaring]
Mulige kategorier: [liste]
```

**Eksempel:**
```
Reichenbach → USIKKER
Grund: Kan være både småby i Østrig og vandfald i Gotthardmassiv
Mulige kategorier: BEBYGGET OMRÅDE, LANDSKABSFORM
```

---

## De 80 steder til klassificering

| Nr | Stednavn | Noter / GeoNames-type | Din klassifikation | Begrundelse |
|:---:|---|---|---|---|
| 1 | Odense | Dansk by, barndomsted | | |
| 2 | København | Danmark, hovedstad | | |
| 3 | Aarhus | Dansk by | | |
| 4 | Elsinore (Helsingør) | Dansk by, Kronborg | | |
| 5 | Sorø | Dansk by | | |
| 6 | Ribe | Dansk by, middelalderbiskopssæde | | |
| 7 | Aalborg | Dansk by | | |
| 8 | Randers | Dansk by | | |
| 9 | Lolland | Dansk ø | | |
| 10 | Bornholm | Dansk ø | | |
| 11 | Kongeriget Danmark | Land | | |
| 12 | Kongeriget Sverige | Land | | |
| 13 | Kongeriget Norge | Land | | |
| 14 | Italien | Land, italiensk republik | | |
| 15 | Tyskland | Land, tysk forbund/rige | | |
| 16 | Schweiz | Land | | |
| 17 | Østrig | Land | | |
| 18 | Grækenland | Land | | |
| 19 | Det Osmanniske Rige | Politisk enhed | | |
| 20 | Rusland | Land | | |
| 21 | Bosnien | Region / provins | | |
| 22 | Wallakiet | Fyrstedømme, later rumænsk region | | |
| 23 | Moldavien | Historisk fyrstedømme, rumænsk region | | |
| 24 | Tyrol | Landskabsregion, Øvre Donau | | |
| 25 | Peloponnes | Græsk halvø / naturgeografisk enhed | | |
| 26 | Akarnianien | Græsk region, antik | | |
| 27 | Slesvig-Holsten | Tysk-dansk region, kulturlandskab | | |
| 28 | Sachsen (Saxony) | Tysk region / provins | | |
| 29 | Preussen | Tysk rige, provins | | |
| 30 | Bayern | Tysk region / kongerige | | |
| 31 | Württemberg | Tysk region | | |
| 32 | Napoli (provincie) | Italiensk provins | | |
| 33 | Lüneburger Heide | Naturgeografisk landskab (hedeslette) | | |
| 34 | Leipziger Tieflandsbucht | Naturgeografisk landskab (lavland) | | |
| 35 | Rom | Italiensk by, hovedstad | | |
| 36 | Firenze | Italiensk by | | |
| 37 | Venedig | Italiensk by, på vand | | |
| 38 | Napoli (by) | Italiensk by | | |
| 39 | Palermo | Italiensk by, på Sicilien | | |
| 40 | Milano | Italiensk by | | |
| 41 | Verona | Italiensk by | | |
| 42 | Genova | Italiensk by, havn | | |
| 43 | Bologna | Italiensk by | | |
| 44 | Ravenna | Italiensk by | | |
| 45 | Perugia | Italiensk by | | |
| 46 | Assisi | Italiensk by | | |
| 47 | Siena | Italiensk by | | |
| 48 | Pisa | Italiensk by | | |
| 49 | Lucca | Italiensk by | | |
| 50 | Berlin | Tysk by, hovedstad | | |
| 51 | Hamburg | Tysk by, havn | | |
| 52 | München | Tysk by, Bavaria | | |
| 53 | Dresden | Tysk by, Sachsen | | |
| 54 | Leipzig | Tysk by, Sachsen | | |
| 55 | Weimar | Tysk by, kulturby | | |
| 56 | Lübeck | Tysk by, Hansastad | | |
| 57 | Kiel | Tysk by, fjord | | |
| 58 | Kölner | Tysk by | | |
| 59 | Frankfurt | Tysk by | | |
| 60 | Stuttgart | Tysk by, Württemberg | | |
| 61 | Athen | Græsk by, hovedstad | | |
| 62 | Korinth | Græsk by, antik | | |
| 63 | Sparta | Græsk by, antik | | |
| 64 | Mykene | Græsk city, antik | | |
| 65 | Delphi | Græsk tempel-sted, antik | | |
| 66 | Constantinopel (Istanbul) | Tyrkisk by, tidligere græsk | | |
| 67 | Smyrne (Izmir) | Tyrkisk by, tidligere græsk | | |
| 68 | Galata | Bydel i Istanbul | | |
| 69 | Sicilien | Italiensk ø | | |
| 70 | Malta | Ø i Middelhavet | | |
| 71 | Ischia | Italiensk ø | | |
| 72 | Capri | Italiensk ø | | |
| 73 | Mykonos | Græsk ø, Kykladerne | | |
| 74 | Delos | Græsk ø, antik, Kykladerne | | |
| 75 | Vesuvius | Vulkan ved Napoli | | |
| 76 | Etna | Vulkan på Sicilien | | |
| 77 | Rigi | Schweizisk bjerg | | |
| 78 | Brenner-passet | Alpepas mellem Østerrig og Italien | | |
| 79 | Elbe (floden) | Europæisk flod, Deutsch-dansk | | |
| 80 | Donau | Europæisk flod, gennem flere lande | | |

---

## Vigtige noter til klassifikatoren

1. **Stil dig kritisk over for egennavne uden stedord-LED:** Ordet "Schönbrunn" eller "Pilatus" ville ikke blive fanget af en simpel "palads/bjerg"-mønster-scan. Du skal bruge dit kendskab til stederne.

2. **Historisk stavemåde:** Hvis stedet skrives som "Storaaen" (med aa i stedet for å), anerkendes det som samme sted som "Storaen", selvom navnemønsteret ikke matcher. Klassificer efter den rigtige moderne stavemåde.

3. **Når GeoNames og navn uenige:** Hvis GeoNames siger et sted er en "region", men stednavnet klart indikerer en by, prioritér stednavnet + kontekst over GeoNames-koden.

4. **Grænsetilfælde uden usikkerhed:** Hvis du kan begrunde det klart (fx "Theresienstadt er klassificeret som BEBYGGET OMRÅDE, fordi HCA-teksten omtaler det som bysted"), undgår du at sige "usikker". Usikkerhed skal være det sidste valg.

5. **Nedskriv begrundelsen:** Hver klassifikation skal kunne forsvares kort — ét til to sætninger. Ikke en roman, men nok til at vise dit ræsonnement.

---

## Template til dit output

Når du har klassificeret alle 80 steder, skriv resultaterne i denne format:

```markdown
# Klassifikationsresultater: 80 SV-steder

| Nr | Stednavn | Kategori | Begrundelse |
|:---:|---|---|---|
| 1 | Odense | 1 BEBYGGET OMRÅDE | Andersens barndomsby, hvor mennesker bor |
| 2 | København | 1 BEBYGGET OMRÅDE | Danmarks hovedstad, bebygget område |
...
```

**Sammenfatning:**
- Kategori 1 (Bebyggede områder): [antal]
- Kategori 2 (Lande/administrative enheder/regioner): [antal]
- Kategori 3 (Vandområder): [antal]
- Kategori 4 (Landskabsformer/naturfænomener): [antal]
- Kategori 5 (Bygninger/anlæg/fortidsminder): [antal]
- Kategori 6 (Parker/haver/naturområder): [antal]
- USIKRE: [antal]

**Validering:** Det samlede antal usikre klassifikationer bør være under 5 % (i.e., færre end 4 ud af 80), da du arbejder ud fra navn + eventuel kontekst, ikke blind navnemønster-gætteri.
```

