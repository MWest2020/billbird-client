"""Period parser shared by the CLI and the MCP server.

Accepts the same three forms everywhere:

- ``YYYY-MM``    — entire calendar month (UTC).
- ``YYYY-MM-DD`` — single day (UTC).
- ``last-Nd``    — the last N days, ending at the current moment.

Returns a :class:`Period` carrying the resolved start and end
timestamps. UTC throughout; callers that need local-time display do
so at the boundary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class Period:
    """Resolved period range. Both ends are inclusive."""

    label: str
    from_iso: str
    until_iso: str

    def to_dict(self) -> dict[str, str]:
        return {"label": self.label, "from": self.from_iso, "until": self.until_iso}


_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")
_DAY_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_LAST_N_RE = re.compile(r"^last-(\d+)d$")


def parse_period(value: str) -> Period:
    """Parse ``value`` into a :class:`Period`.

    Raises ``ValueError`` with a human-readable hint on unrecognised
    input — callers (CLI / MCP tools) turn that into a friendly error.
    """
    if not value:
        raise ValueError("period is required (e.g. '2026-04', '2026-04-15', 'last-7d')")
    now = datetime.now(UTC)

    if m := _MONTH_RE.match(value):
        year, month = int(m.group(1)), int(m.group(2))
        start = datetime(year, month, 1, tzinfo=UTC)
        if month == 12:
            end = datetime(year + 1, 1, 1, tzinfo=UTC) - timedelta(seconds=1)
        else:
            end = datetime(year, month + 1, 1, tzinfo=UTC) - timedelta(seconds=1)
        return Period(label=value, from_iso=_iso(start), until_iso=_iso(end))

    if m := _DAY_RE.match(value):
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        start = datetime(year, month, day, tzinfo=UTC)
        end = start + timedelta(days=1) - timedelta(seconds=1)
        return Period(label=value, from_iso=_iso(start), until_iso=_iso(end))

    if m := _LAST_N_RE.match(value):
        days = int(m.group(1))
        if days <= 0:
            raise ValueError("last-Nd requires N >= 1")
        end = now
        start = end - timedelta(days=days)
        return Period(label=value, from_iso=_iso(start), until_iso=_iso(end))

    raise ValueError(
        f"unrecognised period {value!r} — supported: 'YYYY-MM', 'YYYY-MM-DD', 'last-Nd'"
    )


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
