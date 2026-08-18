"""Circuit-breaker regression test for DeviceCapabilityAnalyzer.

Proves that `_ml_engine_breaker.allow_request()` is awaited at the call
site in `analyze_device_capabilities`. `allow_request()` is `async def`;
calling it without `await` returns an always-truthy coroutine, so
`if not self._ml_engine_breaker.allow_request():` never short-circuits and
every call reaches the HTTP client even while the circuit is open
(bug-hunt c4, BUG-HomeIQ-4-1).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from src.synergy_detection.capability_analyzer import (
    DeviceCapabilityAnalyzer,
    _ml_engine_breaker,
)


class TestCapabilityAnalyzerCircuitBreaker:
    @pytest.mark.asyncio
    async def test_open_circuit_fast_fails_without_http_call(self) -> None:
        await _ml_engine_breaker.reset()
        try:
            for _ in range(3):
                await _ml_engine_breaker.record_failure()
            assert await _ml_engine_breaker.allow_request() is False

            analyzer = DeviceCapabilityAnalyzer()
            mock_client = AsyncMock()
            with patch.object(analyzer, "_get_client", new=AsyncMock(return_value=mock_client)):
                result = await analyzer.analyze_device_capabilities("light.test")

            assert result == []
            mock_client.get.assert_not_called()
        finally:
            await _ml_engine_breaker.reset()
