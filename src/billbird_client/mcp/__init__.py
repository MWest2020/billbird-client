"""MCP server scoped to Billbird-only tools.

Spawn via the ``billbird-mcp`` console script (declared in
``pyproject.toml``). Stdio transport. Read-only contract.

Public surface:

- :data:`TOOLS` — fixed registry list.
- :func:`tool_names` — names in registry order (used by tests and docs).
- :func:`build_server` — construct an :class:`mcp.server.Server`.
- :func:`run_stdio` — block until parent closes stdin.
"""

from __future__ import annotations

from billbird_client.mcp.registry import TOOLS, find, tool_names
from billbird_client.mcp.server import build_server, run_stdio, run_stdio_from_cli

__all__ = [
    "TOOLS",
    "build_server",
    "find",
    "run_stdio",
    "run_stdio_from_cli",
    "tool_names",
]
