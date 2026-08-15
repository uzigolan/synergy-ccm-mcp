"""Inventory + credential loading for synergy-mcp."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ConfigError(RuntimeError):
    pass


@dataclass
class DatabaseConfig:
    """One Synergy database the server is allowed to talk to."""

    name: str
    database: str
    host: str | None = None
    server_url: str | None = None
    role: str = "developer"
    user: str | None = None
    # Extra flags appended verbatim to `ccm start`; lets us adapt to site-specific setups.
    start_flags: list[str] = field(default_factory=lambda: ["-m", "-q", "-nogui"])
    # When set, the server never runs `ccm start` and simply attaches to this CCM_ADDR.
    ccm_addr: str | None = None
    description: str = ""

    @property
    def env_prefix(self) -> str:
        return "SYNERGY_" + "".join(c if c.isalnum() else "_" for c in self.name).upper()

    def resolve_user(self) -> str:
        value = (
            os.environ.get(f"{self.env_prefix}_USER")
            or self.user
            or os.environ.get("SYNERGY_MCP_USER")
        )
        if not value:
            raise ConfigError(
                f"No user for database '{self.name}'. Set {self.env_prefix}_USER, "
                f"set SYNERGY_MCP_USER, or add 'user:' to inventory.yaml."
            )
        return value

    def resolve_password(self) -> str:
        value = os.environ.get(f"{self.env_prefix}_PASSWORD") or os.environ.get(
            "SYNERGY_MCP_PASSWORD"
        )
        if not value:
            raise ConfigError(
                f"No password for database '{self.name}'. Set {self.env_prefix}_PASSWORD "
                f"or SYNERGY_MCP_PASSWORD in the environment (never in inventory.yaml)."
            )
        return value

    def resolve_ccm_addr(self) -> str | None:
        return os.environ.get(f"{self.env_prefix}_CCM_ADDR") or self.ccm_addr


@dataclass
class ServerConfig:
    ccm_binary: str = "ccm"
    command_timeout: int = 120
    start_timeout: int = 300
    max_rows: int = 500
    max_output_bytes: int = 200_000
    databases: dict[str, DatabaseConfig] = field(default_factory=dict)

    def get(self, name: str) -> DatabaseConfig:
        if name not in self.databases:
            known = ", ".join(sorted(self.databases)) or "<none>"
            raise ConfigError(f"Unknown database '{name}'. Known databases: {known}")
        return self.databases[name]


def _inventory_path() -> Path:
    override = os.environ.get("SYNERGY_MCP_INVENTORY")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "inventory.yaml"


def load_config(path: Path | None = None) -> ServerConfig:
    path = path or _inventory_path()
    if not path.exists():
        raise ConfigError(
            f"Inventory not found at {path}. Copy inventory.example.yaml to inventory.yaml "
            f"or set SYNERGY_MCP_INVENTORY."
        )

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    settings = raw.get("settings") or {}

    config = ServerConfig(
        ccm_binary=os.environ.get("SYNERGY_CCM_BINARY") or settings.get("ccm_binary", "ccm"),
        command_timeout=int(settings.get("command_timeout", 120)),
        start_timeout=int(settings.get("start_timeout", 300)),
        max_rows=int(settings.get("max_rows", 500)),
        max_output_bytes=int(settings.get("max_output_bytes", 200_000)),
    )

    entries = raw.get("databases") or []
    if not entries:
        raise ConfigError(f"No 'databases:' entries in {path}.")

    for entry in entries:
        if "name" not in entry or "database" not in entry:
            raise ConfigError(f"Inventory entry missing 'name' or 'database': {entry!r}")
        if "password" in entry:
            raise ConfigError(
                f"Entry '{entry['name']}' contains a 'password' key. Passwords must come "
                f"from the environment, not inventory.yaml."
            )
        db = DatabaseConfig(
            name=str(entry["name"]),
            database=str(entry["database"]),
            host=entry.get("host"),
            server_url=entry.get("server_url"),
            role=entry.get("role", "developer"),
            user=entry.get("user"),
            start_flags=list(entry.get("start_flags", ["-m", "-q", "-nogui"])),
            ccm_addr=entry.get("ccm_addr"),
            description=entry.get("description", ""),
        )
        config.databases[db.name] = db

    return config
