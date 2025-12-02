"""
Tests for label target optimization utilities

Story AI10.2: Label Target Usage in YAML Generation
Epic AI-10: Home Assistant 2025 YAML Target Optimization
"""

import pytest

from src.services.automation.label_target_optimizer import (
    optimize_action_labels,
    add_label_hint_to_description,
    get_common_labels,
    should_use_label_targeting
)


class TestLabelTargetOptimization:
    """Tests for label target optimization"""

    @pytest.mark.asyncio
    async def test_optimize_to_label_id(self):
        """Test optimization to label_id when all entities share common label"""
        yaml_data = {
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": ["light.outdoor_1", "light.outdoor_2", "light.outdoor_3"]
                    }
                }
            ]
        }
        
        # Entity metadata with common 'outdoor' label
        entities_metadata = {
            "light.outdoor_1": {
                "entity_id": "light.outdoor_1",
                "labels": ["outdoor", "security"]
            },
            "light.outdoor_2": {
                "entity_id": "light.outdoor_2",
                "labels": ["outdoor", "garden"]
            },
            "light.outdoor_3": {
                "entity_id": "light.outdoor_3",
                "labels": ["outdoor", "patio"]
            }
        }
        
        optimized = await optimize_action_labels(yaml_data, entities_metadata)
        
        # Should optimize to label_id (common label is 'outdoor')
        assert optimized["action"][0]["target"] == {"label_id": "outdoor"}
    
    @pytest.mark.asyncio
    async def test_optimize_multiple_common_labels(self):
        """Test optimization when entities share multiple common labels"""
        yaml_data = {
            "action": [
                {
                    "service": "light.turn_off",
                    "target": {
                        "entity_id": ["light.holiday_1", "light.holiday_2"]
                    }
                }
            ]
        }
        
        # Entity metadata with multiple common labels
        entities_metadata = {
            "light.holiday_1": {
                "entity_id": "light.holiday_1",
                "labels": ["holiday-lights", "outdoor", "seasonal"]
            },
            "light.holiday_2": {
                "entity_id": "light.holiday_2",
                "labels": ["holiday-lights", "outdoor", "seasonal"]
            }
        }
        
        optimized = await optimize_action_labels(yaml_data, entities_metadata)
        
        # Should optimize to label_id (first alphabetically: 'holiday-lights')
        assert optimized["action"][0]["target"] == {"label_id": "holiday-lights"}
    
    @pytest.mark.asyncio
    async def test_no_optimization_no_common_labels(self):
        """Test no optimization when entities have no common labels"""
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
        
        # Entity metadata with different labels
        entities_metadata = {
            "light.kitchen": {
                "entity_id": "light.kitchen",
                "labels": ["kitchen", "cooking"]
            },
            "light.bedroom": {
                "entity_id": "light.bedroom",
                "labels": ["bedroom", "sleep"]
            }
        }
        
        optimized = await optimize_action_labels(yaml_data, entities_metadata)
        
        # Should NOT optimize - no common labels
        assert optimized["action"][0]["target"]["entity_id"] == ["light.kitchen", "light.bedroom"]
    
    @pytest.mark.asyncio
    async def test_no_optimization_single_entity(self):
        """Test no optimization for single entity"""
        yaml_data = {
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": ["light.outdoor"]
                    }
                }
            ]
        }
        
        # Entity metadata
        entities_metadata = {
            "light.outdoor": {
                "entity_id": "light.outdoor",
                "labels": ["outdoor", "security"]
            }
        }
        
        optimized = await optimize_action_labels(yaml_data, entities_metadata)
        
        # Should NOT optimize - single entity doesn't need optimization
        assert optimized["action"][0]["target"]["entity_id"] == ["light.outdoor"]
    
    @pytest.mark.asyncio
    async def test_no_optimization_without_metadata(self):
        """Test no optimization when entity metadata not available"""
        yaml_data = {
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": ["light.outdoor_1", "light.outdoor_2"]
                    }
                }
            ]
        }
        
        optimized = await optimize_action_labels(yaml_data, None)
        
        # Should NOT optimize - no metadata
        assert optimized["action"][0]["target"]["entity_id"] == ["light.outdoor_1", "light.outdoor_2"]
    
    @pytest.mark.asyncio
    async def test_no_optimization_missing_entity_metadata(self):
        """Test no optimization when metadata missing for some entities"""
        yaml_data = {
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": ["light.outdoor_1", "light.outdoor_2", "light.outdoor_3"]
                    }
                }
            ]
        }
        
        # Metadata missing for light.outdoor_3
        entities_metadata = {
            "light.outdoor_1": {
                "entity_id": "light.outdoor_1",
                "labels": ["outdoor"]
            },
            "light.outdoor_2": {
                "entity_id": "light.outdoor_2",
                "labels": ["outdoor"]
            }
        }
        
        optimized = await optimize_action_labels(yaml_data, entities_metadata)
        
        # Should NOT optimize - missing metadata for one entity
        assert optimized["action"][0]["target"]["entity_id"] == ["light.outdoor_1", "light.outdoor_2", "light.outdoor_3"]
    
    @pytest.mark.asyncio
    async def test_optimization_preserves_other_actions(self):
        """Test optimization preserves actions that don't need optimization"""
        yaml_data = {
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": ["light.holiday_1", "light.holiday_2"]
                    }
                },
                {
                    "service": "notify.mobile_app",
                    "data": {
                        "message": "Holiday lights turned on"
                    }
                }
            ]
        }
        
        # Entity metadata
        entities_metadata = {
            "light.holiday_1": {
                "entity_id": "light.holiday_1",
                "labels": ["holiday-lights"]
            },
            "light.holiday_2": {
                "entity_id": "light.holiday_2",
                "labels": ["holiday-lights"]
            }
        }
        
        optimized = await optimize_action_labels(yaml_data, entities_metadata)
        
        # First action should be optimized
        assert optimized["action"][0]["target"] == {"label_id": "holiday-lights"}
        # Second action should be preserved
        assert optimized["action"][1]["service"] == "notify.mobile_app"
        assert "data" in optimized["action"][1]
    
    @pytest.mark.asyncio
    async def test_optimization_with_empty_labels(self):
        """Test no optimization when entities have empty label lists"""
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
        
        # Entity metadata with empty labels
        entities_metadata = {
            "light.bulb_1": {
                "entity_id": "light.bulb_1",
                "labels": []
            },
            "light.bulb_2": {
                "entity_id": "light.bulb_2",
                "labels": []
            }
        }
        
        optimized = await optimize_action_labels(yaml_data, entities_metadata)
        
        # Should NOT optimize - no labels
        assert optimized["action"][0]["target"]["entity_id"] == ["light.bulb_1", "light.bulb_2"]


class TestLabelHintDescription:
    """Tests for label hint description enhancement"""
    
    def test_add_label_hint_to_existing_description(self):
        """Test adding label hint to existing description"""
        description = "Turn on holiday lights at sunset"
        enhanced = add_label_hint_to_description(description, "holiday-lights", 6)
        
        assert "holiday-lights" in enhanced
        assert "6 devices" in enhanced
        assert enhanced.startswith("Turn on holiday lights at sunset")
    
    def test_add_label_hint_to_empty_description(self):
        """Test creating description when none exists"""
        enhanced = add_label_hint_to_description("", "outdoor", 4)
        
        assert "outdoor" in enhanced
        assert "labeled devices" in enhanced
    
    def test_avoid_duplicate_label_hints(self):
        """Test that label hints are not duplicated"""
        description = "Manage outdoor lights"
        enhanced = add_label_hint_to_description(description, "outdoor", 3)
        
        # Should not add hint since 'outdoor' already in description
        assert description in enhanced or enhanced == description


class TestCommonLabels:
    """Tests for common label detection"""
    
    def test_get_common_labels_multiple_entities(self):
        """Test finding common labels across multiple entities"""
        entities = [
            {"labels": ["outdoor", "security", "night"]},
            {"labels": ["outdoor", "garden", "night"]},
            {"labels": ["outdoor", "patio", "night"]}
        ]
        
        common = get_common_labels(entities)
        
        assert common == {"outdoor", "night"}
    
    def test_get_common_labels_no_common(self):
        """Test when entities have no common labels"""
        entities = [
            {"labels": ["kitchen"]},
            {"labels": ["bedroom"]},
            {"labels": ["bathroom"]}
        ]
        
        common = get_common_labels(entities)
        
        assert common == set()
    
    def test_get_common_labels_all_same(self):
        """Test when all entities have exactly the same labels"""
        entities = [
            {"labels": ["holiday-lights", "outdoor"]},
            {"labels": ["holiday-lights", "outdoor"]}
        ]
        
        common = get_common_labels(entities)
        
        assert common == {"holiday-lights", "outdoor"}
    
    def test_get_common_labels_empty_list(self):
        """Test with empty entity list"""
        common = get_common_labels([])
        
        assert common == set()
    
    def test_get_common_labels_missing_labels_field(self):
        """Test with entities missing labels field"""
        entities = [
            {"entity_id": "light.outdoor"},
            {"entity_id": "light.garden"}
        ]
        
        common = get_common_labels(entities)
        
        assert common == set()


class TestShouldUseLabelTargeting:
    """Tests for label targeting decision logic"""
    
    def test_should_use_label_targeting_valid(self):
        """Test label targeting should be used when valid"""
        entity_ids = ["light.outdoor_1", "light.outdoor_2", "light.outdoor_3"]
        entities_metadata = {
            "light.outdoor_1": {"labels": ["outdoor", "security"]},
            "light.outdoor_2": {"labels": ["outdoor", "garden"]},
            "light.outdoor_3": {"labels": ["outdoor", "patio"]}
        }
        
        should_use, label_id = should_use_label_targeting(entity_ids, entities_metadata)
        
        assert should_use is True
        assert label_id == "outdoor"
    
    def test_should_not_use_label_targeting_no_common(self):
        """Test label targeting should not be used when no common labels"""
        entity_ids = ["light.kitchen", "light.bedroom"]
        entities_metadata = {
            "light.kitchen": {"labels": ["kitchen"]},
            "light.bedroom": {"labels": ["bedroom"]}
        }
        
        should_use, label_id = should_use_label_targeting(entity_ids, entities_metadata)
        
        assert should_use is False
        assert label_id is None
    
    def test_should_not_use_label_targeting_single_entity(self):
        """Test label targeting should not be used for single entity"""
        entity_ids = ["light.outdoor"]
        entities_metadata = {
            "light.outdoor": {"labels": ["outdoor", "security"]}
        }
        
        should_use, label_id = should_use_label_targeting(entity_ids, entities_metadata)
        
        assert should_use is False
        assert label_id is None
    
    def test_should_not_use_label_targeting_missing_metadata(self):
        """Test label targeting should not be used when metadata missing"""
        entity_ids = ["light.outdoor_1", "light.outdoor_2"]
        entities_metadata = {
            "light.outdoor_1": {"labels": ["outdoor"]}
            # light.outdoor_2 metadata missing
        }
        
        should_use, label_id = should_use_label_targeting(entity_ids, entities_metadata)
        
        assert should_use is False
        assert label_id is None

