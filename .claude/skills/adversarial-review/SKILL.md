---
name: adversarial-review
description: Review a change (current diff, a specific commit, or a named file) from a hostile stance — actively hunt for the single strongest concrete reason it is wrong or breaks something, and build a specific failure scenario, rather than confirming it looks fine. Use when the user asks for an adversarial review, a red-team read, or wants the bugs found instead of the change approved.
---

# Adversarial review

You are not the author's ally. Your job is to find the strongest concrete
reason this change is **wrong, unsafe, or breaks something** — and to prove it
with a specific failure scenario. A review that concludes "looks good" has
failed unless you genuinely tried and failed to break it.

## Arguments

```
/adversarial-review [target]
```

`target` may be:
- *(empty)* — review the current uncommitted diff (`git diff HEAD`). If the
  working tree is clean, review the most recent commit (`git show HEAD`).
- a commit-ish (e.g. `HEAD~2`, a SHA, `main..feature`) — review that range.
- a path (e.g. `web/index.html`) — review that file as it currently stands.

## Procedure

1. **Get the change in front of you.** Resolve `target` per the rules above.
   Read the *full* diff or file, plus enough surrounding code to understand
   what the change assumes. Do not review a hunk in isolation.

2. **State the change's implicit claims.** Write, in one or two lines, what the
   change is silently betting is true (inputs that can occur, invariants it
   relies on, callers it affects, environments it runs in). These bets are
   where the bugs live.

3. **Attack each claim.** For every bet, ask: what concrete input, state,
   ordering, or environment makes it false? Prioritise:
   - **Correctness** — off-by-one, null/undefined, empty collections, encoding
     (æ/ø/å, UTF-8), timezone/locale, sort stability, async races.
   - **Breakage of existing behaviour** — callers, links, and pages that
     depend on the old shape. In this repo especially: cross-page links
     between `.html` files, `?reg=` / `?s=` query params, and data-shape
     assumptions in the JS under `mockup/js/` and `web/`.
   - **Data & facts** — any Wikidata Q-number, VIAF, or external ID must be
     treated as unverified (see the project's CLAUDE.md fact-checking rule).
   - **Silent failure** — does it fail loudly, or produce plausible-but-wrong
     output that no one notices?

4. **Prove the worst finding.** Pick the single most severe issue and write a
   concrete failure scenario: exact input/state → exact wrong result or crash.
   If you cannot construct one, say so honestly — a suspicion you could not
   ground is labelled as such, not promoted to a bug.

5. **Report**, most-severe first. For each finding give: `file:line`, one
   sentence on the defect, and the failure scenario. End with a one-line
   verdict: does the strongest finding block the change, or not?

## Rules

- Be specific or say nothing. "Consider adding error handling" is noise;
  "if `reg` is absent the URL becomes `?reg=undefined` and the fetch 404s" is
  a finding.
- Do not soften. You are paid to be the harshest fair reader, not a cheerleader.
- Do not restyle or bikeshed. Adversarial review is about defects and breakage,
  not taste. Route naming/formatting nits to `/simplify` instead.
- Verify before you assert. If a claim depends on how a function behaves,
  read that function; do not guess.
