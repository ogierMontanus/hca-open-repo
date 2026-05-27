# SAMPO Ecosystem — Analysis and Inspiration

The Finnish SAMPO ecosystem is probably the closest existing precedent for what this project is becoming:
a cultural-semantic navigation environment built around:

* faceted discovery,
* multiple perspectives on the same data,
* linked entities,
* and humanities-oriented exploration.

The important point is that this project differs in emphasis:
the SAMPO portals are fundamentally Linked Data / semantic-web systems first,
whereas this project is intentionally beginning:

* CSV-first,
* institution-first,
* interface-first,
* and migration-friendly.

However, many UI and interaction ideas are directly reusable.

---

# Key SAMPO Concepts Worth Reusing

## 1. Multi-Perspective Navigation

One of the core SAMPO principles is:

> the same underlying data should be accessible from multiple perspectives.

This maps almost perfectly onto the project discussions:

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
2. exploration/analysis phase.

This is probably the single most important UI pattern to adopt.

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

This aligns extremely well with the existing project discussions.

---

# 3. Faceted Search Interface

The SAMPO systems are heavily facet-driven.

This is probably the strongest reusable frontend pattern.

Study:

* dynamic filter panels;
* cascading facets;
* contextual result counts;
* multi-select filtering;
* narrowing workflows.

The project's own discussions already repeatedly emphasized:

* hierarchical narrowing;
* avoiding gigantic lists;
* progressive refinement.

The SAMPO model validates this approach.

---

# 4. "Multiple Perspectives" as UI Tabs

The SAMPO portals often expose:

* maps;
* timelines;
* network graphs;
* tables;
* statistics;
* biographies;
* linked objects.

All derived from the same filtered subset.

This is extremely important for the architecture.

A user should filter once, then switch between:

* gallery mode;
* map mode;
* timeline mode;
* network mode;
* entity mode.

This becomes a major frontend principle.

---

# 5. Entity-Centered Pages

BiographySampo, BookSampo, and related portals demonstrate strong aggregation pages around entities.

This is directly compatible with the project's ideas about:

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
different datasets remain distinct while becoming interoperable through shared entities and ontologies.

This strongly reinforces the project principle:
do not flatten institutional identity.

The project should preserve:

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
* public-facing interfaces.

That is also clearly the trajectory of this project.

This has UI implications:

* visually approachable;
* but semantically deep.

---

# What Should NOT Be Copied Directly

The project should not simply replicate the SAMPO stack.

Important differences:

## 1. Avoid Early SPARQL Dependence

SAMPO relies heavily on:

* RDF;
* SPARQL;
* Linked Open Data infrastructure.

This project currently benefits from:

* lighter onboarding;
* CSV compatibility;
* iterative modeling.

Preserve this advantage initially.

---

## 2. Avoid Ontology Overengineering Early

The SAMPO ecosystem is ontology-heavy.

The project discussions repeatedly emphasized:

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

This project is stronger when:

* institutional orientation remains visually primary.

This is one of the genuinely distinctive ideas.

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

## Dynamic Result Counts

Example:

```text
Painting (12,481)
Sculpture (2,119)
Opera (481)
```

Very useful for exploration.

---

## Breadcrumb Navigation

Example:

```text
Galleries
→ Painting
→ Symbolism
→ Denmark
→ 1880–1910
```

---

## Multiple Result Layouts

Switchable:

* grid;
* table;
* timeline;
* map;
* network.

---

## Entity-Centered Result Cards

Result cards should emphasize:

* entities;
* relationships;
* contextual metadata.

Not merely thumbnails.

---

## Contextual Crosslinks

Example:
A painting page should expose:

* depicted persons;
* depicted places;
* related texts;
* performances;
* institutions;
* timeline position.

This is central to the project identity.

---

# Recommended Strategic Position

The emerging architecture could be summarized as:

> "A CSV-first, institution-oriented cultural discovery platform inspired by the faceted semantic-navigation principles of the Finnish SAMPO portals, but optimized for gradual evolution toward richer semantic interconnection."

That is a strong and coherent positioning.

---

## References

* Sampo-UI: A Full Stack JavaScript Framework for Developing Semantic Portal User Interfaces — University of Helsinki
* "Sampo" Model and Semantic Portals for Digital Humanities on the Semantic Web — University of Helsinki
