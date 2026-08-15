---
name: synergy-query-language
description: "Synergy query grammar and recipes for Rational Synergy 7.2. Use when the user asks to find objects, tasks, projects or baselines by criteria, or needs a Synergy query expression written, narrowed or explained."
version: 1.0.0
families: [ccm72]
servers: [synergy-ccm-mcp, synergy-mcp]
requires_tools:
  - query
  - find_tasks
  - find_baselines
---

# Synergy Query Language

> **Skill version:** 1.0.0 · updated 2026-08-15. Initial query-language workflow skill.

**Contents:** [Session self-check](#session-self-check) · [Golden rules](#golden-rules) · [Core patterns](#core-patterns) · [Recipes](#recipes) · [Cost discipline](#cost-discipline) · [Versions](#versions)

## Session self-check

Confirm `health_check(database)` has succeeded. If the exposed tool is named `query` rather than `ccm_query`, use the live tool name.

## Golden rules

1. **Use `cvtype` for object category.** `cvtype='task'`, `cvtype='project'`, `cvtype='baseline'` identify Synergy object classes.
2. **Use `type` for file type.** `type='csrc'` is site-defined and may not match every C source object.
3. **Start narrow.** Query by exact `name`, `owner`, `release`, `status` or known object name before broad recursive functions.
4. **Ask for fields deliberately.** Include only fields needed for the answer: `objectname`, `status`, `owner`, `task`, `release`, `create_time`, `modify_time`.
5. **Bound unknown result sets.** Pass `max_rows` for broad searches.
6. **Empty rows are a valid answer.** `rows: []` with `total_matched: 0` means no match, not a tool failure.

## Core patterns

| Goal | Query shape |
|---|---|
| Tasks for a release | `cvtype='task' and release='product/2.0'` |
| Completed release tasks | `cvtype='task' and release='product/2.0' and status='completed'` |
| One file's versions | `name='parser.c' and cvtype='csrc'` |
| User working objects | `owner='uzi' and status='working'` |
| Checked-in source not released | `type='csrc' and status='integrate'` |
| Modified after a date | `modify_time>time('Mon Jan 1 2026')` |
| Direct project members | `is_member_of('core-int:project:1')` |
| Recursive project members | `hierarchy_project_members('core-int:project:1','none')` |
| Successors of a version | `has_predecessor('parser.c-6:csrc:1')` |

## Recipes

Find file versions:

```text
query(database, "name='parser.c' and cvtype='csrc'", ["objectname", "status", "owner", "task"])
```

Find release tasks:

```text
find_tasks(database, release="product/2.0", status="completed", max_rows=200)
```

Find direct project members:

```text
query(database, "is_member_of('core-int:project:1')", ["objectname", "status", "owner", "task"], max_rows=500)
```

## Cost discipline

Prefer one structured query with fields over N property lookups. Use recursive project functions only after direct-member queries show the scope is reasonable.

## Versions

| Skill | Version | Applies to |
|---|---|---|
| synergy-query-language | 1.0.0 | Rational Synergy 7.2 / 7.2.1 |