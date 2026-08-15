"""Subprocess layer for the ccm binary.

Every invocation goes through :func:`run_ccm` with an argv list. `shell=True` is
never used: Synergy query expressions are full of quotes and single-quotes, and
building shell strings from them would be a command-injection hole.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

_REDACT_AFTER = {"-pw", "-password"}


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
        super().__init__(
            f"ccm {' '.join(redact(result.argv))} failed (rc={result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
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
        raise RuntimeError(
            f"ccm binary '{binary}' not found on PATH. Set CCM_HOME/PATH or "
            f"settings.ccm_binary in inventory.yaml."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"ccm {' '.join(redact(argv))} timed out after {timeout}s."
        ) from exc

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
    if check and not result.ok:
        raise CcmError(result)
    return result
