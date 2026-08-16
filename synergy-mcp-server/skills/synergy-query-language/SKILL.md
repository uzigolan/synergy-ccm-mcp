---
name: synergy-query-language
description: "Synergy query grammar and recipes for Rational Synergy 7.2. Load whenever the user addresses 'synergy'. Use when the user asks to find objects, tasks, projects or baselines by criteria, or needs a Synergy query expression written, narrowed or explained."
version: 1.1.0
families: [ccm72]
servers: [synergy-ccm-mcp, synergy-mcp]
requires_tools:
  - query
  - find_tasks
  - find_baselines
  - find_releases
  - list_attributes
---

# Synergy Query Language

> **Skill version:** 1.1.0 · updated 2026-08-16. Adds dates, wildcards, aggregation and attribute discovery.

**Contents:** [Session self-check](#session-self-check) · [Golden rules](#golden-rules) · [Core patterns](#core-patterns) · [Dates](#dates) · [Wildcards](#wildcards) · [Aggregation](#aggregation) · [Recipes](#recipes) · [Cost discipline](#cost-discipline) · [Versions](#versions)

## Session self-check

Confirm `health_check(database)` has succeeded. If the exposed tool is named `query` rather than `ccm_query`, use the live tool name.

## Golden rules

1. **Use `cvtype` for object category.** `cvtype='task'`, `cvtype='problem'`, `cvtype='project'`, `cvtype='baseline'`, `cvtype='releasedef'` identify Synergy object classes.
2. **Use `type` for file type.** `type='csrc'` is site-defined and may not match every C source object.
3. **Never guess attribute names.** Call `list_attributes(database, cvtype)` first. `objectname` is **not** a queryable attribute — filtering on it fails with rc=6 and no output.
4. **Start narrow.** Query by exact `name`, `owner`, `release`, `status` or known object name before broad recursive functions.
5. **Count before you list.** For "how many" or "break down by", use `count_only=True` or `group_by=[...]` instead of fetching every row.
6. **Bound unknown result sets.** Pass `max_rows`; page with `offset`. Default cap is 500.
7. **Empty rows are a valid answer.** `rows: []` with `total_matched: 0` means no match, not a tool failure.

## Core patterns

| Goal | Query shape |
|---|---|
| Tasks for a release | `cvtype='task' and release='product/2.0'` |
| Completed release tasks | `cvtype='task' and release='product/2.0' and status='completed'` |
| Change requests | `cvtype='problem' and crstatus='assigned'` |
| Release definitions | `cvtype='releasedef' and name match '*etx2i*'` |
| One file's versions | `name='parser.c' and cvtype='csrc'` |
| User working objects | `owner='uzi' and status='working'` |
| Checked-in source not released | `type='csrc' and status='integrate'` |
| Modified after a date | `modify_time>time('1/1/2026')` |
| Direct project members | `is_member_of('core-int:project:1')` |
| Recursive project members | `hierarchy_project_members('core-int:project:1','none')` |
| Successors of a version | `has_predecessor('parser.c-6:csrc:1')` |

## Dates

Date attributes take a `time('M/D/YYYY')` literal:

```text
completion_date>time('2/1/2026')
entry_date>time('2/1/2026') and entry_date<time('8/1/2026')
```

The convenience tools normalize dates for you — `completed_since` / `completed_until` on
`find_tasks` and `entered_since` / `entered_until` on `find_crs` all accept:

| Input | Meaning |
|---|---|
| `2/1/2026` | US form, passed through |
| `2026-02-01` | ISO form |
| `H1 2026` / `H2 2026` | 1 Jan / 1 Jul of that year |
| `last 6 months` | relative to today |

Common date fields: `create_time`, `modify_time`, `completion_date` (task),
`entry_date`, `resolution_date`, `conclusion_date` (problem).

## Wildcards

Use the `match` operator with `*` and `?` — never `=` — for partial names:

```text
cvtype='task' and release match 'etxa*'
cvtype='releasedef' and name match '*etx2i*'
```

`find_tasks(release_match='etxa*')` and `find_crs(release_match='etxa*')` wrap this.
Rolling up a product line always needs `match`, since `release='etxa'` matches nothing.

## Aggregation

Do not pull thousands of rows to count them.

```text
query(db, "cvtype='task' and release match 'etxa*'", ["release"], count_only=True)
find_tasks(db, release_match="etxa*", completed_since="H1 2026",
           group_by=["release", "resolver"])
```

`group_by` fields must be present in `fields`. The response carries `groups`
(sorted by count), `distinct_groups` and `total_matched`.

For spreadsheet hand-off use `format="csv"` or `format="tsv"`; the rows come back
as a `text` blob instead of JSON. The server never writes files.

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

Prefer one structured query with fields over N property lookups. Use recursive project functions only after direct-member queries show the scope is reasonable. Count or group first, then drill into the specific rows the user asks about.

## Versions

| Skill | Version | Applies to |
|---|---|---|
| synergy-query-language | 1.1.0 | Rational Synergy 7.2 / 7.2.1 |