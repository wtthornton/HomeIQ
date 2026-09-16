"""WS /ws/status carries a "rooms" section (TAP-7587, VAL-03).

The pre-existing payload test (test_status_auth.py's
``test_ws_status_valid_token_connects_and_receives_one_frame``) makes no
mocked HTTP calls and must keep passing unmodified — see this repo's
``git diff`` evidence. So the WS handler must never perform a live fetch to
data-api inline in the connect path; it only reads whatever
``_known_area_cache`` was last warmed with (see status.py's ``ws_status``).
This test warms that cache directly rather than mocking the network, then
asserts the initial snapshot frame's "rooms" key includes a zero-sensor area
as "unknown" alongside a sensor-reporting area.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from src.api.routers import status as status_router
from src.house_status.aggregator import HouseStatusAggregator
from src.house_status.websocket_publisher import StatusWebSocketPublisher

if TYPE_CHECKING:
    from collections.abc import Iterator

VALID_TOKEN = "tap7587-ws-test-token-not-a-real-secret"  # noqa: S105 - test fixture


@pytest.fixture(autouse=True)
def _configured_api_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(status_router.settings, "api_key", SecretStr(VALID_TOKEN))
    yield


@pytest.fixture(autouse=True)
def _reset_known_area_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(status_router, "_known_area_cache", status_router.KnownAreaCache())
    yield


class _StubService:
    def __init__(self, *, ready: bool) -> None:
        self.house_status_aggregator = HouseStatusAggregator()
        self.house_status_aggregator._ready = ready
        self.house_status_publisher = StatusWebSocketPublisher()


def _build_client(*, ready: bool = True) -> TestClient:
    app = FastAPI()
    app.include_router(status_router.router)
    app.state.service = _StubService(ready=ready)
    return TestClient(app)


def test_ws_snapshot_carries_rooms_section_with_zero_sensor_area() -> None:
    client = _build_client(ready=True)
    aggregator = client.app.state.service.house_status_aggregator
    aggregator._room_occupancy["office"] = {
        "entities": {"binary_sensor.office_motion": "on"},
        "last_changed": "2026-09-15T00:00:00+00:00",
    }
    # Warm the cache the way GET /api/status/rooms would, without a real
    # HTTP call to data-api.
    status_router._known_area_cache.update(["office", "guest_room"])

    with client.websocket_connect(
        "/ws/status", headers={"Authorization": f"Bearer {VALID_TOKEN}"}
    ) as websocket:
        frame = websocket.receive_json()

    assert frame["type"] == "snapshot"
    assert "rooms" in frame
    rooms_by_area = {r["area_id"]: r for r in frame["rooms"]}
    assert set(rooms_by_area) == {"office", "guest_room"}
    assert rooms_by_area["office"]["state"] == "detected"
    assert rooms_by_area["guest_room"]["state"] == "unknown"
    assert rooms_by_area["guest_room"]["contributing_entity_ids"] == []


def test_ws_snapshot_rooms_falls_back_to_sensor_only_when_cache_cold() -> None:
    """A cold cache (no REST call has warmed it yet) degrades to the
    pre-TAP-7587 sensor-only room_occupancy content rather than failing."""
    client = _build_client(ready=True)
    aggregator = client.app.state.service.house_status_aggregator
    aggregator._room_occupancy["office"] = {
        "entities": {"binary_sensor.office_motion": "on"},
        "last_changed": "2026-09-15T00:00:00+00:00",
    }

    with client.websocket_connect(
        "/ws/status", headers={"Authorization": f"Bearer {VALID_TOKEN}"}
    ) as websocket:
        frame = websocket.receive_json()

    assert frame["type"] == "snapshot"
    rooms_by_area = {r["area_id"]: r for r in frame["rooms"]}
    assert set(rooms_by_area) == {"office"}
    assert rooms_by_area["office"]["state"] == "detected"
