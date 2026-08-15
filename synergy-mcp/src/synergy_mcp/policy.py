"""Command allowlist.

Phase 1 is read-only: every `ccm` invocation must clear this gate before exec.
Writes are not merely unimplemented, they are actively rejected here, so a
future write tier has to be opened deliberately rather than by accident.
"""

from __future__ import annotations

READ_ONLY_COMMANDS: frozenset[str] = frozenset(
    {
        "attribute",
        "baseline",
        "cat",
        "compare",
        "conflicts",
        "delim",
        "diff",
        "dir",
        "finduse",
        "folder",
        "help",
        "history",
        "ls",
        "monitor",
        "project_grouping",
        "properties",
        "prop",
        "ps",
        "query",
        "relate",
        "status",
        "task",
        "version",
    }
)

# Session lifecycle. Not user-callable as raw commands; the SessionManager owns these.
SESSION_COMMANDS: frozenset[str] = frozenset({"start", "stop"})

# Hard-denied regardless of tier or confirmation flags.
FORBIDDEN_COMMANDS: frozenset[str] = frozenset(
    {
        "archive",
        "db",
        "dcm",
        "delete",
        "migrate",
        "purge",
        "rename",
        "typedef",
        "unuse",
        "users",
    }
)

# Sub-flags that turn an otherwise-read command into a mutating one.
MUTATING_SUBFLAGS: frozenset[str] = frozenset(
    {
        "-create",
        "-modify",
        "-delete",
        "-del",
        "-remove",
        "-complete",
        "-checkin",
        "-uncheckout",
        "-associate",
        "-dissociate",
        "-set",
        "-add",
        "-fix",
    }
)


class PolicyError(PermissionError):
    """Raised when a command is not permitted by the current tier."""


def check_readonly(argv: list[str]) -> None:
    """Validate an argv list destined for the ccm binary. Raises PolicyError."""
    if not argv:
        raise PolicyError("Empty command.")

    command = argv[0]

    if command in FORBIDDEN_COMMANDS:
        raise PolicyError(
            f"'ccm {command}' is permanently blocked by synergy-mcp (destructive or admin-level)."
        )

    if command in SESSION_COMMANDS:
        raise PolicyError(
            f"'ccm {command}' is managed internally by the session pool and cannot be called directly."
        )

    if command not in READ_ONLY_COMMANDS:
        raise PolicyError(
            f"'ccm {command}' is not in the read-only allowlist. "
            f"Allowed: {', '.join(sorted(READ_ONLY_COMMANDS))}"
        )

    for arg in argv[1:]:
        if arg.lower() in MUTATING_SUBFLAGS:
            raise PolicyError(
                f"Sub-flag '{arg}' mutates the database; synergy-mcp is running in read-only mode."
            )

    return None
