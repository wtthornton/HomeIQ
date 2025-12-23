"""
Test HA 2024 Area Hierarchy Features

Tests for Story AI11.2: Areas/Floors/Labels Hierarchy
"""

import pytest
from src.training.synthetic_area_generator import (
    SyntheticAreaGenerator,
    FloorType,
    LabelType
)
from src.training.synthetic_device_generator import SyntheticDeviceGenerator


class TestFloorGeneration:
    """Test floor hierarchy generation."""
    
    def test_single_story_has_ground_floor_only(self):
        """Test single-story homes have ground floor only."""
        generator = SyntheticAreaGenerator()
        home_data = {'home_type': 'apartment'}
        areas = generator.generate_areas(home_data)
        
        floors = {area['floor'] for area in areas}
        assert floors == {FloorType.GROUND.value}
    
    def test_multi_story_has_multiple_floors(self):
        """Test multi-story homes have multiple floors."""
        generator = SyntheticAreaGenerator()
        home_data = {'home_type': 'single_family_house'}
        areas = generator.generate_areas(home_data)
        
        floors = {area['floor'] for area in areas}
        assert FloorType.GROUND.value in floors
        # Should have at least one other floor (upstairs or basement)
        assert len(floors) > 1
    
    def test_townhouse_has_ground_and_upstairs(self):
        """Test townhouse has ground floor and upstairs."""
        generator = SyntheticAreaGenerator()
        home_data = {'home_type': 'townhouse'}
        areas = generator.generate_areas(home_data)
        
        floors = {area['floor'] for area in areas}
        assert FloorType.GROUND.value in floors
        assert FloorType.UPSTAIRS.value in floors
    
    def test_multi_story_home_has_basement(self):
        """Test multi-story homes can have basement."""
        generator = SyntheticAreaGenerator()
        home_data = {'home_type': 'multi_story'}
        areas = generator.generate_areas(home_data)
        
        floors = {area['floor'] for area in areas}
        assert FloorType.BASEMENT.value in floors or FloorType.ATTIC.value in floors


class TestAreaFloorAssignment:
    """Test areas are assigned to appropriate floors."""
    
    def test_living_room_on_ground_floor(self):
        """Test living room is on ground floor."""
        generator = SyntheticAreaGenerator()
        home_data = {'home_type': 'single_family_house'}
        areas = generator.generate_areas(home_data)
        
        living_room = next((a for a in areas if 'Living' in a['name'] or 'Family' in a['name'] or 'Great' in a['name']), None)
        if living_room:
            assert living_room['floor'] == FloorType.GROUND.value
    
    def test_kitchen_on_ground_floor(self):
        """Test kitchen is on ground floor."""
        generator = SyntheticAreaGenerator()
        home_data = {'home_type': 'condo'}
        areas = generator.generate_areas(home_data)
        
        kitchen = next((a for a in areas if 'Kitchen' in a['name']), None)
        if kitchen:
            assert kitchen['floor'] == FloorType.GROUND.value
    
    def test_bedrooms_typically_upstairs_multi_story(self):
        """Test bedrooms are typically upstairs in multi-story homes."""
        generator = SyntheticAreaGenerator()
        home_data = {'home_type': 'townhouse'}
        areas = generator.generate_areas(home_data)
        
        bedrooms = [a for a in areas if 'Bedroom' in a['name']]
        if bedrooms:
            # At least some bedrooms should be upstairs
            upstairs_bedrooms = [b for b in bedrooms if b['floor'] == FloorType.UPSTAIRS.value]
            assert len(upstairs_bedrooms) > 0
    
    def test_bedrooms_ground_floor_single_story(self):
        """Test bedrooms are on ground floor in single-story homes."""
        generator = SyntheticAreaGenerator()
        home_data = {'home_type': 'apartment'}
        areas = generator.generate_areas(home_data)
        
        bedrooms = [a for a in areas if 'Bedroom' in a['name']]
        if bedrooms:
            # All bedrooms should be on ground floor
            assert all(b['floor'] == FloorType.GROUND.value for b in bedrooms)
    
    def test_garage_on_ground_floor(self):
        """Test garage is on ground floor."""
        generator = SyntheticAreaGenerator()
        home_data = {'home_type': 'single_family_house'}
        areas = generator.generate_areas(home_data)
        
        garage = next((a for a in areas if 'Garage' in a['name']), None)
        if garage:
            assert garage['floor'] == FloorType.GROUND.value
    
    def test_basement_on_basement_floor(self):
        """Test basement area is on basement floor."""
        generator = SyntheticAreaGenerator()
        home_data = {'home_type': 'multi_story'}
        areas = generator.generate_areas(home_data)
        
        basement = next((a for a in areas if 'Basement' in a['name']), None)
        if basement:
            assert basement['floor'] == FloorType.BASEMENT.value


class TestLabelGeneration:
    """Test label system for device grouping."""
    
    def test_security_label_assignment(self):
        """Test security devices get security label."""
        area_gen = SyntheticAreaGenerator()
        device_gen = SyntheticDeviceGenerator()
        
        # Create a motion sensor device
        device = device_gen._create_device(
            device_type_str='binary_sensor',
            category='security',
            area='Bedroom',
            index=0,
            device_class='motion'
        )
        
        labels = area_gen.generate_labels([device])
        
        assert LabelType.SECURITY.value in labels
        assert device['entity_id'] in labels[LabelType.SECURITY.value]
    
    def test_climate_label_assignment(self):
        """Test climate devices get climate label."""
        area_gen = SyntheticAreaGenerator()
        device_gen = SyntheticDeviceGenerator()
        
        # Create a thermostat device
        device = device_gen._create_device(
            device_type_str='climate',
            category='climate',
            area='Living Room',
            index=0
        )
        
        labels = area_gen.generate_labels([device])
        
        assert LabelType.CLIMATE.value in labels
        assert device['entity_id'] in labels[LabelType.CLIMATE.value]
    
    def test_energy_label_assignment(self):
        """Test energy devices get energy label."""
        area_gen = SyntheticAreaGenerator()
        device_gen = SyntheticDeviceGenerator()
        
        # Create a power monitor
        device = device_gen._create_device(
            device_type_str='sensor',
            category='monitoring',
            area='Kitchen',
            index=0,
            device_class='power'
        )
        
        labels = area_gen.generate_labels([device])
        
        assert LabelType.ENERGY.value in labels
        assert device['entity_id'] in labels[LabelType.ENERGY.value]
    
    def test_multiple_labels_per_device(self):
        """Test devices can have multiple labels."""
        area_gen = SyntheticAreaGenerator()
        device_gen = SyntheticDeviceGenerator()
        
        # Create a climate device (should have both climate and energy labels)
        device = device_gen._create_device(
            device_type_str='climate',
            category='climate',
            area='Bedroom',
            index=0
        )
        
        labels = area_gen.generate_labels([device])
        
        # Climate devices should be in both climate and energy labels
        assert LabelType.CLIMATE.value in labels
        assert LabelType.ENERGY.value in labels
        assert device['entity_id'] in labels[LabelType.CLIMATE.value]
        assert device['entity_id'] in labels[LabelType.ENERGY.value]
    
    def test_empty_labels_removed(self):
        """Test labels with no devices are not included."""
        area_gen = SyntheticAreaGenerator()
        device_gen = SyntheticDeviceGenerator()
        
        # Create a light device (only energy label)
        device = device_gen._create_device(
            device_type_str='light',
            category='lighting',
            area='Kitchen',
            index=0
        )
        
        labels = area_gen.generate_labels([device])
        
        # Should not have labels for kids, holiday, etc
        assert LabelType.KIDS.value not in labels
        assert LabelType.HOLIDAY.value not in labels


class TestGroupGeneration:
    """Test logical device group generation."""
    
    def test_all_lights_group(self):
        """Test 'all_lights' group is created."""
        area_gen = SyntheticAreaGenerator()
        device_gen = SyntheticDeviceGenerator()
        
        # Create multiple light devices
        devices = [
            device_gen._create_device('light', 'lighting', 'Kitchen', 0),
            device_gen._create_device('light', 'lighting', 'Bedroom', 1),
            device_gen._create_device('binary_sensor', 'security', 'Hallway', 0, 'motion')
        ]
        
        areas = [{'name': 'Kitchen'}, {'name': 'Bedroom'}]
        groups = area_gen.generate_groups(devices, areas)
        
        assert 'all_lights' in groups
        assert len(groups['all_lights']) == 2
    
    def test_security_sensors_group(self):
        """Test 'security_sensors' group is created."""
        area_gen = SyntheticAreaGenerator()
        device_gen = SyntheticDeviceGenerator()
        
        # Create security devices
        devices = [
            device_gen._create_device('binary_sensor', 'security', 'Front Door', 0, 'door'),
            device_gen._create_device('binary_sensor', 'security', 'Bedroom', 1, 'motion'),
            device_gen._create_device('lock', 'security', 'Front Door', 0)
        ]
        
        areas = [{'name': 'Front Door'}, {'name': 'Bedroom'}]
        groups = area_gen.generate_groups(devices, areas)
        
        assert 'security_sensors' in groups
        assert len(groups['security_sensors']) == 3
    
    def test_climate_control_group(self):
        """Test 'climate_control' group is created."""
        area_gen = SyntheticAreaGenerator()
        device_gen = SyntheticDeviceGenerator()
        
        # Create climate devices
        devices = [
            device_gen._create_device('climate', 'climate', 'Living Room', 0),
            device_gen._create_device('sensor', 'climate', 'Bedroom', 0, 'temperature')
        ]
        
        areas = [{'name': 'Living Room'}, {'name': 'Bedroom'}]
        groups = area_gen.generate_groups(devices, areas)
        
        assert 'climate_control' in groups
        assert len(groups['climate_control']) == 2
    
    def test_area_specific_lights_group(self):
        """Test area-specific light groups are created."""
        area_gen = SyntheticAreaGenerator()
        device_gen = SyntheticDeviceGenerator()
        
        # Create multiple lights in same area
        devices = [
            device_gen._create_device('light', 'lighting', 'Kitchen', 0),
            device_gen._create_device('light', 'lighting', 'Kitchen', 1)
        ]
        
        areas = [{'name': 'Kitchen'}]
        groups = area_gen.generate_groups(devices, areas)
        
        assert 'kitchen_lights' in groups
        assert len(groups['kitchen_lights']) == 2
    
    def test_floor_specific_lights_group(self):
        """Test floor-specific light groups are created for multi-floor homes."""
        area_gen = SyntheticAreaGenerator()
        device_gen = SyntheticDeviceGenerator()
        
        # Create lights on different floors
        devices = [
            device_gen._create_device('light', 'lighting', 'Living Room', 0),
            device_gen._create_device('light', 'lighting', 'Master Bedroom', 1),
            device_gen._create_device('light', 'lighting', 'Bedroom 2', 2)
        ]
        
        areas = [
            {'name': 'Living Room', 'floor': FloorType.GROUND.value},
            {'name': 'Master Bedroom', 'floor': FloorType.UPSTAIRS.value},
            {'name': 'Bedroom 2', 'floor': FloorType.UPSTAIRS.value}
        ]
        
        groups = area_gen.generate_groups(devices, areas)
        
        # Should have upstairs_lights group
        assert 'upstairslights' in groups or 'upstairs_lights' in groups


class TestIntegration:
    """Test integration of floors, labels, and groups."""
    
    def test_full_home_generation_with_hierarchy(self):
        """Test complete home generation with all organizational features."""
        area_gen = SyntheticAreaGenerator()
        device_gen = SyntheticDeviceGenerator()
        
        # Generate home
        home_data = {'home_type': 'townhouse', 'size_category': 'medium', 'metadata': {}}
        areas = area_gen.generate_areas(home_data)
        
        # Verify floor assignments
        assert all('floor' in area for area in areas)
        floors = {area['floor'] for area in areas}
        assert len(floors) > 0
        
        # Generate devices
        devices = device_gen.generate_devices(home_data, areas)
        
        # Generate labels
        labels = area_gen.generate_labels(devices)
        
        # Generate groups
        groups = area_gen.generate_groups(devices, areas)
        
        # Verify structure
        assert len(areas) > 0
        assert len(devices) > 0
        assert len(labels) > 0
        assert len(groups) > 0
        
        print(f"\n✅ Generated home with {len(areas)} areas, {len(devices)} devices")
        print(f"   Floors: {floors}")
        print(f"   Labels: {list(labels.keys())}")
        print(f"   Groups: {list(groups.keys())}")
    
    def test_backward_compatibility(self):
        """Test areas without floor assignments get them added."""
        area_gen = SyntheticAreaGenerator()
        
        # Old-style areas without floors
        old_areas = [
            {'name': 'Living Room', 'type': 'indoor'},
            {'name': 'Bedroom', 'type': 'indoor'}
        ]
        
        # Add floor assignments
        updated_areas = area_gen._add_floor_assignments(old_areas, 'apartment')
        
        # Verify floors added
        assert all('floor' in area for area in updated_areas)
        assert all(area['floor'] == FloorType.GROUND.value for area in updated_areas)


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_unknown_home_type(self):
        """Test handling of unknown home type."""
        area_gen = SyntheticAreaGenerator()
        home_data = {'home_type': 'unknown_type'}
        areas = area_gen.generate_areas(home_data)
        
        # Should still generate areas (fallback to single_family_house)
        assert len(areas) > 0
        # Should have floor assignments
        assert all('floor' in area for area in areas)
    
    def test_no_devices_labels_and_groups(self):
        """Test label and group generation with no devices."""
        area_gen = SyntheticAreaGenerator()
        
        labels = area_gen.generate_labels([])
        groups = area_gen.generate_groups([], [])
        
        # Should return empty dicts
        assert labels == {}
        assert groups == {}
    
    def test_single_light_no_area_group(self):
        """Test single light in area doesn't create area group."""
        area_gen = SyntheticAreaGenerator()
        device_gen = SyntheticDeviceGenerator()
        
        # Single light
        devices = [device_gen._create_device('light', 'lighting', 'Kitchen', 0)]
        areas = [{'name': 'Kitchen'}]
        
        groups = area_gen.generate_groups(devices, areas)
        
        # Should not create kitchen_lights group (needs >1 light)
        assert 'kitchen_lights' not in groups

