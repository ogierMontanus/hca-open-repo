# Next-Step Implementation Roadmap

## Cultural Entity Navigation Platform

This roadmap assumes the current conceptual state of the project and prepares the transition toward:

* executable prototype infrastructure;
* collaborative repository development;
* and integration with AI coding agents.

---

# Phase 1 — Encoding and Data Infrastructure

## Goal

Create a stable, machine-readable, migration-friendly editorial layer before major frontend work begins.

This phase is foundational.

---

## 1.1 Encoding Strategy

The project currently assumes:

* CSV;
* Excel;
* PowerQuery-derived joins.

The next step is to formalize encoding standards.

### Recommended Principle

Use:

* lightweight normalized tabular data;
* plus optional TEI-compatible export paths later.

Avoid:

* premature RDF complexity;
* ontology overengineering;
* excessive XML dependence during MVP stage.

---

## 1.2 Core Encoding Targets

### Entities

Normalize:

* persons;
* places;
* institutions;
* works;
* events;
* motifs/themes.

### Stable IDs

Every entity requires:

* persistent internal identifier;
* stable slug;
* optional external authority mappings.

Example:

```text
person_000123
place_000456
work_000891
```

---

## 1.3 Authority Integration

Future-compatible fields:

* VIAF
* Wikidata
* Getty ULAN
* GeoNames
* Library authority IDs

These may initially remain optional columns.

---

## 1.4 Relationship Encoding

A lightweight relationship table should be introduced early.

Example:

```csv
source_entity,target_entity,relation_type
work_001,person_009,depicts
diary_012,place_088,mentions
opera_011,work_001,adapts
```

This becomes the bridge toward later graph modeling.

---

## 1.5 Controlled Vocabularies

Introduce controlled values for:

* artwork types;
* institution types;
* relationship types;
* periods;
* genres;
* movements.

This prevents future normalization problems.

---

# Phase 2 — GitHub Repository Architecture

## Goal

Establish a repository structure explicitly designed for:

* collaborative humanities work;
* AI-assisted coding;
* reproducible builds;
* modular evolution.

---

# 2.1 Repository Philosophy

The repository should separate:

* editorial data;
* transformation scripts;
* application code;
* generated artifacts;
* documentation.

Avoid monolithic structure.

---

# 2.2 Recommended Repository Layout

```text
cultural-entity-platform/

├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── docs/
│
├── data/
│   ├── raw/
│   ├── normalized/
│   ├── derived/
│   └── vocabularies/
│
├── scripts/
│   ├── normalization/
│   ├── ingestion/
│   └── exports/
│
├── backend/
│
├── frontend/
│
├── schemas/
│
├── tests/
│
├── examples/
│
└── ai-context/
    ├── project_memory_recap.md
    ├── coding_agent_plan.md
    ├── ontology_notes.md
    └── prompts/
```

---

# 2.3 Essential Early Files

## README.md

Must explain:

* project vision;
* architecture;
* setup instructions;
* roadmap.

---

## CONTRIBUTING.md

Critical for AI-assisted collaboration.

Define:

* naming conventions;
* folder logic;
* branching workflow;
* metadata standards;
* commit message conventions.

---

## schemas/

Store:

* JSON schemas;
* CSV field specifications;
* entity definitions;
* relation vocabularies.

---

# 2.4 Git Strategy

Recommended:

* trunk-based development initially;
* feature branches later.

Suggested branches:

```text
main
dev
frontend
backend
data-model
experimental
```

---

# 2.5 Licensing

Strongly recommended:

* MIT for code;
* CC-BY or CC0 for metadata;
* explicit separation between code license and cultural datasets.

---

# Phase 3 — Integration with AI Coding Agents

## Goal

Design repository and workflows explicitly for collaboration with:

* OpenAI Codex-style systems;
* Claude Code;
* future autonomous coding agents.

This should be treated as a first-class architectural concern.

---

# 3.1 Core Principle

AI agents work best when:

* repository structure is explicit;
* conventions are stable;
* context files are centralized;
* schemas are documented;
* task boundaries are modular.

The repository should therefore become:

* machine-readable for humans;
* and human-readable for machines.

---

# 3.2 Shared AI Context Folder

Critical recommendation:

Create:

```text
/ai-context/
```

Contents:

* project summaries;
* architectural philosophy;
* glossary;
* entity model;
* terminology;
* roadmap;
* prompt templates.

This dramatically improves coding-agent continuity.

---

# 3.3 Agent Instruction Files

Recommended files:

```text
CLAUDE.md
CODEX.md
```

Purpose:

* define coding conventions;
* architectural constraints;
* preferred frameworks;
* forbidden patterns;
* workflow expectations.

---

## Example Topics

### CLAUDE.md

* avoid overengineering;
* prefer readable code;
* preserve modularity;
* maintain CSV compatibility.

### CODEX.md

* strict typing requirements;
* testing expectations;
* schema validation;
* migration rules.

---

# 3.4 Permissions and Access Control

## Recommended Setup

### Human Collaborators

Use:

* GitHub Teams;
* branch protection;
* pull-request workflow.

---

## AI Coding Agents

AI agents should:

* never push directly to `main`;
* work through feature branches or PR generation;
* require review before merge.

---

## Recommended GitHub Permissions

### Maintainers

* full write/admin

### Contributors

* write access

### AI Service Accounts

* restricted write
* PR-only workflow preferred

---

# 3.5 Repository Features to Enable

Recommended GitHub settings:

* branch protection;
* required PR reviews;
* issue templates;
* discussion boards;
* GitHub Actions;
* Dependabot;
* code owners.

---

# 3.6 GitHub Actions

Recommended early automation:

## Validation

* CSV schema validation;
* linting;
* type checks.

## Build

* frontend build checks;
* API tests.

## Documentation

* auto-generate schema docs.

---

# 3.7 AI-Agent-Friendly Documentation

Critical principle:

Every major directory should contain:

```text
README.md
```

Explaining:

* purpose;
* expected files;
* workflows;
* constraints.

AI agents perform significantly better with localized contextual documentation.

---

# Phase 4 — Shareable Colleague Artifact

## Goal

Produce a concise but high-level project introduction for collaborators.

This artifact should:

* explain vision;
* explain architecture;
* explain AI-assisted workflow;
* and reduce onboarding friction.

---

# Recommended Deliverables

## 4.1 Project Brief PDF

Contents:

* conceptual overview;
* screenshots/mockups later;
* repository structure;
* roadmap;
* institutional model;
* semantic model.

---

## 4.2 GitHub Onboarding Guide

Short collaborator guide:

* how to clone repo;
* branch workflow;
* where data lives;
* where documentation lives;
* how AI agents are integrated.

---

## 4.3 AI Collaboration Policy

Important for institutional trust.

Clarify:

* AI-generated code review expectations;
* authorship policy;
* verification requirements;
* provenance tracking.

---

# Phase 5 — Immediate Tactical Next Steps

## Recommended Order

### Step 1

Formalize encoding conventions.

Deliverables:

* entity schema;
* relation schema;
* controlled vocabularies.

---

### Step 2

Create GitHub repository.

Deliverables:

* folder structure;
* README;
* licenses;
* contribution guide.

---

### Step 3

Add AI integration layer.

Deliverables:

* `/ai-context/`
* `CLAUDE.md`
* `CODEX.md`

---

### Step 4

Build ingestion pipeline.

Deliverables:

* CSV normalization scripts;
* schema validation;
* test datasets.

---

### Step 5

Prototype frontend.

Deliverables:

* institution browsing;
* entity pages;
* filtering system;
* timeline filtering.

---

# Long-Term Strategic Direction

The project is evolving toward a hybrid between:

* cultural knowledge graph;
* semantic catalogue;
* institutional discovery platform;
* and humanities navigation engine.

The key architectural insight remains:

> Preserve recognizable cultural structures at the interface layer while enabling increasingly rich semantic interconnection underneath.


This is highly relevant inspiration for the project, both conceptually and architecturally.

The Finnish SAMPO ecosystem is probably the closest existing precedent for what this project is becoming:
a cultural-semantic navigation environment built around:

* faceted discovery,
* multiple perspectives on the same data,
* linked entities,
* and humanities-oriented exploration. ([University of Helsinki][1])

The important point is that your project differs in emphasis:
the SAMPO portals are fundamentally Linked Data / semantic-web systems first,
whereas your current project is intentionally beginning:

* CSV-first,
* institution-first,
* interface-first,
* and migration-friendly.

However, many UI and interaction ideas are directly reusable.

---

# Key SAMPO Concepts Worth Reusing

## 1. Multi-Perspective Navigation

One of the core SAMPO principles is:

> the same underlying data should be accessible from multiple perspectives. ([University of Helsinki][2])

This maps almost perfectly onto your discussions:

* institution views;
* artwork views;
* entity views;
* timeline views;
* geographic views.

This should become an explicit frontend principle.

---

# 2. The Two-Step Usage Cycle

The SAMPO portals repeatedly use a:

1. filter phase;
2. exploration/analysis phase. ([University of Helsinki][1])

This is probably the single most important UI pattern to adopt.

For your project:

## Phase A — Narrowing

User filters:

* institution;
* medium;
* time;
* geography;
* artist;
* entity type;
* themes.

## Phase B — Exploration

User explores:

* entity pages;
* relationships;
* maps;
* timelines;
* networks;
* contextual collections.

This aligns extremely well with your existing discussions.

---

# 3. Faceted Search Interface

The SAMPO systems are heavily facet-driven. ([University of Helsinki][1])

This is probably the strongest reusable frontend pattern.

You should strongly study:

* dynamic filter panels;
* cascading facets;
* contextual result counts;
* multi-select filtering;
* narrowing workflows.

Your own discussions already repeatedly emphasized:

* hierarchical narrowing;
* avoiding gigantic lists;
* progressive refinement.

The SAMPO model validates this approach.

---

# 4. “Multiple Perspectives” as UI Tabs

The SAMPO portals often expose:

* maps;
* timelines;
* network graphs;
* tables;
* statistics;
* biographies;
* linked objects.

All derived from the same filtered subset.

This is extremely important for your architecture.

A user should filter once, then switch between:

* gallery mode;
* map mode;
* timeline mode;
* network mode;
* entity mode.

This becomes a major frontend principle.

---

# 5. Entity-Centered Pages

BiographySampo, BookSampo, and related portals demonstrate strong aggregation pages around entities. ([University of Helsinki][2])

This is directly compatible with your ideas about:

* persons;
* places;
* institutions;
* works;
* themes.

The important reusable idea:

* the entity page acts as a semantic hub.

---

# 6. Linked but Institutionally Distinct Data

A major SAMPO insight:
different datasets remain distinct while becoming interoperable through shared entities and ontologies. ([University of Helsinki][2])

This strongly reinforces your own principle:
do not flatten institutional identity.

This is crucial.

Your project should preserve:

* museum identity;
* library identity;
* theater identity;
* archive identity.

While still enabling:

* semantic traversal.

---

# 7. Hybrid Between Research Tool and Public Interface

SAMPO portals are notable because they work simultaneously as:

* scholarly infrastructure;
* public-facing interfaces. ([University of Helsinki][1])

That is also clearly the trajectory of your project.

This has UI implications:

* visually approachable;
* but semantically deep.

---

# What Should NOT Be Copied Directly

Your project should not simply replicate the SAMPO stack.

Important differences:

## 1. Avoid Early SPARQL Dependence

SAMPO relies heavily on:

* RDF;
* SPARQL;
* Linked Open Data infrastructure.

Your project currently benefits from:

* lighter onboarding;
* CSV compatibility;
* iterative modeling.

You should preserve this advantage initially.

---

## 2. Avoid Ontology Overengineering Early

The SAMPO ecosystem is ontology-heavy.

Your discussions repeatedly emphasized:

* practicality;
* lightweight prototyping;
* gradual enrichment.

This is wise.

Start with:

* normalized tables;
* controlled vocabularies;
* lightweight relationships.

Only later:

* graph layer;
* RDF;
* semantic inferencing.

---

## 3. Preserve Visual Institutional Orientation

SAMPO portals often foreground semantic structure over institutional browsing.

Your project is stronger when:

* institutional orientation remains visually primary.

This is one of your genuinely distinctive ideas.

---

# Concrete Frontend Features Worth Reusing

## Left-Side Facet Panel

Strong recommendation.

Persistent filter sidebar:

* institution;
* medium;
* period;
* creator;
* location;
* movement;
* themes;
* relationship types.

---

# Dynamic Result Counts

Example:

```text
Painting (12,481)
Sculpture (2,119)
Opera (481)
```

Very useful for exploration.

---

# Breadcrumb Navigation

Example:

```text
Galleries
→ Painting
→ Symbolism
→ Denmark
→ 1880–1910
```

---

# Multiple Result Layouts

Switchable:

* grid;
* table;
* timeline;
* map;
* network.

---

# Entity-Centered Result Cards

Result cards should emphasize:

* entities;
* relationships;
* contextual metadata.

Not merely thumbnails.

---

# Contextual Crosslinks

Example:
A painting page should expose:

* depicted persons;
* depicted places;
* related texts;
* performances;
* institutions;
* timeline position.

This is central to your project identity.

---

# Strong Recommendation for Repository Planning

Add a dedicated document:

```text
docs/frontend-inspirations/sampo-analysis.md
```

Include:

* screenshots;
* interaction notes;
* reusable patterns;
* anti-patterns;
* comparison to your architecture.

This will be extremely useful for:

* Codex;
* Claude Code;
* future collaborators.

---

# Recommended Strategic Position

The emerging architecture could be summarized as:

> “A CSV-first, institution-oriented cultural discovery platform inspired by the faceted semantic-navigation principles of the Finnish SAMPO portals, but optimized for gradual evolution toward richer semantic interconnection.”

That is a strong and coherent positioning.

[1]: https://researchportal.helsinki.fi/en/publications/sampo-ui-a-full-stack-javascript-framework-for-developing-semanti?utm_source=chatgpt.com "Sampo-UI: A Full Stack JavaScript Framework for Developing Semantic Portal User Interfaces - University of Helsinki"
[2]: https://researchportal.helsinki.fi/en/publications/sampo-model-and-semantic-portals-for-digital-humanities-on-the-se/?utm_source=chatgpt.com "“Sampo” Model and Semantic Portals for Digital Humanities on the Semantic Web - University of Helsinki"
