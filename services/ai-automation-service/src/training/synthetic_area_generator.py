"""
Synthetic Area Generator

Generate areas (rooms/spaces) for synthetic homes based on home type using templates.
"""

import logging
import random
from typing import Any

logger = logging.getLogger(__name__)


class SyntheticAreaGenerator:
    """
    Generate areas and rooms for synthetic homes using templates.
    
    Uses predefined area templates for each home type with randomization.
    """
    
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
        Generate areas for a synthetic home using templates.
        
        Args:
            home_data: Home data from synthetic home generator
        
        Returns:
            List of area dictionaries
        """
        home_type = home_data.get('home_type', 'single_family_house')
        home_metadata = home_data.get('metadata', {})
        
        # Try to extract areas from metadata if available (for backward compatibility)
        if 'areas' in home_metadata:
            areas = home_metadata['areas']
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
        Generate areas from template with randomization.
        
        Args:
            home_type: Type of home
        
        Returns:
            List of area dictionaries
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
        
        logger.info(f"✅ Generated {len(areas)} areas")
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

