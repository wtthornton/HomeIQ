"""
Unit tests for WLED Device Handler (Epic AI-24).

Tests for WLED master/segment detection and relationship mapping.
"""

import pytest

from src.device_mappings.base import DeviceType
from src.device_mappings.wled.handler import WLEDHandler


class TestWLEDHandler:
    """Tests for WLEDHandler."""
    
    def test_can_handle_wled_manufacturer(self):
        """Test that handler can handle WLED manufacturer."""
        handler = WLEDHandler()
        device = {"manufacturer": "WLED", "model": "Controller"}
        
        assert handler.can_handle(device) is True
    
    def test_can_handle_aircoookie(self):
        """Test that handler can handle Aircoookie manufacturer."""
        handler = WLEDHandler()
        device = {"manufacturer": "Aircoookie", "model": "WLED"}
        
        assert handler.can_handle(device) is True
    
    def test_can_handle_wled_model(self):
        """Test that handler can handle WLED model."""
        handler = WLEDHandler()
        device = {"manufacturer": "Unknown", "model": "WLED Controller"}
        
        assert handler.can_handle(device) is True
    
    def test_can_handle_wled_name(self):
        """Test that handler can handle WLED in device name."""
        handler = WLEDHandler()
        device = {"name": "Office WLED", "manufacturer": None, "model": None}
        
        assert handler.can_handle(device) is True
    
    def test_can_handle_entity_wled_pattern(self):
        """Test that handler can handle WLED entity_id pattern."""
        handler = WLEDHandler()
        
        assert handler.can_handle_entity("light.office_wled") is True
        assert handler.can_handle_entity("light.office_wled_segment_1") is True
        assert handler.can_handle_entity("light.office_hue") is False
    
    def test_identify_type_master(self):
        """Test that handler identifies master devices."""
        handler = WLEDHandler()
        device = {"manufacturer": "WLED", "name": "Office WLED"}
        entities = [{"entity_id": "light.office_wled"}]
        
        device_type = handler.identify_type(device, entities)
        
        assert device_type == DeviceType.MASTER
    
    def test_identify_type_segment(self):
        """Test that handler identifies segment devices."""
        handler = WLEDHandler()
        device = {"manufacturer": "WLED", "name": "Office WLED Segment 1"}
        entities = [{"entity_id": "light.office_wled_segment_1"}]
        
        device_type = handler.identify_type(device, entities)
        
        assert device_type == DeviceType.SEGMENT
    
    def test_get_relationships_segment_to_master(self):
        """Test that handler finds master for segments."""
        handler = WLEDHandler()
        segment_device = {
            "id": "segment1",
            "name": "Office WLED Segment 1",
            "manufacturer": "WLED"
        }
        all_devices = [
            segment_device,
            {
                "id": "master1",
                "name": "Office WLED",
                "manufacturer": "WLED"
            }
        ]
        
        relationships = handler.get_relationships(segment_device, all_devices)
        
        assert len(relationships) == 1
        assert relationships[0]["type"] == "master"
        assert relationships[0]["device_id"] == "master1"
    
    def test_get_relationships_master_to_segments(self):
        """Test that handler finds segments for master."""
        handler = WLEDHandler()
        master_device = {
            "id": "master1",
            "name": "Office WLED",
            "manufacturer": "WLED"
        }
        all_devices = [
            master_device,
            {
                "id": "segment1",
                "name": "Office WLED Segment 1",
                "manufacturer": "WLED"
            },
            {
                "id": "segment2",
                "name": "Office WLED Segment 2",
                "manufacturer": "WLED"
            }
        ]
        
        relationships = handler.get_relationships(master_device, all_devices)
        
        assert len(relationships) == 2
        assert all(rel["type"] == "segment" for rel in relationships)
        assert {rel["device_id"] for rel in relationships} == {"segment1", "segment2"}
    
    def test_enrich_context_master(self):
        """Test that handler enriches context for master."""
        handler = WLEDHandler()
        device = {"name": "Office WLED", "manufacturer": "WLED"}
        entities = [
            {"entity_id": "light.office_wled"},
            {"entity_id": "light.office_wled_segment_1"},
            {"entity_id": "light.office_wled_segment_2"}
        ]
        
        context = handler.enrich_context(device, entities)
        
        assert "WLED master" in context
        assert "2 segments" in context or "controls" in context
    
    def test_enrich_context_segment(self):
        """Test that handler enriches context for segment."""
        handler = WLEDHandler()
        device = {"name": "Office WLED Segment 1", "manufacturer": "WLED"}
        entities = [{"entity_id": "light.office_wled_segment_1"}]
        
        context = handler.enrich_context(device, entities)
        
        assert "WLED segment" in context
        assert "master" in context.lower()

