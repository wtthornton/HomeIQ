"""
Home Assistant Test Loader

Load synthetic homes into test HA container and generate events through HA pipeline.
Validates full pipeline: HA → websocket-ingestion → InfluxDB
"""

import json
import logging
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypedDict

import httpx

from ..training.synthetic_home_ha_loader import LoadResult, SyntheticHomeHALoader

logger = logging.getLogger(__name__)

# Constants
DEFAULT_HTTP_TIMEOUT = 10.0  # seconds


class CleanupResult(TypedDict, total=False):
    """Result structure for cleanup operations."""
    entities_deleted: int
    areas_deleted: int
    errors: list[str]


class HATestLoader:
    """
    Load synthetic homes into test HA and generate events through HA pipeline.
    
    This enables full pipeline validation:
    HA → websocket-ingestion → InfluxDB
    """
    
    def __init__(self, ha_url: str, ha_token: str):
        """
        Initialize HA test loader.
        
        Args:
            ha_url: Home Assistant URL (e.g., http://localhost:8124)
            ha_token: Home Assistant authentication token
        """
        self.ha_url = ha_url
        self.ha_token = ha_token
        self.ha_loader = SyntheticHomeHALoader()
    
    async def load_home_to_ha(
        self,
        home_data: dict[str, Any]
    ) -> LoadResult:
        """
        Load synthetic home into test HA container.
        
        Args:
            home_data: Synthetic home dictionary (from JSON or generator)
        
        Returns:
            Dictionary with loading results:
                - areas_created: Number of areas created
                - entities_created: Number of entities created
                - area_map: Mapping of area names to HA area IDs
                - errors: List of errors encountered
        
        Raises:
            ValueError: If home_data is invalid
        """
        if not home_data:
            raise ValueError("home_data cannot be empty")
        
        # Save home to temp JSON file for loader
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json',
                delete=False,
                encoding='utf-8'
            ) as f:
                json.dump(home_data, f, indent=2, ensure_ascii=False)
                temp_path = Path(f.name)
            
            results = await self.ha_loader.load_json_home_to_ha(
                home_json_path=temp_path,
                ha_url=self.ha_url,
                ha_token=self.ha_token
            )
            return results
        finally:
            # Clean up temp file
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)
    
    async def create_ha_areas(
        self,
        areas: list[dict[str, Any] | str],
        ha_url: str | None = None,
        ha_token: str | None = None
    ) -> dict[str, str]:
        """
        Create areas in Home Assistant.
        
        Args:
            areas: List of area dictionaries or strings
            ha_url: Optional override for HA URL
            ha_token: Optional override for HA token
        
        Returns:
            Dictionary mapping area names to HA area IDs
        """
        ha_url = ha_url or self.ha_url
        ha_token = ha_token or self.ha_token
        
        area_map = {}
        
        async with httpx.AsyncClient() as client:
            for area in areas:
                area_name = area.get('name') if isinstance(area, dict) else str(area)
                if not area_name:
                    continue
                
                area_id = await self.ha_loader.create_ha_area(
                    client, area_name, ha_url, ha_token
                )
                if area_id:
                    area_map[area_name] = area_id
        
        return area_map
    
    async def create_ha_entities(
        self,
        devices: list[dict[str, Any]],
        ha_url: str | None = None,
        ha_token: str | None = None
    ) -> int:
        """
        Create entities in Home Assistant.
        
        Args:
            devices: List of device dictionaries
            ha_url: Optional override for HA URL
            ha_token: Optional override for HA token
        
        Returns:
            Number of entities created
        """
        ha_url = ha_url or self.ha_url
        ha_token = ha_token or self.ha_token
        
        created = 0
        
        async with httpx.AsyncClient() as client:
            for device in devices:
                entity_id = device.get('entity_id')
                if not entity_id:
                    continue
                
                state = device.get('state', 'unknown')
                attributes = device.get('attributes', {})
                
                success = await self.ha_loader.create_ha_entity(
                    client, entity_id, state, attributes, ha_url, ha_token
                )
                if success:
                    created += 1
        
        return created
    
    async def generate_ha_events(
        self,
        devices: list[dict[str, Any]],
        days: int = 7,
        ha_url: str | None = None,
        ha_token: str | None = None
    ) -> int:
        """
        Generate events through Home Assistant.
        
        This simulates real device activity by updating entity states in HA,
        which then flows through websocket-ingestion to InfluxDB.
        
        Args:
            devices: List of device dictionaries
            days: Number of days of events to generate
            ha_url: Optional override for HA URL
            ha_token: Optional override for HA token
        
        Returns:
            Number of events generated
        """
        ha_url = ha_url or self.ha_url
        ha_token = ha_token or self.ha_token
        
        # For now, this is a placeholder that would need to:
        # 1. Generate realistic state changes over time
        # 2. Update HA entity states via API
        # 3. Let websocket-ingestion capture and forward to InfluxDB
        
        # TODO: Implement realistic event generation through HA
        # This would require:
        # - Time-based state changes (e.g., lights on/off at certain times)
        # - Device interaction patterns (e.g., motion sensor triggers light)
        # - State updates via HA API: POST /api/states/{entity_id}
        
        logger.warning(
            "generate_ha_events() is a placeholder. "
            "Full implementation would generate events through HA API."
        )
        
        return 0
    
    async def cleanup_ha_home(
        self,
        home_id: str,
        entity_ids: list[str] | None = None,
        area_ids: list[str] | None = None,
        ha_url: str | None = None,
        ha_token: str | None = None
    ) -> CleanupResult:
        """
        Clean up a home from Home Assistant after testing.
        
        Args:
            home_id: Home identifier
            entity_ids: Optional list of entity IDs to delete
            area_ids: Optional list of area IDs to delete
            ha_url: Optional override for HA URL
            ha_token: Optional override for HA token
        
        Returns:
            Dictionary with cleanup results
        """
        ha_url = ha_url or self.ha_url
        ha_token = ha_token or self.ha_token
        
        results = {
            'entities_deleted': 0,
            'areas_deleted': 0,
            'errors': []
        }
        
        async with httpx.AsyncClient() as client:
            # Delete entities (HA doesn't have direct delete, but we can set them to unavailable)
            if entity_ids:
                for entity_id in entity_ids:
                    try:
                        # Set entity to unavailable state
                        response = await client.post(
                            f"{ha_url}/api/states/{entity_id}",
                            headers={
                                "Authorization": f"Bearer {ha_token}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "state": "unavailable",
                                "attributes": {}
                            },
                            timeout=DEFAULT_HTTP_TIMEOUT,
                        )
                        response.raise_for_status()
                        results['entities_deleted'] += 1
                    except httpx.HTTPStatusError as e:
                        results['errors'].append(
                            f"HTTP error deleting entity {entity_id}: {e.response.status_code}"
                        )
                    except httpx.RequestError as e:
                        results['errors'].append(f"Request error deleting entity {entity_id}: {e}")
                    except Exception as e:
                        results['errors'].append(f"Unexpected error deleting entity {entity_id}: {e}")
            
            # Delete areas (HA API: DELETE /api/config/area_registry/{area_id})
            if area_ids:
                for area_id in area_ids:
                    try:
                        response = await client.delete(
                            f"{ha_url}/api/config/area_registry/{area_id}",
                            headers={
                                "Authorization": f"Bearer {ha_token}",
                            },
                            timeout=DEFAULT_HTTP_TIMEOUT,
                        )
                        response.raise_for_status()
                        results['areas_deleted'] += 1
                    except httpx.HTTPStatusError as e:
                        results['errors'].append(
                            f"HTTP error deleting area {area_id}: {e.response.status_code}"
                        )
                    except httpx.RequestError as e:
                        results['errors'].append(f"Request error deleting area {area_id}: {e}")
                    except Exception as e:
                        results['errors'].append(f"Unexpected error deleting area {area_id}: {e}")
        
        logger.info(
            f"Cleaned up home {home_id}: "
            f"{results['entities_deleted']} entities, "
            f"{results['areas_deleted']} areas"
        )
        
        return results

