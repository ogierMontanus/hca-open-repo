# Pipeline stages

Five stages take a printed register from `raw/` to the normalised CSVs in `data/normalized/`. Each stage has an explicit input, an explicit output, and a small set of constraints that hold across the whole pipeline.

## Cross-cutting constraints

These apply at every stage:

- **UTF-8 throughout.** Source workbooks, intermediate TSVs, and final CSVs are all UTF-8 (no BOM).
- **Original order is reconstructable.** The printed-index ordering carries editorial meaning. Stages either preserve row order or carry a `sequence` / `BookSeqNo` column that lets it be restored.
- **Original data is never lost, only supplemented.** Cleaning produces new columns; it does not overwrite the source. Every transformation must be reversible to the raw entry it came from.
- **Transformations are traceable.** Each parsed row keeps `RegistryTitelID` (`PKRegistryTitelID` in the workbook) as its provenance pointer.
- **Ambiguity is escalated, not guessed.** When a parenthetical or relation marker has more than one plausible classification, parsers flag the row for review.

## Stage 1 — Slice

**Input:** `raw/HCA-Repository V*.xlsx` (highest available version).

**Output:** an in-memory 2-column list — `(RegistryTitle, PKRegistryTitelID)` — filtered to one register section.

The canonical workbook contains every register in a single `Registry` sheet, classified by `RegistryCategory (H1)` / `WorRegSubCat.WorkGenre (H2)` / `WorRegSubCat.RegistryForm (H3)` / `WorRegSubCat.WorkSubForm (H4)`. Stage 1 selects the slice that matches a particular parser's register type (music, novels-plays-tales, non-fiction, etc.).

Implementation: `resolve_ground_truth_xlsx()` and `load_registry_slice()` in `scripts/parsers/_common.py`.

## Stage 2 — Parse

**Input:** the 2-column slice from Stage 1.

**Output:** a structured TSV with register-specific columns, written to a path of the caller's choosing (typically next to the parser).

Each parser is genre-specific because the parenthetical conventions and relevant fields differ:

| Parser | Slice | Output columns (highlights) |
|---|---|---|
| `parse_music_register.py` | `MUSIK / Vokal- og Instrumentalmusik` | main_title, incipit, original_title, creator, opus, part_of, Krydshenvisning_til, Note |
| `parse_novels_plays_tales.py` | `ANDRE FORFATTERE / Romaner, Noveller, Eventyr` | main_title, original_title, creator, part_of, Se_ogsaa, Krydshenvisning_til, cited_directly, Note |
| `parse_non_fiction.py` | `ANDRE FORFATTERE / Faglitteratur` | main_title, pseudonym, creator, translator, source, Se_ogsaa, Krydshenvisning_til, uncertain_citation, Note |

The parsing logic (parenthetical extraction, classification, cross-reference detection) is preserved from the earlier `data-cleaning` workshop; the I/O layer has been refactored to read directly from the canonical workbook.

See [`docs/data-model/source-data-characteristics.md`](../data-model/source-data-characteristics.md) for the parenthetical conventions every parser respects.

## Stage 3 — OpenRefine review (optional, manual)

**Input:** TSV from Stage 2.

**Output:** the same TSV with cleaning history applied.

OpenRefine is the curation tool for human-in-the-loop normalisation: clustering near-duplicates, reconciling person names against VIAF / Wikidata, splitting compound fields that the parser left atomic, fixing rows the parser flagged as ambiguous. Every original column is duplicated before transformation so the raw value survives.

This stage is optional: simple registers may go straight from Stage 2 to Stage 4. It is recorded here because it is part of the documented workflow for entries that need authority reconciliation.

## Stage 4 — Normalize to entity-centric CSVs

**Input:** one or more parsed/curated TSVs.

**Output:** `data/normalized/entities.csv`, `data/normalized/diary.csv`, `data/normalized/references.csv`.

`scripts/normalization/hca_xlsx_to_csv.py` consumes the canonical workbook plus parsed register slices and produces the three CSVs that the rest of the platform consumes. The output schema is documented in [`ai-context/coding_agent_plan.md`](../../ai-context/coding_agent_plan.md) §4.

This is the canonical handoff between the pipeline and the application: anything downstream (frontend, backend API, search index, graph build) reads from these files.

## Stage 5 — Optional Postgres load

**Input:** the three normalised CSVs from Stage 4.

**Output:** populated `record`, `alias`, `see_also`, and `relation` tables in a PostgreSQL database.

Recommended schema in [`docs/data-model/wemi-and-relations.md`](../data-model/wemi-and-relations.md). The CSVs are the canonical form; the database is a derived artifact that supports graph traversal and full-text search beyond what CSV can answer.

## Stage extension: language tagging

`scripts/parsers/add_language_column.py` runs on any Stage-2 output and appends `probable_language` (ISO 639-1) and `language_confidence` columns. It uses `lingua-language-detector`, which is designed for short texts like titles. The language column drives downstream OPAC routing (REX/KB, DNB, BnF, BL, Libris, etc.).

The detector is restricted to the languages that appear in the registers: da, de, fr, en, sv, nl, it, la, es, pt, nb (the last is remapped to da; written Bokmål and Danish are near-identical for cataloguing purposes). Rows with `language_confidence < 0.35` are flagged for manual review.
