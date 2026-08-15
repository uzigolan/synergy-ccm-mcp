"""synergy-mcp: read-only MCP tools over the IBM Rational Synergy 7.2 `ccm` CLI."""

from __future__ import annotations

import atexit
import logging
import re
from functools import lru_cache

from mcp.server.fastmcp import FastMCP

from .config import ServerConfig, load_config
from .exec import CcmError
from .formats import (
    DEFAULT_OBJECT_FIELDS,
    DEFAULT_TASK_FIELDS,
    format_spec,
    is_empty_result,
    parse_rows,
)
from .session import SessionManager

log = logging.getLogger("synergy_mcp")

mcp = FastMCP("synergy-mcp")

# Object names are interpolated into ccm query expressions, so anything that
# could break out of a single-quoted literal is rejected up front.
_OBJECTNAME_RE = re.compile(r"^[A-Za-z0-9_.:~#+\-/\\ ]{1,400}$")


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
def run_readonly_command(database: str, args: list[str]) -> dict:
    """Escape hatch: run an allowlisted read-only ccm command as an argv list.

    Example: ["conflicts", "myproj-1:project:1"]. Mutating verbs and sub-flags
    are rejected by the policy layer.
    """
    return _text_tool(database, [str(a) for a in args])


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    mcp.run()
