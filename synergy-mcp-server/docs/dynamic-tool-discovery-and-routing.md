# Dynamic Tool Discovery and Routing

**Contents:** [The problem](#the-problem) · [Token economics](#token-economics) · [Profiles as the macro lever](#profiles-as-the-macro-lever) · [Status as the discovery surface](#status-as-the-discovery-surface) · [Intent tagging](#intent-tagging) · [Ranking rules](#ranking-rules) · [Next-step guidance](#next-step-guidance) · [Degradation](#degradation) · [Measuring](#measuring)

## The problem

Tool schemas are injected into context on **every turn**. A server that registers 50 tools taxes every message in the conversation, whether or not any tool is used. For a Synergy server the temptation is real: `ccm` has dozens of verbs and it would be easy to wrap each one.

We do not. The tool surface is deliberately small and the depth lives in skills and one general-purpose tool.

## Token economics

Rough costs, measured against a comparable CLI-wrapping MCP server:

| Item | Cost |
|---|---|
| One registered tool schema | ~100 tokens, every turn |
| `lean` profile (≈15 tools) | ~1.5 k tokens/turn |
| `legacy` profile (≈25 tools) | ~2.5 k tokens/turn |
| `synergy://skills` index | ~100 tokens, once |
| One `SKILL.md` body | 1–3 k tokens, on demand |

Wrapping every `ccm` verb as its own tool would cost more per turn than the entire skill layer costs once. This is why `ccm_query` plus `run_readonly_command` exist: one flexible tool with a good skill beats twenty narrow tools with none.

## Profiles as the macro lever

`lean` is the default. It registers `session`, `query`, `object`, `task` and `project`, and folds introspection into a resource.

`legacy` adds `introspection`, `inventory` and `dev`. Use it for development and debugging, not for daily work.

A disabled group's tools **are not registered**. There is no "hidden but callable" state — if the model cannot see it, it cannot call it, and that is the same fact.

## Status as the discovery surface

`synergy://status` is the single answer to "what can I do right now":

```json
{
  "server_version": "0.1.0",
  "tool_profile": "lean",
  "read_only": true,
  "groups": {"session": true, "query": true, "object": true,
             "task": true, "project": true,
             "introspection": false, "inventory": false, "dev": false},
  "databases": [{"name": "prod-core", "session_open": true}],
  "skills": [{"name": "synergy-core", "server_version": "1.2.0", "missing_tools": []}]
}
```

Reading a resource costs no tool call and no round-trip to Synergy. Prefer it over an introspection tool.

## Intent tagging

When routing among several available providers (this server, a Git MCP, a ticketing MCP), tag by intent rather than by name:

| Intent | Tool |
|---|---|
| `db_lookup` | `list_databases`, `health_check` |
| `object_search` | `ccm_query` |
| `object_detail` | `object_properties`, `object_attributes`, `attribute_value` |
| `content_read` | `object_content` |
| `history` | `object_history`, `find_use` |
| `compare` | `object_diff` |
| `change_set` | `task_info`, `task_objects`, `find_tasks` |
| `structure` | `project_members`, `find_baselines`, `project_grouping_info` |
| `raw` | `run_readonly_command` |

## Ranking rules

When more than one tool could serve an intent:

1. **Exact target match first.** A dedicated tool beats the escape hatch — `task_objects` over `run_readonly_command(["task","-show","objects",…])`.
2. **Structured over textual.** `ccm_query` with explicit `fields` returns rows; `run_readonly_command` returns a wall of text that costs more and parses worse.
3. **Cheap before expensive.** Non-recursive `project_members` before recursive.
4. **Read before write.** In phase 1 this is trivially satisfied; keep the habit for phase 3.
5. **Bounded before unbounded.** Always pass `max_rows` when the shape of the result is unknown.

## Next-step guidance

Tool results carry the model forward rather than leaving it to guess:

- Truncated results say so explicitly and state the total: `"returned": 500, "total_matched": 21874, "truncated": true`. The model should narrow the query, not paginate blindly.
- `health_check` reports `session_owned_by_server`, which tells the operator whether the server is holding a seat.
- Refusals name the allowed alternatives rather than only stating the prohibition.
- Phase 3's `stage_change` will return a `next_step` string telling the model exactly what has to happen before `commit_change` is permitted.

## Degradation

When a capability is absent, say why and offer the fallback:

> The `task` group is not enabled in this profile, so `find_tasks` is unavailable. I can get the same information with `ccm_query(database, "cvtype='task' and release='product/2.0'")`. Alternatively, enable `SYNERGY_MCP_TASK` and restart the server.

Never fail silently, and never pretend a missing tool's job is impossible when the general-purpose tool can do it.

## Measuring

`scripts/extract_tools.py` prints the registered tool count and estimated schema tokens per profile. Run it before adding a tool:

```bash
python synergy-mcp-server/scripts/extract_tools.py --profile lean
```

A new tool must justify ~100 tokens on every turn for every user. If it is a thin wrapper over `run_readonly_command`, it should be a skill recipe instead.
