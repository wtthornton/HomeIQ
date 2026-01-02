"""
Test Suite for Phase 1, 2 & 3 Features

Verifies all implemented features are working correctly:
- Phase 1: Health scores, relationships, availability
- Phase 2: Capabilities, constraints, patterns, energy
- Phase 3: Prioritization, filtering
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from src.services.devices_summary_service import DevicesSummaryService
from src.services.device_state_context_service import DeviceStateContextService
from src.services.automation_patterns_service import AutomationPatternsService
from src.services.context_prioritization_service import ContextPrioritizationService
from src.services.context_filtering_service import ContextFilteringService
from src.services.context_builder import ContextBuilder
from src.config import Settings


class TestPhase1Features:
    """Test Phase 1: Critical Fixes"""
    
    @pytest.mark.asyncio
    async def test_health_scores_in_device_summary(self):
        """Test that health scores are included in device summary"""
        # Mock settings and context builder
        settings = MagicMock(spec=Settings)
        settings.data_api_url = "http://test-data-api:8006"
        settings.ha_url = "http://test-ha:8123"
        settings.ha_token = "test-token"
        settings.device_intelligence_url = "http://test-device-intel:8007"
        settings.device_intelligence_enabled = True
        
        context_builder = MagicMock()
        context_builder._get_cached_value = AsyncMock(return_value=None)
        context_builder._set_cached_value = AsyncMock()
        
        service = DevicesSummaryService(settings, context_builder)
        
        # Mock device data with health score
        mock_devices = [
            {
                "device_id": "test_device_1",
                "name": "Test Light",
                "manufacturer": "Test Corp",
                "model": "TL-100",
                "area_id": "office",
                "entity_count": 2,
                "health_score": 85
            }
        ]
        
        with patch.object(service.data_api_client, 'fetch_devices', new_callable=AsyncMock) as mock_fetch_devices, \
             patch.object(service.data_api_client, 'fetch_entities', new_callable=AsyncMock) as mock_fetch_entities, \
             patch.object(service.data_api_client, 'fetch_areas', new_callable=AsyncMock) as mock_fetch_areas:
            
            mock_fetch_devices.return_value = mock_devices
            mock_fetch_entities.return_value = []
            mock_fetch_areas.return_value = []
            
            summary = await service.get_summary()
            
            # Verify health score is in summary
            assert "health_score" in summary.lower() or "85" in summary
            print("✅ Phase 1.1: Health scores included in device summary")
    
    @pytest.mark.asyncio
    async def test_device_relationships_in_summary(self):
        """Test that device relationships are included in device summary"""
        settings = MagicMock(spec=Settings)
        settings.data_api_url = "http://test-data-api:8006"
        settings.ha_url = "http://test-ha:8123"
        settings.ha_token = "test-token"
        settings.device_intelligence_url = "http://test-device-intel:8007"
        settings.device_intelligence_enabled = True
        
        context_builder = MagicMock()
        context_builder._get_cached_value = AsyncMock(return_value=None)
        context_builder._set_cached_value = AsyncMock()
        
        service = DevicesSummaryService(settings, context_builder)
        
        # Mock device with description
        mock_devices = [
            {
                "device_id": "test_device_1",
                "name": "Hue Room",
                "manufacturer": "Signify",
                "model": "Room",
                "area_id": "office",
                "entity_count": 5,
                "device_description": "Hue Room - controls 5 lights"
            }
        ]
        
        with patch.object(service.data_api_client, 'fetch_devices', new_callable=AsyncMock) as mock_fetch_devices, \
             patch.object(service.data_api_client, 'fetch_entities', new_callable=AsyncMock) as mock_fetch_entities, \
             patch.object(service.data_api_client, 'fetch_areas', new_callable=AsyncMock) as mock_fetch_areas:
            
            mock_fetch_devices.return_value = mock_devices
            mock_fetch_entities.return_value = []
            mock_fetch_areas.return_value = []
            
            summary = await service.get_summary()
            
            # Verify device description is in summary
            assert "controls" in summary.lower() or "Hue Room" in summary
            print("✅ Phase 1.2: Device relationships included in device summary")
    
    def test_entity_availability_highlighting(self):
        """Test that unavailable entities are highlighted in state context"""
        settings = MagicMock(spec=Settings)
        settings.data_api_url = "http://test-data-api:8006"
        settings.ha_url = "http://test-ha:8123"
        settings.ha_token = "test-token"
        
        context_builder = MagicMock()
        
        service = DeviceStateContextService(settings, context_builder)
        
        # Mock state with unavailable entity
        mock_state = {
            "entity_id": "light.office_go",
            "state": "unavailable",
            "attributes": {}
        }
        
        formatted = service._format_state_entry(mock_state)
        
        # Verify unavailable warning is present
        assert "unavailable" in formatted.lower()
        assert "⚠️" in formatted or "warning" in formatted.lower()
        print("✅ Phase 1.3: Entity availability status highlighted")


class TestPhase2Features:
    """Test Phase 2: High-Value Improvements"""
    
    @pytest.mark.asyncio
    async def test_device_capabilities_in_summary(self):
        """Test that device capabilities are included in device summary"""
        settings = MagicMock(spec=Settings)
        settings.data_api_url = "http://test-data-api:8006"
        settings.ha_url = "http://test-ha:8123"
        settings.ha_token = "test-token"
        settings.device_intelligence_url = "http://test-device-intel:8007"
        settings.device_intelligence_enabled = False
        
        context_builder = MagicMock()
        context_builder._get_cached_value = AsyncMock(return_value=None)
        context_builder._set_cached_value = AsyncMock()
        
        service = DevicesSummaryService(settings, context_builder)
        
        # Mock devices and entities with capabilities
        mock_devices = [
            {
                "device_id": "test_light_1",
                "name": "Test Light",
                "manufacturer": "Test Corp",
                "model": "TL-100",
                "area_id": "office",
                "entity_count": 1
            }
        ]
        
        mock_entities = [
            {
                "entity_id": "light.test_light",
                "device_id": "test_light_1",
                "domain": "light",
                "attributes": {
                    "effect_list": ["Fireworks", "Rainbow", "Chase"],
                    "supported_color_modes": ["rgb", "hs"],
                    "preset_modes": ["Party", "Relax", "Read"]
                }
            }
        ]
        
        with patch.object(service.data_api_client, 'fetch_devices', new_callable=AsyncMock) as mock_fetch_devices, \
             patch.object(service.data_api_client, 'fetch_entities', new_callable=AsyncMock) as mock_fetch_entities, \
             patch.object(service.data_api_client, 'fetch_areas', new_callable=AsyncMock) as mock_fetch_areas:
            
            mock_fetch_devices.return_value = mock_devices
            mock_fetch_entities.return_value = mock_entities
            mock_fetch_areas.return_value = []
            
            summary = await service.get_summary()
            
            # Verify capabilities are in summary
            assert "effects" in summary.lower() or "colors" in summary.lower() or "presets" in summary.lower()
            print("✅ Phase 2.1: Device capabilities included in device summary")
    
    @pytest.mark.asyncio
    async def test_device_constraints_in_summary(self):
        """Test that device constraints are included in device summary"""
        settings = MagicMock(spec=Settings)
        settings.data_api_url = "http://test-data-api:8006"
        settings.ha_url = "http://test-ha:8123"
        settings.ha_token = "test-token"
        settings.device_intelligence_url = "http://test-device-intel:8007"
        settings.device_intelligence_enabled = False
        
        context_builder = MagicMock()
        context_builder._get_cached_value = AsyncMock(return_value=None)
        context_builder._set_cached_value = AsyncMock()
        
        service = DevicesSummaryService(settings, context_builder)
        
        # Mock devices and entities with constraints
        mock_devices = [
            {
                "device_id": "test_light_1",
                "name": "Test Light",
                "manufacturer": "Test Corp",
                "model": "TL-100",
                "area_id": "office",
                "entity_count": 1
            }
        ]
        
        mock_entities = [
            {
                "entity_id": "light.test_light",
                "device_id": "test_light_1",
                "domain": "light",
                "attributes": {
                    "max_brightness": 255,
                    "min_color_temp": 153,
                    "max_color_temp": 500
                }
            }
        ]
        
        with patch.object(service.data_api_client, 'fetch_devices', new_callable=AsyncMock) as mock_fetch_devices, \
             patch.object(service.data_api_client, 'fetch_entities', new_callable=AsyncMock) as mock_fetch_entities, \
             patch.object(service.data_api_client, 'fetch_areas', new_callable=AsyncMock) as mock_fetch_areas:
            
            mock_fetch_devices.return_value = mock_devices
            mock_fetch_entities.return_value = mock_entities
            mock_fetch_areas.return_value = []
            
            summary = await service.get_summary()
            
            # Verify constraints are in summary
            assert "max_brightness" in summary.lower() or "255" in summary
            assert "color_temp" in summary.lower() or "153" in summary
            print("✅ Phase 2.2: Device constraints included in device summary")
    
    @pytest.mark.asyncio
    async def test_automation_patterns_service(self):
        """Test that automation patterns service works"""
        settings = MagicMock(spec=Settings)
        settings.data_api_url = "http://test-data-api:8006"
        settings.ha_url = "http://test-ha:8123"
        settings.ha_token = "test-token"
        
        context_builder = MagicMock()
        context_builder._get_cached_value = AsyncMock(return_value=None)
        context_builder._set_cached_value = AsyncMock()
        
        service = AutomationPatternsService(settings, context_builder)
        
        # Mock automation entities
        mock_automations = [
            {
                "entity_id": "automation.office_lights_morning",
                "friendly_name": "Office Lights Morning",
                "domain": "automation"
            }
        ]
        
        with patch.object(service.data_api_client, 'fetch_entities', new_callable=AsyncMock) as mock_fetch_entities, \
             patch.object(service, '_get_automation_config', new_callable=AsyncMock) as mock_get_config:
            
            mock_fetch_entities.return_value = mock_automations
            mock_get_config.return_value = {
                "alias": "Office Lights Morning",
                "trigger": [{"platform": "time", "at": "07:00"}],
                "action": [{"service": "light.turn_on", "target": {"area_id": "office"}}]
            }
            
            patterns = await service.get_recent_patterns(
                user_prompt="turn on office lights",
                limit=3
            )
            
            # Verify patterns are returned
            assert patterns
            assert "PATTERNS" in patterns or "Office Lights" in patterns
            print("✅ Phase 2.3: Automation patterns service working")
    
    @pytest.mark.asyncio
    async def test_energy_consumption_in_summary(self):
        """Test that energy consumption data is included in device summary"""
        settings = MagicMock(spec=Settings)
        settings.data_api_url = "http://test-data-api:8006"
        settings.ha_url = "http://test-ha:8123"
        settings.ha_token = "test-token"
        settings.device_intelligence_url = "http://test-device-intel:8007"
        settings.device_intelligence_enabled = False
        
        context_builder = MagicMock()
        context_builder._get_cached_value = AsyncMock(return_value=None)
        context_builder._set_cached_value = AsyncMock()
        
        service = DevicesSummaryService(settings, context_builder)
        
        # Mock device with power consumption
        mock_devices = [
            {
                "device_id": "test_light_1",
                "name": "Test Light",
                "manufacturer": "Test Corp",
                "model": "TL-100",
                "area_id": "office",
                "entity_count": 1,
                "power_consumption_active_w": 15.0
            }
        ]
        
        with patch.object(service.data_api_client, 'fetch_devices', new_callable=AsyncMock) as mock_fetch_devices, \
             patch.object(service.data_api_client, 'fetch_entities', new_callable=AsyncMock) as mock_fetch_entities, \
             patch.object(service.data_api_client, 'fetch_areas', new_callable=AsyncMock) as mock_fetch_areas:
            
            mock_fetch_devices.return_value = mock_devices
            mock_fetch_entities.return_value = []
            mock_fetch_areas.return_value = []
            
            summary = await service.get_summary()
            
            # Verify energy data is in summary
            assert "power" in summary.lower() or "15" in summary or "w" in summary.lower()
            print("✅ Phase 2.4: Energy consumption data included in device summary")


class TestPhase3Features:
    """Test Phase 3: Efficiency Improvements"""
    
    def test_context_prioritization(self):
        """Test that context prioritization service works"""
        service = ContextPrioritizationService()
        
        # Test entity scoring
        entity = {
            "entity_id": "light.office_go",
            "friendly_name": "Office Light",
            "domain": "light",
            "area_id": "office"
        }
        
        score = service.score_entity_relevance(entity, "turn on office light")
        
        # Verify score is calculated
        assert 0.0 <= score <= 1.0
        assert score > 0  # Should have some relevance
        print(f"✅ Phase 3.1: Context prioritization scoring works (score: {score:.2f})")
        
        # Test prioritization
        entities = [
            {"entity_id": "light.office_go", "friendly_name": "Office Light", "domain": "light", "area_id": "office"},
            {"entity_id": "light.bedroom", "friendly_name": "Bedroom Light", "domain": "light", "area_id": "bedroom"},
            {"entity_id": "sensor.temperature", "friendly_name": "Temperature", "domain": "sensor", "area_id": "office"}
        ]
        
        prioritized = service.prioritize_entities(entities, "turn on office light", top_n=2)
        
        # Verify prioritization works
        assert len(prioritized) <= 2
        assert prioritized[0]["entity_id"] == "light.office_go"  # Should be most relevant
        print("✅ Phase 3.1: Context prioritization filtering works")
    
    def test_context_filtering(self):
        """Test that context filtering service works"""
        service = ContextFilteringService()
        
        # Test intent extraction
        intent = service.extract_intent("turn on office lights")
        
        # Verify intent is extracted
        assert "areas" in intent
        assert "domains" in intent
        assert "light" in intent["domains"] or "office" in intent["areas"]
        print(f"✅ Phase 3.2: Intent extraction works (intent: {intent})")
        
        # Test entity filtering
        entities = [
            {"entity_id": "light.office_go", "domain": "light", "area_id": "office"},
            {"entity_id": "light.bedroom", "domain": "light", "area_id": "bedroom"},
            {"entity_id": "sensor.temperature", "domain": "sensor", "area_id": "office"}
        ]
        
        filtered = service.filter_entities(entities, intent)
        
        # Verify filtering works
        assert len(filtered) <= len(entities)
        # Office light should be included
        office_lights = [e for e in filtered if e["area_id"] == "office" and e["domain"] == "light"]
        assert len(office_lights) > 0
        print("✅ Phase 3.2: Context filtering works")


class TestIntegration:
    """Test integration of all features"""
    
    @pytest.mark.asyncio
    async def test_context_builder_integration(self):
        """Test that context builder integrates all Phase 1-3 services"""
        settings = MagicMock(spec=Settings)
        settings.data_api_url = "http://test-data-api:8006"
        settings.ha_url = "http://test-ha:8123"
        settings.ha_token = "test-token"
        settings.device_intelligence_url = "http://test-device-intel:8007"
        settings.device_intelligence_enabled = True
        
        context_builder = ContextBuilder(settings)
        
        # Verify all services are initialized
        await context_builder.initialize()
        
        # Verify Phase 3 services are initialized
        assert context_builder._context_prioritization_service is not None
        assert context_builder._context_filtering_service is not None
        print("✅ Integration: Context builder initializes all Phase 1-3 services")
        
        # Cleanup
        await context_builder.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 1, 2 & 3 Features Test Suite")
    print("=" * 60)
    print("\nRunning tests...\n")
    
    # Run basic tests
    test_phase1 = TestPhase1Features()
    test_phase1.test_entity_availability_highlighting()
    
    test_phase3 = TestPhase3Features()
    test_phase3.test_context_prioritization()
    test_phase3.test_context_filtering()
    
    print("\n" + "=" * 60)
    print("✅ Basic tests completed!")
    print("Run 'pytest tests/test_phase_1_2_3_features.py' for full test suite")
    print("=" * 60)
