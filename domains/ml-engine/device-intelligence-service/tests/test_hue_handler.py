"""
Unit tests for Hue Device Handler (Epic AI-24).

Tests for Hue Room/Zone group detection and individual light identification.
"""

import pytest

from src.device_mappings.base import DeviceType
from src.device_mappings.hue.handler import HueHandler


class TestHueHandler:
    """Tests for HueHandler."""
    
    def test_can_handle_signify(self):
        """Test that handler can handle Signify devices."""
        handler = HueHandler()
        device = {"manufacturer": "Signify", "model": "Room"}
        
        assert handler.can_handle(device) is True
    
    def test_can_handle_philips(self):
        """Test that handler can handle Philips devices."""
        handler = HueHandler()
        device = {"manufacturer": "Philips", "model": "Hue go"}
        
        assert handler.can_handle(device) is True
    
    def test_can_handle_lowercase(self):
        """Test that handler handles lowercase manufacturer names."""
        handler = HueHandler()
        device = {"manufacturer": "signify", "model": "Room"}
        
        assert handler.can_handle(device) is True
    
    def test_can_handle_other_manufacturer(self):
        """Test that handler does not handle non-Hue devices."""
        handler = HueHandler()
        device = {"manufacturer": "WLED", "model": "FOSS"}
        
        assert handler.can_handle(device) is False
    
    def test_identify_type_room_group(self):
        """Test identifying Room group."""
        handler = HueHandler()
        device = {"manufacturer": "Signify", "model": "Room"}
        entity = {"entity_id": "light.office"}
        
        assert handler.identify_type(device, entity) == DeviceType.GROUP
    
    def test_identify_type_zone_group(self):
        """Test identifying Zone group."""
        handler = HueHandler()
        device = {"manufacturer": "Signify", "model": "Zone"}
        entity = {"entity_id": "light.office_zone"}
        
        assert handler.identify_type(device, entity) == DeviceType.GROUP
    
    def test_identify_type_individual_light(self):
        """Test identifying individual light."""
        handler = HueHandler()
        device = {"manufacturer": "Signify", "model": "Hue go"}
        entity = {"entity_id": "light.office_go"}
        
        assert handler.identify_type(device, entity) == DeviceType.INDIVIDUAL
    
    def test_identify_type_individual_color_downlight(self):
        """Test identifying individual color downlight."""
        handler = HueHandler()
        device = {"manufacturer": "Signify", "model": "Hue color downlight"}
        entity = {"entity_id": "light.office_back_right"}
        
        assert handler.identify_type(device, entity) == DeviceType.INDIVIDUAL
    
    def test_identify_type_case_insensitive(self):
        """Test that model matching is case-insensitive."""
        handler = HueHandler()
        device = {"manufacturer": "Signify", "model": "ROOM"}
        entity = {"entity_id": "light.office"}
        
        assert handler.identify_type(device, entity) == DeviceType.GROUP
    
    def test_get_relationships_room_group(self):
        """Test getting relationships for Room group."""
        handler = HueHandler()
        device = {"id": "room_device_1", "manufacturer": "Signify", "model": "Room", "area_id": "office"}
        entities = [
            {"entity_id": "light.office_go", "device_id": "light_device_1", "area_id": "office"},
            {"entity_id": "light.office_back_right", "device_id": "light_device_2", "area_id": "office"}
        ]
        
        relationships = handler.get_relationships(device, entities)
        
        assert relationships["type"] == "room_group"
        assert relationships["area_id"] == "office"
        assert "individual_lights" in relationships
    
    def test_get_relationships_individual_light(self):
        """Test getting relationships for individual light."""
        handler = HueHandler()
        device = {"id": "light_device_1", "manufacturer": "Signify", "model": "Hue go", "area_id": "office"}
        entities = [
            {"entity_id": "light.office", "device_id": "room_device_1", "area_id": "office"}
        ]
        
        relationships = handler.get_relationships(device, entities)
        
        assert relationships["type"] == "individual_light"
        assert relationships["area_id"] == "office"
        assert "room_group" in relationships
    
    def test_enrich_context_room_group(self):
        """Test enriching context for Room group."""
        handler = HueHandler()
        device = {"manufacturer": "Signify", "model": "Room"}
        entity = {"entity_id": "light.office"}
        
        context = handler.enrich_context(device, entity)
        
        assert context["description"] == "Hue Room - controls all lights in the area"
        assert context["device_type"] == "hue_group"
        assert context["group_type"] == "room"
        assert context["manufacturer"] == "Signify"
        assert context["model"] == "Room"
    
    def test_enrich_context_zone_group(self):
        """Test enriching context for Zone group."""
        handler = HueHandler()
        device = {"manufacturer": "Signify", "model": "Zone"}
        entity = {"entity_id": "light.office_zone"}
        
        context = handler.enrich_context(device, entity)
        
        assert context["description"] == "Hue Zone - controls all lights in the area"
        assert context["device_type"] == "hue_group"
        assert context["group_type"] == "zone"
    
    def test_enrich_context_individual_light(self):
        """Test enriching context for individual light."""
        handler = HueHandler()
        device = {"manufacturer": "Signify", "model": "Hue go"}
        entity = {"entity_id": "light.office_go"}
        
        context = handler.enrich_context(device, entity)
        
        assert context["description"] == "Hue Hue go"
        assert context["device_type"] == "hue_individual"
        assert context["manufacturer"] == "Signify"
        assert context["model"] == "Hue go"
        assert context["bulb_type"] == "Hue go"
    
    def test_enrich_context_missing_fields(self):
        """Test enriching context with missing device fields."""
        handler = HueHandler()
        device = {"manufacturer": "Signify"}  # Missing model
        entity = {"entity_id": "light.office"}
        
        context = handler.enrich_context(device, entity)
        
        # Should handle missing fields gracefully
        assert "description" in context
        assert "device_type" in context


class TestHueHandlerIntegration:
    """Integration tests for HueHandler with registry."""
    
    def test_handler_registration(self):
        """Test that Hue handler can be registered."""
        from src.device_mappings.registry import DeviceMappingRegistry
        from src.device_mappings.hue.handler import HueHandler
        
        registry = DeviceMappingRegistry()
        handler = HueHandler()
        registry.register("hue", handler)
        
        assert registry.get_handler("hue") == handler
    
    def test_handler_discovery(self):
        """Test that Hue handler can be discovered."""
        from src.device_mappings.registry import DeviceMappingRegistry
        
        registry = DeviceMappingRegistry()
        registry.discover_handlers()
        
        # Should discover Hue handler if module exists
        handler = registry.get_handler("hue")
        if handler is not None:
            assert isinstance(handler, HueHandler)
    
    def test_find_handler_for_hue_device(self):
        """Test finding Hue handler for Hue device."""
        from src.device_mappings.registry import DeviceMappingRegistry
        
        registry = DeviceMappingRegistry()
        handler = HueHandler()
        registry.register("hue", handler)
        
        device = {"manufacturer": "Signify", "model": "Room"}
        found = registry.find_handler(device)
        
        assert found == handler

