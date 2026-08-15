# Installing for Claude Desktop — MCPB

**Contents:** [What this installs](#what-this-installs) · [Before you start](#before-you-start) · [Step 1 — Prepare the server](#step-1--prepare-the-server) · [Step 2 — Build the MCPB](#step-2--build-the-mcpb) · [Step 3 — Import into Claude Desktop](#step-3--import-into-claude-desktop) · [Step 4 — Verify](#step-4--verify) · [Generated artifacts](#generated-artifacts)

## What this installs

This flow builds a local Claude Desktop MCPB bundle that starts `synergy-mcp` over stdio.

The bundle points at the repo-local Python virtual environment under `synergy-mcp/.venv` and the repo-local `synergy-mcp/inventory.yaml`.

## Before you start

- Install Claude Desktop.
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

## Step 2 — Build the MCPB

Windows PowerShell:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\skills_and_mcp\install-claude-desktop-mcpb.ps1
```

Linux bash:

```bash
bash ./synergy-mcp-server/scripts/install/skills_and_mcp/install-claude-desktop-mcpb.sh
```

## Step 3 — Import into Claude Desktop

1. Open Claude Desktop settings.
2. Open Extensions.
3. Choose Install from file.
4. Select `synergy-mcp-server/dist/claude-desktop-mcpb/synergy-ccm-mcp-local.mcpb`.
5. Save the extension settings.
6. Fully quit Claude Desktop and relaunch it.

If your Claude Desktop version prefers manual local MCP JSON, use `synergy-mcp-server/dist/claude-desktop-local-mcp/synergy-ccm-mcp-local-mcp-server.json`.

## Step 4 — Verify

In a new Claude Desktop chat, ask:

```text
List the Synergy databases you can see, then run health_check for prod-core.
```

## Generated artifacts

| File | Purpose |
|---|---|
| `synergy-mcp-server/dist/claude-desktop-mcpb/synergy-ccm-mcp-local.mcpb` | Claude Desktop extension bundle |
| `synergy-mcp-server/dist/claude-desktop-local-mcp/synergy-ccm-mcp-local-mcp-server.json` | Manual local MCP JSON payload |