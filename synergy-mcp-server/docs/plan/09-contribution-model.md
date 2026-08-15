# 09 — Contribution Model

**Status:** accepted · **Phase:** 1

**Contents:** [Context](#context) · [Decision](#decision) · [Rejected alternatives](#rejected-alternatives) · [Consequences](#consequences)

## Context

Most of this repo is ordinary code where a normal review is fine. A small part of it is the only thing standing between an agent and a decade of engineering history. Those two categories cannot share a review standard, and "be careful" is not a process.

## Decision

**Safety-critical paths are enumerated in code**, in `synergy_core/safety.py`:

```
synergy_core/safety.py
synergy_core/boundary.py
synergy_core/audit.py
synergy_core/scope.py
synergy_core/drivers/base.py
synergy_core/drivers/ccm72.py
synergy_core/backends/ccm.py
docs/ccm-contract.md
```

`scripts/flag_safety_paths.py` runs in CI and labels any PR touching them. Those PRs require two reviewers and an accompanying eval case. Everything else takes one.

**Automated checks**, all wired into `scripts/run_all_checks.py`:

| Script | Fails on |
|---|---|
| `check_version_sync.py` | Package versions out of step |
| `check_import_isolation.py` | A capability package importing another capability package |
| `check_contracts.py` | A tool registered outside its declared group |
| `check_skill_sync.py` | A skill's `requires_tools` naming a tool that does not exist; prompt/command drift |
| `forge_validate.py` | Corpus frontmatter, manifest or chunking violations |
| `flag_safety_paths.py` | Labels safety PRs |

**Eval cases** live in `tests/evals/cases/`. `safety.yaml` is mandatory reading before changing the policy layer; every allowlist or boundary change adds a case proving the new boundary holds. A safety change without a case is not reviewable.

**Documentation is part of the change.** A behaviour change edits `docs/architecture.md` in the same commit. A new decision adds a numbered plan record rather than editing an accepted one — accepted records are superseded, never rewritten.

**Skills version independently.** A skill edit bumps its own `version:` and does not require a package release. This is what makes knowledge corrections cheap enough to actually happen.

## Rejected alternatives

**Uniform review for everything.** Either too heavy for a docstring fix or too light for an allowlist change. Enumerating the small dangerous set is what makes the rest lightweight.

**A `# SAFETY:` comment convention instead of a path manifest.** Greppable but not enforceable, and it drifts silently as files move. A manifest in code can be tested and is itself in the manifest.

**Trusting review to catch policy regressions.** A one-line allowlist addition looks like nothing in a diff. That is exactly why it needs a mandatory eval case rather than a careful reader.

**Requiring live-database tests in CI.** Not portable and not safe to assume. The evals run against recorded `ccm` transcripts; live validation is a separate, opt-in run documented in `tests/README.md`.

## Consequences

- Contributors must run `scripts/run_all_checks.py` before opening a PR. It is the single command that reproduces CI.
- The safety manifest must be maintained as files move. It lists itself, so a change to it is always flagged.
- Recorded-transcript tests mean the CLI harvest from phase 2 doubles as test fixtures, which is a further argument for doing the harvest early.
