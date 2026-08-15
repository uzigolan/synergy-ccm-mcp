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
DIST="$REPO_ROOT/synergy-mcp-server/dist"
MCPB_DIR="$DIST/claude-desktop-mcpb"
LOCAL_JSON_DIR="$DIST/claude-desktop-local-mcp"
TEMP_DIR="$DIST/claude-desktop-mcpb-work"
MCPB_FILE="$MCPB_DIR/synergy-ccm-mcp-local.mcpb"
LOCAL_JSON_FILE="$LOCAL_JSON_DIR/synergy-ccm-mcp-local-mcp-server.json"

mkdir -p "$MCPB_DIR" "$LOCAL_JSON_DIR"
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

"$VENV_PYTHON" - "$NAME" "$VENV_PYTHON" "$INVENTORY" "$LOCAL_JSON_FILE" "$TEMP_DIR/manifest.json" <<'PY'
import json
import sys
from pathlib import Path

name, python, inventory, local_json, manifest = sys.argv[1:]
server = {
    "type": "stdio",
    "command": python,
    "args": ["-m", "synergy_mcp"],
    "env": {"SYNERGY_MCP_INVENTORY": inventory},
}
Path(local_json).write_text(json.dumps({"mcpServers": {name: server}}, indent=2) + "\n", encoding="utf-8")
Path(manifest).write_text(json.dumps({
    "name": "synergy-ccm-mcp",
    "display_name": "Synergy CCM MCP",
    "version": "0.1.0",
    "description": "Read-only IBM Rational Synergy MCP server over local stdio.",
    "mcpServers": {name: server},
}, indent=2) + "\n", encoding="utf-8")
PY

"$VENV_PYTHON" - "$TEMP_DIR" "$MCPB_FILE" <<'PY'
import sys
import zipfile
from pathlib import Path

root = Path(sys.argv[1])
target = Path(sys.argv[2])
with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
  for path in root.rglob("*"):
    if path.is_file():
      archive.write(path, path.relative_to(root).as_posix())
PY
rm -rf "$TEMP_DIR"

echo ""
echo "Done. Claude Desktop artifacts created:"
echo "  MCPB:           $MCPB_FILE"
echo "  Local MCP JSON: $LOCAL_JSON_FILE"
echo "Import the MCPB in Claude Desktop Settings -> Extensions, then fully restart Claude Desktop."