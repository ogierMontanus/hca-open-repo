
# Coding-Agent-Oriented Implementation Plan
## Cultural Entity Navigation Platform

> **Related methodology docs:** see [`docs/data-model/`](../docs/data-model/) for the WEMI/FRBR rationale behind the entity schema, the printed-index conventions parsers must handle, and the star-schema target (dimensions + facts) that supersedes the simple CSV layer described in §4. The conversion pipeline from `raw/HCA-Repository V*.xlsx` to the normalised CSVs and on to the Power Pivot MVP is in [`docs/pipeline/`](../docs/pipeline/).
>
> **Model evolution direction (per 2026-06-01 meeting):** CSV-first → **dimensions + facts (star schema)** → graph layer. The Power Query / Power Pivot model in Excel is the current MVP — embedded directly in the highest-versioned `raw/HCA-Repository V*.xlsx`. It validates the schema at full data scale before any web-stack investment. "Data quality before interface" — a smart frontend cannot rescue a weak grounding.
>
> **Web-facing target (per 2026-06-02 planning):** a very thin layer between data and presentation. The API exposes the star schema close to its physical shape; avoid heavy ORM / domain layers while the data model is still stabilising. First demo entity is **Places**.

# 1. Primary Objective

Build a modular web platform for exploring named entities across cultural collections.

The platform must:
- preserve institutional browsing structures;
- support semantic cross-linking;
- remain compatible with lightweight editorial workflows;
- and permit future migration toward graph-oriented infrastructures.

The implementation should initially prioritize:
- clarity;
- modularity;
- CSV compatibility;
- faceted browsing;
- read-only exploration.

---

# 2. Core Architectural Principle

The system has two simultaneous structures.

## 2.1 Visible Structure
Human-facing hierarchical navigation:

Institution
→ Media Type
→ Collection
→ Work
→ Entity references

Examples:
Gallery → Painting → Danish Golden Age → Artwork

Library → Diaries → Travel Journals → Entry

Theater → Opera → Production

---

## 2.2 Underlying Structure
Entity-centered semantic graph.

Core entities:
- Person
- Place
- Work
- Institution
- Event
- Theme
- Motif
- Historical period

Relationship examples:
- depicts
- mentions
- adapts
- performed_at
- created_by
- located_in
- inspired_by

---

# 3. Recommended MVP Scope

The MVP should avoid full semantic complexity.

Focus on:
- faceted browsing;
- entity pages;
- linked references;
- institution/media hierarchy;
- timeline filtering;
- search.

Avoid initially:
- inferencing;
- AI querying;
- complex ontology frameworks;
- automated semantic reconciliation.

---

# 4. Recommended Data Model

## 4.1 Core Tables

### institutions.csv
Fields:
- institution_id
- name
- institution_type
- country
- city
- website

---

### collections.csv
Fields:
- collection_id
- institution_id
- name
- collection_type

---

### works.csv
Fields:
- work_id
- title
- work_type
- creator_id
- date_start
- date_end
- collection_id
- description

---

### entities.csv
Fields:
- entity_id
- entity_type
- label
- birth_year
- death_year
- nationality
- authority_links

---

### references.csv
Join table connecting works and entities.

Fields:
- reference_id
- work_id
- entity_id
- relationship_type
- confidence
- note

---

### places.csv
Fields:
- place_id
- name
- country
- region
- coordinates

---

### timelines.csv
Optional temporal aggregation layer.

---

### entity_event.csv
Structured representation of dates that belong to an entity's own life
cycle, replacing the flat `birth_year` / `death_year` / `date_start` /
`date_end` columns once dual chronology (§11) is wired. See
[`docs/data-model/temporal-modelling.md`](../docs/data-model/temporal-modelling.md)
for the rationale and the mapping from today's `year_derived` /
`date_derived` columns.

Fields:
- event_id
- entity_id
- event_type   (birth · death · publication · reprint · composition ·
                premiere · performance · creation · exhibition ·
                foundation · closure · …)
- date_start   (ISO-8601; day / month / year precision)
- date_end     (equals date_start for point events)
- precision    (day · month · year · decade · century)
- source       (short citation, optional)

Mention dates (when Andersen referred to the entity) do **not** live in
this table. They are already represented by joins between
`references.csv` and a date-bearing source table (today `diary.csv`;
future `almanac.csv`, `notebook.csv`, `letter.csv`).

---

# 5. Frontend Navigation Model

## Homepage

Main entry blocks:
- Galleries
- Libraries
- Archives
- Theater
- Film
- Music
- Named Entities
- Timeline Explorer
- Map Explorer

---

# 6. Institution Pages

Institution pages should expose:
- metadata;
- collections;
- filters;
- related entities;
- media types.

Example:
Museum page
→ Painting
→ Sculpture
→ Photography

---

# 7. Media-Type Pages

Each media type supports:
- filtering;
- timeline browsing;
- artist filtering;
- thematic filtering.

Example filters:
- movement;
- period;
- geography;
- subject;
- creator;
- depicted entity.

---

# 8. Entity Pages

Entity pages are central aggregation nodes.

Required sections:
- metadata;
- biography summary;
- related works;
- institutions;
- timeline;
- geographic relations;
- network relations.

The entity page is effectively the semantic hub.

---

# 9. Filtering Requirements

Required facets:
- institution
- collection
- medium
- creator
- entity type
- nationality
- geography
- date range
- movement
- theme
- relationship type

Filters must be combinable.

## 9.1 ⚠ Attention point — creator as a top-level work filter (high priority)

**Status today.** Works on `bibliotek.html`, `billedkunst.html` and
`teater-musik.html` can be filtered live by **title genre (H2)** and
**form (H3)** only — see §9 wiring landed in the previous pass.
The **creator** (author · composer · painter · sculptor · illustrator)
is *not* a filter. It is visible only as a passive text line on each
work card and as a small "Komponist / Forfatter (top)" decorative
chip group on `teater-musik.html`. The same is true on the other wing
landing pages where a similar co-occurring-persons block appears.

**Why this matters.** A reader exploring the register is more often
asking *"what does Andersen reference by Shakespeare / Mozart /
Thorvaldsen?"* than *"which other persons co-appear on the same diary
page as this work?"* The co-occurrence facet (top persons that share
a diary page with the work) is **markedly less relevant** for works
than the structured creator. Promote creator; demote the
co-occurrence sidebar group.

**What we have in the data already.**

- `entities.PersonDerived` (Excel `PersonDerived` column) — populated
  for **1,391 / 3,708 work rows (37.4 %)** — but biased toward
  *illustrators and editors* (V. Pedersen, Lorenz Frølich, Erik Dal),
  not primary creators.
- `WORKS_EXTRA.author` (parser output of
  `scripts/build_mockup/build_works_extra.py`) — populated for
  **2,889 / 3,708 (77.9 %)**, parsed from the title parenthetical.
  Per H2 bucket:
  - H. C. ANDERSEN — **100 %** (the author is HCA himself)
  - ANDRE FORFATTERE — **100 %** *but* 880 fall through to the literal
    H2 string "ANDRE FORFATTERE" because the parser couldn't extract
    an individual author. Real distinct-author resolution is ≈ 43 %
    of the bucket.
  - MUSIK — **68 %** (Bournonville, Auber, Scribe, Heiberg …)
  - BILLEDKUNST — **29 %** (Raphael, Thorvaldsen, Bissen are
    extracted; the rest sit unparsed in the title)

**What needs to happen, in sequence.**

1. **Improve creator extraction in `build_works_extra.py`.** Lift
   the 880 ANDRE FORFATTERE fallthroughs and the 71 % gap on
   BILLEDKUNST by widening the parenthetical regex to handle
   "(Painter)", "(Sculptor, 1820)", "(Komponeret af X)", "efter X",
   "af X" and similar patterns. Cross-check the result against
   `PersonDerived` where both exist — when they disagree, prefer the
   parsed primary creator (PersonDerived is the illustrator/editor).
2. **Add `creator_role`** alongside `author` so the data carries
   *author · composer · painter · sculptor · illustrator* instead of
   collapsing them. Drives the facet labels per H2 bucket
   ("Komponist" on Musik, "Maler" on Billedkunst, "Forfatter" on
   Bibliotek). This aligns with the §11 entity-type-aware-labels rule.
3. **Promote creator to a top-level facet** in
   `js/category-catalogue.js`. Add a "Creator" facet group above
   "Form (H3)" on bibliotek, billedkunst and teater-musik —
   populated dynamically from the distinct authors in the current
   wing (top N by reference count, with a typeahead box for the
   long tail). Same OR-within-group / AND-across-groups predicate
   model the H2/H3 facets already use.
4. **Demote the "Komponist / Forfatter (top)" / co-occurring-persons
   facet** to a secondary "Mere kontekst" expander, or remove it
   from the wing landing pages entirely. Co-occurrence remains
   useful on per-place / per-person detail pages (mention-density
   data); it just doesn't belong as a peer of the structured creator
   filter on a *work* listing.
5. **Match the H2/H3 wiring already in place.** Each new "Creator"
   checkbox carries `data-author="<exact WORKS_EXTRA.author value>"`
   (and optionally `data-creator-role="…"` once role is structured).
   The catalogue reads it the same way as `data-h2` / `data-h3` via
   `readFacetGroups()`.

---

# 10. Search Requirements

Support:
- full-text keyword search;
- faceted narrowing;
- direct entity lookup;
- autocomplete.

The search layer should tolerate incomplete metadata.

---

# 11. Timeline Features

Time navigation is mandatory.

Support:
- year;
- ranges;
- historical periods;
- chronology views.

Potential future:
interactive timelines.

## 11.1 Two date families

Every temporal control operates on one of two top-level families. They
are never silently merged. See
[`docs/data-model/temporal-modelling.md`](../docs/data-model/temporal-modelling.md)
for the conceptual model.

- **Entity Dates** — events in the life cycle of the entity itself
  (birth/death, publication/reprint, composition/premiere/performance,
  creation/exhibition, foundation/closure). Subtype detail is preserved
  internally but exposed under one grouped "Entity Dates" concept in the
  primary UI.
- **Mention Dates** — when Andersen referred to the entity (diary today;
  almanacs, notebooks, letters in future). Independent of the entity's
  own chronology; queryable as first-class data.

A book published in 1820 may be mentioned in 1860; a person born in 1780
may be mentioned in 1855. The two questions must be answered
independently.

## 11.2 Required UI behaviour

1. **Temporal-mode selector.** Wherever a date filter, slider,
   histogram, timeline, or facet appears, a control selects which
   family is active. The active family is always visible to the reader.
2. **Explicit default.** The default mode is stated, not implicit.
   Switching mode updates URL/state so a shared link reproduces the
   same view.
3. **Entity-type-aware labels.** When `entity_dates` is active, labels
   match the entity type:
   - Person → Født · Død
   - Book → Udgivet · Genoptryk
   - Theatre / opera / ballet → Premiere · Opførelse
   - Painting / sculpture → Skabt · Udstillet
   - Institution → Stiftet · Lukket
   - Place → optional historical dates
   Mention-date labels stay constant ("Omtalt").
4. **Grouped exposure, typed storage.** Internally preserve the
   detailed `event_type`; group it under "Entity Dates" in the primary
   UI. Advanced query (Sampo-style query builder) may still pivot on
   typed events.
5. **Entity cards and detail pages.** Show entity-specific dates
   first (Født, Udgivet, Premiere …), then a separate mention
   chronology block. Never mix them in the same line.
6. **Timelines support independent layers.** Components are designed
   from the outset for two layers: an entity timeline and a mention
   timeline, switchable, with a future combined overlay.
7. **Search facets disambiguate.** Date facets and search filters say
   which category they are using (`Født: 1805`, `Mentioned: 1844–1848`).
   A reader is never left uncertain whether a year refers to the entity
   or to Andersen's reference to it.
8. **Mention dates are first-class.** Treat them as queryable temporal
   data, not annotations attached to entity events. Mention histograms,
   density-by-year, and per-source breakdowns are valid analytics on
   their own.

## 11.3 Underlying architecture

The schema must distinguish:

- entity type (person, place, work)
- entity subtype (book, theatre, painting, …) — drives event-label set
- entity event dates → `entity_event` table (see §4 and
  [`docs/data-model/temporal-modelling.md`](../docs/data-model/temporal-modelling.md))
- mention dates → `references.csv ⋈ diary.csv` (and future
  almanac/notebook/letter join tables)

This is likely to become a core organising principle of the diary-index
UI because it separates the chronology of the world being described
from the chronology of Andersen's observation and recording of that
world.

## 11.4 Deferred — "Datokategori" UI toggle (printed works first)

The "Datokategori" facet group (Omtaledatoer · Begivenhedsdatoer) is
**hidden site-wide** until the `entity_event` table is populated.
First implementation target is the **printed-works wing** (`bibliotek.html`):
each book has structured `publication` / `reprint` events derivable from
`year_derived` / `date_derived` and the parenthetical of `entities.label`,
so it is the cheapest place to bring the second family online. The
hidden UI elements in `places.html`, `billedkunst.html`,
`teater-musik.html`, `diaries.html`, `romaner.html` and on `bibliotek.html`
itself stay in the HTML (style `display:none`) so re-enabling on each page
is a one-line change once its event source is ready.

---

# 12. Geographic Features

Geographic layers should support:
- place pages;
- map filtering;
- travel routes;
- production locations;
- depiction locations.

Future compatibility with GIS layers is desirable.

## 12.1 Alternative place forms (planned)

The place register inherits nineteenth-century Danish orthography. A reader
searching for the modern form (*Sverige*, *USA*, *København*) must still find
the entry whose canonical label is the historical form (*Sverrig*, *Amerika
(de forenede Stater)*, *Kjøbenhavn*).

A `place_alias` table — modelled on the `alias` table in
[`docs/data-model/wemi-and-relations.md`](../docs/data-model/wemi-and-relations.md)
— captures `alias_label → canonical place_id` mappings tagged by
`alias_type` (historical spelling · modern abbreviation · modern name ·
exonym · translation). The canonical register label is never overwritten;
the modern form is surfaced as a secondary line on the place card and
unioned into the search index.

Schema, UI rules, and data sources (curated CSV first, Wikidata `altLabel`
second) are in
[`docs/data-model/place-toponymy.md`](../docs/data-model/place-toponymy.md).

---

# 13. UI/UX Philosophy

The interface should prioritize:
- exploratory browsing;
- discoverability;
- low cognitive load;
- progressive disclosure;
- minimal clicks.

The system should feel:
- visually institutional;
- semantically interconnected.

## 13.1 Deferred — grid (Gitter) layout (illustrations dependency)

The result-page layout switcher previously offered **Liste** (list) and
**Gitter** (grid) views. The Gitter button has been removed: a grid view
of mostly-textual register entries adds visual noise without adding
information. Grid layout becomes useful only when cards carry
illustrations — works that have a thumbnail (painting, sculpture, book
cover, set photo), persons with a portrait, places with a representative
image.

Reinstating Gitter is therefore gated on an editorial image pipeline:
sourcing, rights-clearing, and attaching one illustration per
register entry, across ~16,000 entries. The effort is comparable to
the planned geocoordinate pass for places (§12) — both are large
editorial+reconciliation passes against external sources (Wikidata
P18 for images, Wikidata P625 / GeoNames for coordinates).

When images do land, the switcher returns with three states:
**Liste · Gitter · Tidslinje** (the Tidslinje option is already
present on `diaries.html` as a placeholder).

---

# 14. Recommended Technical Stack

## MVP
Possible stack:
- static frontend framework;
- lightweight backend API;
- CSV ingestion pipeline;
- SQLite or Postgres;
- faceted search index.

Potential technologies:
- Next.js
- Astro
- SvelteKit
- FastAPI
- SQLite/Postgres
- Typesense/Meilisearch

---

# 15. Data Pipeline

Recommended ingestion flow:

CSV/Excel
→ normalization scripts
→ joined tables
→ API layer
→ frontend rendering

Editorial work remains external to production database.

## 15.0 ⚠ Attention point — V0.92 source structure shift

The source has moved from a single `HCA-Repository V0.82.xlsx`
workbook to a **nine-file folder** at
`data/raw/HCA REPOSITORY V0.92/`, organised by domain (Calendar,
Person, Location, Diary) and by processing stage (`-PQ-`
semi-raw · `DiaryFactDim-PQ-` fact+dim extract · `-PP-`
StarSchema Power Pivot model). Star-schema modelling that was
target-state in `docs/data-model/star-schema.md` is now *shipped*
state. Full per-file sheet inventory and the V0.82 → V0.92 diff are
in [`docs/data-model/v0.92-structural-diff.md`](../docs/data-model/v0.92-structural-diff.md).

Highest-priority follow-ups:

1. **V0.92 covers Persons / Places / Calendar / Diaries only** —
   not Works. The pipeline must run dual-source until the works
   register ships in V0.9x: persons + places + diaries from V0.92,
   works still from V0.82.
2. **`scripts/normalization/hca_xlsx_to_csv.py` is single-file
   V0.82-shaped.** A V0.92 sibling `hca_v092_to_csv.py` now exists
   and emits `data/normalized_v092/{entities,diary,references}.csv`
   — see `data/normalized_v092/README.md` for the schema map.
3. **`FactDiaLocPerPag` (92,307 rows)** is the authoritative
   person × place × diary-page co-occurrence grain. Replaces
   `scripts/build_mockup/build_cooccurrence.py` for the V0.92 slice.
4. **`Raw.See-Also` in `LocationData-PQ-V0.92.xlsx` (85 rows)**
   structures the cross-references that V0.82 left inline in
   `RegistryTitle` — partially closes the §15.1 gap for places. The
   §15.1 attention point should be re-scoped to *persons* once a
   person-side `Raw.See-Also` ships.

## 15.1 Attention point — inline `se:` cross-references (deferred)

The Excel master sheet (`raw/HCA-Repository V*.xlsx`) has dedicated
`SeeTitle` / `SeeAlsoTittle` columns. The normalizer copies these
verbatim into `entities.see` / `entities.see_also`.

The coverage split is uneven:

- **Works (118 inline `se:` markers):** 117 also have `SeeTitle`
  populated — the parser already captures the link. ✓
- **Persons (385) and places (76) — 461 entries:** `SeeTitle` is
  empty in Excel. The cross-reference exists *only* inside the
  `RegistryTitle` string (e.g. Reg0081650 *"L, Frue, se: Læssøe,
  Signe."*). The Python script does not yet recover it. ✗

Implementation sketch: when `SeeTitle` is empty, match
`RegistryTitle` against `^(?P<alias>.+?),\s*\n?\s*se:\s*(?P<target>.+?)\.?\s*$`
and lift `target` into `see`; the alias becomes the entry's `label`.
Resolve `target` to an `entity_id` with the head-label + whole-word
prefix matcher already used by `scripts/build_mockup/
build_works_extra.py:resolve_ref()`. See
[`docs/data-model/source-field-audit.md`](../docs/data-model/source-field-audit.md#inline-se-cross-references)
for the full proposal.

This sits next to but is **separate from** the planned `place_alias`
work (§12.1 / [`place-toponymy.md`](../docs/data-model/place-toponymy.md)):
that one captures *new* modern-spelling aliases (USA, Sverige,
København) that the register does not already record. This section
covers *existing* register aliases whose link is just stored in the
wrong column.

---

# 16. Long-Term Evolution

The architecture should permit migration toward:
- graph database backend;
- RDF/linked open data;
- Wikibase integration;
- authority reconciliation;
- AI-assisted exploration.

However:
the frontend navigation philosophy should remain stable.

---

# 17. Guiding Principle for Coding Agents

Do not over-engineer semantic infrastructure in the first implementation.

The essential value lies in:
- navigation structure;
- discoverability;
- entity aggregation;
- cross-institution traversal;
- and scalable metadata layering.

The project should evolve iteratively:
CSV-first → relational → semantic graph.
