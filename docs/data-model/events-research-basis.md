# Begivenheder i HCA Open Repository: sammenfatning og forskningsgrundlag

Status: gemt 2026-10-28 som modtaget fra projektet (udkast, ikke specifikation) ·
datarevisionen (afsnit 4): [`events-data-audit.md`](events-data-audit.md) ·
eksisterende planlagt tabel for entitetsdatoer: [`temporal-modelling.md`](temporal-modelling.md)

> **Proveniens.** Teksten nedenfor er indsat uændret i indhold fra en
> sammenfatning leveret af projektet. Påstande om eksterne projekter og
> standarder (Schnitzler-kronikken, TEI, CIDOC CRM, Wikidata, SKOS, Europeana)
> er **ikke efterprøvet** i denne omgang og skal verificeres ved live opslag
> (jf. `CLAUDE.md`, «Faktakontrol») før de citeres videre. Weblinks fra den
> oprindelige tekst fulgte ikke med og er ikke tilføjet fra hukommelsen.

## 1. Sammenfatning af problemstillingen

Målet er at definere en enkel, men udvidelig datamodel for begivenheder i HCA
Open Repository. Modellen skal kunne håndtere begivenheder knyttet til H.C.
Andersens liv, hans værker og de steder, han opholdt sig, men også historiske
begivenheder i den samtid, der beskrives i tidstavlen.

Begivenheder er dermed en ny entitetstype, som på tværs af registeret kan
forbinde personer, værker, steder og datoer. Den er tæt beslægtet med den
eksisterende datamodel for datoer, men bør ikke reduceres til en dato: En dato
angiver, hvornår noget finder sted; en begivenhed angiver, hvad der finder sted,
og hvordan det relaterer sig til andre entiteter.

### 1.1. Kendte grupper af begivenheder

**A. Begivenheder i et menneskes liv.** Fødsel, død, giftermål, møder med andre
personer og andre biografiske hændelser. Et livsforløb kan modelleres som en
kæde af begivenheder, der knytter sig til en person, ofte på en bestemt dato og
eventuelt et bestemt sted.

**B. Begivenheder i et værks tilblivelse og historie.** Udarbejdelse, revision,
færdiggørelse, udgivelse, anden offentliggørelse og oversættelse. Et værk kan
have flere begivenheder, som finder sted på forskellige tidspunkter og steder og
vedrører forskellige sprog og udgaver.

**C. Rejser og ophold.** En rejse forbinder forskellige steder gennem et forløb
med afrejse, eventuelle mellemstationer og ankomst. Et ophold er derimod en
tilstand over en periode på et bestemt sted. De to fænomener er beslægtede, men
ikke identiske.

**D. Begivenheder i samtiden.** Politiske, kulturelle, videnskabelige og andre
historiske begivenheder, som indgår i tidstavlen, men ikke nødvendigvis vedrører
Andersen direkte. Disse bør kunne administreres uafhængigt af hans biografi og
forbindes med eksterne autoritative kilder.

### 1.2. De grundlæggende konfigurationer

Der er mindst tre grundkonfigurationer, som bør undersøges, frem for på forhånd
at forudsætte én universel begivenhedsstruktur.

| Konfiguration | Eksempel | Centrale egenskaber |
|---|---|---|
| Punktbegivenhed | Andersen fødes; et værk udkommer | En dato eller et dateringsinterval, en begivenhedstype og en eller flere involverede entiteter |
| Periodebegivenhed | Andersen opholder sig i en by; et manuskript udarbejdes over tid | Start og slutning, eventuelt usikre eller ufuldstændige |
| Forløb eller kæde | En rejse gennem Europa; et værks tilblivelse og efterfølgende udgivelser | Flere selvstændige begivenheder, som forbindes gennem eksplicitte relationer |

En vigtig skelnen er, at en rejse eller et værks historie kan repræsenteres som
et forløb uden nødvendigvis at blive én stor begivenhed med alle oplysninger
indlejret i sig. De enkelte hændelser skal fortsat kunne søges, dateres og
forbindes selvstændigt.

### 1.3. Eksempel: værkets udgivelseshistorie

Antag, at *Improvisatoren* udkommer i København på dansk den 2. februar 1835 og i
Leipzig på tysk den 4. maj 1836.

Det er ikke én begivenhed med to datoer. Det er to forskellige
udgivelsesbegivenheder, der begge vedrører samme værk, men har forskellige
datoer, steder, sprog og eventuelt forskellige udgaver eller oversættelser.

Det illustrerer et generelt princip:

* Identiteten af begivenheden afgøres af, hvad der konkret sker.
* Dato, sted, sprog og involverede entiteter beskriver begivenheden.
* Relationer mellem begivenheder beskriver rækkefølge, afhængighed eller
  tilhørsforhold til et større forløb.

Modellen skal desuden kunne skelne mellem en faktisk begivenhed og en hypotese
om, at noget kan være sket på et bestemt tidspunkt eller sted.

> *Note (revisionen, 2026-10-28):* datoerne i dette eksempel er illustrative.
> I de faktiske data er første danske udgivelse 9. april 1835, og den tyske
> oversættelse er dateret «april 1835» — se `events-data-audit.md` §5.

## 2. Forskningsmæssige forbilleder og standarder

Den foreløbige undersøgelse peger på fire relevante spor. De løser forskellige
problemer og bør ikke opfattes som indbyrdes konkurrerende alternativer.

### 2.1. Arthur Schnitzler – Chronik

Österreichische Akademie der Wissenschaften, Wien (den digitale kronik og dens
datakode/kilderepository).

Dette er et særligt relevant forbillede, fordi projektet integrerer materiale
fra flere digitale forskningsprojekter og gør det muligt at undersøge Schnitzlers
liv dag for dag. Ifølge projektets egen beskrivelse indeholder kronikken knap
64.000 dataelementer og sammenkobler blandt andet dagbøger, breve, geografiske
oplysninger og digitale udgaver af værker. Projektet har desuden planlagt at
inddrage udgivelsesdatoer for værker og anmeldelser.

Det er ikke blot en biografisk tidslinje, men en integrationsmodel for
heterogene forskningsdata. Tre elementer er særligt relevante for HCA Open
Repository:

* **Datoen som indgang:** Brugeren kan navigere til en bestemt dag og se
  tilknyttet materiale.
* **Sammenkædning af kilder:** Begivenheder og oplysninger henviser videre til de
  underliggende digitale udgaver og databaser.
* **Adskillelse mellem data og visning:** Projektets data findes i et åbent
  repository og kan leveres i HTML, JSON og XML.

En supplerende ressource er Schnitzlers database over kulturarrangementer. Den
registrerer blandt andet teaterforestillinger, koncerter, biografbesøg, prøver
og oplæsninger samt deltagere, værker, steder og institutioner. Det er et mere
specifikt forbillede for begivenheder, hvor flere entiteter mødes i én konkret
hændelse.

**Vurdering:** Schnitzler-projektet er det bedste umiddelbare operationelle
forbillede. Det viser, hvordan et forskningsprojekt kan integrere
begivenhedsrelaterede data fra flere kilder. Det er dog ikke i sig selv
dokumentation for, at alle de begivenhedstyper, vi har brug for, er modelleret
ensartet. Det kræver en nærmere gennemgang af XML-data og repository-strukturen.

### 2.2. TEI: en enkel struktur for begivenheder

TEI har eksplicit understøttelse af begivenheder gennem elementerne `event` og
`listEvent`.

* `event` beskriver noget identificerbart, der finder sted i tid.
* `listEvent` samler beskrivelser af flere begivenheder.
* Begivenheder kan dateres, typificeres, forsynes med identifikatorer og
  forbindes med andre elementer.
* TEI-eksemplerne viser både historiske begivenheder med start- og slutdatoer og
  hierarkisk indlejring af begivenheder.

TEI er særligt relevant i en forskningskontekst, hvor begivenheder skal kunne
indgå i XML-baserede udgaver og forbindes med personer, steder og værker. Det er
imidlertid en kodningsstandard, ikke i sig selv en komplet begivenhedsontologi
eller en færdig databasemodel.

### 2.3. CIDOC CRM: en referencemodel for kulturarv

CIDOC Conceptual Reference Model (CIDOC CRM, version 7.1.3) er den vigtigste
kandidat, hvis målet er at forankre modellen i en bredt anvendt
kulturarvsstandard. Modellen skelner blandt andet mellem:

* **E4 Period:** et tidsligt afgrænset sammenhængende fænomen eller en historisk periode.
* **E5 Event:** en begivenhed, der kan betragtes som en forandring i et kulturelt, socialt eller fysisk system.
* **E7 Activity:** en aktivitet, der udføres af aktører.
* **E52 Time-Span:** et tidsrum.
* **E53 Place:** et sted.
* **E39 Actor:** en aktør, eksempelvis en person eller organisation.

Den indeholder også relationer, der kan forbinde begivenheder med deltagere og
andre entiteter. Den væsentlige pointe er, at begivenheder ikke behøver at være
defineret alene ved deres dato. De kan modelleres som selvstændige entiteter med
deltagere, sted, tidsrum og forbindelser til andre entiteter.

CIDOC CRM er imidlertid omfattende. Det vil derfor være uhensigtsmæssigt at
implementere hele modellen, før vi har identificeret vores faktiske behov.

### 2.4. Wikidata og SKOS

**Wikidata** skelner mellem entiteter, udsagn, egenskaber og kvalificerende
oplysninger. Modellen understøtter eksempelvis starttid og sluttid som
kvalifikationer til et udsagn. Det er en nyttig inspiration til at koble
begivenheder til datoer og til at genbruge eksterne identifikatorer. Men
Wikidatas fleksible udsagnsmodel bør ikke ukritisk kopieres som en fuld
begivenhedsmodel. Det er nødvendigt at fastlægge en konsistent delmængde af
egenskaber og relationer.

**SKOS** er velegnet til at organisere kontrollerede begrebssystemer, eksempelvis
typer af begivenheder og hierarkier mellem dem. Det er ikke en selvstændig model
for begivenheder med datoer, deltagere og steder. SKOS kan derfor supplere en
begivenhedsmodel, men bør ikke stå alene.

En anden relevant reference er **Europeana Data Model**, som indeholder klassen
`edm:Event` og eksplicit bygger på begreber fra CIDOC CRM.

### Samlet vurdering

| Ressource | Primær anvendelse | Relevans for HCA |
|---|---|---|
| Arthur Schnitzler – Chronik | Integration af biografiske forskningsdata | Meget høj |
| TEI event / listEvent | Kodning af begivenheder i forskningsdata | Høj |
| CIDOC CRM | Semantisk model for begivenheder og relationer | Høj som reference |
| Wikidata | Eksterne identifikatorer og strukturerede udsagn | Høj som supplement |
| SKOS | Kontrollerede begrebssystemer | Høj til klassifikation |
| Europeana Data Model | Udveksling af kulturarvsdata | Relevant ved senere interoperabilitet |

Den foreløbige anbefaling er at undersøge en enkel lokal model med eksplicitte
relationer, informeret af TEI og en begrænset, kompatibel delmængde af CIDOC CRM.
SKOS kan bruges til at organisere begivenhedstyper, mens Wikidata kan fungere som
ekstern kilde til generelle historiske begivenheder.

## 3. Hjælpespørgsmål til at identificere og afgrænse begivenheder

Før den endelige model fastlægges, bør vi opstille et sæt spørgsmål, som både kan
bruges til at klassificere eksisterende data og til at afgøre, hvornår to
oplysninger skal repræsenteres som én eller flere begivenheder.

### 3.1. Er der tale om én begivenhed eller flere?

1. **Beskriver oplysningerne én konkret hændelse?** Eksempel: Et værk udkommer på
   dansk i København og senere på tysk i Leipzig. Hvis der er tale om forskellige
   udgivelseshandlinger, skal de som udgangspunkt registreres som to begivenheder.
2. **Er datoerne forskellige, fordi begivenheden varer ved, eller fordi der sker
   flere ting?** Eksempel: Andersen opholder sig i en by i tre måneder. Det taler
   for én periodebegivenhed. Afrejse, ankomst og eventuelle mellemliggende
   hændelser kan samtidig registreres særskilt.
3. **Er der tale om en overordnet begivenhed med underbegivenheder?** Eksempel: En
   rejse gennem Europa består af flere ophold og transportetaper. Et overordnet
   rejseforløb kan forbindes med de enkelte hændelser uden at erstatte dem.
4. **Er der tale om en begivenhed eller blot en tidslig egenskab?** Eksempel: Et
   værk har en udgivelsesdato, men ikke alle værker har en dokumenteret særskilt
   begivenhed for hver fase af deres tilblivelse. Modellen bør kunne repræsentere
   både en simpel dateret oplysning og en fuldt beskrevet begivenhed, men vi skal
   beslutte, hvornår en dato alene er tilstrækkelig.

### 3.2. Hvilke oplysninger skal kunne knyttes til en begivenhed?

| Dimension | Afklarende spørgsmål |
|---|---|
| Identitet | Hvad er det konkret, der sker? |
| Type | Er det en fødsel, udgivelse, oversættelse, rejse, et ophold, et møde eller noget andet? |
| Tid | Er begivenheden knyttet til en bestemt dato, et interval eller et usikkert tidspunkt? |
| Sted | Finder den sted ét sted, flere steder eller på en rute? |
| Personer | Hvem deltager, og i hvilken rolle? |
| Værker | Hvilket værk eller hvilken udgave vedrører begivenheden? |
| Relationer | Er begivenheden en del af et større forløb eller knyttet til andre begivenheder? |
| Kilder | Hvorfra stammer oplysningen, og hvor sikker er dateringen? |
| Eksterne identifikatorer | Findes begivenheden allerede i Wikidata eller et andet autoritativt register? |

Ikke alle felter skal være obligatoriske. Modellen bør kunne håndtere historiske
oplysninger, hvor eksempelvis dato, sted eller deltagere er ukendte.

## 4. Hvad skal undersøges i de eksisterende data?

Den nuværende beskrivelse identificerer fire datagrupper, men vi har endnu ikke
gennemgået de konkrete datasæt og deres felter. Det er derfor for tidligt at
konkludere, at de beskrevne konfigurationer dækker alle faktiske tilfælde.

1. **Biografiske data:** De eksisterende, relativt strukturerede oplysninger om
   begivenheder i Andersens liv. Hvilke typer forekommer faktisk, og hvordan
   repræsenteres datoer, personer og steder?
2. **Værkdata:** Udgivelser, oversættelser og oplysninger om manuskripternes
   tilblivelse. Skel mellem værket som abstrakt entitet, konkrete udgaver og de
   begivenheder, der forbinder dem.
3. **Steddata:** Rejser og ophold, herunder oplysninger med start- og slutdatoer,
   flere destinationer eller kun en upræcis datering.
4. **Tidstavlen:** Generelle historiske begivenheder, som ikke nødvendigvis
   vedrører Andersen. Hvilke oplysninger kan kobles til eksterne kilder, og hvilke
   kræver en selvstændig lokal beskrivelse?

For hvert datasæt bør resultatet være en oversigt over faktiske felter,
eksempler på registreringer, manglende oplysninger og identificerede undtagelser.

## 5. Foreløbig arkitektur for datamodellen

Et muligt udgangspunkt er at skelne mellem begivenheden, dens tidslige placering,
dens deltagere og dens relationer til andre entiteter.

| Del | Indhold |
|---|---|
| Begivenhed | ID · betegnelse · type · beskrivelse · kilde |
| Dato / tidsrum | Punkt, interval eller usikker datering |
| Sted | Ét eller flere steder |
| Personer | Deltagere og roller |
| Relationer | Værker, andre begivenheder og forløb |

Dette er en konceptuel skitse, ikke en endelig specifikation. Den skal især
afprøves mod udgivelsesbegivenheder, ophold og rejser, hvor en enkel begivenhed
med én dato og ét sted ikke er tilstrækkelig.

Et centralt designvalg er, at en begivenhed skal kunne have relationer til flere
entitetstyper uden at blive defineret som en undertype af person, sted eller
værk. Det gør det muligt at tilføje nye begivenhedstyper senere uden at ændre
hele registerets grundstruktur.

## 6. Foreslået arbejdsrækkefølge

1. **Kortlæg eksisterende data.** Dokumentér felter, registreringsformer og
   konkrete eksempler fra de fire datagrupper. *(Udført som første pas: se
   `events-data-audit.md`.)*
2. **Undersøg Schnitzler-projektets datamodel.** Gennemgå TEI-filerne, især brugen
   af `event`, `listEvent`, datering, identifikatorer og relationer. Sammenhold
   kronikken med databasen over kulturarrangementer. *(Ikke påbegyndt.)*
3. **Sammenlign med standarderne.** Identificér en begrænset delmængde af TEI og
   CIDOC CRM, der dækker de faktiske behov. Vurdér SKOS til klassifikation og
   Wikidata til eksterne forbindelser. *(Ikke påbegyndt.)*
4. **Afprøv modellen på repræsentative eksempler.** Medtag mindst en biografisk
   hændelse, et længere ophold, en rejse, en manuskriptfase, en udgivelse i flere
   lande og en generel historisk begivenhed. *(Eksemplerne er udvalgt af de
   faktiske data: se `events-data-audit.md` §5.)*
5. **Skriv specifikationen.** Beskriv felter, kardinaliteter, dateringsregler,
   relationer, usikkerhed, kildeangivelser og regler for at afgøre, om oplysninger
   repræsenterer samme begivenhed.

Det vigtigste næste skridt er datarevisionen. Forskningsstandarderne giver et
kvalificeret udgangspunkt, men den endelige model skal bestemmes af de faktiske
registreringer og de forespørgsler, som registeret skal understøtte.
Schnitzler-projektet er det mest direkte forbillede for integrationsarbejdet,
mens CIDOC CRM og TEI giver de stærkeste kandidater til henholdsvis begrebsmodel
og konkret kodning.
