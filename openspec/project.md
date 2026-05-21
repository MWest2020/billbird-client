# billbird-client

A standalone Python package — client library, CLI, and MCP server — for reading data from [Billbird](https://github.com/MWest2020/Billbird)'s REST API. One Billbird endpoint per install; one bearer token; no opinion about analytics.

**Scale of ambition:**

- v1: bearer-token client, four MCP tools (hours, plan-vs-actual, recent activity, cycle-time stub), CLI with the same four operations plus an `mcp` subcommand.
- horizon: stay focused on Billbird reads. Writes never happen here. Cross-source analytics live in [Gitsweeper](https://github.com/MWest2020/Gitsweeper), not here.

## Stack

- **Language:** Python 3.11+
- **Tooling:** [uv](https://docs.astral.sh/uv/) for environments, dependencies, and script execution. Never call `pip` directly.
- **HTTP client:** `httpx` (synchronous).
- **CLI:** `typer` + `rich`.
- **MCP:** the official `mcp` SDK over stdio.
- **Tests / lint:** `pytest`, `pytest-httpx`, `ruff`.
- **Licence:** MIT.

## Conventions

- **Read-only.** No write tool, ever. Slash commands in GitHub remain the only path to create or modify Billbird state.
- **Boring & auditable wins.** No clever abstractions; the entire `BillbirdClient` is one file. Adding a method = adding a route mapping plus one test.
- **uv-only.** All Python tooling commands go through `uv` (`uv run`, `uv add`, `uv sync`). Lockfile is part of the audit trail.
- **No hard dependency on Gitsweeper.** This package does not import Gitsweeper, does not assume Gitsweeper, does not reference Gitsweeper in code. Gitsweeper may consume *this* package, but never the other way around.
- **Single endpoint per install.** This is the deployment model that mirrors Billbird's "one instance per organisation": configure one `BILLBIRD_API_URL` per `billbird-client` install.
- **Structured error envelopes.** Tools never raise across the MCP boundary; they return `{"error": "...", ...}` payloads so the AI client can present the failure mode to the user.
- **CHANGELOG.md is non-negotiable.** Every session that changes observable state gets a dated entry.

## Repository layout

```
billbird-client/
  src/billbird_client/
    __init__.py        — public surface
    client.py          — BillbirdClient + typed errors
    periods.py         — period parser shared by CLI and MCP
    cli.py             — typer entry: hours / pva / recent / mcp
    mcp/
      __init__.py
      registry.py      — fixed TOOLS list
      tools.py         — four tool implementations
      server.py        — stdio server wiring
  tests/               — unit + e2e-with-mock-Billbird
  docs/
    cli.md             — CLI reference
    mcp.md             — MCP setup + tool list + Claude Desktop config
  openspec/            — specs + changes (this directory)
  CHANGELOG.md
  README.md
  pyproject.toml       — uv-managed
```

## Architecture decisions

These are the non-trivial choices that shape v1. They live here rather than in a per-change `design.md` because there is no change yet — this is the greenfield baseline.

### Read-only surface, no exceptions

Slash commands in GitHub (`/log`, `/plan`, `/correct`, `/delete`, `/unplan`) are the *only* way to write to Billbird. Every write traces back to a specific GitHub comment, which is the audit invariant Billbird's design relies on. A `billbird-cli log 2h` command would either bypass the audit trail (bad) or post a slash-comment via `gh` (just a thin shell wrapper). Either way, not interesting enough to ship here.

### One endpoint per install

The package reads exactly one Billbird URL from `BILLBIRD_API_URL`. Multi-endpoint support is excluded: in practice each Billbird instance belongs to one organisation, and an operator who needs to query two organisations runs the CLI twice with different env vars. Adding `--profile` / `--endpoint` would invite questions about config-file precedence that aren't worth answering yet.

### Bearer-only auth

Cookie auth exists in Billbird for the admin panel, but `billbird-client` is for non-browser callers. Adding cookie support would mean shipping an OAuth flow in a CLI process, which has its own credential-storage problems. Bearer tokens are the right tool here.

### Period strings, not date pairs

The CLI and the MCP both accept a single `period` argument (`2026-04`, `last-7d`, `2026-04-15`) rather than separate `--from` and `--until`. Users speak in periods, not in pairs of dates. The parser is centralised in `periods.py` and returns a `Period` carrying the resolved start and end timestamps; the response payload echoes those back so consumers see exactly what was counted.

### MCP transport: stdio only

No HTTP transport for MCP. stdio matches how Claude Desktop and similar AI clients spawn MCP servers (one child process per session). HTTP transport adds auth-surface and port-binding concerns that no current caller asks for; an HTTP variant can be added later behind the same tool registry without changing the registry shape.

### Errors are envelopes, never exceptions, at the MCP boundary

Every Billbird-touching tool catches `BillbirdNotConfigured` and `BillbirdHTTPError` and turns them into `{"error": "...", ...}` payloads. The MCP `call_tool` handler also catches `TypeError` (bad arguments) and `Exception` (defensive). The AI client always gets JSON; the user always sees an articulable reason for the failure.

### No write-through cache

Each MCP / CLI invocation hits Billbird live. Caching invites staleness questions (what TTL? per-tool or global? invalidation triggers?) for a marginal speedup. Billbird's `/api/v1/*` is fast; if it ever isn't, that's a Billbird-side problem to fix, not a client-side workaround.

## Out of scope for v1

Explicit non-goals, listed so they do not creep in:

- Write operations of any shape.
- Multiple simultaneous Billbird endpoints.
- A persistent local cache.
- HTML / dashboard rendering. (Use Billbird's admin panel.)
- Cross-source analytics. (Use Gitsweeper.)
- Cycle-time aggregation — stubbed until Billbird exposes the REST endpoint.
- A "service-account" tier of API token. Tokens are user-scoped per Billbird's design.
