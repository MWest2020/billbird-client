"""Billbird-only MCP tool implementations.

Four tools, each maps to one Billbird REST shape. Returns are
JSON-serialisable dicts; the period and scope are echoed back so
callers cannot drop context.

All Billbird-touching errors short-circuit with a structured envelope:

- ``billbird_not_configured`` with a ``missing: [...]`` list when env
  vars are absent.
- ``billbird_http_error`` with ``status`` / ``hint`` / ``body`` for any
  non-2xx response (auth, not-found, server, client).

Tools never raise; the MCP boundary expects a structured payload.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from billbird_client.client import (
    BillbirdClient,
    BillbirdHTTPError,
    BillbirdNotConfigured,
)
from billbird_client.periods import Period, parse_period

ERR_NOT_CONFIGURED = "billbird_not_configured"
ERR_HTTP = "billbird_http_error"
ERR_INVALID = "invalid_argument"


def _not_configured_response(exc: BillbirdNotConfigured) -> dict[str, Any]:
    return {
        "error": ERR_NOT_CONFIGURED,
        "missing": exc.missing,
        "docs": "https://github.com/MWest2020/billbird-client/blob/main/docs/mcp.md",
    }


def _http_error_response(exc: BillbirdHTTPError) -> dict[str, Any]:
    return {
        "error": ERR_HTTP,
        "status": exc.status,
        "hint": exc.hint,
        "body": exc.body,
    }


# --- Tools ---------------------------------------------------------


def billbird_hours_summary(
    period: str,
    group_by: str,
    repository: str | None = None,
    client: str | None = None,
    user: str | None = None,
) -> dict[str, Any]:
    """Aggregate active log minutes for a period, grouped by one axis."""
    if group_by not in {"user", "client", "repo", "issue"}:
        return {
            "error": ERR_INVALID,
            "field": "group_by",
            "hint": "must be one of 'user', 'client', 'repo', 'issue'",
        }
    try:
        p = parse_period(period)
    except ValueError as exc:
        return {"error": ERR_INVALID, "field": "period", "hint": str(exc)}

    try:
        with BillbirdClient.from_env() as bb:
            client_id = _resolve_client_id(bb, client) if client else None
            if client and client_id is None:
                return {
                    "error": "client_not_found",
                    "client": client,
                    "hint": "exact name match; check /api/v1/clients",
                }
            entries = bb.time_entries(
                repository=repository,
                username=user,
                client_id=client_id,
                date_from=_iso_to_date(p.from_iso),
                date_to=_iso_to_date(p.until_iso),
            )
            clients_lookup = (
                {c["id"]: c["name"] for c in bb.clients()}
                if group_by == "client"
                else {}
            )
    except BillbirdNotConfigured as exc:
        return _not_configured_response(exc)
    except BillbirdHTTPError as exc:
        return _http_error_response(exc)

    groups = _group_minutes(entries, group_by, clients_lookup)
    return {
        "unit": "minutes",
        "period": p.to_dict(),
        "scope": {
            "repository": repository,
            "client": client,
            "user": user,
            "group_by": group_by,
        },
        "groups": groups,
        "total_minutes": sum(g["minutes"] for g in groups),
        "entry_count": len(entries),
    }


def billbird_plan_vs_actual(
    period: str | None = None,
    status: str | None = None,
    repository: str | None = None,
    client: str | None = None,
) -> dict[str, Any]:
    """Per-issue plan-vs-actual variance, ordered by absolute drift."""
    p: Period | None = None
    if period:
        try:
            p = parse_period(period)
        except ValueError as exc:
            return {"error": ERR_INVALID, "field": "period", "hint": str(exc)}
    if status is not None and status not in {"no_plan", "under", "on_target", "over"}:
        return {
            "error": ERR_INVALID,
            "field": "status",
            "hint": "must be one of 'no_plan', 'under', 'on_target', 'over'",
        }

    try:
        with BillbirdClient.from_env() as bb:
            plans = bb.plans(
                repository=repository,
                status="active",
                since=_iso_to_date(p.from_iso) if p else None,
                until=_iso_to_date(p.until_iso) if p else None,
            )
            results: list[dict[str, Any]] = []
            for plan in plans:
                repo_full = plan.get("Repository") or plan.get("repository") or ""
                issue_num = plan.get("IssueNumber") or plan.get("issue_number")
                if not repo_full or issue_num is None:
                    continue
                owner, name = _split_repo(repo_full)
                pva = bb.plan_vs_actual(owner, name, issue_num)
                if status and pva.get("status") != status:
                    continue
                results.append(
                    {
                        "repository": pva.get("repository"),
                        "issue_number": pva.get("issue_number"),
                        "planned_minutes": pva.get("planned_minutes", 0),
                        "logged_minutes": pva.get("logged_minutes", 0),
                        "variance_minutes": pva.get("variance_minutes", 0),
                        "status": pva.get("status", "no_plan"),
                    }
                )
            results.sort(key=lambda r: abs(r["variance_minutes"]), reverse=True)
    except BillbirdNotConfigured as exc:
        return _not_configured_response(exc)
    except BillbirdHTTPError as exc:
        return _http_error_response(exc)

    return {
        "unit": "minutes",
        "period": p.to_dict() if p else None,
        "scope": {"repository": repository, "client": client, "status": status},
        "issues": results,
        "count": len(results),
    }


def billbird_recent_activity(since: str, limit: int = 50) -> dict[str, Any]:
    """Combined log + plan entries since a timestamp, type-tagged, newest first."""
    try:
        with BillbirdClient.from_env() as bb:
            since_date = since[:10] if len(since) >= 10 else since
            entries = bb.time_entries(date_from=since_date)
            plans = bb.plans(since=since_date)
    except BillbirdNotConfigured as exc:
        return _not_configured_response(exc)
    except BillbirdHTTPError as exc:
        return _http_error_response(exc)

    combined: list[dict[str, Any]] = []
    for e in entries:
        combined.append(_normalise_activity(e, "log"))
    for p in plans:
        combined.append(_normalise_activity(p, "plan"))
    combined.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return {
        "unit": "minutes",
        "since": since,
        "limit": limit,
        "entries": combined[:limit],
        "count": min(len(combined), limit),
    }


def billbird_cycle_time(
    period: str | None = None, repository: str | None = None
) -> dict[str, Any]:
    """Stub: Billbird's cycle-time REST endpoint is not yet exposed.

    The tool's shape is in place; flipping it to a real call is a
    one-line change once the endpoint lands.
    """
    _ = period, repository
    return {
        "error": "not_implemented",
        "hint": (
            "Billbird's cycle-time REST endpoint is not exposed yet. "
            "Once /api/v1/cycle-time lands, this tool will return per-issue "
            "and aggregate records."
        ),
    }


# --- Internal helpers ----------------------------------------------


def _normalise_activity(row: dict[str, Any], kind: str) -> dict[str, Any]:
    return {
        "type": kind,
        "id": row.get("ID") or row.get("id"),
        "created_at": row.get("CreatedAt") or row.get("created_at"),
        "repository": row.get("Repository") or row.get("repository"),
        "issue_number": row.get("IssueNumber") or row.get("issue_number"),
        "duration_minutes": row.get("DurationMinutes") or row.get("duration_minutes"),
        "github_username": row.get("GitHubUsername") or row.get("github_username"),
        "description": row.get("Description") or row.get("description"),
        "labels": row.get("labels") or [],
    }


def _split_repo(spec: str) -> tuple[str, str]:
    owner, _, name = spec.partition("/")
    if not owner or not name:
        raise ValueError(f"invalid repository spec {spec!r}; expected owner/repo")
    return owner, name


def _iso_to_date(iso: str | None) -> str:
    return iso[:10] if iso else ""


def _resolve_client_id(bb: BillbirdClient, name: str) -> int | None:
    for c in bb.clients():
        if c.get("name") == name:
            return c.get("id")
    return None


def _group_minutes(
    entries: Iterable[dict[str, Any]],
    group_by: str,
    clients_lookup: dict[int, str],
) -> list[dict[str, Any]]:
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
    rows = [
        {"group": k, "minutes": totals[k], "entries": counts[k]} for k in totals
    ]
    rows.sort(key=lambda r: r["minutes"], reverse=True)
    return rows
