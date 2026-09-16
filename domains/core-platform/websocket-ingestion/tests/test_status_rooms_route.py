"""Tests for GET /api/status/rooms (TAP-7587).

VAL-01: the route returns one entry per area known to data-api — including
an area with zero presence-capable sensors, reported ``unknown`` rather than
omitted. The aggregator alone can't prove this: its ``_room_occupancy`` cache
only ever contains areas a presence sensor has reported for (see
``aggregator.py:318-321``), so a test built only from sensor events would
still pass against a route that just iterates that cache. These tests fetch
the known-area set from a fake data-api instead, via a stub in place of
``fetch_known_area_ids`` — no real HTTP request is made.

VAL-02: unauthenticated -> 401, authenticated -> 200, matching the existing
``/api/status/house`` auth contract (TAP-7318, now landed per PR 172).
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

VALID_TOKEN = "tap7587-test-token-not-a-real-secret"  # noqa: S105 - test fixture
WRONG_TOKEN = "not-the-configured-token"  # noqa: S105 - test fixture, not a real credential

KNOWN_AREAS = ["office", "guest_room"]


@pytest.fixture(autouse=True)
def _configured_api_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Force the shared settings singleton to a known key for every test here."""
    monkeypatch.setattr(status_router.settings, "api_key", SecretStr(VALID_TOKEN))
    yield


@pytest.fixture(autouse=True)
def _reset_known_area_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A fresh, never-fetched cache per test — no state leaks between tests."""
    monkeypatch.setattr(status_router, "_known_area_cache", status_router.KnownAreaCache())
    yield


def _stub_fetch_known_area_ids(area_ids: list[str]):
    """Replace the network call with a canned result — no real HTTP request."""

    async def _fetch(data_api_url: str, api_key: str | None, timeout: float = 5.0) -> list[str]:
        return list(area_ids)

    return _fetch


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


# -- VAL-02: auth --------------------------------------------------------


def test_rooms_no_header_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        status_router, "fetch_known_area_ids", _stub_fetch_known_area_ids(KNOWN_AREAS)
    )
    client = _build_client()
    response = client.get("/api/status/rooms")
    assert response.status_code == 401


def test_rooms_wrong_token_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        status_router, "fetch_known_area_ids", _stub_fetch_known_area_ids(KNOWN_AREAS)
    )
    client = _build_client()
    response = client.get("/api/status/rooms", headers={"Authorization": f"Bearer {WRONG_TOKEN}"})
    assert response.status_code == 401


def test_rooms_valid_token_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        status_router, "fetch_known_area_ids", _stub_fetch_known_area_ids(KNOWN_AREAS)
    )
    client = _build_client()
    response = client.get("/api/status/rooms", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200


# -- VAL-01: zero-sensor areas appear as "unknown", never omitted --------


def test_zero_sensor_area_is_present_with_unknown_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """The core acceptance box: an area with no presence sensor at all
    (never seen by the aggregator, only known via data-api) must still be
    in the response, with state "unknown"."""
    monkeypatch.setattr(
        status_router, "fetch_known_area_ids", _stub_fetch_known_area_ids(KNOWN_AREAS)
    )
    client = _build_client(ready=False)  # zero events processed at all

    response = client.get("/api/status/rooms", headers={"Authorization": f"Bearer {VALID_TOKEN}"})

    assert response.status_code == 200
    body = response.json()
    rooms_by_area = {r["area_id"]: r for r in body["rooms"]}
    assert set(rooms_by_area) == set(KNOWN_AREAS)
    for area_id in KNOWN_AREAS:
        assert rooms_by_area[area_id]["state"] == "unknown"
        assert rooms_by_area[area_id]["contributing_entity_ids"] == []


def test_sensor_reporting_area_merges_with_known_areas(monkeypatch: pytest.MonkeyPatch) -> None:
    """One area has a live sensor; the other is known only to data-api.
    Both appear, with distinct correct states.

    State is written directly into the aggregator's roll-up dict rather
    than via ``process_state_change`` (which acquires an ``asyncio.Lock``):
    TestClient drives requests on its own event loop, and binding the lock
    outside of it risks a "different loop" error — see test_status_auth.py's
    module docstring for the same tradeoff.
    """
    monkeypatch.setattr(
        status_router, "fetch_known_area_ids", _stub_fetch_known_area_ids(KNOWN_AREAS)
    )
    client = _build_client(ready=True)
    aggregator = client.app.state.service.house_status_aggregator
    aggregator._room_occupancy["office"] = {
        "entities": {"binary_sensor.office_motion": "on"},
        "last_changed": "2026-09-15T00:00:00+00:00",
    }

    response = client.get("/api/status/rooms", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    rooms_by_area = {r["area_id"]: r for r in response.json()["rooms"]}

    assert set(rooms_by_area) == {"office", "guest_room"}
    assert rooms_by_area["office"]["state"] == "detected"
    assert rooms_by_area["office"]["contributing_entity_ids"] == ["binary_sensor.office_motion"]
    assert rooms_by_area["guest_room"]["state"] == "unknown"


def test_negative_control_area_count_matches_known_areas(monkeypatch: pytest.MonkeyPatch) -> None:
    """A distinct known-area set produces a distinct, matching room count."""
    areas = ["kitchen", "office", "guest_room", "garage"]
    monkeypatch.setattr(status_router, "fetch_known_area_ids", _stub_fetch_known_area_ids(areas))
    client = _build_client(ready=False)

    response = client.get("/api/status/rooms", headers={"Authorization": f"Bearer {VALID_TOKEN}"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["rooms"]) == len(areas)
    assert {r["area_id"] for r in body["rooms"]} == set(areas)


# -- data-api unreachable: fail closed only when nothing is cached -------


def test_known_areas_unavailable_and_uncached_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _raise(data_api_url: str, api_key: str | None, timeout: float = 5.0) -> list[str]:
        raise status_router.KnownAreasUnavailable("data-api is down")

    monkeypatch.setattr(status_router, "fetch_known_area_ids", _raise)
    client = _build_client(ready=False)

    response = client.get("/api/status/rooms", headers={"Authorization": f"Bearer {VALID_TOKEN}"})

    assert response.status_code == 503
