# MCP Capabilities

**Contents:** [Surfaces](#surfaces) · [User-facing capabilities](#user-facing-capabilities) · [Tool groups](#tool-groups) · [session](#group-session) · [query](#group-query) · [object](#group-object) · [task](#group-task) · [project](#group-project) · [introspection](#group-introspection) · [inventory](#group-inventory-write-flag-gated) · [dev](#group-dev-flag-gated) · [Resources](#resources) · [Prompts](#prompts) · [Return shapes](#return-shapes) · [Error style](#error-style)

## Surfaces

The server exposes three MCP surfaces:

- **Tools** — actions the model may call. Registered conditionally per [tool profile](#tool-groups).
- **Resources** — read-only context the client can pull without spending a tool call.
- **Prompts** — portable workflow definitions shared with `commands/*.md` so there is one definition and no drift.

## User-facing capabilities

`show_capabilities()` and `synergy://status` return a grouped capability list so users asking "what can you do?" see workflows, not only tool names.

| Capability | What it supports | Main tools | Main skills |
|---|---|---|---|
| `session-health` | List databases and verify/read sessions | `list_databases`, `health_check`, `ccm_version` | `synergy-core`, `synergy-troubleshooting` |
| `query-and-reporting` | Bounded queries, counts, group-by, pagination, CSV/TSV export | `query`, `find_tasks`, `find_crs`, `find_releases`, `list_attributes` | `synergy-query-language`, `synergy-reporting` |
| `change-requests` | CR/problem lifecycle, resolver/status/release fields, associated tasks | `find_crs`, `cr_info`, `cr_tasks`, `task_objects_bulk` | `synergy-change-requests` |
| `trs-workflows` | Find CRs by TRS, handle `trs` field vs synopsis/task fallback, summarize release/baseline deltas | `find_trs`, `trs_info`, `trs_changes`, `summarize_release_changes` | `synergy-trs-workflows` |
| `task-and-project-audit` | Tasks, changed objects, project membership, baselines and release task sets | `task_info`, `task_objects`, `task_objects_bulk`, `project_members`, `find_baselines`, `project_grouping_info` | `synergy-task-project`, `synergy-object-model` |
| `object-history-and-diff` | Object properties, attributes, content, history, diffs and finduse | `object_properties`, `object_attributes`, `attribute_value`, `object_content`, `object_history`, `object_diff`, `find_use` | `synergy-object-model` |
| `knowledge-corpus` | Local Synergy CLI/help/manual lookup for exact syntax and docs | `knowledge_search` | `synergy-knowledge-corpus` |

TRS examples:

```text
find_trs(database, "24952")
trs_changes(database, "24986")
summarize_release_changes(database, trs_values=["24952", "24986"], release_match="mp*4*")
```

## Tool groups

Groups are enabled by `tool_profile.config.json` and environment flags. A disabled group's tools **do not exist** in the session — they are not registered, not merely hidden. The model discovers what is active by reading `synergy://status`.

| Group | Default (`lean`) | Flag | Writes |
|---|---|---|---|
| `session` | on | always | no |
| `query` | on | always | no |
| `object` | on | always | no |
| `task` | on | `SYNERGY_MCP_TASK` | no |
| `project` | on | `SYNERGY_MCP_PROJECT` | no |
| `introspection` | off (folded into `synergy://status`) | `legacy` profile | no |
| `inventory` | off | `SYNERGY_MCP_INVENTORY_WRITE` | yes (local YAML only) |
| `dev` | off | `SYNERGY_MCP_DEV_TOOLS` | no (demo only) |

`legacy` enables every group. `lean` is the default and keeps the tool schema budget near 15 tools.

---

### Group: `session`

| Tool | Signature | Purpose |
|---|---|---|
| `list_databases` | `() -> list[dict]` | Databases this server may reach. Credential-free. |
| `health_check` | `(database: str) -> dict` | Open or verify the session. **Call this first.** |
| `ccm_version` | `(database: str) -> str` | Client version, to confirm 7.2 syntax assumptions. |

`health_check` returns `{database, reachable, ccm_addr, session_owned_by_server, db_path, role, status_output}`.

### Group: `query`

| Tool | Signature | Purpose |
|---|---|---|
| `ccm_query` | `(database, expression, fields=None, max_rows=None) -> dict` | The workhorse. Raw Synergy query syntax in, structured rows out. |
| `run_readonly_command` | `(database, args: list[str]) -> str` | Escape hatch for allowlisted verbs not wrapped by a dedicated tool. |

`ccm_query` returns `{database, expression, fields, rows, returned, total_matched, truncated}`. An empty result set is `rows: []` with `total_matched: 0` — **not** an error, even though `ccm` exits non-zero.

### Group: `object`

| Tool | Signature | Purpose |
|---|---|---|
| `object_properties` | `(database, object_name) -> str` | `ccm properties` |
| `object_attributes` | `(database, object_name) -> str` | `ccm attribute -la` |
| `attribute_value` | `(database, object_name, attribute) -> str` | `ccm attribute -show` |
| `object_content` | `(database, object_name) -> str` | `ccm cat` — content of one version |
| `object_history` | `(database, object_name) -> str` | `ccm history` |
| `object_diff` | `(database, object_a, object_b) -> str` | `ccm diff` |
| `find_use` | `(database, object_name) -> str` | `ccm finduse` — which projects contain it |

### Group: `task`

| Tool | Signature | Purpose |
|---|---|---|
| `task_info` | `(database, task) -> str` | `ccm task -show info` |
| `task_objects` | `(database, task) -> str` | `ccm task -show objects` — the change set |
| `find_tasks` | `(database, owner=None, release=None, status=None, max_rows=None) -> dict` | Structured task search |

### Group: `project`

| Tool | Signature | Purpose |
|---|---|---|
| `project_members` | `(database, project, recursive=False, max_rows=None) -> dict` | `is_member_of` or `hierarchy_project_members` |
| `find_baselines` | `(database, release=None, max_rows=None) -> dict` | Baseline objects, optionally by release |
| `project_grouping_info` | `(database, project) -> str` | `ccm project_grouping` |

### Group: `introspection` (legacy)

| Tool | Purpose |
|---|---|
| `check_skill_version` | Compare the client's loaded skill version against the server's copy |
| `list_versions` | Server, package and skill versions |
| `tool_versions` | Registered tools and their owning group |

In `lean` these are folded into the `synergy://status` resource to save schema tokens.

### Group: `inventory` (write, flag-gated)

| Tool | Purpose |
|---|---|
| `add_database` | Append an entry to `inventory.yaml` |
| `update_database` | Modify an entry |
| `remove_database` | Delete an entry |

These write **only the local inventory file**, never the Synergy database. Credentials are still set out-of-band by a human via `synergy-mcp-set-credentials`.

### Group: `dev` (flag-gated)

| Tool | Purpose |
|---|---|
| `run_demo_database` | Start an in-process fake `ccm` for tests and demos |
| `stop_demo_database` | Stop it |

---

## Resources

| URI | Contents |
|---|---|
| `synergy://status` | Server version, read-only posture, registered tools, served skill versions, missing-tool warnings |
| `synergy://inventory` | Credential-free database list |
| `synergy://skills` | Skill index: name, description, version (~100 tokens, no bodies) |
| `synergy://skills/<name>` | Full `SKILL.md` body, fetched on demand |
| `synergy://skills/<name>/<relpath>` | A file inside a skill directory, e.g. harvested `ccm help` output |

Skills are served by the MCP server. They are not embedded into Claude Desktop MCPB or VS Code Copilot install artifacts.

`synergy://status` is the single source of truth for "what can I do right now". If a tool the model expects is missing, status says why.

## Prompts

| Prompt | Slash command | Workflow |
|---|---|---|
| `synergy_health` | `/synergy-health` | Verify session, report version + database facts |
| `synergy_who_changed` | `/synergy-who-changed` | File → history → task → author → sibling objects |
| `synergy_task_audit` | `/synergy-task-audit` | Tasks for a release, with completeness checks |
| `synergy_baseline_diff` | `/synergy-baseline-diff` | Compare two baselines by task set |

## Return shapes

There is **no universal envelope**. A tool returns what its type hint says:

- Structured search tools return `dict` with `rows` plus `returned` / `total_matched` / `truncated`.
- Text tools return `str`, always wrapped in a `<ccm-output>` boundary block.
- Listing tools return `list[dict]`.

Truncation is always explicit. A tool never silently drops rows.

## Error style

Errors are raised as `ToolError`, never returned as a success string. Message conventions:

- `REFUSED:` — the model asked for something the policy forbids. State what *is* allowed.
- `INVALID:` — malformed argument, e.g. an object name containing a quote.
- `UNAVAILABLE:` — the session or binary could not be reached; include the remedy.

Example:

```
REFUSED: 'ccm delete' is permanently blocked by synergy-mcp (destructive).
Allowed read verbs: attribute, baseline, cat, compare, conflicts, delim, diff,
dir, finduse, folder, history, ls, project_grouping, properties, query, relate,
status, task, version.
```
