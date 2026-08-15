# Installing for VS Code Copilot — Local STDIO

**Contents:** [What this installs](#what-this-installs) · [Before you start](#before-you-start) · [Step 1 — Prepare the server](#step-1--prepare-the-server) · [Step 2 — Write VS Code MCP config](#step-2--write-vs-code-mcp-config) · [Step 3 — Reload and verify](#step-3--reload-and-verify) · [Generated config](#generated-config)

## What this installs

This flow configures VS Code GitHub Copilot to start `synergy-mcp` locally over stdio.

It writes `.vscode/mcp.json` in this repository. The command points at the repo-local Python virtual environment under `synergy-mcp/.venv`.

## Before you start

- Install VS Code and the official GitHub Copilot extension.
- Install the Synergy `ccm` client on this machine.
- Run all commands from the repo root, `rad-synergy-toolkit/`.

## Step 1 — Prepare the server

Windows PowerShell:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\mcp_server\install-stdio-mcp-server.ps1
```

Linux bash:

```bash
bash ./synergy-mcp-server/scripts/install/mcp_server/install-stdio-mcp-server.sh
```

## Step 2 — Write VS Code MCP config

Windows PowerShell:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\skills_and_mcp\install-vscode-copilot-stdio.ps1
```

Linux bash:

```bash
bash ./synergy-mcp-server/scripts/install/skills_and_mcp/install-vscode-copilot-stdio.sh
```

## Step 3 — Reload and verify

1. In VS Code, run `Developer: Reload Window`.
2. Open Copilot Chat in Agent mode.
3. Ask: `List the Synergy databases you can see.`
4. Ask: `Run health_check for prod-core.`

## Generated config

The installer writes this shape to `.vscode/mcp.json`:

```json
{
  "servers": {
    "synergy-ccm-mcp": {
      "type": "stdio",
      "command": "<repo>/synergy-mcp/.venv/Scripts/python.exe",
      "args": ["-m", "synergy_mcp"],
      "env": {
        "SYNERGY_MCP_INVENTORY": "<repo>/synergy-mcp/inventory.yaml"
      }
    }
  }
}
```

On Linux the Python path is `synergy-mcp/.venv/bin/python`.