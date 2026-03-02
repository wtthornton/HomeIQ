"""Managed HTTP client for HomeIQ services.

Provides a lifecycle-managed ``httpx.AsyncClient`` with connection
pooling, timeout defaults, and retry logic.  Replaces 7+ duplicate
httpx/aiohttp session management patterns across services.

Usage::

    from homeiq_resilience import ManagedHTTPClient

    client = ManagedHTTPClient(
        base_url="http://data-api:8006",
        service_name="data-api",
    )

    # In lifespan startup:
    await client.start()

    # Use the client:
    resp = await client.get("/api/v1/entities")

    # In lifespan shutdown:
    await client.close()

    # Or as an async context manager:
    async with ManagedHTTPClient(base_url="http://data-api:8006") as client:
        data = await client.get("/health")
"""

from __future__ import annotations

import logging
from types import TracebackType
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class ManagedHTTPClient:
    """Lifecycle-managed async HTTP client with retry and connection pooling.

    Parameters
    ----------
    base_url:
        Base URL for all requests.
    service_name:
        Human-readable name for logging.
    timeout:
        Default request timeout in seconds.
    max_retries:
        Maximum retry attempts for transient failures.
    max_connections:
        Maximum number of connections in the pool.
    max_keepalive:
        Maximum number of keepalive connections.
    auth_token:
        Optional Bearer token for all requests.
    """

    def __init__(
        self,
        base_url: str,
        service_name: str = "",
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
        max_connections: int = 10,
        max_keepalive: int = 5,
        auth_token: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_name = service_name or base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._auth_token = auth_token
        self._client: httpx.AsyncClient | None = None
        self._pool_limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive,
        )

    async def start(self) -> None:
        """Create the underlying httpx.AsyncClient."""
        if self._client is not None:
            return

        headers: dict[str, str] = {}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            limits=self._pool_limits,
            headers=headers,
            follow_redirects=True,
        )
        logger.debug("HTTP client started: %s", self.service_name)

    async def close(self) -> None:
        """Close the underlying httpx.AsyncClient."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.debug("HTTP client closed: %s", self.service_name)

    @property
    def client(self) -> httpx.AsyncClient:
        """Return the underlying client, auto-starting if needed."""
        if self._client is None:
            raise RuntimeError(
                f"HTTP client not started for {self.service_name}. "
                "Call await client.start() first or use 'async with' context manager."
            )
        return self._client

    # --- Context manager ---

    async def __aenter__(self) -> ManagedHTTPClient:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    # --- HTTP methods ---

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send a GET request with retry."""
        return await self._request("GET", path, params=params, headers=headers)

    async def post(
        self,
        path: str,
        *,
        json: Any | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send a POST request with retry."""
        return await self._request("POST", path, json=json, data=data, headers=headers)

    async def put(
        self,
        path: str,
        *,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send a PUT request with retry."""
        return await self._request("PUT", path, json=json, headers=headers)

    async def delete(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send a DELETE request with retry."""
        return await self._request("DELETE", path, headers=headers)

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Internal method that dispatches requests with retry logic."""

        @retry(
            retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True,
        )
        async def _do_request() -> httpx.Response:
            return await self.client.request(method, path, **kwargs)

        try:
            response = await _do_request()
            return response
        except Exception:
            logger.warning("%s %s%s failed", method, self.service_name, path)
            raise
