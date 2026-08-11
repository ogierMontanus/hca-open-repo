# Klassifikation af 80-stedssample efter 6-leddet stedtypologi — copilot-rapport

> **Status:** Arkiveret intern dokumentation. Dette er resultatrapporten fra
> en copilot/bot-klassifikation af de 80 stednavne i
> [`place-categorization-copilot-prompt.md`](place-categorization-copilot-prompt.md),
> udført efter den endelige 6-kategori-taksonomi i
> [`place-typology.md`](place-typology.md) (afsnit F). Rapporten er gemt
> verbatim (kun tabelstruktur er genoprettet fra en sammenklappet
> copy-paste), som sammenligningsgrundlag for fremtidige klassifikations-
> gennemgange.
>
> **Kilde:** Copilot-gennemgang leveret af bruger, 2026-08-11.
>
> **Redaktionel bemærkning om fodnoter:** Kildeteksten indeholder spredte
> fodnote-/citationsnumre (fx `.17`, `.16`, `16.`, `.109`), der refererer til
> en ekstern litteraturliste, som ikke fulgte med i den indsendte rapport.
> Numrene er bevaret i teksten som proveniens-markører, men kan ikke pt.
> opløses til deres kildehenvisning. Ét sted i kildeteksten
> (`de interne lister.2119`) er to sammenklappede fodnotetal, der ikke kan
> adskilles med sikkerhed — bevaret som i originalen.

## Kort resultat

80 stednavne er klassificeret. Rapportens forfatter regner 2 som **USIKRE**
på klassifikationsniveau: *Falkensten* og *Chåtdet*. Flere andre har usikker
eller historisk normalform, men kategorien vurderes forsvarlig.

Klassifikationen er afstemt mod enterprise-registre, især
`Location-V0.91-Data.xlsx`, `HCA-Repository V0.82.xlsx` og
`Sted-register.txt`, hvor mange af navnene optræder som
registertitler/forekomster — fx er Arbesau, Breitenburg, Chåtdet, Falkensten,
Galli/Li, Hessingen (Essingen), Kowicz og Kuhstall m.fl. registreret i de
interne lister.

Typologisk er kategorierne læst funktionelt: GeoNames' featurekoder skelner
bl.a. mellem administrative enheder, vandløb/søer, populated places, parker,
bygninger/anlæg og topografiske former som bjerge, øer og klipper.

## Samlet statistik

*Figur 1: Fordeling af de 80 stednavne på den 6-leddede stedtypologi.*

| Kategori | Antal |
|---|---:|
| Bebyggede områder | 51 |
| Lande/administrative enheder/regioner | 7 |
| Vandområder | 4 |
| Landskabsformer og naturfænomener, inkl. øer | 12 |
| Bygninger/anlæg/fortidsminder | 5 |
| Parker/haver/naturområder | 1 |
| **I alt** | **80** |
| **USIKRE klassifikationer** | **2** |

## Fuld klassifikationsliste

**Forkortelser:** Bebygg. = bebyggede områder; Adm./reg. = lande/administrative
enheder/regioner; Vand = vandområder; Landskab/natur = landskabsformer og
naturfænomener inkl. øer; Anlæg/fortidsm. = bygninger/anlæg/fortidsminder;
Park/natur = parker/haver/naturområder.

| Stednavn | Mest sandsynlige referent | Kategori | Begrundelse |
|---|---|---|---|
| Sieghartskirchen | Kommune/by i Niederösterreich | Bebygg. | Bebyggelsesnavn. |
| Gotha | By i Thüringen | Bebygg. | By. |
| Woigwitz | Historisk landsby i Schlesien; Meyers angiver "Dorf" | Bebygg. | Landsby. [17] |
| Malines | Mechelen/Malines, Belgien | Bebygg. | By. |
| Heiligeostedten | Heiligenstedten, Holsten | Bebygg. | Landsby/kommuneform. |
| Randers | Dansk købstad/by | Bebygg. | By. |
| Källtorp | Svensk lokalitet/gårdnavn | Bebygg. | Bebyggelses-/gårdnavn. |
| Trollhättan | Svensk by | Bebygg. | Bare navneform, ikke "faldene". |
| Karrebæksminde | Dansk kystby | Bebygg. | Bebyggelse. |
| Strengberg | Østrigsk kommune | Bebygg. | Kommune/by. |
| Nordtyskland | Historisk/geografisk region | Adm./reg. | Regional betegnelse. |
| Reuss | Reuss-floden i Schweiz | Vand | Schweiz' turistportal beskriver Reuss som central-schweizisk flod. [16] |
| Tostedt | Tysk kommune/by | Bebygg. | Bebyggelse. |
| Horsens | Dansk by | Bebygg. | By. |
| Marmara-Øen | Ø i Marmarahavet | Landskab/natur | Ø. |
| Valencia | Valencia, Spanien | Bebygg. | Primært byreferent. |
| Mori | Mori i Trentino | Bebygg. | By/kommune. |
| Theresienstadt | Terezín/Theresienstadt, fæstningsby | Bebygg. | Kilden kalder stedet en lille by og fæstningsby; her valgt som bynavn, ikke lejr-/fortidsmindetype. [5] |
| Butzbach | Tysk by | Bebygg. | By. |
| Hesselagerstenen | Damestenen/Hesselagerstenen, vandreblok | Landskab/natur | Geoparkkilde: Danmarks største kendte vandreblok på land. [15] |
| Sevilla | Sevilla, Spanien | Bebygg. | By. |
| Falkensten | Sandsynlig Falkenstein/Falkensten, slot/ruin eller klippested | Anlæg/fortidsm. | **USIKKER:** intern registerform findes, ekstern referent ikke sikkert verificeret. |
| Trier | Trier, Tyskland | Bebygg. | By. |
| Hofmansgave | Herregården/godset Hofmansgave | Anlæg/fortidsm. | VisitNordfyn beskriver Hofmansgave som herregård/gods. [14] |
| Rava | Rava, kroatisk ø i Zadar-arkipelaget | Landskab/natur | Visit Zadar beskriver Rava som ø med Vela Rava og Mala Rava. [13] |
| Bornholm | Ø | Landskab/natur | Ø. |
| Niesen | Bjerg i Schweiz | Landskab/natur | Bjerg. |
| Rheine | Tysk by | Bebygg. | By. |
| Senlis | Fransk by | Bebygg. | By. |
| Dublin | Irsk hovedstad/by | Bebygg. | By. |
| England | Land/historisk region | Adm./reg. | Land/region. |
| Monte Rosa | Alpebjerg/massiv | Landskab/natur | Bjergmassiv. |
| Pietra Mala | Pietramala/Pietra Mala, italiensk lokalitet | Bebygg. | Vej-/lokalitetsnavn, ikke primært naturtype her. |
| Mornaux | Les Mornaux/Mornaux, belgisk/fransk lokalitet | Bebygg. | Lokalitet; normalform bør kontrolleres. |
| Neuhaus (Schweiz) | Schweizisk lokalitet, sandsynlig Neuhaus | Bebygg. | Bebyggelses-/lokalitetsnavn. |
| Hellebæk | Dansk by/lokalitet | Bebygg. | Bebyggelse. |
| Monte Cavo | Vulkanbjerg i Albanerbjergene | Landskab/natur | Bjerg/vulkan. |
| Roosendaal | Nederlandsk by | Bebygg. | By. |
| Reichenbach | Sandsynlig by/lokalitet, ikke Reichenbachfaldene | Bebygg. | Bare navneform; falde ville normalt markeres særskilt. |
| Meran | Merano/Meran | Bebygg. | By. |
| Wallersee | Sø i Østrig | Vand | Sø. |
| Hollabrunn (Ober-Hollabrunn) | Østrigsk by | Bebygg. | By. |
| Rabenstein ved Maxen | Klippe-/naturpunkt ved Maxen | Landskab/natur | "ved Maxen" peger mod lokalt topografisk punkt; dog vanskelig. |
| Indien | Land/region | Adm./reg. | Land. |
| Hermupolis Syra | Ermoupoli på Syros | Bebygg. | By. |
| Bellevue (Klampenborg) | Bellevue Strand/strandbad ved Klampenborg | Park/natur | VisitCopenhagen beskriver Bellevue som 700 m sandstrand i Klampenborg. [12] |
| Haag | Den Haag | Bebygg. | By. |
| Arbesau | Historisk bøhmisk/tysk lokalitet | Bebygg. | Registerform; by-/lokalitetsnavn. |
| Kowicz | Sandsynlig polsk lokalitet/by | Bebygg. | Registerform; normalform usikker, kategori stabil. |
| Sæby Løve H Holbæk A | Sæby i Løve Herred, Holbæk Amt | Bebygg. | Lokalitet/sogn angivet med herred/amt. |
| Minneapolis | By i USA | Bebygg. | By. |
| Weissenburg Bayern | Weißenburg i Bayern | Bebygg. | By. |
| Rieti | Italiensk by | Bebygg. | By. |
| Danmark Sogn i Uppsala Len | Danmark sogn, Uppsala län | Adm./reg. | Sogn = administrativ/kirkelig enhed; GeoNames har PRSH som parish/ecclesiastical district. [6] |
| Mornex | Fransk kommune/lokalitet | Bebygg. | Bebyggelse. |
| Irland | Land | Adm./reg. | Land. |
| Jerichow | Tysk by/lokalitet | Bebygg. | By. |
| Seinen | Seine-floden | Vand | Flod. |
| Oldenzaal | Nederlandsk by | Bebygg. | By. |
| Elmshorn | Tysk by | Bebygg. | By. |
| Helvetes-Faldene Trollhätta | Vandfald ved Trollhättan | Landskab/natur | Navnet markerer fald/naturfænomen. |
| Orange | Orange, Provence | Bebygg. | By. |
| Steinsdorf | Tysk/østrigsk landsby-/lokalitetsnavn | Bebygg. | Bebyggelse. |
| Erfurt | Tysk by | Bebygg. | By. |
| Kuhstall | Naturlig klippeport i Sachsisk Schweiz | Landskab/natur | Officiel kilde beskriver Kuhstall som naturlig sandstens-klippeport. [11] |
| Petershøi | Henriques' Petershøi ved Klampenborg | Anlæg/fortidsm. | KB/Samlinger placerer Andersen "hos Henriques paa Petershøi ved Klampenborg" og "indenfor Petershøis Enemærker"; behandles som ejendom/villa. [109] |
| Mägdesprung | By/lokalitet i Harzen | Bebygg. | Bebyggelsesnavn. |
| Münchberg | Tysk by | Bebygg. | By. |
| Semendria (Smederevo) | Smederevo/Semendria | Bebygg. | By; fæstning sekundær her. |
| Galli Li | Li Galli/Sirenuse-øerne | Landskab/natur | Positano-kilde beskriver Li Galli som tre små øer/islets. [8] |
| Ekeberg Christiania | Ekeberg ved Christiania/Oslo | Landskab/natur | Høj/terræn- og udsigtområde. |
| Mose1 | Sandsynlig Mosel; OCR/normaliseringsproblem | Vand | Britannica beskriver Moselle/Mosel som flod; "Mose1" læses sandsynligvis Mosel. [4] |
| Hessingen (Essingen) | Essingen/Hessingen, lokalitet | Bebygg. | Bebyggelsesnavn. |
| Waadt (Kanton) | Kanton Vaud/Waadt | Adm./reg. | Kanton = administrativ enhed. |
| Breitenburg | Schloss/Gut Breitenburg | Anlæg/fortidsm. | Kilde beskriver Breitenburg Castle som herregård/fæstet renæssancesæde. [7] |
| Chåtdet | Sandsynlig fejl-/OCR-form, mulig Châtelet | Anlæg/fortidsm. | **USIKKER:** intern registerform findes, men ekstern identifikation ikke sikkert verificeret. |
| Genova | Genova/Genoa | Bebygg. | By. |
| Albano Laziale | Italiensk by | Bebygg. | By. |
| Ferrara | Italiensk by | Bebygg. | By. |
| Sachsen (Kongerige) | Kongeriget Sachsen | Adm./reg. | Historisk stat/administrativ enhed. |

## Særligt vanskelige/tvetydige tilfælde

**Reichenbach** er klassificeret som bebyggelse, ikke vandfald. Grunden er
navneformen: når der menes vandfald, er register- og stednavnepraksis
normalt eksplicit med "Fald/Faldene", som i *Helvetes-Faldene Trollhätta* og
andre faldnavne i registermaterialet. (Dette bekræfter grænsetilfælde-
vejledningen for Reichenbach i
[`place-categorization-copilot-prompt.md`](place-categorization-copilot-prompt.md#1-bebyggede-omr%C3%A5der):
uden eksplicit "Fald"-markør klassificeres som BEBYGGET.)

**Theresienstadt** kunne friste til Bygninger/anlæg/fortidsminder, fordi
stedet er stærkt forbundet med fæstning, ghetto og mindested; men kilden
beskriver det samtidig som en lille by/fæstningsby, og navneformen i listen
er bynavnet. Derfor Bebyggede områder — i overensstemmelse med
grænsetilfælde-reglen i prompten.

**Mose1** er sandsynligvis en OCR-/normaliseringsfejl for *Mosel*. Fordi den
relevante geografiske referent er Mosel/Moselle-floden, er kategorien
Vandområder, men normalformen bør korrigeres i data.

**Rabenstein ved Maxen** er ikke markeret USIKKER, men bør kontrolleres mod
tekstkontekst. "Ved Maxen" peger mere mod et lokalt klippe-/terrænpunkt end
en selvstændig by; Maxen-konteksten er et bakket landskab ved Dresden og
Sachsisk Schweiz.

**Falkensten** og **Chåtdet** er de eneste to, der markeres USIKKER på
klassifikationsniveau. Begge findes i enterprise-registermaterialet, men
rapportens forfatter fandt ikke tilstrækkelig sikker ekstern identifikation
til at afgøre, om de er anlæg, bebyggelse eller naturpunkt uden forbehold.

## Observationer ved arkivering

- Rapportens klassifikationer af sammensatte navne med administrativ
  markør (*Danmark Sogn i Uppsala Len* → Adm./reg.; *Waadt (Kanton)* →
  Adm./reg.) er konsistente med undtagelsesreglen for Kategori 2 vs. 4 i
  `place-typology.md` (afsnit F): suffiks som "sogn"/"kanton" udløser
  Kategori 2, mens bare naturgeografiske navne uden suffiks (*Bornholm*,
  *Marmara-Øen*) forbliver Kategori 4.
- **Sæby Løve H Holbæk A** er klassificeret som Bebygg., ikke Adm./reg.,
  selvom herred og amt indgår i navnet — fordi herred/amt her fungerer som
  *lokaliserende tilføjelse* til stednavnet "Sæby" (et almindeligt
  værktøj i ældre danske topografiske registre til at skelne mellem
  flere steder med samme navn), ikke som betegnelse for selve den
  administrative enhed. Dette er en anden situation end fx *Bogø Sogn*,
  hvor sognet selv er referenten.
- Ingen af de 80 klassifikationer falder under den særskilt dokumenterede
  kanal-undtagelse (Kategori 3 fremfor 5) — sample'en indeholder ingen
  kanalnavne.
