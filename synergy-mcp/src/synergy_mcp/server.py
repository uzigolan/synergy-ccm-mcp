"""synergy-mcp: read-only MCP tools over the IBM Rational Synergy 7.2 `ccm` CLI."""

from __future__ import annotations

import atexit
import fnmatch
import json
import logging
import os
import re
from collections import Counter
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from mcp.server.fastmcp import FastMCP
import yaml

from .config import ServerConfig, load_config
from .exec import CcmError
from .formats import (
    DEFAULT_CR_FIELDS,
    DEFAULT_OBJECT_FIELDS,
    DEFAULT_TASK_FIELDS,
    format_spec,
    is_empty_result,
    normalize_time,
    parse_rows,
    parse_task_objects,
    rows_to_delimited,
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
# Same set plus the wildcards ccm's `match` operator understands.
_PATTERN_RE = re.compile(r"^[A-Za-z0-9_.:~#+!@\-/\\ *?]{1,400}$")
_SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
_CVTYPE_RE = re.compile(r"^[a-z_][a-z0-9_]{0,40}$")
_ATTR_RE = re.compile(r"^_?[A-Za-z][A-Za-z0-9_]{0,80}$")
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_REGISTERED_TOOLS = frozenset(
    {
        "list_databases",
        "health_check",
        "ccm_version",
        "show_capabilities",
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
        "task_objects_bulk",
        "find_tasks",
        "find_crs",
        "find_trs",
        "trs_info",
        "trs_changes",
        "summarize_release_changes",
        "cr_info",
        "cr_tasks",
        "find_releases",
        "list_attributes",
        "project_members",
        "find_baselines",
        "project_grouping_info",
        "run_readonly_command",
        "knowledge_search",
        "check_skill_version",
    }
)

# Guards a single bulk call from turning into hundreds of ccm round trips.
_MAX_BULK_TASKS = 100
_TRS_RE = re.compile(r"^(?:TRS[- ]?)?(\d{1,12})$", re.IGNORECASE)


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


def _safe_pattern(pattern: str, label: str = "pattern") -> str:
    pattern = pattern.strip()
    if not _PATTERN_RE.match(pattern):
        raise ValueError(
            f"Invalid {label} {pattern!r}. Use plain text with '*' or '?' wildcards, e.g. 'etxa*'."
        )
    return pattern


def _safe_attr(attr: str, label: str = "field") -> str:
    attr = attr.strip().lower()
    if not _ATTR_RE.match(attr):
        raise ValueError(f"Invalid {label} {attr!r}. Expected a Synergy attribute name.")
    return attr


def _safe_fields(fields: list[str]) -> list[str]:
    return [_safe_attr(field, "field") for field in fields]


def _normalize_query_expression(expression: str) -> str:
    """Normalize Synergy query identifiers without changing quoted values."""
    parts = re.split(r"('[^']*')", expression)
    for index in range(0, len(parts), 2):
        parts[index] = _IDENT_RE.sub(lambda match: match.group(0).lower(), parts[index])
    return "".join(parts)


def _case_variants(value: str) -> list[str]:
    variants = [value, value.lower(), value.upper(), value.title()]
    return list(dict.fromkeys(variants))


def _eq_clause(field: str, value: str) -> str:
    field = _safe_attr(field)
    variants = [_safe_object(variant, field) for variant in _case_variants(value)]
    if len(variants) == 1:
        return f"{field}='{variants[0]}'"
    return "(" + " or ".join(f"{field}='{variant}'" for variant in variants) + ")"


def _match_clause(field: str, pattern: str) -> str:
    field = _safe_attr(field)
    variants = [_safe_pattern(variant, field) for variant in _case_variants(pattern)]
    if len(variants) == 1:
        return f"{field} match '{variants[0]}'"
    return "(" + " or ".join(f"{field} match '{variant}'" for variant in variants) + ")"


def _safe_cvtype(cvtype: str) -> str:
    cvtype = cvtype.strip().lower()
    if not _CVTYPE_RE.match(cvtype):
        raise ValueError(f"Invalid cvtype {cvtype!r}. Expected e.g. 'task', 'problem', 'project'.")
    return cvtype


def _date_clause(field: str, value: str, operator: str) -> str:
    return f"{field}{operator}{normalize_time(value)}"


def _wildcard_match(value: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(str(value).lower(), str(pattern).lower())


def _safe_trs(trs: str) -> str:
    text = str(trs).strip()
    match = _TRS_RE.match(text)
    if not match:
        raise ValueError(f"Invalid TRS {trs!r}. Use a number like '24952' or 'TRS-24952'.")
    return match.group(1)


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
def show_capabilities() -> dict:
    """Show all available Synergy MCP tools, skills, and capabilities."""
    return json.loads(_status_resource())


def _run_query(
    database: str,
    expression: str,
    fields: list[str] | None = None,
    max_rows: int | None = None,
    *,
    offset: int = 0,
    group_by: list[str] | None = None,
    count_only: bool = False,
    output_format: str = "rows",
) -> dict:
    cfg = _config()
    expression = _normalize_query_expression(expression)
    fields = _safe_fields(fields or list(DEFAULT_OBJECT_FIELDS))
    group_by = _safe_fields(group_by) if group_by else None
    limit = min(max_rows or cfg.max_rows, cfg.max_rows)
    if offset < 0:
        raise ValueError("offset must be zero or positive.")
    if output_format not in ("rows", "csv", "tsv"):
        raise ValueError(f"Unknown format {output_format!r}. Use 'rows', 'csv' or 'tsv'.")

    argv = ["query", expression, "-u", "-ns", "-f", format_spec(fields)]
    header = {"database": database, "expression": expression, "fields": fields}
    try:
        result = _sessions().run(database, argv)
    except CcmError as exc:
        if is_empty_result(exc.result.stdout, exc.result.stderr):
            empty = (
                {"grouped_by": group_by, "groups": [], "distinct_groups": 0, "total_matched": 0}
                if group_by
                else {"rows": [], "returned": 0, "total_matched": 0, "truncated": False}
            )
            return {**header, **empty}
        raise

    parsed = parse_rows(
        result.stdout, fields, limit, offset=offset, group_by=group_by, count_only=count_only
    )
    if output_format != "rows" and "rows" in parsed:
        delimiter = "," if output_format == "csv" else "\t"
        parsed["text"] = rows_to_delimited(parsed["rows"], fields, delimiter)
        parsed["format"] = output_format
        del parsed["rows"]
    return {**header, **parsed}


@mcp.tool()
def query(
    database: str,
    expression: str,
    fields: list[str] | None = None,
    max_rows: int | None = None,
    offset: int = 0,
    group_by: list[str] | None = None,
    count_only: bool = False,
    format: str = "rows",
) -> dict:
    """Run a `ccm query` and return structured rows.

    `expression` is raw Synergy query syntax, e.g.
    "type='csrc' and status='integrate'" or "is_member_of('proj-1:project:1')".
    `fields` are bare attribute names such as objectname, status, owner, task.
    Use `count_only` for totals, `group_by` for a per-key rollup (fields must be
    in `fields`), `offset` to page, and format='csv'|'tsv' for spreadsheet text.
    """
    return _run_query(
        database,
        expression,
        fields,
        max_rows,
        offset=offset,
        group_by=group_by,
        count_only=count_only,
        output_format=format,
    )


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
    release_match: str | None = None,
    status: str | None = None,
    resolver: str | None = None,
    completed_since: str | None = None,
    completed_until: str | None = None,
    max_rows: int | None = None,
    offset: int = 0,
    group_by: list[str] | None = None,
    count_only: bool = False,
    format: str = "rows",
) -> dict:
    """Query tasks by owner, resolver, release, status and completion date.

    Use `release_match='etxa*'` to roll up a whole product line, and
    `completed_since='1/2/2026'` / 'H1 2026' / 'last 6 months' for date windows.
    """
    clauses = ["cvtype='task'"]
    for field, value in (
        ("owner", owner),
        ("release", release),
        ("status", status),
        ("resolver", resolver),
    ):
        if value:
            clauses.append(_eq_clause(field, value))
    if release_match:
        clauses.append(_match_clause("release", release_match))
    if completed_since:
        clauses.append(_date_clause("completion_date", completed_since, ">"))
    if completed_until:
        clauses.append(_date_clause("completion_date", completed_until, "<"))

    fields = list(DEFAULT_TASK_FIELDS)
    if completed_since or completed_until or (group_by and "completion_date" in group_by):
        fields.append("completion_date")

    return _run_query(
        database,
        " and ".join(clauses),
        fields,
        max_rows,
        offset=offset,
        group_by=group_by,
        count_only=count_only,
        output_format=format,
    )


@mcp.tool()
def find_crs(
    database: str,
    trs: str | None = None,
    crstatus: str | None = None,
    severity: str | None = None,
    release: str | None = None,
    release_match: str | None = None,
    resolver: str | None = None,
    product_name: str | None = None,
    entered_since: str | None = None,
    entered_until: str | None = None,
    max_rows: int | None = None,
    offset: int = 0,
    group_by: list[str] | None = None,
    count_only: bool = False,
    format: str = "rows",
) -> dict:
    """Query change requests (`cvtype='problem'`) by TRS, status, severity, release and entry date.

    The CR counterpart of find_tasks. Returns the standard CR field set:
    problem_number, trs, crstatus, severity, priority, product_name, phase_found,
    submitter_name, resolver, entry/resolution/conclusion dates and synopsis.
    """
    clauses = ["cvtype='problem'"]
    for field, value in (
        ("trs", trs),
        ("crstatus", crstatus),
        ("severity", severity),
        ("release", release),
        ("resolver", resolver),
        ("product_name", product_name),
    ):
        if value:
            clauses.append(_eq_clause(field, value))
    if release_match:
        clauses.append(_match_clause("release", release_match))
    if entered_since:
        clauses.append(_date_clause("entry_date", entered_since, ">"))
    if entered_until:
        clauses.append(_date_clause("entry_date", entered_until, "<"))

    return _run_query(
        database,
        " and ".join(clauses),
        list(DEFAULT_CR_FIELDS),
        max_rows,
        offset=offset,
        group_by=group_by,
        count_only=count_only,
        output_format=format,
    )


def _trs_rows(
    database: str,
    expression: str,
    source: str,
    confidence: str,
    limit: int,
    *,
    required: bool = False,
) -> list[dict]:
    try:
        result = _run_query(
            database,
            expression,
            [
                "objectname",
                "problem_number",
                "trs",
                "crstatus",
                "release",
                "fixed_in_baseline",
                "phase_fixed",
                "resolver",
                "problem_synopsis",
            ],
            limit,
        )
    except CcmError:
        if required:
            raise
        return []
    rows = result.get("rows") or []
    for row in rows:
        row["match_source"] = source
        row["confidence"] = confidence
    return rows


def _task_trs_rows(database: str, trs: str, limit: int) -> tuple[list[dict], list[dict]]:
    try:
        task_result = _run_query(
            database,
            f"cvtype='task' and task_synopsis match '*TRS*{trs}*'",
            ["displayname", "objectname", "status", "resolver", "release", "task_synopsis"],
            limit,
        )
    except CcmError:
        return [], []
    tasks = task_result.get("rows") or []
    matches: list[dict] = []
    seen: set[str] = set()
    for task in tasks:
        task_name = task.get("displayname") or task.get("objectname") or ""
        if not task_name:
            continue
        try:
            info = task_info(database, task_name)
        except Exception as exc:
            task["cr_lookup_error"] = str(exc)
            continue
        output = info.get("output", "")
        for cr_number, synopsis in re.findall(r"\b[A-Za-z]+!(\d+):\s*(.+)", output):
            if cr_number in seen:
                continue
            seen.add(cr_number)
            cr_rows = _trs_rows(
                database,
                f"cvtype='problem' and problem_number='{cr_number}'",
                "task_synopsis",
                "medium",
                1,
            )
            if cr_rows:
                cr_rows[0]["matched_task"] = task
                cr_rows[0]["associated_cr_text"] = synopsis.strip()
                matches.extend(cr_rows)
    return matches, tasks


def _dedupe_trs_matches(matches: list[dict]) -> list[dict]:
    priority = {"trs_attribute": 0, "problem_synopsis": 1, "task_synopsis": 2}
    by_cr: dict[str, dict] = {}
    for row in matches:
        key = row.get("problem_number") or row.get("objectname") or json.dumps(row, sort_keys=True)
        current = by_cr.get(key)
        if current is None or priority.get(row.get("match_source", ""), 99) < priority.get(
            current.get("match_source", ""), 99
        ):
            by_cr[key] = row
    return sorted(by_cr.values(), key=lambda item: item.get("problem_number", ""))


@mcp.tool()
def find_trs(
    database: str,
    trs: str,
    include_text_fallback: bool = True,
    max_rows: int | None = None,
) -> dict:
    """Find CRs related to a TRS number using the TRS field, CR text and task text."""
    number = _safe_trs(trs)
    limit = min(max_rows or _config().max_rows, _config().max_rows)
    matches = _trs_rows(
        database,
        f"cvtype='problem' and trs='{number}'",
        "trs_attribute",
        "exact",
        limit,
    )
    task_candidates: list[dict] = []
    if include_text_fallback and not matches:
        remaining = max(limit - len(matches), 1)
        matches.extend(
            _trs_rows(
                database,
                f"cvtype='problem' and problem_synopsis match '*TRS*{number}*'",
                "problem_synopsis",
                "high",
                remaining,
            )
        )
        task_matches, task_candidates = _task_trs_rows(database, number, remaining)
        matches.extend(task_matches)

    deduped = _dedupe_trs_matches(matches)[:limit]
    return {
        "database": database,
        "trs": number,
        "matches": deduped,
        "match_count": len(deduped),
        "task_candidates": task_candidates,
        "warnings": [
            "Some older CRs store TRS only in synopsis/task text; inspect match_source and confidence."
        ]
        if any(row.get("match_source") != "trs_attribute" for row in deduped)
        else [],
    }


@mcp.tool()
def trs_info(
    database: str,
    trs: str,
    include_tasks: bool = True,
    include_objects: bool = False,
) -> dict:
    """Show manager-friendly CR/task context for a TRS number."""
    found = find_trs(database, trs, include_text_fallback=True)
    details: list[dict] = []
    for match in found.get("matches", []):
        cr_number = match.get("problem_number")
        detail = {"match": match}
        if cr_number:
            detail["cr_info"] = cr_info(database, cr_number)
            if include_tasks:
                detail["cr_tasks"] = cr_tasks(database, cr_number, include_objects=include_objects)
        details.append(detail)
    return {**found, "details": details}


@mcp.tool()
def trs_changes(database: str, trs: str) -> dict:
    """List changed objects for all tasks associated with a TRS."""
    info = trs_info(database, trs, include_tasks=True, include_objects=False)
    tasks: set[str] = set()
    for detail in info.get("details", []):
        for task in (detail.get("cr_tasks") or {}).get("tasks", []):
            if re.search(r"!\d+\b", task):
                tasks.add(task)
    if not tasks:
        return {**info, "objects": None, "object_note": "No associated tasks found."}
    objects = task_objects_bulk(database, sorted(tasks))
    return {**info, "objects": objects}


def _classify_cr(row: dict) -> str:
    text = " ".join(
        str(row.get(field, ""))
        for field in ("request_type", "problem_synopsis", "trs", "phase_fixed")
    ).lower()
    if row.get("trs") and row.get("trs") != "<void>":
        return "trs_fix"
    if re.search(r"\btrs\s*[- ]?\d+", text):
        return "trs_fix"
    if any(word in text for word in ("enhancement", "feature", "add ", "support", "introduce")):
        return "enhancement_or_feature"
    if any(word in text for word in ("fix", "bug", "problem", "failure", "does not", "cannot")):
        return "fix"
    return "other"


def _summary_rows(database: str, expression: str, source: str, limit: int) -> list[dict]:
    result = _run_query(database, expression, list(DEFAULT_CR_FIELDS), limit)
    rows = result.get("rows") or []
    for row in rows:
        row["match_source"] = source
        row["change_type"] = _classify_cr(row)
    return rows


@mcp.tool()
def summarize_release_changes(
    database: str,
    trs_values: list[str] | None = None,
    release_match: str | None = None,
    fixed_baseline_match: str | None = None,
    include_tasks: bool = False,
    max_rows: int | None = None,
) -> dict:
    """Summarize TRS fixes, enhancements and other CRs for a release/baseline slice.

    Use `trs_values` when release notes already identified solved TRSs. Use
    `release_match` or `fixed_baseline_match` to gather Synergy CRs directly.
    """
    if not any((trs_values, release_match, fixed_baseline_match)):
        raise ValueError("Pass trs_values, release_match or fixed_baseline_match.")

    limit = min(max_rows or _config().max_rows, _config().max_rows)
    rows: list[dict] = []
    warnings: list[str] = []

    for value in trs_values or []:
        found = find_trs(database, value, max_rows=limit)
        for match in found.get("matches", []):
            match = dict(match)
            match["input_trs"] = _safe_trs(value)
            match["change_type"] = _classify_cr(match)
            rows.append(match)
        warnings.extend(found.get("warnings", []))

    if release_match and not trs_values:
        try:
            rows.extend(
                _summary_rows(
                    database,
                    f"cvtype='problem' and release match '{_safe_pattern(release_match, 'release_match')}'",
                    "release_match",
                    limit,
                )
            )
        except (CcmError, RuntimeError) as exc:
            warnings.append(f"release_match query failed: {exc}")

    if fixed_baseline_match and not trs_values:
        try:
            rows.extend(
                _summary_rows(
                    database,
                    f"cvtype='problem' and fixed_in_baseline match '{_safe_pattern(fixed_baseline_match, 'fixed_baseline_match')}'",
                    "fixed_baseline_match",
                    limit,
                )
            )
        except (CcmError, RuntimeError) as exc:
            warnings.append(f"fixed_baseline_match query failed: {exc}")

    deduped: dict[str, dict] = {}
    for row in rows:
        key = row.get("problem_number") or row.get("objectname") or json.dumps(row, sort_keys=True)
        deduped.setdefault(key, row)
    final_rows = list(deduped.values())
    if trs_values and release_match:
        final_rows = [row for row in final_rows if _wildcard_match(row.get("release", ""), release_match)]
    if trs_values and fixed_baseline_match:
        final_rows = [
            row
            for row in final_rows
            if _wildcard_match(row.get("fixed_in_baseline", ""), fixed_baseline_match)
        ]
    final_rows = sorted(
        final_rows, key=lambda row: (row.get("change_type", ""), row.get("problem_number", ""))
    )
    buckets = Counter(row.get("change_type", "other") for row in final_rows)

    tasks: dict[str, dict] = {}
    if include_tasks:
        for row in final_rows:
            cr_number = row.get("problem_number")
            if cr_number:
                tasks[cr_number] = cr_tasks(database, cr_number)

    return {
        "database": database,
        "criteria": {
            "trs_values": [_safe_trs(value) for value in trs_values or []],
            "release_match": release_match,
            "fixed_baseline_match": fixed_baseline_match,
        },
        "summary": dict(buckets),
        "total_crs": len(final_rows),
        "crs": final_rows,
        "tasks": tasks,
        "warnings": sorted(set(warnings)),
    }


def _cr_objectname(database: str, cr: str) -> str:
    """Resolve a bare CR number to its problem object name."""
    cr = cr.strip()
    if ":problem:" in cr:
        return _safe_object(cr, "cr")
    number = cr.lstrip("#").replace("problem", "")
    if not number.isdigit():
        raise ValueError(f"Invalid cr {cr!r}. Pass a number like '102454' or a full object name.")
    found = _run_query(
        database, f"cvtype='problem' and problem_number='{number}'", ["objectname"], 2
    )
    rows = found.get("rows") or []
    if not rows:
        raise ValueError(f"No change request found with problem_number '{number}'.")
    return rows[0]["objectname"]


@mcp.tool()
def cr_info(database: str, cr: str) -> dict:
    """Show a change request's properties. Accepts a CR number or full problem object name."""
    objectname = _cr_objectname(database, cr)
    result = _text_tool(database, ["properties", objectname])
    return {"cr": objectname, **result}


@mcp.tool()
def cr_tasks(database: str, cr: str, include_objects: bool = False) -> dict:
    """List the tasks associated with a change request, optionally with their changed objects."""
    objectname = _cr_objectname(database, cr)
    result = _text_tool(database, ["properties", objectname])
    output = result.get("output", "")
    tasks = sorted(set(re.findall(r"\b[A-Za-z]+![0-9]+\b", output)))

    payload = {"cr": objectname, "tasks": tasks, "task_count": len(tasks), "properties": output}
    if include_objects and tasks:
        payload["objects"] = task_objects_bulk(database, tasks)
    return payload


@mcp.tool()
def task_objects_bulk(database: str, tasks: list[str]) -> dict:
    """List changed objects for many tasks at once, with a file-frequency rollup.

    Replaces looping `task_objects` per task. Capped at 100 tasks per call so a
    single request cannot turn into hundreds of ccm round trips.
    """
    if not tasks:
        raise ValueError("No tasks given.")
    if len(tasks) > _MAX_BULK_TASKS:
        raise ValueError(
            f"{len(tasks)} tasks requested; the cap is {_MAX_BULK_TASKS} per call. "
            f"Narrow the task set or page through it."
        )

    per_task: list[dict] = []
    frequency: Counter[str] = Counter()
    errors: list[dict] = []

    for task in tasks:
        safe = _safe_object(str(task), "task")
        try:
            result = _sessions().run(database, ["task", "-show", "objects", safe])
        except CcmError as exc:
            errors.append({"task": safe, "error": str(exc)})
            continue
        objects = parse_task_objects(result.text)
        frequency.update(obj["name"] for obj in objects)
        per_task.append({"task": safe, "object_count": len(objects), "objects": objects})

    return {
        "database": database,
        "tasks_requested": len(tasks),
        "tasks_read": len(per_task),
        "distinct_files": len(frequency),
        "file_frequency": [
            {"name": name, "tasks": count} for name, count in frequency.most_common()
        ],
        "per_task": per_task,
        "errors": errors,
    }


@mcp.tool()
def find_releases(database: str, pattern: str | None = None, max_rows: int | None = None) -> dict:
    """List release definitions, optionally filtered by a name pattern such as 'etx2i'."""
    expression = "cvtype='releasedef'"
    if pattern:
        term = _safe_pattern(pattern, "pattern")
        if "*" not in term and "?" not in term:
            term = f"*{term}*"
        expression += f" and name match '{term}'"
    return _run_query(
        database,
        expression,
        ["objectname", "name", "version", "status", "owner", "create_time"],
        max_rows,
    )


@mcp.tool()
def list_attributes(database: str, cvtype: str) -> dict:
    """List the attributes available on a given cvtype, sampled from a real object.

    Use this before writing a query instead of guessing field names; `objectname`,
    for instance, is not a queryable attribute.
    """
    kind = _safe_cvtype(cvtype)
    sample = _run_query(database, f"cvtype='{kind}'", ["objectname"], 1)
    rows = sample.get("rows") or []
    if not rows:
        return {"database": database, "cvtype": kind, "attributes": [], "sample_object": None}

    objectname = rows[0]["objectname"]
    result = _sessions().run(database, ["attribute", "-la", objectname])
    attributes = sorted(
        {
            line.split()[0]
            for line in result.text.splitlines()
            if line.strip() and not line.startswith(" ") and line.split()
        }
    )
    return {
        "database": database,
        "cvtype": kind,
        "sample_object": objectname,
        "attributes": attributes,
        "raw": result.text.strip(),
    }


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
    return _run_query(database, expression, ["objectname", "status", "owner", "task"], max_rows)


@mcp.tool()
def find_baselines(database: str, release: str | None = None, max_rows: int | None = None) -> dict:
    """List baselines, optionally filtered by release."""
    expression = "cvtype='baseline'"
    if release:
        expression += f" and release='{_safe_object(release, 'release')}'"
    return _run_query(
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
