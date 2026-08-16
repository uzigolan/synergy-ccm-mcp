"""Turn ccm's delimited text output into structured rows."""

from __future__ import annotations

import csv
import io
import re
from collections import Counter
from datetime import date, timedelta

# Chosen because it cannot appear in a Synergy object name, status, or task synopsis.
FIELD_SEP = "\x1f"

DEFAULT_OBJECT_FIELDS = ["objectname", "status", "owner", "type", "create_time"]
DEFAULT_TASK_FIELDS = ["displayname", "task_synopsis", "status", "resolver", "release"]
DEFAULT_CR_FIELDS = [
    "problem_number",
    "crstatus",
    "request_type",
    "severity",
    "priority",
    "product_name",
    "component",
    "subsystem",
    "found_at_site",
    "phase_found",
    "phase_fixed",
    "submitter_name",
    "resolver",
    "in_verification_by",
    "entry_date",
    "resolution_date",
    "conclusion_date",
    "release",
    "problem_synopsis",
]

_NO_RESULT_MARKERS = (
    "no results",
    "no match",
    "warning: no objects",
)

_RELATIVE_RE = re.compile(r"^last\s+(\d+)\s+(day|week|month|year)s?$", re.IGNORECASE)
_ISO_RE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_US_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_HALF_RE = re.compile(r"^(H[12])\s+(\d{4})$", re.IGNORECASE)


def format_spec(fields: list[str]) -> str:
    """Build the argument for ccm's -f flag from bare attribute names."""
    return FIELD_SEP.join(f"%{f}" for f in fields)


def parse_rows(
    stdout: str,
    fields: list[str],
    max_rows: int,
    *,
    offset: int = 0,
    group_by: list[str] | None = None,
    count_only: bool = False,
) -> dict:
    """Parse -f delimited output into rows, a group-by rollup, or just a count."""
    parsed: list[dict[str, str]] = []

    for line in stdout.splitlines():
        if not line.strip():
            continue
        if FIELD_SEP not in line and len(fields) > 1:
            # Warnings and banners from ccm arrive without the separator.
            continue
        parts = line.split(FIELD_SEP)
        parts += [""] * (len(fields) - len(parts))
        parsed.append({name: parts[i].strip() for i, name in enumerate(fields)})

    total = len(parsed)

    if group_by:
        missing = [f for f in group_by if f not in fields]
        if missing:
            raise ValueError(
                f"group_by fields {missing} are not in the requested fields {fields}."
            )
        counter = Counter(tuple(row[f] for f in group_by) for row in parsed)
        groups = [
            {"key": dict(zip(group_by, key)), "count": count}
            for key, count in counter.most_common()
        ]
        return {
            "grouped_by": group_by,
            "groups": groups,
            "distinct_groups": len(groups),
            "total_matched": total,
        }

    if count_only:
        return {"rows": [], "returned": 0, "total_matched": total, "truncated": False}

    window = parsed[offset : offset + max_rows]
    return {
        "rows": window,
        "returned": len(window),
        "offset": offset,
        "total_matched": total,
        "truncated": offset + len(window) < total,
    }


def rows_to_delimited(rows: list[dict], fields: list[str], delimiter: str = ",") -> str:
    """Serialize parsed rows as CSV/TSV text for spreadsheet hand-off."""
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=fields, delimiter=delimiter, lineterminator="\n", extrasaction="ignore"
    )
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def normalize_time(value: str, *, today: date | None = None) -> str:
    """Turn a human date into the `time('M/D/YYYY')` literal ccm query expects.

    Accepts '2/1/2026', '2026-02-01', 'last 6 months' and 'H1 2026'.
    """
    text = value.strip()
    today = today or date.today()

    match = _RELATIVE_RE.match(text)
    if match:
        amount, unit = int(match.group(1)), match.group(2).lower()
        days = {"day": 1, "week": 7, "month": 30, "year": 365}[unit] * amount
        target = today - timedelta(days=days)
        return f"time('{target.month}/{target.day}/{target.year}')"

    match = _HALF_RE.match(text)
    if match:
        year = int(match.group(2))
        month = 1 if match.group(1).upper() == "H1" else 7
        return f"time('{month}/1/{year}')"

    match = _ISO_RE.match(text)
    if match:
        year, month, day = (int(g) for g in match.groups())
        return f"time('{month}/{day}/{year}')"

    match = _US_RE.match(text)
    if match:
        month, day, year = (int(g) for g in match.groups())
        return f"time('{month}/{day}/{year}')"

    raise ValueError(
        f"Unrecognized date {value!r}. Use '2/1/2026', '2026-02-01', 'H1 2026' or 'last 6 months'."
    )


_TASK_OBJECT_RE = re.compile(r"^\s*\d+\)\s+(\S+)(?:\s+(\S+))?(?:\s+(\S+))?")


def parse_task_objects(text: str) -> list[dict[str, str]]:
    """Parse the numbered listing produced by `ccm task -show objects`."""
    objects: list[dict[str, str]] = []
    for line in text.splitlines():
        match = _TASK_OBJECT_RE.match(line)
        if not match:
            continue
        objectname = match.group(1)
        objects.append(
            {
                "objectname": objectname,
                "name": objectname.split("~", 1)[0],
                "status": match.group(2) or "",
                "owner": match.group(3) or "",
            }
        )
    return objects


def is_empty_result(stdout: str, stderr: str) -> bool:
    """ccm exits non-zero when a query simply matches nothing; that is not an error."""
    blob = f"{stdout}\n{stderr}".lower()
    return any(marker in blob for marker in _NO_RESULT_MARKERS)
