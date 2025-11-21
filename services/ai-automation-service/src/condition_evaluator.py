"""
Condition Evaluation Engine with AND/OR/NOT Logic
Home Assistant Pattern Improvement #3 (2025)

Provides runtime condition evaluation with AND/OR/NOT logic operators,
nested conditions, and template condition support.
Compatible with Home Assistant 2025 condition evaluation patterns.
"""

import logging
from datetime import datetime
from datetime import time as dt_time
from enum import Enum
from typing import Any

from .clients.ha_client import HomeAssistantClient
from .template_engine import TemplateEngine

logger = logging.getLogger(__name__)


class ConditionType(str, Enum):
    """Condition type enumeration"""
    STATE = "state"
    NUMERIC_STATE = "numeric_state"
    TIME = "time"
    SUN = "sun"
    TEMPLATE = "template"
    ZONE = "zone"
    AND = "and"
    OR = "or"
    NOT = "not"
    DEVICE = "device"


class ConditionEvaluator:
    """
    Evaluates automation conditions with AND/OR/NOT logic.

    Supports Home Assistant-style condition evaluation:
    - AND/OR/NOT logic operators
    - Nested conditions
    - Template conditions
    - State conditions
    - Numeric state conditions
    - Time-based conditions
    """

    def __init__(self, ha_client: HomeAssistantClient, template_engine: TemplateEngine | None = None):
        """
        Initialize condition evaluator.

        Args:
            ha_client: Home Assistant client for fetching states
            template_engine: Optional template engine for template conditions
        """
        self.ha_client = ha_client
        self.template_engine = template_engine or TemplateEngine(ha_client)

    async def evaluate(
        self,
        condition: dict[str, Any] | list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> bool:
        """
        Evaluate condition(s) with AND/OR/NOT logic.

        Args:
            condition: Condition dict or list of conditions
            context: Optional context for evaluation

        Returns:
            True if condition(s) are met, False otherwise

        Examples:
            # AND logic
            condition = {
                "condition": "and",
                "conditions": [
                    {"condition": "state", "entity_id": "sensor.temperature", "state": "on"},
                    {"condition": "numeric_state", "entity_id": "sensor.temp", "above": 20}
                ]
            }

            # OR logic
            condition = {
                "condition": "or",
                "conditions": [
                    {"condition": "state", "entity_id": "switch.1", "state": "on"},
                    {"condition": "state", "entity_id": "switch.2", "state": "on"}
                ]
            }

            # NOT logic
            condition = {
                "condition": "not",
                "conditions": [
                    {"condition": "state", "entity_id": "sensor.motion", "state": "on"}
                ]
            }

            # List of conditions (defaults to AND)
            condition = [
                {"condition": "state", "entity_id": "sensor.temp", "state": "on"},
                {"condition": "numeric_state", "entity_id": "sensor.temp", "above": 20}
            ]
        """
        if context is None:
            context = {}

        # Handle list of conditions (default to AND logic)
        if isinstance(condition, list):
            results = []
            for cond in condition:
                result = await self.evaluate(cond, context)
                results.append(result)
            # Default to AND: all conditions must be True
            return all(results)

        # Handle dict condition
        if not isinstance(condition, dict):
            logger.warning(f"Invalid condition type: {type(condition)}")
            return False

        # Check for logic operator
        if "condition" in condition:
            condition_type = condition["condition"]

            # AND logic
            if condition_type == ConditionType.AND:
                sub_conditions = condition.get("conditions", [])
                if not sub_conditions:
                    logger.warning("AND condition with no sub-conditions")
                    return True  # Empty AND is True

                results = []
                for sub_cond in sub_conditions:
                    result = await self.evaluate(sub_cond, context)
                    results.append(result)
                return all(results)

            # OR logic
            if condition_type == ConditionType.OR:
                sub_conditions = condition.get("conditions", [])
                if not sub_conditions:
                    logger.warning("OR condition with no sub-conditions")
                    return False  # Empty OR is False

                results = []
                for sub_cond in sub_conditions:
                    result = await self.evaluate(sub_cond, context)
                    results.append(result)
                return any(results)

            # NOT logic
            if condition_type == ConditionType.NOT:
                sub_conditions = condition.get("conditions", [])
                if len(sub_conditions) != 1:
                    logger.warning(f"NOT condition should have exactly 1 sub-condition, got {len(sub_conditions)}")
                    return False

                sub_result = await self.evaluate(sub_conditions[0], context)
                return not sub_result

            # Specific condition type
            return await self._evaluate_specific_condition(condition, context)

        # No condition type specified - treat as state condition
        logger.warning("Condition dict without 'condition' key, treating as state condition")
        return await self._evaluate_state_condition(condition, context)

    async def _evaluate_specific_condition(
        self,
        condition: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        """
        Evaluate specific condition type.

        Args:
            condition: Condition dict
            context: Evaluation context

        Returns:
            True if condition is met, False otherwise
        """
        condition_type = condition.get("condition")

        try:
            if condition_type == ConditionType.STATE:
                return await self._evaluate_state_condition(condition, context)

            if condition_type == ConditionType.NUMERIC_STATE:
                return await self._evaluate_numeric_state_condition(condition, context)

            if condition_type == ConditionType.TIME:
                return await self._evaluate_time_condition(condition, context)

            if condition_type == ConditionType.TEMPLATE:
                return await self._evaluate_template_condition(condition, context)

            if condition_type == ConditionType.ZONE:
                return await self._evaluate_zone_condition(condition, context)

            if condition_type == ConditionType.DEVICE:
                return await self._evaluate_device_condition(condition, context)

            logger.warning(f"Unknown condition type: {condition_type}")
            return False

        except Exception as e:
            logger.exception(f"Error evaluating condition {condition_type}: {e}")
            return False

    async def _evaluate_state_condition(
        self,
        condition: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        """Evaluate state condition"""
        entity_id = condition.get("entity_id")
        target_state = condition.get("state")

        if not entity_id:
            logger.warning("State condition missing entity_id")
            return False

        if target_state is None:
            logger.warning("State condition missing state")
            return False

        try:
            # Get current state
            states = await self.ha_client.get_states()
            entity = next((s for s in states if s["entity_id"] == entity_id), None)

            if not entity:
                logger.warning(f"Entity not found: {entity_id}")
                return False

            current_state = entity.get("state", "unknown")

            # Handle list of acceptable states
            if isinstance(target_state, list):
                return current_state in target_state

            # Handle string state
            return current_state == target_state

        except Exception as e:
            logger.exception(f"Error evaluating state condition: {e}")
            return False

    async def _evaluate_numeric_state_condition(
        self,
        condition: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        """Evaluate numeric state condition"""
        entity_id = condition.get("entity_id")
        above = condition.get("above")
        below = condition.get("below")
        value_template = condition.get("value_template")

        if not entity_id:
            logger.warning("Numeric state condition missing entity_id")
            return False

        try:
            # Get current state
            states = await self.ha_client.get_states()
            entity = next((s for s in states if s["entity_id"] == entity_id), None)

            if not entity:
                logger.warning(f"Entity not found: {entity_id}")
                return False

            current_state_str = entity.get("state", "unknown")

            # Handle value_template
            if value_template:
                rendered = await self.template_engine.render(value_template, context)
                try:
                    current_value = float(rendered)
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert template result to float: {rendered}")
                    return False
            else:
                try:
                    current_value = float(current_state_str)
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert state to float: {current_state_str}")
                    return False

            # Check above threshold
            if above is not None and current_value <= above:
                return False

            # Check below threshold
            return not (below is not None and current_value >= below)

        except Exception as e:
            logger.exception(f"Error evaluating numeric state condition: {e}")
            return False

    async def _evaluate_time_condition(
        self,
        condition: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        """Evaluate time condition"""
        after = condition.get("after")
        before = condition.get("before")
        weekday = condition.get("weekday")

        now = datetime.now()
        current_time = now.time()

        # Check weekday
        if weekday:
            weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
            current_weekday = weekdays[now.weekday()]
            if current_weekday not in weekday:
                return False

        # Check after time
        if after:
            after_time = self._parse_time(after)
            if after_time and current_time < after_time:
                return False

        # Check before time
        if before:
            before_time = self._parse_time(before)
            if before_time and current_time > before_time:
                return False

        return True

    async def _evaluate_template_condition(
        self,
        condition: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        """Evaluate template condition"""
        value_template = condition.get("value_template")

        if not value_template:
            logger.warning("Template condition missing value_template")
            return False

        try:
            rendered = await self.template_engine.render(value_template, context)

            # Template should evaluate to True/False
            # Handle common string representations
            rendered_lower = str(rendered).lower().strip()
            if rendered_lower in ("true", "1", "yes", "on"):
                return True
            if rendered_lower in ("false", "0", "no", "off", ""):
                return False

            # Try boolean conversion
            try:
                return bool(float(rendered))
            except (ValueError, TypeError):
                return bool(rendered)

        except Exception as e:
            logger.exception(f"Error evaluating template condition: {e}")
            return False

    async def _evaluate_zone_condition(
        self,
        condition: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        """Evaluate zone condition"""
        # Zone conditions require person/device tracker entities
        # This is a simplified implementation
        entity_id = condition.get("entity_id")
        zone = condition.get("zone")

        if not entity_id or not zone:
            logger.warning("Zone condition missing entity_id or zone")
            return False

        try:
            states = await self.ha_client.get_states()
            entity = next((s for s in states if s["entity_id"] == entity_id), None)

            if not entity:
                return False

            # Check if entity is in zone
            attributes = entity.get("attributes", {})
            entity_zone = attributes.get("zone")

            return entity_zone == zone

        except Exception as e:
            logger.exception(f"Error evaluating zone condition: {e}")
            return False

    async def _evaluate_device_condition(
        self,
        condition: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        """Evaluate device condition"""
        # Device conditions check device state
        # This is a simplified implementation
        device_id = condition.get("device_id")
        condition.get("type")
        condition.get("subtype")

        if not device_id:
            logger.warning("Device condition missing device_id")
            return False

        # For now, return True (full device condition evaluation would require
        # device registry integration)
        logger.debug(f"Device condition evaluation not fully implemented: {device_id}")
        return True

    def _parse_time(self, time_str: str) -> dt_time | None:
        """Parse time string (HH:MM:SS or HH:MM)"""
        try:
            parts = time_str.split(":")
            if len(parts) == 2:
                hour, minute = int(parts[0]), int(parts[1])
                return dt_time(hour, minute)
            if len(parts) == 3:
                hour, minute, second = int(parts[0]), int(parts[1]), int(parts[2])
                return dt_time(hour, minute, second)
        except (ValueError, IndexError):
            logger.warning(f"Could not parse time string: {time_str}")
        return None

