"""
Blueprint Renderer Service

Renders blueprint YAML by replacing !input variables with actual values.
"""

import logging
import re
import uuid
from typing import Any

import yaml as yaml_lib

logger = logging.getLogger(__name__)


class BlueprintRenderer:
    """
    Render blueprint YAML by replacing !input variables.
    
    Converts blueprint template YAML into valid Home Assistant automation YAML
    by substituting input variables with actual values.
    """

    async def render_blueprint(
        self,
        blueprint_yaml: str,
        inputs: dict[str, Any],
        suggestion: dict[str, Any] | None = None
    ) -> str:
        """
        Render blueprint YAML with filled inputs.

        Args:
            blueprint_yaml: Full blueprint YAML string from automation-miner
            inputs: Dictionary of filled input values (input_name -> value)
            suggestion: Optional suggestion dictionary for metadata

        Returns:
            Valid Home Assistant automation YAML string
        """
        if not blueprint_yaml:
            raise ValueError("Blueprint YAML is empty")

        if not inputs:
            raise ValueError("No inputs provided for blueprint rendering")

        try:
            # Replace !input variables BEFORE parsing (YAML parser can't handle !input tags)
            rendered_yaml = self._substitute_inputs(blueprint_yaml, inputs)

            # Now parse the YAML (after substitution)
            blueprint_data = yaml_lib.safe_load(rendered_yaml)

            if not blueprint_data:
                raise ValueError("Failed to parse blueprint YAML after substitution")

            # Extract automation section (everything except blueprint:)
            rendered_data = self._extract_automation_section(blueprint_data)

            # Add 2025 HA standards (id, alias, description)
            rendered_data = self._add_ha_2025_standards(rendered_data, suggestion)

            # Convert back to YAML
            final_yaml = yaml_lib.dump(rendered_data, default_flow_style=False, sort_keys=False)

            logger.info(f"Successfully rendered blueprint YAML ({len(final_yaml)} chars)")
            return final_yaml

        except Exception as e:
            logger.error(f"Failed to render blueprint: {e}", exc_info=True)
            raise ValueError(f"Blueprint rendering failed: {e}") from e

    def _extract_automation_section(self, blueprint_data: dict[str, Any]) -> dict[str, Any]:
        """Extract automation section, removing blueprint metadata."""
        automation_data = {}

        # Copy all keys except 'blueprint'
        for key, value in blueprint_data.items():
            if key != "blueprint":
                automation_data[key] = value

        return automation_data

    def _substitute_inputs(self, yaml_str: str, inputs: dict[str, Any]) -> str:
        """
        Replace !input variable_name with actual values.

        Handles various YAML formats:
        - !input variable_name
        - entity_id: !input motion_sensor
        - brightness_pct: !input brightness
        """
        result = yaml_str

        # Find all !input references
        input_pattern = r'!input\s+(\w+)'
        matches = re.finditer(input_pattern, result)

        # Replace in reverse order to preserve positions
        replacements = []
        for match in matches:
            input_name = match.group(1)
            if input_name in inputs:
                value = inputs[input_name]
                # Format value appropriately
                formatted_value = self._format_yaml_value(value)
                replacements.append((match.start(), match.end(), formatted_value))

        # Apply replacements in reverse order
        for start, end, replacement in reversed(replacements):
            result = result[:start] + replacement + result[end:]

        return result

    def _format_yaml_value(self, value: Any) -> str:
        """Format value for YAML insertion."""
        if isinstance(value, str):
            # Escape quotes and wrap in quotes if needed
            if ":" in value or " " in value or value.startswith("!"):
                return f'"{value}"'
            return value
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (int, float)):
            return str(value)
        elif value is None:
            return "null"
        else:
            # For complex types, convert to YAML string
            return yaml_lib.dump(value, default_flow_style=True).strip()

    def _add_ha_2025_standards(
        self,
        automation_data: dict[str, Any],
        suggestion: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Add HA 2025.10+ required fields: id, alias, description, initial_state.

        Args:
            automation_data: Parsed automation YAML data
            suggestion: Optional suggestion for metadata

        Returns:
            Automation data with 2025.10+ standards applied
        """
        # Generate unique ID if not present
        if "id" not in automation_data:
            automation_data["id"] = str(uuid.uuid4())

        # Add alias from suggestion or blueprint name
        if "alias" not in automation_data:
            if suggestion:
                alias = suggestion.get("title") or suggestion.get("description", "")[:50]
            else:
                alias = "Automation"
            automation_data["alias"] = alias

        # Add description if not present
        if "description" not in automation_data:
            if suggestion:
                description = suggestion.get("description", "")
            else:
                description = automation_data.get("alias", "Automation")
            automation_data["description"] = description

        # Add initial_state if not present (2025 best practice)
        if "initial_state" not in automation_data:
            automation_data["initial_state"] = True

        return automation_data

