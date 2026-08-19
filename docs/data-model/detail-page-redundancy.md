# Redundans-oprydning på detaljevisninger (person/sted/værk)

**Brugerpræference (2026-08-19):** `persons.html`, `place.html` og
`work.html`s detaljevisning (`?reg=…`) viste tidligere det samme faktum
flere gange i forskellig indpakning — samme navn i titel, brødtekst-
overskrift *og* en sidebar-tabel; samme årstal i titlen *og* en metadata-
linje *og* en Født/Død-række; samme registertype som et badge *og* en
tabelrække, selvom brødsmuls-stien allerede sagde det samme. En bruger
skulle læse den samme oplysning tre-fire gange for at finde ud af, at det
rent faktisk kun var ét faktum.

**Princip:** hver oplysning skal have **ét** naturligt hjem på siden — det
sted en læser instinktivt leder efter den — og vises **kun** der. Et
internt ID, et navn, en dato, et antal dagbogsreferencer optræder ikke i
flere former blot fordi flere komponenter historisk set alle fik lov at
vise det.

## Hvor hver oplysning bor nu

| Oplysning | Bor nu | Bor IKKE længere i |
|---|---|---|
| Internt ID-nr. (`RegXXXXXXX`) | Sidste led i brødkrumme-stien (monospace) | Hero-badge/chip, sidebar-tabel |
| Navn/titel | `<h1>` | Sidebar "Label"-række |
| Registertype (PERSON-/STED-/VÆRK-REGISTER) | Brødkrumme-stiens 2. led (person/sted) — **udgår helt** for værker, se nedenfor | Hero-badge, sidebar-tabel |
| Fødsels-/dødsår, "1800-tallet" | `<h1>`s egen `(1825–1912)`-parentes | Hero-metalinje, sidebar Født/Død-rækker. "1800-tallet" vises slet ikke — overflødigt ved siden af de eksakte år |
| Rolle/beskrivelse | "Beskrivelse"-sektionen i hovedindholdet | Hero-metalinje, sidebar "Rolle"-række |
| H2/H3-kategori (værker) | Brødkrumme-stiens 2.–3. led | Hero-chips, hero-metalinje, sidebar-tabel |
| Antal dagbogstræffere | "Dagbogsreferencer"/"Viser X af Y …"-linjen, i sin naturlige kontekst | Hero-metalinje, sidebar "Træffere"-række |
| Sprog, forfatter, dato (værker) | Sidebar "Registeroplysninger" — de eneste felter der **ikke** vises andetsteds | Hero-metalinje (sprog) |
| Land, engelsk eksonym (steder) | Hero-metalinje — de eneste felter der ikke vises andetsteds | Sidebar-tabel |
| Koordinater (steder) | "Kort"-sektionens billedtekst, ved siden af selve kortet | Hero-metalinje, sidebar-tabel |
| Wikidata-autoritetslink | "Autoritetslinks"-sidebarblokken (markeret `info-block--enriched`/`sidebar-box`, se `docs/external-links.md` §2a) | Hero-chip/badge (var tidligere dupleret der) |

## Konsekvens: hele "Registerdata"-blokken udgår på personer/steder

For `persons.html` og `place.html` viste sidebar-blokken **udelukkende**
felter, der allerede stod et andet sted på siden, når først ID'et var
flyttet til brødkrummen — der var intet tilbage, der retfærdiggjorde
blokken. Den er derfor fjernet helt; sidebaren viser nu kun de blokke der
faktisk tilføjer noget (`Autoritetslinks`, `Biografiske opslag`).

For `work.html` er situationen anderledes: "Registeroplysninger"-boksen
rummede *også* forfatter, originalsprog og dateringsår — felter der intet
andet sted vises. Boksen udgår derfor ikke, men de rækker der reelt
duplikerede brødkrumme/hero er skåret væk (ID, H1, H2, H3, antal refs.).
Boksen renderes slet ikke, hvis ingen af de tre resterende felter er sat —
en næsten-tom boks med kun en overskrift ville se ud som en fejl.

## Hvorfor H2/H3 stadig vises to steder på work.html (bevidst undtagelse)

Brødkrummens 2.–3. led (`Bibliotek › Samlede og blandede Skrifter`) er
selv **navigation** — et klik fører til den overordnede kategori. Det er
ikke ren gentagelse i samme forstand som fx et badge, der blot genskriver
samme tekst uden funktion; det er den etablerede måde at vise "hvor er jeg
i hierarkiet" på tværs af hele registret. Hero-chips, hero-metalinje og
sidebar-rækkerne, der *også* skrev H2/H3 som ren tekst uden nogen
funktion ud over at gentage brødkrummen, er fjernet.

## Berørte filer

- `mockup/persons.html` — brødkrumme, hero-chips/-meta, sidebar
- `mockup/place.html` — brødkrumme, hero-chips/-meta, sidebar
- `mockup/work.html` — brødkrumme, hero-chips/-meta, sidebar
- `mockup/person.html` — **ikke** ændret i denne omgang; siden er en
  ubrugt legacy-visning (kort til `persons.html?reg=…`, ikke
  `person.html?reg=…` — se `docs/data-model/person-bio-search-links.md`),
  så den er lavere prioritet end de tre live sider.
