"""Tests for async helper utilities."""

import asyncio

import pytest
from utils.async_helpers import run_async_safe


class TestRunAsyncSafe:
    def test_successful_execution(self):
        async def add(a: int, b: int) -> int:
            return a + b

        result = run_async_safe(add(2, 3))
        assert result == 5

    def test_returns_correct_type(self):
        async def get_list() -> list[str]:
            return ["a", "b"]

        result = run_async_safe(get_list())
        assert result == ["a", "b"]

    def test_error_propagation(self):
        async def fail() -> None:
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            run_async_safe(fail())

    def test_timeout_parameter_accepted(self):
        """Verify timeout parameter is accepted without error."""

        async def quick() -> str:
            return "done"

        result = run_async_safe(quick(), timeout=5.0)
        assert result == "done"

    def test_none_return(self):
        async def noop() -> None:
            pass

        result = run_async_safe(noop())
        assert result is None

    def test_works_from_within_running_loop(self):
        """When called from inside a running event loop, uses thread executor."""

        async def outer() -> int:
            # Inside a running loop, run_async_safe should still work
            async def inner() -> int:
                return 42

            return run_async_safe(inner(), timeout=5.0)

        # Use asyncio.run to create a running loop context
        result = asyncio.run(outer())
        assert result == 42

    def test_custom_exception_propagation(self):
        class CustomError(Exception):
            pass

        async def raise_custom() -> None:
            raise CustomError("custom")

        with pytest.raises(CustomError, match="custom"):
            run_async_safe(raise_custom())
