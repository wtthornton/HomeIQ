"""Tests for DeviceHygieneAnalyzer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from src.clients.ha_client import HAArea, HADevice, HAEntity
from src.config import Settings
from src.core.database import get_db_session, initialize_database
from src.models.database import Device, DeviceEntity, DeviceHygieneIssue
from src.services.hygiene_analyzer import DeviceHygieneAnalyzer

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def _initialized_app():
    """Initialize the database connection this module's tests read/write
    through. Named `_initialized_app` to match the fixture these tests were
    already written against -- no FastAPI app is actually needed since the
    analyzer is exercised directly against a session, not over HTTP."""
    await initialize_database(Settings())
    yield


def _area(area_id: str, name: str) -> HAArea:
    now = datetime.now(UTC)
    return HAArea(
        area_id=area_id,
        name=name,
        normalized_name=name.lower().replace(" ", "_"),
        aliases=[],
        created_at=now,
        updated_at=now,
    )


def _device(
    device_id: str,
    name: str,
    *,
    name_by_user: str | None = None,
    area_id: str | None = None,
    suggested_area: str | None = None,
    integration: str = "hue",
    config_entries: list[str] | None = None,
    created_at: datetime | None = None,
    disabled_by: str | None = None,
) -> HADevice:
    now = datetime.now(UTC)
    return HADevice(
        id=device_id,
        name=name,
        name_by_user=name_by_user,
        manufacturer="Signify",
        model="Hue",
        area_id=area_id,
        suggested_area=suggested_area,
        integration=integration,
        entry_type=None,
        configuration_url=None,
        config_entries=config_entries if config_entries is not None else ["hue_bridge"],
        identifiers=[[integration, device_id]],
        connections=[],
        sw_version="1.0",
        hw_version=None,
        via_device_id=None,
        disabled_by=disabled_by,
        created_at=created_at or now,
        updated_at=now,
    )


async def _seed_devices(session: AsyncSession, devices: list[HADevice]) -> None:
    """Insert a Device row per HADevice so device_hygiene_issues.device_id can
    satisfy its foreign key. The analyzer only reads HADevice/HAEntity value
    objects -- it never sees these rows -- but persisting a
    DeviceHygieneIssue for a device the `devices` table has never heard of is
    a real FK violation, not a mock-vs-real-DB mismatch.
    """
    for device in devices:
        session.add(
            Device(
                id=device.id,
                name=device.name,
                manufacturer=device.manufacturer,
                model=device.model,
                area_id=device.area_id,
                integration=device.integration,
            )
        )
    await session.commit()


async def _seed_entities(session: AsyncSession, entities: list[HAEntity]) -> None:
    """Insert a DeviceEntity row per HAEntity so device_hygiene_issues.entity_id
    can satisfy its foreign key (the disabled_entity finding stores it)."""
    for entity in entities:
        session.add(
            DeviceEntity(
                entity_id=entity.entity_id,
                device_id=entity.device_id,
                name=entity.name,
                original_name=entity.original_name,
                platform=entity.platform,
                domain=entity.domain,
                disabled_by=entity.disabled_by,
                entity_category=entity.entity_category,
                has_entity_name=entity.has_entity_name,
                unique_id=entity.unique_id,
            )
        )
    await session.commit()


def _entity(
    entity_id: str,
    device_id: str | None,
    *,
    disabled_by: str | None = None,
    entity_category: str | None = None,
) -> HAEntity:
    now = datetime.now(UTC)
    return HAEntity(
        entity_id=entity_id,
        name=None,
        original_name=entity_id,
        device_id=device_id,
        area_id=None,
        platform="hue",
        domain=entity_id.split(".")[0],
        disabled_by=disabled_by,
        entity_category=entity_category,
        hidden_by=None,
        has_entity_name=False,
        original_icon=None,
        unique_id=f"uid-{entity_id}",
        translation_key=None,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_analyzer_generates_and_persists_findings(_initialized_app):
    """Analyzer should flag duplicates, placeholders, missing areas, stale devices, and disabled entities."""

    living_room = _area("living_room", "Living Room")
    now = datetime.now(UTC)

    devices = [
        _device("dev-1", "Lamp", name_by_user="Hallway Light", area_id="living_room"),
        _device("dev-2", "Lamp", name_by_user="Hallway Light", area_id="living_room"),
        _device(
            "dev-3", "Device 101", name_by_user=None, area_id=None, suggested_area="living_room"
        ),
        _device(
            "dev-4",
            "Garage Sensor",
            area_id=None,
            config_entries=[],
            created_at=now - timedelta(days=45),
            integration="zha",
        ),
    ]

    entities = [
        _entity("light.hallway_light", "dev-1"),
        _entity("light.hallway_light_aux", "dev-2"),
        _entity("binary_sensor.placeholder_motion", "dev-3", disabled_by="user"),
    ]

    device_ids = [d.id for d in devices]
    entity_ids = [e.entity_id for e in entities]
    async for session in get_db_session():
        await session.execute(delete(DeviceHygieneIssue))
        await session.execute(delete(DeviceEntity).where(DeviceEntity.entity_id.in_(entity_ids)))
        await session.execute(delete(Device).where(Device.id.in_(device_ids)))
        await _seed_devices(session, devices)
        await _seed_entities(session, entities)

        analyzer = DeviceHygieneAnalyzer(session)
        findings = await analyzer.analyze(devices, entities, [living_room])

        assert any(f.issue_type == "duplicate_name" for f in findings)
        assert any(f.issue_type == "placeholder_name" for f in findings)
        assert any(f.issue_type == "missing_area" for f in findings)
        assert any(f.issue_type == "pending_configuration" for f in findings)
        assert any(f.issue_type == "disabled_entity" for f in findings)

        stored = await session.execute(select(DeviceHygieneIssue))
        issues = stored.scalars().all()
        issue_types = {issue.issue_type for issue in issues}
        assert {
            "duplicate_name",
            "placeholder_name",
            "missing_area",
            "pending_configuration",
            "disabled_entity",
        }.issubset(issue_types)

        # This table has no per-test namespacing (issue_key is the only
        # uniqueness), so a row left behind here would inflate the row count
        # test_hygiene_router.py's test_list_issues_returns_data asserts on
        # when the whole suite runs in one process.
        await session.execute(delete(DeviceHygieneIssue))
        await session.execute(delete(DeviceEntity).where(DeviceEntity.entity_id.in_(entity_ids)))
        await session.execute(delete(Device).where(Device.id.in_(device_ids)))
        await session.commit()
        break


@pytest.mark.asyncio
async def test_analyzer_marks_resolved_when_issue_disappears(_initialized_app):
    living_room = _area("living_room", "Living Room")
    devices_initial = [
        _device("dev-1", "Lamp", name_by_user="Hallway Light", area_id="living_room"),
        _device("dev-2", "Lamp", name_by_user="Hallway Light", area_id="living_room"),
    ]
    entities = [_entity("light.hallway_light", "dev-1")]

    device_ids = [d.id for d in devices_initial]
    async for session in get_db_session():
        await session.execute(delete(DeviceHygieneIssue))
        await session.execute(delete(Device).where(Device.id.in_(device_ids)))
        await _seed_devices(session, devices_initial)

        analyzer = DeviceHygieneAnalyzer(session)
        await analyzer.analyze(devices_initial, entities, [living_room])
        break

    # Rename device to remove duplicate condition
    devices_updated = [
        _device("dev-1", "Lamp", name_by_user="Hallway Light", area_id="living_room"),
        _device("dev-2", "Lamp", name_by_user="Landing Light", area_id="living_room"),
    ]

    async for session in get_db_session():
        analyzer = DeviceHygieneAnalyzer(session)
        await analyzer.analyze(devices_updated, entities, [living_room])

        stored = await session.execute(
            select(DeviceHygieneIssue).where(DeviceHygieneIssue.issue_key == "duplicate_name:dev-2")
        )
        issue = stored.scalar_one()
        assert issue.status == "resolved"

        # See the comment in test_analyzer_generates_and_persists_findings:
        # this table has no per-test namespacing.
        await session.execute(delete(DeviceHygieneIssue))
        await session.execute(delete(Device).where(Device.id.in_(device_ids)))
        await session.commit()
        break
