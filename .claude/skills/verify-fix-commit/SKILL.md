---
name: verify-fix-commit
description: Re-verify a commit that claims to fix a described root cause (CSS, race condition, off-by-one, etc.) by re-deriving the bug's mechanism against the code as it stands after the change. Use whenever asked to doublecheck, confirm, or verify that a fix actually works — do not treat the commit's own message as proof.
---

# Verificering af "fix"-commits

**Krav:** Tag ikke en fix-commits egen commit-besked som bevis for at den
virker. Genudled fejlens beskrevne mekanisme mod koden, *som den er efter
ændringen* — linje for linje — før den betragtes som løst.

**Baggrund:** En commit på `facet-panel--overlay-open` diagnosticerede
korrekt at iOS Safari fanger `position:fixed`-efterkommere, når en
`position:sticky`-forfader har en hvilken som helst ikke-`visible`
overflow-værdi. Commit'en fjernede derfor `overflow:hidden` fra
`.facet-panel--overlay-open` — men `.facet-panel`s grundregel satte
allerede `overflow-y: auto` ubetinget, uafhængigt af den klasse, så
fælden stod stadig åben. Diagnosen var rigtig; ændringen ramte bare det
forkerte sted. Fejlen blev først fanget ved eksplicit at blive bedt om at
"doublecheck" — ikke ved almindelig selvkritik efter commit.

## Procedure

Efter enhver fix af en beskrevet rod-årsag (CSS, race conditions,
off-by-one, osv.):

1. Genlæs fixens egen beskrivelse af mekanismen — hvilken betingelse
   udløser fejlen?
2. Læs koden *som den er nu*, ikke som commit-beskeden beskriver den.
   Bekræft linje for linje at ændringen faktisk fjerner betingelsen.
3. Find alle andre steder i den nuværende kode, der uafhængigt kan
   udløse samme mekanisme — ikke kun det sted der blev rettet. En
   ubetinget grundregel andetsteds i samme fil/komponent kan stadig
   opfylde betingelsen, selvom den specifikke klasse blev rettet.
4. Rapportér eksplicit om fixen er fuldstændig, delvis, eller slet ikke
   virker — en rigtig diagnose garanterer ikke en fuldstændig rettelse.
