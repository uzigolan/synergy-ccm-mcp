# Versions

**Contents:** [Version policy](#version-policy) · [Component matrix](#component-matrix) · [Skill versions](#skill-versions) · [Driver versions](#driver-versions) · [Compatibility](#compatibility) · [Checking at runtime](#checking-at-runtime) · [Release process](#release-process)

## Version policy

- **All Python packages are locked to one version.** `synergy-core`, `synergy-db` and `synergy-mcp` always ship the same number. A mismatch is a CI failure (`scripts/check_version_sync.py`), not a warning.
- **Skills version independently** with their own semver, because their content changes far more often than the code.
- **Drivers version independently**, because they track the Synergy client generation rather than the server.

## Component matrix

| Component | Version | Notes |
|---|---|---|
| `synergy-mcp` (server) | 0.1.0 | Combined server |
| `synergy-core` | 0.1.0 | Locked to server |
| `synergy-db` | 0.1.0 | Locked to server |
| `fastmcp` | ≥ 2.0 | MCP framework |
| Python | ≥ 3.10 | PEP 604 unions |

## Skill versions

| Skill | Version | Covers |
|---|---|---|
| `synergy-core` | 1.0.0 | Safety rules, session ritual, routing |
| `synergy-ccm-reference` | 1.0.0 | `ccm` 7.2 verb syntax |
| `synergy-query-language` | 1.0.0 | Query grammar and recipes |
| `synergy-db-mng` | 1.0.0 | Inventory and credentials |

Bump the minor version for new content, the patch version for corrections, and the major version when previously documented guidance becomes wrong.

## Driver versions

| Driver | Version | Synergy client |
|---|---|---|
| `Ccm72Driver` | 1.0.0 | Rational Synergy 7.2 / 7.2.1 |

The driver owns the read allowlist, the mutating sub-flag list, the `-f` format specifier set and the health sequence. Supporting 7.1 or 6.5 means adding a driver, never editing the tool layer.

Verified against `ccm version` output of the form:

```
Rational Synergy Version 7.2 ...
```

If your client reports something else, `ccm_version` will still work but syntax assumptions in the driver are unverified. Report it before trusting results.

## Compatibility

| Synergy version | Status |
|---|---|
| 7.2, 7.2.1 | Supported — the target |
| 7.1, 7.1a | Expected to work; query language and object model are unchanged. Unverified. |
| 7.0 | Unverified |
| 6.5 and earlier (Telelogic / CM Synergy) | Object model matches; CLI flags differ. Needs its own driver. |

The stable surface across all of these is the query language and the four-part object name. The volatile surface is flag spelling on `task`, `folder` and `baseline`.

## Checking at runtime

Lean profile:

```
read resource synergy://status
```

Legacy profile:

```
list_versions()
tool_versions()
check_skill_version(name="synergy-core", client_version="1.0.0")
```

`synergy://status` reports server version, package versions, per-skill server-side versions, and any `missing_tools` a skill declares but the active profile does not register.

## Release process

1. Bump the version in all three `pyproject.toml` files together.
2. Update the matrix in this file.
3. Update `CHANGELOG.md`.
4. Run `python synergy-mcp-server/scripts/run_all_checks.py`, which enforces version sync, contract compliance and skill/tool cross-references.
5. Tag `v<version>`.
