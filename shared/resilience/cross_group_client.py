"""HTTP client for cross-group service calls with retry and circuit breaker.

Wraps ``httpx.AsyncClient`` with automatic exponential-backoff retries and
circuit-breaker protection.  Designed for inter-group HTTP communication
inside the HomeIQ platform (not for external APIs).

Usage::

    client = CrossGroupClient(
        base_url="http://data-api:8006",
        group_name="core-platform",
    )
    response = await client.call("GET", "/api/v1/entities")
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from .circuit_breaker import CircuitBreaker, CircuitOpenError

# Optional OpenTelemetry integration for trace propagation.
try:
    from opentelemetry import trace
    from opentelemetry.propagate import inject as otel_inject

    _OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _OTEL_AVAILABLE = False

logger = logging.getLogger(__name__)

# Transient errors that should trigger a retry.
_RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.RemoteProtocolError,
)


class CrossGroupClient:
    """Resilient HTTP client for cross-group service calls.

    Parameters
    ----------
    base_url:
        Root URL of the target service (e.g. ``http://data-api:8006``).
    group_name:
        Name of the service group being called (used in logs / metrics).
    timeout:
        Per-request timeout in seconds.
    max_retries:
        Maximum retry attempts on transient failures.
    auth_token:
        Optional bearer token for cross-group authentication.
    circuit_breaker:
        An existing ``CircuitBreaker`` instance.  If ``None`` a default
        one is created internally.
    """

    def __init__(
        self,
        base_url: str,
        group_name: str,
        timeout: float = 10.0,
        max_retries: int = 3,
        auth_token: str | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._group_name = group_name
        self._timeout = timeout
        self._max_retries = max_retries
        self._auth_token = auth_token
        self._breaker = circuit_breaker or CircuitBreaker(name=group_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def call(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute an HTTP request with retry and circuit-breaker logic.

        Parameters
        ----------
        method:
            HTTP method (``GET``, ``POST``, etc.).
        path:
            URL path appended to *base_url* (e.g. ``/api/v1/entities``).
        **kwargs:
            Forwarded to ``httpx.AsyncClient.request``.

        Returns
        -------
        httpx.Response

        Raises
        ------
        CircuitOpenError
            If the circuit breaker is open and requests are not allowed.
        httpx.HTTPError
            If all retries are exhausted.
        """
        last_exc: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            if not self._breaker.allow_request():
                raise CircuitOpenError(
                    f"Circuit open for group '{self._group_name}' — "
                    f"requests to {self._base_url} are blocked"
                )

            if self._breaker.state.value == "half_open":
                await self._breaker.increment_half_open_calls()

            try:
                response = await self._do_request(method, path, **kwargs)
                await self._breaker.record_success()
                return response

            except _RETRYABLE_EXCEPTIONS as exc:
                last_exc = exc
                await self._breaker.record_failure()

                if attempt < self._max_retries:
                    backoff = min(2 ** (attempt - 1), 10)
                    logger.warning(
                        "Transient error calling %s %s%s (group=%s, "
                        "attempt %d/%d, backoff=%ds): %s",
                        method,
                        self._base_url,
                        path,
                        self._group_name,
                        attempt,
                        self._max_retries,
                        backoff,
                        exc,
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        "All %d retries exhausted for %s %s%s (group=%s): %s",
                        self._max_retries,
                        method,
                        self._base_url,
                        path,
                        self._group_name,
                        exc,
                    )

        # All retries exhausted — re-raise the last transient error.
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _do_request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform a single HTTP request."""
        headers = dict(kwargs.pop("headers", {}))
        if self._auth_token:
            headers.setdefault("Authorization", f"Bearer {self._auth_token}")

        # Propagate OpenTelemetry trace context across group boundaries.
        if _OTEL_AVAILABLE:
            otel_inject(headers)
            span = trace.get_current_span()
            if span and span.is_recording():
                span.set_attribute("homeiq.target_group", self._group_name)

        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
        ) as client:
            response = await client.request(
                method,
                path,
                headers=headers,
                **kwargs,
            )
            return response
