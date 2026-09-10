"""Base adapter interface for the collectors service.

Extends the ABC-based adapter shape already used by the smart-meter service's
``MeterAdapter`` (``smart_meter/meters/base.py`` in this package — a narrower
interface for swapping meter data sources) up to the level of the collectors
process as a whole: each former standalone service becomes a
``CollectorAdapter`` exposing a router plus its own startup/shutdown/health
hooks, mounted into one shared FastAPI app by ``src/main.py``.
"""

from __future__ import annotations

import asyncio
import functools
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, TypeVar

from fastapi import APIRouter, HTTPException

if TYPE_CHECKING:
    from homeiq_resilience import StandardHealthCheck

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


class CollectorAdapter(ABC):
    """Base class for a former standalone collector mounted into `collectors`."""

    name: str

    @property
    @abstractmethod
    def router(self) -> APIRouter:
        """Return this adapter's routes, registered at their former (unprefixed) paths."""

    async def startup(self) -> None:
        """Start the adapter (HTTP session, background poll task, etc.)."""
        return None

    async def shutdown(self) -> None:
        """Stop the adapter, releasing sessions and background tasks."""
        return None

    def register_health(self, _health: StandardHealthCheck) -> None:
        """Register this adapter's readiness checks on the shared health check."""
        return None


def with_adapter_timeout(name: str, timeout_seconds: float) -> Callable[[F], F]:
    """Bound one adapter's request handler so its upstream cannot stall the process.

    The epic's named risk is that one adapter's hung or raising upstream call
    stalls the other five. A raised exception already can't do that — each
    request runs on its own asyncio task, and FastAPI's own exception handler
    answers it independently. A *hang* is the real risk once all six adapters
    share one event loop: wrapping every adapter route in ``asyncio.wait_for``
    turns an indefinite await into a bounded 504 for that adapter alone,
    without touching the others' tasks.
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await asyncio.wait_for(fn(*args, **kwargs), timeout=timeout_seconds)
            except TimeoutError as exc:
                logger.error("%s adapter timed out after %ss", name, timeout_seconds)
                raise HTTPException(status_code=504, detail=f"{name} adapter timed out") from exc

        return wrapper  # type: ignore[return-value]

    return decorator
