"""A small client for the two calls the integration makes, on Home Assistant's aiohttp session."""

from __future__ import annotations

from typing import Any

import aiohttp

from .const import API_BASE_URL

TIMEOUT = aiohttp.ClientTimeout(total=20)


class NimboApiError(Exception):
    """An error answer or a failed request."""

    def __init__(
        self, message: str, *, status: int | None = None, code: str | None = None, retry_after: float | None = None
    ) -> None:
        super().__init__(f"{code}: {message}" if code else message)
        self.status = status
        self.code = code
        self.retry_after = retry_after


class NimboAuthError(NimboApiError):
    """401: missing, invalid or revoked key."""


class NimboOutOfCoverage(NimboApiError):
    """404 out_of_coverage: the place is outside the forecast area."""


class NimboRateLimited(NimboApiError):
    """429: the monthly quota is used up (``monthly_quota_exceeded``) or too many calls at once."""


class NimboApi:
    def __init__(self, session: aiohttp.ClientSession, api_key: str, base_url: str = API_BASE_URL) -> None:
        self._session = session
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"X-API-Key": self._api_key, "Accept": "application/json"}
        try:
            async with self._session.get(f"{self._base_url}{path}", params=params, headers=headers, timeout=TIMEOUT) as resp:
                try:
                    body = await resp.json(content_type=None)
                except (aiohttp.ContentTypeError, ValueError):
                    body = None
                if resp.status < 400 and isinstance(body, dict):
                    return body
                data = body if isinstance(body, dict) else {}
                code = data.get("error") if isinstance(data.get("error"), str) else None
                message = str(data.get("message") or f"HTTP {resp.status}")
                retry_after: float | None = None
                try:
                    retry_after = float(resp.headers.get("Retry-After", ""))
                except ValueError:
                    retry_after = None
                cls: type[NimboApiError] = NimboApiError
                if resp.status == 401:
                    cls = NimboAuthError
                elif resp.status == 404 and code == "out_of_coverage":
                    cls = NimboOutOfCoverage
                elif resp.status == 429:
                    cls = NimboRateLimited
                raise cls(message, status=resp.status, code=code, retry_after=retry_after)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise NimboApiError(f"Request failed: {err}") from err

    async def nowcast(self, lat: float, lon: float) -> dict[str, Any]:
        """The point forecast, 5-minute steps for the next 3 hours (one counted call)."""
        return await self._get("/v1/nowcast", {"lat": f"{lat:.4f}", "lon": f"{lon:.4f}", "step": 5})

    async def key_usage(self) -> dict[str, Any]:
        """The key's plan and usage (not counted): checks a key without spending a call."""
        return await self._get("/v1/keys/me")
