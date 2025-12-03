"""
Home Assistant Tool Implementations

Implements all tool functions for OpenAI function calling.
Each tool function handles validation, execution, and error handling.
"""

import logging
import re
from typing import Any

import yaml

from ..clients.data_api_client import DataAPIClient
from ..clients.ha_client import HomeAssistantClient

logger = logging.getLogger(__name__)


class HAToolHandler:
    """
    Handler for Home Assistant tool execution.

    Implements all tool functions defined in tool_schemas.py.
    """

    def __init__(
        self,
        ha_client: HomeAssistantClient,
        data_api_client: DataAPIClient
    ):
        """
        Initialize tool handler.

        Args:
            ha_client: Home Assistant API client
            data_api_client: Data API client for entity queries
        """
        self.ha_client = ha_client
        self.data_api_client = data_api_client

    async def get_entity_state(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Get current state of a Home Assistant entity.

        Args:
            arguments: Tool arguments containing entity_id

        Returns:
            Dictionary with entity state information
        """
        entity_id = arguments.get("entity_id")
        if not entity_id:
            raise ValueError("entity_id is required")

        # Validate entity ID format
        if not re.match(r"^[a-z_]+\.[a-z0-9_]+$", entity_id):
            raise ValueError(f"Invalid entity_id format: {entity_id}. Expected format: domain.entity_id")

        try:
            # Get all states and find the entity
            states = await self.ha_client.get_states()
            entity_state = None

            for state in states:
                if state.get("entity_id") == entity_id:
                    entity_state = state
                    break

            if not entity_state:
                return {
                    "success": False,
                    "error": f"Entity not found: {entity_id}",
                    "entity_id": entity_id
                }

            return {
                "success": True,
                "entity_id": entity_id,
                "state": entity_state.get("state"),
                "attributes": entity_state.get("attributes", {}),
                "last_changed": entity_state.get("last_changed"),
                "last_updated": entity_state.get("last_updated")
            }
        except Exception as e:
            logger.error(f"Error getting entity state for {entity_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "entity_id": entity_id
            }

    async def call_service(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Call a Home Assistant service.

        Args:
            arguments: Tool arguments containing domain, service, and optional targets

        Returns:
            Dictionary with service call result
        """
        domain = arguments.get("domain")
        service = arguments.get("service")

        if not domain or not service:
            raise ValueError("domain and service are required")

        # Build service data
        service_data: dict[str, Any] = arguments.get("service_data", {})

        # Handle target (entity_id, area_id, or device_id)
        entity_id = arguments.get("entity_id")
        area_id = arguments.get("area_id")
        device_id = arguments.get("device_id")

        # Build target in service_data
        if entity_id:
            # Handle both string and list formats
            if isinstance(entity_id, (str, list)):
                service_data["entity_id"] = entity_id
        elif area_id:
            service_data["area_id"] = area_id
        elif device_id:
            service_data["device_id"] = device_id

        try:
            # Call service via HA client
            # Note: We need to add call_service method to ha_client
            # For now, we'll use aiohttp directly

            session = await self.ha_client._get_session()
            url = f"{self.ha_client.ha_url}/api/services/{domain}/{service}"

            async with session.post(url, json=service_data) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "domain": domain,
                        "service": service,
                        "service_data": service_data,
                        "result": result
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"Service call failed: {response.status} - {error_text}",
                        "domain": domain,
                        "service": service
                    }
        except Exception as e:
            logger.error(f"Error calling service {domain}.{service}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "domain": domain,
                "service": service
            }

    async def get_entities(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Search for entities by domain, area, or name.

        Args:
            arguments: Tool arguments with optional filters

        Returns:
            Dictionary with matching entities
        """
        domain = arguments.get("domain")
        area_id = arguments.get("area_id")
        search_term = arguments.get("search_term")

        try:
            # Fetch entities from Data API
            entities = await self.data_api_client.fetch_entities(
                domain=domain,
                area_id=area_id,
                limit=1000  # Reasonable limit for search
            )

            # Filter by search term if provided
            if search_term:
                search_lower = search_term.lower()
                filtered = []
                for entity in entities:
                    entity_id = entity.get("entity_id", "")
                    friendly_name = entity.get("friendly_name", "")
                    aliases = entity.get("aliases", [])

                    # Check if search term matches
                    if (search_lower in entity_id.lower() or
                        search_lower in friendly_name.lower() or
                        any(search_lower in str(alias).lower() for alias in aliases)):
                        filtered.append(entity)
                entities = filtered

            # Format response
            formatted_entities = []
            for entity in entities[:50]:  # Limit to 50 results
                formatted_entities.append({
                    "entity_id": entity.get("entity_id"),
                    "friendly_name": entity.get("friendly_name"),
                    "domain": entity.get("domain"),
                    "area_id": entity.get("area_id"),
                    "device_id": entity.get("device_id"),
                    "state": entity.get("state")  # If available
                })

            return {
                "success": True,
                "count": len(formatted_entities),
                "total_matched": len(entities),
                "entities": formatted_entities
            }
        except Exception as e:
            logger.error(f"Error searching entities: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def create_automation(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new Home Assistant automation.

        Args:
            arguments: Tool arguments containing automation_yaml and alias

        Returns:
            Dictionary with automation creation result
        """
        automation_yaml = arguments.get("automation_yaml")
        alias = arguments.get("alias")

        if not automation_yaml or not alias:
            raise ValueError("automation_yaml and alias are required")

        # Validate YAML first
        try:
            automation_dict = yaml.safe_load(automation_yaml)
            if not isinstance(automation_dict, dict):
                raise ValueError("Automation YAML must be a dictionary")

            # Ensure required fields
            if "trigger" not in automation_dict:
                raise ValueError("Automation must have a 'trigger' field")
            if "action" not in automation_dict:
                raise ValueError("Automation must have an 'action' field")

            # Set alias if not provided
            if "alias" not in automation_dict:
                automation_dict["alias"] = alias

        except yaml.YAMLError as e:
            return {
                "success": False,
                "error": f"Invalid YAML: {str(e)}",
                "alias": alias
            }
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "alias": alias
            }

        try:
            # Create automation via HA API

            session = await self.ha_client._get_session()
            url = f"{self.ha_client.ha_url}/api/config/automation/config/{alias}"

            # Home Assistant expects automation config in specific format
            # We need to convert YAML to the format HA expects
            automation_config = {
                "alias": alias,
                **automation_dict
            }

            async with session.post(url, json=automation_config) as response:
                if response.status in (200, 201):
                    result = await response.json()
                    return {
                        "success": True,
                        "automation_id": result.get("id", f"automation.{alias.lower().replace(' ', '_')}"),
                        "alias": alias,
                        "message": "Automation created successfully"
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"Failed to create automation: {response.status} - {error_text}",
                        "alias": alias
                    }
        except Exception as e:
            logger.error(f"Error creating automation: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "alias": alias
            }

    async def update_automation(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Update an existing Home Assistant automation.

        Args:
            arguments: Tool arguments containing automation_id and automation_yaml

        Returns:
            Dictionary with update result
        """
        automation_id = arguments.get("automation_id")
        automation_yaml = arguments.get("automation_yaml")

        if not automation_id or not automation_yaml:
            raise ValueError("automation_id and automation_yaml are required")

        # Validate YAML
        try:
            automation_dict = yaml.safe_load(automation_yaml)
            if not isinstance(automation_dict, dict):
                raise ValueError("Automation YAML must be a dictionary")
        except yaml.YAMLError as e:
            return {
                "success": False,
                "error": f"Invalid YAML: {str(e)}",
                "automation_id": automation_id
            }

        try:
            # Update automation via HA API

            session = await self.ha_client._get_session()
            # Extract ID from automation_id (e.g., "automation.morning_lights" -> "morning_lights")
            config_id = automation_id.replace("automation.", "") if automation_id.startswith("automation.") else automation_id
            url = f"{self.ha_client.ha_url}/api/config/automation/config/{config_id}"

            async with session.put(url, json=automation_dict) as response:
                if response.status == 200:
                    return {
                        "success": True,
                        "automation_id": automation_id,
                        "message": "Automation updated successfully"
                    }
                elif response.status == 404:
                    return {
                        "success": False,
                        "error": f"Automation not found: {automation_id}",
                        "automation_id": automation_id
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"Failed to update automation: {response.status} - {error_text}",
                        "automation_id": automation_id
                    }
        except Exception as e:
            logger.error(f"Error updating automation {automation_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "automation_id": automation_id
            }

    async def delete_automation(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Delete a Home Assistant automation.

        Args:
            arguments: Tool arguments containing automation_id

        Returns:
            Dictionary with deletion result
        """
        automation_id = arguments.get("automation_id")
        if not automation_id:
            raise ValueError("automation_id is required")

        try:
            # Delete automation via HA API

            session = await self.ha_client._get_session()
            # Extract ID from automation_id
            config_id = automation_id.replace("automation.", "") if automation_id.startswith("automation.") else automation_id
            url = f"{self.ha_client.ha_url}/api/config/automation/config/{config_id}"

            async with session.delete(url) as response:
                if response.status == 200:
                    return {
                        "success": True,
                        "automation_id": automation_id,
                        "message": "Automation deleted successfully"
                    }
                elif response.status == 404:
                    return {
                        "success": False,
                        "error": f"Automation not found: {automation_id}",
                        "automation_id": automation_id
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"Failed to delete automation: {response.status} - {error_text}",
                        "automation_id": automation_id
                    }
        except Exception as e:
            logger.error(f"Error deleting automation {automation_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "automation_id": automation_id
            }

    async def get_automations(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        List all Home Assistant automations.

        Args:
            arguments: Tool arguments with optional search_term

        Returns:
            Dictionary with list of automations
        """
        search_term = arguments.get("search_term")

        try:
            # Get automations via HA API

            session = await self.ha_client._get_session()
            url = f"{self.ha_client.ha_url}/api/config/automation/config"

            async with session.get(url) as response:
                if response.status == 200:
                    automations = await response.json()

                    # Handle different response formats
                    if isinstance(automations, dict):
                        # HA may return dict with automations list
                        if "automations" in automations:
                            automations = automations["automations"]
                        elif "data" in automations:
                            automations = automations["data"]

                    if not isinstance(automations, list):
                        automations = []

                    # Filter by search term if provided
                    if search_term:
                        search_lower = search_term.lower()
                        filtered = []
                        for automation in automations:
                            alias = automation.get("alias", "")
                            description = automation.get("description", "")
                            automation_id = automation.get("id", "")

                            if (search_lower in alias.lower() or
                                search_lower in description.lower() or
                                search_lower in str(automation_id).lower()):
                                filtered.append(automation)
                        automations = filtered

                    # Format response
                    formatted_automations = []
                    for automation in automations:
                        formatted_automations.append({
                            "id": automation.get("id"),
                            "alias": automation.get("alias"),
                            "description": automation.get("description"),
                            "enabled": automation.get("enabled", True)
                        })

                    return {
                        "success": True,
                        "count": len(formatted_automations),
                        "automations": formatted_automations
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"Failed to get automations: {response.status} - {error_text}"
                    }
        except Exception as e:
            logger.error(f"Error getting automations: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def test_automation_yaml(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Validate Home Assistant automation YAML syntax.

        Args:
            arguments: Tool arguments containing automation_yaml

        Returns:
            Dictionary with validation result
        """
        automation_yaml = arguments.get("automation_yaml")
        if not automation_yaml:
            raise ValueError("automation_yaml is required")

        errors = []
        warnings = []

        try:
            # Parse YAML
            automation_dict = yaml.safe_load(automation_yaml)

            if not isinstance(automation_dict, dict):
                errors.append("Automation YAML must be a dictionary")
                return {
                    "success": False,
                    "valid": False,
                    "errors": errors,
                    "warnings": warnings
                }

            # Check required fields
            if "trigger" not in automation_dict:
                errors.append("Missing required field: 'trigger'")
            elif not automation_dict["trigger"]:
                errors.append("Field 'trigger' cannot be empty")

            if "action" not in automation_dict:
                errors.append("Missing required field: 'action'")
            elif not automation_dict["action"]:
                errors.append("Field 'action' cannot be empty")

            # Check optional but recommended fields
            if "alias" not in automation_dict:
                warnings.append("Missing recommended field: 'alias' (used for identification)")

            if "description" not in automation_dict:
                warnings.append("Missing recommended field: 'description' (helps with automation management)")

            # Validate trigger structure
            if "trigger" in automation_dict:
                trigger = automation_dict["trigger"]
                if isinstance(trigger, list):
                    if len(trigger) == 0:
                        errors.append("Trigger list cannot be empty")
                elif isinstance(trigger, dict) and "platform" not in trigger:
                    errors.append("Trigger must have a 'platform' field")

            # Validate action structure
            if "action" in automation_dict:
                action = automation_dict["action"]
                if isinstance(action, list) and len(action) == 0:
                    errors.append("Action list cannot be empty")
                elif isinstance(action, dict) and "service" not in action and "scene" not in action:
                    errors.append("Action must have either 'service' or 'scene' field")

            valid = len(errors) == 0

            return {
                "success": True,
                "valid": valid,
                "errors": errors,
                "warnings": warnings
            }

        except yaml.YAMLError as e:
            return {
                "success": True,
                "valid": False,
                "errors": [f"YAML syntax error: {str(e)}"],
                "warnings": warnings
            }
        except Exception as e:
            logger.error(f"Error validating automation YAML: {e}", exc_info=True)
            return {
                "success": False,
                "valid": False,
                "errors": [str(e)],
                "warnings": warnings
            }

