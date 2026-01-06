"""
Unit tests for pattern-to-synergy conversion functionality

Tests the detect_synergies_from_patterns method in DeviceSynergyDetector.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from src.synergy_detection.synergy_detector import DeviceSynergyDetector


class TestPatternToSynergyConversion:
    """Test suite for pattern-to-synergy conversion."""
    
    @pytest.fixture
    def mock_data_api_client(self):
        """Create mock data-api client."""
        client = AsyncMock()
        client.fetch_devices = AsyncMock(return_value=[])
        client.fetch_entities = AsyncMock(return_value=[])
        return client
    
    @pytest.fixture
    def mock_ha_client(self):
        """Create mock Home Assistant client."""
        client = AsyncMock()
        client.get_automations = AsyncMock(return_value=[])
        return client
    
    @pytest.fixture
    def mock_influxdb_client(self):
        """Create mock InfluxDB client."""
        return MagicMock()
    
    @pytest.fixture
    def detector(
        self,
        mock_data_api_client,
        mock_ha_client,
        mock_influxdb_client
    ):
        """Create DeviceSynergyDetector instance for testing."""
        return DeviceSynergyDetector(
            data_api_client=mock_data_api_client,
            ha_client=mock_ha_client,
            influxdb_client=mock_influxdb_client,
            min_confidence=0.7,
            same_area_required=True
        )
    
    @pytest.fixture
    def sample_co_occurrence_pattern(self) -> dict[str, Any]:
        """Sample co-occurrence pattern for testing."""
        return {
            'id': 1,
            'pattern_type': 'co_occurrence',
            'device_id': 'binary_sensor.motion+light.kitchen',
            'pattern_metadata': {
                'device1': 'binary_sensor.motion',
                'device2': 'light.kitchen',
                'confidence': 0.85
            },
            'confidence': 0.85,
            'occurrences': 50
        }
    
    @pytest.fixture
    def sample_time_patterns(self) -> list[dict[str, Any]]:
        """Sample time-of-day patterns for testing."""
        return [
            {
                'id': 2,
                'pattern_type': 'time_of_day',
                'device_id': 'light.bedroom',
                'pattern_metadata': {
                    'hour': 7,
                    'minute': 0
                },
                'confidence': 0.9,
                'occurrences': 30
            },
            {
                'id': 3,
                'pattern_type': 'time_of_day',
                'device_id': 'climate.bedroom',
                'pattern_metadata': {
                    'hour': 7,
                    'minute': 0
                },
                'confidence': 0.85,
                'occurrences': 25
            }
        ]
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_detect_synergies_from_co_occurrence_patterns(
        self,
        detector: DeviceSynergyDetector,
        sample_co_occurrence_pattern: dict[str, Any]
    ):
        """Test generating synergies from co-occurrence patterns."""
        patterns = [sample_co_occurrence_pattern]
        
        # Execute
        synergies = await detector.detect_synergies_from_patterns(patterns)
        
        # Verify
        assert len(synergies) == 1
        synergy = synergies[0]
        assert synergy['synergy_type'] == 'device_pair'
        assert synergy['devices'] == ['binary_sensor.motion', 'light.kitchen']
        assert synergy['trigger_entity'] == 'binary_sensor.motion'
        assert synergy['action_entity'] == 'light.kitchen'
        assert synergy['confidence'] == 0.85
        assert synergy['pattern_support_score'] == 1.0
        assert synergy['validated_by_patterns'] is True
        assert synergy['supporting_pattern_ids'] == [1]
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_detect_synergies_from_time_patterns(
        self,
        detector: DeviceSynergyDetector,
        sample_time_patterns: list[dict[str, Any]]
    ):
        """Test generating schedule-based synergies from time-of-day patterns."""
        # Execute
        synergies = await detector.detect_synergies_from_patterns(sample_time_patterns)
        
        # Verify
        assert len(synergies) == 1
        synergy = synergies[0]
        assert synergy['synergy_type'] == 'schedule_based'
        assert 'light.bedroom' in synergy['devices']
        assert 'climate.bedroom' in synergy['devices']
        assert synergy['pattern_support_score'] == 1.0
        assert synergy['validated_by_patterns'] is True
        assert len(synergy['supporting_pattern_ids']) == 2
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_detect_synergies_from_mixed_patterns(
        self,
        detector: DeviceSynergyDetector,
        sample_co_occurrence_pattern: dict[str, Any],
        sample_time_patterns: list[dict[str, Any]]
    ):
        """Test generating synergies from mixed pattern types."""
        patterns = [sample_co_occurrence_pattern] + sample_time_patterns
        
        # Execute
        synergies = await detector.detect_synergies_from_patterns(patterns)
        
        # Verify
        assert len(synergies) >= 2  # At least co-occurrence + schedule-based
        co_occurrence_synergies = [s for s in synergies if s['synergy_type'] == 'device_pair']
        schedule_synergies = [s for s in synergies if s['synergy_type'] == 'schedule_based']
        
        assert len(co_occurrence_synergies) == 1
        assert len(schedule_synergies) == 1
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_pattern_to_synergy_conversion(
        self,
        detector: DeviceSynergyDetector,
        sample_co_occurrence_pattern: dict[str, Any]
    ):
        """Test _pattern_to_synergy helper method."""
        # Execute
        synergy = detector._pattern_to_synergy(sample_co_occurrence_pattern)
        
        # Verify
        assert synergy is not None
        assert synergy['synergy_type'] == 'device_pair'
        assert synergy['devices'] == ['binary_sensor.motion', 'light.kitchen']
        assert synergy['confidence'] == 0.85
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_pattern_to_synergy_invalid_pattern(
        self,
        detector: DeviceSynergyDetector
    ):
        """Test _pattern_to_synergy with invalid pattern type."""
        invalid_pattern = {
            'pattern_type': 'time_of_day',  # Not co_occurrence
            'device_id': 'light.kitchen',
            'confidence': 0.8
        }
        
        # Execute
        synergy = detector._pattern_to_synergy(invalid_pattern)
        
        # Verify
        assert synergy is None
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_pattern_to_synergy_missing_devices(
        self,
        detector: DeviceSynergyDetector
    ):
        """Test _pattern_to_synergy with pattern missing device information."""
        invalid_pattern = {
            'pattern_type': 'co_occurrence',
            'device_id': '',  # Empty device_id
            'pattern_metadata': {},
            'confidence': 0.8
        }
        
        # Execute
        synergy = detector._pattern_to_synergy(invalid_pattern)
        
        # Verify
        assert synergy is None
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_detect_synergies_from_empty_patterns(
        self,
        detector: DeviceSynergyDetector
    ):
        """Test generating synergies from empty pattern list."""
        # Execute
        synergies = await detector.detect_synergies_from_patterns([])
        
        # Verify
        assert len(synergies) == 0
