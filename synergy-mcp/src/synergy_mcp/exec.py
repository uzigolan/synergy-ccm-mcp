"""Subprocess layer for the ccm binary.

Every invocation goes through :func:`run_ccm` with an argv list. `shell=True` is
never used: Synergy query expressions are full of quotes and single-quotes, and
building shell strings from them would be a command-injection hole.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from dataclasses import dataclass

log = logging.getLogger("synergy_mcp.exec")

_REDACT_AFTER = {"-pw", "-password"}

# ccm is routinely slow; anything past this is worth an operator-visible warning.
_SLOW_MS = int(os.environ.get("SYNERGY_MCP_SLOW_MS", "10000"))

# ccm often fails with a bare exit code and no output at all.
_RC_HINTS = {
    1: "general failure",
    4: "object or project not found, or not visible in this session",
    6: "query syntax error, or an attribute name that does not exist in this database",
}


@dataclass
class CcmResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str
    truncated: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def text(self) -> str:
        return self.stdout if self.stdout.strip() else self.stderr


class CcmError(RuntimeError):
    def __init__(self, result: CcmResult):
        self.result = result
        detail = result.stderr.strip() or result.stdout.strip()
        if not detail:
            hint = _RC_HINTS.get(result.returncode, "no diagnostic output")
            detail = f"ccm produced no output ({hint})"
        super().__init__(
            f"ccm {' '.join(redact(result.argv))} failed (rc={result.returncode}): {detail}"
        )


def redact(argv: list[str]) -> list[str]:
    """Mask credential values so they never reach logs or model context."""
    out: list[str] = []
    mask_next = False
    for arg in argv:
        if mask_next:
            out.append("****")
            mask_next = False
            continue
        out.append(arg)
        if arg.lower() in _REDACT_AFTER:
            mask_next = True
    return out


def run_ccm(
    binary: str,
    argv: list[str],
    *,
    env: dict[str, str],
    timeout: int,
    max_output_bytes: int = 200_000,
    check: bool = True,
) -> CcmResult:
    full = [binary, *argv]
    safe = " ".join(redact(argv))
    log.debug(
        "exec: ccm %s (timeout=%ss, ccm_addr=%s)", safe, timeout, env.get("CCM_ADDR", "<unset>")
    )
    started = time.monotonic()
    try:
        proc = subprocess.run(
            full,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except FileNotFoundError as exc:
        log.error("exec: ccm binary %r not found on PATH", binary)
        raise RuntimeError(
            f"ccm binary '{binary}' not found on PATH. Set CCM_HOME/PATH or "
            f"settings.ccm_binary in inventory.yaml."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        log.warning("exec: ccm %s timed out after %ss (%sms elapsed)", safe, timeout, elapsed_ms)
        raise RuntimeError(
            f"ccm {' '.join(redact(argv))} timed out after {timeout}s."
        ) from exc

    elapsed_ms = int((time.monotonic() - started) * 1000)
    stdout = proc.stdout or ""
    truncated = len(stdout) > max_output_bytes
    if truncated:
        stdout = stdout[:max_output_bytes] + "\n... [output truncated by synergy-mcp]"

    result = CcmResult(
        argv=argv,
        returncode=proc.returncode,
        stdout=stdout,
        stderr=proc.stderr or "",
        truncated=truncated,
    )
    log.debug(
        "exec: ccm %s -> rc=%s in %sms (stdout=%sB, stderr=%sB, truncated=%s)",
        safe,
        result.returncode,
        elapsed_ms,
        len(result.stdout),
        len(result.stderr),
        truncated,
    )
    if elapsed_ms >= _SLOW_MS:
        log.warning(
            "exec: SLOW ccm %s took %sms (rc=%s, timeout=%ss)", safe, elapsed_ms, result.returncode, timeout
        )
    if not result.ok:
        log.debug(
            "exec: ccm %s failure output: %s",
            safe,
            result.text.strip()[:2000] or f"<none> ({_RC_HINTS.get(result.returncode, 'unknown rc')})",
        )
    if check and not result.ok:
        raise CcmError(result)
    return result
