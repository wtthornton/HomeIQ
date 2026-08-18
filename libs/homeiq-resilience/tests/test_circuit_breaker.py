"""Tests for the CircuitBreaker state machine.

Covers all state transitions:
  CLOSED -> OPEN  (after threshold failures)
  OPEN -> HALF_OPEN  (after recovery timeout)
  HALF_OPEN -> CLOSED  (on success)
  HALF_OPEN -> OPEN  (on failure)
  CircuitOpenError raised when circuit is open
"""

from __future__ import annotations

import time

import pytest
from homeiq_resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)


@pytest.fixture
def breaker() -> CircuitBreaker:
    """Create a breaker with low thresholds for fast tests."""
    return CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=1.0,
        half_open_max_calls=1,
        name="test-breaker",
    )


# ------------------------------------------------------------------
# Initial state
# ------------------------------------------------------------------


class TestInitialState:
    def test_starts_closed(self, breaker: CircuitBreaker) -> None:
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_allows_requests_when_closed(self, breaker: CircuitBreaker) -> None:
        assert await breaker.allow_request() is True

    def test_name_is_set(self, breaker: CircuitBreaker) -> None:
        assert breaker.name == "test-breaker"


# ------------------------------------------------------------------
# CLOSED -> OPEN transition
# ------------------------------------------------------------------


class TestClosedToOpen:
    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self, breaker: CircuitBreaker) -> None:
        for _ in range(3):
            await breaker.record_failure()

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_stays_closed_below_threshold(self, breaker: CircuitBreaker) -> None:
        for _ in range(2):
            await breaker.record_failure()

        assert breaker.state == CircuitState.CLOSED
        assert await breaker.allow_request() is True

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, breaker: CircuitBreaker) -> None:
        await breaker.record_failure()
        await breaker.record_failure()
        await breaker.record_success()
        # After reset, need full threshold again
        await breaker.record_failure()
        await breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_blocks_requests_when_open(self, breaker: CircuitBreaker) -> None:
        for _ in range(3):
            await breaker.record_failure()

        assert await breaker.allow_request() is False


# ------------------------------------------------------------------
# OPEN -> HALF_OPEN transition
# ------------------------------------------------------------------


class TestOpenToHalfOpen:
    @pytest.mark.asyncio
    async def test_transitions_after_recovery_timeout(self, breaker: CircuitBreaker) -> None:
        for _ in range(3):
            await breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Simulate time passing beyond recovery timeout
        breaker._last_failure_time = time.monotonic() - 2.0

        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_stays_open_before_timeout(self, breaker: CircuitBreaker) -> None:
        for _ in range(3):
            await breaker.record_failure()

        # Last failure is recent — should stay OPEN
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_allows_limited_requests_in_half_open(self, breaker: CircuitBreaker) -> None:
        for _ in range(3):
            await breaker.record_failure()

        breaker._last_failure_time = time.monotonic() - 2.0
        assert breaker.state == CircuitState.HALF_OPEN
        assert await breaker.allow_request() is True

        # After one trial call, should block further requests
        await breaker.increment_half_open_calls()
        assert await breaker.allow_request() is False


# ------------------------------------------------------------------
# HALF_OPEN -> CLOSED transition
# ------------------------------------------------------------------


class TestHalfOpenToClosed:
    @pytest.mark.asyncio
    async def test_closes_on_success(self, breaker: CircuitBreaker) -> None:
        # Open the circuit
        for _ in range(3):
            await breaker.record_failure()

        # Transition to HALF_OPEN
        breaker._last_failure_time = time.monotonic() - 2.0
        assert breaker.state == CircuitState.HALF_OPEN

        # Success closes it
        await breaker.record_success()
        assert breaker.state == CircuitState.CLOSED
        assert await breaker.allow_request() is True


# ------------------------------------------------------------------
# HALF_OPEN -> OPEN transition
# ------------------------------------------------------------------


class TestHalfOpenToOpen:
    @pytest.mark.asyncio
    async def test_reopens_on_failure(self, breaker: CircuitBreaker) -> None:
        # Open the circuit
        for _ in range(3):
            await breaker.record_failure()

        # Transition to HALF_OPEN
        breaker._last_failure_time = time.monotonic() - 2.0
        assert breaker.state == CircuitState.HALF_OPEN

        # Failure during HALF_OPEN -> back to OPEN
        await breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        assert await breaker.allow_request() is False


# ------------------------------------------------------------------
# CircuitOpenError
# ------------------------------------------------------------------


class TestCircuitOpenError:
    def test_is_an_exception(self) -> None:
        assert issubclass(CircuitOpenError, Exception)

    def test_message_preserved(self) -> None:
        err = CircuitOpenError("group ml-engine is down")
        assert str(err) == "group ml-engine is down"


# ------------------------------------------------------------------
# Reset
# ------------------------------------------------------------------


class TestAsyncContextManager:
    """`async with breaker:` protocol (bug-hunt c4, BUG-HomeIQ-4-2).

    Multiple call sites (ha_rest_client.py, linter_client.py, agent_loop.py)
    already used `async with <breaker>:` as if CircuitBreaker supported the
    async context manager protocol. It didn't, so every one of those calls
    raised TypeError before ever reaching the protected block.
    """

    @pytest.mark.asyncio
    async def test_allows_request_and_records_success(self, breaker: CircuitBreaker) -> None:
        async with breaker:
            pass
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_records_failure_and_reraises_on_exception(self, breaker: CircuitBreaker) -> None:
        with pytest.raises(ValueError, match="boom"):
            async with breaker:
                raise ValueError("boom")
        assert breaker._failure_count == 1

    @pytest.mark.asyncio
    async def test_raises_circuit_open_error_when_open(self, breaker: CircuitBreaker) -> None:
        for _ in range(3):
            await breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        with pytest.raises(CircuitOpenError):
            async with breaker:
                raise AssertionError("protected block must not run")


class TestReset:
    @pytest.mark.asyncio
    async def test_reset_returns_to_closed(self, breaker: CircuitBreaker) -> None:
        for _ in range(3):
            await breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        await breaker.reset()
        assert breaker.state == CircuitState.CLOSED
        assert await breaker.allow_request() is True
