"""Tests for hygiene API router."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from homeiq_ha.client.errors import HACommandError
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from src.api.hygiene_router import get_ha_client
from src.config import Settings
from src.core.database import get_db_session, initialize_database
from src.main import app
from src.models.database import Device, DeviceHygieneIssue

#: What HA's config/device_registry/update command schema actually accepts. A
#: stub that echoed back any field it was handed is what let the `name=` rename
#: look like it worked -- real HA answers success: false for anything else.
_DEVICE_UPDATE_FIELDS = {"area_id", "disabled_by", "labels", "name_by_user"}


class StubHomeAssistantClient:
    """A registry just deep enough to answer HARegistryWriter's read-back."""

    def __init__(self):
        self.calls = []
        self.devices = [{"id": "device-1", "name": "Kitchen Light", "area_id": "kitchen"}]
        self.entities = [{"entity_id": "light.kitchen", "disabled_by": "user"}]
        self.areas = [{"area_id": "kitchen", "name": "Kitchen"}]

    async def send_command(self, command_type: str, *, fields=None, **payload):
        args = {**payload, **(fields or {})}
        self.calls.append((command_type, args))

        if command_type == "config/device_registry/list":
            return self.devices
        if command_type == "config/area_registry/list":
            return self.areas
        if command_type == "config/entity_registry/get":
            return next(e for e in self.entities if e["entity_id"] == args["entity_id"])
        if command_type == "config/device_registry/update":
            changes = {k: v for k, v in args.items() if k != "device_id"}
            if unknown := set(changes) - _DEVICE_UPDATE_FIELDS:
                raise HACommandError(command_type, "invalid_format", f"extra keys: {unknown}")
            entry = next(d for d in self.devices if d["id"] == args["device_id"])
            entry.update(changes)
            return entry
        if command_type == "config/entity_registry/update":
            entry = next(e for e in self.entities if e["entity_id"] == args["entity_id"])
            entry.update({k: v for k, v in args.items() if k != "entity_id"})
            return entry
        raise AssertionError(f"unexpected command {command_type}")

    async def update_entity_registry_entry(self, entity_id: str, **fields):
        self.calls.append(("entity_update", entity_id, fields))
        return {"entity_id": entity_id, **fields}

    async def start_config_flow(self, handler: str, data=None):
        self.calls.append(("config_flow", handler, data))
        return {"handler": handler}


@pytest_asyncio.fixture(autouse=True)
async def setup_database(tmp_path_factory):
    db_dir = Path("./data")
    db_dir.mkdir(exist_ok=True)
    tmp_path_factory.mktemp("device-int-api") / "hygiene_api.db"
    settings = Settings(DATABASE_URL="postgresql+asyncpg://homeiq:homeiq@localhost:5432/homeiq")
    await initialize_database(settings)

    # Seed sample data
    now = datetime.now(UTC)
    async for session in get_db_session():
        device = Device(
            id="device-1",
            name="Kitchen Light",
            manufacturer="Signify",
            model="Hue",
            area_id="kitchen",
            integration="hue",
            created_at=now,
            updated_at=now,
        )
        issue = DeviceHygieneIssue(
            issue_key="duplicate_name:device-1",
            issue_type="duplicate_name",
            severity="high",
            status="open",
            device_id="device-1",
            name="Hallway Light",
            suggested_action="rename_device",
            metadata_json={"conflicting_device_ids": ["device-2"]},
            detected_at=now,
            updated_at=now,
        )
        session.add_all([device, issue])
        await session.commit()
        break

    yield

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_list_issues_returns_data(test_client):
    response = await test_client.get("/api/hygiene/issues")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["issues"][0]["issue_key"] == "duplicate_name:device-1"


@pytest.mark.asyncio
async def test_apply_action_uses_home_assistant_client(test_client):
    stub_client = StubHomeAssistantClient()

    async def fake_client_dependency():
        yield stub_client

    app.dependency_overrides[get_ha_client] = fake_client_dependency

    response = await test_client.post(
        "/api/hygiene/issues/duplicate_name:device-1/actions/apply",
        json={"action": "rename_device", "value": "Kitchen Main Light"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "resolved"
    # The rename must reach name_by_user -- a device's `name` is integration-owned.
    assert stub_client.devices[0]["name_by_user"] == "Kitchen Main Light"
    assert ("config/device_registry/update", {
        "device_id": "device-1",
        "name_by_user": "Kitchen Main Light",
    }) in stub_client.calls

    # Verify database updated
    async for session in get_db_session():
        result = await session.execute(
            select(DeviceHygieneIssue).where(
                DeviceHygieneIssue.issue_key == "duplicate_name:device-1"
            )
        )
        issue = result.scalar_one()
        assert issue.status == "resolved"
        break
