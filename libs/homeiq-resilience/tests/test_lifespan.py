"""Tests for ServiceLifespan.

Covers:
  - Startup hooks execute in order
  - Shutdown hooks execute in reverse order
  - Graceful mode catches startup errors
  - Non-graceful mode propagates startup errors
  - Shutdown errors are logged but don't propagate
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from homeiq_resilience.lifespan import ServiceLifespan


class TestServiceLifespan:
    @pytest.mark.asyncio
    async def test_startup_hooks_execute_in_order(self) -> None:
        order: list[str] = []

        async def hook_a() -> None:
            order.append("a")

        async def hook_b() -> None:
            order.append("b")

        lifespan = ServiceLifespan("test")
        lifespan.on_startup(hook_a, name="a")
        lifespan.on_startup(hook_b, name="b")

        app = FastAPI()
        async with lifespan.handler(app):
            assert order == ["a", "b"]

    @pytest.mark.asyncio
    async def test_shutdown_hooks_execute_in_reverse(self) -> None:
        order: list[str] = []

        async def hook_a() -> None:
            order.append("a")

        async def hook_b() -> None:
            order.append("b")

        lifespan = ServiceLifespan("test")
        lifespan.on_shutdown(hook_a, name="a")
        lifespan.on_shutdown(hook_b, name="b")

        app = FastAPI()
        async with lifespan.handler(app):
            pass

        assert order == ["b", "a"]

    @pytest.mark.asyncio
    async def test_graceful_mode_catches_startup_errors(self) -> None:
        async def failing_hook() -> None:
            raise RuntimeError("startup fail")

        lifespan = ServiceLifespan("test", graceful=True)
        lifespan.on_startup(failing_hook, name="fail")

        app = FastAPI()
        # Should NOT raise
        async with lifespan.handler(app):
            pass

    @pytest.mark.asyncio
    async def test_non_graceful_mode_raises(self) -> None:
        async def failing_hook() -> None:
            raise RuntimeError("startup fail")

        lifespan = ServiceLifespan("test", graceful=False)
        lifespan.on_startup(failing_hook, name="fail")

        app = FastAPI()
        with pytest.raises(RuntimeError, match="startup fail"):
            async with lifespan.handler(app):
                pass

    @pytest.mark.asyncio
    async def test_shutdown_error_does_not_propagate(self) -> None:
        async def failing_shutdown() -> None:
            raise RuntimeError("shutdown fail")

        lifespan = ServiceLifespan("test")
        lifespan.on_shutdown(failing_shutdown, name="fail")

        app = FastAPI()
        # Should NOT raise
        async with lifespan.handler(app):
            pass

    @pytest.mark.asyncio
    async def test_both_startup_and_shutdown(self) -> None:
        started = AsyncMock()
        stopped = AsyncMock()

        lifespan = ServiceLifespan("test")
        lifespan.on_startup(started, name="start")
        lifespan.on_shutdown(stopped, name="stop")

        app = FastAPI()
        async with lifespan.handler(app):
            started.assert_awaited_once()
            stopped.assert_not_awaited()

        stopped.assert_awaited_once()
