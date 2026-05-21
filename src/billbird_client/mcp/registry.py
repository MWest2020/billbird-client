"""Fixed tool registry.

Adding or removing a tool is a code change in this file — not a
runtime config. Order matters: AI clients receive tools in this order
and lead with the first one they think fits.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from billbird_client.mcp import tools as t


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., dict[str, Any] | list[Any]]


_PERIOD_DESC = (
    "Period like '2026-04', '2026-04-15', or 'last-7d'. UTC. The response "
    "echoes the resolved start/end timestamps."
)


TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="billbird_hours_summary",
        description=(
            "Aggregate active log minutes for a period, grouped by user, "
            "client, repo, or issue. Output unit: minutes."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": _PERIOD_DESC},
                "group_by": {
                    "type": "string",
                    "enum": ["user", "client", "repo", "issue"],
                    "description": "One of user, client, repo, issue.",
                },
                "repository": {"type": "string", "description": "Optional owner/name filter"},
                "client": {"type": "string", "description": "Optional client name (exact match)"},
                "user": {"type": "string", "description": "Optional GitHub username filter"},
            },
            "required": ["period", "group_by"],
            "additionalProperties": False,
        },
        handler=t.billbird_hours_summary,
    ),
    ToolSpec(
        name="billbird_plan_vs_actual",
        description=(
            "Per-issue variance between active plan and active log totals. "
            "Output unit: minutes. Ordered by absolute variance descending "
            "so the issues most in need of attention lead the list."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "Optional " + _PERIOD_DESC},
                "status": {
                    "type": "string",
                    "enum": ["no_plan", "under", "on_target", "over"],
                    "description": "Optional status filter",
                },
                "repository": {"type": "string"},
                "client": {"type": "string"},
            },
            "required": [],
            "additionalProperties": False,
        },
        handler=t.billbird_plan_vs_actual,
    ),
    ToolSpec(
        name="billbird_recent_activity",
        description=(
            "Recent log + plan entries (combined, type-tagged 'log' or "
            "'plan'). Newest first. Output unit: minutes."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "since": {
                    "type": "string",
                    "description": (
                        "Lower bound on creation timestamp "
                        "(ISO 8601 UTC, e.g. 2026-05-17T00:00:00Z)"
                    ),
                },
                "limit": {
                    "type": "integer",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum number of rows returned. Default 50.",
                },
            },
            "required": ["since"],
            "additionalProperties": False,
        },
        handler=t.billbird_recent_activity,
    ),
    ToolSpec(
        name="billbird_cycle_time",
        description=(
            "Cycle-time per issue and aggregate for a scope. Stub: returns "
            "a structured 'not_implemented' response until Billbird exposes "
            "the matching REST endpoint."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "Optional " + _PERIOD_DESC},
                "repository": {"type": "string"},
            },
            "required": [],
            "additionalProperties": False,
        },
        handler=t.billbird_cycle_time,
    ),
]


def tool_names() -> list[str]:
    return [spec.name for spec in TOOLS]


def find(name: str) -> ToolSpec | None:
    for spec in TOOLS:
        if spec.name == name:
            return spec
    return None
