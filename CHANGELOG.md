# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows [Semantic Versioning](https://semver.org/) starting with the first tagged release.

## [Unreleased]

### Added

- `2026-05-21` — Initial release. Standalone Python client + CLI + MCP server for Billbird's REST API.
  - `BillbirdClient` HTTP wrapper around `/api/v1/*` with bearer-token auth, typed errors (`BillbirdNotConfigured`, `BillbirdHTTPError` with `auth` / `not_found` / `server` / `client` hints).
  - `billbird-cli` typer command set: `hours`, `pva` (plan-vs-actual), `recent`, `mcp`.
  - `billbird-mcp` stdio server exposing four read-only tools: `billbird_hours_summary`, `billbird_plan_vs_actual`, `billbird_recent_activity`, `billbird_cycle_time` (stub until Billbird ships the endpoint).
  - Period parser shared between CLI and MCP: `YYYY-MM`, `YYYY-MM-DD`, `last-Nd`.
  - Read-only contract: no writes anywhere. Slash commands in GitHub remain the only path to create or modify Billbird state.
  - Docs: `docs/cli.md`, `docs/mcp.md` (Claude Desktop snippet, tool list, read-only contract).
