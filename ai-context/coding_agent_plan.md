
# Coding-Agent-Oriented Implementation Plan
## Cultural Entity Navigation Platform

> **Related methodology docs:** see [`docs/data-model/`](../docs/data-model/) for the WEMI/FRBR rationale behind the entity schema, the printed-index conventions parsers must handle, and the star-schema target (dimensions + facts) that supersedes the simple CSV layer described in §4. The conversion pipeline from `raw/HCA-Repository V*.xlsx` to the normalised CSVs and on to the Power Pivot MVP is in [`docs/pipeline/`](../docs/pipeline/).
>
> **Model evolution direction (per 2026-06-01 meeting):** CSV-first → **dimensions + facts (star schema)** → graph layer. The Power Query / Power Pivot model in Excel is the current MVP; it validates the schema at full data scale before any web-stack investment. "Data quality before interface" — a smart frontend cannot rescue a weak grounding.

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

---

# 12. Geographic Features

Geographic layers should support:
- place pages;
- map filtering;
- travel routes;
- production locations;
- depiction locations.

Future compatibility with GIS layers is desirable.

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
