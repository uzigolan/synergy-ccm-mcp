# Performance

**Contents:** [Where time goes](#where-time-goes) · [Session pooling](#session-pooling) · [Licence seats](#licence-seats) · [Query cost](#query-cost) · [Result caps](#result-caps) · [Field selection](#field-selection) · [Call patterns](#call-patterns) · [Timeouts](#timeouts) · [Benchmarks to collect](#benchmarks-to-collect)

## Where time goes

| Operation | Typical | Dominated by |
|---|---|---|
| `ccm start` | 5–60 s | Session setup, licence checkout |
| `ccm version`, `ccm delim` | 0.2–0.5 s | Process spawn |
| `ccm query` (bounded, indexed) | 0.3–2 s | Database |
| `ccm query` (unbounded hierarchy) | 10 s – minutes | Database |
| `ccm cat` | 0.3–1 s | Object size |
| `ccm history` | 0.5–3 s | Version count |

The first row is why sessions are pooled. The last three are why queries are bounded.

## Session pooling

One session per database, held for the process lifetime, guarded by a per-database lock.

- Cost is paid once, on first use of a database, not per tool call.
- Listing the inventory does **not** open a session.
- A stale session triggers one transparent restart. The user sees a slow call, not an error.
- Concurrency is serialised per database by the lock — a `ccm` session is not safe for concurrent commands.

Serialisation is a deliberate trade: correctness over throughput. If you need parallelism, run multiple databases, not multiple commands per session.

## Licence seats

Seats, not CPU, are the binding constraint at most sites.

- N databases in the inventory that get used ⇒ N seats.
- Seats are held until process exit. A long-lived server holds them all day.
- **Attach mode** (`SYNERGY_<DB>_CCM_ADDR`) reuses a seat a human already owns and returns nothing on shutdown.
- One shared HTTP server consumes far fewer seats than one stdio server per developer.

`health_check` reports `session_owned_by_server` so you can account for what the server is holding.

## Query cost

The query planner is not yours to control, but the query is:

- Filter on indexed attributes first: `cvtype`, `type`, `status`, `owner`, `release`.
- `name='x'` is cheap; substring matching with `match` is not.
- `is_member_of()` is bounded by one project's member list — cheap.
- `hierarchy_project_members()` walks the whole subtree — expensive, and on a product-level project can return tens of thousands of rows.
- `modify_time>time(...)` is effective at cutting result sets; prefer it to post-filtering.

Rule of thumb: get the direct-member count before ever going recursive.

## Result caps

`max_rows` defaults to 500 and is clamped by `settings.max_rows` in the inventory. Truncation is always reported:

```json
{"returned": 500, "total_matched": 21874, "truncated": true}
```

The correct response to truncation is to narrow the expression, not to page through 21 874 rows into the context window. `total_matched` is provided precisely so the model can tell the user the query was too broad without fetching everything.

Raw text output is separately capped by `max_output_bytes` (200 000) with an explicit truncation marker.

## Field selection

`ccm_query` sends `-f` with only the fields you asked for. Requesting five fields instead of twelve is a direct, linear saving in both database work and context tokens.

Default field set is `objectname, status, owner, type, create_time`. Override it when you need less:

```
ccm_query(db, "cvtype='task' and release='product/2.0'", ["displayname", "task_synopsis"])
```

## Call patterns

| Anti-pattern | Cost | Instead |
|---|---|---|
| `ccm_query` then `object_properties` per row | N+1 round trips | Ask for the fields in the query |
| `health_check` before every operation | 0.3 s each | Once per session |
| Recursive `project_members` to count files | Minutes | Non-recursive first, then decide |
| Fetching two versions to diff them | 2 calls, large payloads | `object_diff` |
| `run_readonly_command` for something with a tool | Unstructured output | Use the dedicated tool |

## Timeouts

| Setting | Default | Applies to |
|---|---|---|
| `command_timeout` | 120 s | Every `ccm` invocation except `start` |
| `start_timeout` | 300 s | `ccm start` |

Both are configurable per deployment in `inventory.yaml` under `settings:`. A timeout raises `UNAVAILABLE:` with the command that hung — it never leaves the server blocked.

## Benchmarks to collect

Before tuning anything, measure on your own database. `scripts/bench_queries.py` should record, per database:

- session start time
- `ccm version` round-trip (process spawn floor)
- a bounded query at 100 / 500 / 2000 rows
- direct vs recursive `project_members` on your largest project

Site databases differ by orders of magnitude. Defaults in this repo are starting points, not tuned values.
