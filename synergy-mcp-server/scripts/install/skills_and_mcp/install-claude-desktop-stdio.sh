#!/usr/bin/env bash
set -euo pipefail

NAME="synergy-ccm-mcp"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) NAME="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
SERVER_INSTALLER="$REPO_ROOT/synergy-mcp-server/scripts/install/mcp_server/install-stdio-mcp-server.sh"

bash "$SERVER_INSTALLER"

VENV_PYTHON="$REPO_ROOT/synergy-mcp/.venv/bin/python"
INVENTORY="$REPO_ROOT/synergy-mcp/inventory.yaml"
LAUNCHER="$REPO_ROOT/synergy-mcp-server/scripts/launch_synergy_mcp.ps1"
PLUGIN_BUILDER="$REPO_ROOT/synergy-mcp-server/scripts/build_claude_plugin.py"
PLUGIN_DIST="$REPO_ROOT/synergy-mcp-server/dist/plugin"

"$VENV_PYTHON" "$PLUGIN_BUILDER" --name "$NAME"

if [[ "$(uname -s)" == "Darwin" ]]; then
  open "$PLUGIN_DIST" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$PLUGIN_DIST" >/dev/null 2>&1 || true
fi

echo ""
echo "Done. Claude Desktop plugin built: $PLUGIN_DIST"
echo "Import the plugin zip from this folder in Claude Desktop."
echo ""
echo "Add this entry manually under the top-level mcpServers object in Claude Desktop config:"
"$VENV_PYTHON" - "$NAME" "$VENV_PYTHON" "$INVENTORY" "$LAUNCHER" <<'PY'
import json
import sys

name = sys.argv[1]
python = sys.argv[2]
inventory = sys.argv[3]
launcher = sys.argv[4]
server = {
    "command": "powershell.exe",
    "args": [
        "-NoProfile",
        "-NonInteractive",
        "-WindowStyle",
        "Hidden",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        launcher,
        "-PythonPath",
        python,
        "-InventoryPath",
        inventory,
    ],
}
print(f'"{name}": ' + json.dumps(server, indent=2))
PY
echo ""
echo "The installer did not modify claude_desktop_config.json."
