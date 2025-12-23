"""
Blueprint Input Filler Service

Fills blueprint template inputs with user's actual entities and values.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class BlueprintInputFiller:
    """
    Fill blueprint inputs with user's devices and values.
    
    Maps validated entities to blueprint input requirements and extracts
    numeric/boolean values from suggestion text.
    """

    async def fill_blueprint_inputs(
        self,
        blueprint: dict[str, Any],
        suggestion: dict[str, Any],
        validated_entities: dict[str, str]
    ) -> dict[str, Any]:
        """
        Fill blueprint inputs with user's actual entities and values.

        Args:
            blueprint: Blueprint dictionary with metadata
            suggestion: Suggestion dictionary with description, etc.
            validated_entities: Dictionary mapping device names to entity_ids

        Returns:
            Dictionary of filled input values (input_name -> value)
        """
        metadata = blueprint.get("metadata", {})
        blueprint_vars = metadata.get("_blueprint_variables", {})
        filled_inputs = {}

        description = suggestion.get("description", "").lower()
        trigger_summary = suggestion.get("trigger_summary", "").lower()
        action_summary = suggestion.get("action_summary", "").lower()
        full_text = f"{description} {trigger_summary} {action_summary}"

        for input_name, input_spec in blueprint_vars.items():
            filled_value = await self._fill_input(
                input_name=input_name,
                input_spec=input_spec,
                suggestion=suggestion,
                validated_entities=validated_entities,
                full_text=full_text
            )

            if filled_value is not None:
                filled_inputs[input_name] = filled_value
            else:
                # Use default if available
                default = input_spec.get("default")
                if default is not None:
                    filled_inputs[input_name] = default
                else:
                    logger.warning(f"No value found for blueprint input: {input_name}")

        return filled_inputs

    async def _fill_input(
        self,
        input_name: str,
        input_spec: dict[str, Any],
        suggestion: dict[str, Any],
        validated_entities: dict[str, str],
        full_text: str
    ) -> Any:
        """Fill a single blueprint input based on its selector type."""
        selector = input_spec.get("selector", {})

        # Handle entity selector
        if "entity" in selector:
            return self._match_entity_to_input(
                input_name=input_name,
                input_spec=input_spec,
                selector=selector["entity"],
                validated_entities=validated_entities
            )

        # Handle number selector
        if "number" in selector:
            return self._extract_number_value(
                input_name=input_name,
                input_spec=input_spec,
                full_text=full_text
            )

        # Handle boolean selector
        if "boolean" in selector:
            return self._extract_boolean_value(
                input_name=input_name,
                input_spec=input_spec,
                full_text=full_text
            )

        # Handle text selector
        if "text" in selector:
            return self._extract_text_value(
                input_name=input_name,
                input_spec=input_spec,
                full_text=full_text
            )

        # Handle time selector
        if "time" in selector:
            return self._extract_time_value(
                input_name=input_name,
                input_spec=input_spec,
                full_text=full_text
            )

        logger.debug(f"Unknown selector type for input: {input_name}")
        return None

    def _match_entity_to_input(
        self,
        input_name: str,
        input_spec: dict[str, Any],
        selector: dict[str, Any],
        validated_entities: dict[str, Any]
    ) -> str | None:
        """Match user entity to blueprint input requirement."""
        required_domain = selector.get("domain", "")
        device_class = selector.get("device_class", "")
        input_name_lower = input_name.lower()

        # Try to match by input name first (e.g., "motion_sensor" -> look for motion sensors)
        for entity_name, entity_id in validated_entities.items():
            entity_domain = entity_id.split(".")[0] if "." in entity_id else ""

            # Check domain match
            if required_domain and entity_domain != required_domain:
                continue

            # Check if input name hints at what to look for
            if input_name_lower in entity_name.lower() or entity_name.lower() in input_name_lower:
                return entity_id

        # Fallback: match by domain and device_class
        for entity_name, entity_id in validated_entities.items():
            entity_domain = entity_id.split(".")[0] if "." in entity_id else ""

            if required_domain and entity_domain == required_domain:
                # If device_class specified, try to match (would need entity metadata)
                # For now, return first matching domain
                return entity_id

        # Last resort: return first entity if only one
        if len(validated_entities) == 1:
            return list(validated_entities.values())[0]

        logger.warning(
            f"Could not match entity for blueprint input: {input_name} "
            f"(required: domain={required_domain}, device_class={device_class})"
        )
        return None

    def _extract_number_value(
        self,
        input_name: str,
        input_spec: dict[str, Any],
        full_text: str
    ) -> int | float | None:
        """Extract numeric value from suggestion text."""
        input_name_lower = input_name.lower()

        # Look for patterns like "50% brightness", "30 seconds", "75 brightness"
        patterns = [
            rf"{input_name_lower}.*?(\d+)",  # "brightness 50"
            rf"(\d+).*?{input_name_lower}",  # "50 brightness"
            rf"(\d+)%",  # "50%" (for brightness/percentage)
            rf"(\d+)\s*(?:seconds?|sec|minutes?|min)",  # "30 seconds"
        ]

        for pattern in patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                # Check if percentage
                if "%" in full_text[match.start():match.end()]:
                    return int(value)
                return int(value) if value.is_integer() else value

        # Check selector constraints for default
        selector = input_spec.get("selector", {}).get("number", {})
        default = selector.get("default")
        if default is not None:
            return default

        # Use min value as fallback
        min_val = selector.get("min", 0)
        return min_val

    def _extract_boolean_value(
        self,
        input_name: str,
        input_spec: dict[str, Any],
        full_text: str
    ) -> bool | None:
        """Extract boolean value from suggestion text."""
        input_name_lower = input_name.lower()
        full_text_lower = full_text.lower()

        # Negative keywords (check first to avoid false positives)
        negative_keywords = ["disable", "off", "false", "no", "never", "don't", "dont"]
        # Positive keywords (exclude "on" to avoid false matches with "turn on")
        positive_keywords = ["enable", "true", "yes", "only", "always"]

        # Check for negative keywords first (higher priority)
        for keyword in negative_keywords:
            if keyword in full_text_lower:
                # Check if input name relates: keyword in input name OR input name in text
                if keyword in input_name_lower or input_name_lower in full_text_lower:
                    return False

        # Check for positive keywords
        for keyword in positive_keywords:
            if keyword in full_text_lower:
                # Check if input name relates to this keyword
                # Multiple ways to relate:
                # 1. Input name contains the keyword (e.g., "enable_notification" contains "enable")
                # 2. Input name appears in text (e.g., "enable_notification" in "enable notifications...")
                # 3. Input name equals keyword (e.g., "enable" == "enable")
                # 4. Input name starts with keyword (e.g., "enable_notification" starts with "enable")
                relates = (
                    keyword in input_name_lower or
                    input_name_lower in full_text_lower or
                    input_name_lower == keyword or
                    input_name_lower.startswith(keyword + "_")
                )
                if relates:
                    return True

        # Check default
        selector = input_spec.get("selector", {}).get("boolean", {})
        default = selector.get("default")
        if default is not None:
            return default

        return False  # Default to False

    def _extract_text_value(
        self,
        input_name: str,
        input_spec: dict[str, Any],
        full_text: str
    ) -> str | None:
        """Extract text value from suggestion text."""
        # For text inputs, try to find quoted strings or specific patterns
        # This is basic - can be enhanced with NLP
        quoted = re.findall(r'"([^"]+)"', full_text)
        if quoted:
            return quoted[0]

        # Check default
        selector = input_spec.get("selector", {}).get("text", {})
        default = selector.get("default")
        if default is not None:
            return default

        return None

    def _extract_time_value(
        self,
        input_name: str,
        input_spec: dict[str, Any],
        full_text: str
    ) -> str | None:
        """Extract time value from suggestion text."""
        # Look for time patterns like "7:00 AM", "07:00", "7am"
        time_patterns = [
            r"(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)",
            r"(\d{1,2}):(\d{2})",
            r"(\d{1,2})\s*(am|pm|AM|PM)",
        ]

        for pattern in time_patterns:
            match = re.search(pattern, full_text)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2)) if len(match.groups()) > 1 and match.group(2).isdigit() else 0
                period = match.group(-1).upper() if len(match.groups()) > 1 else None

                # Convert to 24-hour format
                if period == "PM" and hour != 12:
                    hour += 12
                elif period == "AM" and hour == 12:
                    hour = 0

                return f"{hour:02d}:{minute:02d}:00"

        # Check default
        selector = input_spec.get("selector", {}).get("time", {})
        default = selector.get("default")
        if default is not None:
            return default

        return "00:00:00"  # Default midnight

