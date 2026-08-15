# 01 — Capability Grouping

**Status:** accepted · **Phase:** 1

**Contents:** [Context](#context) · [Decision](#decision) · [Rejected alternatives](#rejected-alternatives) · [Consequences](#consequences)

## Context

Tool schemas are injected into the model's context on every turn. A server that registers a tool per `ccm` verb would tax every message in every conversation, including the ones that never touch Synergy. Meanwhile some capabilities — inventory writes, demo databases — are useful to a maintainer and pure overhead to a user.

## Decision

Tools are organised into **groups**, and groups are registered conditionally at startup.

| Group | Default | Flag |
|---|---|---|
| `session` | on | always |
| `query` | on | always |
| `object` | on | always |
| `task` | on | `SYNERGY_MCP_TASK` |
| `project` | on | `SYNERGY_MCP_PROJECT` |
| `introspection` | off | `legacy` profile |
| `inventory` | off | `SYNERGY_MCP_INVENTORY_WRITE` |
| `dev` | off | `SYNERGY_MCP_DEV_TOOLS` |

Two profiles: `lean` (default, ~15 tools) and `legacy` (everything).

A disabled group is **not registered**. There is no hidden-but-callable state.

Discovery is via the `synergy://status` resource, not an introspection tool, because reading a resource costs no tool schema.

Registration is a function per group with a keyword-only signature:

```python
def register_object_tools(mcp: FastMCP, *, write_enabled: bool = False) -> None:
```

## Rejected alternatives

**One tool per `ccm` verb.** Roughly 24 read verbs plus sub-forms would be 40+ tools, ~4 k tokens per turn. Most would be one-line wrappers around `run_readonly_command`. See [04](04-query-as-primary-surface.md).

**Runtime enable/disable via a tool.** A `set_profile` tool would let the model widen its own capabilities, which is precisely backwards. Profiles are set by the operator at startup.

**Dynamic registration on first use.** MCP clients cache the tool list; changing it mid-session is poorly supported and confusing. Startup-time registration is boring and correct.

**No grouping — just a readonly flag.** Insufficient. Read tools also differ in cost and relevance; a user who never looks at baselines should not pay for the `project` group.

## Consequences

- The model must read `synergy://status` to know what is available; a skill that assumes a tool exists will fail on a lean deployment. This is why `requires_tools` in skill frontmatter is checked and reported as `missing_tools`.
- Adding a tool is a deliberate act with a measurable cost. `scripts/extract_tools.py` prints the per-profile token estimate, and a new tool must justify ~100 tokens on every turn for every user.
- Group boundaries are also the package boundaries ([08](08-server-decomposition.md)), so a group can be deployed standalone without profile flags.
