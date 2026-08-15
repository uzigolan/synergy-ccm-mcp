"""Filesystem roots for the synergy toolkit."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """The synergy-mcp-server directory (holds skills/, commands/, inventory.yaml)."""
    override = os.environ.get("SYNERGY_MCP_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    # packages/synergy-core/synergy_core/paths.py -> synergy-mcp-server
    return Path(__file__).resolve().parents[3]


def data_root() -> Path:
    override = os.environ.get("SYNERGY_MCP_DATA_DIR")
    return Path(override).expanduser().resolve() if override else repo_root()


def log_dir() -> Path:
    override = os.environ.get("SYNERGY_MCP_LOG_DIR")
    path = Path(override).expanduser().resolve() if override else data_root() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def skills_dir() -> Path:
    return repo_root() / "skills"


def inventory_path() -> Path:
    override = os.environ.get("SYNERGY_MCP_INVENTORY")
    return Path(override).expanduser().resolve() if override else repo_root() / "inventory.yaml"


def env_file() -> Path:
    override = os.environ.get("SYNERGY_MCP_ENV_FILE")
    return Path(override).expanduser().resolve() if override else repo_root() / "server" / ".env"
