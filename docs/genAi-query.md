# GenAI query options for the HCA registers

Three low-cost paths to add a natural-language query layer on top of the
existing register pipeline. Scope is the October mockup phase: a working
demo against the structured Excel + JSON corpus produced by
`scripts/build_web/build_web_data.py`, with a budget that allows
trialling without procurement.

The three options share the same input — the markdown bundle proposed
in the previous Copilot review (≈30 files, ~1–10 MB each, bucketed by
register × aggregate dimension) — and differ in **where the retrieval
loop runs** and **how grounded the answers are**.

---

## Option 1 — Claude.ai Projects (hosted chat workspace)

**Setup.** Create a Project in the Claude.ai web app, upload the 30
markdown files, paste a system prompt that anchors the agent in the
HCA scholarly context (e.g. "you answer in Danish unless asked
otherwise, you cite the `Reg…` ID when surfacing an entry"), and the
workspace is ready. No code, no infrastructure, no embeddings step —
Claude indexes the project files internally and retrieves on every
turn.

**Account requirement.** The **Free tier** allows Projects with file
uploads up to **20 files per chat and 30 MB total**, defaulting to
**Claude Sonnet 4.5**. **Claude Pro (~$20/month per user)** raises the
file caps, unlocks **Opus 4.6 and 4.7**, and gives longer sessions
[1, 2]. The 30-file bundle sits right at the free-tier ceiling — fine
for a stakeholder demo, comfortable on Pro.

**Strengths.** Zero infrastructure. The whole pipeline is: regenerate
markdown → drag into the Project → chat. Danish-language queries work
out of the box because Sonnet/Opus are multilingual at production
quality. Citations are inline. Cost is predictable: **$0 for the demo,
$20/user/month if working sessions exceed free quota**.

**Limits.** The Project is a hosted UI, not a programmable API — you
cannot embed it in the public website. Files must be re-uploaded when
the pipeline produces a new `V*.xlsx` build (unless the user scripts a
sync via the Claude Files API). No web-app integration without
duplicating into Option 2.

**HCA fit:** strong for stakeholder demos and team sessions; not the
production answer for the public-facing site.

---

## Option 2 — Claude API + prompt caching (no vector DB)

**Setup.** A small Python service (Flask / FastAPI) takes a user query,
selects the relevant subset of markdown buckets (by register + the
aggregate dimensions already in `places.json` and `works.json`), and
calls the Anthropic API with the bucket as a cached prefix and the
question as the suffix. Claude returns a grounded answer. The same
script that emits the markdown bundle can pre-warm caches.

**Pricing (2026).** Claude Sonnet 4.6 is **$3 per 1M input tokens /
$15 per 1M output**; Opus 4.7 is **$5 / $25**. All three top models
ship with a **1M-token context window** at standard pricing [3, 4].
The critical lever is **prompt caching**, which "can reduce costs by
**88–95%**" for the cached prefix [4]. The **Batch API** adds a
further **50% discount** asynchronously, and the two stack — **"the
discount stacks with prompt caching, potentially reducing costs by
95% or more"** [4].

**Cost math for the HCA case.** The full markdown corpus is on the
order of 100–200 MB raw, roughly 30–60M tokens — too big for a single
context, even at 1M tokens. The right pattern is **bucket-then-cache**:
route the query to one register (Persons / Places / Works) and one
sub-bucket (country / form / letter range) via the aggregates already
in the JSON; load only that bucket (typically 1–5 MB ≈ 0.3–1.5M
tokens) as the cached prefix. With caching, the same prefix at
~$3 × 0.05 (cache discount) × ~1M tokens ≈ **\$0.15 per cold call,
~\$0.01 per warm call** plus a few cents for the answer. At a few
hundred queries per day in the demo phase, total monthly spend stays
**well under \$10**.

**Strengths.** Programmable, embeddable in the existing web mockup
(`web/app.js` can `fetch()` to the service), works in Danish and
English, no separate vector DB to operate. Marginal cost per query at
HCA scale is in single cents. Fits the "thin layer between data and
presentation" principle already in `docs/data-model/october-pipeline.md`.

**Limits.** Requires implementing the bucket-routing layer (small but
non-zero work). Cache misses on the first call of a session — the
Batch API handles cold-warm latency for non-interactive jobs.

**HCA fit:** the right default for the public-facing demo if a
deployable backend is acceptable.

---

## Option 3 — Pinecone Starter + Voyage/OpenAI embeddings + Claude

**Setup.** Add a Stage 4 to the pipeline: `scripts/build_vector/build_index.py`
reads the markdown bundle, splits each entry into chunks, calls an
embedding API to vectorise them, and upserts into Pinecone. At query
time, the web app sends the user's question to the embedder, queries
Pinecone for the top-k neighbours, then passes the retrieved chunks
to Claude (or another LLM) for the answer. Classic production RAG.

**Free tier (Starter plan, 2026).** **2 GB storage, 5 indexes, 2M
write units / month, 1M read units / month, 5M embedding tokens / month
for popular models** [5]. The free tier handles **"up to ~100 K vectors
with 1536 dimensions"**, restricted to AWS us-east-1 and 1 project /
2 users [5, 6]. **Indexes pause after 3 weeks of inactivity** and
resume on the next read [5, 6].

**Fit for HCA scale.** 16 000 entities × a few chunks each ≈ 50 000–80 000
vectors — well inside the 100 K free-tier ceiling. The 5M monthly
embedding-token quota covers an initial pass of the whole corpus with
margin to spare. Re-embedding when a new `V*.xlsx` lands is a daily
or weekly job, not a hot path. **Recurring cost: $0** unless the
project outgrows the limits.

**Strengths.** This is the architecture that scales beyond the demo
without rework. Embeddings + vector search is the most accurate
retrieval pattern when query phrasing diverges from source-language
phrasing — and Danish queries against Danish source text plus
occasional German / French place names is exactly that scenario.
Voyage AI's `voyage-3` is **Anthropic's recommended embedding model**
and multilingual at production quality [7].

**Limits.** Two services to run (embedder + Pinecone) and a small
RAG-pattern boilerplate to maintain. Free tier locks region to AWS
us-east-1 — fine for a Danish-language academic site but worth
flagging.

**HCA fit:** the production-grade path, free to trial, drops in on top
of the existing Stage 1–3 pipeline.

---

## Side-by-side

| Dimension | Option 1 — Projects | Option 2 — API + caching | Option 3 — Pinecone RAG |
|---|---|---|---|
| Trial cost | **$0** (Free) → \$20/mo Pro | < \$10 / mo at HCA scale | **$0** (Starter free tier) |
| Setup time | minutes | a weekend of Python | one day |
| Public-website integration | no (chat UI only) | yes (HTTP service) | yes (HTTP service) |
| Danish-language quality | high (Sonnet 4.5 / Opus 4.7) | high (same models) | high (Voyage + Claude) |
| Recurring infra | none | Anthropic only | Anthropic + Pinecone |
| Best stage | stakeholder demos | mockup backend | production path |

## Recommendation

Run them in parallel through the October phase:

1. **Stand up Option 1 immediately** for stakeholder sessions — cost
   $0, ready in an afternoon, no code touched.
2. **Prototype Option 2** behind the existing `web/` mockup so the
   October demo has a live query box; cost stays sub-$10/month and the
   integration is small.
3. **Bring up Option 3 in parallel** as the path forward beyond the
   mockup; the free tier covers HCA volumes, and the same markdown
   bundle from Option 1/2 feeds straight into the embedder. Promoting
   from Option 2 to Option 3 is additive, not a rewrite.

All three reuse the 30-file markdown bundle described in
`docs/data-model/october-pipeline.md`. None require Microsoft Copilot
licensing, Copilot Studio tenancy, or Pro Airtable tiers.

---

## References

[1] *Plans & Pricing*. Anthropic. <https://claude.com/pricing>

[2] *Claude free tier limits: what breaks first and what Pro fixes*.
Daehnhardt blog, May 2026.
<https://daehnhardt.com/blog/2026/05/21/claude-pro-vs-free/>

[3] *Pricing*. Claude API Documentation. Anthropic.
<https://platform.claude.com/docs/en/about-claude/pricing>

[4] *Claude API Pricing 2026: Latest Anthropic Costs for Opus, Sonnet,
Haiku*. evolink.ai, 2026.
<https://evolink.ai/blog/claude-api-pricing-guide-2026>

[5] *Pinecone pricing — Starter plan*. Pinecone.
<https://www.pinecone.io/pricing/>

[6] *Pinecone Pricing 2026: Free Tier, Serverless, and Enterprise
Costs*. PE Collective, 2026.
<https://pecollective.com/tools/pinecone-pricing/>

[7] *Embeddings — Voyage AI*. Anthropic Docs.
<https://docs.anthropic.com/en/docs/build-with-claude/embeddings>
