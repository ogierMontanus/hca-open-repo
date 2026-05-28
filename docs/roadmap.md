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

> **Status:** the methodology layer for this phase is now in place — see [`data-model/`](data-model/) and [`pipeline/`](pipeline/) for the documented schema rationale and conversion stages, plus `scripts/parsers/` for the section-specific parsers that consume `raw/HCA-Repository V*.xlsx`.

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
