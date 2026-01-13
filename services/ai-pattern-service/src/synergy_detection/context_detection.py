"""
Context-Aware Detection Module

Detects context-aware synergies based on weather, energy, and carbon data.

These synergies combine multiple context factors to suggest automations
that optimize for comfort, cost, and sustainability.

Extracted from synergy_detector.py for better maintainability.
"""

import logging
import uuid
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# Configuration constants
MAX_CONTEXT_SYNERGIES = 30  # Maximum context-aware synergies to generate
MAX_DEVICES_PER_CONTEXT_TYPE = 5  # Maximum devices per context type

# High-power device domains that benefit from energy scheduling
HIGH_POWER_DOMAINS = {'climate', 'water_heater', 'dryer', 'washer', 'dishwasher', 'ev_charger'}


class ContextAwareDetector:
    """
    Detects context-aware synergies based on environmental, energy, sports, calendar, and carbon data.
    
    Context types supported:
    - Weather + Climate: Pre-cool/heat based on forecast
    - Weather + Cover: Close blinds when sunny
    - Weather + Light: Adjust lighting based on conditions
    - Energy + High-power devices: Schedule for off-peak hours
    - Carbon Intensity + High-power devices: Schedule for low-carbon hours
    - Sports + Lighting: Set lighting for game time
    - Sports + Media: Auto-play game on TV
    - Calendar + Lighting: Adjust lighting for calendar events
    
    Attributes:
        max_synergies: Maximum number of synergies to generate
        area_lookup_fn: Optional function to look up area from entity IDs
    """
    
    def __init__(
        self,
        max_synergies: int = MAX_CONTEXT_SYNERGIES,
        area_lookup_fn: Optional[Callable[[list[str], list[dict[str, Any]]], Optional[str]]] = None
    ):
        """
        Initialize context-aware detector.
        
        Args:
            max_synergies: Maximum number of synergies to generate
            area_lookup_fn: Optional function to look up area from entity IDs
        """
        self.max_synergies = max_synergies
        self.area_lookup_fn = area_lookup_fn
    
    def _get_area(
        self,
        entity_ids: list[str],
        entities: list[dict[str, Any]]
    ) -> Optional[str]:
        """
        Look up area for entity IDs.
        
        Args:
            entity_ids: List of entity IDs to look up
            entities: List of all entities
            
        Returns:
            Area ID if found, None otherwise
        """
        if self.area_lookup_fn:
            return self.area_lookup_fn(entity_ids, entities)
        
        # Default implementation
        for entity_id in entity_ids:
            for entity in entities:
                if entity.get('entity_id') == entity_id:
                    area = entity.get('area_id')
                    if area:
                        return area
        return None
    
    def _find_devices_by_prefix(
        self,
        entities: list[dict[str, Any]],
        prefix: str
    ) -> list[str]:
        """
        Find device entity IDs by prefix.
        
        Args:
            entities: List of entity dictionaries
            prefix: Entity ID prefix (e.g., 'climate.')
            
        Returns:
            List of matching entity IDs
        """
        return [
            e.get('entity_id')
            for e in entities
            if e.get('entity_id', '').startswith(prefix)
        ]
    
    def _find_weather_entities(
        self,
        entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Find weather entities.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            List of weather entity dictionaries
        """
        return [
            e for e in entities
            if e.get('entity_id', '').startswith('weather.')
        ]
    
    def _find_energy_sensors(
        self,
        entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Find energy-related sensors.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            List of energy sensor entity dictionaries
        """
        return [
            e for e in entities
            if 'energy' in e.get('entity_id', '').lower() or
               'power' in e.get('entity_id', '').lower()
        ]
    
    def _find_sports_entities(
        self,
        entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Find sports-related entities (team tracker sensors).
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            List of sports entity dictionaries
        """
        return [
            e for e in entities
            if 'team_tracker' in e.get('entity_id', '').lower() or
               any(league in e.get('entity_id', '').lower() 
                   for league in ['nfl_', 'nhl_', 'mlb_', 'nba_', 'ncaa_'])
        ]
    
    def _find_calendar_entities(
        self,
        entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Find calendar entities.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            List of calendar entity dictionaries
        """
        return [
            e for e in entities
            if e.get('entity_id', '').startswith('calendar.')
        ]
    
    def _find_carbon_intensity_sensors(
        self,
        entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Find carbon intensity sensors.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            List of carbon intensity sensor dictionaries
        """
        return [
            e for e in entities
            if 'carbon_intensity' in e.get('entity_id', '').lower() or
               'carbon' in e.get('entity_id', '').lower()
        ]
    
    def _find_media_player_devices(
        self,
        entities: list[dict[str, Any]]
    ) -> list[str]:
        """
        Find media player devices.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            List of media player entity IDs
        """
        return self._find_devices_by_prefix(entities, 'media_player.')
    
    def _find_notify_services(
        self,
        entities: list[dict[str, Any]]
    ) -> list[str]:
        """
        Find notification services.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            List of notify service entity IDs (typically notify.*)
        """
        return self._find_devices_by_prefix(entities, 'notify.')
    
    def _find_high_power_devices(
        self,
        entities: list[dict[str, Any]]
    ) -> list[str]:
        """
        Find high-power device entity IDs.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            List of high-power device entity IDs
        """
        return [
            e.get('entity_id')
            for e in entities
            if e.get('entity_id', '').split('.')[0] in HIGH_POWER_DOMAINS
        ]
    
    def _create_weather_climate_synergy(
        self,
        weather_entity_id: str,
        climate_entity_id: str,
        area: Optional[str]
    ) -> dict[str, Any]:
        """
        Create a weather + climate synergy.
        
        Args:
            weather_entity_id: Weather entity ID
            climate_entity_id: Climate device entity ID
            area: Area ID (optional)
            
        Returns:
            Context-aware synergy dictionary
        """
        return {
            'synergy_id': str(uuid.uuid4()),
            'synergy_type': 'weather_context',  # Specific type for weather-based synergies
            'devices': [weather_entity_id, climate_entity_id],
            'trigger_entity': weather_entity_id,
            'action_entity': climate_entity_id,
            'area': area,
            'impact_score': 0.75,
            'confidence': 0.70,
            'complexity': 'medium',
            'rationale': 'Weather context: Pre-cool/heat based on weather forecast to optimize energy',
            'synergy_depth': 2,
            'chain_devices': [weather_entity_id, climate_entity_id],
            'context_metadata': {
                'context_type': 'weather_climate',
                'triggers': {
                    'weather': {'condition': 'sunny', 'temp_above': 80},
                    'energy': {'peak_hours': True}
                },
                'benefits': ['energy_savings', 'comfort', 'cost_reduction'],
                'estimated_savings': '10-15% cooling costs'
            }
        }
    
    def _create_weather_cover_synergy(
        self,
        weather_entity_id: str,
        cover_entity_id: str,
        area: Optional[str]
    ) -> dict[str, Any]:
        """
        Create a weather + cover synergy.
        
        Args:
            weather_entity_id: Weather entity ID
            cover_entity_id: Cover device entity ID
            area: Area ID (optional)
            
        Returns:
            Context-aware synergy dictionary
        """
        return {
            'synergy_id': str(uuid.uuid4()),
            'synergy_type': 'weather_context',  # Specific type for weather-based synergies
            'devices': [weather_entity_id, cover_entity_id],
            'trigger_entity': weather_entity_id,
            'action_entity': cover_entity_id,
            'area': area,
            'impact_score': 0.70,
            'confidence': 0.75,
            'complexity': 'low',
            'rationale': 'Weather context: Close blinds when sunny to reduce cooling load',
            'synergy_depth': 2,
            'chain_devices': [weather_entity_id, cover_entity_id],
            'context_metadata': {
                'context_type': 'weather_cover',
                'triggers': {
                    'weather': {'condition': 'sunny', 'temp_above': 75}
                },
                'benefits': ['energy_savings', 'comfort'],
                'estimated_savings': '5-10% cooling costs'
            }
        }
    
    def _create_energy_scheduling_synergy(
        self,
        energy_entity_id: str,
        device_entity_id: str,
        area: Optional[str]
    ) -> dict[str, Any]:
        """
        Create an energy scheduling synergy.
        
        Args:
            energy_entity_id: Energy sensor entity ID
            device_entity_id: High-power device entity ID
            area: Area ID (optional)
            
        Returns:
            Context-aware synergy dictionary
        """
        device_domain = device_entity_id.split('.')[0]
        
        return {
            'synergy_id': str(uuid.uuid4()),
            'synergy_type': 'energy_context',  # Specific type for energy-based synergies
            'devices': [energy_entity_id, device_entity_id],
            'trigger_entity': energy_entity_id,
            'action_entity': device_entity_id,
            'area': area,
            'impact_score': 0.80,
            'confidence': 0.70,
            'complexity': 'medium',
            'rationale': f'Energy context: Schedule {device_domain} during off-peak energy hours',
            'synergy_depth': 2,
            'chain_devices': [energy_entity_id, device_entity_id],
            'context_metadata': {
                'context_type': 'energy_scheduling',
                'triggers': {
                    'energy': {'peak_hours': False, 'price_below': 0.12}
                },
                'benefits': ['cost_reduction', 'grid_optimization'],
                'estimated_savings': '15-25% energy costs'
            }
        }
    
    def _create_weather_lighting_synergy(
        self,
        weather_entity_id: str,
        light_entity_id: str,
        area: Optional[str]
    ) -> dict[str, Any]:
        """
        Create a weather + lighting synergy.
        
        Args:
            weather_entity_id: Weather entity ID
            light_entity_id: Light device entity ID
            area: Area ID (optional)
            
        Returns:
            Context-aware synergy dictionary
        """
        return {
            'synergy_id': str(uuid.uuid4()),
            'synergy_type': 'weather_context',  # Specific type for weather-based synergies
            'devices': [weather_entity_id, light_entity_id],
            'trigger_entity': weather_entity_id,
            'action_entity': light_entity_id,
            'area': area,
            'impact_score': 0.65,
            'confidence': 0.70,
            'complexity': 'low',
            'rationale': 'Weather context: Adjust lighting based on weather conditions and daylight',
            'synergy_depth': 2,
            'chain_devices': [weather_entity_id, light_entity_id],
            'context_metadata': {
                'context_type': 'weather_lighting',
                'triggers': {
                    'weather': {'condition': 'cloudy'},
                    'time': {'is_daytime': True}
                },
                'benefits': ['comfort', 'energy_savings'],
                'estimated_savings': '5-10% lighting costs'
            }
        }
    
    def _create_sports_lighting_synergy(
        self,
        sports_entity_id: str,
        light_entity_id: str,
        area: Optional[str]
    ) -> dict[str, Any]:
        """
        Create a sports + lighting synergy.
        
        Args:
            sports_entity_id: Sports/team tracker entity ID
            light_entity_id: Light device entity ID
            area: Area ID (optional)
            
        Returns:
            Context-aware synergy dictionary
        """
        return {
            'synergy_id': str(uuid.uuid4()),
            'synergy_type': 'sports_context',
            'devices': [sports_entity_id, light_entity_id],
            'trigger_entity': sports_entity_id,
            'action_entity': light_entity_id,
            'area': area,
            'impact_score': 0.70,
            'confidence': 0.75,
            'complexity': 'low',
            'rationale': 'Sports context: Set lighting for game time viewing comfort',
            'synergy_depth': 2,
            'chain_devices': [sports_entity_id, light_entity_id],
            'context_metadata': {
                'context_type': 'sports_lighting',
                'triggers': {
                    'sports': {'game_start': True, 'game_live': True}
                },
                'benefits': ['convenience', 'entertainment', 'comfort'],
                'estimated_savings': 'Enhanced viewing experience'
            }
        }
    
    def _create_sports_media_synergy(
        self,
        sports_entity_id: str,
        media_entity_id: str,
        area: Optional[str]
    ) -> dict[str, Any]:
        """
        Create a sports + media player synergy.
        
        Args:
            sports_entity_id: Sports/team tracker entity ID
            media_entity_id: Media player entity ID
            area: Area ID (optional)
            
        Returns:
            Context-aware synergy dictionary
        """
        return {
            'synergy_id': str(uuid.uuid4()),
            'synergy_type': 'sports_context',
            'devices': [sports_entity_id, media_entity_id],
            'trigger_entity': sports_entity_id,
            'action_entity': media_entity_id,
            'area': area,
            'impact_score': 0.75,
            'confidence': 0.70,
            'complexity': 'medium',
            'rationale': 'Sports context: Auto-play game on TV when game starts',
            'synergy_depth': 2,
            'chain_devices': [sports_entity_id, media_entity_id],
            'context_metadata': {
                'context_type': 'sports_media',
                'triggers': {
                    'sports': {'game_start': True}
                },
                'benefits': ['convenience', 'entertainment'],
                'estimated_savings': 'Automated game viewing'
            }
        }
    
    def _create_calendar_lighting_synergy(
        self,
        calendar_entity_id: str,
        light_entity_id: str,
        area: Optional[str]
    ) -> dict[str, Any]:
        """
        Create a calendar + lighting synergy.
        
        Args:
            calendar_entity_id: Calendar entity ID
            light_entity_id: Light device entity ID
            area: Area ID (optional)
            
        Returns:
            Context-aware synergy dictionary
        """
        return {
            'synergy_id': str(uuid.uuid4()),
            'synergy_type': 'calendar_context',
            'devices': [calendar_entity_id, light_entity_id],
            'trigger_entity': calendar_entity_id,
            'action_entity': light_entity_id,
            'area': area,
            'impact_score': 0.65,
            'confidence': 0.70,
            'complexity': 'low',
            'rationale': 'Calendar context: Adjust lighting for calendar events',
            'synergy_depth': 2,
            'chain_devices': [calendar_entity_id, light_entity_id],
            'context_metadata': {
                'context_type': 'calendar_lighting',
                'triggers': {
                    'calendar': {'event_start': True}
                },
                'benefits': ['convenience', 'preparation'],
                'estimated_savings': 'Enhanced event preparation'
            }
        }
    
    def _create_carbon_intensity_scheduling_synergy(
        self,
        carbon_entity_id: str,
        device_entity_id: str,
        area: Optional[str]
    ) -> dict[str, Any]:
        """
        Create a carbon intensity + device scheduling synergy.
        
        Args:
            carbon_entity_id: Carbon intensity sensor entity ID
            device_entity_id: High-power device entity ID
            area: Area ID (optional)
            
        Returns:
            Context-aware synergy dictionary
        """
        device_domain = device_entity_id.split('.')[0]
        
        return {
            'synergy_id': str(uuid.uuid4()),
            'synergy_type': 'carbon_context',
            'devices': [carbon_entity_id, device_entity_id],
            'trigger_entity': carbon_entity_id,
            'action_entity': device_entity_id,
            'area': area,
            'impact_score': 0.80,
            'confidence': 0.75,
            'complexity': 'medium',
            'rationale': f'Carbon context: Schedule {device_domain} during low-carbon hours',
            'synergy_depth': 2,
            'chain_devices': [carbon_entity_id, device_entity_id],
            'context_metadata': {
                'context_type': 'carbon_scheduling',
                'triggers': {
                    'carbon': {'intensity_below': 200, 'unit': 'gCO2/kWh'}
                },
                'benefits': ['sustainability', 'carbon_reduction', 'environmental'],
                'estimated_savings': 'Reduced carbon footprint'
            }
        }
    
    async def detect_context_aware_synergies(
        self,
        entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Detect context-aware synergies based on weather, energy, carbon, sports, and calendar data.
        
        These synergies combine multiple context factors to suggest automations
        that optimize for comfort, cost, sustainability, and convenience.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            List of context-aware synergy opportunities
        """
        logger.info("   → Detecting context-aware synergies...")
        synergies: list[dict[str, Any]] = []
        
        # Find relevant devices
        climate_devices = self._find_devices_by_prefix(entities, 'climate.')
        cover_devices = self._find_devices_by_prefix(entities, 'cover.')
        light_devices = self._find_devices_by_prefix(entities, 'light.')
        media_devices = self._find_media_player_devices(entities)
        notify_services = self._find_notify_services(entities)
        weather_entities = self._find_weather_entities(entities)
        energy_sensors = self._find_energy_sensors(entities)
        carbon_sensors = self._find_carbon_intensity_sensors(entities)
        sports_entities = self._find_sports_entities(entities)
        calendar_entities = self._find_calendar_entities(entities)
        high_power_devices = self._find_high_power_devices(entities)
        
        logger.info(
            f"      Found {len(climate_devices)} climate, {len(cover_devices)} cover, "
            f"{len(weather_entities)} weather, {len(energy_sensors)} energy, "
            f"{len(carbon_sensors)} carbon, {len(sports_entities)} sports, "
            f"{len(calendar_entities)} calendar entities"
        )
        
        # Weather + Climate synergies
        if weather_entities and climate_devices:
            weather_id = weather_entities[0].get('entity_id')
            for climate in climate_devices[:MAX_DEVICES_PER_CONTEXT_TYPE]:
                if len(synergies) >= self.max_synergies:
                    break
                area = self._get_area([climate], entities)
                synergy = self._create_weather_climate_synergy(weather_id, climate, area)
                synergies.append(synergy)
        
        # Weather + Cover synergies
        if weather_entities and cover_devices:
            weather_id = weather_entities[0].get('entity_id')
            for cover in cover_devices[:MAX_DEVICES_PER_CONTEXT_TYPE]:
                if len(synergies) >= self.max_synergies:
                    break
                area = self._get_area([cover], entities)
                synergy = self._create_weather_cover_synergy(weather_id, cover, area)
                synergies.append(synergy)
        
        # Energy + High-power device synergies
        if energy_sensors and high_power_devices:
            energy_id = energy_sensors[0].get('entity_id', 'sensor.energy_price')
            for device in high_power_devices[:MAX_DEVICES_PER_CONTEXT_TYPE]:
                if len(synergies) >= self.max_synergies:
                    break
                area = self._get_area([device], entities)
                synergy = self._create_energy_scheduling_synergy(energy_id, device, area)
                synergies.append(synergy)
        
        # Weather + Light synergies
        if weather_entities and light_devices and len(synergies) < self.max_synergies:
            weather_id = weather_entities[0].get('entity_id')
            for light in light_devices[:MAX_DEVICES_PER_CONTEXT_TYPE]:
                if len(synergies) >= self.max_synergies:
                    break
                area = self._get_area([light], entities)
                synergy = self._create_weather_lighting_synergy(weather_id, light, area)
                synergies.append(synergy)
        
        # Sports + Lighting synergies
        if sports_entities and light_devices and len(synergies) < self.max_synergies:
            sports_id = sports_entities[0].get('entity_id')
            for light in light_devices[:MAX_DEVICES_PER_CONTEXT_TYPE]:
                if len(synergies) >= self.max_synergies:
                    break
                area = self._get_area([light], entities)
                synergy = self._create_sports_lighting_synergy(sports_id, light, area)
                synergies.append(synergy)
        
        # Sports + Media player synergies
        if sports_entities and media_devices and len(synergies) < self.max_synergies:
            sports_id = sports_entities[0].get('entity_id')
            for media in media_devices[:MAX_DEVICES_PER_CONTEXT_TYPE]:
                if len(synergies) >= self.max_synergies:
                    break
                area = self._get_area([media], entities)
                synergy = self._create_sports_media_synergy(sports_id, media, area)
                synergies.append(synergy)
        
        # Calendar + Lighting synergies
        if calendar_entities and light_devices and len(synergies) < self.max_synergies:
            calendar_id = calendar_entities[0].get('entity_id')
            for light in light_devices[:MAX_DEVICES_PER_CONTEXT_TYPE]:
                if len(synergies) >= self.max_synergies:
                    break
                area = self._get_area([light], entities)
                synergy = self._create_calendar_lighting_synergy(calendar_id, light, area)
                synergies.append(synergy)
        
        # Carbon Intensity + High-power device synergies
        if carbon_sensors and high_power_devices and len(synergies) < self.max_synergies:
            carbon_id = carbon_sensors[0].get('entity_id')
            for device in high_power_devices[:MAX_DEVICES_PER_CONTEXT_TYPE]:
                if len(synergies) >= self.max_synergies:
                    break
                area = self._get_area([device], entities)
                synergy = self._create_carbon_intensity_scheduling_synergy(carbon_id, device, area)
                synergies.append(synergy)
        
        logger.info(f"      ✅ Generated {len(synergies)} context-aware synergies")
        return synergies
