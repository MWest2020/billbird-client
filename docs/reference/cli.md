---
status: draft
last_reviewed: 2026-07-13
---

# CLI reference

`billbird-cli` is a thin command-line over Billbird's REST API. Every subcommand maps to one route. Output is a rich table by default; pass `--json` for machine-readable output suitable for piping.

## Configuration

Two environment variables:

```bash
export BILLBIRD_API_URL=https://billbird.example.com
export BILLBIRD_API_TOKEN=bb_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Generate the token in Billbird's admin panel. The CLI exits with a clear error if either variable is missing.

## `billbird-cli hours`

Aggregate active log minutes for a period.

```
billbird-cli hours --period <PERIOD> --group-by <AXIS> [filters]
```

| Flag | Meaning |
|---|---|
| `--period` | `YYYY-MM`, `YYYY-MM-DD`, or `last-Nd`. UTC. |
| `--group-by` | `user`, `client`, `repo`, or `issue`. Default `user`. |
| `--repository` | `owner/name` filter. |
| `--client` | Client name (exact). |
| `--user` | GitHub username filter. |
| `--json` | Emit JSON instead of a table. |

Example:

```bash
billbird-cli hours --period last-30d --group-by client
billbird-cli hours --period 2026-05 --group-by user --repository org/repo
```

## `billbird-cli pva`

Plan-vs-actual per issue, ordered by absolute variance descending — issues most in need of attention lead.

```
billbird-cli pva [--period <PERIOD>] [--status <STATUS>] [--repository <OWNER/NAME>] [--json]
```

| Flag | Meaning |
|---|---|
| `--period` | Optional period; restricts which plans are considered active. |
| `--status` | Filter: `no_plan`, `under`, `on_target`, `over`. |
| `--repository` | `owner/name` filter. |

Example:

```bash
billbird-cli pva --status over                    # outliers only
billbird-cli pva --period 2026-05 --json | jq .   # pipe-friendly
```

## `billbird-cli recent`

Recent log + plan entries combined, type-tagged, newest first.

```
billbird-cli recent --since <ISO 8601> [--limit N] [--json]
```

Example:

```bash
billbird-cli recent --since 2026-05-20T00:00:00Z --limit 20
```

## `billbird-cli mcp`

Run the Billbird-MCP server over stdio. Equivalent to the standalone `billbird-mcp` console script (also installed by this package); the subcommand exists so a single CLI install gives both surfaces.

```bash
billbird-cli mcp     # blocks until stdin closes
```

See [`mcp.md`](mcp.md) for Claude Desktop configuration.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Generic error (unexpected) |
| 2 | Billbird not configured (missing env var) |
| 3 | Argument resolution failed (e.g. unknown `--client`) |
| 4 | Billbird returned an HTTP error |

`--json` always produces valid JSON on stdout when the command succeeds; errors go to stderr and are not JSON.
