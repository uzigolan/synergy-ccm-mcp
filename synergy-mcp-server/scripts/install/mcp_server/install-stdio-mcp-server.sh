#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-python3}"
FORCE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --python) PYTHON_BIN="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PACKAGE_DIR="$REPO_ROOT/synergy-mcp"
VENV_DIR="$PACKAGE_DIR/.venv"
INVENTORY="$PACKAGE_DIR/inventory.yaml"
INVENTORY_EXAMPLE="$PACKAGE_DIR/inventory.example.yaml"

if [[ ! -d "$PACKAGE_DIR" ]]; then
  echo "Package directory not found: $PACKAGE_DIR" >&2
  exit 1
fi

if [[ "$FORCE" == "1" && -d "$VENV_DIR" ]]; then
  rm -rf "$VENV_DIR"
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating Python virtual environment: $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

VENV_PYTHON="$VENV_DIR/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Virtual environment Python not found: $VENV_PYTHON" >&2
  exit 1
fi

echo "Installing synergy-mcp into the virtual environment ..."
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -e "$PACKAGE_DIR"

if [[ ! -f "$INVENTORY" ]]; then
  cp "$INVENTORY_EXAMPLE" "$INVENTORY"
  echo "Created inventory: $INVENTORY"
  echo "Edit it before first use. Do not put passwords in inventory.yaml."
else
  echo "Keeping existing inventory: $INVENTORY"
fi

echo ""
echo "Done. Local stdio MCP server is prepared."
echo "  Python:    $VENV_PYTHON"
echo "  Inventory: $INVENTORY"
echo ""
echo "Next: configure credentials or attach mode, then install a client target."