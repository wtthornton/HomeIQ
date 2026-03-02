"""Standardized lifespan handler for HomeIQ services.

Manages startup/shutdown hooks with graceful degradation when
dependencies are unavailable.

Usage::

    from homeiq_resilience import ServiceLifespan, StandardHealthCheck

    health = StandardHealthCheck(service_name="my-service", version="1.0.0")

    lifespan = ServiceLifespan(service_name="my-service")
    lifespan.on_startup(init_database)
    lifespan.on_startup(init_http_clients)
    lifespan.on_shutdown(close_database)
    lifespan.on_shutdown(close_http_clients)

    app = create_app(title="My Service", lifespan=lifespan.handler)
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

logger = logging.getLogger(__name__)

# Type for lifecycle hooks: async callables that optionally accept the app
LifecycleHook = Callable[..., Awaitable[Any]]


class ServiceLifespan:
    """Manages startup and shutdown hooks for a FastAPI service.

    Parameters
    ----------
    service_name:
        Name used in log messages.
    graceful:
        If ``True`` (default), startup hook failures are logged as
        warnings instead of propagated.  The service starts in
        degraded mode.
    """

    def __init__(self, service_name: str, *, graceful: bool = True) -> None:
        self.service_name = service_name
        self.graceful = graceful
        self._startup_hooks: list[tuple[str, LifecycleHook]] = []
        self._shutdown_hooks: list[tuple[str, LifecycleHook]] = []

    def on_startup(self, fn: LifecycleHook, *, name: str | None = None) -> None:
        """Register an async startup hook.

        Parameters
        ----------
        fn:
            Async callable invoked during startup.
        name:
            Optional label for log messages (defaults to function name).
        """
        label = name or getattr(fn, "__name__", "startup_hook")
        self._startup_hooks.append((label, fn))

    def on_shutdown(self, fn: LifecycleHook, *, name: str | None = None) -> None:
        """Register an async shutdown hook.

        Parameters
        ----------
        fn:
            Async callable invoked during shutdown.
        name:
            Optional label for log messages (defaults to function name).
        """
        label = name or getattr(fn, "__name__", "shutdown_hook")
        self._shutdown_hooks.append((label, fn))

    @asynccontextmanager
    async def handler(self, app: FastAPI) -> AsyncGenerator[None, None]:
        """Async context manager compatible with FastAPI's ``lifespan`` param."""
        logger.info("%s starting up...", self.service_name)
        start = time.monotonic()

        for label, fn in self._startup_hooks:
            try:
                await fn()
                logger.info("  [startup] %s: OK", label)
            except Exception:
                if self.graceful:
                    logger.warning(
                        "  [startup] %s: FAILED (degraded mode)",
                        label,
                        exc_info=True,
                    )
                else:
                    logger.error("  [startup] %s: FAILED", label, exc_info=True)
                    raise

        elapsed = time.monotonic() - start
        logger.info("%s started in %.1fs", self.service_name, elapsed)

        yield

        logger.info("%s shutting down...", self.service_name)
        for label, fn in reversed(self._shutdown_hooks):
            try:
                await fn()
                logger.info("  [shutdown] %s: OK", label)
            except Exception:
                logger.warning(
                    "  [shutdown] %s: FAILED",
                    label,
                    exc_info=True,
                )

        logger.info("%s shutdown complete", self.service_name)
