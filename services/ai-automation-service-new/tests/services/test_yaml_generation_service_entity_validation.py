"""
Tests for entity validation functionality in YAMLGenerationService.

Epic 39, Story 39.10: Entity Validation Fix
Tests R1, R2, R3, R5 from REQUIREMENTS_ENTITY_VALIDATION_FIX.md
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock
import yaml

from src.services.yaml_generation_service import (
    YAMLGenerationService,
    YAMLGenerationError
)
from src.clients.data_api_client import DataAPIClient
from src.clients.openai_client import OpenAIClient
from src.clients.yaml_validation_client import YAMLValidationClient


@pytest.fixture
def mock_data_api_client():
    """Mock DataAPIClient for testing."""
    client = AsyncMock(spec=DataAPIClient)
    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAIClient for testing."""
    client = AsyncMock(spec=OpenAIClient)
    return client


@pytest.fixture
def mock_yaml_validation_client():
    """Mock YAMLValidationClient for testing."""
    client = AsyncMock(spec=YAMLValidationClient)
    return client


@pytest.fixture
def yaml_service(mock_data_api_client, mock_openai_client, mock_yaml_validation_client):
    """Create YAMLGenerationService instance with mocked dependencies."""
    # Create service with minimal dependencies (similar to test_yaml_validation.py)
    # The service will use default None values for optional dependencies
    service = YAMLGenerationService(
        openai_client=mock_openai_client,
        data_api_client=mock_data_api_client,
        yaml_validation_client=mock_yaml_validation_client
    )
    return service


@pytest.fixture
def sample_entities():
    """Sample entity data for testing."""
    return [
        {
            "entity_id": "light.office_main",
            "friendly_name": "Office Main Light",
            "area_id": "office",
            "domain": "light",
            "device_class": None
        },
        {
            "entity_id": "binary_sensor.office_motion",
            "friendly_name": "Office Motion Sensor",
            "area_id": "office",
            "domain": "binary_sensor",
            "device_class": "motion"
        },
        {
            "entity_id": "sensor.office_temperature",
            "friendly_name": "Office Temperature",
            "area_id": "office",
            "domain": "sensor",
            "device_class": "temperature"
        },
        {
            "entity_id": "light.living_room",
            "friendly_name": "Living Room Light",
            "area_id": "living_room",
            "domain": "light",
            "device_class": None
        }
    ]


class TestFetchEntityContext:
    """Test R1: Entity Context Fetching."""
    
    @pytest.mark.asyncio
    async def test_fetch_entity_context_success(self, yaml_service, mock_data_api_client, sample_entities):
        """Test successful entity fetch."""
        mock_data_api_client.fetch_entities.return_value = sample_entities
        
        result = await yaml_service._fetch_entity_context()
        
        assert "entities" in result
        assert "total_count" in result
        assert result["total_count"] == 4
        assert "light" in result["entities"]
        assert "binary_sensor" in result["entities"]
        assert len(result["entities"]["light"]) == 2
        assert len(result["entities"]["binary_sensor"]) == 1
        
        # Verify entity info extraction
        light_entities = result["entities"]["light"]
        assert light_entities[0]["entity_id"] == "light.office_main"
        assert light_entities[0]["friendly_name"] == "Office Main Light"
        assert light_entities[0]["area_id"] == "office"
    
    @pytest.mark.asyncio
    async def test_fetch_entity_context_empty(self, yaml_service, mock_data_api_client):
        """Test empty result handling."""
        mock_data_api_client.fetch_entities.return_value = []
        
        result = await yaml_service._fetch_entity_context()
        
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_fetch_entity_context_api_failure(self, yaml_service, mock_data_api_client):
        """Test Data API failure handling."""
        mock_data_api_client.fetch_entities.side_effect = Exception("API Error")
        
        result = await yaml_service._fetch_entity_context()
        
        # Should return empty dict on failure
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_fetch_entity_context_grouping(self, yaml_service, mock_data_api_client, sample_entities):
        """Test entity grouping by domain."""
        mock_data_api_client.fetch_entities.return_value = sample_entities
        
        result = await yaml_service._fetch_entity_context()
        
        # Verify grouping
        assert "light" in result["entities"]
        assert "binary_sensor" in result["entities"]
        assert "sensor" in result["entities"]
        assert len(result["entities"]["light"]) == 2
        assert len(result["entities"]["binary_sensor"]) == 1
        assert len(result["entities"]["sensor"]) == 1


class TestFormatEntityContextForPrompt:
    """Test R2: Entity Context Formatting for LLM Prompts."""
    
    def test_format_entity_context_with_entities(self, yaml_service, sample_entities):
        """Test formatting with entities."""
        entity_context = {
            "entities": {
                "light": [
                    {"entity_id": "light.office_main", "friendly_name": "Office Main Light", "area_id": "office"},
                    {"entity_id": "light.living_room", "friendly_name": "Living Room Light", "area_id": "living_room"}
                ],
                "binary_sensor": [
                    {"entity_id": "binary_sensor.office_motion", "friendly_name": "Office Motion", "area_id": "office"}
                ]
            },
            "total_count": 3
        }
        
        formatted = yaml_service._format_entity_context_for_prompt(entity_context)
        
        assert "LIGHT entities:" in formatted
        assert "light.office_main" in formatted
        assert "Office Main Light" in formatted
        assert "[area: office]" in formatted
        assert "BINARY_SENSOR entities:" in formatted
        assert "binary_sensor.office_motion" in formatted
    
    def test_format_entity_context_empty(self, yaml_service):
        """Test empty context handling."""
        result = yaml_service._format_entity_context_for_prompt({})
        assert result == ""
        
        result = yaml_service._format_entity_context_for_prompt({"entities": {}})
        assert result == ""
    
    def test_format_entity_context_domain_limit(self, yaml_service):
        """Test entity limit (50 per domain)."""
        # Create 60 entities for one domain
        entities = [
            {"entity_id": f"light.entity_{i}", "friendly_name": f"Light {i}", "area_id": "office"}
            for i in range(60)
        ]
        
        entity_context = {
            "entities": {
                "light": entities
            },
            "total_count": 60
        }
        
        formatted = yaml_service._format_entity_context_for_prompt(entity_context)
        
        # Should only include first 50
        assert formatted.count("light.entity_") == 50
        assert "(+10 more)" in formatted


class TestExtractEntityIds:
    """Test R5: Enhanced Entity Extraction."""
    
    def test_extract_direct_entity_id(self, yaml_service):
        """Test direct entity_id extraction."""
        data = {
            "entity_id": "light.office_main",
            "action": "light.turn_on"
        }
        
        entity_ids = yaml_service._extract_entity_ids(data)
        
        assert "light.office_main" in entity_ids
    
    def test_extract_entity_id_list(self, yaml_service):
        """Test entity_id list extraction."""
        data = {
            "entity_id": [
                "light.office_main",
                "light.office_desk_lamp",
                "binary_sensor.office_motion"
            ]
        }
        
        entity_ids = yaml_service._extract_entity_ids(data)
        
        assert "light.office_main" in entity_ids
        assert "light.office_desk_lamp" in entity_ids
        assert "binary_sensor.office_motion" in entity_ids
        assert len(entity_ids) == 3
    
    def test_extract_template_expression(self, yaml_service):
        """Test template expression extraction."""
        data = {
            "value_template": "{{ states('light.office_main') }}",
            "condition": "{{ is_state('binary_sensor.office_motion', 'on') }}"
        }
        
        entity_ids = yaml_service._extract_entity_ids(data)
        
        assert "light.office_main" in entity_ids
        assert "binary_sensor.office_motion" in entity_ids
    
    def test_extract_scene_snapshot(self, yaml_service):
        """Test scene snapshot extraction."""
        data = {
            "action": "scene.create",
            "snapshot_entities": [
                "light.office_main",
                "light.office_desk_lamp",
                "light.office_accent_strip"
            ]
        }
        
        entity_ids = yaml_service._extract_entity_ids(data)
        
        assert "light.office_main" in entity_ids
        assert "light.office_desk_lamp" in entity_ids
        assert "light.office_accent_strip" in entity_ids
    
    def test_extract_nested_structure(self, yaml_service):
        """Test nested structure traversal."""
        data = {
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "binary_sensor.office_motion_1",
                    "from": "off",
                    "to": "on"
                },
                {
                    "platform": "state",
                    "entity_id": "binary_sensor.office_motion_2"
                }
            ],
            "action": {
                "service": "light.turn_on",
                "target": {
                    "entity_id": "light.office_main"
                }
            }
        }
        
        entity_ids = yaml_service._extract_entity_ids(data)
        
        assert "binary_sensor.office_motion_1" in entity_ids
        assert "binary_sensor.office_motion_2" in entity_ids
        assert "light.office_main" in entity_ids
    
    def test_extract_area_id_not_added(self, yaml_service):
        """Test area_id handling (not added to entity_ids)."""
        data = {
            "target": {
                "area_id": "office"
            },
            "entity_id": "light.office_main"
        }
        
        entity_ids = yaml_service._extract_entity_ids(data)
        
        # area_id should not be in entity_ids
        assert "office" not in entity_ids
        assert "light.office_main" in entity_ids


class TestValidateEntities:
    """Test R3: Entity Validation."""
    
    @pytest.mark.asyncio
    async def test_validate_entities_valid(self, yaml_service, mock_data_api_client, sample_entities):
        """Test validation with valid entities."""
        mock_data_api_client.fetch_entities.return_value = sample_entities
        
        yaml_content = """
        id: test-automation
        alias: Test Automation
        trigger:
          - platform: state
            entity_id: binary_sensor.office_motion
        action:
          - service: light.turn_on
            target:
              entity_id: light.office_main
        """
        
        is_valid, invalid_entities = await yaml_service.validate_entities(yaml_content)
        
        assert is_valid is True
        assert len(invalid_entities) == 0
    
    @pytest.mark.asyncio
    async def test_validate_entities_invalid(self, yaml_service, mock_data_api_client, sample_entities):
        """Test validation with invalid entities."""
        mock_data_api_client.fetch_entities.return_value = sample_entities
        
        yaml_content = """
        id: test-automation
        alias: Test Automation
        trigger:
          - platform: state
            entity_id: binary_sensor.fictional_motion
        action:
          - service: light.turn_on
            target:
              entity_id: light.fictional_light
        """
        
        is_valid, invalid_entities = await yaml_service.validate_entities(yaml_content)
        
        assert is_valid is False
        assert "binary_sensor.fictional_motion" in invalid_entities
        assert "light.fictional_light" in invalid_entities
    
    @pytest.mark.asyncio
    async def test_validate_entities_empty_yaml(self, yaml_service):
        """Test validation with empty YAML."""
        is_valid, invalid_entities = await yaml_service.validate_entities("")
        
        assert is_valid is True
        assert len(invalid_entities) == 0
    
    @pytest.mark.asyncio
    async def test_validate_entities_no_entities(self, yaml_service, mock_data_api_client):
        """Test validation with YAML containing no entities."""
        mock_data_api_client.fetch_entities.return_value = []
        
        yaml_content = """
        id: test-automation
        alias: Test Automation
        trigger:
          - platform: time
            at: '07:00:00'
        """
        
        is_valid, invalid_entities = await yaml_service.validate_entities(yaml_content)
        
        assert is_valid is True
        assert len(invalid_entities) == 0


class TestEntityValidationIntegration:
    """Integration tests for entity validation flow."""
    
    @pytest.mark.asyncio
    async def test_full_flow_fetch_generate_validate(
        self, yaml_service, mock_data_api_client, mock_openai_client, sample_entities
    ):
        """Test full flow: fetch → generate → validate."""
        # Setup mocks
        mock_data_api_client.fetch_entities.return_value = sample_entities
        
        # Mock OpenAI to return YAML with valid entities
        valid_yaml = """
        id: test-automation
        alias: Test Automation
        trigger:
          - platform: state
            entity_id: binary_sensor.office_motion
        action:
          - service: light.turn_on
            target:
              entity_id: light.office_main
        """
        mock_openai_client.generate_yaml.return_value = valid_yaml
        
        # Test the flow
        suggestion = {
            "title": "Test Automation",
            "description": "Turn on office light when motion detected"
        }
        
        # This should succeed with valid entities
        result = await yaml_service._generate_yaml_direct(
            title=suggestion["title"],
            description=suggestion["description"]
        )
        
        assert result is not None
        assert "light.office_main" in result
        assert "binary_sensor.office_motion" in result
    
    @pytest.mark.asyncio
    async def test_validation_blocks_invalid_yaml(
        self, yaml_service, mock_data_api_client, mock_openai_client, sample_entities
    ):
        """Test validation blocks invalid YAML."""
        # Setup mocks
        mock_data_api_client.fetch_entities.return_value = sample_entities
        
        # Mock OpenAI to return YAML with invalid entities
        invalid_yaml = """
        id: test-automation
        alias: Test Automation
        trigger:
          - platform: state
            entity_id: binary_sensor.fictional_motion
        action:
          - service: light.turn_on
            target:
              entity_id: light.fictional_light
        """
        mock_openai_client.generate_yaml.return_value = invalid_yaml
        
        # Test that validation fails
        suggestion = {
            "title": "Test Automation",
            "description": "Test automation with invalid entities"
        }
        
        with pytest.raises(YAMLGenerationError) as exc_info:
            await yaml_service._generate_yaml_direct(
                title=suggestion["title"],
                description=suggestion["description"]
            )
        
        assert "Invalid entities found" in str(exc_info.value)
        assert "binary_sensor.fictional_motion" in str(exc_info.value) or "light.fictional_light" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_entity_context_passed_to_openai(
        self, yaml_service, mock_data_api_client, mock_openai_client, sample_entities
    ):
        """Test entity context passed to OpenAI client."""
        # Setup mocks
        mock_data_api_client.fetch_entities.return_value = sample_entities
        
        valid_yaml = """
        id: test-automation
        alias: Test Automation
        trigger:
          - platform: state
            entity_id: binary_sensor.office_motion
        action:
          - service: light.turn_on
            target:
              entity_id: light.office_main
        """
        mock_openai_client.generate_yaml.return_value = valid_yaml
        
        suggestion = {
            "title": "Test Automation",
            "description": "Test automation"
        }
        
        await yaml_service._generate_yaml_direct(
            title=suggestion["title"],
            description=suggestion["description"]
        )
        
        # Verify entity_context was passed to OpenAI client
        assert mock_openai_client.generate_yaml.called
        call_kwargs = mock_openai_client.generate_yaml.call_args[1]
        assert "entity_context" in call_kwargs
        
        entity_context = call_kwargs["entity_context"]
        assert "entities" in entity_context
        assert "light" in entity_context["entities"]
        assert "binary_sensor" in entity_context["entities"]
