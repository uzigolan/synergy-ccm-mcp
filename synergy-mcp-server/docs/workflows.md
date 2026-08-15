# Workflows

**Contents:** [Session opening](#session-opening) · [Who changed this file](#who-changed-this-file) · [What is in this release](#what-is-in-this-release) · [Compare two baselines](#compare-two-baselines) · [Audit a developer's work](#audit-a-developers-work) · [Reconstruct a file version](#reconstruct-a-file-version) · [Find where an object is used](#find-where-an-object-is-used) · [Cost discipline](#cost-discipline)

Each workflow below has a matching prompt in `synergy_core/prompts.py` and a slash command in `commands/`.

## Session opening

Always the same three steps. Do not skip them; a wrong assumption about the delimiter or the lifecycle states poisons every later query.

1. `health_check(database)` — opens or verifies the pooled session.
2. `ccm_version(database)` — confirm the client really is 7.2.
3. `run_readonly_command(database, ["delim"])` — learn the name/version delimiter for this database.

## Who changed this file

The Synergy answer is a *task* answer, not a file answer. See [CONCEPTS.md](CONCEPTS.md#task-based-cm).

```
1. ccm_query(db, "name='parser.c' and cvtype='csrc'", ["objectname","status","owner"])
      -> pick the version of interest
2. object_history(db, "parser.c-7:csrc:1")
      -> predecessors and successors
3. ccm_query(db, "is_associated_object_of(task('4711'))")   # or:
   object_properties(db, "parser.c-7:csrc:1")               # read the 'task' attribute
4. task_info(db, "4711")
      -> synopsis, resolver, release, completion date
5. task_objects(db, "4711")
      -> the rest of the change set: the other files that changed with it
```

Step 5 is the one people forget. A file version in isolation is half the story; the task is the change.

## What is in this release

```
find_tasks(db, release="product/2.0", status="completed")
```

Then, for anything that looks incomplete:

```
find_tasks(db, release="product/2.0", status="assigned")
```

Report both. "Release 2.0 has 214 completed tasks and 9 still assigned" is a materially different answer from "release 2.0 has 214 tasks".

## Compare two baselines

Baselines are compared by **task set**, not by file tree.

```
1. find_baselines(db, release="product/2.0")
      -> identify the two baseline objects
2. object_properties(db, "<baseline-a>")   # note its project versions
   object_properties(db, "<baseline-b>")
3. ccm_query(db, "is_task_in_folder_of(...)")  per baseline's folders
4. Set-difference the task lists; report tasks present in B but not A.
```

If the baselines belong to different releases, say so explicitly — the diff is then not a clean superset relationship.

## Audit a developer's work

```
find_tasks(db, owner="uzi", release="product/2.0")
```

For each task of interest, `task_objects` gives the files touched. Aggregate, do not enumerate: report counts and notable files, then offer to drill in. A developer with 300 tasks will otherwise flood the context.

## Reconstruct a file version

No work area is needed — `ccm cat` reads from the database directly.

```
1. ccm_query(db, "name='config.xml' and cvtype='ascii'", ["objectname","status","create_time"])
2. object_content(db, "config.xml-12:ascii:1")
```

For a diff between two versions, prefer `object_diff` over fetching both and comparing in-context — it is one call instead of two and returns far fewer tokens.

## Find where an object is used

```
find_use(db, "libcommon.a-4:binary:1")
```

Answers "which project versions contain this object". This is the reverse-dependency question and has no cheap equivalent via `ccm_query`.

For the forward direction — what does this project contain — use `project_members(db, project, recursive=False)` first. Only escalate to `recursive=True` after confirming the direct-member count is small, because `hierarchy_project_members` on a product-level project can return tens of thousands of rows.

## Cost discipline

Every tool call is a subprocess spawn plus database round-trip, roughly 0.3–5 s.

- Ask for the fields you need in one `ccm_query` rather than querying then fetching properties per row.
- Bound every query. `max_rows` exists; use it deliberately rather than discovering the cap by hitting it.
- Prefer one `find_tasks` over N `task_info` calls when you only need synopses.
- Do not re-run `health_check` per operation. Once per session.
