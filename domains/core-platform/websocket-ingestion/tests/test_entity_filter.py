"""
Unit tests for Entity Filter (Epic 45.2)
"""

import pytest
from src.entity_filter import EntityFilter


def test_filter_exclude_mode():
    """Test exclude mode (opt-out)"""
    config = {
        "mode": "exclude",
        "patterns": [
            {"entity_id": "sensor.*_battery"},
            {"device_class": "battery"}
        ]
    }
    filter_obj = EntityFilter(config)
    
    # Should exclude battery sensors
    assert not filter_obj.should_include({"entity_id": "sensor.device_battery"})
    assert not filter_obj.should_include({"device_class": "battery"})
    
    # Should include other entities
    assert filter_obj.should_include({"entity_id": "sensor.temperature"})
    assert filter_obj.should_include({"entity_id": "light.living_room"})


def test_filter_include_mode():
    """Test include mode (opt-in)"""
    config = {
        "mode": "include",
        "patterns": [
            {"domain": "sensor"},
            {"domain": "light"}
        ]
    }
    filter_obj = EntityFilter(config)
    
    # Should include matching entities
    assert filter_obj.should_include({"entity_id": "sensor.temperature"})
    assert filter_obj.should_include({"entity_id": "light.living_room"})
    
    # Should exclude non-matching entities
    assert not filter_obj.should_include({"entity_id": "switch.kitchen"})


def test_filter_exceptions():
    """Test exception patterns (always included)"""
    config = {
        "mode": "exclude",
        "patterns": [
            {"entity_id": "sensor.*_battery"}
        ],
        "exceptions": [
            {"entity_id": "sensor.important_battery"}
        ]
    }
    filter_obj = EntityFilter(config)
    
    # Exception should override filter
    assert filter_obj.should_include({"entity_id": "sensor.important_battery"})
    
    # Other battery sensors should be filtered
    assert not filter_obj.should_include({"entity_id": "sensor.device_battery"})


def test_filter_domain():
    """Test filtering by domain"""
    config = {
        "mode": "exclude",
        "patterns": [
            {"domain": "diagnostic"}
        ]
    }
    filter_obj = EntityFilter(config)
    
    # Should extract domain from entity_id
    assert not filter_obj.should_include({"entity_id": "diagnostic.sensor"})
    assert filter_obj.should_include({"entity_id": "sensor.temperature"})


def test_filter_device_class():
    """Test filtering by device_class"""
    config = {
        "mode": "exclude",
        "patterns": [
            {"device_class": "battery"}
        ]
    }
    filter_obj = EntityFilter(config)
    
    assert not filter_obj.should_include({"device_class": "battery"})
    assert filter_obj.should_include({"device_class": "temperature"})


def test_filter_area_id():
    """Test filtering by area_id"""
    config = {
        "mode": "exclude",
        "patterns": [
            {"area_id": "garage"}
        ]
    }
    filter_obj = EntityFilter(config)
    
    assert not filter_obj.should_include({"area_id": "garage"})
    assert filter_obj.should_include({"area_id": "living_room"})


def test_filter_statistics():
    """Test filter statistics tracking"""
    config = {
        "mode": "exclude",
        "patterns": [{"entity_id": "sensor.*_battery"}]
    }
    filter_obj = EntityFilter(config)
    
    # Process some events
    filter_obj.should_include({"entity_id": "sensor.battery"})  # Filtered
    filter_obj.should_include({"entity_id": "sensor.temperature"})  # Passed
    filter_obj.should_include({"entity_id": "sensor.battery2"})  # Filtered
    
    stats = filter_obj.get_statistics()
    assert stats["filtered_count"] == 2
    assert stats["passed_count"] == 1
    assert stats["mode"] == "exclude"


def test_filter_no_config():
    """Test filter with no configuration (default: include all)"""
    filter_obj = EntityFilter()
    
    # Should include all entities by default
    assert filter_obj.should_include({"entity_id": "sensor.temperature"})
    assert filter_obj.should_include({"entity_id": "light.living_room"})


def test_filter_reload_config():
    """Test reloading filter configuration"""
    config1 = {
        "mode": "exclude",
        "patterns": [{"entity_id": "sensor.*_battery"}]
    }
    filter_obj = EntityFilter(config1)
    
    assert not filter_obj.should_include({"entity_id": "sensor.battery"})
    
    # Reload with new config
    config2 = {
        "mode": "include",
        "patterns": [{"domain": "sensor"}]
    }
    filter_obj.reload_config(config2)
    
    assert filter_obj.should_include({"entity_id": "sensor.battery"})
    assert not filter_obj.should_include({"entity_id": "light.living_room"})

