# Integration Guide

**Contents:** [Deployment shapes](#deployment-shapes) · [Combined server](#combined-server) · [Standalone packages](#standalone-packages) · [Remote HTTP](#remote-http) · [Scopes and interlocks](#scopes-and-interlocks) · [Multi-database fleets](#multi-database-fleets) · [Licence budgeting](#licence-budgeting) · [Coexisting with other MCP servers](#coexisting-with-other-mcp-servers) · [CI usage](#ci-usage)

## Deployment shapes

| Shape | When | Entry point |
|---|---|---|
| Combined stdio server | Desktop / single developer | `python -m synergy_mcp` |
| Standalone package | You want only one capability | `synergy-db` |
| Remote HTTP | Shared team instance | `python -m synergy_mcp --http` |

The `ccm` client must be local to whichever process runs the backend. In remote HTTP shape, the server sits on the build host beside Synergy; the clients are elsewhere.

## Combined server

Registers every enabled group into one FastMCP app. This is the default and what `.mcp.json` points at.

```bash
cd rad-synergy-toolkit
bash ./synergy-mcp-server/scripts/install/mcp_server/install-stdio-mcp-server.sh
. synergy-mcp/.venv/bin/activate
python -m synergy_mcp
```

## Standalone packages

Each capability package ships its own entry point, so a deployment can expose a strict subset without relying on profile flags:

```bash
synergy-db        # session + query + object + task + project groups only
```

Version lock: every package pins the same version as `synergy-mcp`. Mismatches fail `scripts/check_contracts.py` in CI. Do not upgrade one package independently.

## Remote HTTP

```bash
python -m synergy_mcp --http --host 0.0.0.0 --port 8770
```

Bearer tokens are configured out-of-band in `server/.synergy-mcp-tokens`, one per line:

```
<token>  <scopes>
abc123…  read
def456…  read,write
```

Serve behind TLS. The Synergy database contains proprietary source code; the transport carries it verbatim.

## Scopes and interlocks

Three interlocks:

1. **Registration gate** — a group that the profile disables is never registered. Tools that do not exist cannot be called.
2. **Per-call scope check** — over HTTP, privileged tools call `require_write_scope()`; a read-scoped token is refused.
3. **Skill-layer gate** — when `SYNERGY_MCP_REQUIRE_SKILLS=true`, a session that has not fetched `synergy://skills/synergy-core` is refused privileged calls with an instruction to read the skill first.

In phase 1 there are no write tools, so interlocks 2 and 3 guard only the flag-gated `inventory` group. They exist now so phase 3 does not have to introduce security machinery under deadline.

## Multi-database fleets

`inventory.yaml` may list many databases; `groups:` tags let a query target a subset.

```yaml
databases:
  - name: core-prod
    groups: [production, core]
  - name: core-dev
    groups: [lab, core]
  - name: telecom-prod
    groups: [production, telecom]
```

```
list_databases(group="production")
```

Sessions are created lazily, on first use of a database — listing the inventory does not open sessions or consume seats.

## Licence budgeting

This is the operational constraint that most affects design.

- One pooled session per database, held for the process lifetime.
- N databases in play ⇒ N seats consumed, not N × tool calls.
- Prefer attach mode in production so the seat is one a human already owns and can reclaim.
- `health_check` reports `session_owned_by_server` so you can tell which seats the server is holding.

If your site has a small seat pool, run one shared HTTP server rather than one stdio server per developer.

## Coexisting with other MCP servers

`synergy-ccm-mcp` uses its own resource scheme (`synergy://`) and tool names that are prefixed or domain-specific enough not to collide with typical Git, issue-tracker or filesystem servers. Running it alongside others is expected.

The cost of running several servers is the **union of their tool schemas**, charged on every turn. Keep each on its leanest profile. See [dynamic-tool-discovery-and-routing.md](dynamic-tool-discovery-and-routing.md#token-economics).

When both a Git server and this one are present, route by system of record: history before the Synergy-to-Git migration lives here; anything after it lives in Git. State which one an answer came from.

## CI usage

Read-only phase 1 is safe to run in CI against a real database:

```bash
export SYNERGY_MCP_READONLY=true
export SYNERGY_CORE_PROD_CCM_ADDR="$CCM_ADDR"
python -m synergy_mcp.smoke --database core-prod
```

`smoke.py` opens the session, runs `version`, `delim` and a bounded query, and writes `logs/smoke-<timestamp>.txt`. It never mutates.
