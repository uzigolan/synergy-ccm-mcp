"""Turn ccm's delimited text output into structured rows."""

from __future__ import annotations

# Chosen because it cannot appear in a Synergy object name, status, or task synopsis.
FIELD_SEP = "\x1f"

DEFAULT_OBJECT_FIELDS = ["objectname", "status", "owner", "type", "create_time"]
DEFAULT_TASK_FIELDS = ["displayname", "task_synopsis", "status", "resolver", "release"]

_NO_RESULT_MARKERS = (
    "no results",
    "no match",
    "warning: no objects",
)


def format_spec(fields: list[str]) -> str:
    """Build the argument for ccm's -f flag from bare attribute names."""
    return FIELD_SEP.join(f"%{f}" for f in fields)


def parse_rows(stdout: str, fields: list[str], max_rows: int) -> dict:
    """Parse -f delimited output into a list of dicts plus truncation metadata."""
    rows: list[dict[str, str]] = []
    total = 0

    for line in stdout.splitlines():
        if not line.strip():
            continue
        if FIELD_SEP not in line and len(fields) > 1:
            # Warnings and banners from ccm arrive without the separator.
            continue
        total += 1
        if len(rows) >= max_rows:
            continue
        parts = line.split(FIELD_SEP)
        parts += [""] * (len(fields) - len(parts))
        rows.append({name: parts[i].strip() for i, name in enumerate(fields)})

    return {
        "rows": rows,
        "returned": len(rows),
        "total_matched": total,
        "truncated": total > len(rows),
    }


def is_empty_result(stdout: str, stderr: str) -> bool:
    """ccm exits non-zero when a query simply matches nothing; that is not an error."""
    blob = f"{stdout}\n{stderr}".lower()
    return any(marker in blob for marker in _NO_RESULT_MARKERS)
