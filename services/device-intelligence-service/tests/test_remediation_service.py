"""Tests for DeviceHygieneRemediationService."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from src.config import Settings
from src.core.database import get_db_session, initialize_database
from src.models.database import DeviceHygieneIssue
from src.services.remediation_service import DeviceHygieneRemediationService


class FakeHaClient:
    def __init__(self, succeed: bool = True):
        self.succeed = succeed
        self.calls = []

    async def update_device_registry_entry(self, device_id: str, **fields):
        self.calls.append(("device_update", device_id, fields))
        if not self.succeed:
            msg = "update failed"
            raise RuntimeError(msg)
        return {"id": device_id, **fields}

    async def update_entity_registry_entry(self, entity_id: str, **fields):
        self.calls.append(("entity_update", entity_id, fields))
        if not self.succeed:
            msg = "entity update failed"
            raise RuntimeError(msg)
        return {"entity_id": entity_id, **fields}

    async def start_config_flow(self, handler: str, data=None):
        self.calls.append(("config_flow", handler, data))
        if not self.succeed:
            msg = "config flow failed"
            raise RuntimeError(msg)
        return {"handler": handler}


@pytest_asyncio.fixture(scope="module")
async def db_setup(tmp_path_factory):
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)
    db_path = tmp_path_factory.mktemp("device-int") / "remediation.db"
    settings = Settings(SQLITE_DATABASE_URL=f"sqlite+aiosqlite:///{db_path}")
    await initialize_database(settings)
    yield


@pytest_asyncio.fixture
async def fresh_issue(db_setup):
    now = datetime.now(timezone.utc)
    async for session in get_db_session():
        issue = DeviceHygieneIssue(
            issue_key="duplicate_name:test",
            issue_type="duplicate_name",
            severity="high",
            status="open",
            device_id="device-1",
            name="Old Name",
            suggested_action="rename_device",
            metadata_json={},
            detected_at=now,
            updated_at=now,
        )
        session.add(issue)
        await session.commit()
        await session.refresh(issue)
        yield issue.id
        # cleanup
        await session.delete(issue)
        await session.commit()
        break


@pytest.mark.asyncio
async def test_rename_device_marks_issue_resolved(fresh_issue):
    fake_client = FakeHaClient()
    async for session in get_db_session():
        issue = await session.get(DeviceHygieneIssue, fresh_issue)
        service = DeviceHygieneRemediationService(fake_client, session)
        result = await service.apply_action(issue, "rename_device", "Kitchen Light")
        assert result is True
        await session.refresh(issue)
        assert issue.status == "resolved"
        assert issue.metadata_json["applied_value"] == "Kitchen Light"
        break


@pytest.mark.asyncio
async def test_assign_area_requires_device_id(fresh_issue):
    fake_client = FakeHaClient()
    async for session in get_db_session():
        issue = await session.get(DeviceHygieneIssue, fresh_issue)
        issue.device_id = None
        service = DeviceHygieneRemediationService(fake_client, session)
        result = await service.apply_action(issue, "assign_area", "kitchen")
        assert result is False
        break


@pytest.mark.asyncio
async def test_enable_entity_updates_status(fresh_issue):
    fake_client = FakeHaClient()
    async for session in get_db_session():
        issue = await session.get(DeviceHygieneIssue, fresh_issue)
        issue.entity_id = "light.kitchen"
        issue.status = "open"
        issue.metadata_json = {}
        service = DeviceHygieneRemediationService(fake_client, session)
        result = await service.apply_action(issue, "review_entity_state")
        assert result is True
        await session.refresh(issue)
        assert issue.status == "resolved"
        break


@pytest.mark.asyncio
async def test_remediation_failure_rolls_back(fresh_issue):
    fake_client = FakeHaClient(succeed=False)
    async for session in get_db_session():
        issue = await session.get(DeviceHygieneIssue, fresh_issue)
        service = DeviceHygieneRemediationService(fake_client, session)
        with pytest.raises(RuntimeError):
            await service.apply_action(issue, "rename_device", "Office")
        await session.refresh(issue)
        assert issue.status == "open"
        break

