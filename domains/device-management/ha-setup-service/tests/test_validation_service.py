"""
Unit tests for Validation Service
Epic 32: Home Assistant Configuration Validation & Suggestions
"""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from src.validation_service import (
    AreaReassignRefused,
    ValidationIssue,
    ValidationService,
)


class FakeHAConnection:
    """Just enough of the WS command surface for apply_fix and the gateway."""

    def __init__(
        self,
        entities: dict[str, dict],
        areas: list[str],
        devices: list[dict] | None = None,
    ):
        self.entities = entities
        self.areas = areas
        self.devices = devices or []
        self.update_calls: list[dict] = []

    async def send_command(self, command_type: str, fields: dict | None = None) -> Any:
        fields = fields or {}
        if command_type == "config/entity_registry/get":
            return dict(self.entities.get(fields["entity_id"], {}))
        if command_type == "config/entity_registry/update":
            self.update_calls.append(fields)
            entry = self.entities[fields["entity_id"]]
            entry.update({k: v for k, v in fields.items() if k != "entity_id"})
            return dict(entry)
        if command_type == "config/device_registry/list":
            return [dict(d) for d in self.devices]
        if command_type == "config/area_registry/list":
            return [{"area_id": a} for a in self.areas]
        raise AssertionError(f"unexpected command {command_type}")


@pytest.fixture
def validation_service():
    return ValidationService()


@pytest.fixture
def mock_entities():
    return [
        {
            "entity_id": "light.hue_office_back_left",
            "name": "Hue Office Back Left",
            "area_id": None,
            "device_id": "device123",
        },
        {
            "entity_id": "light.living_room_2",
            "name": "Living Room 2",
            "area_id": "living_room",
            "device_id": "device456",
        },
        {
            "entity_id": "light.kitchen_main",
            "name": "Kitchen Main",
            "area_id": None,
            "device_id": "device789",
        },
    ]


@pytest.fixture
def mock_areas():
    return [
        {"area_id": "office", "name": "Office"},
        {"area_id": "living_room", "name": "Living Room"},
        {"area_id": "kitchen", "name": "Kitchen"},
    ]


@pytest.mark.asyncio
async def test_detect_missing_area_assignments(validation_service, mock_entities, mock_areas):
    """Test detection of missing area assignments"""
    issues = await validation_service._detect_issues(mock_entities, mock_areas)

    # Should detect issues for entities without area_id
    missing_area_issues = [i for i in issues if i.category == "missing_area_assignment"]
    assert len(missing_area_issues) >= 2  # office and kitchen lights

    # Check that suggestions are provided
    for issue in missing_area_issues:
        assert len(issue.suggestions) > 0
        assert issue.confidence > 0


@pytest.mark.asyncio
async def test_detect_name_area_mismatches(validation_service, mock_areas):
    """Test detection of incorrect area assignments"""
    # Create entity with incorrect area
    entities_with_incorrect = [
        {
            "entity_id": "light.office_desk",
            "name": "Office Desk Light",
            "area_id": "living_room",  # Incorrect!
            "device_id": "device123",
        }
    ]

    issues = await validation_service._detect_issues(entities_with_incorrect, mock_areas)

    incorrect_issues = [i for i in issues if i.category == "name_area_mismatch"]
    # A human-assigned area that disagrees with the top name-derived suggestion
    # MUST surface as a report (and only as a report) -- a silent zero here
    # would mean the mismatch detector regressed.
    assert len(incorrect_issues) == 1
    assert incorrect_issues[0].current_area == "living_room"
    assert len(incorrect_issues[0].suggestions) > 0


@pytest.mark.asyncio
async def test_detect_name_area_mismatch_for_device_inherited_area(
    validation_service, mock_areas
):
    """Most entities carry no area override — their area comes from the device.

    The swapped-dimmer defect that motivated TAP-6228 was exactly this shape:
    a device-level area and a misleading entity name. Detection must resolve
    the EFFECTIVE area, or the mismatch report is blind to the majority case
    (and proposes the entity as 'missing' instead).
    """
    entities = [
        {
            "entity_id": "light.office_desk",
            "name": "Office Desk Light",
            "area_id": None,  # no entity-level override
            "device_id": "dev1",
        }
    ]

    issues = await validation_service._detect_issues(
        entities, mock_areas, device_areas={"dev1": "living_room"}
    )

    assert [i.category for i in issues] == ["name_area_mismatch"]
    assert issues[0].current_area == "living_room"  # the effective area, for the UI


@pytest.mark.asyncio
async def test_apply_fix_refuses_a_device_inherited_area_without_opt_in(
    validation_service,
):
    """Writing an entity area overrides the device's — that is a reassign too."""
    conn = FakeHAConnection(
        entities={
            "light.office_desk": {
                "entity_id": "light.office_desk",
                "area_id": None,
                "device_id": "dev1",
            }
        },
        areas=["office", "living_room"],
        devices=[{"id": "dev1", "area_id": "living_room"}],
    )
    with patch.object(validation_service, "_connection", new=AsyncMock(return_value=conn)):
        with pytest.raises(AreaReassignRefused, match="living_room"):
            await validation_service.apply_fix("light.office_desk", "office")

    assert conn.update_calls == []


@pytest.mark.asyncio
async def test_apply_fix_refuses_to_overwrite_an_assigned_area(validation_service):
    """An already-assigned area is never changed without explicit opt-in (TAP-6228)."""
    conn = FakeHAConnection(
        entities={
            "light.office_desk": {
                "entity_id": "light.office_desk",
                "area_id": "living_room",
                "device_id": "dev1",
            }
        },
        areas=["office", "living_room"],
    )
    with patch.object(validation_service, "_connection", new=AsyncMock(return_value=conn)):
        with pytest.raises(AreaReassignRefused, match="allow_reassign"):
            await validation_service.apply_fix("light.office_desk", "office")

    assert conn.update_calls == []  # refused before any write reached HA


@pytest.mark.asyncio
async def test_apply_fix_reassigns_only_with_explicit_opt_in(validation_service):
    conn = FakeHAConnection(
        entities={
            "light.office_desk": {
                "entity_id": "light.office_desk",
                "area_id": "living_room",
                "device_id": "dev1",
            }
        },
        areas=["office", "living_room"],
    )
    with patch.object(validation_service, "_connection", new=AsyncMock(return_value=conn)):
        result = await validation_service.apply_fix(
            "light.office_desk", "office", allow_reassign=True
        )

    assert result["success"] is True
    assert result["previous_area_id"] == "living_room"
    assert conn.entities["light.office_desk"]["area_id"] == "office"


@pytest.mark.asyncio
async def test_bulk_apply_has_no_bulk_level_reassign_override(validation_service):
    """Each bulk item needs its own allow_reassign; one item's flag frees only itself."""
    conn = FakeHAConnection(
        entities={
            "light.a": {"entity_id": "light.a", "area_id": "living_room", "device_id": "d1"},
            "light.b": {"entity_id": "light.b", "area_id": "living_room", "device_id": "d2"},
            "light.c": {"entity_id": "light.c", "area_id": None, "device_id": None},
        },
        areas=["office", "living_room"],
    )
    with patch.object(validation_service, "_connection", new=AsyncMock(return_value=conn)):
        result = await validation_service.apply_bulk_fixes(
            [
                {"entity_id": "light.a", "area_id": "office"},
                {"entity_id": "light.b", "area_id": "office", "allow_reassign": True},
                {"entity_id": "light.c", "area_id": "office"},  # first-time fill: allowed
            ]
        )

    by_id = {r["entity_id"]: r for r in result["results"]}
    assert by_id["light.a"]["success"] is False
    assert by_id["light.a"]["refused"] is True
    assert by_id["light.b"]["success"] is True
    assert by_id["light.c"]["success"] is True
    assert conn.entities["light.a"]["area_id"] == "living_room"  # untouched
    assert conn.entities["light.b"]["area_id"] == "office"
    assert conn.entities["light.c"]["area_id"] == "office"


@pytest.mark.asyncio
async def test_generate_summary(validation_service):
    """Test summary generation"""
    issues = [
        ValidationIssue(
            entity_id="light.test1",
            category="missing_area_assignment",
            current_area=None,
            suggestions=[],
            confidence=80.0,
        ),
        ValidationIssue(
            entity_id="light.test2",
            category="missing_area_assignment",
            current_area=None,
            suggestions=[],
            confidence=90.0,
        ),
        ValidationIssue(
            entity_id="light.test3",
            category="name_area_mismatch",
            current_area="wrong",
            suggestions=[],
            confidence=85.0,
        ),
    ]

    summary = validation_service._generate_summary(issues, "2025.10.0")

    assert summary.total_issues == 3
    assert summary.by_category["missing_area_assignment"] == 2
    assert summary.by_category["name_area_mismatch"] == 1
    assert summary.ha_version == "2025.10.0"


@pytest.mark.asyncio
async def test_filter_by_category(validation_service):
    """Test filtering by category"""
    # Mock fetch_ha_data
    with patch.object(validation_service, "_fetch_ha_data", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = ([], [], {}, None)

        # Mock _detect_issues to return test issues
        with patch.object(
            validation_service, "_detect_issues", new_callable=AsyncMock
        ) as mock_detect:
            mock_detect.return_value = [
                ValidationIssue(
                    entity_id="light.test1",
                    category="missing_area_assignment",
                    current_area=None,
                    suggestions=[],
                    confidence=80.0,
                ),
                ValidationIssue(
                    entity_id="light.test2",
                    category="name_area_mismatch",
                    current_area="wrong",
                    suggestions=[],
                    confidence=90.0,
                ),
            ]

            result = await validation_service.validate_ha_config(category="missing_area_assignment")

            assert len(result.issues) == 1
            assert result.issues[0].category == "missing_area_assignment"


@pytest.mark.asyncio
async def test_filter_by_confidence(validation_service):
    """Test filtering by minimum confidence"""
    with patch.object(validation_service, "_fetch_ha_data", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = ([], [], {}, None)

        with patch.object(
            validation_service, "_detect_issues", new_callable=AsyncMock
        ) as mock_detect:
            mock_detect.return_value = [
                ValidationIssue(
                    entity_id="light.test1",
                    category="missing_area_assignment",
                    current_area=None,
                    suggestions=[{"confidence": 95}],
                    confidence=95.0,
                ),
                ValidationIssue(
                    entity_id="light.test2",
                    category="missing_area_assignment",
                    current_area=None,
                    suggestions=[{"confidence": 50}],
                    confidence=50.0,
                ),
            ]

            result = await validation_service.validate_ha_config(min_confidence=80)

            assert len(result.issues) == 1
            assert result.issues[0].confidence >= 80


@pytest.mark.asyncio
async def test_cache_functionality(validation_service):
    """Test caching of validation results"""
    with patch.object(validation_service, "_fetch_ha_data", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = ([], [], {}, None)

        with patch.object(
            validation_service, "_detect_issues", new_callable=AsyncMock
        ) as mock_detect:
            mock_detect.return_value = []

            # First call should fetch data
            await validation_service.validate_ha_config(use_cache=True)
            assert mock_fetch.call_count == 1

            # Second call should use cache
            await validation_service.validate_ha_config(use_cache=True)
            assert mock_fetch.call_count == 1  # Should not call again

            # Clear cache and call again
            validation_service.clear_cache()
            await validation_service.validate_ha_config(use_cache=True)
            assert mock_fetch.call_count == 2  # Should call again
