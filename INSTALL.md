# Installing the Synergy CCM MCP Toolkit

**Contents:** [Installation kinds](#installation-kinds) · [Prerequisites](#prerequisites) · [Step 1 — Setup](#step-1--setup) · [Step 2 — Prepare the MCP server](#step-2--prepare-the-mcp-server) · [Step 3 — Configure/Update Synergy credentials](#step-3--configureupdate-synergy-credentials) · [Step 4 — Install a client target](#step-4--install-a-client-target) · [Step 5 — Verify](#step-5--verify) · [Update](#update) · [Troubleshooting](#troubleshooting)

This guide installs the local stdio Synergy MCP server. The same MCP server works on Windows or Linux as long as the IBM Rational Synergy `ccm` client is installed on that machine and can reach the target database.

## Installation kinds

| Kind | Use when | Guide |
|---|---|---|
| VS Code Copilot stdio | VS Code starts the MCP server locally | [INSTALL-vscode-copilot-stdio.md](INSTALL-vscode-copilot-stdio.md) |
| Claude Desktop stdio | Claude Desktop starts the MCP server locally | [INSTALL-claude-desktop-stdio.md](INSTALL-claude-desktop-stdio.md) |
| Claude Desktop MCPB | Future packaging flow, not the current local install path | [INSTALL-claude-desktop-mcpb.md](INSTALL-claude-desktop-mcpb.md) |

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
git clone git://172.18.178.24/rad-synergy synergy-ccm-mcp
cd synergy-ccm-mcp
```

Existing checkout:

```bash
cd synergy-ccm-mcp
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

## Step 3 — Configure/Update Synergy Credentials

The synergy-mcp MCP server needs your Synergy CCM username and password. The credential script also checks the Synergy CCM CLI binary path in `synergy-mcp/inventory.yaml`, finds `ccm.exe` automatically, or prompts for a different path if needed. The database path is already configured in `synergy-mcp/inventory.yaml`; do not enter `/ccmdb/prod` here.

Windows PowerShell:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\skills_and_mcp\configure-synergy-credentials.ps1
```

Linux bash:

```bash
bash ./synergy-mcp-server/scripts/install/skills_and_mcp/configure-synergy-credentials.sh
```

The script sets `SYNERGY_MCP_USER`, `SYNERGY_MCP_PASSWORD`, and `CCM_CRED_FILE` for your user.

Preferred for production: start `ccm` yourself and let the MCP server attach with `SYNERGY_<DB>_CCM_ADDR`, so the MCP process never handles a password.

## Step 4 — Install a client target

VS Code Copilot:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\skills_and_mcp\install-vscode-copilot-stdio.ps1
```

Claude Desktop stdio:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\skills_and_mcp\install-claude-desktop-stdio.ps1
```

Linux equivalents:

```bash
bash ./synergy-mcp-server/scripts/install/skills_and_mcp/install-vscode-copilot-stdio.sh
bash ./synergy-mcp-server/scripts/install/skills_and_mcp/install-claude-desktop-stdio.sh
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
cd synergy-ccm-mcp
git pull
```

Then rerun the relevant installer. Existing `inventory.yaml` is kept.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ccm` not found | Synergy client path is not configured | Rerun the credential script and enter the full `ccm.exe` path when prompted |
| Inventory not found | `synergy-mcp/inventory.yaml` missing | Rerun the stdio server installer |
| No user/password | Env vars missing | Rerun the credential script, or use attach mode |
| License exhaustion | Too many Synergy sessions | Prefer attach mode or a shared server process |
| Client shows no server | Config not reloaded | Restart/reload the client after install |