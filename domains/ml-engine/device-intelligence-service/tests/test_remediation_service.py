"""Tests for DeviceHygieneRemediationService."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from homeiq_ha.client.errors import HACommandError
from homeiq_ha.registry_writer import UnknownTarget, WriteNotVerified
from sqlalchemy import delete
from src.config import Settings
from src.core.database import get_db_session, initialize_database
from src.models.database import Device, DeviceEntity, DeviceHygieneIssue
from src.services.remediation_service import DeviceHygieneRemediationService

#: What HA's config/device_registry/update command schema actually accepts. A
#: fake that echoed back any field handed to it is what let the `name=` rename
#: look like it worked -- real HA answers success: false for anything else.
_DEVICE_UPDATE_FIELDS = {"area_id", "disabled_by", "labels", "name_by_user"}


class FakeHaClient:
    """A registry just deep enough to answer HARegistryWriter's read-back."""

    def __init__(self, succeed: bool = True, *, drop_writes: bool = False):
        self.succeed = succeed
        self.drop_writes = drop_writes
        self.calls = []
        self.devices = [{"id": "device-1", "name": "Kitchen Light", "area_id": None}]
        self.areas = [{"area_id": "kitchen", "name": "Kitchen"}]

    async def send_command(self, command_type: str, *, fields=None, **payload):
        args = {**payload, **(fields or {})}
        self.calls.append((command_type, args))

        if command_type == "config/device_registry/list":
            return self.devices
        if command_type == "config/area_registry/list":
            return self.areas
        if command_type == "config/device_registry/update":
            if not self.succeed:
                raise RuntimeError("update failed")
            changes = {k: v for k, v in args.items() if k != "device_id"}
            if unknown := set(changes) - _DEVICE_UPDATE_FIELDS:
                raise HACommandError(command_type, "invalid_format", f"extra keys: {unknown}")
            if self.drop_writes:
                return {}
            entry = next(d for d in self.devices if d["id"] == args["device_id"])
            entry.update(changes)
            return entry
        raise AssertionError(f"unexpected command {command_type}")

    async def update_entity_registry_entry(self, entity_id: str, **fields):
        self.calls.append(("entity_update", entity_id, fields))
        if not self.succeed:
            raise RuntimeError("entity update failed")
        return {"entity_id": entity_id, **fields}

    async def start_config_flow(self, handler: str, data=None):
        self.calls.append(("config_flow", handler, data))
        if not self.succeed:
            raise RuntimeError("config flow failed")
        return {"handler": handler}


@pytest_asyncio.fixture
async def db_setup(tmp_path_factory):
    # Function-scoped to match pytest.ini's `asyncio_default_fixture_loop_scope
    # = function`: a module-scoped async fixture is created against a
    # module-scoped event loop runner, which pytest-asyncio then refuses to
    # hand to a function-scoped test (`ScopeMismatch`).
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)
    tmp_path_factory.mktemp("device-int") / "remediation.db"
    settings = Settings(DATABASE_URL="postgresql+asyncpg://homeiq:homeiq@localhost:5432/homeiq")
    await initialize_database(settings)

    # DeviceHygieneIssue.device_id is a real FK to devices.id. This module's
    # fixtures reference "device-1" -- own that row here rather than relying
    # on another test module (e.g. test_hygiene_router.py) to have left one
    # behind, which is exactly the kind of cross-file leak TAP-6308 flagged.
    async for session in get_db_session():
        session.add(Device(id="device-1", name="Kitchen Light", integration="hue"))
        await session.commit()
        break

    yield

    async for session in get_db_session():
        await session.execute(
            delete(DeviceHygieneIssue).where(DeviceHygieneIssue.device_id == "device-1")
        )
        await session.execute(delete(Device).where(Device.id == "device-1"))
        await session.commit()
        break


@pytest_asyncio.fixture
async def fresh_issue(db_setup):
    now = datetime.now(UTC)
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
        # issue.entity_id is a real FK to device_entities.entity_id; own the
        # row here rather than assigning an id nothing has inserted. Cascades
        # away with the "device-1" Device row db_setup tears down.
        session.add(
            DeviceEntity(
                entity_id="light.kitchen",
                device_id="device-1",
                platform="hue",
                domain="light",
                unique_id="uid-light.kitchen",
            )
        )
        await session.commit()

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


# -- Registry-gateway behaviour, without a database -------------------------
#
# The cases above need Postgres to build a DeviceHygieneIssue. These use a stand-in
# so the Home Assistant side stays covered wherever the suite runs.


class _Issue:
    def __init__(self) -> None:
        self.device_id = "device-1"
        self.entity_id = None
        self.status = "open"
        self.metadata_json: dict = {}
        self.updated_at = None
        self.resolved_at = None


class _Session:
    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:  # pragma: no cover - SQLAlchemy errors only
        pass


@pytest.mark.asyncio
async def test_rename_writes_name_by_user_and_leaves_the_integration_name():
    ha = FakeHaClient()
    issue = _Issue()

    assert (
        await DeviceHygieneRemediationService(ha, _Session()).apply_action(
            issue, "rename_device", "Kitchen Main Light"
        )
        is True
    )
    assert ha.devices[0]["name_by_user"] == "Kitchen Main Light"
    assert ha.devices[0]["name"] == "Kitchen Light"  # integration-owned, untouched


@pytest.mark.asyncio
async def test_a_rename_that_does_not_land_leaves_the_issue_open():
    ha = FakeHaClient(drop_writes=True)
    issue = _Issue()

    with pytest.raises(WriteNotVerified):
        await DeviceHygieneRemediationService(ha, _Session()).apply_action(
            issue, "rename_device", "Kitchen Main Light"
        )
    assert issue.status == "open"


@pytest.mark.asyncio
async def test_assign_area_refuses_an_area_that_does_not_exist():
    ha = FakeHaClient()
    issue = _Issue()
    service = DeviceHygieneRemediationService(ha, _Session())

    assert await service.apply_action(issue, "assign_area", "kitchen") is True
    assert ha.devices[0]["area_id"] == "kitchen"

    issue.status = "open"
    with pytest.raises(UnknownTarget):
        await service.apply_action(issue, "assign_area", "attic")
    assert issue.status == "open"
