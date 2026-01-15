"""
Unit tests for TargetResolver
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Fix import path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.validation.target_resolver import TargetResolver


class TestTargetResolver:
    """Test TargetResolver class"""
    
    @pytest.fixture
    def mock_capability_graph(self):
        """Mock capability graph"""
        graph = MagicMock()
        
        # Mock entities by area
        graph.get_entities_by_area.return_value = [
            {"entity_id": "light.living_room"},
            {"entity_id": "light.kitchen"}
        ]
        
        # Mock entities by device class
        graph.get_entities_by_device_class.return_value = [
            {"entity_id": "light.bedroom"},
            {"entity_id": "light.hallway"}
        ]
        
        return graph
    
    @pytest.fixture
    def resolver(self, mock_capability_graph):
        """Create TargetResolver instance"""
        return TargetResolver(mock_capability_graph)
    
    def test_resolve_entity_id_string(self, resolver):
        """Test resolving single entity_id string"""
        target = {"entity_id": "light.living_room"}
        result = resolver.resolve_target(target)
        assert result == ["light.living_room"]
    
    def test_resolve_entity_id_list(self, resolver):
        """Test resolving entity_id list"""
        target = {"entity_id": ["light.living_room", "light.kitchen"]}
        result = resolver.resolve_target(target)
        assert result == ["light.living_room", "light.kitchen"]
    
    def test_resolve_area(self, resolver, mock_capability_graph):
        """Test resolving area selector"""
        target = {"area": "living_room"}
        result = resolver.resolve_target(target)
        assert len(result) == 2
        assert "light.living_room" in result
        assert "light.kitchen" in result
        mock_capability_graph.get_entities_by_area.assert_called_once_with("living_room")
    
    def test_resolve_device_class(self, resolver, mock_capability_graph):
        """Test resolving device_class selector"""
        target = {"device_class": "light"}
        result = resolver.resolve_target(target)
        assert len(result) == 2
        assert "light.bedroom" in result
        assert "light.hallway" in result
        mock_capability_graph.get_entities_by_device_class.assert_called_once_with("light")
    
    def test_resolve_user_not_implemented(self, resolver):
        """Test user selector (not yet implemented)"""
        target = {"user": "primary"}
        result = resolver.resolve_target(target)
        assert result == []  # Returns empty list with warning
    
    def test_resolve_duplicates_removed(self, resolver):
        """Test that duplicates are removed"""
        target = {"entity_id": ["light.test", "light.test", "light.other"]}
        result = resolver.resolve_target(target)
        assert result == ["light.test", "light.other"]
        assert len(result) == 2
    
    def test_resolve_action_targets(self, resolver):
        """Test resolving targets for multiple actions"""
        actions = [
            {"id": "act1", "target": {"entity_id": "light.test1"}},
            {"id": "act2", "target": {"area": "living_room"}}
        ]
        result = resolver.resolve_action_targets(actions)
        assert len(result) == 2
        assert result[0]["resolved_entity_ids"] == ["light.test1"]
        assert len(result[1]["resolved_entity_ids"]) == 2
        assert result[0]["target_resolved"] is True
        assert result[1]["target_resolved"] is True
    
    def test_create_execution_plan(self, resolver):
        """Test creating execution plan"""
        spec = {
            "id": "test_spec",
            "version": "1.0.0",
            "actions": [
                {"id": "act1", "target": {"entity_id": "light.test1"}},
                {"id": "act2", "target": {"entity_id": "light.test2"}}
            ]
        }
        plan = resolver.create_execution_plan(spec)
        assert plan["spec_id"] == "test_spec"
        assert plan["spec_version"] == "1.0.0"
        assert plan["total_actions"] == 2
        assert plan["total_entities"] == 2
    
    def test_resolve_empty_target(self, resolver):
        """Test resolving empty target"""
        target = {}
        result = resolver.resolve_target(target)
        assert result == []
    
    def test_resolve_no_matching_entities(self, resolver, mock_capability_graph):
        """Test resolving when no entities match"""
        mock_capability_graph.get_entities_by_area.return_value = []
        target = {"area": "nonexistent"}
        result = resolver.resolve_target(target)
        assert result == []
