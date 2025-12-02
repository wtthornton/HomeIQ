"""
Tests for target optimization utilities
"""

import pytest

from src.services.automation.target_optimization import optimize_action_targets


class MockHAClient:
    """Mock Home Assistant client for testing"""
    
    def __init__(self, entity_metadata: dict[str, dict]):
        self.entity_metadata = entity_metadata
    
    async def get_entity_state(self, entity_id: str) -> dict:
        """Mock get_entity_state"""
        return self.entity_metadata.get(entity_id)


class TestTargetOptimization:
    """Tests for target optimization"""

    @pytest.mark.asyncio
    async def test_optimize_to_area_id(self):
        """Test optimization to area_id when all entities in same area"""
        yaml_data = {
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": ["light.kitchen_1", "light.kitchen_2", "light.kitchen_3"]
                    }
                }
            ]
        }
        
        # Mock HA client with entities in same area
        ha_client = MockHAClient({
            "light.kitchen_1": {
                "attributes": {"area_id": "kitchen", "device_id": "device_1"}
            },
            "light.kitchen_2": {
                "attributes": {"area_id": "kitchen", "device_id": "device_2"}
            },
            "light.kitchen_3": {
                "attributes": {"area_id": "kitchen", "device_id": "device_3"}
            }
        })
        
        optimized = await optimize_action_targets(yaml_data, ha_client)
        
        # Should optimize to area_id
        assert optimized["action"][0]["target"] == {"area_id": "kitchen"}
    
    @pytest.mark.asyncio
    async def test_optimize_to_device_id(self):
        """Test optimization to device_id when all entities on same device"""
        yaml_data = {
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": ["light.bulb_1", "light.bulb_2"]
                    }
                }
            ]
        }
        
        # Mock HA client with entities on same device
        ha_client = MockHAClient({
            "light.bulb_1": {
                "attributes": {"area_id": "living_room", "device_id": "hue_bridge_1"}
            },
            "light.bulb_2": {
                "attributes": {"area_id": "living_room", "device_id": "hue_bridge_1"}
            }
        })
        
        optimized = await optimize_action_targets(yaml_data, ha_client)
        
        # Should optimize to device_id
        assert optimized["action"][0]["target"] == {"device_id": "hue_bridge_1"}
    
    @pytest.mark.asyncio
    async def test_no_optimization_different_areas(self):
        """Test no optimization when entities in different areas"""
        yaml_data = {
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": ["light.kitchen", "light.bedroom"]
                    }
                }
            ]
        }
        
        # Mock HA client with entities in different areas
        ha_client = MockHAClient({
            "light.kitchen": {
                "attributes": {"area_id": "kitchen", "device_id": "device_1"}
            },
            "light.bedroom": {
                "attributes": {"area_id": "bedroom", "device_id": "device_2"}
            }
        })
        
        optimized = await optimize_action_targets(yaml_data, ha_client)
        
        # Should NOT optimize - keep original entity_id list
        assert optimized["action"][0]["target"]["entity_id"] == ["light.kitchen", "light.bedroom"]
    
    @pytest.mark.asyncio
    async def test_no_optimization_single_entity(self):
        """Test no optimization for single entity"""
        yaml_data = {
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": ["light.kitchen"]
                    }
                }
            ]
        }
        
        # Mock HA client
        ha_client = MockHAClient({
            "light.kitchen": {
                "attributes": {"area_id": "kitchen", "device_id": "device_1"}
            }
        })
        
        optimized = await optimize_action_targets(yaml_data, ha_client)
        
        # Should NOT optimize - single entity doesn't need optimization
        assert optimized["action"][0]["target"]["entity_id"] == ["light.kitchen"]
    
    @pytest.mark.asyncio
    async def test_no_optimization_without_ha_client(self):
        """Test no optimization when HA client not available"""
        yaml_data = {
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": ["light.kitchen_1", "light.kitchen_2"]
                    }
                }
            ]
        }
        
        optimized = await optimize_action_targets(yaml_data, None)
        
        # Should NOT optimize - no HA client
        assert optimized["action"][0]["target"]["entity_id"] == ["light.kitchen_1", "light.kitchen_2"]
    
    @pytest.mark.asyncio
    async def test_optimization_preserves_other_actions(self):
        """Test optimization preserves actions that don't need optimization"""
        yaml_data = {
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": ["light.kitchen_1", "light.kitchen_2"]
                    }
                },
                {
                    "service": "notify.mobile_app",
                    "data": {
                        "message": "Lights turned on"
                    }
                }
            ]
        }
        
        # Mock HA client
        ha_client = MockHAClient({
            "light.kitchen_1": {
                "attributes": {"area_id": "kitchen", "device_id": "device_1"}
            },
            "light.kitchen_2": {
                "attributes": {"area_id": "kitchen", "device_id": "device_2"}
            }
        })
        
        optimized = await optimize_action_targets(yaml_data, ha_client)
        
        # First action should be optimized
        assert optimized["action"][0]["target"] == {"area_id": "kitchen"}
        # Second action should be preserved
        assert optimized["action"][1]["service"] == "notify.mobile_app"
        assert "data" in optimized["action"][1]

