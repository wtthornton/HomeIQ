"""
Synthetic Home HA Loader

Load our generated synthetic home JSON files into Home Assistant test container.
Converts JSON format to HA-compatible format (areas, entities, states).
"""

import json
import logging
from pathlib import Path
from typing import Any, TypedDict

import httpx

from .synthetic_area_generator import SyntheticAreaGenerator
from .synthetic_device_generator import SyntheticDeviceGenerator

logger = logging.getLogger(__name__)

# Constants
DEFAULT_HTTP_TIMEOUT = 10.0  # seconds


class LoadResult(TypedDict, total=False):
    """Result structure for home loading operations."""
    areas_created: int
    entities_created: int
    area_map: dict[str, str]
    errors: list[str]


class SyntheticHomeHALoader:
    """Load synthetic home JSON into Home Assistant"""
    
    def __init__(self):
        """Initialize HA loader"""
        self.area_generator = SyntheticAreaGenerator()
        self.device_generator = SyntheticDeviceGenerator()
    
    async def load_json_home_to_ha(
        self,
        home_json_path: Path,
        ha_url: str,
        ha_token: str
    ) -> LoadResult:
        """
        Load a synthetic home JSON file into Home Assistant.
        
        Args:
            home_json_path: Path to JSON file
            ha_url: Home Assistant URL
            ha_token: Home Assistant authentication token
        
        Returns:
            Dictionary with loading results:
                - areas_created: Number of areas created
                - entities_created: Number of entities created
                - area_map: Mapping of area names to HA area IDs
                - errors: List of errors encountered
        """
        # Validate inputs
        if not home_json_path.exists():
            raise FileNotFoundError(f"Home JSON file not found: {home_json_path}")
        
        if not ha_url:
            raise ValueError("ha_url cannot be empty")
        
        if not ha_token:
            raise ValueError("ha_token cannot be empty")
        
        # Load JSON home
        try:
            with open(home_json_path, 'r', encoding='utf-8') as f:
                home_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in home file {home_json_path}: {e}") from e
        except OSError as e:
            raise IOError(f"Failed to read home file {home_json_path}: {e}") from e
        
        logger.info(f"Loading home: {home_data.get('metadata', {}).get('home', {}).get('name', 'Unknown')}")
        
        # Generate areas and devices if not present
        if 'areas' not in home_data:
            areas = self.area_generator.generate_areas(home_data)
            home_data['areas'] = areas
        
        if 'devices' not in home_data:
            devices = self.device_generator.generate_devices(home_data, home_data['areas'])
            home_data['devices'] = devices
        
        # Convert and load to HA
        results = {
            'areas_created': 0,
            'entities_created': 0,
            'area_map': {},
            'errors': []
        }
        
        async with httpx.AsyncClient() as client:
            # Create areas
            areas = home_data.get('areas', [])
            area_map = {}
            
            for area in areas:
                area_name = area.get('name') if isinstance(area, dict) else str(area)
                if not area_name:
                    continue
                
                area_id = await self.create_ha_area(client, area_name, ha_url, ha_token)
                if area_id:
                    area_map[area_name] = area_id
                    results['areas_created'] += 1
                else:
                    results['errors'].append(f"Failed to create area: {area_name}")
            
            results['area_map'] = area_map
            
            # Create entities
            devices = home_data.get('devices', [])
            
            for device in devices:
                entity_id = device.get('entity_id')
                if not entity_id:
                    # Generate entity_id from device name and type
                    device_name = device.get('name', 'unknown')
                    device_type = device.get('device_type', 'sensor')
                    # Sanitize entity_id: lowercase, replace spaces/hyphens with underscores
                    sanitized_name = device_name.lower().replace(' ', '_').replace('-', '_')
                    # Remove any invalid characters for entity_id
                    sanitized_name = ''.join(c for c in sanitized_name if c.isalnum() or c == '_')
                    entity_id = f"{device_type}.{sanitized_name}"
                
                state = device.get('state', 'unknown')
                attributes = device.get('attributes', {})
                
                # Add area if available
                area_name = device.get('area')
                if area_name and area_name in area_map:
                    attributes['area_id'] = area_map[area_name]
                
                success = await self.create_ha_entity(
                    client, entity_id, state, attributes, ha_url, ha_token
                )
                if success:
                    results['entities_created'] += 1
                else:
                    results['errors'].append(f"Failed to create entity: {entity_id}")
        
        logger.info(
            f"✅ Loaded home: {results['areas_created']} areas, "
            f"{results['entities_created']} entities"
        )
        
        return results
    
    async def create_ha_area(
        self,
        client: httpx.AsyncClient,
        area_name: str,
        ha_url: str,
        ha_token: str
    ) -> str | None:
        """
        Create an area in Home Assistant.
        
        Args:
            client: HTTP client
            area_name: Name of area
            ha_url: Home Assistant URL
            ha_token: Authentication token
        
        Returns:
            Area ID or None if failed
        """
        try:
            response = await client.post(
                f"{ha_url}/api/config/area_registry/create",
                headers={
                    "Authorization": f"Bearer {ha_token}",
                    "Content-Type": "application/json",
                },
                json={"name": area_name},
                timeout=DEFAULT_HTTP_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("area_id")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating area {area_name}: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error creating area {area_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating area {area_name}: {e}")
            return None
    
    async def create_ha_entity(
        self,
        client: httpx.AsyncClient,
        entity_id: str,
        state: str,
        attributes: dict[str, Any],
        ha_url: str,
        ha_token: str
    ) -> bool:
        """
        Create or update an entity in Home Assistant.
        
        Args:
            client: HTTP client
            entity_id: Entity ID (e.g., 'light.living_room_light')
            state: Initial state value
            attributes: Entity attributes
            ha_url: Home Assistant URL
            ha_token: Authentication token
        
        Returns:
            True if successful, False otherwise
        """
        try:
            response = await client.post(
                f"{ha_url}/api/states/{entity_id}",
                headers={
                    "Authorization": f"Bearer {ha_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "state": state,
                    "attributes": attributes,
                },
                timeout=DEFAULT_HTTP_TIMEOUT,
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error creating entity {entity_id}: {e.response.status_code} - {e.response.text}")
            return False
        except httpx.RequestError as e:
            logger.warning(f"Request error creating entity {entity_id}: {e}")
            return False
        except Exception as e:
            logger.warning(f"Unexpected error creating entity {entity_id}: {e}")
            return False
    
    def convert_areas_to_ha(self, areas: list[dict[str, Any] | str]) -> list[dict[str, Any]]:
        """
        Convert areas to HA format.
        
        Args:
            areas: List of area dictionaries or strings
        
        Returns:
            List of HA-formatted area dictionaries
        """
        ha_areas = []
        for area in areas:
            if isinstance(area, str):
                ha_areas.append({"name": area})
            elif isinstance(area, dict):
                ha_areas.append({
                    "name": area.get("name", "Unknown"),
                    "id": area.get("id"),
                    "aliases": area.get("aliases", [])
                })
        return ha_areas
    
    def convert_devices_to_entities(self, devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Convert devices to HA entity format.
        
        Args:
            devices: List of device dictionaries
        
        Returns:
            List of HA-formatted entity dictionaries
        """
        entities = []
        for device in devices:
            entity_id = device.get("entity_id")
            if not entity_id:
                # Generate entity_id
                device_name = device.get("name", "unknown")
                device_type = device.get("device_type", "sensor")
                # Sanitize entity_id
                sanitized_name = device_name.lower().replace(' ', '_').replace('-', '_')
                sanitized_name = ''.join(c for c in sanitized_name if c.isalnum() or c == '_')
                entity_id = f"{device_type}.{sanitized_name}"
            
            entity = {
                "entity_id": entity_id,
                "state": device.get("state", "unknown"),
                "attributes": device.get("attributes", {})
            }
            
            # Add area if available
            if "area" in device:
                entity["attributes"]["area_name"] = device["area"]
            
            entities.append(entity)
        
        return entities

