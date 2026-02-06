"""
Automation Combination Service

Combines multiple HomeIQ JSON automations into a single automation.
"""

import logging
from typing import Any
from datetime import datetime, timezone

from shared.homeiq_automation.schema import (
    HomeIQAction,
    HomeIQAutomation,
    HomeIQCondition,
    HomeIQMetadata,
    HomeIQTrigger,
    DeviceContext,
)

logger = logging.getLogger(__name__)


class AutomationCombiner:
    """
    Service for combining multiple HomeIQ JSON automations.
    
    Features:
    - Merge triggers, conditions, actions
    - Resolve conflicts
    - Generate combined automation JSON
    """
    
    def combine(
        self,
        automations: list[HomeIQAutomation | dict[str, Any]],
        alias: str | None = None,
        description: str | None = None
    ) -> HomeIQAutomation:
        """
        Combine multiple HomeIQ automations into one.
        
        Args:
            automations: List of HomeIQ automations (dict or HomeIQAutomation)
            alias: Optional alias for combined automation
            description: Optional description for combined automation
        
        Returns:
            Combined HomeIQAutomation instance
        """
        # Convert dicts to HomeIQAutomation
        automation_objects: list[HomeIQAutomation] = []
        for auto in automations:
            if isinstance(auto, dict):
                automation_objects.append(HomeIQAutomation(**auto))
            else:
                automation_objects.append(auto)
        
        if not automation_objects:
            raise ValueError("At least one automation is required")
        
        # Merge triggers
        combined_triggers: list[HomeIQTrigger] = []
        for auto in automation_objects:
            combined_triggers.extend(auto.triggers)
        
        # Merge conditions
        combined_conditions: list[HomeIQCondition] | None = None
        all_conditions: list[HomeIQCondition] = []
        for auto in automation_objects:
            if auto.conditions:
                all_conditions.extend(auto.conditions)
        if all_conditions:
            combined_conditions = all_conditions
        
        # Merge actions
        combined_actions: list[HomeIQAction] = []
        for auto in automation_objects:
            combined_actions.extend(auto.actions)
        
        # Merge device context
        combined_device_ids: set[str] = set()
        combined_entity_ids: set[str] = set()
        combined_device_types: set[str] = set()
        combined_area_ids: set[str] = set()
        
        for auto in automation_objects:
            combined_device_ids.update(auto.device_context.device_ids)
            combined_entity_ids.update(auto.device_context.entity_ids)
            combined_device_types.update(auto.device_context.device_types)
            if auto.device_context.area_ids:
                combined_area_ids.update(auto.device_context.area_ids)
        
        combined_device_context = DeviceContext(
            device_ids=list(combined_device_ids),
            entity_ids=list(combined_entity_ids),
            device_types=list(combined_device_types),
            area_ids=list(combined_area_ids) if combined_area_ids else None
        )
        
        # Merge area context
        combined_area_context: list[str] | None = None
        all_area_ids: set[str] = set()
        for auto in automation_objects:
            if auto.area_context:
                all_area_ids.update(auto.area_context)
        if all_area_ids:
            combined_area_context = list(all_area_ids)
        
        # Merge dependencies
        combined_dependencies: set[str] = set()
        for auto in automation_objects:
            if auto.dependencies:
                combined_dependencies.update(auto.dependencies)
        
        # Merge tags
        combined_tags: set[str] = set()
        for auto in automation_objects:
            if auto.tags:
                combined_tags.update(auto.tags)
        
        # Determine use_case and complexity
        use_cases = [auto.homeiq_metadata.use_case for auto in automation_objects]
        use_case = max(set(use_cases), key=use_cases.count) if use_cases else "convenience"
        
        complexities = [auto.homeiq_metadata.complexity for auto in automation_objects]
        complexity = max(set(complexities), key=complexities.count) if complexities else "medium"
        
        # Create combined metadata
        combined_metadata = HomeIQMetadata(
            created_by="automation_combiner",
            created_at=datetime.now(timezone.utc),
            use_case=use_case,
            complexity=complexity
        )
        
        # Create combined automation
        combined_automation = HomeIQAutomation(
            alias=alias or f"Combined: {', '.join(a.alias for a in automation_objects[:3])}",
            description=description or f"Combined from {len(automation_objects)} automations",
            version="1.0.0",
            homeiq_metadata=combined_metadata,
            device_context=combined_device_context,
            area_context=combined_area_context,
            triggers=combined_triggers,
            conditions=combined_conditions,
            actions=combined_actions,
            dependencies=list(combined_dependencies) if combined_dependencies else None,
            tags=list(combined_tags) if combined_tags else None
        )
        
        logger.info(f"Combined {len(automation_objects)} automations into: {combined_automation.alias}")
        return combined_automation

