# Installing for Claude Desktop - Local STDIO

**Contents:** [Installation Kind](#installation-kind) · [Before you start](#before-you-start) · [Step 1 - Setup](#step-1--setup) · [Step 2 - Prepare the server](#step-2--prepare-the-server) · [Step 3 - Configure/Update credentials](#step-3--configureupdate-your-synergy-ccm-credentials) · [Step 4 - Install Claude Desktop STDIO](#step-4--install-claude-desktop-stdio) · [Step 5 - Verify](#step-5--verify) · [Generated config](#generated-config)

## Installation Kind

**Local STDIO** is the current Claude Desktop flow. Claude Desktop starts the local `synergy-mcp` server directly over stdio.

Use MCPB later only when the project ships a packaged HTTP/server flow. For now, do not use MCPB as the normal install path.

## Before you start

- Install Claude Desktop.
- Install Python 3.10 or newer.
- Install Git.
- Install the Synergy `ccm` client on this machine.
- Run commands from the repository root, `synergy-ccm-mcp/`.

## Step 1 - Setup

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

## Step 2 - Prepare the server

Windows PowerShell:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\mcp_server\install-stdio-mcp-server.ps1
```

Linux/macOS bash:

```bash
bash ./synergy-mcp-server/scripts/install/mcp_server/install-stdio-mcp-server.sh
```

This creates `synergy-mcp/.venv`, installs `synergy-mcp` into it, and creates `synergy-mcp/inventory.yaml` from `synergy-mcp/inventory.example.yaml` if needed.

## Step 3 - Configure/Update Your Synergy CCM Credentials

The synergy-mcp MCP server needs your Synergy CCM username and password. The credential script also checks the Synergy CCM CLI binary path in `synergy-mcp/inventory.yaml`, finds `ccm.exe` automatically, or prompts for a different path if needed. The database path is already configured in `synergy-mcp/inventory.yaml`; do not enter `/ccmdb/prod` here.

Windows PowerShell:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\skills_and_mcp\configure-synergy-credentials.ps1
```

Linux/macOS bash:

```bash
bash ./synergy-mcp-server/scripts/install/skills_and_mcp/configure-synergy-credentials.sh
```

## Step 4 - Install Claude Desktop STDIO

Windows PowerShell:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\skills_and_mcp\install-claude-desktop-stdio.ps1
```

Linux/macOS bash:

```bash
bash ./synergy-mcp-server/scripts/install/skills_and_mcp/install-claude-desktop-stdio.sh
```

The installer builds a Claude plugin containing all `synergy-*` skills and prints the local stdio MCP connector entry for you to paste manually in Claude Desktop settings. It does not modify `claude_desktop_config.json`. It opens the plugin dist directory:

- Plugin folder: `synergy-mcp-server/dist/plugin/synergy-ccm-mcp`
- Upload zip: `synergy-mcp-server/dist/plugin/synergy-ccm-mcp-plugin.zip`

## Step 5 - Verify

Fully quit Claude Desktop and relaunch it. In a new chat, ask:

```text
List the Synergy databases you can see, then run health_check for prod-core.
```

Then ask a bounded read-only question:

```text
Find CRs changed today, max 20 rows.
```

## Generated plugin and MCP config

Add this MCP server entry under `mcpServers` in Claude Desktop's config file:

```json
{
  "mcpServers": {
    "synergy-ccm-mcp": {
      "command": "powershell.exe",
      "args": [
        "-NoProfile",
        "-NonInteractive",
        "-WindowStyle",
        "Hidden",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        ".../synergy-mcp-server/scripts/launch_synergy_mcp.ps1",
        "-PythonPath",
        ".../synergy-mcp/.venv/Scripts/python.exe",
        "-InventoryPath",
        ".../synergy-mcp/inventory.yaml"
      ]
    }
  }
}
```

The generated plugin is skills-only. It contains `.claude-plugin/plugin.json`, `README.md`, and all Synergy skill folders under `skills/`.
