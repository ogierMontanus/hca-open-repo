# Claude-skills i dette repo — og hvordan `wikidata-verify` kan blive tværgående

Status: note 2026-10-29 · skills ligger i `.claude/skills/<navn>/SKILL.md`

## Hvad er et «håndtag» som `/wikidata-verify`?

En **skill** er en mappe med en `SKILL.md`: en frontmatter (`name`, `description`) og en brødtekst med procedure.
Navnet i frontmatter er skillens **håndtag**:

* `/wikidata-verify` i en prompt **starter skillen på ordre** (en «slash-kommando»). Skillens tekst indlæses i
  samtalen, og Claude følger den i stedet for sin standardfremgangsmåde.
* Uden `/` kan Claude **selv vælge** skillen ud fra `description` («Use whenever assigning, checking, or citing a
  Wikidata identifier»). `description` er altså udløseren; brødteksten er proceduren.
* At *nævne* håndtaget i en besked (som her) kører ikke skillen — kun `/…` eller et bevidst kald gør.

Repoets skills (alle projekt-lokale, i `.claude/skills/`):

| Håndtag | Hvad | Hvorfor den findes |
|---|---|---|
| `wikidata-verify` | Live opslag af Wikidata/DBpedia/VIAF-ID'er før de skrives; verificerede og kendt forkerte Q-numre | 6 af 8 Q-numre gættet fra hukommelsen var forkerte (75 %) |
| `verify-fix-commit` | Genudled en «fix»-commits mekanisme mod koden, ikke mod commit-beskeden | facet-panel/iOS-fælden |
| `adversarial-review` | Fjendtlig gennemgang af en ændring | find fejl i stedet for at godkende |
| `design-sync` | Claude Design ↔ `mockup/css/style.css` | komponent-pipeline |
| `steering` | Hvor hører en instruktion hjemme (CLAUDE.md, regel, skill, hook …) | undgå at CLAUDE.md vokser |

`CLAUDE.md` henviser til `wikidata-verify` og `verify-fix-commit` som *krav* — skillen er proceduren, CLAUDE.md er
reglen om at bruge den.

## Gøre `wikidata-verify` tilgængelig i alle repos

Claude Code kender (efter min viden — **bekræft i Claude Code-dokumentationen, jeg har ikke slået det op her**) tre
placeringer: **projekt** `.claude/skills/` (følger repoet), **personlig** `~/.claude/skills/` (gælder alle dine repos
på maskinen) og **plugin** (deles med andre, versioneres). Til «på tværs af mine repos» er den personlige mappe det
enkleste; et plugin, hvis andre skal have den.

Skillen bør **splittes**, for i dag blander den procedure og HCA-data:

| Del | I dag | Tværgående version |
|---|---|---|
| Procedure (søg live, læs Q-nummer fra URL, bekræft navn + type/levetid/land, aldrig fra hukommelsen) | på dansk | på engelsk (eller tosproget), generel |
| «Kendte korrekte»/«kendt forkerte» Q-numre (Dickens, Murillo, Odense …) | indlejret i SKILL.md | **flyttes til repoet** (`data/curated/wikidata_verified.csv`) — de er projektdata, ikke procedure |
| Henvisninger til `wikidata_lookup.py`, `works_wikidata.csv` | indlejret | kun i repoets egen CLAUDE.md / tynde projekt-skill |

Foreslået model: en **generel** `wikidata-verify` (personlig/plugin) + en **tynd projektfil** i hvert repo, der siger
hvor repoets verificerede ID'er ligger. Repoets nuværende SKILL.md kan blive som den tynde del.

### Udkast til generel `SKILL.md` (engelsk, klar til `~/.claude/skills/wikidata-verify/`)

```markdown
---
name: wikidata-verify
description: Verify a Wikidata Q-number, VIAF/DBpedia/GeoNames/authority ID or other external identifier for a person, place or work BEFORE writing it to a file or presenting it. Use whenever assigning, checking or citing an external identifier — never from memory alone.
---

# External-identifier verification

Never write or cite an authority ID from memory (a past session got 6 of 8 Wikidata Q-numbers wrong).

1. Look the entity up live (web search restricted to the authority's domain, or its API).
2. Read the ID from the actual result URL/record, not from your recollection.
3. Confirm the match on SEVERAL independent facts: label, dates (born/died), type/class, country/place,
   and — for works — the specific item (collection/edition), not just the creator.
4. Keep the verdict PER ENTITY: never cache "verified" per URL/ID — relatives and namesakes share pages.
5. Record `verified_via` + date next to the ID; keep unverified guesses out of the data.
6. If the project keeps a list of verified/known-wrong IDs, read it first (the project says where).
```

## Generaliserbare erfaringer fra Lex-arbejdet (kan komme med i den tværgående skill)

Lex-opslagene (`docs/data-model/lex-dk-dbl-bucket-results.md`) fandt fejl, som gælder *alle* autoritetslinks:

* **AI-chatbots opfinder URL'er** — kun links, der optræder som kilder/kort, accepteres.
* **Verdikt pr. person, aldrig pr. URL i en cache** (slægtninge delte artikler: 51 falske bekræftelser).
* **Identitet kræver artiklens *egne* data** (metabeskrivelsen), ikke hele indledningen — forældres/børns årstal
  står også dér.
* **Værksnavne er ikke fakta** («Dansk Biografisk Leksikon» ≠ nationalitet *dansk*).
* **En artikel tilhører én person**: ved flere krav vælges den, hvis datoer står først; resten til gennemgang.
