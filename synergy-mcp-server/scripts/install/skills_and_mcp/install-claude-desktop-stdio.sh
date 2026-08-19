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

if [[ "$(uname -s)" == "Darwin" ]]; then
  VENV_PYTHON="$REPO_ROOT/synergy-mcp/.venv/bin/python"
  CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
else
  VENV_PYTHON="$REPO_ROOT/synergy-mcp/.venv/bin/python"
  CLAUDE_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/Claude/claude_desktop_config.json"
fi

INVENTORY="$REPO_ROOT/synergy-mcp/inventory.yaml"
PLUGIN_BUILDER="$REPO_ROOT/synergy-mcp-server/scripts/build_claude_plugin.py"
PLUGIN_DIST="$REPO_ROOT/synergy-mcp-server/dist/plugin"
CLAUDE_DIR="$(dirname "$CLAUDE_CONFIG")"
mkdir -p "$CLAUDE_DIR"

if [[ -f "$CLAUDE_CONFIG" ]]; then
  BACKUP_FILE="$CLAUDE_CONFIG.$(date +%Y%m%d-%H%M%S).bak"
  cp "$CLAUDE_CONFIG" "$BACKUP_FILE"
  echo "Backup saved: $BACKUP_FILE"
fi

bash "$SERVER_INSTALLER"

"$VENV_PYTHON" - "$CLAUDE_CONFIG" "$NAME" "$VENV_PYTHON" "$INVENTORY" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
name = sys.argv[2]
python = sys.argv[3]
inventory = sys.argv[4]
if path.exists():
    data = json.loads(path.read_text(encoding="utf-8"))
else:
    data = {}
server = {
    "command": python,
    "args": ["-m", "synergy_mcp"],
    "env": {"SYNERGY_MCP_INVENTORY": inventory},
}
print("Claude Desktop MCP server entry to add:")
print(json.dumps(server, indent=2))
data.setdefault("mcpServers", {})[name] = server
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

"$VENV_PYTHON" "$PLUGIN_BUILDER" --name "$NAME"

if [[ "$(uname -s)" == "Darwin" ]]; then
  open "$PLUGIN_DIST" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$PLUGIN_DIST" >/dev/null 2>&1 || true
fi

echo ""
echo "Done. Claude Desktop MCP stdio config updated: $CLAUDE_CONFIG"
echo "Done. Claude Desktop plugin built: $PLUGIN_DIST"
echo "Fully quit Claude Desktop, relaunch it, then ask: List the Synergy databases you can see."
