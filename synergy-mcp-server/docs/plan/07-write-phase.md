# 07 — Write Phase

**Status:** proposed · **Phase:** 3

**Contents:** [Context](#context) · [Decision](#decision) · [Rejected alternatives](#rejected-alternatives) · [Consequences](#consequences)

## Context

Read-only answers investigation questions. It does not help with the daily work: creating a task, associating objects, completing a task. Users will ask for this, and the staged-commit pattern needed to do it safely is well established.

The blocker for phase 1 was not safety design — it was that we do not yet have verified 7.2 flag spellings for the mutating forms. Guessing at the syntax of a command that modifies a system of record is not acceptable.

## Decision

Phase 3 adds writes **only after** the phase-2 CLI harvest provides ground truth for the mutating verb syntax, and **only** for task management. The flow is the staged-commit pattern, unchanged:

1. `stage_change(database, operation, args, purpose)` — validates, resolves, returns a **preview**. Touches nothing. Returns `{stage_id, database, purpose, preview, next_step}`.
2. A human reads the preview.
3. `commit_change(stage_id, confirm=true)` — applies it. `confirm` is mandatory and must be supplied explicitly; a missing or false value is refused, not defaulted.

Additional interlocks, all inherited:

- **Pre-change snapshot.** Task state and object associations are captured to `backups/<database>-<timestamp>.json` before any mutation, and the restore path is returned in the commit output.
- **Commit guard.** A commit is refused if the database was read after staging — the read counter from [02](02-untrusted-output.md) is compared against the value recorded at stage time. Legitimate flow is stage → human reads → human approves → commit, with no reads in between. Kill switch: `SYNERGY_MCP_STRICT_COMMIT_GUARD=false`.
- **Scope gate.** Over HTTP, `require_write_scope()` rejects read-scoped tokens per call.
- **Skill gate.** A session that has not fetched `synergy://skills/synergy-core` is refused write access with an instruction to read it first.
- **Permanent denylist unchanged.** `delete`, `purge`, `archive`, `migrate`, `db`, `dcm`, `typedef`, `users` remain unreachable. Phase 3 does not touch them.

Scope, in order: `task -create`, `task -modify` (synopsis/resolver), `task -complete`. Checkout/checkin is phase 4 and is not in scope here.

## Rejected alternatives

**Direct write tools with a `confirm` parameter.** One-step confirmation is not confirmation — the model supplies the argument itself in the same turn it decided to act. Separating stage from commit puts a human turn in the middle, which is the entire point.

**Rollback instead of snapshot.** Synergy has no transaction to roll back. A snapshot plus a documented manual restore path is the honest offering.

**Allowing checkout/checkin in phase 3.** Materially larger blast radius: it touches work areas, file content and the object lifecycle. Task metadata is recoverable; a botched checkin during an integration window is not. Deferred to phase 4 with its own record.

**Trusting the commit guard alone and dropping the human turn.** The guard is a backstop against a specific failure (acting on freshly-read injected text), not a substitute for approval.

## Consequences

- Requires phase 2 to land first. This ordering is deliberate and non-negotiable.
- The safety machinery must be built and tested before the first write tool is registered, not alongside it. Eval cases under `tests/evals/cases/safety.yaml` come first.
- `SYNERGY_MCP_READONLY=true` remains the default even after phase 3. Writes are opt-in per deployment.
- The scope and skill gates exist unused in phase 1 precisely so that this phase adds a feature rather than a security subsystem.
