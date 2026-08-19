# Installing for VS Code Copilot — Local STDIO

**Contents:** [Installation Kind](#installation-kind) · [Before you start](#before-you-start) · [Step 1 — Environment](#step-1--prepare-your-environment) · [Step 2 — Setup](#step-2--setup) · [Step 3 — Install](#step-3--install-mcp-stdio) · [Step 4 — Verify](#step-4--reload-and-verify) · [Generated config](#generated-config)

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

## Step 2a — Configure Your Synergy CCM Credentials (Optional)

The synergy-mcp MCP server needs your credentials to access the Synergy CCM database. Use the automated credential configuration script (run from repo root):

**Windows (PowerShell):**

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\skills_and_mcp\configure-synergy-credentials.ps1
```

**Linux/macOS (bash):**

```bash
bash ./synergy-mcp-server/scripts/install/skills_and_mcp/configure-synergy-credentials.sh
```

**Manual Setup (if preferred):**

If you prefer to configure credentials manually, see the [manual setup section](#manual-credential-setup) below.

### What the script does:

1. Prompts for your Synergy CCM username
2. Prompts for your Synergy CCM password (secure input)
3. Stores the encrypted password securely:
   - **Windows**: `%APPDATA%\synergy-mcp\ccm_password.txt`
   - **Linux**: System keychain or encrypted file
   - **macOS**: System Keychain
4. Sets environment variables: `CCM_USER`, `CCM_ADDR`, `CCM_CRED_FILE`

---

### Manual Credential Setup

**Windows (Credential Manager):**

```powershell
# Create the directory if it doesn't exist
$CredDir = "$env:APPDATA\synergy-mcp"
New-Item -ItemType Directory -Force -Path $CredDir | Out-Null

# Store YOUR password securely (replace with your actual username)
$username = "your-synergy-username"
$cred = Get-Credential -UserName $username -Message "Enter your Synergy CCM password"
$cred.Password | ConvertFrom-SecureString | Set-Content "$CredDir\ccm_password.txt"

# Set your environment variables
[Environment]::SetEnvironmentVariable("CCM_USER", "$username", "User")
[Environment]::SetEnvironmentVariable("CCM_ADDR", "your-ccm-server:5580", "User")
```

**Linux/macOS (System Keychain):**

```bash
# Store YOUR password in system keychain (replace with your actual username)
YOUR_USERNAME="your-synergy-username"
read -sp "Enter your Synergy CCM password: " CCM_PASSWORD
echo "$CCM_PASSWORD" | pass insert synergy-ccm/password

# Set your environment variables
echo "export CCM_USER=\"$YOUR_USERNAME\"" >> ~/.bashrc
echo 'export CCM_ADDR="your-ccm-server:5580"' >> ~/.bashrc
source ~/.bashrc
```

## Step 4 — Install MCP STDIO

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