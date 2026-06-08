# Cultural Entity Navigation Platform

**Live mockup:** https://ogiermontanus.github.io/hca-open-repo/

A modular web platform for exploring named entities across cultural collections — museums, libraries, archives, theaters, and film collections — through institutionally familiar navigation and semantically rich cross-linking.

## Vision

Cultural heritage is institutionally fragmented, but researchers think across boundaries. This platform preserves the recognizable structures of individual institutions while enabling semantic traversal through shared named entities (persons, places, works, events, themes).

Architecture evolves iteratively: **CSV-first → relational → semantic graph**.

## Repository Structure

```
ai-context/                   # Context files for AI coding agents and project continuity
  coding_agent_plan.md        # Technical architecture and implementation guidance
  project_memory_recap.md     # Project history, intellectual foundation, long-term vision

docs/                         # Human-facing documentation
  roadmap.md                  # Phased implementation roadmap (phases 1–5)
  data-model/                 # WEMI/FRBR rationale, relation tables, source-data conventions
  pipeline/                   # Five-stage conversion pipeline from raw register to normalized CSV
  inspiration/
    sampo-analysis.md         # Analysis of the Finnish SAMPO ecosystem as design reference

data/                         # Editorial data (raw, normalized, derived, vocabularies)
scripts/                      # Normalization, ingestion, and export scripts
schemas/                      # JSON schemas, CSV field specs, entity/relation definitions
backend/                      # API layer
frontend/                     # Web interface
tests/
```

## Key Documents

| Document | Purpose |
|---|---|
| `ai-context/coding_agent_plan.md` | Architecture, data model, tech stack, guiding principles for coding agents |
| `ai-context/project_memory_recap.md` | Origin, intellectual problem, conceptual evolution |
| `docs/roadmap.md` | Phased roadmap from data encoding through frontend prototype |
| `docs/inspiration/sampo-analysis.md` | UI/UX patterns drawn from the Finnish SAMPO portals |
| `docs/inspiration/query-builder-survey.md` | Survey of open-source query-builder modules (GLAM/SAMPO, SPARQL/SQL GUIs, relational, library APIs) with ranked picks for Phase A and Phase B |
| `docs/data-model/star-schema.md` | Star-schema target — dimensions, facts, the Power Pivot MVP, and the road to a Postgres warehouse |
| `docs/data-model/wemi-and-relations.md` | Work / Expression boundary, alias vs. relation, hybrid relational + JSONB design |
| `docs/data-model/source-data-characteristics.md` | Printed-index conventions a parser must handle (parens, names, `se:` / `Se ogsaa:`, special tokens) |
| `docs/pipeline/stages.md` | Six-stage conversion pipeline from `raw/HCA-Repository V*.xlsx` to normalized CSVs and on to the star-schema model |

## Core Principles

- **Institution-first navigation**: users enter through familiar cultural institutions, not abstract ontology
- **Entity-centered semantics**: named entities are the connective layer beneath the institutional surface
- **Gradual enrichment**: start CSV-simple, evolve toward graph-oriented infrastructure
- **AI-assisted development**: repository and documentation are designed for collaboration with coding agents
