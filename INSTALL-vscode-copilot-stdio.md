# Installing for VS Code Copilot — Local STDIO

**Contents:** [Installation Kind](#installation-kind) · [Before you start](#before-you-start) · [Step 1 — Environment](#step-1--prepare-your-environment) · [Step 2 — Setup](#step-2--setup) · [Step 3 — Credentials](#step-3--configureupdate-your-synergy-ccm-credentials) · [Step 4 — Install](#step-4--install-mcp-stdio-and-copilot-on-vs-code) · [Step 5 — Verify](#step-5--reload-and-verify) · [Generated config](#generated-config)

## Installation Kind

**Local STDIO** (default):
- Client starts synergy-mcp server via stdio.
- Local Python 3.10+ and dependencies are required on the client machine.
- Synergy CCM client must be installed and configured on this machine.
- You control when to make database queries and interact with the Synergy system.
- Full MCP toolset is available locally.

## Before you start

- Run commands from the repository root.
- Install VS Code and the official GitHub Copilot extension.
- Install the Synergy CCM client on this machine and ensure it is configured.
- Use this flow for local stdio transport (default).

## Step 1 — Prepare Your Environment

Choose your platform:

#### VS Code on Windows
- Download and install VS Code: https://code.visualstudio.com/download
- Download and install Git: https://git-scm.com/install/windows
- Install the official GitHub Copilot extension: https://marketplace.visualstudio.com/items?itemName=GitHub.copilot
- Install Synergy CCM client and ensure it is accessible.

#### VS Code on Linux / macOS
- Download and install VS Code: https://code.visualstudio.com/download
- Download and install Git: https://git-scm.com/download/linux (Linux) or https://git-scm.com/download/mac (macOS)
- Install the official GitHub Copilot extension: https://marketplace.visualstudio.com/items?itemName=GitHub.copilot
- Install Synergy CCM client and ensure it is accessible.

## Step 2 — Setup

### New

```bash
git clone git://172.18.178.24/rad-synergy synergy-ccm-mcp
cd synergy-ccm-mcp
```

### Update

```bash
cd synergy-ccm-mcp
git pull
```

## Step 3 — Configure/Update Your Synergy CCM Credentials

The synergy-mcp MCP server needs your Synergy CCM username and password. The database path is already configured in `synergy-mcp/inventory.yaml`; do not enter `/ccmdb/prod` here.

**Windows (PowerShell):**

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\skills_and_mcp\configure-synergy-credentials.ps1
```

**Linux/macOS (bash):**

```bash
bash ./synergy-mcp-server/scripts/install/skills_and_mcp/configure-synergy-credentials.sh
```

### What the script does:

1. Checks the Synergy CCM CLI binary path in `synergy-mcp/inventory.yaml`
2. Finds `ccm.exe` automatically or prompts for a different path if needed
3. Prompts for your Synergy CCM username
4. Prompts for your Synergy CCM password (secure input)
5. Stores the encrypted password securely:
   - **Windows**: `%APPDATA%\synergy-mcp\ccm_password.txt`
   - **Linux**: System keychain or encrypted file
   - **macOS**: System Keychain
6. Sets environment variables: `SYNERGY_MCP_USER`, `SYNERGY_MCP_PASSWORD`, `CCM_CRED_FILE`

## Step 4 — Install MCP STDIO and Copilot on VS Code

Prepare the synergy-mcp server once per machine. This creates the repo-local Python environment under `synergy-mcp/.venv` and installs the internal packages.

**Windows (PowerShell):**

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\skills_and_mcp\install-vscode-copilot-stdio.ps1
```

**Linux / macOS (bash):**

```bash
bash ./synergy-mcp-server/scripts/install/skills_and_mcp/install-vscode-copilot-stdio.sh
```

The installer will:

1. Prepare the local Python virtual environment under `synergy-mcp/.venv`
2. Install synergy-mcp and its dependencies
3. Write `.vscode/mcp.json` configuration in the repository
4. Configure VS Code to start the synergy-mcp server over stdio
5. Install Synergy skills to your Copilot skills folder

## Step 5 — Reload and Verify

1. In VS Code, run `Developer: Reload Window`.
2. Open Copilot Chat in Agent mode.
3. Ask: `List the Synergy databases you can see.`
4. Ask: `Run health_check for a database.`
5. Type `/synergy-core` and confirm the skill appears.
6. Ask: `Show me the available Synergy commands.`

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

---

**End of guide.** See [INSTALL.html](INSTALL.html) for the main installation guide and other transport options.