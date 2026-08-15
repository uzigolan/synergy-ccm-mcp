# Glossary

**Contents:** [Synergy terms](#synergy-terms) · [Toolkit terms](#toolkit-terms) · [MCP terms](#mcp-terms) · [Abbreviations](#abbreviations)

## Synergy terms

**Attach mode** — Operating the server against a session a human started, supplied via `SYNERGY_<DB>_CCM_ADDR`. The server never handles a password and never stops the session.

**Baseline** — An immutable snapshot: a set of project versions plus the tasks that produced them. The nearest Git analogue is a tag, but it names project *versions* rather than a tree hash.

**`ccm`** — The Synergy command-line client, in `$CCM_HOME/bin`. The only channel this server uses.

**`CCM_ADDR`** — Environment variable identifying a session, of the form `host:port:host`. Every command runs inside one.

**`cvtype`** — The object category: `csrc`, `dir`, `project`, `task`, `folder`, `releasedef`, `baseline`, `problem`. Distinct from `type`, which is the file type.

**Database** — A Synergy repository. Holds many products. The unit of session and inventory in this toolkit.

**DCM** — Distributed Change Management, Synergy's multi-site replication. Object names are DCM-qualified in replicated databases. Its commands are permanently denylisted.

**Delimiter** — The character between name and version in an object name, `-` or `~`. Database-configurable; read it with `ccm delim`, never assume it.

**Folder** — A collection of tasks, usually query-based. Folders feed project groupings.

**Four-part name** — `name-version:type:instance`, e.g. `main.c-3:csrc:1`. The universal object identifier.

**Object** — Everything in Synergy: file versions, directories, projects, tasks, folders, baselines. This is why one query tool answers most questions.

**Project** — A versioned object whose members are files, directories and other projects. Products are hierarchies of project versions.

**Project grouping** — What determines which object versions a project's members resolve to, derived from its folders and release.

**Release / `releasedef`** — A label such as `product/2.0` scoping tasks, folders and projects.

**Seat** — A floating licence held for a session's lifetime. The binding operational constraint; see [03](03-session-pooling.md).

**Session** — A connection to a database. Slow to establish, holds a seat, not safe for concurrent commands.

**Status** — Lifecycle state: `working`, `visible`, `integrate`, `test`, `released`. Only `working` objects are mutable.

**Task** — A unit of change grouping object versions. The Synergy answer to "what changed" is a task, not a file.

**Work area** — The on-disk materialisation of a project version. Not required for reads; `ccm cat` reads from the database.

## Toolkit terms

**Allowlist** — The read verbs the policy layer permits, matched by exact string equality. Fails closed.

**Boundary / boundary block** — The `<ccm-output …>` wrapper applied at one seam to everything the database returns. See [02](02-untrusted-output.md).

**Capability package** — A versioned Python package providing one area of tools (`synergy-db`). Depends only on `synergy-core`.

**Commit guard** — Phase 3 interlock refusing a commit if the database was read after staging.

**Corpus** — Ingested reference material (CLI help, manuals, release notes) searchable via FTS5. See [corpus-contract.md](../corpus-contract.md).

**Denylist** — Verbs unreachable by any configuration (`delete`, `purge`, `dcm`, …) and mutating sub-flags (`-create`, `-complete`, …).

**Driver** — Encodes what is allowed and how to phrase it for a Synergy generation. `Ccm72Driver` today.

**Escape hatch** — `run_readonly_command`, for allowlisted verbs with no dedicated tool.

**Group** — A set of tools registered together: `session`, `query`, `object`, `task`, `project`, `introspection`, `inventory`, `dev`.

**Harvest** — Capturing `ccm help` output from a live client as ground truth for that installation.

**Inventory** — `inventory.yaml`. Database facts only; credentials live in `.env`.

**Profile** — `lean` (default, ~15 tools) or `legacy` (everything). Set by the operator at startup, never by the model.

**Safety-critical path** — A file listed in `synergy_core/safety.py`, requiring two reviewers and an eval case.

**Session pool** — One long-lived session per database, with per-database locking and transparent stale-session retry.

**Staged change** — Phase 3 write flow: `stage_change` previews, a human approves, `commit_change(confirm=true)` applies.

## MCP terms

**FastMCP** — The framework. Tools are registered with `@mcp.tool()`; the docstring becomes the tool description the model reads.

**Prompt** — An invocable, parameterised workflow. Shares its body with the matching slash command.

**Resource** — Read-only context addressed by URI (`synergy://status`), retrievable without a tool call and therefore without schema cost.

**`requires_tools`** — Skill frontmatter listing the tools its instructions call. Checked against the live registry; unmet entries surface as `missing_tools`.

**Skill** — A `SKILL.md` file of operating instructions loaded by the client. Versions independently of the code.

**Tool schema** — The JSON schema injected into context every turn, ~100 tokens per tool. The reason the tool surface is deliberately small.

## Abbreviations

| Short | Long |
|---|---|
| CM | Configuration Management |
| DCM | Distributed Change Management |
| FTS5 | SQLite full-text search, version 5 |
| MCP | Model Context Protocol |
| RA | Registration Authority |
| TOC | Table of contents |
