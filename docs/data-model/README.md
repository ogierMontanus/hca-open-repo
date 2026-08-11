# Data model

Methodology notes for the entity-centred data model used by this project. These documents distill the conventions developed against the H.C. Andersen diary registers and translate them into a form usable across the wider cultural-entity platform.

The current core schema (tables, fields, relationship vocabulary) lives in [`ai-context/coding_agent_plan.md`](../../ai-context/coding_agent_plan.md) §4. The docs in this folder explain the **rationale** behind it: why Works and Expressions are split the way they are, how the printed-index conventions encode relations, and how to extend the schema when new register types arrive.

## Documents

| File | Purpose |
|---|---|
| [`star-schema.md`](star-schema.md) | Dimensions + facts target model, Power Query / Power Pivot MVP, evolution path from the current CSV layer to the eventual PostgreSQL warehouse |
| [`october-pipeline.md`](october-pipeline.md) | Proposed end-to-end CSV + JSON pipeline for the October mockup — automated `raw/*.xlsx` → `data/normalized/*.csv` → `web/data/*.json` → static site, no SQL/SQLite |
| [`wemi-and-relations.md`](wemi-and-relations.md) | Work / Expression / Manifestation / Item boundary; how `se:` and `Se ogsaa:` markers in printed indexes map to alias and relation tables; the hybrid relational + JSONB design for heterogeneous parsed fields |
| [`source-data-characteristics.md`](source-data-characteristics.md) | How a printed-index entry is structured — parentheses as primary separator, name conventions, multilingual titles, special tokens (`Ͻ:`, `[...]`, guillemets) — with worked examples |
| [`source-field-audit.md`](source-field-audit.md) | Column-by-column fill rates and surfacing status for every field in the three normalized CSVs — spots data that is collected but never shown |
| [`temporal-modelling.md`](temporal-modelling.md) | Entity dates vs. mention dates — why the two date families must be kept separate, and how that distinction flows through filtering, timelines, search, and entity pages |
| [`place-toponymy.md`](place-toponymy.md) | Planned: historical place spellings (e.g. *Sverrig*, *Kjøbenhavn*) and modern Danish aliases (e.g. *USA* for *Amerika (de forenede Stater)*) — schema, UI behaviour, and data sources for the `place_alias` table |
| [`place-typology.md`](place-typology.md) | **Draft, awaiting editorial sign-off.** Proposed 11-category place-type taxonomy for `data/raw/SV14_places.xml` (481 places), derived bottom-up from place names and the existing GeoNames-derived `type` field rather than imposed top-down — with borderline cases and known bad GeoNames matches flagged before any GeoNames Feature Class/Code mapping is attempted |
| [`v0.92-structural-diff.md`](v0.92-structural-diff.md) | Structural diff V0.82 → V0.92 — what changed when the source moved from one workbook to nine (Power Query · FactDim · StarSchema), per-file sheet inventory, and what the pipeline needs in response |

## Audience

Curators reading raw register entries; coding agents porting parsers; anyone deciding how to extend `entities.csv` or the relation vocabulary.
