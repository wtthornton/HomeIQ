"""HTTP clients for the services the MCP server fronts.

The server owns no data (catalogue: "thin schema-enforcing facade"). Every
backing call maps transport/HTTP failures onto the catalogue error codes so no
upstream traceback ever reaches the agent.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from .errors import ToolError


@dataclass(frozen=True)
class BackingStatus:
    name: str
    ok: bool
    latency_ms: float | None
    detail: str


class HttpBacking:
    """A single upstream HTTP service with a health probe and a JSON GET."""

    def __init__(
        self,
        name: str,
        base_url: str,
        *,
        bearer_token: str = "",
        api_key: str = "",
        health_path: str = "/health",
        timeout_seconds: float = 10.0,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.health_path = health_path
        headers: dict[str, str] = {}
        if bearer_token:  # data-api: HTTPBearer
            headers["Authorization"] = f"Bearer {bearer_token}"
        if api_key:  # device-intelligence-service: X-API-Key
            headers["X-API-Key"] = api_key
        self._client = httpx.AsyncClient(
            base_url=self.base_url, headers=headers, timeout=timeout_seconds
        )

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_json(self, path: str, params: dict[str, Any] | None = None, *, tool: str) -> Any:
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        return await self._request("GET", path, tool=tool, params=clean)

    async def post_json(self, path: str, body: dict[str, Any] | None = None, *, tool: str) -> Any:
        return await self._request("POST", path, tool=tool, json=body)

    async def _request(self, method: str, path: str, *, tool: str, **kwargs: Any) -> Any:
        if not self.configured:
            raise ToolError("backing_unavailable", f"{self.name} is not configured", tool=tool)
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise ToolError("backing_unavailable", f"{self.name} timed out", tool=tool) from exc
        except httpx.HTTPError as exc:
            raise ToolError(
                "backing_unavailable", f"{self.name} unreachable: {type(exc).__name__}", tool=tool
            ) from exc
        if response.status_code == 404:
            raise ToolError("not_found", f"{self.name} has no data for this request", tool=tool)
        if response.status_code in (401, 403):
            raise ToolError(
                "backing_unavailable", f"{self.name} rejected the server credential", tool=tool
            )
        if response.status_code >= 400:
            raise ToolError(
                "backing_unavailable",
                f"{self.name} returned HTTP {response.status_code}",
                tool=tool,
            )
        try:
            return response.json()
        except ValueError as exc:
            raise ToolError(
                "contract_violation", f"{self.name} returned non-JSON", tool=tool
            ) from exc

    async def probe(self) -> BackingStatus:
        if not self.configured:
            return BackingStatus(self.name, False, None, "not configured")
        started = time.perf_counter()
        try:
            response = await self._client.get(self.health_path, timeout=3.0)
        except httpx.HTTPError as exc:
            return BackingStatus(self.name, False, None, type(exc).__name__)
        latency = round((time.perf_counter() - started) * 1000, 1)
        return BackingStatus(
            self.name, response.status_code < 400, latency, f"HTTP {response.status_code}"
        )


class Backings:
    """The set of upstreams, built once from settings."""

    def __init__(
        self, *, data_api: HttpBacking, patterns: HttpBacking, device_intelligence: HttpBacking
    ) -> None:
        self.data_api = data_api
        self.patterns = patterns
        self.device_intelligence = device_intelligence

    def all(self) -> list[HttpBacking]:
        return [self.data_api, self.patterns, self.device_intelligence]

    async def probe_all(self) -> list[BackingStatus]:
        return [await b.probe() for b in self.all()]

    async def aclose(self) -> None:
        for backing in self.all():
            await backing.aclose()


def build_backings(settings: Any) -> Backings:
    timeout = settings.backing_timeout_seconds
    return Backings(
        data_api=HttpBacking(
            "data-api",
            settings.data_api_url,
            bearer_token=settings.data_api_key.get_secret_value(),
            timeout_seconds=timeout,
        ),
        patterns=HttpBacking(
            "ai-pattern-service", settings.pattern_service_url, timeout_seconds=timeout
        ),
        device_intelligence=HttpBacking(
            "device-intelligence-service",
            settings.device_intelligence_url,
            api_key=settings.data_api_key.get_secret_value(),
            timeout_seconds=timeout,
        ),
    )
