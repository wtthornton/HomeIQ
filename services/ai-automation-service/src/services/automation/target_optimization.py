"""
Target Optimization Utilities for Automation Actions

Optimizes action targets to use area_id or device_id when appropriate,
reducing maintenance and improving readability.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def _fetch_entity_metadata_batch(
    ha_client: Any,
    entity_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """
    Fetch entity metadata for multiple entities efficiently.
    
    Attempts batch query if HA client supports it, otherwise falls back to
    individual queries with concurrent execution.
    
    Args:
        ha_client: Home Assistant client
        entity_ids: List of entity IDs to fetch
        
    Returns:
        Dictionary mapping entity_id to metadata
    """
    entity_metadata = {}
    
    # Check if client supports batch queries
    if hasattr(ha_client, 'get_entities_states'):
        try:
            # Batch query (single API call)
            batch_results = await ha_client.get_entities_states(entity_ids)
            if batch_results:
                entity_metadata = batch_results
                logger.debug(f"Batch fetched metadata for {len(entity_metadata)} entities")
                return entity_metadata
        except Exception as e:
            logger.debug(f"Batch query failed, falling back to individual queries: {e}")
    
    # Fallback: Individual queries with asyncio.gather for concurrency
    import asyncio
    
    async def fetch_single(entity_id: str) -> tuple[str, dict[str, Any] | None]:
        """Fetch single entity metadata."""
        try:
            metadata = await ha_client.get_entity_state(entity_id)
            return entity_id, metadata
        except Exception as e:
            logger.debug(f"Could not fetch metadata for {entity_id}: {e}")
            return entity_id, None
    
    # Fetch all entities concurrently
    results = await asyncio.gather(
        *[fetch_single(entity_id) for entity_id in entity_ids],
        return_exceptions=True
    )
    
    # Process results
    for result in results:
        if isinstance(result, Exception):
            logger.debug(f"Error fetching entity: {result}")
            continue
        
        entity_id, metadata = result
        if metadata:
            entity_metadata[entity_id] = metadata
    
    logger.debug(f"Concurrently fetched metadata for {len(entity_metadata)}/{len(entity_ids)} entities")
    return entity_metadata


async def optimize_action_targets(
    yaml_data: dict[str, Any],
    ha_client: Any | None = None
) -> dict[str, Any]:
    """
    Optimize action targets to use area_id or device_id when appropriate.
    
    Converts entity_id lists to:
    - area_id: when all entities belong to the same area
    - device_id: when all entities belong to the same device
    
    Args:
        yaml_data: Parsed automation YAML data
        ha_client: Home Assistant client for entity/device/area resolution
        
    Returns:
        YAML data with optimized targets
    """
    if not ha_client:
        logger.debug("No HA client available, skipping target optimization")
        return yaml_data
    
    try:
        actions = yaml_data.get("action", [])
        if not isinstance(actions, list):
            return yaml_data
        
        optimized_actions = []
        for action in actions:
            if not isinstance(action, dict):
                optimized_actions.append(action)
                continue
            
            # Check if action has target with entity_id list
            target = action.get("target")
            if not target or not isinstance(target, dict):
                optimized_actions.append(action)
                continue
            
            entity_id = target.get("entity_id")
            if not entity_id or not isinstance(entity_id, list) or len(entity_id) < 2:
                # Not a list or only one entity - no optimization needed
                optimized_actions.append(action)
                continue
            
            # Try to optimize to area_id or device_id
            optimized_action = await _optimize_single_action_target(
                action, entity_id, ha_client
            )
            optimized_actions.append(optimized_action)
        
        yaml_data["action"] = optimized_actions
        return yaml_data
    
    except Exception as e:
        logger.debug(f"Could not optimize targets: {e}")
        return yaml_data


async def _optimize_single_action_target(
    action: dict[str, Any],
    entity_ids: list[str],
    ha_client: Any
) -> dict[str, Any]:
    """
    Optimize a single action's target.
    
    Args:
        action: Action dictionary
        entity_ids: List of entity IDs in the target
        ha_client: Home Assistant client
        
    Returns:
        Optimized action dictionary
    """
    try:
        # Fetch entity metadata for all entities (batch if possible)
        entity_metadata = await _fetch_entity_metadata_batch(ha_client, entity_ids)
        
        if not entity_metadata or len(entity_metadata) != len(entity_ids):
            # Could not fetch all metadata - skip optimization
            return action
        
        # Check if all entities belong to the same area
        areas = set()
        devices = set()
        area_count = 0
        device_count = 0
        
        for entity_id, metadata in entity_metadata.items():
            # Get area_id from attributes or entity registry
            area_id = None
            if isinstance(metadata, dict):
                attributes = metadata.get("attributes", {})
                if isinstance(attributes, dict):
                    area_id = attributes.get("area_id")
                    device_id = attributes.get("device_id")
                    
                    if area_id:
                        areas.add(area_id)
                        area_count += 1
                    
                    if device_id:
                        devices.add(device_id)
                        device_count += 1
        
        # Optimize to device_id if all entities on same device
        # Check: exactly 1 unique device AND all entities have device_id
        if len(devices) == 1 and device_count == len(entity_ids):
            device_id = list(devices)[0]
            logger.debug(f"Optimized target to device_id: {device_id} (from {len(entity_ids)} entities)")
            
            # Create optimized action
            optimized_action = action.copy()
            optimized_action["target"] = {"device_id": device_id}
            return optimized_action
        
        # Optimize to area_id if all entities in same area
        # Check: exactly 1 unique area AND all entities have area_id
        if len(areas) == 1 and area_count == len(entity_ids):
            area_id = list(areas)[0]
            logger.debug(f"Optimized target to area_id: {area_id} (from {len(entity_ids)} entities)")
            
            # Create optimized action
            optimized_action = action.copy()
            optimized_action["target"] = {"area_id": area_id}
            return optimized_action
        
        # No optimization possible - return original
        return action
    
    except Exception as e:
        logger.debug(f"Could not optimize action target: {e}")
        return action

