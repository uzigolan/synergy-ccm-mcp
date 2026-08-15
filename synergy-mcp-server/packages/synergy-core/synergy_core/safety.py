"""Manifest of safety-critical source paths.

Changes to any file listed here must be reviewed as a safety change, not a
refactor. CI (`scripts/flag_safety_paths.py`) flags PRs that touch them.
"""

from __future__ import annotations

SAFETY_CRITICAL_PATHS: tuple[str, ...] = (
    "synergy-mcp-server/packages/synergy-core/synergy_core/safety.py",
    "synergy-mcp-server/packages/synergy-core/synergy_core/boundary.py",
    "synergy-mcp-server/packages/synergy-core/synergy_core/audit.py",
    "synergy-mcp-server/packages/synergy-core/synergy_core/scope.py",
    "synergy-mcp-server/packages/synergy-core/synergy_core/drivers/base.py",
    "synergy-mcp-server/packages/synergy-core/synergy_core/drivers/ccm72.py",
    "synergy-mcp-server/packages/synergy-core/synergy_core/backends/ccm.py",
    "synergy-mcp-server/docs/ccm-contract.md",
)
