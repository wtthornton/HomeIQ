"""Tests for hygiene API router."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from src.api.hygiene_router import get_ha_client
from src.config import Settings
from src.core.database import get_db_session, initialize_database
from src.main import app
from src.models.database import Device, DeviceHygieneIssue


class StubHomeAssistantClient:
    def __init__(self):
        self.calls = []

    async def update_device_registry_entry(self, device_id: str, **fields):
        self.calls.append(("device_update", device_id, fields))
        return {"id": device_id, **fields}

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
    db_path = tmp_path_factory.mktemp("device-int-api") / "hygiene_api.db"
    settings = Settings(SQLITE_DATABASE_URL=f"sqlite+aiosqlite:///{db_path}")
    await initialize_database(settings)

    # Seed sample data
    now = datetime.now(timezone.utc)
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
    assert stub_client.calls[0][0] == "device_update"

    # Verify database updated
    async for session in get_db_session():
        result = await session.execute(
            select(DeviceHygieneIssue).where(DeviceHygieneIssue.issue_key == "duplicate_name:device-1")
        )
        issue = result.scalar_one()
        assert issue.status == "resolved"
        break

