"""
Synthetic Area Generator

Generate areas (rooms/spaces) for synthetic homes based on home type using templates.

Enhanced with HA 2024 organizational features:
- Floor hierarchy (ground, upstairs, basement, attic)
- Label system for thematic grouping
- Area-to-floor mappings
"""

import logging
import random
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class FloorType(str, Enum):
    """Floor types for multi-story homes (HA 2024 standard)."""
    GROUND = "ground_floor"
    UPSTAIRS = "upstairs"
    DOWNSTAIRS = "downstairs"
    BASEMENT = "basement"
    ATTIC = "attic"


class LabelType(str, Enum):
    """Thematic labels for device grouping (HA 2024 standard)."""
    SECURITY = "security"
    CLIMATE = "climate"
    ENERGY = "energy"
    HOLIDAY = "holiday"
    KIDS = "kids"
    ENTERTAINMENT = "entertainment"
    HEALTH = "health"


class SyntheticAreaGenerator:
    """
    Generate areas and rooms for synthetic homes with HA 2024 organization.
    
    Features:
    - Floor hierarchy per home type
    - Area-to-floor assignments
    - Label system for thematic grouping
    - Realistic organizational patterns
    """
    
    # Floor configurations by home type
    FLOOR_CONFIGS = {
        'single_family_house': [FloorType.GROUND, FloorType.UPSTAIRS, FloorType.BASEMENT],
        'apartment': [FloorType.GROUND],
        'condo': [FloorType.GROUND, FloorType.UPSTAIRS],
        'townhouse': [FloorType.GROUND, FloorType.UPSTAIRS],
        'cottage': [FloorType.GROUND],
        'studio': [FloorType.GROUND],
        'multi_story': [FloorType.GROUND, FloorType.UPSTAIRS, FloorType.BASEMENT, FloorType.ATTIC],
        'ranch_house': [FloorType.GROUND, FloorType.BASEMENT]
    }
    
    # Area-to-floor mapping (realistic room placement)
    AREA_FLOOR_MAPPING = {
        # Living spaces - typically ground floor
        'Living Room': FloorType.GROUND,
        'Family Room': FloorType.GROUND,
        'Great Room': FloorType.GROUND,
        'Living Space': FloorType.GROUND,
        'Kitchen': FloorType.GROUND,
        'Kitchen Area': FloorType.GROUND,
        'Cooking Space': FloorType.GROUND,
        'Dining Room': FloorType.GROUND,
        'Entryway': FloorType.GROUND,
        'Hallway': FloorType.GROUND,
        
        # Bedrooms - typically upstairs (or ground for single-story)
        'Master Bedroom': FloorType.UPSTAIRS,
        'Primary Bedroom': FloorType.UPSTAIRS,
        'Main Bedroom': FloorType.UPSTAIRS,
        'Bedroom': FloorType.UPSTAIRS,
        'Bedroom 2': FloorType.UPSTAIRS,
        'Bedroom 3': FloorType.UPSTAIRS,
        'Bedroom 4': FloorType.UPSTAIRS,
        'Guest Bedroom': FloorType.UPSTAIRS,
        'Second Bedroom': FloorType.UPSTAIRS,
        
        # Bathrooms - split between floors
        'Master Bathroom': FloorType.UPSTAIRS,
        'Primary Bathroom': FloorType.UPSTAIRS,
        'Ensuite Bathroom': FloorType.UPSTAIRS,
        'Bathroom': FloorType.GROUND,
        'Full Bath': FloorType.GROUND,
        
        # Utility spaces - ground or basement
        'Garage': FloorType.GROUND,
        'Laundry Room': FloorType.BASEMENT,
        'Office': FloorType.GROUND,
        'Pantry': FloorType.GROUND,
        'Storage': FloorType.BASEMENT,
        
        # Basement/attic specific
        'Basement': FloorType.BASEMENT,
        'Attic': FloorType.ATTIC,
        'Workshop': FloorType.BASEMENT,
        'Library': FloorType.GROUND,
        
        # Outdoor spaces - ground level
        'Backyard': FloorType.GROUND,
        'Front Yard': FloorType.GROUND,
        'Balcony': FloorType.GROUND,  # Will adjust for multi-story
        'Porch': FloorType.GROUND,
        'Garden': FloorType.GROUND,
        'Patio': FloorType.GROUND,
        'Deck': FloorType.GROUND,
        
        # Special spaces
        'Main Room': FloorType.GROUND,  # Studio
        'Closet': FloorType.GROUND,
        'Shed': FloorType.GROUND
    }
    
    # Device label mappings (device_type -> labels)
    DEVICE_LABEL_MAPPING = {
        # Security devices
        'binary_sensor.motion': [LabelType.SECURITY],
        'binary_sensor.door': [LabelType.SECURITY],
        'binary_sensor.window': [LabelType.SECURITY],
        'lock': [LabelType.SECURITY],
        'camera': [LabelType.SECURITY],
        'alarm_control_panel': [LabelType.SECURITY],
        'binary_sensor.smoke': [LabelType.SECURITY, LabelType.HEALTH],
        
        # Climate devices
        'climate': [LabelType.CLIMATE, LabelType.ENERGY],
        'sensor.temperature': [LabelType.CLIMATE],
        'sensor.humidity': [LabelType.CLIMATE],
        'fan': [LabelType.CLIMATE],
        
        # Energy devices
        'sensor.power': [LabelType.ENERGY],
        'sensor.energy': [LabelType.ENERGY],
        'sensor.battery': [LabelType.ENERGY],
        'switch': [LabelType.ENERGY],  # Smart plugs
        'light': [LabelType.ENERGY],
        
        # Entertainment
        'media_player': [LabelType.ENTERTAINMENT],
        
        # Other
        'vacuum': [LabelType.ENERGY],
        'cover': [LabelType.ENERGY]
    }
    
    # Common area types by home type
    AREA_TEMPLATES = {
        'single_family_house': [
            'Living Room', 'Kitchen', 'Master Bedroom', 'Bedroom 2', 'Bedroom 3',
            'Bathroom', 'Master Bathroom', 'Garage', 'Backyard', 'Front Yard'
        ],
        'apartment': [
            'Living Room', 'Kitchen', 'Bedroom', 'Bathroom', 'Balcony'
        ],
        'condo': [
            'Living Room', 'Kitchen', 'Master Bedroom', 'Bedroom 2',
            'Bathroom', 'Balcony', 'Garage'
        ],
        'townhouse': [
            'Living Room', 'Kitchen', 'Master Bedroom', 'Bedroom 2',
            'Bathroom', 'Garage', 'Backyard', 'Front Yard'
        ],
        'cottage': [
            'Living Room', 'Kitchen', 'Bedroom', 'Bathroom', 'Porch', 'Garden'
        ],
        'studio': [
            'Main Room', 'Kitchen Area', 'Bathroom', 'Closet'
        ],
        'multi_story': [
            'Living Room', 'Kitchen', 'Dining Room', 'Master Bedroom',
            'Bedroom 2', 'Bedroom 3', 'Bedroom 4', 'Bathroom', 'Master Bathroom',
            'Garage', 'Basement', 'Attic', 'Backyard', 'Front Yard'
        ],
        'ranch_house': [
            'Living Room', 'Kitchen', 'Master Bedroom', 'Bedroom 2', 'Bedroom 3',
            'Bathroom', 'Master Bathroom', 'Garage', 'Backyard', 'Front Yard'
        ]
    }
    
    def __init__(self):
        """
        Initialize area generator.
        """
        logger.info("SyntheticAreaGenerator initialized")
    
    def generate_areas(
        self,
        home_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Generate areas for a synthetic home with floor assignments and HA 2024 organization.
        
        Args:
            home_data: Home data from synthetic home generator
        
        Returns:
            List of area dictionaries with floor assignments
        """
        home_type = home_data.get('home_type', 'single_family_house')
        home_metadata = home_data.get('metadata', {})
        
        # Try to extract areas from metadata if available (for backward compatibility)
        if 'areas' in home_metadata:
            areas = home_metadata['areas']
            # Add floor assignments if missing (for backward compatibility)
            if areas and 'floor' not in areas[0]:
                areas = self._add_floor_assignments(areas, home_type)
            logger.info(f"Using areas from home metadata: {len(areas)} areas")
            return areas
        
        # Generate areas from template with randomization
        logger.info(f"Generating areas for {home_type} home...")
        areas = self._generate_from_template(home_type)
        
        return areas
    
    def _generate_from_template(
        self,
        home_type: str
    ) -> list[dict[str, Any]]:
        """
        Generate areas from template with floor assignments and HA 2024 organization.
        
        Args:
            home_type: Type of home
        
        Returns:
            List of area dictionaries with floor assignments
        """
        # Get template areas, fallback to single_family_house if home_type not found
        template_areas = self.AREA_TEMPLATES.get(
            home_type,
            self.AREA_TEMPLATES.get('single_family_house', ['Living Room', 'Kitchen', 'Bedroom', 'Bathroom'])
        )
        
        # Create base areas from template
        areas = self._create_areas_from_template(template_areas)
        
        # Add 0-2 optional areas based on home type for variation
        optional_areas_by_type = {
            'single_family_house': ['Office', 'Laundry Room', 'Pantry'],
            'apartment': ['Storage', 'Entryway'],
            'condo': ['Office', 'Storage'],
            'townhouse': ['Office', 'Laundry Room'],
            'cottage': ['Shed', 'Workshop'],
            'studio': ['Entryway'],
            'multi_story': ['Office', 'Laundry Room', 'Pantry', 'Library'],
            'ranch_house': ['Office', 'Laundry Room', 'Pantry']
        }
        
        optional_areas = optional_areas_by_type.get(home_type, [])
        if optional_areas and random.random() < 0.6:  # 60% chance to add optional areas
            num_optional = random.randint(0, min(2, len(optional_areas)))
            if num_optional > 0:
                selected_optional = random.sample(optional_areas, num_optional)
                optional_area_dicts = self._create_areas_from_template(selected_optional)
                areas.extend(optional_area_dicts)
        
        # Vary area names slightly for diversity
        for area in areas:
            if random.random() < 0.2:  # 20% chance to vary name
                name_variations = {
                    'Living Room': ['Family Room', 'Great Room', 'Living Space'],
                    'Kitchen': ['Kitchen Area', 'Cooking Space'],
                    'Master Bedroom': ['Primary Bedroom', 'Main Bedroom'],
                    'Bedroom 2': ['Guest Bedroom', 'Second Bedroom'],
                    'Bathroom': ['Full Bath', 'Bathroom'],
                    'Master Bathroom': ['Primary Bathroom', 'Ensuite Bathroom']
                }
                if area['name'] in name_variations:
                    area['name'] = random.choice(name_variations[area['name']])
        
        # Add floor assignments
        areas = self._add_floor_assignments(areas, home_type)
        
        logger.info(f"✅ Generated {len(areas)} areas with floor assignments")
        return areas
    
    def _create_areas_from_template(
        self,
        area_names: list[str]
    ) -> list[dict[str, Any]]:
        """
        Create area dictionaries from template names.
        
        Args:
            area_names: List of area names
        
        Returns:
            List of area dictionaries
        """
        outdoor_keywords = ['yard', 'balcony', 'porch', 'garden', 'patio', 'deck']
        
        areas = []
        for name in area_names:
            area_type = 'outdoor' if any(kw in name.lower() for kw in outdoor_keywords) else 'indoor'
            areas.append({
                'name': name,
                'type': area_type,
                'description': f"{name} in the home"
            })
        
        return areas
    
    def _add_floor_assignments(
        self,
        areas: list[dict[str, Any]],
        home_type: str
    ) -> list[dict[str, Any]]:
        """
        Add floor assignments to areas based on home type and HA 2024 patterns.
        
        Args:
            areas: List of area dictionaries
            home_type: Type of home
        
        Returns:
            Areas with floor assignments added
        """
        # Get available floors for this home type
        available_floors = self.FLOOR_CONFIGS.get(
            home_type,
            [FloorType.GROUND]
        )
        
        # For single-floor homes, all areas are on ground floor
        if len(available_floors) == 1:
            for area in areas:
                area['floor'] = available_floors[0].value
            return areas
        
        # For multi-floor homes, assign based on area type
        for area in areas:
            area_name = area['name']
            
            # Get default floor assignment for this area
            default_floor = self.AREA_FLOOR_MAPPING.get(area_name, FloorType.GROUND)
            
            # Adjust for available floors (e.g., if no upstairs, put bedrooms on ground)
            if default_floor not in available_floors:
                if default_floor == FloorType.UPSTAIRS and FloorType.GROUND in available_floors:
                    default_floor = FloorType.GROUND
                elif default_floor == FloorType.BASEMENT and FloorType.GROUND in available_floors:
                    default_floor = FloorType.GROUND
                elif default_floor == FloorType.ATTIC and FloorType.UPSTAIRS in available_floors:
                    default_floor = FloorType.UPSTAIRS
                else:
                    default_floor = available_floors[0]  # Fallback to first floor
            
            area['floor'] = default_floor.value
        
        return areas
    
    def generate_labels(
        self,
        devices: list[dict[str, Any]]
    ) -> dict[str, list[str]]:
        """
        Generate thematic labels for devices (HA 2024 organization).
        
        Args:
            devices: List of device dictionaries
        
        Returns:
            Dictionary mapping label names to device entity IDs
        """
        labels: dict[str, list[str]] = {
            label_type.value: [] for label_type in LabelType
        }
        
        for device in devices:
            entity_id = device.get('entity_id', '')
            device_type = device.get('device_type', '')
            device_class = device.get('device_class')
            
            # Build lookup key
            if device_class:
                lookup_key = f"{device_type}.{device_class}"
            else:
                lookup_key = device_type
            
            # Get labels for this device type
            device_labels = self.DEVICE_LABEL_MAPPING.get(lookup_key, [])
            
            # Fallback to device type without class
            if not device_labels and device_class:
                device_labels = self.DEVICE_LABEL_MAPPING.get(device_type, [])
            
            # Add device to each applicable label
            for label in device_labels:
                labels[label.value].append(entity_id)
        
        # Remove empty labels
        labels = {k: v for k, v in labels.items() if v}
        
        logger.info(f"✅ Generated labels for {len(devices)} devices across {len(labels)} categories")
        return labels
    
    def generate_groups(
        self,
        devices: list[dict[str, Any]],
        areas: list[dict[str, Any]]
    ) -> dict[str, list[str]]:
        """
        Generate logical device groups (HA 2024 organization).
        
        Args:
            devices: List of device dictionaries
            areas: List of area dictionaries
        
        Returns:
            Dictionary mapping group names to device entity IDs
        """
        groups: dict[str, list[str]] = {}
        
        # Group 1: All lights
        all_lights = [d['entity_id'] for d in devices if d.get('device_type') == 'light']
        if all_lights:
            groups['all_lights'] = all_lights
        
        # Group 2: All security sensors
        security_types = ['binary_sensor.motion', 'binary_sensor.door', 'binary_sensor.window', 'lock', 'camera']
        all_security = []
        for device in devices:
            device_type = device.get('device_type', '')
            device_class = device.get('device_class')
            lookup_key = f"{device_type}.{device_class}" if device_class else device_type
            if lookup_key in security_types or device_type in ['lock', 'camera', 'alarm_control_panel']:
                all_security.append(device['entity_id'])
        if all_security:
            groups['security_sensors'] = all_security
        
        # Group 3: All climate devices
        climate_types = ['climate', 'sensor.temperature', 'sensor.humidity', 'fan']
        all_climate = []
        for device in devices:
            device_type = device.get('device_type', '')
            device_class = device.get('device_class')
            lookup_key = f"{device_type}.{device_class}" if device_class else device_type
            if lookup_key in climate_types or device_type == 'climate':
                all_climate.append(device['entity_id'])
        if all_climate:
            groups['climate_control'] = all_climate
        
        # Group 4: Area-specific groups (lights per area)
        area_names = {area['name'] for area in areas}
        for area_name in area_names:
            area_lights = [d['entity_id'] for d in devices 
                          if d.get('device_type') == 'light' and d.get('area') == area_name]
            if area_lights and len(area_lights) > 1:
                group_name = f"{area_name.lower().replace(' ', '_')}_lights"
                groups[group_name] = area_lights
        
        # Group 5: Floor-specific groups (if multi-floor)
        floors = {area.get('floor') for area in areas if area.get('floor')}
        if len(floors) > 1:
            for floor in floors:
                # Get areas on this floor
                floor_areas = {area['name'] for area in areas if area.get('floor') == floor}
                # Get lights in these areas
                floor_lights = [d['entity_id'] for d in devices 
                               if d.get('device_type') == 'light' and d.get('area') in floor_areas]
                if floor_lights and len(floor_lights) > 1:
                    floor_name = floor.replace('_', ' ').title().replace(' ', '')
                    group_name = f"{floor_name.lower()}_lights"
                    groups[group_name] = floor_lights
        
        logger.info(f"✅ Generated {len(groups)} device groups")
        return groups

