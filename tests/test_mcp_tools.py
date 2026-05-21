"""Tests for the MCP tool implementations + registry.

Covers the registry shape (size, ordering, schema validity, no
mutation tools) and the error envelopes when Billbird env vars are
absent. Live HTTP paths are covered in test_mcp_against_fake_billbird.
"""

from __future__ import annotations

import pytest

from billbird_client.mcp import TOOLS, find, tool_names
from billbird_client.mcp.tools import (
    billbird_cycle_time,
    billbird_hours_summary,
    billbird_plan_vs_actual,
    billbird_recent_activity,
)


@pytest.fixture(autouse=True)
def clear_billbird_env(monkeypatch):
    monkeypatch.delenv("BILLBIRD_API_URL", raising=False)
    monkeypatch.delenv("BILLBIRD_API_TOKEN", raising=False)
    yield


def test_registry_has_four_tools_in_declared_order():
    assert len(TOOLS) == 4
    assert tool_names() == [
        "billbird_hours_summary",
        "billbird_plan_vs_actual",
        "billbird_recent_activity",
        "billbird_cycle_time",
    ]


def test_registry_has_no_mutation_tools():
    for name in tool_names():
        assert not name.startswith(("create_", "update_", "delete_", "revoke_", "post_"))


def test_find_returns_none_for_unknown():
    assert find("nope") is None


def test_every_tool_schema_is_jsonschema_object():
    for spec in TOOLS:
        assert spec.input_schema["type"] == "object"
        assert "properties" in spec.input_schema


# --- Error envelopes -----------------------------------------------


def test_hours_summary_without_billbird_config_returns_structured_error():
    out = billbird_hours_summary(period="2026-04", group_by="user")
    assert out["error"] == "billbird_not_configured"
    assert "BILLBIRD_API_URL" in out["missing"]
    assert "BILLBIRD_API_TOKEN" in out["missing"]
    assert "docs" in out


def test_hours_summary_invalid_group_by():
    out = billbird_hours_summary(period="2026-04", group_by="bogus")
    assert out["error"] == "invalid_argument"
    assert out["field"] == "group_by"


def test_hours_summary_invalid_period(monkeypatch):
    monkeypatch.setenv("BILLBIRD_API_URL", "https://example.test")
    monkeypatch.setenv("BILLBIRD_API_TOKEN", "bb_x")
    out = billbird_hours_summary(period="bad", group_by="user")
    assert out["error"] == "invalid_argument"
    assert out["field"] == "period"


def test_plan_vs_actual_without_billbird_config():
    out = billbird_plan_vs_actual()
    assert out["error"] == "billbird_not_configured"


def test_plan_vs_actual_invalid_status(monkeypatch):
    monkeypatch.setenv("BILLBIRD_API_URL", "https://example.test")
    monkeypatch.setenv("BILLBIRD_API_TOKEN", "bb_x")
    out = billbird_plan_vs_actual(status="bogus")
    assert out["error"] == "invalid_argument"
    assert out["field"] == "status"


def test_recent_activity_without_billbird_config():
    out = billbird_recent_activity(since="2026-05-01")
    assert out["error"] == "billbird_not_configured"


def test_cycle_time_returns_not_implemented():
    out = billbird_cycle_time()
    assert out["error"] == "not_implemented"
