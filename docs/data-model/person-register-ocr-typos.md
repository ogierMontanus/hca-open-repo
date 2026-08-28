# Tastefejl/OCR-fejl i personregistret — Asbjørnsen-sagen (fremtidig opgave)

**Status:** ikke rettet. Dette dokument registrerer et konkret, bekræftet
fund og det bredere billede omkring det, som grundlag for en senere,
selvstændig oprydningsopgave — ikke en rettelse foretaget nu.

## Det konkrete fund

Personregistrets egen post for den norske eventyrsamler er stavet forkert:

```
entity_id: Reg0033060
label:     "Asbjømsen, P. C. (1812–1885)"
```

— skal være **"Asbjørnsen"**. At det er en fejl i selve kildedata, ikke en
gyldig alternativ stavemåde, bekræftes af registrets egen værktitel, som
staver navnet korrekt i samme datasæt:

```
"Norske Folkeeventyr (P. C. Asbjørnsen og Jørgen Moe)"
```

`rn` → `m` er et klassisk OCR-fejllæsningsmønster (ligaturen "rn" minder
visuelt om "m" i mange skrifttyper/scanninger) — det er **ikke** en
diacritic-forskel som Oehlenschlæger/Oehlenschläger (rettet tidligere i
denne session), og derfor rammer ingen af de generelle fold-regler i
`nameKey()` (ä→æ, ö→ø, ü→y, NFD-strip) eller genitiv-fallback'en
(`genitiveStrippedRid`) den. `EntityRefs.personRid("P. C. Asbjørnsen")`
returnerer stadig `null` efter begge fixes.

Fejlens størrelse understreger hvorfor: Levenshtein-afstanden mellem de
foldede efternavne `asbjørnsen` og `asbjømsen` er **2** (ét bogstav
slettet, ét substitueret), ikke 1. Den ligger dermed uden for rækkevidde
af den edit-distance-≤1-heuristik, der bruges til at finde "sandsynlige
stavevarianter" i det bredere skøn nedenfor — et endnu hårdere tilfælde
end dem, der allerede er identificeret der.

## Hvorfor ikke bare rette denne ene post nu

At hardcode en enkelt label-rettelse ("Asbjømsen" → "Asbjørnsen") direkte
i `entities.csv` eller i et byggescript ville løse det synlige symptom
uden at sige noget om, hvor mange lignende OCR-fejl der findes andre
steder i det ~10.228-personer store register, og uden den
live-verifikation CLAUDE.md kræver af faktuelle rettelser. Projektets
"ask, don't guess"-princip (WEMI-dokumentets regel 8) og
fact-check-proceduren peger begge mod en kurateret, efterprøvet tilgang
frem for en ad hoc-patch. Se **Anbefalet fremgangsmåde** nedenfor.

## Det bredere billede (målt 2026-08-28, efter denne sessions rettelser)

Kørt mod `mockup/data/works-extra.js` efter alle denne sessions fixes
(diacritic-fold, genitiv-fallback, multi-forfatter-isolering,
non_fiction-wiring):

| Mål | Antal |
|---|---:|
| Distinkte, ikke-generiske forfatter-strenge i `WORKS_EXTRA` | 1.459 |
| — resolver til en personregister-post | 731 (50 %) |
| — resolver **ikke** | 728 |
| Heraf: efternavn inden for Levenshtein-afstand ≤1 af en registreret person (sandsynlig stavevariant) | 131 |
| Heraf: intet nært match (sandsynligvis reelt uregistreret, team-/institutionskredit, eller flerordskredit) | 597 |

De 131 "sandsynlig stavevariant"-kandidater spænder fra ægte OCR-/tastefejl
(`"C. V. Böttigers"` ~ `"bøttiger"`, `"J. C. Biernatzski"` ~
`"biernatzki"`) til falske positiver, hvor edit-distance-heuristikken
rammer et helt andet, urelateret efternavn ved et tilfælde (`"Karl XV"` ~
`"xiv"`, `"S. Croce"` ~ `"crone"`) — listen er et udgangspunkt for manuel
gennemgang, ikke en automatisk rettelsesliste. Se
`scan_live_authors.py`/`assess_spelling_variants.js`-mønsteret brugt til
at generere den (samme fremgangsmåde som gav Oehlenschläger-fundet
tidligere i denne session).

## Anbefalet fremgangsmåde (næste session)

1. **Kuratér, ret ikke automatisk.** Byg en `data/curated/
   person_label_corrections.csv` efter samme mønster som
   `data/curated/works_wikidata.csv` — én verificeret rettelse pr. linje,
   aldrig en bulk-udskiftning baseret på edit-distance alene.
2. **Verificér hver rettelse live** før den skrives, jf. CLAUDE.md's
   Wikidata-opslagsprocedure — Asbjørnsen som pilottilfælde: bekræft navn
   og Q-nummer via `WebSearch` med `wikidata.org`-domænefilter, ikke ud fra
   hukommelse.
3. **Start med de 131 edit-distance-≤1-kandidater** som næste tranche —
   højeste sandsynlighed for reelle fejl pr. gennemgået post — og lad de
   597 uden nært match ligge; de er langt oftere reelt uregistrerede
   personer eller kollektive krediteringer end tastefejl.
4. Når `person_label_corrections.csv` findes, kan `build_works_extra.py`
   og `build_persons_extra.py` læse den samme måde de allerede læser
   `works_wikidata.csv` — ingen ny mekanisme, kun en ny kilde.
