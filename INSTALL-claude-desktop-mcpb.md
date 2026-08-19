# Claude Desktop MCPB Packaging - Future Flow

MCPB is not the current Claude Desktop install path for this project. Use the local stdio guide now: [INSTALL-claude-desktop-stdio.md](INSTALL-claude-desktop-stdio.md).

This MCPB flow is reserved for later packaging work when the project ships an MCP HTTP/server flow.

**Contents:** [What this installs](#what-this-installs) · [Before you start](#before-you-start) · [Step 1 — Setup](#step-1--setup) · [Step 2 — Prepare the server](#step-2--prepare-the-server) · [Step 3 — Configure/Update credentials](#step-3--configureupdate-your-synergy-ccm-credentials) · [Step 4 — Build the MCPB](#step-4--build-the-mcpb) · [Step 5 — Import into Claude Desktop](#step-5--import-into-claude-desktop) · [Step 6 — Verify](#step-6--verify) · [Generated artifacts](#generated-artifacts)

## What this installs

This future flow builds a Claude Desktop MCPB bundle. It is not the recommended local install path today.

The bundle points at the repo-local Python virtual environment under `synergy-mcp/.venv` and the repo-local `synergy-mcp/inventory.yaml`.

Synergy skills are not embedded in the MCPB. They are served by the MCP server through `synergy://skills` resources.

## Before you start

- Install Claude Desktop.
- Install the Synergy `ccm` client on this machine.
- Run all commands from the repo root, `synergy-ccm-mcp/`.

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

## Step 2 — Prepare the server

Windows PowerShell:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\mcp_server\install-stdio-mcp-server.ps1
```

Linux bash:

```bash
bash ./synergy-mcp-server/scripts/install/mcp_server/install-stdio-mcp-server.sh
```

## Step 3 — Configure/Update Your Synergy CCM Credentials

The synergy-mcp MCP server needs your Synergy CCM username and password. The credential script also checks the Synergy CCM CLI binary path in `synergy-mcp/inventory.yaml`, finds `ccm.exe` automatically, or prompts for a different path if needed. The database path is already configured in `synergy-mcp/inventory.yaml`; do not enter `/ccmdb/prod` here.

Windows PowerShell:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\skills_and_mcp\configure-synergy-credentials.ps1
```

Linux bash:

```bash
bash ./synergy-mcp-server/scripts/install/skills_and_mcp/configure-synergy-credentials.sh
```

## Step 4 — Build the MCPB

Windows PowerShell:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\skills_and_mcp\install-claude-desktop-mcpb.ps1
```

Linux bash:

```bash
bash ./synergy-mcp-server/scripts/install/skills_and_mcp/install-claude-desktop-mcpb.sh
```

The installer also builds a Claude plugin containing all `synergy-*` skill folders and opens `synergy-mcp-server/dist/plugin/`.

## Step 5 — Import into Claude Desktop

1. Open Claude Desktop settings.
2. Open Extensions.
3. Choose Install from file.
4. Select `synergy-mcp-server/dist/claude-desktop-mcpb/synergy-ccm-mcp-local.mcpb`.
5. Save the extension settings.
6. Fully quit Claude Desktop and relaunch it.

If your Claude Desktop version prefers manual local MCP JSON, use `synergy-mcp-server/dist/claude-desktop-local-mcp/synergy-ccm-mcp-local-mcp-server.json`.

## Step 6 — Verify

In a new Claude Desktop chat, ask:

```text
List the Synergy databases you can see, then run health_check for prod-core.
```

## Generated artifacts

| File | Purpose |
|---|---|
| `synergy-mcp-server/dist/claude-desktop-mcpb/synergy-ccm-mcp-local.mcpb` | Claude Desktop extension bundle |
| `synergy-mcp-server/dist/claude-desktop-local-mcp/synergy-ccm-mcp-local-mcp-server.json` | Manual local MCP JSON payload |