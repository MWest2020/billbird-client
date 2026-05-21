"""Typer CLI for billbird-client.

Subcommands map one-to-one onto Billbird REST routes:

- ``billbird-cli hours --period last-7d --group-by user``
- ``billbird-cli pva --status over``
- ``billbird-cli recent --since 2026-05-20T00:00:00Z``
- ``billbird-cli mcp`` — start the MCP server over stdio

Every command supports ``--json`` for machine-readable output. The
default is a rich table so the human use case stays ergonomic.
"""

from __future__ import annotations

import json
import sys

import typer
from rich.console import Console
from rich.table import Table

from billbird_client.client import (
    BillbirdClient,
    BillbirdHTTPError,
    BillbirdNotConfigured,
)
from billbird_client.periods import parse_period

app = typer.Typer(
    name="billbird-cli",
    help="Read-only client for Billbird's REST API.",
    no_args_is_help=True,
    add_completion=False,
)


def _open_client() -> BillbirdClient:
    """Build the client from env or exit cleanly with a named error."""
    try:
        return BillbirdClient.from_env()
    except BillbirdNotConfigured as exc:
        typer.echo(
            "Billbird is not configured: missing " + ", ".join(exc.missing),
            err=True,
        )
        typer.echo(
            "Set BILLBIRD_API_URL and BILLBIRD_API_TOKEN. See the README for details.",
            err=True,
        )
        raise typer.Exit(code=2) from exc


def _print_json(payload: object) -> None:
    json.dump(payload, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


@app.command()
def hours(
    period: str = typer.Option(
        ...,
        "--period",
        help="Period: YYYY-MM, YYYY-MM-DD, or last-Nd (UTC).",
    ),
    group_by: str = typer.Option(
        "user",
        "--group-by",
        help="Aggregation axis: user / client / repo / issue.",
    ),
    repository: str | None = typer.Option(
        None, "--repository", help="Optional owner/name filter"
    ),
    client: str | None = typer.Option(
        None, "--client", help="Optional client name (exact match)"
    ),
    user: str | None = typer.Option(
        None, "--user", help="Optional GitHub username filter"
    ),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table"),
) -> None:
    """Aggregate active log minutes by user / client / repo / issue."""
    if group_by not in {"user", "client", "repo", "issue"}:
        raise typer.BadParameter("--group-by must be one of user, client, repo, issue")
    try:
        p = parse_period(period)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    bb = _open_client()
    try:
        client_id: int | None = None
        if client:
            clients_lookup = {c.get("name"): c.get("id") for c in bb.clients()}
            client_id = clients_lookup.get(client)
            if client_id is None:
                typer.echo(f"client {client!r} not found", err=True)
                raise typer.Exit(code=3)
        entries = bb.time_entries(
            repository=repository,
            username=user,
            client_id=client_id,
            date_from=p.from_iso[:10],
            date_to=p.until_iso[:10],
        )
        clients_for_groupby = (
            {c["id"]: c["name"] for c in bb.clients()} if group_by == "client" else {}
        )
    except BillbirdHTTPError as exc:
        typer.echo(f"Billbird HTTP {exc.status} ({exc.hint}): {exc.body}", err=True)
        raise typer.Exit(code=4) from exc
    finally:
        bb.close()

    groups = _group_minutes(entries, group_by, clients_for_groupby)
    total = sum(g["minutes"] for g in groups)

    if json_out:
        _print_json(
            {
                "unit": "minutes",
                "period": p.to_dict(),
                "scope": {
                    "repository": repository,
                    "client": client,
                    "user": user,
                    "group_by": group_by,
                },
                "groups": groups,
                "total_minutes": total,
                "entry_count": len(entries),
            }
        )
        return

    console = Console()
    table = Table(
        title=f"hours by {group_by} · {p.label} · total {_fmt_hm(total)} ({len(entries)} entries)"
    )
    table.add_column(group_by)
    table.add_column("minutes", justify="right")
    table.add_column("hours", justify="right")
    table.add_column("entries", justify="right")
    for g in groups:
        table.add_row(
            g["group"],
            str(g["minutes"]),
            _fmt_hm(g["minutes"]),
            str(g["entries"]),
        )
    console.print(table)


@app.command()
def pva(
    period: str | None = typer.Option(None, "--period", help="Optional period filter"),
    status: str | None = typer.Option(
        None,
        "--status",
        help="Optional filter: no_plan / under / on_target / over",
    ),
    repository: str | None = typer.Option(None, "--repository", help="owner/name filter"),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table"),
) -> None:
    """Plan-vs-actual per issue, ordered by absolute variance descending."""
    if status is not None and status not in {"no_plan", "under", "on_target", "over"}:
        raise typer.BadParameter(
            "--status must be one of no_plan, under, on_target, over"
        )
    p = None
    if period:
        try:
            p = parse_period(period)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc

    bb = _open_client()
    try:
        plans = bb.plans(
            repository=repository,
            status="active",
            since=p.from_iso[:10] if p else None,
            until=p.until_iso[:10] if p else None,
        )
        rows: list[dict[str, object]] = []
        for plan in plans:
            repo_full = plan.get("Repository") or plan.get("repository") or ""
            issue_num = plan.get("IssueNumber") or plan.get("issue_number")
            if not repo_full or issue_num is None:
                continue
            owner, name = repo_full.split("/", 1)
            agg = bb.plan_vs_actual(owner, name, issue_num)
            if status and agg.get("status") != status:
                continue
            rows.append(agg)
        rows.sort(key=lambda r: abs(r.get("variance_minutes", 0)), reverse=True)
    except BillbirdHTTPError as exc:
        typer.echo(f"Billbird HTTP {exc.status} ({exc.hint}): {exc.body}", err=True)
        raise typer.Exit(code=4) from exc
    finally:
        bb.close()

    if json_out:
        _print_json(
            {
                "unit": "minutes",
                "period": p.to_dict() if p else None,
                "scope": {"repository": repository, "status": status},
                "issues": rows,
                "count": len(rows),
            }
        )
        return

    console = Console()
    table = Table(title=f"plan vs actual{' · ' + p.label if p else ''} · {len(rows)} issue(s)")
    table.add_column("repo")
    table.add_column("issue", justify="right")
    table.add_column("planned", justify="right")
    table.add_column("logged", justify="right")
    table.add_column("variance", justify="right")
    table.add_column("status")
    for r in rows:
        table.add_row(
            str(r.get("repository", "")),
            f"#{r.get('issue_number', '?')}",
            _fmt_hm(r.get("planned_minutes", 0)),
            _fmt_hm(r.get("logged_minutes", 0)),
            _fmt_signed(r.get("variance_minutes", 0)),
            str(r.get("status", "")),
        )
    console.print(table)


@app.command()
def recent(
    since: str = typer.Option(..., "--since", help="ISO 8601 UTC lower bound"),
    limit: int = typer.Option(50, "--limit", help="Max rows. Default 50."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table"),
) -> None:
    """Recent log + plan entries (combined, newest first)."""
    bb = _open_client()
    try:
        since_date = since[:10]
        entries = bb.time_entries(date_from=since_date)
        plans = bb.plans(since=since_date)
    except BillbirdHTTPError as exc:
        typer.echo(f"Billbird HTTP {exc.status} ({exc.hint}): {exc.body}", err=True)
        raise typer.Exit(code=4) from exc
    finally:
        bb.close()

    def _norm(row: dict[str, object], kind: str) -> dict[str, object]:
        return {
            "type": kind,
            "id": row.get("ID") or row.get("id"),
            "created_at": row.get("CreatedAt") or row.get("created_at"),
            "repository": row.get("Repository") or row.get("repository"),
            "issue_number": row.get("IssueNumber") or row.get("issue_number"),
            "duration_minutes": row.get("DurationMinutes") or row.get("duration_minutes"),
            "github_username": row.get("GitHubUsername") or row.get("github_username"),
            "description": row.get("Description") or row.get("description"),
        }

    combined = [_norm(e, "log") for e in entries] + [_norm(p, "plan") for p in plans]
    combined.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    combined = combined[:limit]

    if json_out:
        _print_json(
            {
                "since": since,
                "limit": limit,
                "entries": combined,
                "count": len(combined),
            }
        )
        return

    console = Console()
    table = Table(title=f"recent activity since {since} · {len(combined)} row(s)")
    table.add_column("when")
    table.add_column("type")
    table.add_column("who")
    table.add_column("repo / issue")
    table.add_column("minutes", justify="right")
    table.add_column("note")
    for r in combined:
        table.add_row(
            (r.get("created_at") or "")[:19],
            str(r.get("type", "")),
            str(r.get("github_username", "")),
            f"{r.get('repository', '')}#{r.get('issue_number', '?')}",
            str(r.get("duration_minutes", "")),
            str(r.get("description") or ""),
        )
    console.print(table)


@app.command()
def mcp() -> None:
    """Run the Billbird-MCP server over stdio.

    Equivalent to the standalone ``billbird-mcp`` console script;
    available here as well so a single CLI install gives both surfaces.
    Blocks until stdin closes.
    """
    try:
        from billbird_client.mcp import run_stdio
    except ImportError as exc:
        typer.echo(f"MCP support requires the 'mcp' package: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    run_stdio()


# --- helpers -------------------------------------------------------


def _group_minutes(
    entries: list[dict[str, object]],
    group_by: str,
    clients_lookup: dict[int, str],
) -> list[dict[str, object]]:
    from collections import defaultdict

    totals: dict[str, int] = defaultdict(int)
    counts: dict[str, int] = defaultdict(int)
    for e in entries:
        if group_by == "user":
            key = e.get("GitHubUsername") or e.get("github_username") or "unknown"
        elif group_by == "client":
            cid = e.get("ClientID") or e.get("client_id")
            key = clients_lookup.get(cid, "(no client)") if cid else "(no client)"
        elif group_by == "repo":
            key = e.get("Repository") or e.get("repository") or "unknown"
        elif group_by == "issue":
            repo = e.get("Repository") or e.get("repository") or "unknown"
            issue = e.get("IssueNumber") or e.get("issue_number")
            key = f"{repo}#{issue}"
        else:
            key = "unknown"
        minutes = e.get("DurationMinutes") or e.get("duration_minutes") or 0
        totals[key] += minutes
        counts[key] += 1
    rows = [{"group": k, "minutes": totals[k], "entries": counts[k]} for k in totals]
    rows.sort(key=lambda r: r["minutes"], reverse=True)
    return rows


def _fmt_hm(minutes: int) -> str:
    if minutes >= 60:
        h, m = divmod(minutes, 60)
        return f"{h}h{m}m" if m else f"{h}h"
    return f"{minutes}m"


def _fmt_signed(minutes: int) -> str:
    if minutes == 0:
        return "0m"
    return ("+" if minutes > 0 else "-") + _fmt_hm(abs(minutes))


def main() -> None:  # pragma: no cover - thin wrapper for entrypoint scripts
    app()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app() or 0)
