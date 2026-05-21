"""Python client + CLI + MCP server for Billbird's REST API.

Read-only by design. Public surface:

- :class:`BillbirdClient` — synchronous HTTP wrapper around
  ``/api/v1/*``. Build via :meth:`BillbirdClient.from_env` for the
  common case (``BILLBIRD_API_URL`` + ``BILLBIRD_API_TOKEN``).
- :class:`BillbirdNotConfigured` — raised when env vars are missing.
- :class:`BillbirdHTTPError` — raised for any non-2xx response; carries
  ``status``, ``body``, and a ``hint`` field
  (``auth`` / ``not_found`` / ``server`` / ``client``).

For ergonomic use, see also :mod:`billbird_client.cli` and
:mod:`billbird_client.mcp`.
"""

from __future__ import annotations

from billbird_client.client import (
    BillbirdClient,
    BillbirdHTTPError,
    BillbirdNotConfigured,
)

__all__ = [
    "BillbirdClient",
    "BillbirdHTTPError",
    "BillbirdNotConfigured",
]
__version__ = "0.1.0"
