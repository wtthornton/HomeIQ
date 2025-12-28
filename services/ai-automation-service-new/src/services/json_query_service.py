"""
JSON Query Service

Query and filter automations by JSON properties.
"""

import logging
from typing import Any

from shared.homeiq_automation.schema import HomeIQAutomation

logger = logging.getLogger(__name__)


class JSONQueryService:
    """
    Service for querying automations by JSON properties.
    
    Features:
    - Query by device_id, area_id, pattern_type
    - Query by use_case, complexity
    - Query by energy impact, safety requirements
    """
    
    def query(
        self,
        automations: list[HomeIQAutomation | dict[str, Any]],
        filters: dict[str, Any]
    ) -> list[HomeIQAutomation]:
        """
        Query automations by JSON properties.
        
        Args:
            automations: List of automations to query
            filters: Dictionary of filter criteria
        
        Returns:
            List of matching automations
        """
        # Convert dicts to HomeIQAutomation
        automation_objects: list[HomeIQAutomation] = []
        for auto in automations:
            if isinstance(auto, dict):
                try:
                    automation_objects.append(HomeIQAutomation(**auto))
                except Exception as e:
                    logger.warning(f"Failed to parse automation: {e}")
                    continue
            else:
                automation_objects.append(auto)
        
        results: list[HomeIQAutomation] = []
        
        for auto in automation_objects:
            if self._matches_filters(auto, filters):
                results.append(auto)
        
        logger.debug(f"Query returned {len(results)} automations from {len(automation_objects)} total")
        return results
    
    def _matches_filters(self, automation: HomeIQAutomation, filters: dict[str, Any]) -> bool:
        """Check if automation matches all filters."""
        # Filter by device_id
        if "device_id" in filters:
            device_ids = automation.device_context.device_ids
            filter_device_ids = filters["device_id"]
            if isinstance(filter_device_ids, str):
                filter_device_ids = [filter_device_ids]
            if not any(did in device_ids for did in filter_device_ids):
                return False
        
        # Filter by entity_id
        if "entity_id" in filters:
            entity_ids = automation.device_context.entity_ids
            filter_entity_ids = filters["entity_id"]
            if isinstance(filter_entity_ids, str):
                filter_entity_ids = [filter_entity_ids]
            if not any(eid in entity_ids for eid in filter_entity_ids):
                return False
        
        # Filter by area_id
        if "area_id" in filters:
            area_ids = automation.area_context or []
            filter_area_ids = filters["area_id"]
            if isinstance(filter_area_ids, str):
                filter_area_ids = [filter_area_ids]
            if not any(aid in area_ids for aid in filter_area_ids):
                return False
        
        # Filter by pattern_type
        if "pattern_type" in filters:
            if not automation.pattern_context:
                return False
            if automation.pattern_context.pattern_type != filters["pattern_type"]:
                return False
        
        # Filter by use_case
        if "use_case" in filters:
            if automation.homeiq_metadata.use_case != filters["use_case"]:
                return False
        
        # Filter by complexity
        if "complexity" in filters:
            if automation.homeiq_metadata.complexity != filters["complexity"]:
                return False
        
        # Filter by energy impact
        if "min_energy_impact_w" in filters:
            if not automation.energy_impact or not automation.energy_impact.estimated_power_w:
                return False
            if automation.energy_impact.estimated_power_w < filters["min_energy_impact_w"]:
                return False
        
        # Filter by safety requirements
        if "requires_confirmation" in filters:
            if not automation.safety_checks:
                return False
            if automation.safety_checks.requires_confirmation != filters["requires_confirmation"]:
                return False
        
        # Filter by tags
        if "tags" in filters:
            automation_tags = automation.tags or []
            filter_tags = filters["tags"]
            if isinstance(filter_tags, str):
                filter_tags = [filter_tags]
            if not any(tag in automation_tags for tag in filter_tags):
                return False
        
        return True
    
    def query_by_device(self, automations: list[HomeIQAutomation], device_id: str) -> list[HomeIQAutomation]:
        """Query automations by device ID."""
        return self.query(automations, {"device_id": device_id})
    
    def query_by_area(self, automations: list[HomeIQAutomation], area_id: str) -> list[HomeIQAutomation]:
        """Query automations by area ID."""
        return self.query(automations, {"area_id": area_id})
    
    def query_by_pattern_type(self, automations: list[HomeIQAutomation], pattern_type: str) -> list[HomeIQAutomation]:
        """Query automations by pattern type."""
        return self.query(automations, {"pattern_type": pattern_type})
    
    def query_by_use_case(self, automations: list[HomeIQAutomation], use_case: str) -> list[HomeIQAutomation]:
        """Query automations by use case."""
        return self.query(automations, {"use_case": use_case})

