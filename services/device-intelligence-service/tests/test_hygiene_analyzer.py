"""Tests for DeviceHygieneAnalyzer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select

from src.clients.ha_client import HAArea, HADevice, HAEntity
from src.core.database import get_db_session
from src.models.database import DeviceHygieneIssue
from src.services.hygiene_analyzer import DeviceHygieneAnalyzer


def _area(area_id: str, name: str) -> HAArea:
    now = datetime.now(timezone.utc)
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
    now = datetime.now(timezone.utc)
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


def _entity(
    entity_id: str,
    device_id: str | None,
    *,
    disabled_by: str | None = None,
    entity_category: str | None = None,
) -> HAEntity:
    now = datetime.now(timezone.utc)
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
async def test_analyzer_generates_and_persists_findings(initialized_app):
    """Analyzer should flag duplicates, placeholders, missing areas, stale devices, and disabled entities."""

    living_room = _area("living_room", "Living Room")
    now = datetime.now(timezone.utc)

    devices = [
        _device("dev-1", "Lamp", name_by_user="Hallway Light", area_id="living_room"),
        _device("dev-2", "Lamp", name_by_user="Hallway Light", area_id="living_room"),
        _device("dev-3", "Device 101", name_by_user=None, area_id=None, suggested_area="living_room"),
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

    async for session in get_db_session():
        await session.execute(delete(DeviceHygieneIssue))
        await session.commit()

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
        assert {"duplicate_name", "placeholder_name", "missing_area", "pending_configuration", "disabled_entity"}.issubset(issue_types)
        break


@pytest.mark.asyncio
async def test_analyzer_marks_resolved_when_issue_disappears(initialized_app):
    living_room = _area("living_room", "Living Room")
    devices_initial = [
        _device("dev-1", "Lamp", name_by_user="Hallway Light", area_id="living_room"),
        _device("dev-2", "Lamp", name_by_user="Hallway Light", area_id="living_room"),
    ]
    entities = [_entity("light.hallway_light", "dev-1")]

    async for session in get_db_session():
        await session.execute(delete(DeviceHygieneIssue))
        await session.commit()

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

        stored = await session.execute(select(DeviceHygieneIssue).where(DeviceHygieneIssue.issue_key == "duplicate_name:dev-2"))
        issue = stored.scalar_one()
        assert issue.status == "resolved"
        break

