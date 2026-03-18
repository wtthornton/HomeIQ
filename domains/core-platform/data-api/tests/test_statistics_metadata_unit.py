"""Unit tests for StatisticsMetadataService — Story 85.2

Tests statistics eligibility logic and metadata sync with mocked DB sessions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.statistics_metadata import StatisticsMetadataService


class TestIsStatisticsEligible:

    @pytest.mark.asyncio
    async def test_eligible_when_meta_exists(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        assert await StatisticsMetadataService.is_statistics_eligible("sensor.temp", mock_session) is True

    @pytest.mark.asyncio
    async def test_not_eligible_when_no_meta(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        assert await StatisticsMetadataService.is_statistics_eligible("sensor.temp", mock_session) is False


class TestGetMetadata:

    @pytest.mark.asyncio
    async def test_returns_meta_when_exists(self):
        meta = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = meta
        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        result = await StatisticsMetadataService.get_metadata("sensor.temp", mock_session)
        assert result is meta

    @pytest.mark.asyncio
    async def test_returns_none_when_not_exists(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        result = await StatisticsMetadataService.get_metadata("sensor.temp", mock_session)
        assert result is None


class TestSyncMetadataFromEntity:
    """Test eligibility determination logic in sync_metadata_from_entity."""

    def _make_entity(self, entity_id="sensor.temp", domain="sensor", unit="°C"):
        entity = MagicMock()
        entity.entity_id = entity_id
        entity.domain = domain
        entity.unit_of_measurement = unit
        return entity

    @pytest.mark.asyncio
    async def test_measurement_state_class_eligible(self):
        entity = self._make_entity()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        result = await StatisticsMetadataService.sync_metadata_from_entity(
            entity, state_class="measurement", session=mock_session
        )
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_total_increasing_eligible(self):
        entity = self._make_entity()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        result = await StatisticsMetadataService.sync_metadata_from_entity(
            entity, state_class="total_increasing", session=mock_session
        )
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_total_eligible(self):
        entity = self._make_entity()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        result = await StatisticsMetadataService.sync_metadata_from_entity(
            entity, state_class="total", session=mock_session
        )
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_sensor_with_unit_fallback_eligible(self):
        """Sensor with unit_of_measurement but no state_class should still be eligible."""
        entity = self._make_entity(domain="sensor", unit="W")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        result = await StatisticsMetadataService.sync_metadata_from_entity(
            entity, state_class=None, session=mock_session
        )
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_eligible_returns_none(self):
        """Entity without state_class or unit is not eligible."""
        entity = self._make_entity(domain="automation", unit=None)
        mock_session = AsyncMock()

        result = await StatisticsMetadataService.sync_metadata_from_entity(
            entity, state_class=None, session=mock_session
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_updates_existing_metadata(self):
        entity = self._make_entity()
        existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        result = await StatisticsMetadataService.sync_metadata_from_entity(
            entity, state_class="measurement", session=mock_session
        )
        assert existing.state_class == "measurement"
        assert existing.has_mean is True
        mock_session.commit.assert_called_once()


class TestGetAllEligibleEntityIds:

    @pytest.mark.asyncio
    async def test_returns_entity_ids(self):
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("sensor.temp",), ("sensor.humidity",)]
        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        ids = await StatisticsMetadataService.get_all_eligible_entity_ids(mock_session)
        assert ids == ["sensor.temp", "sensor.humidity"]

    @pytest.mark.asyncio
    async def test_empty_when_none_eligible(self):
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        ids = await StatisticsMetadataService.get_all_eligible_entity_ids(mock_session)
        assert ids == []
