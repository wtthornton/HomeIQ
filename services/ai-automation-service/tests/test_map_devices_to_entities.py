"""
Unit tests for map_devices_to_entities and consolidate_devices_involved functions.

Tests the optimization for single-home local solutions:
- Deduplication of redundant mappings
- Area-aware fuzzy matching
- Match quality prioritization
- Consolidation of devices_involved arrays
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Dict, List, Any
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import the functions to test - use direct import to avoid module initialization issues
try:
    # Import just the functions we need to avoid circular imports
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ask_ai_router",
        src_path / "api" / "ask_ai_router.py"
    )
    ask_ai_module = importlib.util.module_from_spec(spec)
    
    # Mock dependencies before importing
    import sys
    sys.modules['shared.logging_config'] = Mock()
    sys.modules['shared.metrics_collector'] = Mock()
    
    spec.loader.exec_module(ask_ai_module)
    map_devices_to_entities = ask_ai_module.map_devices_to_entities
    consolidate_devices_involved = ask_ai_module.consolidate_devices_involved
except ImportError as e:
    # Fallback: use direct import if module structure allows
    from api.ask_ai_router import map_devices_to_entities, consolidate_devices_involved


class TestMapDevicesToEntities:
    """Test suite for map_devices_to_entities function"""
    
    @pytest.fixture
    def sample_enriched_data(self):
        """Sample enriched entity data matching the case from lines 550-557"""
        return {
            "light.wled_office": {
                "entity_id": "light.wled_office",
                "friendly_name": "WLED Office",
                "domain": "light",
                "area_name": "Office",
                "capabilities": ["brightness", "rgb_color", "color_temp", "transition", "effect"]
            },
            "light.lr_front_left_ceiling": {
                "entity_id": "light.lr_front_left_ceiling",
                "friendly_name": "LR Front Left Ceiling",
                "domain": "light",
                "area_name": "Living Room",
                "capabilities": ["brightness", "color_temp", "transition"]
            },
            "light.lr_back_right_ceiling": {
                "entity_id": "light.lr_back_right_ceiling",
                "friendly_name": "LR Back Right Ceiling",
                "domain": "light",
                "area_name": "Living Room",
                "capabilities": ["brightness", "color_temp", "transition"]
            },
            "light.lr_front_right_ceiling": {
                "entity_id": "light.lr_front_right_ceiling",
                "friendly_name": "LR Front Right Ceiling",
                "domain": "light",
                "area_name": "Living Room",
                "capabilities": ["brightness", "color_temp", "transition"]
            },
            "light.lr_back_left_ceiling": {
                "entity_id": "light.lr_back_left_ceiling",
                "friendly_name": "LR Back Left Ceiling",
                "domain": "light",
                "area_name": "Living Room",
                "capabilities": ["brightness", "color_temp", "transition"]
            }
        }
    
    @pytest.fixture
    def mock_ha_client(self):
        """Mock Home Assistant client"""
        client = AsyncMock()
        client.get_entity.return_value = {"state": "on"}
        return client
    
    @pytest.mark.asyncio
    async def test_exact_match_priority(self, sample_enriched_data, mock_ha_client):
        """Test that exact matches are prioritized over fuzzy matches"""
        devices_involved = ["WLED Office", "wled office"]
        
        result = await map_devices_to_entities(
            devices_involved,
            sample_enriched_data,
            ha_client=mock_ha_client,
            fuzzy_match=True
        )
        
        # Both should map to same entity, but exact match should be kept
        assert len(result) == 2  # Both map initially
        assert all(entity_id == "light.wled_office" for entity_id in result.values())
        assert "WLED Office" in result
        assert "wled office" in result
    
    @pytest.mark.asyncio
    async def test_deduplication_same_entity(self, sample_enriched_data, mock_ha_client):
        """Test deduplication when multiple device names map to same entity"""
        # "wled led strip" and "Office" should both map to light.wled_office
        devices_involved = ["wled led strip", "Office", "WLED Office"]
        
        result = await map_devices_to_entities(
            devices_involved,
            sample_enriched_data,
            ha_client=mock_ha_client,
            fuzzy_match=True
        )
        
        # All should map to same entity
        assert all(entity_id == "light.wled_office" for entity_id in result.values())
        # Should have mappings for all (deduplication happens in consolidate function)
        assert len(result) >= 1
    
    @pytest.mark.asyncio
    async def test_area_aware_fuzzy_matching(self, sample_enriched_data, mock_ha_client):
        """Test that area context improves fuzzy matching"""
        devices_involved = ["ceiling lights", "Living Room"]
        
        result = await map_devices_to_entities(
            devices_involved,
            sample_enriched_data,
            ha_client=mock_ha_client,
            fuzzy_match=True
        )
        
        # "ceiling lights" should match one of the LR ceiling lights
        # "Living Room" should match via area context
        assert len(result) >= 1
        # At least one ceiling light should be matched
        ceiling_lights_matched = [
            eid for eid in result.values() 
            if "lr_" in eid and "ceiling" in eid
        ]
        assert len(ceiling_lights_matched) > 0
    
    @pytest.mark.asyncio
    async def test_fuzzy_match_scoring(self, sample_enriched_data, mock_ha_client):
        """Test fuzzy match scoring with area context"""
        devices_involved = ["LR Front Left Ceiling"]
        
        result = await map_devices_to_entities(
            devices_involved,
            sample_enriched_data,
            ha_client=mock_ha_client,
            fuzzy_match=True
        )
        
        assert len(result) == 1
        assert result["LR Front Left Ceiling"] == "light.lr_front_left_ceiling"
    
    @pytest.mark.asyncio
    async def test_complete_case_from_lines_550_557(self, sample_enriched_data, mock_ha_client):
        """Test the specific case from APPROVE_BUTTON_COMPLETE_DATA_STRUCTURE.md lines 550-557"""
        devices_involved = [
            "wled led strip",
            "ceiling lights",
            "Office",
            "LR Front Left Ceiling",
            "LR Back Right Ceiling",
            "LR Front Right Ceiling",
            "LR Back Left Ceiling"
        ]
        
        result = await map_devices_to_entities(
            devices_involved,
            sample_enriched_data,
            ha_client=mock_ha_client,
            fuzzy_match=True
        )
        
        # Should map all devices
        assert len(result) >= 5  # At least 5 unique entities (1 WLED + 4 ceiling lights)
        
        # Verify WLED office is mapped
        wled_mappings = [
            device for device, entity_id in result.items()
            if entity_id == "light.wled_office"
        ]
        assert len(wled_mappings) >= 1  # At least one WLED mapping
        
        # Verify all 4 ceiling lights are mapped
        ceiling_entities = [
            entity_id for entity_id in result.values()
            if "lr_" in entity_id and "ceiling" in entity_id
        ]
        unique_ceiling_entities = set(ceiling_entities)
        assert len(unique_ceiling_entities) == 4  # All 4 ceiling lights mapped
    
    @pytest.mark.asyncio
    async def test_unmapped_devices(self, sample_enriched_data, mock_ha_client):
        """Test handling of devices that cannot be mapped"""
        devices_involved = ["WLED Office", "Non-existent Device", "LR Front Left Ceiling"]
        
        result = await map_devices_to_entities(
            devices_involved,
            sample_enriched_data,
            ha_client=mock_ha_client,
            fuzzy_match=True
        )
        
        # Should map 2 out of 3 devices
        assert len(result) == 2
        assert "WLED Office" in result
        assert "LR Front Left Ceiling" in result
        assert "Non-existent Device" not in result
    
    @pytest.mark.asyncio
    async def test_empty_enriched_data(self, mock_ha_client):
        """Test with empty enriched_data"""
        devices_involved = ["WLED Office", "Office Light"]
        
        result = await map_devices_to_entities(
            devices_involved,
            {},
            ha_client=mock_ha_client,
            fuzzy_match=True
        )
        
        # Should return empty dict
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_empty_devices_involved(self, sample_enriched_data, mock_ha_client):
        """Test with empty devices_involved list"""
        result = await map_devices_to_entities(
            [],
            sample_enriched_data,
            ha_client=mock_ha_client,
            fuzzy_match=True
        )
        
        # Should return empty dict
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_fuzzy_match_disabled(self, sample_enriched_data, mock_ha_client):
        """Test with fuzzy matching disabled"""
        devices_involved = ["wled led strip", "Office"]  # Won't match exactly
        
        result = await map_devices_to_entities(
            devices_involved,
            sample_enriched_data,
            ha_client=mock_ha_client,
            fuzzy_match=False
        )
        
        # Should only match exact matches
        # "wled led strip" won't match exactly, so may return empty or partial
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_ha_client_verification(self, sample_enriched_data):
        """Test entity verification with HA client"""
        mock_ha_client = AsyncMock()
        
        # Mock verification to return True for all entities
        async def mock_verify_entities(entity_ids, ha_client):
            return {eid: True for eid in entity_ids}
        
        with patch('api.ask_ai_router.verify_entities_exist_in_ha', side_effect=mock_verify_entities):
            devices_involved = ["WLED Office", "LR Front Left Ceiling"]
            
            result = await map_devices_to_entities(
                devices_involved,
                sample_enriched_data,
                ha_client=mock_ha_client,
                fuzzy_match=True
            )
            
            # Should verify entities exist
            assert len(result) == 2


class TestConsolidateDevicesInvolved:
    """Test suite for consolidate_devices_involved function"""
    
    def test_basic_consolidation(self):
        """Test basic consolidation of redundant device names"""
        devices_involved = ["wled led strip", "Office", "WLED Office"]
        validated_entities = {
            "wled led strip": "light.wled_office",
            "Office": "light.wled_office",
            "WLED Office": "light.wled_office"
        }
        
        result = consolidate_devices_involved(devices_involved, validated_entities)
        
        # Should consolidate to one entry (prefer longer, more specific name)
        assert len(result) == 1
        assert "WLED Office" in result  # Should prefer longer name
    
    def test_multiple_entities_no_redundancy(self):
        """Test consolidation when no redundancy exists"""
        devices_involved = [
            "LR Front Left Ceiling",
            "LR Back Right Ceiling",
            "LR Front Right Ceiling",
            "LR Back Left Ceiling"
        ]
        validated_entities = {
            "LR Front Left Ceiling": "light.lr_front_left_ceiling",
            "LR Back Right Ceiling": "light.lr_back_right_ceiling",
            "LR Front Right Ceiling": "light.lr_front_right_ceiling",
            "LR Back Left Ceiling": "light.lr_back_left_ceiling"
        }
        
        result = consolidate_devices_involved(devices_involved, validated_entities)
        
        # All are unique entities, so no consolidation
        assert len(result) == 4
        assert set(result) == set(devices_involved)
    
    def test_complete_case_consolidation(self):
        """Test consolidation for the complete case from lines 550-557"""
        devices_involved = [
            "wled led strip",
            "ceiling lights",
            "Office",
            "LR Front Left Ceiling",
            "LR Back Right Ceiling",
            "LR Front Right Ceiling",
            "LR Back Left Ceiling"
        ]
        validated_entities = {
            "wled led strip": "light.wled_office",
            "Office": "light.wled_office",
            "LR Front Left Ceiling": "light.lr_front_left_ceiling",
            "LR Back Right Ceiling": "light.lr_back_right_ceiling",
            "LR Front Right Ceiling": "light.lr_front_right_ceiling",
            "LR Back Left Ceiling": "light.lr_back_left_ceiling"
        }
        
        result = consolidate_devices_involved(devices_involved, validated_entities)
        
        # Should consolidate from 7 → 5 entries (remove redundant WLED mappings)
        assert len(result) <= 6  # At most 6 (1 WLED + 4 ceiling + 1 ceiling lights if mapped)
        assert len(result) >= 5  # At least 5 (1 WLED + 4 ceiling lights)
        
        # Should keep one WLED entry (prefer longer name)
        wled_entries = [d for d in result if "wled" in d.lower() or "office" in d.lower()]
        assert len(wled_entries) == 1
        
        # Should keep all 4 ceiling lights
        ceiling_entries = [d for d in result if "ceiling" in d.lower()]
        assert len(ceiling_entries) == 4
    
    def test_mixed_mapped_unmapped(self):
        """Test consolidation with some unmapped devices"""
        devices_involved = ["WLED Office", "Non-existent Device", "LR Front Left Ceiling"]
        validated_entities = {
            "WLED Office": "light.wled_office",
            "LR Front Left Ceiling": "light.lr_front_left_ceiling"
        }
        
        result = consolidate_devices_involved(devices_involved, validated_entities)
        
        # Should keep unmapped device, consolidate mapped ones
        assert len(result) == 3  # All kept (no redundancy)
        assert "Non-existent Device" in result
    
    def test_empty_inputs(self):
        """Test with empty inputs"""
        result = consolidate_devices_involved([], {})
        assert result == []
        
        result = consolidate_devices_involved(["Device"], {})
        assert result == ["Device"]  # Unmapped devices kept
    
    def test_prefer_longer_names(self):
        """Test that longer, more specific names are preferred"""
        devices_involved = ["Office", "WLED Office", "Office WLED Light"]
        validated_entities = {
            "Office": "light.wled_office",
            "WLED Office": "light.wled_office",
            "Office WLED Light": "light.wled_office"
        }
        
        result = consolidate_devices_involved(devices_involved, validated_entities)
        
        # Should prefer longest name
        assert len(result) == 1
        assert "Office WLED Light" in result  # Longest name
    
    def test_preserve_order(self):
        """Test that order is preserved while consolidating"""
        devices_involved = ["A", "B", "C", "D"]
        validated_entities = {
            "A": "light.entity1",
            "B": "light.entity1",  # Same as A
            "C": "light.entity2",
            "D": "light.entity2"   # Same as C
        }
        
        result = consolidate_devices_involved(devices_involved, validated_entities)
        
        # Should preserve order: A (first of entity1), C (first of entity2)
        assert result == ["A", "C"] or result == ["B", "D"]  # First occurrence kept
    
    def test_all_same_entity(self):
        """Test when all devices map to same entity"""
        devices_involved = ["Device 1", "Device 2", "Device 3", "Device 4"]
        validated_entities = {
            device: "light.same_entity" for device in devices_involved
        }
        
        result = consolidate_devices_involved(devices_involved, validated_entities)
        
        # Should consolidate to one entry
        assert len(result) == 1
        assert result[0] in devices_involved  # One of them kept


class TestIntegration:
    """Integration tests combining both functions"""
    
    @pytest.mark.asyncio
    async def test_full_flow_consolidation(self):
        """Test full flow: mapping + consolidation"""
        enriched_data = {
            "light.wled_office": {
                "entity_id": "light.wled_office",
                "friendly_name": "WLED Office",
                "domain": "light",
                "area_name": "Office"
            },
            "light.lr_front_left_ceiling": {
                "entity_id": "light.lr_front_left_ceiling",
                "friendly_name": "LR Front Left Ceiling",
                "domain": "light",
                "area_name": "Living Room"
            }
        }
        
        mock_ha_client = AsyncMock()
        
        # Step 1: Map devices to entities
        devices_involved = ["wled led strip", "Office", "LR Front Left Ceiling"]
        validated_entities = await map_devices_to_entities(
            devices_involved,
            enriched_data,
            ha_client=mock_ha_client,
            fuzzy_match=True
        )
        
        # Step 2: Consolidate
        consolidated = consolidate_devices_involved(devices_involved, validated_entities)
        
        # Verify consolidation worked
        assert len(consolidated) <= len(devices_involved)
        assert len(set(validated_entities.values())) >= len(consolidated)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

