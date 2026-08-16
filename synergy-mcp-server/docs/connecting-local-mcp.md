# Connecting a Local MCP Client

**Contents:** [Prerequisites](#prerequisites) · [Install](#install) · [Inventory](#inventory) · [Credentials](#credentials) · [Attach mode](#attach-mode-recommended) · [Client config](#client-config) · [Verify](#verify) · [Environment reference](#environment-reference) · [Troubleshooting](#troubleshooting)

All paths and commands are relative to the repo root, `synergy-ccm-mcp/`.

## Prerequisites

- The Synergy 7.2 `ccm` client installed and on `PATH`, with `CCM_HOME` set.
- Python ≥ 3.10 on the same host as the `ccm` client.
- A Synergy user account with read access to the target database.

Confirm the client is reachable before touching the server:

```bash
ccm version
echo "$CCM_HOME"
```

## Install

Windows PowerShell:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\mcp_server\install-stdio-mcp-server.ps1
```

Linux bash:

```bash
bash ./synergy-mcp-server/scripts/install/mcp_server/install-stdio-mcp-server.sh
```

## Inventory

The installer creates `synergy-mcp/inventory.yaml` from `synergy-mcp/inventory.example.yaml` if needed.

Edit it to describe your databases. Facts only — **never credentials**:

```yaml
databases:
  - name: prod-core
    database: /opt/ccm/db/core
    host: buildhost
    server_url: http://buildhost:8400
    role: developer
    groups: [production]
    description: "Core product, production database"
```

## Credentials

Secrets are set out-of-band by a human. The server never writes them and the model never sees them. In the normal read-only deployment, configure one MCP-level Synergy identity:

```bash
synergy-mcp-set-credentials --user uzi
```

Store `SYNERGY_MCP_USER` and `SYNERGY_MCP_PASSWORD` in the environment used to launch the MCP server. Every client using this MCP server then accesses Synergy through that same account. For phase 1, use a Synergy account with read access only, because the enabled `query`, `object`, `task` and `project` groups are all read-only.

Per-database overrides are still available for exceptional cases: set `SYNERGY_<DB>_USER` and `SYNERGY_<DB>_PASSWORD`, where `<DB>` is the inventory name upper-cased with non-alphanumerics replaced by `_`. Do not edit `inventory.yaml` to add a `password:` key — the loader rejects that outright.

## Attach mode (recommended)

Better than giving the server a password: start the Synergy session yourself and let the server attach to it.

```bash
ccm start -m -q -nogui -d /opt/ccm/db/core \
          -s http://buildhost:8400 -r developer -n uzi -pw -
# prints e.g. buildhost:1234:10.0.0.5

export SYNERGY_PROD_CORE_CCM_ADDR=buildhost:1234:10.0.0.5
```

The server then never handles a credential, and it will not stop the session on shutdown. `health_check` reports `session_owned_by_server: false`.

## Client config

VS Code workspace config, `.vscode/mcp.json`:

```json
{
  "servers": {
    "synergy-ccm-mcp": {
      "type": "stdio",
      "command": "synergy-mcp/.venv/bin/python",
      "args": ["-m", "synergy_mcp"],
      "env": {
        "SYNERGY_MCP_INVENTORY": "synergy-mcp/inventory.yaml"
      }
    }
  }
}
```

The VS Code installer writes this automatically. Claude Desktop users can build a local MCPB with [INSTALL-claude-desktop-mcpb.md](../../INSTALL-claude-desktop-mcpb.md).

## Verify

```
list_databases()
health_check(database="prod-core")
ccm_version(database="prod-core")
```

Then read `synergy://status` and confirm the profile and enabled groups are what you expect.

## Environment reference

| Variable | Default | Meaning |
|---|---|---|
| `SYNERGY_MCP_TOOL_PROFILE` | `lean` | `lean` or `legacy` |
| `SYNERGY_MCP_READONLY` | `true` | Phase 1 keeps this true |
| `SYNERGY_MCP_TASK` | `true` | Enable the task group |
| `SYNERGY_MCP_PROJECT` | `true` | Enable the project group |
| `SYNERGY_MCP_INVENTORY_WRITE` | `false` | Enable inventory CRUD tools |
| `SYNERGY_MCP_DEV_TOOLS` | `false` | Enable demo-database tools |
| `SYNERGY_MCP_REQUIRE_SKILLS` | `true` | Require the core skill before privileged calls |
| `SYNERGY_CCM_BINARY` | `ccm` | Path to the client |
| `SYNERGY_MCP_ROOT` | auto | Override `synergy-mcp-server/` location |
| `SYNERGY_MCP_INVENTORY` | auto | Override inventory path |
| `SYNERGY_MCP_LOG_DIR` | `logs/` | Audit log destination |
| `SYNERGY_MCP_USER` | — | Shared Synergy user for all databases without an override |
| `SYNERGY_MCP_PASSWORD` | — | Shared Synergy password for all databases without an override |
| `SYNERGY_<DB>_USER` | — | Per-database user |
| `SYNERGY_<DB>_PASSWORD` | — | Per-database password |
| `SYNERGY_<DB>_CCM_ADDR` | — | Attach mode session address |

`<DB>` is the inventory name upper-cased with non-alphanumerics replaced by `_`: `prod-core` → `PROD_CORE`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ccm binary 'ccm' not found` | `CCM_HOME/bin` not on the server process's `PATH` | Set `SYNERGY_CCM_BINARY` to the absolute path |
| `Could not parse CCM_ADDR` | Site-specific `ccm start` flags | Adjust `start_flags:` in the inventory entry |
| `UNAVAILABLE: licence` | Seat pool exhausted | Use attach mode; one session per database, not per call |
| Session dies after idle | Server-side session timeout | Expected; the pool restarts transparently on the next call |
| No tools appear | Profile disabled every group | Read `synergy://status`; check `tool_profile.config.json` |
