"""synergy-mcp package."""

__all__ = ["mcp", "run"]


def __getattr__(name: str):
    if name in __all__:
        from .server import mcp, run

        return {"mcp": mcp, "run": run}[name]
    raise AttributeError(name)
