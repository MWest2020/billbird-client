"""Synchronous HTTP client for Billbird's REST API.

Mirrors the shape of established Python clients for similar
single-instance services: env-driven construction, bearer auth, typed
errors, no automatic retries beyond what Billbird itself does, and a
context-manager lifecycle so resources close deterministically.

The client is **read-only** at the surface — every method maps to a
``GET`` on Billbird. Writes happen in GitHub via slash commands and
land in Billbird through its webhook; this package does not invent a
second write path.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

import httpx

DEFAULT_TIMEOUT = 15.0


class BillbirdNotConfigured(RuntimeError):
    """Raised when the env vars Billbird needs are missing or empty."""

    def __init__(self, missing: Iterable[str]) -> None:
        self.missing = list(missing)
        super().__init__(
            "Billbird is not configured: missing " + ", ".join(self.missing)
        )


class BillbirdHTTPError(RuntimeError):
    """Raised for any Billbird response outside the 2xx range.

    ``hint`` is one of ``auth``, ``not_found``, ``server``, or
    ``client``; it is computed from the status code so the caller can
    classify without re-parsing.
    """

    def __init__(self, status: int, body: Any) -> None:
        self.status = status
        self.body = body
        self.hint = _classify_status(status)
        super().__init__(f"billbird HTTP {status} ({self.hint}): {body!r}")


def _classify_status(status: int) -> str:
    if status in (401, 403):
        return "auth"
    if status == 404:
        return "not_found"
    if 500 <= status < 600:
        return "server"
    return "client"


class BillbirdClient:
    """Thin synchronous wrapper around Billbird's ``/api/v1/*`` routes."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        http_client: httpx.Client | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        if http_client is None:
            self._http = httpx.Client(
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
            self._owns_http = True
        else:
            self._http = http_client
            self._owns_http = False

    # --- lifecycle ---

    @classmethod
    def from_env(
        cls,
        *,
        http_client: httpx.Client | None = None,
    ) -> BillbirdClient:
        """Build a client from ``BILLBIRD_API_URL`` and
        ``BILLBIRD_API_TOKEN``.

        Raises :class:`BillbirdNotConfigured` (not ``KeyError``) when
        either env var is missing — callers turn that into a friendly
        error rather than letting a 500 escape.
        """
        url = os.environ.get("BILLBIRD_API_URL", "").strip()
        token = os.environ.get("BILLBIRD_API_TOKEN", "").strip()
        missing: list[str] = []
        if not url:
            missing.append("BILLBIRD_API_URL")
        if not token:
            missing.append("BILLBIRD_API_TOKEN")
        if missing:
            raise BillbirdNotConfigured(missing)
        return cls(base_url=url, token=token, http_client=http_client)

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> BillbirdClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # --- low-level helpers ---

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        resp = self._http.get(self._base_url + path, params=_clean(params))
        if 200 <= resp.status_code < 300:
            if resp.content:
                return resp.json()
            return None
        body: Any
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        raise BillbirdHTTPError(resp.status_code, body)

    # --- typed routes ---

    def time_entries(
        self,
        *,
        repository: str | None = None,
        username: str | None = None,
        client_id: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        labels: list[str] | None = None,
        label_prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "repo": repository,
            "username": username,
            "client_id": client_id,
            "from": date_from,
            "to": date_to,
            "label_prefix": label_prefix,
        }
        # httpx serialises a list value into a repeated key, which
        # matches Billbird's ?label=foo&label=bar semantics.
        if labels:
            params["label"] = labels
        data = self._get("/api/v1/time-entries", params)
        return data or []

    def plans(
        self,
        *,
        repository: str | None = None,
        issue: int | None = None,
        status: str | None = None,
        since: str | None = None,
        until: str | None = None,
        labels: list[str] | None = None,
        label_prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "repository": repository,
            "issue": issue,
            "status": status,
            "since": since,
            "until": until,
            "label_prefix": label_prefix,
        }
        if labels:
            params["label"] = labels
        data = self._get("/api/v1/plans", params)
        return data or []

    def plan_vs_actual(self, owner: str, repo: str, issue_number: int) -> dict[str, Any]:
        return self._get(
            f"/api/v1/issues/{owner}/{repo}/{issue_number}/plan-vs-actual"
        )

    def clients(self) -> list[dict[str, Any]]:
        data = self._get("/api/v1/clients")
        return data or []


def _clean(params: dict[str, Any] | None) -> dict[str, Any] | None:
    if not params:
        return None
    return {k: v for k, v in params.items() if v is not None and v != ""}
