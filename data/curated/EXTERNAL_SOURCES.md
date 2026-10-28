# Eksterne kilder — proveniens og licens

Plan: [`docs/plan-tidstavle-data.md`](../../docs/plan-tidstavle-data.md) trin 2.4.
Princip: **ingen runtime-kald** fra siden. Eksterne data hentes lokalt ved
build eller af et engangsscript og committes; CSP'en (`docs/security.md`) er
uændret. Licenser nedenfor er dem, projektet selv har noteret; kolonnen
«Verificeret» siger, hvad der er set i selve kilden — udfyld den, når en kilde
tages i brug, i stedet for at antage.

| Kilde | Hvad hentes | Hvor i repoet | Hentet | Licens (som noteret) | Kreditering | Verificeret |
|---|---|---|---|---|---|---|
| Wikidata | Q-numre + billedfilnavn for 35 værker | `data/curated/works_wikidata.csv` | 2026-08-09 (WebSearch, pr. række i `verified_via`) | CC0 | ikke krævet | pr. række, jf. `wikidata-verify` |
| Natural Earth | verdens- og Europa-kystlinjer til det offline basiskort | `mockup/vendor/basemap/` (bygget af `scripts/build_mockup/build_basemap.py`) | ved build | public domain | ikke krævet, kildelinje står på kortet | — |
| Leaflet 1.9.4, Leaflet.markercluster 1.5.3 | kortbibliotek (vendoreret, byte-identisk med unpkg-udgivelserne) | `mockup/vendor/leaflet/` | — | se `LICENSE-*.txt` ved siden af | licenstekst ligger ved | filerne i mappen |
| Det Kgl. Bibliotek, EPUB «H.C. Andersens Dagbøger» | **kun URL'er** (92 sider) — ingen indhold kopieres; linkstatus kontrolleres | `data/curated/kb_link_status.csv` (`scripts/qa/check_kb_links.py`) | 2026-10-28: 92 af 92 svarer 200 | ikke undersøgt — der hentes intet indhold, kun HEAD | linkes diskret i nyt faneblad (`docs/external-links.md`) | — |
| H.C. Andersen Centret / SDU: `hca_db.sql` | intern database (ikke et eksternt datasæt) | uden for repoet (`raw/hca_db.sql`, gitignoreret); udtræk i `data/normalized_v092/` | — | internt | — | — |
| GeoNames | **ikke hentet endnu** (plan 2.1) | — | — | CC BY — kræver kreditering på `om.html` («Vores kilder») når den tages i brug | skal tilføjes samtidig | — |
| VIAF | **ikke hentet endnu** (plan 2.1) | — | — | ikke undersøgt | — | — |

## Regler ved nye kilder

1. Ny række her *før* data committes: kilde-URL, licens, hentedato, version.
2. Licens og kreditering læses i selve kilden, ikke fra hukommelsen.
3. Wikidata/VIAF/DBpedia-oplysninger efterprøves pr. post via live opslag
   (`.claude/skills/wikidata-verify`) og får `verified_via` + dato.
4. Link-checks (som `check_kb_links.py`) er sjældne, høflige (≤ 1 request/s,
   identificerende User-Agent) og skriver kun status — aldrig indhold.
