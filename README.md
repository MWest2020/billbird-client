# billbird-client

Python client, CLI, and MCP server for [Billbird](https://github.com/MWest2020/Billbird)'s REST API.

Standalone. No Gitsweeper, no opinion about analytics — just a focused tool for reading time-tracking data out of one Billbird instance over its bearer-token API.

## Install

```bash
uv add billbird-client     # in a uv-managed project
# or
pip install billbird-client
```

## Configure

```bash
export BILLBIRD_API_URL=https://billbird.example.com
export BILLBIRD_API_TOKEN=bb_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Generate the token in Billbird's admin panel under **API tokens**. See [Billbird's docs](https://github.com/MWest2020/Billbird/blob/main/docs/api-tokens.md) for the lifecycle.

## CLI

```bash
billbird-cli hours --period last-7d --group-by user
billbird-cli hours --period 2026-05 --group-by client
billbird-cli pva --status over                       # plan-vs-actual outliers
billbird-cli recent --since 2026-05-20T00:00:00Z
```

Every command takes `--json` for machine-readable output. See [`docs/cli.md`](docs/cli.md) for the full reference.

## MCP server

For AI clients (Claude Desktop and similar):

```bash
billbird-mcp
```

The server speaks JSON-RPC over stdio. Tools exposed:

- `billbird_hours_summary(period, group_by, repo?, client?, user?)`
- `billbird_plan_vs_actual(period?, status?, repo?, client?)`
- `billbird_recent_activity(since, limit?)`
- `billbird_cycle_time(period?, repo?)` — stub until Billbird exposes the endpoint

See [`docs/mcp.md`](docs/mcp.md) for Claude Desktop configuration and the read-only contract.

## Library

For programmatic use:

```python
from billbird_client import BillbirdClient

with BillbirdClient.from_env() as client:
    entries = client.time_entries(repository="org/repo")
    plans = client.plans(status="active")
    pva = client.plan_vs_actual("org", "repo", 42)
```

## Scope

This package is **read-only**. Writes happen in GitHub via slash commands (`/log`, `/plan`, etc.) and land in Billbird through its webhook. There is no `billbird-cli log 2h` — that would be a separate command path with separate security implications, and slash commands already work everywhere `gh` works.

This package has **no dependency** on [Gitsweeper](https://github.com/MWest2020/Gitsweeper). Gitsweeper may consume this package for cross-source analytics (e.g. reconciling commit `Time:` footers against `/log` entries), but Billbird and billbird-client work fine without it.

## License

[MIT](LICENSE).
