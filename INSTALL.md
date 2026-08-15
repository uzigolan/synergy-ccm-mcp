# Installing the Synergy CCM MCP Toolkit

**Contents:** [Installation kinds](#installation-kinds) · [Prerequisites](#prerequisites) · [Step 1 — Setup](#step-1--setup) · [Step 2 — Prepare the MCP server](#step-2--prepare-the-mcp-server) · [Step 3 — Configure Synergy access](#step-3--configure-synergy-access) · [Step 4 — Install a client target](#step-4--install-a-client-target) · [Step 5 — Verify](#step-5--verify) · [Update](#update) · [Troubleshooting](#troubleshooting)

This guide installs the local stdio Synergy MCP server. The same MCP server works on Windows or Linux as long as the IBM Rational Synergy `ccm` client is installed on that machine and can reach the target database.

## Installation kinds

| Kind | Use when | Guide |
|---|---|---|
| VS Code Copilot stdio | VS Code starts the MCP server locally | [INSTALL-vscode-copilot-stdio.md](INSTALL-vscode-copilot-stdio.md) |
| Claude Desktop MCPB | Claude Desktop imports a local extension bundle | [INSTALL-claude-desktop-mcpb.md](INSTALL-claude-desktop-mcpb.md) |

Both targets use the same Python package, inventory file, credential model and knowledge corpus.

## Prerequisites

- Python 3.10 or newer.
- Git.
- IBM Rational Synergy 7.2 or 7.2.1 `ccm` client on the same machine.
- A Synergy account with read access to the target database.

Confirm the Synergy client before installing the MCP server:

Windows PowerShell:

```powershell
ccm version
```

Linux bash:

```bash
ccm version
```

## Step 1 — Setup

New checkout:

```bash
git clone https://github.com/uzigolan/synergy-ccm-mcp.git rad-synergy-toolkit
cd rad-synergy-toolkit
```

Existing checkout:

```bash
cd rad-synergy-toolkit
git pull
```

## Step 2 — Prepare the MCP server

Windows PowerShell:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\mcp_server\install-stdio-mcp-server.ps1
```

Linux bash:

```bash
bash ./synergy-mcp-server/scripts/install/mcp_server/install-stdio-mcp-server.sh
```

This creates `synergy-mcp/.venv`, installs `synergy-mcp` into it, and creates `synergy-mcp/inventory.yaml` from `synergy-mcp/inventory.example.yaml` if needed.

## Step 3 — Configure Synergy access

Edit `synergy-mcp/inventory.yaml` and set the database path, host, server URL and role for your site.

Credentials are environment variables, not inventory fields. For one shared MCP-level Synergy identity:

Windows PowerShell:

```powershell
$env:SYNERGY_MCP_USER = "your-synergy-user"
$env:SYNERGY_MCP_PASSWORD = "your-synergy-password"
```

Linux bash:

```bash
export SYNERGY_MCP_USER="your-synergy-user"
export SYNERGY_MCP_PASSWORD="your-synergy-password"
```

Preferred for production: start `ccm` yourself and let the MCP server attach with `SYNERGY_<DB>_CCM_ADDR`, so the MCP process never handles a password.

## Step 4 — Install a client target

VS Code Copilot:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\skills_and_mcp\install-vscode-copilot-stdio.ps1
```

Claude Desktop MCPB:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\skills_and_mcp\install-claude-desktop-mcpb.ps1
```

Linux equivalents:

```bash
bash ./synergy-mcp-server/scripts/install/skills_and_mcp/install-vscode-copilot-stdio.sh
bash ./synergy-mcp-server/scripts/install/skills_and_mcp/install-claude-desktop-mcpb.sh
```

## Step 5 — Verify

In the MCP client, ask:

```text
List the Synergy databases you can see, then run health_check for prod-core.
```

Then ask a bounded read-only question:

```text
Find completed tasks for release product/2.0, max 20 rows.
```

## Update

```bash
cd rad-synergy-toolkit
git pull
```

Then rerun the relevant installer. Existing `inventory.yaml` is kept.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ccm` not found | Synergy client is not on `PATH` | Set `SYNERGY_CCM_BINARY` or update `PATH` |
| Inventory not found | `synergy-mcp/inventory.yaml` missing | Rerun the stdio server installer |
| No user/password | Env vars missing | Set `SYNERGY_MCP_USER` and `SYNERGY_MCP_PASSWORD`, or use attach mode |
| License exhaustion | Too many Synergy sessions | Prefer attach mode or a shared server process |
| Client shows no server | Config not reloaded | Restart/reload the client after install |