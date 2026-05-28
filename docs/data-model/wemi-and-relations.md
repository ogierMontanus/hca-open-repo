# WEMI, aliases, and work-to-work relations

How the project decides when a derivative is a new Work or a new Expression, and how the two reference markers found in printed indexes (`se:` and `Se ogsaa:`) become rows in the relational model.

## The operative Work / Expression boundary

[FRBR/WEMI](https://en.wikipedia.org/wiki/Functional_Requirements_for_Bibliographic_Records) defines four levels: Work, Expression, Manifestation, Item. The boundary that matters most in practice — and the one this project applies consistently — is between Work and Expression:

> **Any version with a new named creator (translator, adapter, arranger) is treated as a new, independent Work. Expression is reserved for revised versions by the same creator.**

This is intentionally stricter than canonical FRBR. FRBR would file a translation as a new Expression of the same Work; we file it as a new Work with a `translation_of` edge back to the original. The rationale is operational: we cannot consistently judge, entry by entry, whether a translator's contribution rises to "new Work" — so we treat every named new creator as one. Expression therefore stays narrow and is used only for cases like *Agnete og Havmanden* (1834) → *Scene-Udgave* (1843), where Andersen himself revised his own text for a new platform.

### Signals in the source text

| Signal in the entry | Classification | WEMI |
|---|---|---|
| `(Oversættelse)` or `oversat af [name]` | new creator → new Work | W |
| `bearbejdet af / bearbejdet efter`, `frit bearbejdet af` | new creator → new Work | W |
| `efter [name]s Roman` / `efter [name]s Drama` | new creator → new Work | W |
| `[Title] (Scene-Udgave [year])` — same creator | realisation of same Work | E |
| `2. forøgede / reviderede Udgave` — same creator | realisation of same Work | E |
| `[N.] Opl.` (reprint, unchanged text) | new edition of same Expression | M |
| Specific physical copy with shelfmark | individual exemplar | I |

### Worked chain — Reg001138

```
En lille Heks ──translation_of──▶ Die Grille ──adaptation_of──▶ La petite Fadette
(Work, DK)                        (Work, DE)                    (Work, FR)
Recke & Aalborg                   Birch-Pfeiffer                George Sand, 1849
```

Three independent Works. Arrows mark derivation, not hierarchy. Each named creator triggers a new Work; the edge type encodes how it derives.

## Two reference markers: `se:` vs. `Se ogsaa:`

Printed register entries carry two reference forms that look similar but mean different things. In the Vol12 register they never co-occur on a single entry.

| Marker | Purpose | Maps to |
|---|---|---|
| `se:` | Pure redirect — alternative title points to the canonical entry | `alias` table |
| `Se ogsaa:` | Work-to-work relation — two independent Works are connected | `see_also` / `relation` table |

### `se:` — name authority

A `se:` entry has no descriptive body. It says "this is an alternative name; look up the canonical title instead":

```
Aamanden, se: Klokkedybet
Eventyrbogen, se: Kræblingen
Toppen og Bolden, se: Kjærestefolkene
```

Roughly half the targets are entries inside the same volume; the other half point outside it (to other volumes or to unregistered titles).

```sql
CREATE TABLE alias (
    alias_title  TEXT,
    canonical_id TEXT REFERENCES record(id)
);
```

### `Se ogsaa:` — work-to-work relation

A `Se ogsaa:` entry is a full standard entry that *also* points to a related independent Work. The register does not state the relation type; it must be inferred from the body of the entry (`RegistryTitle`). Three sub-types occur:

1. **Translation → original** (one-way): *Dronningen paa 16 Aar* (Danish translation) → *Die Königin von 16 Jahre* (original). The original may not have its own entry — model as a stub.
2. **Adaptation ↔ source** (two-way): Reg001138 *En lille Heks* and Reg000881 *Die Grille* each carry a `Se ogsaa:` pointing at the other. Both edges are recorded; direction is read from the entry body.
3. **Parallel titles, same play, multiple languages** (multi-way): *Bagtalelsens Skole*, *Die Lästerschule*, *School for Scandal* all cross-reference each other. Three independent Works sharing one intellectual source.

### Two-step population

Adopt an untyped `see_also` table first, then promote typed edges into `relation` as text-pattern markers are extracted:

```sql
-- Step 1: untyped, populated directly from SeeAlsoTittle
CREATE TABLE see_also (
    from_id TEXT REFERENCES record(id),
    to_id   TEXT REFERENCES record(id)
);

-- Step 2: typed edges, promoted when RegistryTitle makes the type explicit
CREATE TABLE relation (
    from_id       TEXT REFERENCES record(id),
    to_id         TEXT REFERENCES record(id),
    relation_type TEXT,           -- 'translation_of' | 'adaptation_of' | 'part_of'
    note          TEXT
);
```

| Marker in `RegistryTitle` | `relation_type` |
|---|---|
| `(Oversættelse)` / `oversat af` | `translation_of` |
| `bearbejdet efter` / `frit bearbejdet af` / `efter [x]s Roman` | `adaptation_of` |
| No marker (parallel titles, language variants) | stays in `see_also` untyped |

### Rule: no shortcut edges

Indirectly linked nodes (e.g. a Danish play C derived from a French novel D via a German adaptation E) must **not** carry a direct C → D edge. Store only the two real edges (C → E adaptation, E → D translation) and surface the chain via a query when the UI needs it.

### When does the type matter?

- **Untyped is enough** for search and display ("show everything related to *Die Grille*").
- **Typed is required** for graph traversal across Works ("find every Danish play that, through some chain, derives from a French novel").
- **Typed is mandatory** for Linked Open Data export, where `wdt:P144` (based on) ≠ `wdt:P941` (inspired by) ≠ `wdt:P4969` (derivative work).

## Hybrid relational + JSONB design

Register entries are heterogeneous: most have a creator, but only some carry `opus`, `incipit`, `adapted_from`, `ultimate_source`, etc. Two design extremes both lose: a fully normalised 3NF schema leaves most rows mostly NULL; a single JSONB blob throws away the columns we actually search on.

The recommended position is hybrid — core searchable fields as real columns, heterogeneous descriptive fields in a `JSONB` payload, relation edges as their own normalised tables.

```sql
CREATE TABLE record (
    id             TEXT PRIMARY KEY,       -- PKRegistryTitelID
    registry_title TEXT NOT NULL,          -- always preserve the original
    main_title     TEXT,                   -- searched frequently → column
    creator        TEXT,                   -- searched frequently → column
    post_type      TEXT,                   -- 'standardpost' | 'krydshenvisning'
    is_expression  BOOLEAN DEFAULT FALSE,
    expression_of  TEXT REFERENCES record(id),
    is_stub        BOOLEAN DEFAULT FALSE,
    parsed_fields  JSONB                   -- creator_note, opus, adapted_from,
                                           -- incipit, ultimate_source, ...
);

CREATE INDEX idx_record_main_title ON record (main_title);
CREATE INDEX idx_record_parsed     ON record USING GIN (parsed_fields);
```

Why this split:

| Field type | Goes in column | Goes in JSONB | Goes in own table |
|---|---|---|---|
| Always present, frequently filtered | ✓ | | |
| Sparse, varies by register type | | ✓ | |
| Graph edge (work-to-work) | | | ✓ (`relation`) |

JSONB cannot answer multi-hop traversal queries efficiently — that is exactly what `relation` is for.

### JSONB payload — Reg001138

```json
{
  "creator_note":            "bearbejdet efter en tysk Dramatisering",
  "adapted_from":            "Die Grille",
  "adapted_from_type":       "tysk Dramatisering",
  "ultimate_source":         "La petite Fadette",
  "ultimate_source_creator": "George Sand",
  "Se_ogsaa":                "Die Grille"
}
```

`main_title` and `creator` for the same row sit in the relational columns; everything register-specific sits in the payload.

## How this maps onto the current CSV layer

The CSV-first form documented in [`ai-context/coding_agent_plan.md`](../../ai-context/coding_agent_plan.md) §4 (`entities.csv`, `references.csv`) is the input to this model, not a replacement for it. As the schema evolves toward relational storage:

- `entities.csv` rows become `record` rows. Most current columns map to `record` columns; the long tail of register-specific fields gets folded into `parsed_fields`.
- `se:` redirects discovered during parsing populate `alias`.
- `Se ogsaa:` mentions populate `see_also` first, with typed edges promoted into `relation` once the source marker is recognised.
- Stub records are created for cross-references whose target is not yet in the dataset; they carry `is_stub = TRUE` and are filled in when the target register is parsed.

## Parsing rules summarised

1. Title is the first token before the first parenthesis.
2. First parenthetical block usually contains the creator(s); split at the comma if it carries `bearbejdet efter` / `oversat af`.
3. Guillemets `»...«` always mark a title — source work or incipit; context decides which.
4. `af [Name]s [genre]` identifies the source work's creator and genre.
5. `- Se ogsaa:` at the tail of the entry is a work-to-work relation; content after the colon is the `Se_ogsaa` field.
6. `(Oversættelse)` → `translation_of`. `bearbejdet efter` → `adaptation_of`.
7. `se:` without "ogsaa" is a pure cross-reference; the entry is an alias, not a `record`.
8. When ambiguous: **ask, do not guess**.
9. After every parsing run, review for structural violations: opus embedded in a title, creator embedded in a `part_of`, folk descriptor placed as `original_title`, etc.
