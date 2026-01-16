"""
Async helper utilities for Streamlit pages.

Provides safe async execution helpers that work with Streamlit's execution model.
"""

import asyncio
import concurrent.futures
from typing import Any, Callable, Coroutine, TypeVar

T = TypeVar("T")


def run_async_safe(coro: Coroutine[Any, Any, T], timeout: float = 30.0) -> T:
    """
    Run async coroutine safely in Streamlit context.
    
    Handles cases where an event loop may already be running.
    
    Args:
        coro: Async coroutine to execute
        timeout: Timeout in seconds
        
    Returns:
        Result of coroutine execution
        
    Raises:
        TimeoutError: If execution exceeds timeout
        Exception: Any exception raised by the coroutine
    """
    try:
        # Check if there's a running event loop
        asyncio.get_running_loop()
        # Loop is running, use thread executor
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result(timeout=timeout)
    except RuntimeError:
        # No running loop, can use asyncio.run() directly
        return asyncio.run(coro)
