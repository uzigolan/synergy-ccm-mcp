---
name: synergy-task-project
description: "Task, release, project and baseline workflows for Rational Synergy. Load whenever the user addresses 'synergy'. Use when the user asks what changed, what is in a release, which files a task touched, project members, baselines, project grouping, or release-readiness audits."
version: 1.1.0
families: [ccm72]
servers: [synergy-ccm-mcp, synergy-mcp]
requires_tools:
  - find_tasks
  - task_info
  - task_objects
  - task_objects_bulk
  - project_members
  - find_baselines
  - find_releases
  - project_grouping_info
---

# Synergy Task And Project Workflows

> **Skill version:** 1.1.0 · updated 2026-08-16. Adds release rollups, date windows and bulk object lookup.

**Contents:** [Session self-check](#session-self-check) · [Golden rules](#golden-rules) · [Tasks](#tasks) · [Release rollups](#release-rollups) · [Projects](#projects) · [Baselines and releases](#baselines-and-releases) · [Audit patterns](#audit-patterns) · [Versions](#versions)

## Session self-check

Confirm `health_check(database)` has succeeded. If task/project tools are missing, fall back to `query` and `run_readonly_command` only for read-only verbs.

## Golden rules

1. **A task is the change set.** Always list task objects when explaining a change.
2. **Release answers need open and completed work.** Report incomplete tasks alongside completed ones.
3. **Compare baselines by task set first.** Do not assume a file-tree diff is the primary Synergy answer.
4. **Use direct project members first.** Recursive hierarchy queries can be very large.
5. **Aggregate large audits.** Summarize counts and notable objects before drilling into every task.
6. **Never loop `task_objects`.** Use `task_objects_bulk` for more than a couple of tasks.
7. **A feature can be backported.** The release where a task completed is not always where the feature originated — check the whole `release_match` set before concluding.

## Tasks

Inspect one task:

```text
task_info(database, "4711")
task_objects(database, "4711")
```

Find tasks:

```text
find_tasks(database, owner="uzi", release="product/2.0", status="completed", max_rows=200)
```

Objects for many tasks at once, with a file-frequency rollup:

```text
task_objects_bulk(database, ["IL!257398", "IL!257416", "IL!257418"])
```

Capped at 100 tasks per call.

## Release rollups

A product line spans many release names. Discover them, then roll up:

```text
find_releases(database, "etxa")
find_tasks(database, release_match="etxa*", completed_since="H1 2026",
           group_by=["release"])
```

`release='etxa'` matches nothing — partial names always need `release_match`.
Date windows accept `2/1/2026`, `2026-02-01`, `H1 2026` or `last 6 months`.

## Projects

Direct members:

```text
project_members(database, "core-int:project:1", recursive=False, max_rows=500)
```

Recursive members:

```text
project_members(database, "core-int:project:1", recursive=True, max_rows=2000)
```

Project grouping:

```text
project_grouping_info(database, "core-int:project:1")
```

## Baselines and releases

Find baselines:

```text
find_baselines(database, release="product/2.0", max_rows=100)
```

Release audit pattern:

1. Find completed tasks for the release.
2. Find assigned/open tasks for the release.
3. For suspicious or high-impact tasks, call `task_objects`.
4. Report counts, statuses and notable change sets.

## Audit patterns

For "what has this developer done", query tasks by owner and release, then inspect only the tasks the user asks to drill into. Avoid flooding the context with hundreds of task bodies. For counts and period comparisons load **`synergy-reporting`**; for defect-driven questions load **`synergy-change-requests`**.

## Versions

| Skill | Version | Applies to |
|---|---|---|
| synergy-task-project | 1.1.0 | Rational Synergy 7.2 / 7.2.1 |