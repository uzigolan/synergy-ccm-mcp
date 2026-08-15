# Design Plan

**Contents:** [Purpose](#purpose) · [How to read this](#how-to-read-this) · [Index](#index) · [Status](#status) · [Decision record format](#decision-record-format)

## Purpose

`docs/plan/` is the decision history: how the architecture was arrived at, what was considered and rejected, and what is deferred. [`docs/architecture.md`](../architecture.md) records what is true *now*; these files record *why*.

When the two disagree, `architecture.md` wins and the plan file is stale — fix it.

## How to read this

Read `00` first. After that the files are largely independent. Each is short by design: a decision, its rationale, its consequences, and its status.

## Index

| # | File | Decision |
|---|---|---|
| 00 | [baseline-and-guardrails](00-baseline-and-guardrails.md) | Read-only phase 1, allowlist over denylist, no shell |
| 01 | [capability-grouping](01-capability-grouping.md) | Tool groups, profiles, what earns a dedicated tool |
| 02 | [untrusted-output](02-untrusted-output.md) | One boundary seam; why Synergy content is higher-risk |
| 03 | [session-pooling](03-session-pooling.md) | Pooled sessions, attach mode, licence seats |
| 04 | [query-as-primary-surface](04-query-as-primary-surface.md) | One flexible query tool plus a skill, not twenty wrappers |
| 05 | [knowledge-corpus](05-knowledge-corpus.md) | Harvest `ccm help`; corpus contract |
| 06 | [mcp-prompts](06-mcp-prompts.md) | One workflow definition shared by prompts and commands |
| 07 | [write-phase](07-write-phase.md) | Staged change flow, deferred to phase 3 |
| 08 | [server-decomposition](08-server-decomposition.md) | Package split and version locking |
| 09 | [contribution-model](09-contribution-model.md) | Safety paths, review rules, eval cases |
| — | [GLOSSARY](GLOSSARY.md) | Terms used across these documents |

## Status

| Phase | Content | Status |
|---|---|---|
| 1 | Read-only tools over `ccm` | in progress |
| 2 | Knowledge corpus and `knowledge` group | designed, not built |
| 3 | Task-management writes behind stage → commit | designed, not built |
| 4 | Checkout/checkin, work areas | not scheduled |

## Decision record format

Each numbered file follows the same shape:

```markdown
# NN — Title

**Status:** accepted | proposed | superseded by NN · **Phase:** 1

## Context
What forced a decision.

## Decision
What we do. Imperative, specific.

## Rejected alternatives
What else was considered, and the concrete reason it lost.

## Consequences
What this costs us and what it forecloses.
```

Do not edit an accepted record to change its decision. Supersede it with a new record and mark the old one.
