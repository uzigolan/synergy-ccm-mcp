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
SKILLS_SRC="$REPO_ROOT/synergy-mcp-server/skills"
SKILLS_DEST="$HOME/.copilot/skills"

if [[ "$(uname -s)" == "Darwin" ]]; then
  MCP_FILE="$HOME/Library/Application Support/Code/User/mcp.json"
else
  MCP_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/Code/User/mcp.json"
fi

MCP_DIR="$(dirname "$MCP_FILE")"
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

"$VENV_PYTHON" - "$SKILLS_SRC" "$SKILLS_DEST" <<'PY'
import shutil
import sys
from pathlib import Path

src = Path(sys.argv[1])
dest = Path(sys.argv[2])
dest.mkdir(parents=True, exist_ok=True)

selected = []
if src.exists():
  for skill_dir in sorted(p for p in src.iterdir() if p.is_dir()):
    if not (skill_dir / "SKILL.md").exists():
      continue
    selected.append(skill_dir.name)
    target = dest / skill_dir.name
    if target.exists():
      shutil.rmtree(target)
    shutil.copytree(skill_dir, target)

for stale in dest.glob("synergy-*"):
  if stale.is_dir() and stale.name not in selected:
    shutil.rmtree(stale)
PY

echo ""
echo "Done. VS Code MCP config updated: $MCP_FILE"
echo "Done. Copilot skills refreshed: $SKILLS_DEST"
echo "Reload VS Code, start Copilot Agent mode, then ask: /synergy-core"