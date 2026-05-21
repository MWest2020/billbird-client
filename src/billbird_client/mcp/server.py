"""MCP server wiring (stdio transport).

The ``billbird-mcp`` console script (declared in ``pyproject.toml``)
points at :func:`run_stdio_from_cli`. AI clients (Claude Desktop and
similar) spawn it as a child process.
"""

from __future__ import annotations

import json
from typing import Any

from billbird_client.mcp.registry import TOOLS, find


def build_server():
    """Construct the underlying MCP Server with every tool registered.

    Imported lazily so the rest of the package (and the test suite)
    work without forcing an import of the ``mcp`` SDK at top level.
    """
    from mcp.server import Server
    from mcp.types import TextContent, Tool

    server: Server = Server("billbird-mcp")

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return [
            Tool(
                name=spec.name,
                description=spec.description,
                inputSchema=spec.input_schema,
            )
            for spec in TOOLS
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        spec = find(name)
        if spec is None:
            payload = {"error": "unknown_tool", "name": name}
        else:
            try:
                payload = spec.handler(**(arguments or {}))
            except TypeError as exc:
                payload = {"error": "invalid_argument", "hint": str(exc)}
            except Exception as exc:  # pragma: no cover - defensive
                payload = {"error": "internal_error", "hint": repr(exc)}
        return [TextContent(type="text", text=json.dumps(payload, default=str))]

    return server


def run_stdio() -> None:
    """Run the MCP server over stdio until stdin closes. Blocking."""
    import asyncio

    from mcp.server.stdio import stdio_server

    async def _main() -> None:
        server = build_server()
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(_main())


def run_stdio_from_cli() -> None:
    """Entrypoint suitable for ``[project.scripts] billbird-mcp``.

    Currently the same as :func:`run_stdio`; the indirection exists so
    we can add startup-logging or env-var sanity checks here without
    touching the consumers of :func:`run_stdio`.
    """
    run_stdio()
