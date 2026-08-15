# 04 — Query as the Primary Surface

**Status:** accepted · **Phase:** 1

**Contents:** [Context](#context) · [Decision](#decision) · [Rejected alternatives](#rejected-alternatives) · [Consequences](#consequences)

## Context

Synergy stores everything as objects, so `ccm query` answers most questions: which files changed, which tasks are open, what a project contains, which baselines exist. It is a real query language with functions, attribute predicates and time comparisons.

The obvious MCP design — a tool per question — collides with this. Wrapping "find tasks by owner", "find tasks by release", "find tasks by status", "find objects by type", "find objects modified since" as separate tools produces dozens of near-identical tools that are collectively less capable than the one query language underneath them.

## Decision

**`ccm_query` is the primary tool.** It takes a raw query expression and a field list, and returns structured rows.

Dedicated tools exist only where one of these holds:

1. The underlying `ccm` verb is **not** `query` — `cat`, `diff`, `history`, `finduse`, `properties`, `attribute`, `task -show`.
2. The query is **error-prone to write** and frequently needed — `project_members` picks between `is_member_of` and `hierarchy_project_members`; `find_tasks` composes `cvtype='task'` with escaped predicates.

`run_readonly_command` is the escape hatch for allowlisted verbs with no wrapper.

The query language itself is documented in the **`synergy-query-language`** skill, loaded on demand, with a recipe cookbook. Depth lives in knowledge, not in tool count.

## Rejected alternatives

**A tool per question.** ~40 tools, ~4 k tokens per turn, and still not covering the query space — the moment a user asks something the tool authors did not anticipate, the model is stuck. One flexible tool plus a good skill is strictly more capable and an order of magnitude cheaper.

**A structured query builder** (`ccm_query(cvtype=..., owner=..., status=..., modified_after=...)`). Tempting, and safer-looking. Rejected because it can only ever express a subset of the language: no `has_predecessor`, no `is_member_of`, no boolean nesting, no `match`. It would force an escape hatch anyway, and then there would be two ways to do everything.

**Free-text natural language → query translation server-side.** Moves model work into the server, badly. The model is better at this than a rule engine, provided it has the grammar — which is what the skill is for.

## Consequences

- The safety of `ccm_query` rests entirely on `query` being incapable of mutation. That is true in stock Synergy 7.2 and is asserted in [ccm-contract.md](../ccm-contract.md); a site with query customisations must re-verify it.
- The expression argument is deliberately **not** character-validated, unlike object names. It is raw syntax by design, and it is safe because it is one argv element passed to a non-shell process. This asymmetry is unintuitive and is called out explicitly in the contract.
- Query quality becomes a knowledge problem. If the model writes bad queries, the fix is the skill, not the server. That is a feature: skills version independently and can be corrected without a release.
- Unbounded queries are the main performance hazard, so `max_rows` is enforced with explicit truncation reporting rather than silent capping.
