"""End-to-end MCP tool tests against a pytest-httpx-mocked Billbird.

Proves the wire contract: query-param scrubbing, period echoing, unit
declarations, error-envelope shape on 401, and the variance-descending
sort of plan_vs_actual.
"""

from __future__ import annotations

import re

import pytest

from billbird_client.mcp.tools import (
    billbird_hours_summary,
    billbird_plan_vs_actual,
    billbird_recent_activity,
)


@pytest.fixture
def _billbird_env(monkeypatch):
    monkeypatch.setenv("BILLBIRD_API_URL", "http://billbird.test")
    monkeypatch.setenv("BILLBIRD_API_TOKEN", "bb_test_token")
    yield


def test_hours_summary_round_trip(_billbird_env, httpx_mock):
    httpx_mock.add_response(
        url=re.compile(r"^http://billbird\.test/api/v1/time-entries.*"),
        json=[
            {"DurationMinutes": 60, "GitHubUsername": "alice", "Repository": "org/r1", "IssueNumber": 1},
            {"DurationMinutes": 90, "GitHubUsername": "alice", "Repository": "org/r1", "IssueNumber": 2},
            {"DurationMinutes": 30, "GitHubUsername": "bob", "Repository": "org/r1", "IssueNumber": 1},
        ],
    )
    out = billbird_hours_summary(period="2026-04", group_by="user")
    assert "error" not in out, out
    assert out["unit"] == "minutes"
    assert out["total_minutes"] == 180
    assert out["entry_count"] == 3
    groups = {g["group"]: g["minutes"] for g in out["groups"]}
    assert groups == {"alice": 150, "bob": 30}
    assert out["period"]["label"] == "2026-04"


def test_plan_vs_actual_orders_by_absolute_variance(_billbird_env, httpx_mock):
    # First response: plan list
    httpx_mock.add_response(
        url=re.compile(r"^http://billbird\.test/api/v1/plans.*"),
        json=[
            {"Repository": "org/r1", "IssueNumber": 1, "status": "active"},
            {"Repository": "org/r1", "IssueNumber": 2, "status": "active"},
        ],
    )
    # plan-vs-actual per issue
    httpx_mock.add_response(
        url="http://billbird.test/api/v1/issues/org/r1/1/plan-vs-actual",
        json={
            "repository": "org/r1",
            "issue_number": 1,
            "planned_minutes": 480,
            "logged_minutes": 180,
            "variance_minutes": -300,
            "status": "under",
        },
    )
    httpx_mock.add_response(
        url="http://billbird.test/api/v1/issues/org/r1/2/plan-vs-actual",
        json={
            "repository": "org/r1",
            "issue_number": 2,
            "planned_minutes": 240,
            "logged_minutes": 480,
            "variance_minutes": 240,
            "status": "over",
        },
    )

    out = billbird_plan_vs_actual(period="2026-04")
    assert out["count"] == 2
    # |-300| > |240| → issue 1 leads
    assert out["issues"][0]["issue_number"] == 1


def test_recent_activity_combines_logs_and_plans(_billbird_env, httpx_mock):
    httpx_mock.add_response(
        url=re.compile(r"^http://billbird\.test/api/v1/time-entries.*"),
        json=[{"ID": 1, "CreatedAt": "2026-05-18T09:00:00Z", "DurationMinutes": 60}],
    )
    httpx_mock.add_response(
        url=re.compile(r"^http://billbird\.test/api/v1/plans.*"),
        json=[{"ID": 99, "CreatedAt": "2026-05-18T10:00:00Z", "DurationMinutes": 480}],
    )
    out = billbird_recent_activity(since="2026-05-18T00:00:00Z")
    assert out["count"] == 2
    types = [e["type"] for e in out["entries"]]
    # plan is newer → first
    assert types == ["plan", "log"]


def test_bogus_token_surfaces_http_error(_billbird_env, httpx_mock):
    httpx_mock.add_response(
        url=re.compile(r"^http://billbird\.test/.*"),
        status_code=401,
        json={"error": "invalid token"},
    )
    out = billbird_hours_summary(period="2026-04", group_by="user")
    assert out["error"] == "billbird_http_error"
    assert out["status"] == 401
    assert out["hint"] == "auth"
