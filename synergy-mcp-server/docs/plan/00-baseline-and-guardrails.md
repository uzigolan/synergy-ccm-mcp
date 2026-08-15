# 00 — Baseline and Guardrails

**Status:** accepted · **Phase:** 1

**Contents:** [Context](#context) · [Decision](#decision) · [Rejected alternatives](#rejected-alternatives) · [Consequences](#consequences)

## Context

Synergy 7.2 is a system of record for a decade or more of engineering history at a site that still runs it. It is frequently the only copy. The `ccm` CLI can delete objects, purge history, alter the type schema and reconfigure DCM replication — and several of those are irreversible without a database restore.

An agent driving that CLI is a new and unusual risk: it is fast, it is confident, and its instructions can be influenced by text it reads out of the database itself.

## Decision

1. **Phase 1 is read-only.** No write tool is implemented, and mutating verbs are rejected by the policy layer rather than merely absent.
2. **Allowlist the verbs, denylist the sub-flags.** The read verb set is small and stable, so an allowlist is maintainable. Sub-flags are numerous and version-dependent, so `-create` / `-modify` / `-delete` / `-complete` and friends get an explicit denylist layered on top.
3. **A permanent denylist exists above both.** `delete`, `purge`, `archive`, `migrate`, `db`, `dcm`, `typedef`, `users`, `rename`, `unuse` are unreachable by any configuration. No flag enables them; phase 3 will not add them.
4. **Never invoke a shell.** All execution is `subprocess.run(argv, shell=False)`.
5. **Validate anything interpolated into a query expression** against a conservative character class.
6. **Session lifecycle is internal.** `ccm start` / `ccm stop` are not tools.
7. **Everything is audited** to append-only JSONL with secrets redacted.

## Rejected alternatives

**Denylist only.** Enumerating dangerous `ccm` verbs and allowing the rest fails open: a verb we have not heard of, or one added by a site customisation, is permitted by default. With ~24 useful read verbs, an allowlist costs almost nothing and fails closed.

**Wrapping the Java API instead of the CLI.** The `ccm.jar` API is better structured, but it is less documented, less stable across 7.x point releases, and would put us on a code path nobody at the site exercises. The CLI is what the operators know and what the manuals describe, so failures are diagnosable by humans.

**Allowing writes behind confirmation from the start.** A staged-commit flow would have worked and is well understood. It was rejected for phase 1 purely on sequencing: we do not yet have verified 7.2 flag spellings for the mutating forms, and guessing at the syntax of a command that modifies a system of record is not acceptable. Writes land in phase 3, after the CLI harvest gives us ground truth.

**Running over SSH to a remote Synergy host.** Rejected because the client is co-located with the server in this deployment. Adding a transport abstraction with no second implementation would be speculative generality.

## Consequences

- The server cannot help with day-to-day development work — no checkouts, no task completion. It is an *investigation* tool for phase 1.
- The policy layer must be maintained as a real security boundary, with its own tests, not treated as input validation.
- `ccm query` is unusually powerful for a read-only tool, and its safety rests entirely on `query` being incapable of mutation. That assumption is documented in [ccm-contract.md](../ccm-contract.md#argument-validation) and must be re-verified if a site adds query customisations.
- Phase 3 inherits a working allowlist, audit trail and boundary seam, so it only has to add the staged flow rather than build safety machinery under deadline.
