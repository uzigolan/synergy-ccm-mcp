# Synergy Concepts for Agents

**Contents:** [Why this exists](#why-this-exists) · [Object model](#object-model) · [Four-part names](#four-part-names) · [Types](#types) · [Lifecycle states](#lifecycle-states) · [Task-based CM](#task-based-cm) · [Projects and hierarchies](#projects-and-hierarchies) · [Baselines and releases](#baselines-and-releases) · [Sessions and work areas](#sessions-and-work-areas) · [Vocabulary map](#vocabulary-map)

## Why this exists

Synergy predates Git and does not share its mental model. An agent that assumes "commit / branch / repo" will produce wrong queries and wrong conclusions. This document is the domain grounding; `skills/synergy-core/SKILL.md` is the operational rulebook.

## Object model

Everything in Synergy is an **object** stored in a database, including things Git would treat as metadata:

- a file version is an object
- a directory is an object
- a **project** is an object
- a **task** is an object
- a **folder**, **baseline**, **release definition** and **change request** are objects

This is why one tool — `ccm_query` — answers most questions. There is no separate "log" or "branch" command; you query objects.

## Four-part names

The universal identifier is the **four-part name**:

```
name  -  version  :  type  :  instance
main.c   -    3    :  csrc  :    1
```

- `name` — the object's name
- `version` — a string, not a number (`3`, `1.2.1`, `int_20250114`)
- `type` — the `cvtype` (see below)
- `instance` — disambiguates objects that share name and type across subsystems (usually `1`)

The delimiter between name and version is **database-configurable** (`-` or `~`). Never hard-code it; read it with `ccm delim`.

A project version looks the same: `mymodule-int:project:1`.

## Types

| `cvtype` | Meaning |
|---|---|
| `csrc` | C source file (the exact set is site-defined: `ascii`, `binary`, `makefile`, `shsrc`, …) |
| `dir` | Directory object |
| `project` | A versioned collection of members |
| `task` | A unit of change grouping object versions |
| `folder` | A query-based or manual collection of tasks |
| `releasedef` | A release definition, e.g. `product/2.0` |
| `baseline` | A snapshot of projects and tasks at a point in time |
| `problem` | Change-request object (only if Change is integrated) |

`type=` filters the file type; `cvtype=` filters the object category. They are not interchangeable.

## Lifecycle states

The default four-state lifecycle, though sites customise it:

| `status` | Meaning |
|---|---|
| `working` | Checked out, private to one developer, mutable |
| `visible` | Optional intermediate state |
| `integrate` | Checked in, visible to the integration build |
| `test` | Promoted to test |
| `released` | Frozen; a released version is immutable |

An object in `working` state is owned by exactly one user and is the only mutable form. Everything else is immutable — which is why a read-only server can still answer almost every question.

## Task-based CM

This is the central concept and the biggest departure from Git.

- A developer creates a **task** ("fix null deref in parser").
- Every checkout/checkin is **associated with that task**.
- Completing the task moves its objects to `integrate` together.
- Tasks are grouped into **folders** by query (e.g. "all completed tasks for release 2.0").
- Folders are collected into a **project grouping**, which determines what a project's members resolve to.

Consequence: **"what changed" is a task question, not a file question.** To find why a file changed, get the file's task, then that task's other objects — the task is the change set.

```
ccm query "cvtype='task' and release='product/2.0' and status='completed'"
ccm task -show objects 4711
```

## Projects and hierarchies

A **project** is a versioned object whose members are file and directory objects — and other projects. A real product is therefore a *hierarchy* of project versions.

Two different queries:

| Question | Query function |
|---|---|
| Direct members of this project only | `is_member_of('proj-1:project:1')` |
| Every member of the whole subtree | `hierarchy_project_members('proj-1:project:1','none')` |

`hierarchy_project_members` on a large product can return tens of thousands of rows. Always bound it.

## Baselines and releases

- A **release** (`releasedef`) is a label like `product/2.0` that scopes tasks, folders and projects.
- A **baseline** is an immutable snapshot: a set of project versions plus the tasks that produced them.

Comparing two baselines is the Synergy equivalent of `git diff v1.0..v2.0`, and it is answered by comparing their task sets, not their file trees.

## Sessions and work areas

- A **session** is a connection to the database, identified by `CCM_ADDR`. It holds a licence seat.
- A **work area** is the on-disk materialisation of a project version. Read-only tooling does not need one.

`ccm cat` reads content straight from the database, so file content is available without any work area — this is what makes a read-only server useful.

## Vocabulary map

Approximate translations. Treat them as intuition pumps, not equivalences.

| Git | Synergy | Caveat |
|---|---|---|
| commit | **task** | A task is a *set* of object versions, closer to a changeset than a commit. |
| commit message | task synopsis | |
| branch | project version / release | Synergy versions objects, not the repo. |
| tag | baseline | A baseline names project *versions*, not a tree hash. |
| working tree | work area | Materialised on demand; not required for reads. |
| `git log <file>` | `ccm history <object>` | |
| `git blame` | object history + task lookup | No line-level attribution. |
| `git grep` | `ccm query` + `ccm cat` | No server-side content search. |
| repository | database | One database holds many products. |
