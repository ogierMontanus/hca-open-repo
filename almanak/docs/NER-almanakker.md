# Opgave: Digitalisering af almanakken – analyse af datakilder og genbrug af eksisterende pipeline

## 1. Baggrund og overordnet mål

Vi skal digitalisere en almanak, som er beslægtet med det allerede digitaliserede dagbogsmateriale. Almanakken har en grundlæggende struktur, der minder om dagbøgernes, men er et selvstændigt dokument med sit eget indhold og sine egne registreringsbehov.

Arbejdet skal foregå i det eksisterende repository, som indeholder materialer, data, Python-scripts, Markdown-dokumentation og pipelines udviklet til digitaliseringen af dagbogsregistrene.

Opret en særskilt mappe til almanakprojektet i repositoryet. Almanakkens data og projektspecifikke arbejdsgange skal holdes adskilt fra dagbogsprojektets eksisterende data, samtidig med at fælles funktionalitet genbruges.

**Den overordnede opgave er at undersøge de eksisterende datakilder, vælge det bedste grundlag for digitaliseringen og derefter udarbejde en plan for at genbruge og tilpasse de eksisterende pipelines.**

## 2. De to datakilder

Arbejdet tager udgangspunkt i to kilder:

**A. Den eksisterende database**
- den ligger i sharepoint: mappe sql/hca_db.sql.
- Tabellen "almanak" indeholder almanakrelaterede data i en større database.
- De enkelte dage udgør den grundlæggende strukturelle enhed.
- Undersøg, hvordan almanakkens afsnit og underafsnit er repræsenteret i databasen.
- Undersøg databasens struktur, felter, metadata, hierarkier og eventuelle relationer til andre data.
- Antag ikke, at databasen har de samme indholdsregistre, metadata eller redaktionelle funktioner som den trykte kilde.

**B. PDF-kilden**
- Indeholder en digital gengivelse af den trykte almanak.
- Siden er den grundlæggende visuelle enhed, mens tekst og indhold kan være organiseret i mindre afsnit.
- Undersøg PDF'ens faktiske struktur, tekstlag, sideinddeling og eventuelle problemer med OCR eller tekstudtræk.
- Brug PDF'en som kilde til at kontrollere databasens indhold og struktur.

Identificér først de konkrete filer, tabeller, databaser og relevante afsnit. Dokumentér, hvad der faktisk findes, før du drager konklusioner om kildernes kvalitet.

## 3. Sammenlign repræsentative afsnit

Udvælg et begrænset, men repræsentativt udsnit af almanakken. Udsnittet skal gøre det muligt at sammenligne de to kilder på samme indhold.

Sammenlign de tilsvarende afsnit i databasen og PDF'en. Foretag sammenligningen på flere parametre:

1. **Tekstlig fuldstændighed:** Er alt indhold medtaget, eller mangler der ord, sætninger, afsnit eller hele poster?
2. **Tekstlig korrekthed:** Er stavning, tegnsætning, tal, datoer, navne og øvrige tekstdata gengivet korrekt?
3. **Strukturel korrekthed:** Er dage, afsnit, underafsnit og deres indbyrdes hierarki repræsenteret korrekt?
4. **Registreringsdybde:** Hvilke oplysninger er eksplicit registreret i databasen, og hvilke findes kun i PDF'en?
5. **Søgbarhed og genanvendelighed:** Hvilke oplysninger er strukturerede og direkte maskinelt bearbejdelige?
6. **Kildekontrol:** Kan databaseposterne entydigt forbindes med den relevante side, dag eller det relevante afsnit i PDF'en?
7. **Fejl og usikkerhed:** Hvilke fejl, uoverensstemmelser og tvetydigheder findes der i hver kilde?

Registrér konkrete eksempler på både styrker og svagheder. Skeln mellem dokumenterede fejl, manglende data, strukturelle forskelle og tilfælde, hvor det ikke er muligt at afgøre, hvilken gengivelse der er korrekt.

Undersøg, om databasens struktur kan sammenholdes med PDF'en på tværs af flere dage og afsnit. Undgå at basere konklusionerne på et enkelt eksempel.

## 4. Vurdering og valg af datagrundlag

Udarbejd en sammenlignende vurdering af de to kilder.

For hvert relevant parameter skal det fremgå:
- hvilken kilde der er bedst;
- hvilke konkrete observationer vurderingen bygger på;
- om vurderingen gælder hele materialet eller kun det undersøgte udsnit;
- hvilke forbehold der er nødvendige.

Vurder derefter, hvilken kilde der bør være grundlaget for den videre digitalisering.

Det er ikke givet på forhånd, at én kilde er bedst på alle områder. Det kan eksempelvis vise sig, at databasen er bedst til strukturerede data, mens PDF'en er nødvendig for at kontrollere tekstens fuldstændighed eller den oprindelige opbygning.

Overvej derfor mindst følgende muligheder:

- Databasen anvendes som grundlag, og PDF'en bruges til kontrol og supplering.
- PDF'en anvendes som grundlag, og relevante strukturerede data overføres fra databasen.
- Der etableres en kombineret tredje version, som samler de bedste egenskaber fra begge kilder.

**Anbefal én løsning på grundlag af analysen.** Hvis datagrundlaget er utilstrækkeligt til et sikkert valg, skal det fremgå, hvilke yderligere undersøgelser der er nødvendige.

## 5. Etablering af en forbedret tredje version

Undersøg særligt behovet for at kombinere de to kilder i en forbedret tredje version.

En sådan version kan være nødvendig, hvis databasen eksempelvis mangler indholdsregistre, mens PDF'en indeholder information, der ikke er struktureret i databasen.

Hvis en kombineret version anbefales, skal du udarbejde en konkret model for sammenføringen:

- Definér den grundlæggende dataenhed, eksempelvis dag, side, afsnit eller post.
- Fastlæg, hvordan poster fra databasen matches med tekst og struktur i PDF'en.
- Undersøg, hvilke felter der skal bevares fra hver kilde.
- Beskriv, hvordan manglende oplysninger tilføjes uden at overskrive eksisterende data ukritisk.
- Bevar sporbarhed til begge kilder.
- Registrér konflikter, usikkerhed og redaktionelle beslutninger.
- Undgå at fremstille maskinelle sammenføringer som sikre, hvis matchningen er tvetydig.
- Udarbejd regler for validering og kontrol af det sammenførte resultat.

Den forbedrede version skal kunne reproduceres fra kilderne og dokumenterede transformationsregler. Originaldata må ikke ændres destruktivt.

## 6. Undersøg repositoryets eksisterende pipelines

Når datagrundlaget er vurderet, skal du undersøge, hvordan digitaliseringen af almanakken bedst kan bygge videre på det eksisterende arbejde.

Gennemgå repositoryets relevante:
- Python-scripts;
- Markdown-dokumentation;
- dataformater og mappestrukturer;
- validerings- og kontrolrutiner;
- preprocessing og datarensning;
- segmentering og sammenstilling;
- øvrige pipeline-trin, som er relevante for den planlagte digitalisering.

Brug repositoryets eksisterende dokumentation og implementering som udgangspunkt. Undersøg både, hvad scripts faktisk gør, og hvad dokumentationen siger, at de gør.

Klassificér de relevante komponenter som:

1. Kan genbruges uændret.
2. Kan genbruges med konfiguration eller mindre tilpasninger.
3. Kræver en særskilt almanakimplementering.
4. Er ikke relevante for almanakken.

Antag ikke, at hele dagbogspipelinen kan genbruges direkte. Identificér de konkrete afhængigheder af dagbogsregistrenes struktur, filformater, feltnavne og særlige redaktionelle konventioner.

Undgå samtidig at genimplementere eksisterende funktionalitet, blot fordi almanakken er et nyt delprojekt.

## 7. Organisering af almanakprojektet

Opret en dedikeret mappe til almanakken i repositoryet, når du har undersøgt den eksisterende mappestruktur og fastlagt en hensigtsmæssig placering.

Mappen skal rumme almanakspecifikke dokumenter, konfigurationer, scripts og afledte data, hvor dette er relevant. Fælles funktionalitet skal fortsat ligge i eller genbruges fra de eksisterende fælles komponenter.

Fastlæg en mappestruktur, der:
- holder originalkilderne adskilt fra bearbejdede og afledte data;
- gør det tydeligt, hvilke data der er autoritative;
- adskiller almanakspecifik logik fra fælles pipeline-logik;
- dokumenterer afhængigheder til eksisterende scripts;
- gør det muligt at gentage og validere transformationerne.

Tilpas ikke den eksisterende pipeline eller dagbogsdata unødigt for at få plads til almanakken. Foreslå fælles ændringer, når de reelt forbedrer den generelle infrastruktur, og dokumentér deres konsekvenser.

## 8. Plan for den videre digitalisering

På baggrund af kildeanalysen og pipelinegennemgangen skal du udarbejde en trinvis plan for den videre digitalisering.

Planen skal som minimum behandle:

1. Valg og dokumentation af det primære datagrundlag.
2. Eventuel etablering af en kombineret tredje version.
3. Tekst- og strukturmæssig validering.
4. Genbrug og tilpasning af eksisterende preprocessing.
5. Segmentering af almanakken i de relevante dataenheder.
6. Kobling mellem strukturerede data og PDF-sider eller -afsnit.
7. Kvalitetskontrol og håndtering af usikkerhed.
8. Dokumentation af resultatet og mulighed for at gentage processen.

Rækkefølgen skal tilpasses de faktiske forhold i repositoryet og de problemer, der afdækkes i kildeanalysen.

For hvert trin skal du angive:
- formålet;
- relevante eksisterende scripts eller komponenter;
- nødvendige nye komponenter;
- input og forventet output;
- valideringskriterier;
- væsentlige afhængigheder og uafklarede spørgsmål.

## 9. Leverancer fra den indledende opgave

Den indledende opgave er en undersøgelse og en implementeringsplan, ikke en fuld digitalisering.

Aflever følgende:

**A. Kildeanalyse**
En dokumenteret sammenligning af database og PDF med konkrete eksempler, vurderingsparametre og begrundede konklusioner.

**B. Anbefaling af datagrundlag**
Et eksplicit valg mellem de mulige strategier, inklusive begrundelse og eventuelle forbehold.

**C. Plan for en kombineret version**
En beskrivelse af dataenheder, matching, feltprioritering, kildeproveniens og validering, hvis en kombineret version anbefales.

**D. Repository- og pipelineanalyse**
En oversigt over relevante eksisterende scripts, dokumentation og komponenter med anbefalinger om genbrug og tilpasning.

**E. Forslag til mappestruktur**
En konkret, begrundet struktur for almanakprojektet i det eksisterende repository.

**F. Trinvis implementeringsplan**
En prioriteret plan for det videre arbejde med tydelige afhængigheder og acceptkriterier.

## 10. Arbejdsprincipper

- Undersøg først, hvad der allerede findes.
- Dokumentér observationer og konkrete eksempler frem for at basere konklusioner på antagelser.
- Skeln tydeligt mellem faktiske fund, anbefalinger og uafklarede spørgsmål.
- Bevar kildedata og kildeproveniens.
- Prioritér reproducerbare transformationer og eksplicit validering.
- Genbrug eksisterende funktionalitet, hvor det er fagligt og teknisk forsvarligt.
- Undgå at ændre velfungerende dele af dagbogspipelinen uden en dokumenteret grund.
- Stop ved undersøgelse, anbefaling og planlægning, medmindre der allerede foreligger en særskilt godkendelse af implementeringen.

**Det endelige mål er at etablere et veldokumenteret datagrundlag for almanakken og en realistisk plan for at digitalisere den ved at genbruge repositoryets eksisterende infrastruktur, hvor det giver mening.**
