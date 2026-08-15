"""synergy-mcp: read-only MCP tools over the IBM Rational Synergy 7.2 `ccm` CLI."""

from __future__ import annotations

import atexit
import json
import logging
import os
import re
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from mcp.server.fastmcp import FastMCP
import yaml

from .config import ServerConfig, load_config
from .exec import CcmError
from .formats import (
    DEFAULT_OBJECT_FIELDS,
    DEFAULT_TASK_FIELDS,
    format_spec,
    is_empty_result,
    parse_rows,
)
from .knowledge import KnowledgeError, corpus_root, search_knowledge
from .session import SessionManager

log = logging.getLogger("synergy_mcp")

_LOG_LEVEL = os.environ.get("SYNERGY_MCP_LOG_LEVEL", "INFO").upper()

# FastMCP installs its own root handler at this level, so it must agree with ours
# or our DEBUG records get dropped before reaching stderr.
mcp = FastMCP("synergy-mcp", log_level=_LOG_LEVEL)

# Object names are interpolated into ccm query expressions, so anything that
# could break out of a single-quoted literal is rejected up front.
# '!' and '@' appear in multi-database instance ids such as 'proj:project:IL!1'.
_OBJECTNAME_RE = re.compile(r"^[A-Za-z0-9_.:~#+!@\-/\\ ]{1,400}$")
_SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
_REGISTERED_TOOLS = frozenset(
    {
        "list_databases",
        "health_check",
        "ccm_version",
        "query",
        "object_properties",
        "object_attributes",
        "attribute_value",
        "object_content",
        "object_history",
        "object_diff",
        "find_use",
        "task_info",
        "task_objects",
        "find_tasks",
        "project_members",
        "find_baselines",
        "project_grouping_info",
        "run_readonly_command",
        "knowledge_search",
        "check_skill_version",
    }
)


@lru_cache(maxsize=1)
def _config() -> ServerConfig:
    return load_config()


@lru_cache(maxsize=1)
def _sessions() -> SessionManager:
    manager = SessionManager(_config())
    atexit.register(manager.shutdown)
    return manager


def _safe_object(name: str, label: str = "object_name") -> str:
    name = name.strip()
    if not _OBJECTNAME_RE.match(name):
        raise ValueError(
            f"Invalid {label} {name!r}. Expected a Synergy object name such as "
            f"'main.c-3:csrc:1' without quotes or control characters."
        )
    return name


def _text_tool(database: str, argv: list[str], *, timeout: int | None = None) -> dict:
    try:
        result = _sessions().run(database, argv, timeout=timeout)
    except CcmError as exc:
        if is_empty_result(exc.result.stdout, exc.result.stderr):
            return {"database": database, "output": "", "empty": True}
        raise
    return {
        "database": database,
        "output": result.text.strip(),
        "truncated": result.truncated,
        "empty": False,
    }


def _skills_root() -> Path:
    return corpus_root() / "skills"


def _safe_skill_dir(name: str) -> Path:
    if not _SKILL_NAME_RE.match(name):
        raise ValueError(f"Invalid skill name {name!r}.")
    root = _skills_root().resolve()
    path = (root / name).resolve()
    if root not in path.parents or not path.is_dir():
        raise ValueError(f"Unknown skill {name!r}.")
    return path


def _read_skill(name: str) -> tuple[dict, str]:
    path = _safe_skill_dir(name) / "SKILL.md"
    if not path.exists():
        raise ValueError(f"Skill {name!r} has no SKILL.md.")
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"Skill {name!r} is missing YAML frontmatter.")
    _, frontmatter, _ = text.split("---", 2)
    meta = yaml.safe_load(frontmatter) or {}
    return meta, text


def _server_version() -> str:
    try:
        return version("synergy-mcp")
    except PackageNotFoundError:
        return "0.0.0+local"


def _skill_records() -> list[dict]:
    skills = []
    root = _skills_root()
    if root.exists():
        for path in sorted(root.glob("*/SKILL.md")):
            meta, _ = _read_skill(path.parent.name)
            required = list(meta.get("requires_tools") or [])
            skills.append(
                {
                    "name": meta.get("name", path.parent.name),
                    "description": meta.get("description", ""),
                    "version": str(meta.get("version", "")),
                    "families": meta.get("families", []),
                    "servers": meta.get("servers", []),
                    "requires_tools": required,
                    "missing_tools": [tool for tool in required if tool not in _REGISTERED_TOOLS],
                    "delivery": "served",
                }
            )
    return skills


@mcp.resource("synergy://status", mime_type="application/json")
def status_resource() -> str:
    """Report server version, read-only posture, registered tools and expected served skills."""
    return json.dumps(
        {
            "server": "synergy-mcp",
            "server_version": _server_version(),
            "read_only": True,
            "skill_delivery": "served",
            "skills": _skill_records(),
            "tools": sorted(_REGISTERED_TOOLS),
        },
        indent=2,
    )


@mcp.resource("synergy://skills", mime_type="application/json")
def skills_index() -> str:
    """List served Synergy skills without loading their full bodies."""
    return json.dumps({"skills": _skill_records()}, indent=2)


@mcp.resource("synergy://skills/{name}", mime_type="text/markdown")
def skill_resource(name: str) -> str:
    """Return a served Synergy skill body."""
    _, text = _read_skill(name)
    return text


@mcp.tool()
def list_databases() -> dict:
    """List the Synergy databases this server is configured to reach."""
    cfg = _config()
    return {
        "read_only": True,
        "databases": [
            {
                "name": db.name,
                "db_path": db.database,
                "host": db.host,
                "role": db.role,
                "description": db.description,
            }
            for db in cfg.databases.values()
        ],
    }


@mcp.tool()
def health_check(database: str) -> dict:
    """Verify the ccm session for a database, starting one if needed. Run this first."""
    return _sessions().health(database)


@mcp.tool()
def ccm_version(database: str) -> dict:
    """Report the Synergy client version, to confirm CLI syntax assumptions."""
    return _text_tool(database, ["version"])


@mcp.tool()
def query(
    database: str,
    expression: str,
    fields: list[str] | None = None,
    max_rows: int | None = None,
) -> dict:
    """Run a `ccm query` and return structured rows.

    `expression` is raw Synergy query syntax, e.g.
    "type='csrc' and status='integrate'" or "is_member_of('proj-1:project:1')".
    `fields` are bare attribute names such as objectname, status, owner, task.
    """
    cfg = _config()
    fields = fields or list(DEFAULT_OBJECT_FIELDS)
    limit = min(max_rows or cfg.max_rows, cfg.max_rows)

    argv = ["query", expression, "-u", "-ns", "-f", format_spec(fields)]
    try:
        result = _sessions().run(database, argv)
    except CcmError as exc:
        if is_empty_result(exc.result.stdout, exc.result.stderr):
            return {
                "database": database,
                "expression": expression,
                "fields": fields,
                "rows": [],
                "returned": 0,
                "total_matched": 0,
                "truncated": False,
            }
        raise

    parsed = parse_rows(result.stdout, fields, limit)
    return {"database": database, "expression": expression, "fields": fields, **parsed}


@mcp.tool()
def object_properties(database: str, object_name: str) -> dict:
    """Show the properties of a Synergy object (`ccm properties`)."""
    return _text_tool(database, ["properties", _safe_object(object_name)])


@mcp.tool()
def object_attributes(database: str, object_name: str) -> dict:
    """List all attributes defined on an object (`ccm attribute -la`)."""
    return _text_tool(database, ["attribute", "-la", _safe_object(object_name)])


@mcp.tool()
def attribute_value(database: str, object_name: str, attribute: str) -> dict:
    """Show one attribute's value (`ccm attribute -show <attr>`)."""
    attr = _safe_object(attribute, "attribute")
    return _text_tool(database, ["attribute", "-show", attr, _safe_object(object_name)])


@mcp.tool()
def object_content(database: str, object_name: str) -> dict:
    """Dump the file content of a specific object version (`ccm cat`)."""
    return _text_tool(database, ["cat", _safe_object(object_name)])


@mcp.tool()
def object_history(database: str, object_name: str) -> dict:
    """Show the version history of an object (`ccm history`)."""
    return _text_tool(database, ["history", _safe_object(object_name)])


@mcp.tool()
def object_diff(database: str, object_a: str, object_b: str) -> dict:
    """Diff two object versions (`ccm diff`)."""
    return _text_tool(
        database,
        ["diff", _safe_object(object_a, "object_a"), _safe_object(object_b, "object_b")],
    )


@mcp.tool()
def find_use(database: str, object_name: str) -> dict:
    """Find which projects use an object version (`ccm finduse`)."""
    return _text_tool(database, ["finduse", _safe_object(object_name)])


@mcp.tool()
def task_info(database: str, task: str) -> dict:
    """Show details of a task (`ccm task -show info`). Accepts a task number or object name."""
    return _text_tool(database, ["task", "-show", "info", _safe_object(task, "task")])


@mcp.tool()
def task_objects(database: str, task: str) -> dict:
    """List the object versions associated with a task (`ccm task -show objects`)."""
    return _text_tool(database, ["task", "-show", "objects", _safe_object(task, "task")])


@mcp.tool()
def find_tasks(
    database: str,
    owner: str | None = None,
    release: str | None = None,
    status: str | None = None,
    max_rows: int | None = None,
) -> dict:
    """Query tasks by owner, release and/or status."""
    clauses = ["cvtype='task'"]
    for field, value in (("owner", owner), ("release", release), ("status", status)):
        if value:
            clauses.append(f"{field}='{_safe_object(value, field)}'")
    return query(database, " and ".join(clauses), DEFAULT_TASK_FIELDS, max_rows)


@mcp.tool()
def project_members(
    database: str,
    project: str,
    recursive: bool = False,
    max_rows: int | None = None,
) -> dict:
    """List the members of a project, optionally descending the full hierarchy."""
    proj = _safe_object(project, "project")
    expression = (
        f"hierarchy_project_members('{proj}','none')"
        if recursive
        else f"is_member_of('{proj}')"
    )
    return query(database, expression, ["objectname", "status", "owner", "task"], max_rows)


@mcp.tool()
def find_baselines(database: str, release: str | None = None, max_rows: int | None = None) -> dict:
    """List baselines, optionally filtered by release."""
    expression = "cvtype='baseline'"
    if release:
        expression += f" and release='{_safe_object(release, 'release')}'"
    return query(
        database,
        expression,
        ["objectname", "status", "release", "owner", "create_time"],
        max_rows,
    )


@mcp.tool()
def project_grouping_info(database: str, project: str) -> dict:
    """Show project grouping information for a project (`ccm project_grouping`)."""
    return _text_tool(database, ["project_grouping", _safe_object(project, "project")])


@mcp.tool()
def run_readonly_command(database: str, args: list[str]) -> dict:
    """Escape hatch: run an allowlisted read-only ccm command as an argv list.

    Example: ["conflicts", "myproj-1:project:1"]. Mutating verbs and sub-flags
    are rejected by the policy layer.
    """
    return _text_tool(database, [str(a) for a in args])


@mcp.tool()
def knowledge_search(
    search: str,
    corpus: str | None = None,
    family: str | None = None,
    limit: int = 10,
) -> dict:
    """Search the local Synergy reference corpus built from ccm help and manuals."""
    try:
        return search_knowledge(search, corpus=corpus, family=family, limit=limit)
    except KnowledgeError as exc:
        raise ValueError(f"UNAVAILABLE: {exc}") from exc


@mcp.tool()
def check_skill_version(name: str, client_version: str) -> dict:
    """Compare a client's loaded served skill version with the server's expected version."""
    records = {record["name"]: record for record in _skill_records()}
    if name not in records:
        return {
            "name": name,
            "known": False,
            "client_version": client_version,
            "server_version": None,
            "match": False,
            "alerts": [f"Unknown Synergy skill {name!r}. Read synergy://skills for the served index."],
        }
    record = records[name]
    match = str(record["version"]) == str(client_version)
    alerts = [] if match else [
        f"Skill {name} version drift: client has {client_version}, server expects {record['version']}."
    ]
    if record["missing_tools"]:
        alerts.append(f"Skill {name} requires missing tools: {', '.join(record['missing_tools'])}.")
    return {
        "name": name,
        "known": True,
        "client_version": client_version,
        "server_version": record["version"],
        "match": match,
        "missing_tools": record["missing_tools"],
        "alerts": alerts,
    }


def run() -> None:
    logging.basicConfig(
        level=_LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
    logging.getLogger("synergy_mcp").setLevel(_LOG_LEVEL)
    log.info("synergy-mcp starting (log_level=%s)", _LOG_LEVEL)
    mcp.run()
