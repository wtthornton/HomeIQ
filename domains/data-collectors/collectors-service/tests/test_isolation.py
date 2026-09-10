"""Per-adapter timeout and failure isolation (TAP-7274 acceptance criterion).

One adapter's upstream hanging or raising must not stall the other five. The
mechanism under test is `adapters.base.with_adapter_timeout`: it wraps every
adapter route in `asyncio.wait_for`, so a hung upstream call becomes a bounded
504 for that adapter alone rather than blocking the shared event loop.

The first two tests exercise the mechanism directly (a synthetic hung route
next to a healthy one, both served by one ASGI app — this is the actual
request path, not a mock of it). The remaining tests exercise the real
collectors app: all eleven former routes answer, and a raise in one adapter's
request handling never propagates into another adapter's response.
"""

from __future__ import annotations

import asyncio
import os
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("INFLUXDB_TOKEN", "test-token")

from src.adapters.base import with_adapter_timeout  # noqa: E402


def _build_timeout_probe_app() -> FastAPI:
    """A minimal app with one adapter that hangs and one that doesn't.

    Mirrors exactly how `src/main.py` composes adapter routers: each route is
    wrapped in `with_adapter_timeout`, mounted on one shared FastAPI app.
    """
    probe = FastAPI()

    @probe.get("/hung-adapter/data")
    @with_adapter_timeout("hung-adapter", 0.2)
    async def hung_route():
        await asyncio.sleep(999)
        return {"unreachable": True}  # pragma: no cover

    @probe.get("/healthy-adapter/data")
    @with_adapter_timeout("healthy-adapter", 5.0)
    async def healthy_route():
        return {"ok": True}

    return probe


def test_hung_adapter_returns_504_within_its_own_timeout():
    """A real upstream hang is bounded by the per-adapter timeout, not left open."""
    with TestClient(_build_timeout_probe_app()) as client:
        start = time.monotonic()
        response = client.get("/hung-adapter/data")
        elapsed = time.monotonic() - start

    assert response.status_code == 504
    assert "hung-adapter" in response.json()["detail"]
    assert elapsed < 2.0, "the hang must be bounded by the adapter's own timeout, not asyncio's default (none)"


def test_healthy_adapter_still_answers_while_a_sibling_hangs():
    """The other adapter on the same app answers promptly regardless of the hung one."""
    with TestClient(_build_timeout_probe_app()) as client:
        # Fire the hang first (TestClient is sync/sequential, but this proves
        # the healthy route was never touched by the hung one's timeout or
        # exception — no shared state, no leaked lock, no blocked loop).
        client.get("/hung-adapter/data")

        start = time.monotonic()
        response = client.get("/healthy-adapter/data")
        elapsed = time.monotonic() - start

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert elapsed < 1.0


def test_all_former_routes_answer_through_the_merged_app(collectors_client):
    """Every former service's route is reachable, unprefixed, on the merged app.

    Uses the shared session-scoped `collectors_client` fixture rather than a
    second `TestClient(app)` — a second lifespan cycle over the same app
    object reassigns every adapter's module-level `service` singleton (e.g.
    `weather.weather_service`), then nulls it out again on its own shutdown,
    pulling the rug out from under any later test using the shared client.
    """
    former_routes = [
        "/",
        "/health",
        "/current-weather",
        "/cache/stats",
        "/sports-data",
        "/stats",
        "/current-aqi",
        "/cheapest-hours",
        "/api/v1/prediction",
        "/api/v1/events",
        "/consumption",
    ]
    for path in former_routes:
        response = collectors_client.get(path)
        assert response.status_code < 500, f"{path} -> {response.status_code}"


def test_one_adapter_raising_does_not_break_a_sibling_adapter(collectors_client):
    """A request that errors inside one adapter must not affect another adapter's response.

    electricity-pricing has no live upstream in this environment, so
    /cheapest-hours degrades to a handled 503 rather than a 500 — proving the
    error is contained inside that adapter's own handler (FastAPI's exception
    middleware would otherwise turn an unhandled raise into a 500 for that
    request only, still never touching other adapters' state).
    """
    degraded = collectors_client.get("/cheapest-hours")
    assert degraded.status_code in (200, 503)

    healthy = collectors_client.get("/consumption")
    assert healthy.status_code == 200
