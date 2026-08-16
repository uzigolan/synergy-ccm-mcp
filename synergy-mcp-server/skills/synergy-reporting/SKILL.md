---
name: synergy-reporting
description: "Effort analysis and metrics reporting over Rational Synergy. Load whenever the user addresses 'synergy'. Use when the user asks how much work was done in a period, throughput per developer or release, open vs closed counts, release readiness, period-over-period comparisons, or wants a CSV/table export for a spreadsheet."
version: 1.0.0
families: [ccm72]
servers: [synergy-ccm-mcp, synergy-mcp]
requires_tools:
  - query
  - find_tasks
  - find_crs
  - task_objects_bulk
  - find_releases
---

# Synergy Reporting And Effort Analysis

> **Skill version:** 1.0.0 · updated 2026-08-16. Initial reporting workflow skill.

**Contents:** [Session self-check](#session-self-check) · [Golden rules](#golden-rules) · [Count-first workflow](#count-first-workflow) · [Report patterns](#report-patterns) · [Export](#export) · [Pitfalls](#pitfalls) · [Versions](#versions)

## Session self-check

Confirm `health_check(database)` has succeeded, then confirm the release scope with `find_releases(database, pattern)` before running period queries. Guessing a release name wastes a slow round trip.

## Golden rules

1. **Count first, drill second.** Answer "how many" with `count_only=True` or `group_by`, never by fetching rows and tallying them.
2. **Never loop per task.** Use `task_objects_bulk` for object rollups; it caps at 100 tasks and returns `file_frequency` directly.
3. **State the window explicitly.** Every metric needs a date field and a range — say which one you used (`completion_date` vs `entry_date` give different answers).
4. **Separate open from closed.** A release report that only counts completed work overstates readiness.
5. **Report the query.** Include the expression and `total_matched` so the number is reproducible.
6. **Do not write files.** The server is read-only; return CSV text and let the user save it.

## Count-first workflow

```text
1. find_releases(db, "etxa")                          → confirm the release names
2. find_tasks(db, release_match="etxa*",
              completed_since="H1 2026",
              count_only=True)                        → is this 20 rows or 2000?
3. find_tasks(db, ..., group_by=["release","resolver"]) → the actual breakdown
4. find_tasks(db, ..., max_rows=50)                   → only if rows are needed
```

Step 2 costs one query and decides whether steps 3-4 are affordable.

## Report patterns

**Throughput by person**

```text
find_tasks(database, release_match="etxa*", completed_since="H1 2026",
           group_by=["resolver"])
```

**Period-over-period**

Run the same grouped query twice with different windows and compare:

```text
find_tasks(db, release_match="etxa*", completed_since="H1 2026", group_by=["release"])
find_tasks(db, release_match="etxa*", completed_since="H1 2025",
           completed_until="1/1/2026", group_by=["release"])
```

**Release readiness**

```text
find_tasks(database, release="etxa/6.8.7", group_by=["status"])
find_crs(database, release="etxa/6.8.7", group_by=["crstatus", "severity"])
```

Report completed, assigned and in-verification separately, and call out any high-severity CR not yet concluded.

**Defect inflow vs outflow**

```text
find_crs(db, entered_since="H1 2026", count_only=True)      → opened
find_crs(db, crstatus="concluded", entered_since="H1 2026") → closed
```

**Change hotspots**

```text
find_tasks(db, release="etxa/6.8.7", completed_since="last 6 months", max_rows=100)
task_objects_bulk(db, [task ids from above])
→ read file_frequency, report the top files
```

## Export

```text
find_tasks(database, release_match="etxa*", completed_since="1/2/2026",
           format="csv", max_rows=1000)
```

Returns a `text` field of CSV instead of `rows`. Offer to write it into the user's workspace as a separate step — the MCP itself cannot write files.

## Pitfalls

| Pitfall | Consequence |
|---|---|
| `release='etxa'` instead of `release match 'etxa*'` | Zero rows, looks like no work happened |
| Ignoring `truncated: true` | Silent undercount |
| Using `create_time` for "work done" | Counts started, not finished, work |
| Counting fix tasks as separate effort | Inflates throughput — fix tasks reference their parent in the synopsis |
| Automatic tasks in the total | `task_automatic` rows are containers, not work |

Filter out `status='task_automatic'` for effort metrics unless the user asks for everything.

## Versions

| Skill | Version | Applies to |
|---|---|---|
| synergy-reporting | 1.0.0 | Rational Synergy 7.2 / 7.2.1 |
