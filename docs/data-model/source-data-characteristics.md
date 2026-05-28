# Source data characteristics

What a curator or parser needs to know about the printed-index entries that flow into this project. Every convention listed below is something a parser has to handle or a curator has to recognise; getting these wrong tends to produce silently incorrect rows.

The examples are drawn from the H.C. Andersen diary registers (volume 12 and adjacent) but the underlying patterns recur across most pre-1960 European printed indexes.

## Document structure

A printed register is an alphabetical list. Each row is one entry. An entry packs several semantic fields into a single string. The job of parsing is to split that string into atomic fields without losing information.

## Parentheses as the primary structural separator

Parenthetical content carries the bulk of an entry's structure. Inside a single set of parentheses you may find: an author name, an original-language title, a date, a venue, an adaptation note, an opus number, or a source reference.

Order is meaningful. The last parenthetical at the end of an entry is overwhelmingly the creator; an earlier parenthetical is typically the original title or container work. Parsers should walk parentheticals right-to-left and classify by content (year present? `op.` prefix? `oversat af` phrase? guillemets inside?) rather than by position alone.

A common pitfall: not every parenthetical at the end is a creator. A trailing `(1849)` is a date-source, not a person. Classify by content first.

## Names

The canonical name form is:

```
Lastname, Firstname (birth–death)
```

Examples:

- `Sand, George (1804–1876)`
- `Birch-Pfeiffer, Charlotte (1800–1868)`
- `Andersen, H. C. (1805–1875)`

Variants you will encounter:

- Date span missing — entry predates the convention, or the dates were unknown to the original editor.
- Date span uses `d. m. yyyy` (day-month-year) for individual dates rather than spans.
- Nobility names use `[First] af [Place]` (e.g. *Carl Alexander af Sachsen-Weimar-Eisenach*). The bare `af` here is **not** the relation marker `af:` and parsers must not split on it.

## Multi-language titles

Titles in Danish, German, French, Italian, Spanish, Swedish, English, Norwegian, Latin, Portuguese, and Dutch all appear, often within the same register. Parsers must not assume a single source language. Downstream, `add_language_column.py` classifies each row with `lingua-language-detector` for OPAC routing — see [`docs/pipeline/stages.md`](../pipeline/stages.md).

## Two kinds of cross-reference

Two markers carry distinct semantics. They never co-occur on the same entry.

### `se:` — pure redirect

```
Aamanden, se: Klokkedybet
Eventyrbogen, se: Kræblingen
```

The entry has no body of its own; it points at a canonical entry. Parsers emit a `krydshenvisning` post-type. Some `se:` lines are CSV-quoted across two physical lines because of an embedded comma, e.g.:

```
"Aaen, se:
Klokkedybet"
```

This is an artifact of the comma-quoting rules in the source CSV; the parser must rejoin them.

### `Se ogsaa:` — work-to-work relation

A full entry that also points to a related independent Work, e.g.:

```
Die Grille (Birch-Pfeiffer, Charlotte, bearbejdet efter George Sand) - Se ogsaa: En lille Heks.
```

The relation type (`translation_of`, `adaptation_of`, or untyped) is inferred from the body of the entry, not from the `Se ogsaa:` marker itself. See [`wemi-and-relations.md`](wemi-and-relations.md) for the full mapping.

## Special tokens

| Token | Meaning | Notes |
|---|---|---|
| `»...«` (guillemets) | Always marks a title — either an incipit (in music registers) or a source-work reference (in literary registers) | Disambiguate by context, not by the guillemets alone |
| `Ͻ:` (U+03FD) | Abbreviation for "dvs." (i.e.) — used to give the real name behind a pseudonym | Splits `Pseudonym Ͻ: Real Name` into two fields |
| `[...]` | Source reference or uncertain citation — title was inferred from context, not given verbatim | Set `uncertain_citation = True` |
| `[Ͻ: name]` | Real-name annotation embedded in a title | Move `name` to the creator field, strip the brackets from the title |
| `((` at start | Typographic error in the printed source | Normalise to a single `(` |
| `=` at start of parenthetical | Equivalence note (alternate spelling, alternative form) | Capture as `note`, not creator |
| `op. N` or `op. N nr. M` | Opus number | Extract into its own field even when embedded mid-string, e.g. `Symfoni Nr. 4, F-dur, op. 86` |

## Worked examples

### 1. Music — incipit-led entry

Source:
```
»Hvor Skoven dog er frisk og stor« (af »Hyldemoer«, J. P. E. Hartmann)
```

Parsed:
- `04_main_title` (empty — the guillemet phrase is the identifier)
- `04b_incipit` = `Hvor Skoven dog er frisk og stor`
- `08_part_of` = `af »Hyldemoer«`
- `06_creator` = `J. P. E. Hartmann`

### 2. Music — opus embedded in title

Source:
```
Symfoni Nr. 4, F-dur, op. 86 (Niels W. Gade)
```

Parsed:
- `04_main_title` = `Symfoni Nr. 4, F-dur`
- `07_opus` = `op. 86`
- `06_creator` = `Niels W. Gade`

The trailing `, op. 86` would land in the title if the parser stopped at parenthesis-extraction; the cleanup pass moves it to the opus column.

### 3. Adaptation chain — three Works

Source:
```
En lille Heks (Recke og Aalborg, bearbejdet efter en tysk Dramatisering af La petite Fadette) - Se ogsaa: Die Grille.
```

Parsed:
- `04_main_title` = `En lille Heks`
- `06_creator` = `Recke og Aalborg`
- `creator_note` = `bearbejdet efter en tysk Dramatisering`
- `adapted_from` = `Die Grille` (the German dramatisation, implicit)
- `ultimate_source` = `La petite Fadette`
- `08_Se_ogsaa` = `Die Grille`
- Relation type → `adaptation_of`

### 4. Non-fiction — pseudonym split

Source:
```
Rejseskitser fra Kreta (Elpis Melena Ͻ: Marie Esperance Schwartz) (1867)
```

Parsed:
- `04_main_title` = `Rejseskitser fra Kreta`
- `05_pseudonym` = `Elpis Melena`
- `06_creator` = `Marie Esperance Schwartz`
- `08_source` (year-bearing paren) = `1867`

### 5. Cross-reference

Source:
```
Toppen og Bolden, se: Kjærestefolkene
```

Parsed:
- `01_Posttype` = `krydshenvisning`
- `04_main_title` = `Toppen og Bolden`
- `09_Krydshenvisning_til` = `Kjærestefolkene`
- No creator, no body. Stored as `alias`, not `record`.

### 6. Uncertain citation in square brackets

Source:
```
[Klaver-Trio] (Beethoven)
```

Parsed:
- `04_main_title` = `[Klaver-Trio]`
- `11_uncertain_citation` = `True`
- `06_creator` = `Beethoven`

The bracketed form indicates the title is editorially supplied; the original text only described the piece.

## What "review every parsing run" actually means

After any parser produces a TSV, scan for structural violations before the file is considered done:

- Opus number sitting in `original_title` (clean-up pass should have moved it; if it didn't, log a row).
- Creator name embedded in `part_of` (e.g. `af: Rigoletto, G. Verdi` — should split into `part_of = "af: Rigoletto"`, `creator = "G. Verdi"`).
- Folk descriptor (`folkemelodi`, `traditional`) parked in `original_title` instead of `creator` with `creator_is_human = False`.
- Title swallowed into a `Note` because a structurally-ambiguous parenthetical was misclassified.

For ambiguous cases the rule is the same as during parsing: ask, don't guess.
