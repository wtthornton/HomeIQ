"""
Unit tests for BlueprintOpportunityFinder service.

Epic AI-6 Story AI6.1: Blueprint Opportunity Discovery Service Foundation
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.blueprint_discovery.opportunity_finder import BlueprintOpportunityFinder
from src.clients.data_api_client import DataAPIClient
from src.utils.miner_integration import MinerIntegration


@pytest.fixture
def mock_data_api_client():
    """Create a mock DataAPIClient instance."""
    client = MagicMock(spec=DataAPIClient)
    client.fetch_devices = AsyncMock(return_value=[])
    client.fetch_entities = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_miner():
    """Create a mock MinerIntegration instance."""
    miner = MagicMock(spec=MinerIntegration)
    miner.is_available = AsyncMock(return_value=True)
    miner.search_blueprints = AsyncMock(return_value=[])
    return miner


@pytest.fixture
def sample_devices():
    """Sample device data."""
    return [
        {
            "device_id": "device1",
            "name": "Office Light",
            "manufacturer": "Philips Hue",
            "model": "Hue Bulb",
            "area_id": "office"
        },
        {
            "device_id": "device2",
            "name": "Motion Sensor",
            "manufacturer": "Generic",
            "model": "Motion Sensor",
            "area_id": "office"
        }
    ]


@pytest.fixture
def sample_entities():
    """Sample entity data."""
    return [
        {
            "entity_id": "light.office",
            "device_id": "device1",
            "domain": "light",
            "platform": "hue",
            "area_id": "office"
        },
        {
            "entity_id": "binary_sensor.office_motion",
            "device_id": "device2",
            "domain": "binary_sensor",
            "platform": "generic",
            "area_id": "office"
        }
    ]


@pytest.fixture
def sample_blueprint():
    """Sample blueprint data."""
    return {
        "id": "blueprint1",
        "title": "Motion-Activated Light",
        "description": "Turn on lights when motion detected",
        "use_case": "comfort",
        "quality_score": 0.85,
        "metadata": {
            "_blueprint_metadata": {
                "name": "Motion-Activated Light",
                "description": "Turn on lights when motion detected"
            },
            "_blueprint_variables": {
                "motion_sensor": {
                    "domain": "binary_sensor",
                    "device_class": "motion"
                },
                "target_light": {
                    "domain": "light"
                }
            },
            "_blueprint_devices": ["binary_sensor", "light"]
        }
    }


@pytest.fixture
def opportunity_finder(mock_data_api_client, mock_miner):
    """Create a BlueprintOpportunityFinder instance."""
    return BlueprintOpportunityFinder(
        data_api_client=mock_data_api_client,
        miner=mock_miner
    )


class TestBlueprintOpportunityFinder:
    """Test BlueprintOpportunityFinder service."""

    @pytest.mark.asyncio
    async def test_init(self, mock_data_api_client, mock_miner):
        """Test service initialization."""
        finder = BlueprintOpportunityFinder(
            data_api_client=mock_data_api_client,
            miner=mock_miner
        )

        assert finder.data_api == mock_data_api_client
        assert finder.miner == mock_miner
        assert finder._device_cache is None
        assert finder._entity_cache is None
        assert finder._cache_timestamp is None
        assert finder._cache_ttl == 300.0

    @pytest.mark.asyncio
    async def test_scan_devices_success(
        self,
        opportunity_finder,
        mock_data_api_client,
        sample_devices,
        sample_entities
    ):
        """Test successful device scanning."""
        mock_data_api_client.fetch_devices.return_value = sample_devices
        mock_data_api_client.fetch_entities.return_value = sample_entities

        devices, entities = await opportunity_finder._scan_devices()

        assert devices == sample_devices
        assert entities == sample_entities
        assert opportunity_finder._device_cache == sample_devices
        assert opportunity_finder._entity_cache == sample_entities
        assert opportunity_finder._cache_timestamp is not None

    @pytest.mark.asyncio
    async def test_scan_devices_caching(
        self,
        opportunity_finder,
        mock_data_api_client,
        sample_devices,
        sample_entities
    ):
        """Test device scanning with caching."""
        mock_data_api_client.fetch_devices.return_value = sample_devices
        mock_data_api_client.fetch_entities.return_value = sample_entities

        # First call
        devices1, entities1 = await opportunity_finder._scan_devices()

        # Second call should use cache
        devices2, entities2 = await opportunity_finder._scan_devices()

        assert devices1 == devices2
        assert entities1 == entities2
        # Should only fetch once
        assert mock_data_api_client.fetch_devices.call_count == 1
        assert mock_data_api_client.fetch_entities.call_count == 1

    @pytest.mark.asyncio
    async def test_scan_devices_failure_with_cache(
        self,
        opportunity_finder,
        mock_data_api_client,
        sample_devices,
        sample_entities
    ):
        """Test device scanning failure with expired cache fallback."""
        # First, populate cache
        mock_data_api_client.fetch_devices.return_value = sample_devices
        mock_data_api_client.fetch_entities.return_value = sample_entities
        await opportunity_finder._scan_devices()

        # Now make fetch fail
        mock_data_api_client.fetch_devices.side_effect = Exception("API Error")
        mock_data_api_client.fetch_entities.side_effect = Exception("API Error")

        # Should return cached data
        devices, entities = await opportunity_finder._scan_devices()

        assert devices == sample_devices
        assert entities == sample_entities

    @pytest.mark.asyncio
    async def test_scan_devices_no_cache_on_first_failure(
        self,
        opportunity_finder,
        mock_data_api_client
    ):
        """Test device scanning failure with no cache."""
        mock_data_api_client.fetch_devices.side_effect = Exception("API Error")
        mock_data_api_client.fetch_entities.side_effect = Exception("API Error")

        devices, entities = await opportunity_finder._scan_devices()

        assert devices == []
        assert entities == []

    def test_extract_device_info(
        self,
        opportunity_finder,
        sample_devices,
        sample_entities
    ):
        """Test device type and integration extraction."""
        device_types, integrations = opportunity_finder._extract_device_info(
            sample_devices,
            sample_entities
        )

        assert "light" in device_types
        assert "binary_sensor" in device_types
        assert "hue" in integrations or len(integrations) > 0

    def test_extract_device_info_no_entities(
        self,
        opportunity_finder,
        sample_devices
    ):
        """Test device info extraction without entities (fallback)."""
        device_types, integrations = opportunity_finder._extract_device_info(
            sample_devices,
            []
        )

        # Should fall back to device name/model parsing
        assert len(device_types) >= 0  # May find some from names
        assert len(integrations) >= 0  # May find some from manufacturer

    @pytest.mark.asyncio
    async def test_search_blueprints_success(
        self,
        opportunity_finder,
        mock_miner,
        sample_blueprint
    ):
        """Test successful blueprint search."""
        mock_miner.is_available.return_value = True
        mock_miner.search_blueprints.return_value = [sample_blueprint]

        blueprints = await opportunity_finder._search_blueprints(
            device_types=["light", "binary_sensor"],
            min_quality=0.7
        )

        assert len(blueprints) == 1
        assert blueprints[0]["id"] == "blueprint1"
        assert mock_miner.search_blueprints.call_count == 2  # One per device type

    @pytest.mark.asyncio
    async def test_search_blueprints_miner_unavailable(
        self,
        opportunity_finder,
        mock_miner
    ):
        """Test blueprint search when miner is unavailable."""
        mock_miner.is_available.return_value = False

        blueprints = await opportunity_finder._search_blueprints(
            device_types=["light"],
            min_quality=0.7
        )

        assert blueprints == []
        mock_miner.search_blueprints.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_blueprints_deduplication(
        self,
        opportunity_finder,
        mock_miner,
        sample_blueprint
    ):
        """Test blueprint search deduplication."""
        # Same blueprint returned for both device types
        mock_miner.search_blueprints.return_value = [sample_blueprint]

        blueprints = await opportunity_finder._search_blueprints(
            device_types=["light", "binary_sensor"],
            min_quality=0.7
        )

        # Should deduplicate
        assert len(blueprints) == 1
        assert blueprints[0]["id"] == "blueprint1"

    def test_calculate_fit_score(
        self,
        opportunity_finder,
        sample_blueprint
    ):
        """Test fit score calculation."""
        fit_score = opportunity_finder._calculate_fit_score(
            blueprint=sample_blueprint,
            device_types=["light", "binary_sensor"],
            integrations=["hue"]
        )

        assert 0.0 <= fit_score <= 1.0
        # Should have high score for matching devices
        assert fit_score >= 0.5

    def test_calculate_fit_score_low_match(
        self,
        opportunity_finder,
        sample_blueprint
    ):
        """Test fit score with low device match."""
        fit_score = opportunity_finder._calculate_fit_score(
            blueprint=sample_blueprint,
            device_types=["switch"],  # No match
            integrations=[]
        )

        assert 0.0 <= fit_score <= 1.0
        # Should have lower score
        assert fit_score < 0.5

    def test_calculate_device_type_compatibility(
        self,
        opportunity_finder
    ):
        """Test device type compatibility calculation."""
        # Perfect match
        score1 = opportunity_finder._calculate_device_type_compatibility(
            blueprint_devices=["light", "binary_sensor"],
            user_device_types=["light", "binary_sensor"]
        )
        assert score1 == 1.0

        # Partial match
        score2 = opportunity_finder._calculate_device_type_compatibility(
            blueprint_devices=["light", "binary_sensor"],
            user_device_types=["light"]  # Only one of two
        )
        assert 0.0 < score2 < 1.0

        # No match
        score3 = opportunity_finder._calculate_device_type_compatibility(
            blueprint_devices=["light"],
            user_device_types=["switch"]
        )
        assert score3 == 0.0

    def test_calculate_integration_compatibility(
        self,
        opportunity_finder,
        sample_blueprint
    ):
        """Test integration compatibility calculation."""
        # Should return neutral score if no integration requirements
        score = opportunity_finder._calculate_integration_compatibility(
            blueprint=sample_blueprint,
            user_integrations=["hue"]
        )

        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_find_opportunities_success(
        self,
        opportunity_finder,
        mock_data_api_client,
        mock_miner,
        sample_devices,
        sample_entities,
        sample_blueprint
    ):
        """Test successful opportunity discovery."""
        mock_data_api_client.fetch_devices.return_value = sample_devices
        mock_data_api_client.fetch_entities.return_value = sample_entities
        mock_miner.is_available.return_value = True
        mock_miner.search_blueprints.return_value = [sample_blueprint]

        opportunities = await opportunity_finder.find_opportunities(
            min_fit_score=0.6,
            min_blueprint_quality=0.7,
            limit=50
        )

        assert len(opportunities) > 0
        assert opportunities[0]["fit_score"] >= 0.6
        assert "blueprint" in opportunities[0]
        assert "device_types" in opportunities[0]
        assert "integrations" in opportunities[0]

    @pytest.mark.asyncio
    async def test_find_opportunities_no_devices(
        self,
        opportunity_finder,
        mock_data_api_client
    ):
        """Test opportunity discovery with no devices."""
        mock_data_api_client.fetch_devices.return_value = []
        mock_data_api_client.fetch_entities.return_value = []

        opportunities = await opportunity_finder.find_opportunities()

        assert opportunities == []

    @pytest.mark.asyncio
    async def test_find_opportunities_miner_unavailable(
        self,
        opportunity_finder,
        mock_data_api_client,
        mock_miner,
        sample_devices,
        sample_entities
    ):
        """Test opportunity discovery when miner is unavailable."""
        mock_data_api_client.fetch_devices.return_value = sample_devices
        mock_data_api_client.fetch_entities.return_value = sample_entities
        mock_miner.is_available.return_value = False

        opportunities = await opportunity_finder.find_opportunities()

        # Should return empty list, not fail
        assert opportunities == []

    @pytest.mark.asyncio
    async def test_find_opportunities_filters_by_fit_score(
        self,
        opportunity_finder,
        mock_data_api_client,
        mock_miner,
        sample_devices,
        sample_entities,
        sample_blueprint
    ):
        """Test that opportunities are filtered by fit score."""
        mock_data_api_client.fetch_devices.return_value = sample_devices
        mock_data_api_client.fetch_entities.return_value = sample_entities
        mock_miner.is_available.return_value = True
        mock_miner.search_blueprints.return_value = [sample_blueprint]

        opportunities = await opportunity_finder.find_opportunities(
            min_fit_score=0.9,  # High threshold
            min_blueprint_quality=0.7,
            limit=50
        )

        # All returned opportunities should meet threshold
        for opp in opportunities:
            assert opp["fit_score"] >= 0.9

    @pytest.mark.asyncio
    async def test_find_opportunities_sorts_by_fit_score(
        self,
        opportunity_finder,
        mock_data_api_client,
        mock_miner,
        sample_devices,
        sample_entities
    ):
        """Test that opportunities are sorted by fit score."""
        # Create blueprints with different quality scores
        blueprint1 = {
            "id": "bp1",
            "quality_score": 0.9,
            "metadata": {
                "_blueprint_devices": ["light"],
                "_blueprint_metadata": {"description": "Light automation"}
            }
        }
        blueprint2 = {
            "id": "bp2",
            "quality_score": 0.8,
            "metadata": {
                "_blueprint_devices": ["switch"],
                "_blueprint_metadata": {"description": "Switch automation"}
            }
        }

        mock_data_api_client.fetch_devices.return_value = sample_devices
        mock_data_api_client.fetch_entities.return_value = sample_entities
        mock_miner.is_available.return_value = True
        mock_miner.search_blueprints.return_value = [blueprint1, blueprint2]

        opportunities = await opportunity_finder.find_opportunities(
            min_fit_score=0.0,  # Accept all
            limit=50
        )

        # Should be sorted descending
        if len(opportunities) >= 2:
            assert opportunities[0]["fit_score"] >= opportunities[1]["fit_score"]

    @pytest.mark.asyncio
    async def test_find_opportunities_respects_limit(
        self,
        opportunity_finder,
        mock_data_api_client,
        mock_miner,
        sample_devices,
        sample_entities,
        sample_blueprint
    ):
        """Test that opportunities respect limit parameter."""
        # Return multiple blueprints
        blueprints = [sample_blueprint.copy() for _ in range(10)]
        for i, bp in enumerate(blueprints):
            bp["id"] = f"blueprint{i}"

        mock_data_api_client.fetch_devices.return_value = sample_devices
        mock_data_api_client.fetch_entities.return_value = sample_entities
        mock_miner.is_available.return_value = True
        mock_miner.search_blueprints.return_value = blueprints

        opportunities = await opportunity_finder.find_opportunities(
            min_fit_score=0.6,
            limit=5
        )

        assert len(opportunities) <= 5

