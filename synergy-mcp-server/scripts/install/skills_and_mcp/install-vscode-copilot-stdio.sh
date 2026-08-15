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
MCP_DIR="$REPO_ROOT/.vscode"
MCP_FILE="$MCP_DIR/mcp.json"
mkdir -p "$MCP_DIR"

"$VENV_PYTHON" - "$MCP_FILE" "$NAME" "$VENV_PYTHON" "$INVENTORY" <<'PY'
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
data.setdefault("servers", {})[name] = {
    "type": "stdio",
    "command": python,
    "args": ["-m", "synergy_mcp"],
    "env": {"SYNERGY_MCP_INVENTORY": inventory},
}
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

echo ""
echo "Done. VS Code MCP config updated: $MCP_FILE"
echo "Reload VS Code, start Copilot Agent mode, then ask: List the Synergy databases you can see."