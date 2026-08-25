# PostgreSQL migration — draft moved to `nosql-hca-open-repo`

This repo's editorial data currently lives as CSV/Excel/TSV files
(`data/normalized/`, `data/curated/`, `data/parsed/`), described
throughout this `docs/data-model/` folder. The eventual move of that
data layer to a database is being drafted separately, in
[`nosql-hca-open-repo`](https://github.com/ogiermontanus/nosql-hca-open-repo).

That repo holds:

- `docs/data-model/postgres-schema-design.md` — the proposed normalized
  PostgreSQL schema for the Person/Work/Place registers (analysis of
  this repo's CSVs, conceptual model, `CREATE TABLE` statements,
  CSV→Postgres mapping, data-quality issues, editorial workflow, open
  questions).
- `docs/data-model/postgres-schema-design-addendum-parsed-works.md` — a
  companion addendum covering what `data/parsed/*.tsv` (still sourced
  from this repo) change in that schema.

Despite the other repo's name, the drafted schema is a normalized
**PostgreSQL** design, not NoSQL.

## What stays here

- The source CSVs/TSVs themselves — this repo remains the source of
  truth for the register data until a migration actually happens.
- [`star-schema.md`](star-schema.md) — the dimension/fact (Power Query /
  Power Pivot) analytical model. The PostgreSQL draft is designed as the
  authoritative/editable (OLTP) layer *underneath* that model, not a
  replacement for it; see `star-schema.md`'s own "Migration path" note.
- [`../pipeline/stages.md`](../pipeline/stages.md)'s "Stage 6 — Optional
  Postgres warehouse", which frames where a database fits in the
  broader conversion pipeline.

## Status

Proposal stage, not yet built. Track progress and open questions in
`nosql-hca-open-repo`.
