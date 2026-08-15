# Skills Routing

**Contents:** [Why routing](#why-routing) · [The skill set](#the-skill-set) · [Router decision table](#router-decision-table) · [Frontmatter contract](#frontmatter-contract) · [Serving skills](#serving-skills) · [Version checking](#version-checking) · [Writing a skill](#writing-a-skill) · [Anti-patterns](#anti-patterns)

## Why routing

Loading every skill on every turn wastes context. Instead one small always-on skill (`synergy-core`) carries the safety rules and a routing table, and pulls in a domain skill only when the conversation needs it. This is progressive disclosure applied to knowledge rather than tools.

## The skill set

| Skill | Loaded | Owns |
|---|---|---|
| `synergy-core` | Always, at session start | Safety rules, session-opening ritual, object-model grounding, routing table |
| `synergy-ccm-reference` | On demand | Exact `ccm` 7.2 verb syntax, flags, `-f` format specifiers, exit-code behaviour |
| `synergy-query-language` | On demand | Query grammar, functions (`is_member_of`, `has_predecessor`, …), recipe cookbook |
| `synergy-db-mng` | On demand | Inventory CRUD, credential workflow, attach mode |

`synergy-core` is deliberately the only one with a standing context cost.

## Router decision table

`synergy-core` carries this table. The rule is: match the user's intent, load exactly one domain skill, do not pre-load speculatively.

| User intent | Load |
|---|---|
| "what does `ccm history` output mean", "which flag lists attributes" | `synergy-ccm-reference` |
| "find all objects that…", "write me a query for…" | `synergy-query-language` |
| "add my database", "where do credentials go", "remove that entry" | `synergy-db-mng` |
| "who changed X", "what is in release Y" | none — the workflow is in `synergy-core` |
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
  - ccm_query
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

`requires_tools` is what makes a degraded profile visible: if a skill requires `find_tasks` but the `task` group is disabled, `synergy://status` reports `missing_tools` for that skill instead of the model silently failing mid-workflow.

## Serving skills

Skills live on disk under `skills/` and are also served as resources so a remote client gets identical knowledge:

| URI | Payload |
|---|---|
| `synergy://skills` | Index — name, description, version only. ~100 tokens. |
| `synergy://skills/<name>` | Full `SKILL.md` body |
| `synergy://skills/<name>/<relpath>` | A file under the skill directory, e.g. `references/ccm-help-query.md` |

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

- Reference tools by exact name with argument shape: `ccm_query(database, expression, fields)`.
- Quote tool docstrings verbatim where they define a contract; do not paraphrase.
- File paths in backticks.
- Tables for enumerable facts, prose for judgement calls.
- Cross-link sibling skills by name in bold: load the **`synergy-ccm-reference`** skill.

## Anti-patterns

- **Duplicating the CLI manual.** A skill is operating instructions, not a reference dump. Bulk reference belongs in `references/` and is fetched on demand.
- **Restating tool schemas.** The client already has them. Say when to use a tool, not what its parameters are.
- **Soft safety language.** "Try to avoid" is not a rule. Rules are imperative and absolute, and are mirrored by server-side enforcement.
- **Speculative loading.** Do not tell the model to load three skills "for context".
