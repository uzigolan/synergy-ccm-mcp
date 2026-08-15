# Skills Routing

**Contents:** [Why routing](#why-routing) · [The skill set](#the-skill-set) · [Router decision table](#router-decision-table) · [Frontmatter contract](#frontmatter-contract) · [Serving skills](#serving-skills) · [Version checking](#version-checking) · [Writing a skill](#writing-a-skill) · [Anti-patterns](#anti-patterns)

## Why routing

Loading every skill on every turn wastes context. Instead one small always-on skill (`synergy-core`) carries the safety rules and a routing table, and pulls in a domain skill only when the conversation needs it. This is progressive disclosure applied to knowledge rather than tools.

## The skill set

| Skill | Loaded | Owns |
|---|---|---|
| `synergy-core` | Always, at session start | Safety rules, session-opening ritual, routing table, common read-only workflows |
| `synergy-query-language` | On demand | Query grammar, functions (`is_member_of`, `has_predecessor`, …), recipe cookbook |
| `synergy-object-model` | On demand | Four-part names, object types, properties, attributes, content, history, diffs, `finduse` |
| `synergy-task-project` | On demand | Tasks, releases, baselines, project members, project grouping, release audits |
| `synergy-knowledge-corpus` | On demand | Served corpus lookup, harvested `ccm help`, IBM/manual reference, syntax citation |
| `synergy-troubleshooting` | On demand | Runtime failures: missing `ccm`, stale sessions, auth, inventory, licence seats, empty results |

`synergy-core` is deliberately the only one with a standing context cost.

## Router decision table

`synergy-core` carries this table. The rule is: match the user's intent, load exactly one domain skill, do not pre-load speculatively.

| User intent | Load |
|---|---|
| "what does `ccm history` output mean", "which flag lists attributes" | `synergy-knowledge-corpus` |
| "find all objects that…", "write me a query for…" | `synergy-query-language` |
| "what is this object name", "show this version", "where is this object used" | `synergy-object-model` |
| "who changed X", "what is in release Y", "compare baselines" | `synergy-task-project` |
| "ccm not found", "no password", "session stale", "query timed out" | `synergy-troubleshooting` |
| "install Claude", "install VS Code", "build MCPB" | none — installation is docs/scripts, not skills |
| Anything mutating | none — refuse, cite the read-only posture |

## Frontmatter contract

Every `SKILL.md` opens with YAML frontmatter. Fields are load-bearing, not decorative:

```yaml
---
name: synergy-query-language
description: >
  Synergy query grammar and recipes for Rational Synergy 7.2. Use when the user
  asks to find objects, tasks, projects or baselines by criteria, or needs a
  query expression written or explained.
version: 1.0.0
families: [ccm72]
servers: [synergy-mcp, synergy-db]
requires_tools:
  - query
  - find_tasks
---
```

| Field | Purpose |
|---|---|
| `name` | kebab-case, unique, matches the directory name |
| `description` | The routing signal. Written as "use when…", because this is what the client matches against user intent. |
| `version` | semver; bump on any content change |
| `families` | Synergy client generations the content is valid for (`ccm72`) |
| `servers` | Server names this skill ships with; `[]` means all |
| `requires_tools` | Tools the skill's instructions call. Checked against the live registry. |

`requires_tools` is what makes a degraded profile visible: if a skill requires `find_tasks` but the `task` group is disabled, `synergy://status` reports `missing_tools` for that skill instead of the model silently failing mid-workflow. The same status payload is the authoritative list of served skill names and versions expected by this server.

## Serving skills

Synergy skills are **served only**. They live on disk under `skills/` and are exposed by the MCP server as resources. They are not embedded into the Claude Desktop MCPB, VS Code config or any client-side plugin bundle.

| URI | Payload |
|---|---|
| `synergy://skills` | Index — name, description, version only. ~100 tokens. |
| `synergy://skills/<name>` | Full `SKILL.md` body |
| `synergy://skills/<name>/<relpath>` | Reserved for future reference assets under a skill directory |

Path traversal is blocked in `skills.skill_file()`; `<relpath>` is resolved and confirmed to stay inside the skill directory.

## Version checking

The client's loaded copy of a skill can drift from the server's. At session start the model calls `check_skill_version` (legacy profile) or reads `synergy://status` (lean), which reports:

```json
{
  "skills": [
    {"name": "synergy-core", "server_version": "1.2.0", "missing_tools": []},
    {"name": "synergy-query-language", "server_version": "1.0.0", "missing_tools": ["find_tasks"]}
  ]
}
```

A mismatch is surfaced to the user, not silently reconciled.

## Writing a skill

Structure, in order:

1. `# Title`
2. `> **Skill version:** X.Y.Z · updated YYYY-MM-DD` plus a one-line changelog of breaking changes
3. `## Session self-check` — what to verify before acting
4. `## Golden Rules` — numbered, first phrase bolded, imperative
5. Domain sections
6. `## Versions` — matrix of skill and driver versions

Style rules:

- Reference tools by exact live name with argument shape: `query(database, expression, fields)` or the client-visible alias if one is present.
- Quote tool docstrings verbatim where they define a contract; do not paraphrase.
- File paths in backticks.
- Tables for enumerable facts, prose for judgement calls.
- Cross-link sibling skills by name in bold: load the **`synergy-knowledge-corpus`** skill.

## Anti-patterns

- **Duplicating the CLI manual.** A skill is operating instructions, not a reference dump. Bulk reference belongs in `references/` and is fetched on demand.
- **Restating tool schemas.** The client already has them. Say when to use a tool, not what its parameters are.
- **Soft safety language.** "Try to avoid" is not a rule. Rules are imperative and absolute, and are mirrored by server-side enforcement.
- **Speculative loading.** Do not tell the model to load three skills "for context".
