# 03 — Session Pooling

**Status:** accepted · **Phase:** 1

**Contents:** [Context](#context) · [Decision](#decision) · [Rejected alternatives](#rejected-alternatives) · [Consequences](#consequences)

## Context

Synergy has no stateless mode. Every `ccm` command runs inside a session identified by `CCM_ADDR`, and a session:

- takes 5–60 s to establish
- consumes a **floating licence seat** for its lifetime
- is not safe for concurrent commands
- dies on server-side idle timeout, on network interruption, and when an administrator cleans up

A naive implementation starting a session per tool call would make every call take a minute and would exhaust the site's seat pool within a handful of requests. This is the single most consequential implementation decision in the server.

## Decision

**One long-lived session per database**, held by `SessionManager`:

- Created lazily on first use of that database. Listing the inventory opens nothing.
- Keyed by inventory name, guarded by a per-database `threading.Lock`, so commands on one session are serialised.
- `CCM_ADDR` is injected into the environment of each invocation, never passed as an argument.
- Stopped at process exit — but only if the server started it.

**Stale-session recovery:** a failure whose output matches `not a valid session`, `session has been terminated` or `cannot connect to` drops the cached session and retries **once**. A second failure propagates. The user experiences one slow call rather than an error.

**Attach mode** is first-class and recommended for production. If `SYNERGY_<DB>_CCM_ADDR` is set, the server never runs `ccm start`, never handles a password, and never stops the session on shutdown. `health_check` reports `session_owned_by_server: false`.

## Rejected alternatives

**Session per call.** Correct and simple; unusable. 5–60 s per call and seat churn that would get the server banned by the CM administrator.

**Session per client connection.** Ties seat consumption to the number of MCP clients, which is exactly the wrong axis. Ten developers on one shared server should cost one seat per database, not ten.

**A pool of N sessions per database for concurrency.** Multiplies seat consumption to buy throughput nobody has asked for. Serialisation via a lock is the right default; if a site later needs parallelism, it can run a second server instance.

**Background keepalive pings.** Considered — periodic `ccm status` to prevent idle timeout. Rejected as unnecessary complexity: the stale-retry path already handles expiry transparently, and a keepalive thread would hold seats indefinitely even when nobody is working.

## Consequences

- Concurrent tool calls against one database serialise. Correctness over throughput, deliberately.
- A long-lived server holds seats all day. This is documented in [performance.md](../performance.md#licence-seats) and is the reason attach mode exists.
- Password handling is a real concern in non-attach mode: `ccm start -pw <password>` exposes the credential in the process table on a shared host. Attach mode avoids it entirely; the `redact()` helper keeps it out of logs but cannot keep it out of `ps`. This limitation is stated in the install guide rather than hidden.
- `health_check` is the mandated first call in every workflow because it is what materialises the session and surfaces licence or connectivity failures with a clear message instead of a confusing one mid-query.
