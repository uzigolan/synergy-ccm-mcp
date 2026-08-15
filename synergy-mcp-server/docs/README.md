# Documentation Index

**Contents:** [Start here](#start-here) · [Reference](#reference) · [Operations](#operations) · [Design history](#design-history) · [Conventions](#conventions)

Documentation for `synergy-mcp`, an MCP server exposing IBM Rational Synergy 7.2 through the `ccm` CLI.

## Start here

| Document | Read it when |
|---|---|
| [CONCEPTS.md](CONCEPTS.md) | You know Git but not Synergy. Object model, four-part names, task-based CM. |
| [architecture.md](architecture.md) | You want the canonical picture: stack, layout, session model, safety invariants. |
| [connecting-local-mcp.md](connecting-local-mcp.md) | You are setting the server up for the first time. |

## Reference

| Document | Contents |
|---|---|
| [mcp-capabilities.md](mcp-capabilities.md) | Every tool, resource and prompt, with signatures and return shapes. |
| [ccm-contract.md](ccm-contract.md) | **Safety-critical.** Allowlist, denylist, argument validation, output boundary, audit schema. |
| [corpus-contract.md](corpus-contract.md) | Phase 2 knowledge corpus: sources, schema, chunking, provenance. |
| [knowledge-sources.md](knowledge-sources.md) | Official IBM Docs links, local `ccm help` harvest source and ingest commands. |
| [VERSIONS.md](VERSIONS.md) | Version policy, component matrix, Synergy compatibility. |
| [plan/GLOSSARY.md](plan/GLOSSARY.md) | Terms, Synergy and toolkit alike. |

## Operations

| Document | Contents |
|---|---|
| [workflows.md](workflows.md) | The multi-step procedures: who changed a file, what is in a release, baseline comparison. |
| [examples.md](examples.md) | Concrete calls with real output, plus the failure modes that will bite you. |
| [integration-guide.md](integration-guide.md) | Deployment shapes, scopes, licence budgeting, CI usage. |
| [performance.md](performance.md) | Where time goes, session pooling, query cost, call patterns. |
| [skills-routing.md](skills-routing.md) | The skill set, frontmatter contract, how skills are served and versioned. |
| [dynamic-tool-discovery-and-routing.md](dynamic-tool-discovery-and-routing.md) | Token economics, profiles, intent tagging, ranking rules. |

## Design history

[plan/](plan/README.md) records how the architecture was arrived at — what was considered, what was rejected, and why. `architecture.md` records what is true now; when the two disagree, `architecture.md` wins.

Start with [00 — Baseline and Guardrails](plan/00-baseline-and-guardrails.md).

## Conventions

- Every document opens with a **Contents** line linking to its sections.
- Terminal commands are given relative to the repo root, `synergy-ccm-mcp/`.
- `architecture.md`, `ccm-contract.md` and `corpus-contract.md` are contracts: change the document and the code in the same commit.
- Accepted plan records are superseded by new records, never rewritten.
