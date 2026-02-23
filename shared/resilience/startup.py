"""Startup resilience for upstream dependencies.

Provides a non-fatal retry loop so services can wait for their upstream
dependencies on startup instead of crashing.  If a dependency never
becomes available, the service starts in *degraded mode* rather than
exiting.

Usage in a FastAPI ``lifespan``::

    from shared.resilience import wait_for_dependency

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        available = await wait_for_dependency(
            url="http://data-api:8006",
            name="data-api",
        )
        if not available:
            logger.warning("Starting without data-api — features degraded")
        yield
"""

from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)


async def wait_for_dependency(
    url: str,
    name: str,
    max_retries: int = 30,
    health_path: str = "/health",
) -> bool:
    """Wait for an upstream dependency with exponential backoff.

    Parameters
    ----------
    url:
        Base URL of the dependency (e.g. ``http://data-api:8006``).
    name:
        Human-readable name used in log messages.
    max_retries:
        Maximum number of probe attempts.
    health_path:
        Path appended to *url* when probing (default ``/health``).

    Returns
    -------
    bool
        ``True`` if the dependency became available within the retry
        budget, ``False`` otherwise.  The caller should decide how to
        degrade gracefully when ``False`` is returned.
    """
    base = url.rstrip("/")
    probe_url = f"{base}{health_path}"

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(probe_url)
                if resp.status_code == 200:
                    logger.info(
                        "Dependency '%s' is healthy (%s responded 200)",
                        name,
                        probe_url,
                    )
                    return True
        except (httpx.ConnectError, httpx.TimeoutException, OSError):
            pass

        wait_seconds = min(2 ** attempt, 30)
        logger.warning(
            "Waiting for dependency '%s' (attempt %d/%d, next retry in %ds)",
            name,
            attempt + 1,
            max_retries,
            wait_seconds,
        )
        await asyncio.sleep(wait_seconds)

    logger.error(
        "Dependency '%s' not available after %d attempts — "
        "starting in degraded mode",
        name,
        max_retries,
    )
    return False
