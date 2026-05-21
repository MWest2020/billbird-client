"""Unit tests for the BillbirdClient HTTP wrapper.

Uses pytest-httpx to mock Billbird's REST API. Verifies:

- env-driven construction fails loud with a named missing variable
- bearer header lands on the request
- typed errors classify status codes correctly
- query-param scrubbing (None values dropped, lists serialise repeated)
"""

from __future__ import annotations

import re

import pytest

from billbird_client import (
    BillbirdClient,
    BillbirdHTTPError,
    BillbirdNotConfigured,
)

BASE = "https://billbird.test"


def _client(http=None) -> BillbirdClient:
    return BillbirdClient(BASE, "bb_test", http_client=http)


def test_from_env_raises_when_missing(monkeypatch):
    monkeypatch.delenv("BILLBIRD_API_URL", raising=False)
    monkeypatch.delenv("BILLBIRD_API_TOKEN", raising=False)
    with pytest.raises(BillbirdNotConfigured) as info:
        BillbirdClient.from_env()
    assert set(info.value.missing) == {"BILLBIRD_API_URL", "BILLBIRD_API_TOKEN"}


def test_from_env_partial_missing_names_only_that_var(monkeypatch):
    monkeypatch.setenv("BILLBIRD_API_URL", BASE)
    monkeypatch.delenv("BILLBIRD_API_TOKEN", raising=False)
    with pytest.raises(BillbirdNotConfigured) as info:
        BillbirdClient.from_env()
    assert info.value.missing == ["BILLBIRD_API_TOKEN"]


def test_authorization_header_set(httpx_mock):
    httpx_mock.add_response(json=[])
    with BillbirdClient(BASE, "bb_xyz") as bb:
        bb.clients()
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert requests[0].headers["Authorization"] == "Bearer bb_xyz"


def test_time_entries_happy_path(httpx_mock):
    httpx_mock.add_response(
        url=f"{BASE}/api/v1/time-entries",
        json=[{"ID": 1, "DurationMinutes": 60}],
    )
    with _client() as bb:
        entries = bb.time_entries()
    assert entries == [{"ID": 1, "DurationMinutes": 60}]


def test_time_entries_drops_none_params(httpx_mock):
    httpx_mock.add_response(json=[])
    with _client() as bb:
        bb.time_entries(repository="org/repo", username=None, client_id=None)
    query = httpx_mock.get_requests()[0].url.query.decode()
    assert "username=None" not in query
    assert "client_id=None" not in query
    assert "repo=org" in query


def test_time_entries_serialises_labels_as_repeated_param(httpx_mock):
    httpx_mock.add_response(json=[])
    with _client() as bb:
        bb.time_entries(labels=["wbso:speur", "type:development"])
    query = httpx_mock.get_requests()[0].url.query.decode()
    # httpx encodes a list as repeated keys; either order is acceptable.
    assert query.count("label=") == 2
    assert "wbso" in query and "type" in query


def test_label_prefix_param(httpx_mock):
    httpx_mock.add_response(json=[])
    with _client() as bb:
        bb.time_entries(label_prefix="wbso:")
    query = httpx_mock.get_requests()[0].url.query.decode()
    assert "label_prefix=wbso" in query


@pytest.mark.parametrize(
    "status,want_hint",
    [
        (401, "auth"),
        (403, "auth"),
        (404, "not_found"),
        (500, "server"),
        (503, "server"),
        (400, "client"),
    ],
)
def test_http_error_classification(httpx_mock, status, want_hint):
    httpx_mock.add_response(
        url=re.compile(r".*"),
        status_code=status,
        json={"error": "x"},
    )
    with _client() as bb, pytest.raises(BillbirdHTTPError) as info:
        bb.plans()
    assert info.value.status == status
    assert info.value.hint == want_hint


def test_plan_vs_actual_path(httpx_mock):
    httpx_mock.add_response(
        url=f"{BASE}/api/v1/issues/org/repo/42/plan-vs-actual",
        json={
            "repository": "org/repo",
            "issue_number": 42,
            "planned_minutes": 480,
            "logged_minutes": 360,
            "variance_minutes": -120,
            "status": "under",
        },
    )
    with _client() as bb:
        result = bb.plan_vs_actual("org", "repo", 42)
    assert result["status"] == "under"
    assert result["variance_minutes"] == -120
