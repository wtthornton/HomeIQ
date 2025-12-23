"""
Test HA 2024 Naming Conventions

Tests for Story AI11.1: HA 2024 Naming Convention Implementation
"""

import pytest
from src.training.synthetic_device_generator import SyntheticDeviceGenerator


class TestEntityIDFormat:
    """Test entity ID format: {domain}.{area}_{device}_{detail}"""
    
    def test_light_entity_id_format(self):
        """Test light entity ID follows HA 2024 format."""
        generator = SyntheticDeviceGenerator()
        entity_id = generator._generate_entity_id('light', 'Kitchen', detail='ceiling')
        assert entity_id == 'light.kitchen_light_ceiling'
    
    def test_motion_sensor_entity_id(self):
        """Test motion sensor entity ID."""
        generator = SyntheticDeviceGenerator()
        entity_id = generator._generate_entity_id('binary_sensor', 'Bedroom', device_class='motion')
        assert entity_id == 'binary_sensor.bedroom_motion_sensor'
    
    def test_climate_entity_id(self):
        """Test climate entity ID."""
        generator = SyntheticDeviceGenerator()
        entity_id = generator._generate_entity_id('climate', 'Living Room')
        assert entity_id == 'climate.living_room_climate'
    
    def test_lock_entity_id(self):
        """Test lock entity ID."""
        generator = SyntheticDeviceGenerator()
        entity_id = generator._generate_entity_id('lock', 'Front Door', detail='front')
        assert entity_id == 'lock.front_door_lock_front'
    
    def test_media_player_entity_id(self):
        """Test media player entity ID."""
        generator = SyntheticDeviceGenerator()
        entity_id = generator._generate_entity_id('media_player', 'Living Room')
        assert entity_id == 'media_player.living_room_media_player'
    
    def test_door_sensor_entity_id(self):
        """Test door sensor entity ID."""
        generator = SyntheticDeviceGenerator()
        entity_id = generator._generate_entity_id('binary_sensor', 'Front Door', device_class='door')
        assert entity_id == 'binary_sensor.front_door_door_sensor'
    
    def test_temperature_sensor_entity_id(self):
        """Test temperature sensor entity ID."""
        generator = SyntheticDeviceGenerator()
        entity_id = generator._generate_entity_id('sensor', 'Bedroom', device_class='temperature')
        assert entity_id == 'sensor.bedroom_temperature_sensor'


class TestFriendlyNameFormat:
    """Test friendly name format: {Area} {Device} {Detail}"""
    
    def test_light_friendly_name(self):
        """Test light friendly name is human-readable."""
        generator = SyntheticDeviceGenerator()
        name = generator._generate_friendly_name('light', 'Kitchen', detail='ceiling')
        assert name == 'Kitchen Light Ceiling'
    
    def test_motion_sensor_friendly_name(self):
        """Test motion sensor friendly name."""
        generator = SyntheticDeviceGenerator()
        name = generator._generate_friendly_name('binary_sensor', 'Bedroom', device_class='motion')
        assert name == 'Bedroom Motion Sensor'
    
    def test_climate_friendly_name_voice(self):
        """Test climate friendly name uses voice-friendly alias."""
        generator = SyntheticDeviceGenerator()
        name = generator._generate_friendly_name('climate', 'Living Room', voice_friendly=True)
        assert name == 'Living Room Thermostat'
    
    def test_media_player_friendly_name_voice(self):
        """Test media player uses voice-friendly alias."""
        generator = SyntheticDeviceGenerator()
        name = generator._generate_friendly_name('media_player', 'Living Room', voice_friendly=True)
        assert name == 'Living Room TV'
    
    def test_door_sensor_friendly_name(self):
        """Test door sensor friendly name."""
        generator = SyntheticDeviceGenerator()
        name = generator._generate_friendly_name('binary_sensor', 'Front Door', device_class='door')
        assert name == 'Front Door Door Sensor'


class TestNormalization:
    """Test normalization methods."""
    
    def test_area_name_normalization(self):
        """Test area names are normalized to lowercase with underscores."""
        generator = SyntheticDeviceGenerator()
        assert generator._normalize_area_name('Living Room') == 'living_room'
        assert generator._normalize_area_name('Master Bedroom') == 'master_bedroom'
        assert generator._normalize_area_name('Front-Door') == 'front_door'
        assert generator._normalize_area_name('Garage/Basement') == 'garage_basement'
    
    def test_device_name_normalization(self):
        """Test device names are normalized."""
        generator = SyntheticDeviceGenerator()
        assert generator._normalize_device_name('light') == 'light'
        assert generator._normalize_device_name('binary_sensor', 'motion') == 'motion'
        assert generator._normalize_device_name('sensor', 'temperature') == 'temperature'
        assert generator._normalize_device_name('media_player') == 'media_player'
    
    def test_detail_normalization(self):
        """Test detail strings are normalized."""
        generator = SyntheticDeviceGenerator()
        assert generator._normalize_detail('Ceiling') == 'ceiling'
        assert generator._normalize_detail('Wall Mount') == 'wall_mount'
        assert generator._normalize_detail('front-door') == 'front_door'
    
    def test_humanize(self):
        """Test humanize converts snake_case to Title Case."""
        generator = SyntheticDeviceGenerator()
        assert generator._humanize('motion_sensor') == 'Motion Sensor'
        assert generator._humanize('living_room') == 'Living Room'
        assert generator._humanize('front-door') == 'Front Door'


class TestVoiceFriendlyNames:
    """Test voice-friendly aliases."""
    
    def test_voice_friendly_climate(self):
        """Test climate uses 'Thermostat' alias."""
        generator = SyntheticDeviceGenerator()
        name = generator._generate_friendly_name('climate', 'Bedroom', voice_friendly=True)
        assert 'Thermostat' in name
    
    def test_voice_friendly_media_player(self):
        """Test media player uses 'TV' alias."""
        generator = SyntheticDeviceGenerator()
        name = generator._generate_friendly_name('media_player', 'Living Room', voice_friendly=True)
        assert 'TV' in name
    
    def test_voice_friendly_motion_sensor(self):
        """Test motion sensor name."""
        generator = SyntheticDeviceGenerator()
        name = generator._generate_friendly_name('binary_sensor', 'Hallway', device_class='motion', voice_friendly=True)
        assert 'Motion Sensor' in name
    
    def test_voice_friendly_lock(self):
        """Test lock uses 'Lock' alias."""
        generator = SyntheticDeviceGenerator()
        name = generator._generate_friendly_name('lock', 'Front Door', voice_friendly=True)
        assert 'Lock' in name


class TestDeviceGeneration:
    """Test full device generation with HA 2024 naming."""
    
    def test_create_device_with_ha_naming(self):
        """Test _create_device applies HA 2024 naming."""
        generator = SyntheticDeviceGenerator()
        device = generator._create_device(
            device_type_str='light',
            category='lighting',
            area='Kitchen',
            index=0,
            device_class=None
        )
        
        # Check entity_id format
        assert device['entity_id'].startswith('light.kitchen_')
        assert '_' in device['entity_id']
        
        # Check friendly_name exists and is readable
        assert 'friendly_name' in device
        assert 'Kitchen' in device['friendly_name']
        assert 'Light' in device['friendly_name']
    
    def test_create_motion_sensor_with_ha_naming(self):
        """Test motion sensor creation with HA 2024 naming."""
        generator = SyntheticDeviceGenerator()
        device = generator._create_device(
            device_type_str='binary_sensor',
            category='security',
            area='Bedroom',
            index=0,
            device_class='motion'
        )
        
        # Check entity_id
        assert 'bedroom' in device['entity_id']
        assert 'motion' in device['entity_id']
        assert 'sensor' in device['entity_id']
        
        # Check friendly_name
        assert 'Bedroom' in device['friendly_name']
        assert 'Motion' in device['friendly_name']
    
    def test_generate_devices_consistency(self):
        """Test >95% of devices follow naming conventions."""
        generator = SyntheticDeviceGenerator()
        
        home_data = {
            'home_type': 'single_family_house',
            'size_category': 'medium',
            'metadata': {}
        }
        areas = [
            {'name': 'Kitchen'},
            {'name': 'Bedroom'},
            {'name': 'Living Room'}
        ]
        
        devices = generator.generate_devices(home_data, areas)
        
        # Check naming compliance
        compliant_count = 0
        for device in devices:
            entity_id = device['entity_id']
            friendly_name = device.get('friendly_name', device.get('name', ''))
            
            # Entity ID checks
            has_domain = '.' in entity_id
            has_underscores = '_' in entity_id
            is_lowercase = entity_id == entity_id.lower()
            
            # Friendly name checks
            has_friendly_name = bool(friendly_name)
            is_readable = ' ' in friendly_name or len(friendly_name.split('_')) == 1
            
            if has_domain and has_underscores and is_lowercase and has_friendly_name and is_readable:
                compliant_count += 1
        
        compliance_rate = compliant_count / len(devices)
        print(f"\nGenerated {len(devices)} devices")
        print(f"Compliance rate: {compliance_rate * 100:.1f}%")
        print(f"Compliant devices: {compliant_count}/{len(devices)}")
        
        assert compliance_rate >= 0.95, f"Naming compliance {compliance_rate * 100:.1f}% < 95%"
    
    def test_entity_id_uniqueness(self):
        """Test entity IDs are unique within a home."""
        generator = SyntheticDeviceGenerator()
        
        home_data = {
            'home_type': 'apartment',
            'size_category': 'small',
            'metadata': {}
        }
        areas = [
            {'name': 'Living Room'},
            {'name': 'Bedroom'}
        ]
        
        devices = generator.generate_devices(home_data, areas)
        entity_ids = [d['entity_id'] for d in devices]
        
        # Check for duplicates
        unique_ids = set(entity_ids)
        assert len(unique_ids) == len(entity_ids), "Entity IDs must be unique"


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""
    
    def test_device_has_name_field(self):
        """Test devices still have 'name' field for backward compatibility."""
        generator = SyntheticDeviceGenerator()
        device = generator._create_device(
            device_type_str='light',
            category='lighting',
            area='Kitchen',
            index=0
        )
        
        assert 'name' in device
        assert device['name'] == device['friendly_name']
    
    def test_device_has_required_fields(self):
        """Test devices have all required fields."""
        generator = SyntheticDeviceGenerator()
        device = generator._create_device(
            device_type_str='switch',
            category='appliances',
            area='Kitchen',
            index=0
        )
        
        required_fields = ['entity_id', 'device_type', 'name', 'area', 'category', 'friendly_name']
        for field in required_fields:
            assert field in device, f"Missing required field: {field}"


class TestDeviceDetails:
    """Test device detail generation."""
    
    def test_light_detail_cycling(self):
        """Test light details cycle through options."""
        generator = SyntheticDeviceGenerator()
        
        details = []
        for i in range(5):
            detail = generator._get_device_detail('light', None, i)
            details.append(detail)
        
        # Should have different details
        assert len(set(details)) > 1
        # Should cycle within valid options
        assert all(d in ['ceiling', 'wall', 'desk', 'floor', 'strip'] for d in details)
    
    def test_sensor_detail_generation(self):
        """Test sensor details are appropriate."""
        generator = SyntheticDeviceGenerator()
        
        detail = generator._get_device_detail('binary_sensor', 'motion', 0)
        assert detail in ['motion', 'presence', '']


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_empty_area_name(self):
        """Test handling of empty area name."""
        generator = SyntheticDeviceGenerator()
        entity_id = generator._generate_entity_id('light', '', detail='ceiling')
        assert entity_id.startswith('light.')
        assert len(entity_id) > len('light.')
    
    def test_special_characters_in_area(self):
        """Test special characters are normalized."""
        generator = SyntheticDeviceGenerator()
        entity_id = generator._generate_entity_id('switch', 'My-Living/Room!', detail='wall')
        # Should be normalized (no special chars except underscore)
        assert '!' not in entity_id
        assert '/' not in entity_id
        assert '-' not in entity_id or entity_id.count('-') == 0
    
    def test_long_device_names(self):
        """Test long device names are handled."""
        generator = SyntheticDeviceGenerator()
        entity_id = generator._generate_entity_id(
            'sensor',
            'Master Bedroom Walk In Closet',
            device_class='temperature',
            detail='ceiling_mounted'
        )
        # Should be valid (all lowercase, underscores)
        assert entity_id == entity_id.lower()
        assert ' ' not in entity_id

