"""
Synthetic Area Generator

Generate areas (rooms/spaces) for synthetic homes based on home type and description.
"""

import logging
from typing import Any

from ..llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class SyntheticAreaGenerator:
    """
    Generate areas and rooms for synthetic homes.
    
    Pipeline:
    1. Generate areas (rooms/spaces) from home description
    2. Assign area types (indoor/outdoor)
    3. Create area hierarchy if needed
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
    
    def __init__(self, openai_client: OpenAIClient):
        """
        Initialize area generator.
        
        Args:
            openai_client: OpenAI client for LLM generation
        """
        self.llm = openai_client
        logger.info("SyntheticAreaGenerator initialized")
    
    async def generate_areas(
        self,
        home_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Generate areas for a synthetic home.
        
        Args:
            home_data: Home data from synthetic home generator
        
        Returns:
            List of area dictionaries
        """
        home_type = home_data.get('home_type', 'single_family_house')
        home_metadata = home_data.get('metadata', {})
        home_desc = home_metadata.get('home', {}).get('description', '')
        
        # Try to extract areas from LLM response if available
        if 'areas' in home_metadata:
            areas = home_metadata['areas']
            logger.info(f"Using areas from home metadata: {len(areas)} areas")
            return areas
        
        # Fallback: Generate areas from template
        logger.info(f"Generating areas for {home_type} home...")
        areas = await self._generate_from_template(home_type, home_desc)
        
        return areas
    
    async def _generate_from_template(
        self,
        home_type: str,
        home_description: str
    ) -> list[dict[str, Any]]:
        """
        Generate areas from template with LLM enhancement.
        
        Args:
            home_type: Type of home
            home_description: Home description
        
        Returns:
            List of area dictionaries
        """
        template_areas = self.AREA_TEMPLATES.get(home_type, self.AREA_TEMPLATES['single_family_house'])
        
        # Use LLM to enhance and customize areas
        prompt = f"""Generate realistic areas/rooms for a {home_type} home.

Home Description: {home_description}

Base Areas: {', '.join(template_areas)}

Return a JSON array of areas with this structure:
[
    {{
        "name": "Area name",
        "type": "indoor|outdoor",
        "description": "Brief description of the area"
    }}
]

Requirements:
- Include all base areas
- Add 2-3 additional realistic areas if appropriate
- Mark outdoor areas (yard, balcony, porch) as type "outdoor"
- All other areas should be type "indoor"
- Keep descriptions concise (1-2 sentences)
"""
        
        try:
            response = await self.llm.generate_with_unified_prompt(
                prompt_dict={
                    "system_prompt": (
                        "You are a home automation expert generating realistic room/area layouts. "
                        "Return JSON arrays only."
                    ),
                    "user_prompt": prompt
                },
                temperature=0.7,
                max_tokens=800,
                output_format="json"
            )
            
            # Ensure response is a list
            if isinstance(response, list):
                areas = response
            elif isinstance(response, dict) and 'areas' in response:
                areas = response['areas']
            else:
                # Fallback to template
                areas = self._create_areas_from_template(template_areas)
            
            logger.info(f"✅ Generated {len(areas)} areas")
            return areas
            
        except Exception as e:
            logger.warning(f"LLM area generation failed, using template: {e}")
            return self._create_areas_from_template(template_areas)
    
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

