# Metode: krydsreference mellem to versioner af et register

**Skrevet:** 2026-09-05, efter en konkret afstemning mellem bind 12s
kunstnerliste (`ArtistList_linked_manual_2026-09-03.csv`) og to versioner
af bind 11-registret (2A = xlsx fra 3. sep., 2B = tsv fra 4. sep.). Fuld
sagsrapport: `datacleaning/diaries_datacleaning/volume12/person-id-reconciliation-2A-2B-2026-09-05.md`.

Dette dokument generaliserer metoden til brug, når en tredje udgave af et
register (»spreadsheet 3«, eller enhver senere version) skal sammenholdes
med en tidligere, og forskellene skal kunne forklares præcist — ikke bare
konstateres.

## Hvorfor dette overhovedet er nødvendigt

`01_entry_id` (og lignende positionsbestemte id'er) **gennemnummereres**,
hver gang rækker tilføjes, fjernes eller splittes et andet sted i filen.
Et id fra kørsel A peger derfor ikke nødvendigvis på den samme post i
kørsel B — heller ikke hvis kun ét enkelt id ser ud til at være ændret ved
et hurtigt kig. Se `person-master-files.md`s advarsel om samme problem.

Konsekvensen af at ignorere dette er ikke en håndfuld forkerte links. Hvis
id'erne er forskudt systematisk (fx fordi rækker blev fjernet tidligt i
filen), rammer forskydningen **alle efterfølgende id'er** — i den faktiske
sag ville 100 % af 2.239 links have peget på en forkert person.

## Forudsætning: en indbygget facitliste

Metoden kræver, at den fil der skal opdateres ("Index 1" nedenfor) selv
gemmer en **uafhængig beskrivelse** af det den linker til — ikke kun et
id. I den konkrete sag var det en `RegistryTitle`-kolonne ved siden af
`PerID`. Uden den facitliste kan man ikke *måle* om et id peger rigtigt;
man kan kun gætte.

Hvis en sådan kolonne ikke findes, må den konstrueres først (fx ved at
slå det gamle id op i den gamle version og skrive titlen ned), før resten
af metoden giver mening.

## De syv trin

### 1. Lås versionerne fast

Notér filsti og **ændringstidspunkt** for hver version, før noget andet
sker. Rækkefølgen (hvilken er ældre, hvilken er nyere) afgør hvilken vej
krydsreferencen peger.

### 2. Mål — gæt ikke — differencen i rækkeantal

```python
print(len(rows_old), len(rows_new), len(rows_old) - len(rows_new))
```

En antaget difference ("cirka 50") kan være helt forkert (i den faktiske
sag var den 15, ikke 50). Byg intet videre på et ikke-verificeret tal.

### 3. Test hvilken version Index 1 rent faktisk er bundet til

Dette er det afgørende trin, og det springes typisk over. Brug Index 1s
egen facitliste-kolonne:

```python
for version_name, version_index in (("gammel", old_by_id), ("ny", new_by_id)):
    hits = sum(1 for r in index1_rows
               if norm(reconstructed_title(version_index.get(r.id)))
                  == norm(r.recorded_title))
    print(version_name, hits, "/", len(index1_rows))
```

Forvent et skarpt skel — 100 % mod den ene version, tæt på 0 % mod den
anden. Et uklart resultat (fx 60/40) betyder, at Index 1 selv er
inkonsistent, og det skal opklares før man går videre.

### 4. Byg krydsreferencen på indhold, aldrig på position

Match på en nøgle der er stabil på tværs af omnummerering — for
personregistre: efternavn + fornavn + sidehenvisningssignatur (+ evt.
leveår, beskrivelse som tie-breaker). Prøv i faldende specificitet og tag
kun et match, hvis det er entydigt i begge retninger ved det
specificitetsniveau:

```python
levels = [full_content, raw_line, surname_plus_refs]
for key_fn in levels:
    if unique_in(old, key_fn(row)) and unique_in(new, key_fn(row)):
        record_match(...)
        break
```

For hver post der ikke matcher på noget niveau: undersøg *hvorfor* den er
væk, fremfor at antage den er slettet. I den faktiske sag var alle 15
"manglende" poster dubletter af en overlevende `underpost` — ikke tabt
indhold.

### 5. Kør logiktesten (seks kontroller, alle skal give 0 fejl)

| Test | Spørgsmål |
|---|---|
| A. Referenceintegritet | Findes det nye id rent faktisk i den nye fil? |
| B. Entydighed | Peger to gamle poster på samme nye id uden grund? |
| C. Omvendt konsistens | Er personen/tingen bag gammelt og nyt id den samme? |
| D. Manglende id i brug | Bruger Index 1 overhovedet et af de forsvundne id'er? |
| E. Dublet-mål | Får flere af Index 1s brugte id'er samme mål? |
| F. Navnekonsistens | Stemmer navnet/titlen overens mellem gammel og ny post? |

**Test D er ofte den vigtigste for konklusionen.** Hvis ingen af de
forsvundne id'er bruges af Index 1, er de forsvundne poster i praksis
irrelevante for opgaven — også selvom de udgør et reelt tab andetsteds.

### 6. Valider identitet uafhængigt af id-kæden

Trin 3-5 beviser at *substitutionen* er korrekt udført. De beviser ikke,
at den *rigtige person/ting* er fundet. Kør derfor en sidste, uafhængig
kontrol: sammenlign Index 1s eget navnefelt direkte mod den nye posts
navn — uden om nogen af de mellemliggende id'er:

```python
shared = tokens(index1_row.name) & tokens(new_row.title)
```

Gennemgå enkeltvis de tilfælde uden fælles navneled. De falder typisk i
tre grupper:
* tilsigtede stavevarianter/pseudonymer (uskadelige, dokumentér dem);
* eksisterende fejl i Index 1 der intet har med krydsreferencen at gøre
  (fx et kildeudtryk fejlagtigt behandlet som personnavn);
* ægte fejlmatch — kun denne gruppe er et problem med selve metoden.

### 7. Ende-til-ende-stikprøve på grænsetilfælde

Vælg bevidst prøver hvor en systematisk fejl ville vise sig først:

* det laveste og det højeste id i brug (en forskydning slår typisk
  igennem i den ene ende af filen);
* et fast kontrolpunkt, hvis manuelt arbejde allerede er nået dertil;
* stavevarianter, pseudonymer, og poster markeret usikre i forvejen;
* hyppige efternavne + initialer (den klassiske ambiguitetsfælde).

## Levering

* **Krydsreferencetabel** (`id_gammel`, `id_ny`, navn/titel begge veje,
  matchstatus, metode, evidens) — dette er det egentlige produkt, ikke et
  biprodukt.
* **Omskrevet Index 1** med det nye id, men med det gamle id bevaret i
  en revisionskolonne — omskrivningen skal kunne fortrydes.
* **Rapport** med de syv trins resultater, herunder eksplicit:
  * hvor mange id'er blev entydigt mappet;
  * hvor mange manglede, og om de faktisk bruges af Index 1;
  * de konkrete undtagelser fra trin 6, med forklaring;
  * en af de tre endelige kategorier:
    **SAFE TO TRANSFORM** / **SAFE WITH MANUAL REVIEW** / **NOT SAFE**.

## Faldgruber observeret i praksis

* **En observeret offset er ikke en regel.** I den faktiske sag var
  forskydningen +13 for 10.078 rækker, men +15 for den sidste. En
  offset-baseret "genvej" ville have ramt forkert netop ved kanten.
* **Et "ingen match"-resultat kan skjule en dublet, ikke et tab.**
  Undersøg altid hvorfor, før man konkluderer at indhold er forsvundet.
* **Uklare eller manglende matchstatus-felter i Index 1 selv** (fx
  "NO MATCH", "UNCERTAIN") er ofte allerede kendte fejl, der overlever
  krydsreferencen uændret — de er ikke skabt af omskrivningen, men bør
  stadig rapporteres som poster til gennemsyn.
* **Gentag trin 3** hver gang kildefilen ændres igen. Det er den prøve
  der først afslører, om en ny version har introduceret endnu en
  forskydning.

## Genbrug mod en tredje version ("spreadsheet 3")

Når en tredje version skal sammenholdes:

1. Kør trin 1-3 mellem den seneste allerede-validerede version (2B i den
   faktiske sag) og den nye version 3. Brug 2B som den "gamle" side —
   ikke 2A — så den eksisterende, verificerede krydsreference ikke skal
   genopbygges fra bunden.
2. Byg en ny krydsreferencetabel 2B → 3 efter samme metode (trin 4-5).
3. Kæd tabellerne: Index 1 → 2A → 2B → 3. Bekræft med en stikprøve
   (trin 6-7) at kæden samlet set giver den rigtige person, ikke kun at
   hvert enkelt led for sig er internt konsistent.
4. Til kollegaen: forklar forskellene med konkrete tal fra logiktesten
   (hvor mange poster, hvilken kategori, hvilke navngivne undtagelser) —
   ikke med en påstået procentsats uden underliggende optælling.
