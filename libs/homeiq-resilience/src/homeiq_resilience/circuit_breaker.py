"""Circuit breaker pattern for cross-group HTTP resilience.

Implements a three-state circuit breaker (CLOSED, OPEN, HALF_OPEN) that
protects services from cascading failures when upstream dependencies are
unhealthy.  Thread-safe via ``asyncio.Lock``.

Typical usage::

    breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

    if breaker.allow_request():
        try:
            response = await do_request()
            breaker.record_success()
        except Exception:
            breaker.record_failure()
    else:
        raise CircuitOpenError("upstream is down")
"""

from __future__ import annotations

import asyncio
import enum
import logging
import time

logger = logging.getLogger(__name__)


class CircuitState(enum.Enum):
    """Possible states of a circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when a request is attempted while the circuit is open."""


class ServiceDegradedError(Exception):
    """Raised when a service is reachable but returning degraded results.

    Use this to distinguish between "service is down" (CircuitOpenError)
    and "service responded but the response indicates degraded operation"
    (e.g. partial data, stale cache, fallback mode).

    Parameters
    ----------
    service_name:
        Name of the degraded service.
    reason:
        Human-readable explanation of the degradation.
    """

    def __init__(self, service_name: str = "", reason: str = "") -> None:
        self.service_name = service_name
        self.reason = reason
        msg = f"Service '{service_name}' is degraded"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class CircuitBreaker:
    """Three-state circuit breaker with configurable thresholds.

    Parameters
    ----------
    failure_threshold:
        Number of consecutive failures before the circuit opens.
    recovery_timeout:
        Seconds to wait in the OPEN state before transitioning to HALF_OPEN.
    half_open_max_calls:
        Maximum number of trial requests allowed in the HALF_OPEN state.
    name:
        Human-readable label used in log messages.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1,
        name: str = "default",
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_calls = half_open_max_calls
        self._name = name

        self._state = CircuitState.CLOSED
        self._failure_count: int = 0
        self._half_open_calls: int = 0
        self._last_failure_time: float | None = None
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        """Return the current circuit state, transitioning if needed."""
        if (
            self._state == CircuitState.OPEN
            and self._last_failure_time is not None
            and (time.monotonic() - self._last_failure_time) >= self._recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
            self._half_open_calls = 0
            logger.info(
                "Circuit '%s' transitioned OPEN -> HALF_OPEN after %.1fs",
                self._name,
                self._recovery_timeout,
            )
        return self._state

    @property
    def name(self) -> str:
        return self._name

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    async def allow_request(self) -> bool:
        """Return ``True`` if a request is allowed under the current state.

        In the HALF_OPEN state the check and counter increment are performed
        atomically under ``_lock``, preventing multiple concurrent coroutines
        from all seeing ``_half_open_calls == 0`` and flooding the recovering
        upstream with simultaneous probe requests.
        """
        async with self._lock:
            # Apply OPEN -> HALF_OPEN transition inside the lock so that the
            # state read and the subsequent counter increment are one atomic op.
            if (
                self._state == CircuitState.OPEN
                and self._last_failure_time is not None
                and (time.monotonic() - self._last_failure_time)
                >= self._recovery_timeout
            ):
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info(
                    "Circuit '%s' transitioned OPEN -> HALF_OPEN after %.1fs",
                    self._name,
                    self._recovery_timeout,
                )

            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self._half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            return False  # OPEN

    async def record_success(self) -> None:
        """Record a successful request, potentially closing the circuit."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                logger.info(
                    "Circuit '%s' transitioned HALF_OPEN -> CLOSED (recovered)",
                    self._name,
                )
            self._failure_count = 0
            self._half_open_calls = 0

    async def record_failure(self) -> None:
        """Record a failed request, potentially opening the circuit."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit '%s' transitioned HALF_OPEN -> OPEN (trial failed)",
                    self._name,
                )
            elif (
                self._state == CircuitState.CLOSED
                and self._failure_count >= self._failure_threshold
            ):
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit '%s' transitioned CLOSED -> OPEN after %d failures",
                    self._name,
                    self._failure_count,
                )

    async def increment_half_open_calls(self) -> None:
        """Track trial requests in the HALF_OPEN state."""
        async with self._lock:
            self._half_open_calls += 1

    async def reset(self) -> None:
        """Force-reset the circuit to CLOSED (useful for testing)."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._half_open_calls = 0
            self._last_failure_time = None
            logger.info("Circuit '%s' manually reset to CLOSED", self._name)
