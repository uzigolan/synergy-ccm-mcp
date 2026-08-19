#!/usr/bin/env python3
"""Build the Synergy CCM Claude plugin bundle.

The plugin contains:
- .claude-plugin/plugin.json
- .mcp.json pointing at this repo's local synergy-mcp venv and inventory
- all Synergy SKILL.md folders under skills/

The generated zip is intended for Claude Desktop's local plugin upload flow.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO.parent
SKILLS_SRC = REPO / "skills"
OUT_ROOT = REPO / "dist" / "plugin"
PLUGIN = OUT_ROOT / "synergy-ccm-mcp"

if os.name == "nt":
    VENV_PY = ROOT / "synergy-mcp" / ".venv" / "Scripts" / "python.exe"
else:
    VENV_PY = ROOT / "synergy-mcp" / ".venv" / "bin" / "python"
INVENTORY = ROOT / "synergy-mcp" / "inventory.yaml"

MANIFEST = {
    "name": "synergy-ccm-mcp",
    "displayName": "Synergy CCM MCP",
    "version": "0.1.0",
    "description": "Read-only IBM Rational Synergy MCP tools and skills for Claude.",
    "author": {"name": "Uzi Golan"},
    "keywords": ["synergy", "ccm", "rational", "mcp", "change-requests"],
}

README = """# Synergy CCM MCP Claude Plugin

This plugin bundles the Synergy skills and a local MCP stdio server entry.

## Install

Claude Desktop: open Settings -> Extensions or Plugins -> install/upload this local plugin zip.

## Local Build Caveat

`.mcp.json` points at this machine's repo-local Python virtual environment and inventory file.
Install from the same checkout, or rebuild the plugin after moving the repository.

If you already configured `synergy-ccm-mcp` manually in `claude_desktop_config.json`, remove that duplicate entry after installing this plugin.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Synergy CCM Claude plugin bundle.")
    parser.add_argument("--name", default="synergy-ccm-mcp", help="MCP server entry name")
    args = parser.parse_args()

    if OUT_ROOT.exists():
        shutil.rmtree(OUT_ROOT)
    (PLUGIN / ".claude-plugin").mkdir(parents=True)

    mcp = {
        "mcpServers": {
            args.name: {
                "command": str(VENV_PY),
                "args": ["-m", "synergy_mcp"],
                "env": {"SYNERGY_MCP_INVENTORY": str(INVENTORY)},
            }
        }
    }

    (PLUGIN / ".claude-plugin" / "plugin.json").write_text(
        json.dumps(MANIFEST, indent=2) + "\n", encoding="utf-8"
    )
    (PLUGIN / ".mcp.json").write_text(json.dumps(mcp, indent=2) + "\n", encoding="utf-8")
    (PLUGIN / "README.md").write_text(README, encoding="utf-8")

    if not SKILLS_SRC.exists():
        raise SystemExit(f"Skills directory not found: {SKILLS_SRC}")
    shutil.copytree(SKILLS_SRC, PLUGIN / "skills")

    zip_path = OUT_ROOT / "synergy-ccm-mcp-plugin.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for root, _, files in os.walk(PLUGIN):
            for filename in files:
                full = Path(root) / filename
                archive.write(full, full.relative_to(OUT_ROOT).as_posix())

    skill_count = sum(1 for _ in (PLUGIN / "skills").glob("*/SKILL.md"))
    file_count = sum(1 for path in PLUGIN.rglob("*") if path.is_file())
    print(f"plugin -> {PLUGIN.relative_to(REPO)} ({skill_count} skills, {file_count} files)")
    print(f"zip    -> {zip_path.relative_to(REPO)}")
    print("MCP server entry bundled in plugin:")
    print(json.dumps(mcp["mcpServers"][args.name], indent=2))
    if not VENV_PY.exists():
        print(f"WARNING: venv python not found at {VENV_PY}")
    if not INVENTORY.exists():
        print(f"WARNING: inventory not found at {INVENTORY}")


if __name__ == "__main__":
    main()
