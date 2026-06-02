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

## Audience

Curators reading raw register entries; coding agents porting parsers; anyone deciding how to extend `entities.csv` or the relation vocabulary.
