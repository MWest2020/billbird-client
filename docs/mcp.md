# MCP server

`billbird-mcp` is a Model Context Protocol server that exposes four read-only tools backed by Billbird's REST API. It runs over stdio so AI clients (Claude Desktop and similar) can spawn it as a child process.

## Required environment

| Variable | Description |
|---|---|
| `BILLBIRD_API_URL` | Base URL of your Billbird instance, e.g. `https://billbird.example.com` |
| `BILLBIRD_API_TOKEN` | Bearer token issued from Billbird's admin panel |

The server starts even without these set. Tools that need Billbird return a structured `billbird_not_configured` error when called; you'll see the missing variable name in the response.

## Configuring Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%/Claude/claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "billbird": {
      "command": "billbird-mcp",
      "env": {
        "BILLBIRD_API_URL": "https://billbird.example.com",
        "BILLBIRD_API_TOKEN": "bb_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

If you installed via `uv tool install billbird-client`, the binary is on PATH. Otherwise replace `"command"` with the absolute path to the `billbird-mcp` shipped by `pip` / `uv`.

Restart Claude Desktop. The four tools below appear under the server's name.

## Available tools

Four tools, registered in this fixed order:

| Tool | What it returns |
|---|---|
| `billbird_hours_summary` | Aggregate active log minutes for a period, grouped by user / client / repo / issue. |
| `billbird_plan_vs_actual` | Per-issue variance between active plan and active logs, ordered by absolute variance descending. |
| `billbird_recent_activity` | Recent log + plan entries combined, type-tagged, newest first. |
| `billbird_cycle_time` | Stub: returns `not_implemented` until Billbird exposes the cycle-time REST endpoint. |

Every numeric field carries an explicit `unit` (`minutes`, `count`); responses echo back the resolved `period` and `scope` so the AI client cannot drop context when re-presenting numbers.

## Read-only contract

No tool writes. Logging time, planning, correcting, deleting, and revoking tokens all stay on their canonical paths (GitHub slash commands and Billbird's own admin panel). This is an intentional limitation:

- AI surfaces increase blast radius for mistakes. Reads are recoverable; writes are not.
- Every Billbird write today traces back to a specific GitHub comment. Writing through MCP would break that audit invariant.

## Smoke-test the round-trip

Once installed and configured:

```bash
BILLBIRD_API_URL=https://billbird.example.com \
BILLBIRD_API_TOKEN=bb_xxxxx \
    billbird-mcp <<< '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"1.0"}}}'
```

(One-shot; the server expects a follow-up `notifications/initialized` and then your `tools/list` or `tools/call` calls. For interactive use, attach via Claude Desktop.)

## Error envelopes

Every Billbird-touching tool returns a structured error on the bad paths:

```json
{"error": "billbird_not_configured", "missing": ["BILLBIRD_API_URL"], "docs": "..."}
{"error": "billbird_http_error", "status": 401, "hint": "auth", "body": {...}}
{"error": "invalid_argument", "field": "period", "hint": "..."}
```

The `hint` on HTTP errors is one of `auth`, `not_found`, `server`, or `client`, so an AI client can classify without re-parsing the status code.

## Security

`BILLBIRD_API_TOKEN` grants the same read access through the API that the issuing user has through the admin panel. Treat it like a password:

- Store outside the repository, do not commit it.
- Revoke from Billbird's admin panel when it is no longer needed.
- Run `billbird-mcp` as the user's own account, not a shared service account, so revoking that user revokes their token's effect.
