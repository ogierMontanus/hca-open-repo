---
name: steering
description: Decide where a piece of Claude Code steering config belongs — CLAUDE.md, a rule, a skill, a subagent, a hook, an output style, or an appended system prompt. Use when adding or moving project instructions, conventions, guardrails, or workflows, when CLAUDE.md is growing, or when an instruction keeps being ignored and needs to become enforcement.
---

# Steering Claude Code: choosing the mechanism

Source: [Steering Claude Code: when to use CLAUDE.md, skills, hooks, and
subagents](https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more)
(Anthropic, 2026-07-10). This skill condenses that post's recommendations
into a decision procedure.

The core question is **not** "how do I tell Claude to do this?" but "what
kind of thing is this, and what does it cost to load?" Two axes decide it:

- **Is it advisory or absolute?** An instruction the model weighs versus a
  constraint that must hold. Advisory → context (CLAUDE.md, rules, skills).
  Absolute → enforcement (hooks, permissions, managed settings).
- **When is it relevant?** Always → CLAUDE.md. Only for certain paths →
  a path-scoped rule. Only when a task starts → a skill. Never in the
  main thread → a subagent.

## Decision table

| The thing you're adding | Put it in | Why |
|---|---|---|
| Build commands, directory layout, coding conventions, team norms | **CLAUDE.md** | Facts Claude should hold all session |
| A constraint tied to specific files ("migrations are append-only") | **Rule** in `.claude/rules/` with `paths:` frontmatter | Loads only when those paths are touched |
| A procedure: deploy workflow, release checklist, review process | **Skill** in `.claude/skills/` | Body loads only on invocation |
| A side task whose intermediate output you'll never re-read (deep search, log analysis, dependency audit) | **Subagent** in `.claude/agents/` | Isolated context; only the summary returns |
| Something that must happen every time, deterministically (lint after edit, block a command, notify on completion) | **Hook** | Executes code; doesn't depend on the model choosing |
| Something that must *never* happen | **Hook** (`PreToolUse`, exit code 2) or **permissions / managed settings** | An instruction is the wrong tool for a guardrail |
| A significant role change (code assistant → general assistant) | **Output style** — but check the built-ins first | Replaces the default system prompt |
| A one-off constraint for a single invocation | **`--append-system-prompt`** | Additive; preserves default behavior |

## Context cost, cheapest first

1. **Subagent** — zero in the main context until called.
2. **Hook** — config lives outside the context window entirely.
3. **Skill** — only `name` + `description` load at session start; the body
   loads on invocation. Re-injected on compaction up to a shared budget,
   oldest dropping first.
4. **Rule** — medium; free while unscoped paths aren't touched, but an
   *unscoped* rule is "mechanically identical to putting the content in
   CLAUDE.md: always loaded, always costing tokens."
5. **CLAUDE.md** — high; every line loads whether relevant or not.
6. **Output style / appended system prompt** — highest; never compacted,
   though cached after the first request.

## Anti-patterns

- **"Every time X, always do Y" in CLAUDE.md, when reliability matters.**
  The model *choosing* to run a formatter is different from the formatter
  *running*. If it must happen, it's a hook.
- **Guardrails written as instructions.** When something absolutely must
  not happen, an instruction is the wrong tool — use a hook or managed
  settings.
- **Procedural workflows in CLAUDE.md.** Move them to a skill; they don't
  need to be resident.
- **Unscoped rules.** If a rule has no `paths:`, it's just CLAUDE.md with
  extra steps. Scope it or merge it.
- **Personal preferences in project-level CLAUDE.md.** Those belong in
  local settings, not the shared file.
- **A custom output style for tone or formatting.** Check the built-ins
  (Proactive, Explanatory, Learning) first. A custom style *replaces* the
  default system prompt unless `keep-coding-instructions: true` — dropping
  the built-in instructions on scope, comments, security, and testing.
- **Long appended system prompts.** Diminishing returns and contradictions
  reduce adherence; persistent behavior belongs in CLAUDE.md or a rule.

## Hygiene

- **Keep CLAUDE.md under 200 lines.** Give it an owner and review changes
  to it like code.
- **In monorepos**, give each team's directory its own subdirectory
  CLAUDE.md so teams load only their own conventions. Use `claudeMdExcludes`
  to skip irrelevant ones.
- **Org-wide standards** should be deployed via MDM so they can't be excluded.
- **Skill vs. subagent** turns on one question: do you need to see and steer
  each step? Yes → skill (runs in the main thread). No → subagent (isolated,
  returns a summary).
- **Bundle as a plugin** once several skills, subagents, hooks, or output
  styles work together, to share a coherent setup across projects or
  teammates.

## Applying this in hca-open-repo

- `CLAUDE.md` currently carries a mix of facts (project name, tile provider,
  Windows/PowerShell conventions, verified Q-numbers) and procedures
  (Wikidata lookup steps, the Design sync loop, fix-verification). The facts
  are correctly placed. The **procedures are skill-shaped** and are the first
  candidates to move if the file outgrows its budget.
- The fact-checking and fix-verification rules are advisory by nature —
  they ask for judgment, not a blocked action — so they stay context, not
  hooks. But a check that must *always* run (e.g. rejecting a commit that
  writes an unverified Q-number to `data/curated/`) would be a hook.
- `mockup/irrelevant/` being frozen is a path-scoped constraint: rule
  material, if it ever needs enforcing beyond the current CLAUDE.md note.
