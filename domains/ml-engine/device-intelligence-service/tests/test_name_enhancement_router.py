"""sync_name_to_ha: a rename is reported only once the registry shows it.

Before TAP-6230 this posted to the ``homeassistant.update_entity`` service with a
``name`` field. That service only forces a state refresh, so every call returned
200, every rename was logged as "Synced", and nothing was ever renamed. These
tests pin the property that replaced it -- the value is read back.
"""

from __future__ import annotations

from typing import Any

import pytest
from src.api import name_enhancement_router as router
from src.services.name_enhancement import ha_sync


class FakeWs:
    """A device registry just deep enough to answer the gateway."""

    def __init__(self, devices: list[dict[str, Any]], *, drop_writes: bool = False) -> None:
        self.devices = devices
        self.drop_writes = drop_writes

    async def send_command(
        self, command_type: str, *, fields: dict[str, Any] | None = None, **payload: Any
    ) -> Any:
        args = {**payload, **(fields or {})}
        if command_type == "config/device_registry/list":
            return self.devices
        if command_type == "config/device_registry/update":
            if self.drop_writes:
                return {}  # accepted, changed nothing -- the original bug
            entry = next(d for d in self.devices if d["id"] == args["device_id"])
            entry.update({k: v for k, v in args.items() if k != "device_id"})
            return entry
        raise AssertionError(f"unexpected command {command_type}")


@pytest.fixture
def ha(monkeypatch: pytest.MonkeyPatch):
    """Install a fake HAClient and return a handle to the registry behind it."""

    def install(devices: list[dict[str, Any]], *, drop_writes: bool = False) -> FakeWs:
        ws = FakeWs(devices, drop_writes=drop_writes)

        class FakeHAClient:
            def __init__(self, *_args: Any, **_kwargs: Any) -> None:
                self.ws = ws

            async def __aenter__(self) -> FakeHAClient:
                return self

            async def __aexit__(self, *_exc: Any) -> None:
                return None

        monkeypatch.setattr(ha_sync, "HAClient", FakeHAClient)
        monkeypatch.setattr(ha_sync.settings, "HA_TOKEN", "token")
        monkeypatch.setattr(ha_sync.settings, "HA_URL", "http://ha.test")
        return ws

    return install


@pytest.mark.asyncio
async def test_a_rename_that_lands_is_reported_as_synced(ha):
    ws = ha([{"id": "dev0", "name": "WLED 0", "name_by_user": None}])

    assert await router.sync_name_to_ha("dev0", "Office Ceiling") is True
    assert ws.devices[0]["name_by_user"] == "Office Ceiling"


@pytest.mark.asyncio
async def test_a_write_that_changes_nothing_is_not_reported_as_synced(ha):
    """The original defect: accepted by HA, and the device keeps its old name."""
    ha([{"id": "dev0", "name": "WLED 0", "name_by_user": None}], drop_writes=True)

    assert await router.sync_name_to_ha("dev0", "Office Ceiling") is False


@pytest.mark.asyncio
async def test_a_device_missing_from_the_registry_is_not_reported_as_synced(ha):
    ha([{"id": "dev0", "name": "WLED 0", "name_by_user": None}])

    assert await router.sync_name_to_ha("ghost", "Office Ceiling") is False


@pytest.mark.asyncio
async def test_no_token_is_not_reported_as_synced(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ha_sync.settings, "HA_TOKEN", None)

    assert await router.sync_name_to_ha("dev0", "Office Ceiling") is False


class FakeSession:
    """Session double for the accept endpoint: tracks mutations and commits."""

    def __init__(self, device: Any) -> None:
        self.device = device
        self.commits = 0

    async def execute(self, _query: Any) -> Any:
        device = self.device

        class Result:
            def scalar_one_or_none(self) -> Any:
                return device

            def scalars(self) -> Any:
                class Scalars:
                    def all(self) -> list:
                        return []

                return Scalars()

        return Result()

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        pass


@pytest.mark.asyncio
async def test_accept_endpoint_leaves_the_suggestion_unaccepted_on_a_dropped_write(ha):
    """The full endpoint, not just the helper: a write HA accepts-but-ignores
    must 502 with the device row unmutated and nothing committed."""
    from fastapi import HTTPException

    ha([{"id": "dev0", "name": "WLED 0", "name_by_user": None}], drop_writes=True)

    class Device:
        id = "dev0"
        name = "WLED 0"
        name_by_user = None
        updated_at = None

    session = FakeSession(Device())
    request = router.AcceptNameRequest(suggested_name="Office Ceiling")

    with pytest.raises(HTTPException) as excinfo:
        await router.accept_suggested_name("dev0", request, session=session)

    assert excinfo.value.status_code == 502
    assert session.device.name_by_user is None  # local rename never happened
    assert session.commits == 0  # nothing was committed
