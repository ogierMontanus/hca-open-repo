# Query-Builder Survey — End-User Structured Query Tools for GLAM Data

This document surveys existing open-source modules, libraries, and frameworks
that help non-technical humanities users assemble complex, multi-facet structured
queries over cultural-heritage datasets.

The motivating use case is the **H.C. Andersen Diary Register** (`hca-open-repo`):
a static-mockup-now / CSV-relational-future platform navigating ~3,700 works,
~10,200 persons, ~2,500 places, and ~4,500 diary pages from H.C. Andersen's
diaries. Entities carry typed attributes (genre, form, dates, geocoords,
country, etc.) and link back to diary pages. The deployment targets are:

- **Near-term:** static site (`file://` mockup + GitHub Pages), JSON-on-CDN.
- **Future:** relational backend (Postgres, star schema), eventually a semantic
  graph layer.

A scholar should be able to express queries like
> "show me all works that were performed on stage, published in France,
> between 1852 and 1863"
without writing SQL or SPARQL.

This survey is research-only. No code is committed here; conclusions feed into
the roadmap decisions captured in `docs/roadmap.md`.

---

## Method and verification notes

All claims about license, version numbers, last-release dates, and runtime
requirements were verified against primary sources (GitHub release pages,
project documentation, official websites) and cited inline. Where a source
did not surface a date or status, the entry says **"unknown"** rather than
guessing. Per the project rule on factual checks (`CLAUDE.md`), no version
numbers or licenses were taken from memory.

Today's date for the snapshot below is **2026-06-07**.

---

# 1. Faceted-search platforms in GLAM / SAMPO context

These are full-stack discovery platforms rather than embeddable widgets.
They are the "reference architectures" the H.C. Andersen interface should
look at, even if they are too heavy to adopt wholesale in the static-mockup
phase.

## 1.1 Blacklight (Ruby on Rails + Solr)

A discovery interface for any Solr index, originally developed at the
University of Virginia Library and used by many academic libraries.

- **License:** Apache-2.0
  ([repo](https://github.com/projectblacklight/blacklight)).
- **Latest stable release:** **v9.0.0** (2024-11-25), an aggregation of nearly
  300 PRs over 14 months
  ([release notes](https://github.com/projectblacklight/blacklight/releases)).
- **Stack:** Ruby on Rails ≥ 7.2, Ruby ≥ 3.2, Bootstrap 5.3+, ViewComponent 3+,
  Apache Solr backend
  ([release notes](https://github.com/projectblacklight/blacklight/releases)).
- **Fit for HCA static phase:** Poor. Requires a Rails app and a Solr index.
- **Fit for HCA future phase:** Possible but heavy; Postgres-only deployments
  would need a Solr sidecar or a Postgres-FTS adapter.
- **Drop-in cost:** Days-to-weeks to set up; significant Ruby/Rails operational
  burden.
- **Note:** Europeana built `europeana-blacklight` as a REST adapter
  ([repo](https://github.com/europeana/europeana-blacklight)) — proof that a
  Blacklight UI can be retrofitted onto a non-Solr backend, which is relevant
  if HCA ever wants to reuse the Blacklight facet UX patterns without buying
  the Solr stack.

## 1.2 VuFind (PHP + Solr)

A library discovery system "designed and developed for libraries by libraries"
([vufind.org](https://vufind.org/vufind/)).

- **License:** GPL-2.0 (per `vufind.org` project page;
  [repo](https://github.com/vufind-org/vufind)).
- **Latest release:** **v11.0.4** (2026-06-01)
  ([releases](https://github.com/vufind-org/vufind/releases)).
- **Stack:** PHP + Solr.
- **Fit for HCA static phase:** Poor — requires PHP and Solr.
- **Fit for HCA future phase:** Possible, but PHP would be an outlier in an
  otherwise Postgres + JS roadmap.

## 1.3 Sampo-UI (React + Express + SPARQL)

The framework behind the Finnish SAMPO portals (BiographySampo, WarSampo,
NameSampo, Nobel Prize Sampo, etc.), developed by the SeCo group at Aalto.
Already analysed in `sampo-analysis.md`; recapped here for completeness.

- **License:** MIT ([repo](https://github.com/SemanticComputing/sampo-ui)).
- **Latest release:** **v3.0.0** (2025-02-20)
  ([repo](https://github.com/SemanticComputing/sampo-ui)).
- **Stack:** React + Material-UI + Redux + redux-observable on the client,
  Express on the server, talks to a SPARQL endpoint
  ([SeCo project page](https://seco.cs.aalto.fi/tools/sampo-ui/)).
- **Fit for HCA static phase:** Poor — assumes a SPARQL endpoint and an
  Express backend.
- **Fit for HCA future phase:** Possible once a graph layer exists, but it
  locks the project into RDF/SPARQL, which conflicts with the CSV-first
  positioning recorded in `sampo-analysis.md` ("Avoid Early SPARQL Dependence").
- **Lessons learned:** SeCo has published an experience report
  ([Nobel Prize Sampo, CEUR Vol-4064](https://ceur-ws.org/Vol-4064/PD-paper17.pdf))
  and a semantic-web-journal paper
  ([SWJ](https://www.semantic-web-journal.net/content/sampo-ui-full-stack-javascript-framework-developing-semantic-portal-user-interfaces-0))
  documenting iterations from MuseumFinland (2004) through to today's
  configurable Sampo-UI.

## 1.4 Yasgui (SPARQL editor + result visualiser)

A browser-only SPARQL editor with syntax highlighting, autocomplete, and a
pluggable result-view layer.

- **License:** MIT ([repo](https://github.com/TriplyDB/Yasgui)).
- **Latest release of the monorepo:** **v4.0.113** (2020-04-08); the
  **TriplyDB/Yasgui repository was archived 2026-04-20** and is now read-only
  ([repo](https://github.com/TriplyDB/Yasgui)).
- **Stack:** TypeScript, browser-only; expects a CORS-enabled SPARQL endpoint.
- **Fit for HCA static phase:** Not applicable — there is no SPARQL endpoint
  yet, and Yasgui's UX targets users who already know SPARQL.
- **Note:** A forked clone exists at
  [`thegetty/YASGUI`](https://github.com/thegetty/YASGUI). Yasgui is mentioned
  here mainly to be ruled out: archival status + SPARQL-literate audience make
  it the wrong target for HCA's humanities researchers.

## 1.5 Apache Solr / Elasticsearch facet front-ends

Two notable JS libraries that sit on top of Lucene-family search engines:

- **HuygensING/solr-faceted-search-react** — React component pack for Solr
  facets. **Archived 2018-11-26**
  ([repo](https://github.com/HuygensING/solr-faceted-search-react)). Dead end.
- **appbaseio/reactivesearch** — Apache-2.0, 20+ React/Vue UI components for
  Elasticsearch / OpenSearch / Solr / MongoDB; last release of the Vue
  package **v3.4.0 (2025-03-10)**
  ([repo](https://github.com/appbaseio/reactivesearch)).
- **Searchkit** — open source UI components for Elasticsearch/OpenSearch with
  a "search directly from the browser" mode useful for prototyping
  ([searchkit.co](https://www.searchkit.co/)).

These are the lowest-friction options if HCA chooses Elasticsearch over
Solr in the backend phase, but they presume a search server is running.

---

# 2. GUI SPARQL / SQL query builders

These are the closer matches to the literal request "let a humanities user
assemble a structured query".

## 2.1 Sparnatural (visual SPARQL builder, browser-only)

A visual, client-side SPARQL query builder configurable via SHACL, written
in TypeScript.

- **License:** LGPL-3.0 ([repo](https://github.com/sparna-git/Sparnatural)).
- **Latest release:** **v12.2.0 (2026-03-24)**
  ([releases](https://github.com/sparna-git/Sparnatural/releases)).
- **Stack:** TypeScript, browser-only; needs a CORS-enabled SPARQL endpoint
  (the project ships a SPARQL proxy for endpoints that aren't CORS-enabled).
- **Fit for HCA static phase:** Only if HCA stands up a small SPARQL endpoint
  over its CSV — possible (e.g. via Apache Jena Fuseki on the future backend
  host), not possible from `file://`.
- **Fit for HCA future phase:** Excellent. Once an RDF/SPARQL layer exists,
  Sparnatural gives a configurable, SHACL-driven visual query interface.
- **Production track record:** Deployed at
  [data.bnf.fr/sparnatural](https://data.bnf.fr/sparnatural) by the
  Bibliothèque nationale de France; also used in an Archives Nationales
  demonstrator
  ([Sparna blog](https://blog.sparna.fr/2022/05/24/evenement-sparnatural-demonstrateurs-archives-nationales-bnf/)).
  This is the single most directly relevant precedent for HCA.

## 2.2 Sparklis (NL-guided SPARQL builder)

Sébastien Ferré's query builder that verbalises SPARQL in English/French/Spanish.

- **License:** Apache-2.0 ([repo](https://github.com/sebferre/sparklis)).
- **Releases:** No GitHub releases published; activity tracked via commits.
- **Stack:** OCaml compiled to JavaScript via `js_of_ocaml`; runs in the
  browser, requires a CORS-enabled SPARQL endpoint.
- **Strength:** It is the most literally "natural-language-guided" structured
  query builder available, covering "a large subset of SPARQL 1.1 SELECT
  queries" (BGPs, UNION, OPTIONAL, FILTER, GROUP BY, aggregates) — see
  [Ferré 2017, Semantic Web journal](https://journals.sagepub.com/doi/10.3233/SW-150208).
- **Fit for HCA static phase:** Not applicable (needs SPARQL).
- **Fit for HCA future phase:** Strong candidate alongside Sparnatural;
  the trade-off is Sparnatural's SHACL-driven configurability vs. Sparklis's
  more expressive query coverage and stronger NL surface.

## 2.3 SparqlBlocks (Blockly-style block editor)

A Blockly-based visual SPARQL composer.

- **License:** MIT ([repo](https://github.com/miguel76/SparqlBlocks)).
- **Latest release:** unknown — release page failed to load in the snapshot
  and no `Releases` exist publicly; "306 Commits" on master.
- **Stack:** JavaScript (Blockly), browser-only.
- **Fit:** Mainly a teaching tool. Not a strong fit for end-user humanities
  workflows where queries are not meant to "feel like programming".

## 2.4 Wikidata Query Builder (Vue, form-based)

Wikimedia's official form-based query builder, deliberately simpler than
the older Query Helper.

- **License:** BSD-3-Clause
  ([repo](https://github.com/wikimedia/wikidata-query-builder)).
- **Releases:** None published on GitHub; deployed via Wikimedia infrastructure.
- **Stack:** TypeScript + Vue, browser-based.
- **Live UI:** [query.wikidata.org/querybuilder](https://query.wikidata.org/querybuilder/).
- **Maintainer note:** "Query Builder is not meant to replace the Wikidata
  Query Service or SPARQL queries, but to enable easy access to some really
  important features of SPARQL"
  ([Wikidata:Query Builder](https://www.wikidata.org/wiki/Wikidata:Query_Builder)) —
  a useful framing for HCA: a form-based builder is meant to be the
  *first* UI, not the only one.
- **Fit:** Wikidata-specific; not directly reusable, but the UX is a strong
  reference for "narrow but pleasant".

## 2.5 OpenRefine + Reconciliation API

Not a query builder per se — but the reconciliation workflow is the dominant
GLAM tool for matching local CSV strings against external authorities
(Wikidata, VIAF, etc.) and is the natural sibling to a query UI.

- **License:** BSD ([OpenRefine.org history](https://openrefine.org/openrefine_history)).
- **Latest release:** **3.10.1** (2026-03-04)
  ([releases](https://github.com/OpenRefine/OpenRefine/releases)).
- **Stack:** Java backend + browser UI; runs locally as a desktop tool.
- **Fit:** Off the critical path for the query UI itself, but the
  Reconciliation API spec is a standard worth knowing if HCA ever exposes
  its own controlled vocabularies for external reuse.

## 2.6 Linked Data Reactor (LD-R) and Sgvizler — historical

- **LD-R** ([ali1k/ld-r](https://github.com/ali1k/ld-r)): component-based
  Linked Data UI framework (React + Fluxible). Last release **v1.3.10
  (2020-09-10)**; effectively unmaintained.
- **Sgvizler** ([mgskjaeveland/sgvizler](https://github.com/mgskjaeveland/sgvizler)):
  SPARQL result-set visualiser. **Archived 2022-10-14**.
- **Sgvizler 2** ([BorderCloud/sgvizler2](https://github.com/BorderCloud/sgvizler2)):
  TypeScript reboot; latest release **v1.7.6 (2025-08-26)**. Small community
  (12 stars, 13 forks).

These exist for reference but should not be adopted.

---

# 3. Visual query builders for relational data

These target SQL backends. They become relevant for HCA only once the
Postgres backend is live.

## 3.1 Metabase

The clearest "non-technical user builds a structured query" tool for SQL
backends, with a Notebook-style "Question Builder".

- **License:** AGPL-3.0 for the OSS edition; commercial editions otherwise
  ([repo](https://github.com/metabase/metabase)).
- **Latest release:** **v61.3 (2026-06-03)**
  ([repo](https://github.com/metabase/metabase)).
- **Stack:** Clojure + TypeScript; runs as a server connecting to a
  SQL database.
- **Fit for HCA static phase:** Not applicable.
- **Fit for HCA future phase:** Strong candidate as an **internal** research
  tool for editors of the HCA register, less so as the public-facing reading
  UI. The "ask a question" UX maps almost directly onto the multi-facet
  example query in the project brief.
- **License caveat:** AGPL forces source-disclosure for hosted modifications;
  acceptable for a research register but worth flagging.

## 3.2 Apache Superset

Self-service data exploration and SQL Lab.

- **License:** Apache-2.0 ([repo](https://github.com/apache/superset)).
- **Latest release:** **v6.1.0 (2026-05-13)**
  ([repo](https://github.com/apache/superset)).
- **Stack:** Python (Flask) + TypeScript/React; needs a metadata DB and a
  Node toolchain.
- **Fit:** Powerful, but the no-code "viz builder" is dashboard-oriented; the
  free-form query workflow assumes a SQL-literate user.

## 3.3 Redash

Query editor with schema browser and autocomplete; share queries and
visualisations.

- **License:** BSD-2-Clause ([repo](https://github.com/getredash/redash)).
- **Latest release:** **v26.3.0 (2026-03-02)**
  ([repo](https://github.com/getredash/redash)).
- **Stack:** Python + JS/TS; server-side.
- **Fit:** Reasonable, but again SQL-first. Best as an internal editor's
  tool, not as the scholarly reading interface.

## 3.4 Querybook (Pinterest)

Notebook-style query IDE with metadata sidebar.

- **License:** Apache-2.0 ([repo](https://github.com/pinterest/querybook)).
- **Latest release:** **v3.41.4 (2025-04-22)**
  ([releases](https://github.com/pinterest/querybook/releases)).
- **Fit:** Designed for "Big Data" Presto/Hive use; overkill for HCA.

## 3.5 Looker

Commercial, closed-source (Google Cloud). Excluded from the open-source survey
but worth noting as the dominant commercial reference for LookML-style
semantic-modelling-then-query.

## 3.6 React-Querybuilder and React-Awesome-Query-Builder

Embeddable React components — these are the most plausible building blocks
for **a custom HCA query UI**, in either phase.

| Library | License | Latest release | Notes |
|---|---|---|---|
| [react-querybuilder/react-querybuilder](https://github.com/react-querybuilder/react-querybuilder) | MIT | **v8.18.0 (2026-06-01)** | TypeScript; exports to SQL WHERE clauses, MongoDB, JsonLogic, etc.; compatibility packages for MUI, Bootstrap, Ant Design, Chakra, Mantine, PrimeReact. |
| [ukrbublik/react-awesome-query-builder](https://github.com/ukrbublik/react-awesome-query-builder) | MIT | **v6.6.15 (2025-05-16)** | Older but feature-rich; AntD/MUI/Bootstrap/Fluent widget packs. |

Both run entirely in the browser and emit a query AST that the calling app
chooses how to execute. For HCA this is critical: the **same** UI can emit
SQL against a Postgres backend or filter expressions against a static JSON
file — phase-appropriate execution behind a stable UX.

## 3.7 ItemsJS — static-friendly faceted-search engine

A small JavaScript library that does the faceted-search work *on the
client*, given a JSON array.

- **License:** Apache-2.0 ([repo](https://github.com/itemsapi/itemsjs)).
- **Latest release:** **v2.4.3 (2025-11-25)**
  ([repo](https://github.com/itemsapi/itemsjs)).
- **Stack:** JS, works in Node and the browser (UMD via unpkg/jsDelivr).
- **Scale:** Authors target "up to 100K items"; HCA's ~16,400 core entities
  fit comfortably.
- **Fit for HCA static phase:** Excellent. This is the most realistic
  engine for the GitHub-Pages mockup.

## 3.8 staticSearch (Endings Project)

Pure-JSON-on-CDN search engine built from XHTML5 documents at build time;
emphasises archival-grade durability ("no backend, ever").

- **License:** MPL-2.0 / BSD-3-Clause dual
  ([repo](https://github.com/projectEndings/staticSearch)).
- **Latest release:** **v2.0.2 (2026-05-27)**
  ([repo](https://github.com/projectEndings/staticSearch)).
- **Fit:** Strong philosophical match with HCA's static-mockup phase (and
  with the [Endings Project principles](https://endings.uvic.ca/principles.html)
  in general). Less convenient than ItemsJS if the source data is CSV/JSON
  rather than XHTML, but the durability framing is worth borrowing.

## 3.9 Perspective (FINOS)

WebAssembly-backed analytics grid for streaming/large datasets.

- **License:** Apache-2.0 ([repo](https://github.com/finos/perspective)).
- **Latest release:** **v4.5.1 (2026-05-31)**.
- **Fit:** Overkill for HCA's data sizes, but interesting for a future
  "research workbench" mode where editors slice the register.

---

# 4. Library-catalog / archive-finding query systems

Less reusable as code, but valuable as **API contract examples** for the
backend phase.

## 4.1 Europeana Search API

Solr-backed REST API with explicit facet support via the `facet` parameter
(`DEFAULT`, or any indexed Solr field) and refinement via `qf`
([Europeana PRO — Search](https://pro.europeana.eu/page/search);
[GitHub mirror](https://github.com/europeana/labs-preview/blob/master/api/search.md)).
The DEFAULT facet set (UGC, LANGUAGE, TYPE, YEAR, PROVIDER, DATA_PROVIDER,
COUNTRY, RIGHTS) is a useful inventory of "things humanities portals usually
expose".

## 4.2 DPLA API

JSON-LD search API. Facets requested standalone return global counts;
facets requested with a query return constrained counts; field facetability
is dictated by Solr field type
([pro.dp.la/developers](https://pro.dp.la/developers);
[field reference](https://pro.dp.la/developers/field-reference)).
The "global vs. constrained" facet distinction is worth lifting verbatim
into the HCA facet UI.

## 4.3 Chronicling America / loc.gov

As of 2025, Chronicling America moved off its dedicated API onto the
unified `loc.gov` API
([loc.gov NDNP migration](https://www.loc.gov/ndnp/migration/);
[Chronicling America API](https://www.loc.gov/apis/additional-apis/chronicling-america-api/)).
Faceted browse panes on the left side of the collection page filter by
ethnicity, location, subject, language. No API key required; rate limiting
encouraged. Useful precedent for "humanities-grade public API, no
authentication needed".

## 4.4 Trove (NLA)

REST API with categorical facets (e.g. format: books vs. theses), with new
facets added in 2019 (Place, Title, Word count, Illustration type)
([Trove technical guide](https://trove.nla.gov.au/about/create-something/using-api/v3/api-technical-guide)).
A community-built form-based front-end exists at
[Conal-Tuohy/TroveQueryBuilder](https://github.com/Conal-Tuohy/TroveQueryBuilder).

## 4.5 Nasjonalbiblioteket (Norway)

Documented separately if/when an HCA Norwegian-corpus integration becomes
relevant; not surveyed here.

---

# 5. Synthesis — what to actually use for HCA

Two distinct deployment phases, two distinct recommendations.

## Phase A — Static mockup (now)

**Constraints:** no backend, must work from `file://` and GitHub Pages,
data already lives in CSV → JSON-on-CDN. ~16,400 core entities total.

**Ranked recommendation:**

1. **ItemsJS** as the in-browser faceted-search engine. Best fit for the
   data size, Apache-2.0, actively maintained, works from CDN. Drives
   facet counts and filtered result sets.
2. **react-querybuilder** (or `react-awesome-query-builder`) to give
   advanced users a "rule-builder" mode for compound queries like the
   project's motivating example ("works performed on stage AND published
   in France AND date BETWEEN 1852 AND 1863"). MIT, very actively
   maintained (v8.18.0 released 2026-06-01), emits ASTs the static
   filter layer can execute against the ItemsJS index.
3. **Borrow UX from Wikidata Query Builder and Europeana Search** for
   the form layout: a small set of canonical facets at the top,
   "add another filter" affordance, persistent result count.
4. **Borrow durability framing from staticSearch / Endings** for the
   posture and documentation tone — "this site will keep working".

The combination ItemsJS + react-querybuilder gives a credible
"facet-panel + advanced-rules-modal" UX with no backend at all,
running entirely from JSON shards on a CDN.

## Phase B — Postgres backend (future)

**Constraints:** a real query engine exists; URL-shareable queries
become possible; editors and scholars both need workflows.

**Ranked recommendation:**

1. **Keep react-querybuilder as the public-facing facet UI**, but now
   compile its AST to SQL against Postgres rather than to JS filters.
   The user-facing UX is unchanged across the migration, which is
   the strongest argument for picking it in Phase A.
2. **Adopt Sparnatural** *if and when* a SPARQL layer is added on top of
   Postgres (e.g. via R2RML / Ontop or a Fuseki sidecar). It is the
   single most directly comparable production deployment in GLAM
   (data.bnf.fr/sparnatural). LGPL-3.0 is compatible with most
   reuse models; SHACL-driven configuration aligns well with the HCA
   data model.
3. **Stand up Metabase as an internal editor tool** for the
   register team — its Notebook Builder is the closest off-the-shelf
   match to "a humanities researcher poses a structured question".
   Treat it as an internal scholarly workbench, not the public site.
4. **Study Sampo-UI for UX patterns but do not adopt it as a runtime.**
   The earlier `sampo-analysis.md` already established this; the
   conclusion holds: pick the patterns, not the stack.
5. **Treat Blacklight, VuFind, Sparklis, Yasgui as reference only.**
   Blacklight/VuFind impose stacks orthogonal to the project's
   direction; Yasgui is archived; Sparklis targets SPARQL-literate
   power users.

## What this means for the roadmap

- The **single highest-leverage decision** is to commit, in Phase A,
  to a React-based query AST (via `react-querybuilder`) whose
  *execution* layer is pluggable. That makes the Phase B migration to
  Postgres a back-end swap with no UX regression.
- The **single biggest precedent to study in depth** is
  [data.bnf.fr/sparnatural](https://data.bnf.fr/sparnatural): same
  cultural-heritage domain, same kind of multi-facet researcher query,
  in production.
- The **single biggest risk to avoid** is committing to SPARQL too early
  — the existing `sampo-analysis.md` already flagged this; nothing in
  the current survey changes that conclusion.

---

## References (consolidated)

### Faceted-search platforms
- [Project Blacklight repo](https://github.com/projectblacklight/blacklight)
- [Blacklight releases](https://github.com/projectblacklight/blacklight/releases)
- [Europeana Blacklight adapter](https://github.com/europeana/europeana-blacklight)
- [VuFind site](https://vufind.org/vufind/) · [repo](https://github.com/vufind-org/vufind) · [releases](https://github.com/vufind-org/vufind/releases)
- [Sampo-UI repo](https://github.com/SemanticComputing/sampo-ui) · [SeCo project page](https://seco.cs.aalto.fi/tools/sampo-ui/) · [Sampo-UI paper, SWJ](https://www.semantic-web-journal.net/content/sampo-ui-full-stack-javascript-framework-developing-semantic-portal-user-interfaces-0) · [Nobel Prize Sampo experience, CEUR Vol-4064](https://ceur-ws.org/Vol-4064/PD-paper17.pdf)
- [Yasgui repo (archived 2026-04-20)](https://github.com/TriplyDB/Yasgui)
- [HuygensING solr-faceted-search-react (archived 2018)](https://github.com/HuygensING/solr-faceted-search-react)
- [appbaseio ReactiveSearch](https://github.com/appbaseio/reactivesearch) · [Searchkit](https://www.searchkit.co/)

### GUI query builders
- [Sparnatural repo](https://github.com/sparna-git/Sparnatural) · [Sparnatural docs](http://docs.sparnatural.eu/) · [Sparnatural BnF deployment](https://data.bnf.fr/sparnatural) · [Sparna blog on BnF/AN demonstrators](https://blog.sparna.fr/2022/05/24/evenement-sparnatural-demonstrateurs-archives-nationales-bnf/)
- [Sparklis repo](https://github.com/sebferre/sparklis) · [Sparklis SWJ paper](https://journals.sagepub.com/doi/10.3233/SW-150208)
- [SparqlBlocks repo](https://github.com/miguel76/SparqlBlocks)
- [Wikidata Query Builder repo](https://github.com/wikimedia/wikidata-query-builder) · [live UI](https://query.wikidata.org/querybuilder/) · [Wikidata:Query Builder page](https://www.wikidata.org/wiki/Wikidata:Query_Builder)
- [OpenRefine releases](https://github.com/OpenRefine/OpenRefine/releases) · [project history](https://openrefine.org/openrefine_history)
- [LD-R repo](https://github.com/ali1k/ld-r)
- [Sgvizler (archived)](https://github.com/mgskjaeveland/sgvizler) · [Sgvizler2](https://github.com/BorderCloud/sgvizler2)

### Relational / embeddable query UIs
- [Metabase repo](https://github.com/metabase/metabase) · [license page](https://www.metabase.com/license/)
- [Apache Superset repo](https://github.com/apache/superset)
- [Redash repo](https://github.com/getredash/redash)
- [Querybook repo](https://github.com/pinterest/querybook) · [releases](https://github.com/pinterest/querybook/releases)
- [react-querybuilder repo](https://github.com/react-querybuilder/react-querybuilder) · [docs](https://react-querybuilder.js.org/)
- [react-awesome-query-builder repo](https://github.com/ukrbublik/react-awesome-query-builder)
- [ItemsJS repo](https://github.com/itemsapi/itemsjs)
- [staticSearch repo](https://github.com/projectEndings/staticSearch)
- [Perspective repo](https://github.com/finos/perspective)

### Library / archive APIs
- [Europeana Search API](https://pro.europeana.eu/page/search) · [Europeana API source mirror](https://github.com/europeana/labs-preview/blob/master/api/search.md)
- [DPLA developers](https://pro.dp.la/developers) · [DPLA field reference](https://pro.dp.la/developers/field-reference)
- [Chronicling America API](https://www.loc.gov/apis/additional-apis/chronicling-america-api/) · [loc.gov migration](https://www.loc.gov/ndnp/migration/)
- [Trove technical guide](https://trove.nla.gov.au/about/create-something/using-api/v3/api-technical-guide) · [TroveQueryBuilder](https://github.com/Conal-Tuohy/TroveQueryBuilder)
