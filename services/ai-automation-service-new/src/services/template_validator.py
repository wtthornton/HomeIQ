"""
Template Validator Service

Hybrid Flow Implementation: Deterministic validation of automation plans
Validates template_id, parameters, resolves context, performs safety checks.
"""

import logging
from typing import Any

from ..clients.data_api_client import DataAPIClient
from ..clients.ha_client import HomeAssistantClient
from ..templates.template_library import TemplateLibrary
from ..templates.template_schema import SafetyClass, Template

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


class TemplateValidator:
    """
    Service for validating automation plans against templates.

    Responsibilities:
    - Validate template_id exists and version matches
    - Validate parameters against template schema (types, enums, bounds)
    - Resolve context (room → area_id, device names → entity_ids)
    - Safety checks (device types, forbidden targets)
    """

    # Entity states that indicate the sensor is not operational
    _INACTIVE_STATES = {"unavailable", "unknown"}

    def __init__(
        self,
        template_library: TemplateLibrary,
        data_api_client: DataAPIClient,
        ha_client: HomeAssistantClient | None = None,
    ):
        """
        Initialize template validator.

        Args:
            template_library: Template library for template lookups
            data_api_client: Data API client for entity/device lookups
            ha_client: Optional HA client for live state checks
        """
        self.template_library = template_library
        self.data_api_client = data_api_client
        self.ha_client = ha_client

    async def validate_plan(
        self, plan_id: str, template_id: str, template_version: int, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Validate automation plan.

        Args:
            plan_id: Plan identifier
            template_id: Template identifier
            template_version: Template version
            parameters: Template parameters

        Returns:
            Validation result with valid flag, errors, resolved_context, safety info

        Raises:
            ValidationError: If validation fails critically
        """
        validation_errors = []
        resolved_context = {}

        # Step 1: Validate template exists
        template = self.template_library.get_template(template_id, template_version)
        if not template:
            validation_errors.append(
                {
                    "field": "template_id",
                    "message": f"Template '{template_id}' version {template_version} not found",
                }
            )
            return {
                "valid": False,
                "validation_errors": validation_errors,
                "resolved_context": {},
                "safety": {
                    "allowed": False,
                    "requires_confirmation": True,
                    "reasons": ["Template not found"],
                },
            }

        # Step 2: Validate parameters against schema
        for param_name, param_schema in template.parameter_schema.items():
            param_value = parameters.get(param_name)

            # Check required
            if param_schema.required and param_value is None:
                validation_errors.append(
                    {
                        "field": param_name,
                        "message": f"Required parameter '{param_name}' is missing",
                    }
                )
                continue

            # Use default if not provided
            if param_value is None and param_schema.default is not None:
                param_value = param_schema.default
                parameters[param_name] = param_value

            if param_value is None:
                continue  # Optional parameter not provided

            # Validate type
            type_valid = self._validate_parameter_type(param_value, param_schema)
            if not type_valid:
                validation_errors.append(
                    {
                        "field": param_name,
                        "message": f"Parameter '{param_name}' has invalid type. Expected {param_schema.type.value}",
                    }
                )
                continue

            # Validate enum
            if param_schema.enum and param_value not in param_schema.enum:
                validation_errors.append(
                    {
                        "field": param_name,
                        "message": f"Parameter '{param_name}' must be one of: {param_schema.enum}",
                    }
                )
                continue

            # Validate bounds (for numeric types)
            if param_schema.type.value in ["integer", "float"]:
                if param_schema.min is not None and param_value < param_schema.min:
                    validation_errors.append(
                        {
                            "field": param_name,
                            "message": f"Parameter '{param_name}' must be >= {param_schema.min}",
                        }
                    )
                if param_schema.max is not None and param_value > param_schema.max:
                    validation_errors.append(
                        {
                            "field": param_name,
                            "message": f"Parameter '{param_name}' must be <= {param_schema.max}",
                        }
                    )

        # Step 3: Resolve context (room → area_id, device → entity_id)
        try:
            resolved_context = await self._resolve_context(template, parameters)
        except Exception as e:
            validation_errors.append(
                {"field": "context", "message": f"Failed to resolve context: {str(e)}"}
            )

        # Step 4: Safety checks
        safety_result = self._check_safety(template, parameters, resolved_context)

        # Return validation result
        return {
            "valid": len(validation_errors) == 0,
            "validation_errors": validation_errors,
            "resolved_context": resolved_context,
            "safety": safety_result,
        }

    def _validate_parameter_type(self, value: Any, param_schema) -> bool:
        """Validate parameter type matches schema."""
        expected_type = param_schema.type.value

        type_map = {
            "string": str,
            "integer": int,
            "float": (int, float),  # Accept int for float (Python allows this)
            "boolean": bool,
            "object": dict,
            "array": list,
            "time": str,
            "duration": str,
        }

        expected_python_type = type_map.get(expected_type)
        if expected_python_type is None:
            return True  # Unknown type, skip validation

        if isinstance(expected_python_type, tuple):
            return isinstance(value, expected_python_type)
        return isinstance(value, expected_python_type)

    async def _resolve_context(
        self, template: Template, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Resolve context (room names → area_ids, device names → entity_ids).

        Args:
            template: Template instance
            parameters: Template parameters

        Returns:
            Resolved context dictionary
        """
        resolved = {}

        # Resolve room_type → area_id
        if "room_type" in parameters:
            room_type = parameters["room_type"]
            try:
                areas = await self.data_api_client.fetch_areas()

                # Find matching area
                matching_area = None
                for area in areas:
                    area_name = area.get("name", "").lower()
                    if room_type.lower() in area_name or area_name in room_type.lower():
                        matching_area = area
                        break

                if matching_area:
                    resolved["matched_room_id"] = matching_area.get("area_id")
                    resolved["matched_area_id"] = matching_area.get("area_id")
                else:
                    logger.warning(f"Could not resolve room_type '{room_type}' to area_id")

            except Exception as e:
                logger.warning(f"Failed to resolve room_type: {e}")

        # Resolve target_area → area_id (similar logic)
        if "target_area" in parameters:
            target_area = parameters["target_area"]
            if "matched_area_id" not in resolved:
                try:
                    areas = await self.data_api_client.fetch_areas()

                    for area in areas:
                        if target_area.lower() in area.get("name", "").lower():
                            resolved["matched_area_id"] = area.get("area_id")
                            break
                except Exception as e:
                    logger.warning(f"Failed to resolve target_area: {e}")

        # Resolve presence/motion sensors (for room_entry_light_on template)
        if template.template_id == "room_entry_light_on" and "matched_room_id" in resolved:
            area_id = resolved["matched_room_id"]
            try:
                # Query entities in this specific area
                area_entities = await self.data_api_client.fetch_entities_in_area(area_id)

                # Find presence/motion sensors
                presence_sensors = [
                    e["entity_id"]
                    for e in area_entities
                    if e.get("device_class") in ["presence", "motion"]
                    and e.get("domain") == "binary_sensor"
                ]

                if presence_sensors:
                    resolved["presence_sensor_entity"] = presence_sensors[0]
                    resolved["presence_sensor_entities"] = presence_sensors

            except Exception as e:
                logger.warning(f"Failed to resolve presence sensors: {e}")

        # Resolve motion sensors (for motion_dim_off template)
        if template.template_id == "motion_dim_off" and "target_area" in parameters:
            if "matched_area_id" in resolved:
                area_id = resolved["matched_area_id"]
            else:
                area_id = parameters.get("target_area")

            try:
                # Query entities in this specific area
                area_entities = await self.data_api_client.fetch_entities_in_area(area_id)

                motion_sensors = [
                    e["entity_id"]
                    for e in area_entities
                    if e.get("device_class") in ("motion", "occupancy")
                ]

                # Fallback: if area-based lookup found no motion sensors,
                # search all binary_sensors by name pattern (data-api may
                # have area_id=null for sensors not yet mapped to an area).
                if not motion_sensors:
                    logger.info(
                        f"No motion sensors found via area lookup for '{area_id}', "
                        "falling back to name-based search"
                    )
                    try:
                        all_entities = await self.data_api_client.fetch_entities(limit=2000)
                        area_lower = area_id.lower()
                        motion_sensors = [
                            e["entity_id"]
                            for e in all_entities
                            if (
                                e.get("domain") == "binary_sensor"
                                and area_lower in e.get("entity_id", "").lower()
                                and (
                                    e.get("device_class") in ("motion", "occupancy")
                                    or "motion" in e.get("entity_id", "").lower()
                                    or "presence" in e.get("entity_id", "").lower()
                                    or "occupancy" in e.get("entity_id", "").lower()
                                )
                            )
                        ]
                        if motion_sensors:
                            logger.info(
                                f"Name-based fallback found {len(motion_sensors)} "
                                f"motion sensors for '{area_id}': {motion_sensors}"
                            )
                    except Exception as fallback_exc:
                        logger.warning(f"Name-based motion sensor fallback failed: {fallback_exc}")

                # Filter out sensors that are unavailable/unknown in HA
                if motion_sensors and self.ha_client:
                    active_sensors = []
                    for entity_id in motion_sensors:
                        try:
                            state = await self.ha_client.get_state(entity_id)
                            if state is None:
                                logger.warning(
                                    f"Could not get state for {entity_id}, keeping by default"
                                )
                                active_sensors.append(entity_id)
                            elif state.get("state") in self._INACTIVE_STATES:
                                logger.info(
                                    f"Excluding inactive sensor {entity_id} "
                                    f"(state={state.get('state')})"
                                )
                            else:
                                active_sensors.append(entity_id)
                        except Exception as exc:
                            logger.warning(f"Error checking state for {entity_id}: {exc}, keeping")
                            active_sensors.append(entity_id)
                    if active_sensors:
                        motion_sensors = active_sensors

                if motion_sensors:
                    # ON trigger: all sensors (OR — any one triggers lights on)
                    resolved["motion_sensor_entities"] = motion_sensors

                    # OFF trigger: template that requires ALL sensors off (AND)
                    # e.g. {{ is_state('sensor.a', 'off') and is_state('sensor.b', 'off') }}
                    all_off_parts = [f"is_state('{eid}', 'off')" for eid in motion_sensors]
                    resolved["motion_all_off_template"] = (
                        "{{ " + "\n   and ".join(all_off_parts) + " }}"
                    )
                    logger.info(
                        f"Resolved {len(motion_sensors)} motion sensors for '{area_id}': "
                        f"{motion_sensors}"
                    )
                else:
                    logger.warning(f"No active motion sensors found in area '{area_id}'")

            except Exception as e:
                logger.warning(f"Failed to resolve motion sensors: {e}")

            # Pre-compute zero-padded timeout duration for HA "for:" field
            timeout_s = parameters.get("motion_timeout_seconds", 60)
            mins, secs = divmod(int(timeout_s), 60)
            hours, mins = divmod(mins, 60)
            resolved["motion_timeout_for"] = f"{hours:02d}:{mins:02d}:{secs:02d}"

        return resolved

    def _check_safety(
        self, template: Template, parameters: dict[str, Any], resolved_context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Perform safety checks.

        Args:
            template: Template instance
            parameters: Template parameters
            resolved_context: Resolved context

        Returns:
            Safety check result
        """
        safety_class = SafetyClass(template.safety_class)
        requires_confirmation = safety_class in [SafetyClass.HIGH, SafetyClass.CRITICAL]
        reasons = []

        # Check forbidden targets
        if template.forbidden_targets:
            # Check if any resolved entities match forbidden patterns
            for forbidden in template.forbidden_targets:
                # Simple pattern matching (can be enhanced)
                if any(forbidden.lower() in str(v).lower() for v in resolved_context.values()):
                    reasons.append(f"Forbidden target pattern '{forbidden}' detected")
                    requires_confirmation = True

        return {
            "allowed": True,  # Can be set to False if critical issues found
            "requires_confirmation": requires_confirmation,
            "reasons": reasons,
        }
