# 08 — Server Decomposition

**Status:** accepted · **Phase:** 1

**Contents:** [Context](#context) · [Decision](#decision) · [Rejected alternatives](#rejected-alternatives) · [Consequences](#consequences)

## Context

A single flat package is the easy start and the hard finish. Servers of this shape reliably reach a point where mechanism (audit, boundary, transport, inventory) is tangled with policy (which tools exist) and has to be decomposed after the fact. There is no reason to walk into that knowingly.

There is also a deployment argument: a site may want the query tools on a build host without the inventory-write tools, and profile flags are a weaker guarantee than simply not installing the code.

## Decision

Two packages plus a combined server, all version-locked.

| Package | Contains | Depends on |
|---|---|---|
| `synergy-core` | Mechanism only: `audit`, `boundary`, `scope`, `safety`, `paths`, `inventory`, `formats`, `prompts`, `doc_resources`, `drivers/`, `backends/` | `fastmcp`, `PyYAML` |
| `synergy-db` | The read tool groups: `session`, `query`, `object`, `task`, `project` | `synergy-core` |
| `synergy-mcp` (in `server/`) | Combined server: profile resolution, group registration, skills, credentials CLI | both |

Rules:

- **`synergy-core` never registers a tool.** It provides mechanism; capability packages provide policy. If core imports `@mcp.tool()`, the layering has failed.
- **Every package ships the same version.** `scripts/check_version_sync.py` fails CI on a mismatch. Dependencies are pinned with `==`, not `>=`.
- **Each capability package has its own entry point** (`synergy-db`) so it can run standalone without relying on profile flags.
- Registration functions are keyword-only: `register_object_tools(mcp, *, write_enabled=False)`.
- `scripts/check_import_isolation.py` fails CI if a capability package imports another capability package. They may only share `synergy-core`.

Driver/backend split inside core:

- `drivers/` owns **what is allowed and how to say it** for a Synergy generation — read allowlist, mutating sub-flags, format specifiers, health sequence. `Ccm72Driver` is the only one today.
- `backends/` owns **how to execute** — `CcmBackend` handles the session pool and subprocess. A future backend (Java API, remote SSH) implements the same ABC.

## Rejected alternatives

**One flat package.** Faster now, and the tangle is predictable. The split costs two `pyproject.toml` files.

**A package per tool group** (`synergy-query`, `synergy-object`, `synergy-task`, …). Over-decomposed for five small groups that share a session pool and are always deployed together. Groups already give per-deployment control; packages would add five build artefacts for no additional isolation.

**Reusing an existing MCP toolkit's core package.** Considered, since generic mechanism (`audit`, `boundary`, `scope`) is similar across CLI-wrapping servers and reuse would avoid duplication. Rejected: it would couple two products' release cycles and drag unrelated domain concepts — device families, hardware drivers, SNMP — into a version-control tool. Conventions are worth sharing; code across unrelated domains is not.

**No driver layer, syntax inline in tools.** Guarantees that adding 7.1 support means editing every tool. The driver exists so a second Synergy generation is a new file, not a rewrite.

## Consequences

- Three `pyproject.toml` files to keep in step; automated by the version-sync check.
- Editable installs need all three: `pip install -e packages/synergy-core -e packages/synergy-db -e server`.
- The driver layer is speculative today — there is exactly one driver. It is justified because the alternative discovered later is a rewrite, and because it gives the allowlist a natural home separate from the execution path.
