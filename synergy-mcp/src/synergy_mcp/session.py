"""Synergy session pool.

Starting a `ccm` session is slow and consumes a floating licence seat, so the
server keeps one long-lived session per database and reuses it across tool
calls. Sessions started by this process are stopped on shutdown; sessions we
merely attached to (operator-provided CCM_ADDR) are left running.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time

from .config import DatabaseConfig, ServerConfig
from .exec import CcmError, CcmResult, run_ccm
from .policy import check_readonly

log = logging.getLogger("synergy_mcp.session")

_ADDR_RE = re.compile(r"\b\S+:\d+:\S+\b")

_STALE_SESSION_MARKERS = (
    "not a valid session",
    "no session",
    "session has been terminated",
    "cannot connect to",
    "ccm_addr",
)


class SessionError(RuntimeError):
    pass


class _Session:
    __slots__ = ("addr", "owned")

    def __init__(self, addr: str, owned: bool):
        self.addr = addr
        self.owned = owned


class SessionManager:
    def __init__(self, config: ServerConfig):
        self.config = config
        self._sessions: dict[str, _Session] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def _lock_for(self, name: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(name, threading.Lock())

    def _base_env(self, addr: str | None = None) -> dict[str, str]:
        env = dict(os.environ)
        if addr:
            env["CCM_ADDR"] = addr
        else:
            env.pop("CCM_ADDR", None)
        return env

    def _start(self, db: DatabaseConfig) -> _Session:
        attached = db.resolve_ccm_addr()
        if attached:
            log.info("Attaching to operator-provided session for '%s'", db.name)
            return _Session(attached, owned=False)

        argv: list[str] = ["start", *db.start_flags, "-d", db.database]
        if db.server_url:
            argv += ["-s", db.server_url]
        argv += ["-r", db.role, "-n", db.resolve_user(), "-pw", db.resolve_password()]

        log.info(
            "Starting session for '%s' (this can take minutes on a busy Synergy server; "
            "timeout=%ss)",
            db.name,
            self.config.start_timeout,
        )
        started = time.monotonic()
        result = run_ccm(
            self.config.ccm_binary,
            argv,
            env=self._base_env(),
            timeout=self.config.start_timeout,
            max_output_bytes=self.config.max_output_bytes,
        )

        for line in reversed(result.stdout.splitlines()):
            match = _ADDR_RE.search(line.strip())
            if match:
                addr = match.group(0)
                log.info(
                    "Started session for '%s' in %ss",
                    db.name,
                    round(time.monotonic() - started, 1),
                )
                return _Session(addr, owned=True)

        raise SessionError(
            f"Could not parse CCM_ADDR from `ccm start` output for '{db.name}'. "
            f"Output was: {result.stdout.strip()[:500]}"
        )

    def session_addr(self, db_name: str) -> str:
        db = self.config.get(db_name)
        with self._lock_for(db_name):
            session = self._sessions.get(db_name)
            if session is None:
                session = self._start(db)
                self._sessions[db_name] = session
            else:
                log.debug("Reusing session for '%s' (owned=%s)", db_name, session.owned)
            return session.addr

    def _drop(self, db_name: str) -> None:
        with self._guard:
            self._sessions.pop(db_name, None)

    def run(
        self,
        db_name: str,
        argv: list[str],
        *,
        check: bool = True,
        timeout: int | None = None,
    ) -> CcmResult:
        """Run an allowlisted read-only ccm command against a database session."""
        check_readonly(argv)
        self.config.get(db_name)
        log.debug("run: db=%s argv=%s timeout=%s", db_name, argv, timeout or self.config.command_timeout)

        for attempt in (1, 2):
            addr = self.session_addr(db_name)
            try:
                return run_ccm(
                    self.config.ccm_binary,
                    argv,
                    env=self._base_env(addr),
                    timeout=timeout or self.config.command_timeout,
                    max_output_bytes=self.config.max_output_bytes,
                    check=check,
                )
            except CcmError as exc:
                blob = f"{exc.result.stdout}\n{exc.result.stderr}".lower()
                if attempt == 1 and any(m in blob for m in _STALE_SESSION_MARKERS):
                    log.warning("Session for '%s' looks stale; restarting.", db_name)
                    self._drop(db_name)
                    continue
                raise

        raise SessionError(f"Unreachable retry state for '{db_name}'.")

    def health(self, db_name: str) -> dict:
        db = self.config.get(db_name)
        try:
            addr = self.session_addr(db_name)
        except Exception as exc:
            return {"database": db_name, "reachable": False, "error": str(exc)}

        result = run_ccm(
            self.config.ccm_binary,
            ["status"],
            env=self._base_env(addr),
            timeout=self.config.command_timeout,
            max_output_bytes=self.config.max_output_bytes,
            check=False,
        )
        owned = self._sessions[db_name].owned if db_name in self._sessions else False
        return {
            "database": db_name,
            "reachable": result.ok,
            "ccm_addr": addr,
            "session_owned_by_server": owned,
            "db_path": db.database,
            "role": db.role,
            "status_output": result.text.strip()[:4000],
        }

    def shutdown(self) -> None:
        for name, session in list(self._sessions.items()):
            if not session.owned:
                continue
            try:
                run_ccm(
                    self.config.ccm_binary,
                    ["stop"],
                    env=self._base_env(session.addr),
                    timeout=60,
                    check=False,
                )
                log.info("Stopped session for '%s'", name)
            except Exception:
                log.exception("Failed to stop session for '%s'", name)
        self._sessions.clear()
