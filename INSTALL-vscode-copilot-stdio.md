# Installing for VS Code Copilot — Local STDIO

**Contents:** [What this installs](#what-this-installs) · [Before you start](#before-you-start) · [Step 1 — Prepare the server](#step-1--prepare-the-server) · [Step 2 — Write VS Code MCP config](#step-2--write-vs-code-mcp-config) · [Step 3 — Reload and verify](#step-3--reload-and-verify) · [Generated config](#generated-config)

## What this installs

This flow configures VS Code GitHub Copilot to start `synergy-mcp` locally over stdio.

By default it writes a global user-level MCP config and refreshes Synergy skills into the user Copilot skills folder.

This installer is global-only. It does not write workspace MCP config or workspace skills.

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

Global user-level (default):

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
5. Type `/synergy-core` and confirm the skill appears.
6. Ask: `Read synergy://skills/synergy-core`.

## Generated config

The installer writes this shape to `mcp.json`:

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

By default, the JSON is written at:

- Windows: `%APPDATA%\Code\User\mcp.json`
- Linux: `${XDG_CONFIG_HOME:-~/.config}/Code/User/mcp.json`
- macOS: `~/Library/Application Support/Code/User/mcp.json`

The installer also refreshes Synergy skill folders at:

- Windows: `%USERPROFILE%\.copilot\skills\synergy-*`
- Linux/macOS: `~/.copilot/skills/synergy-*`