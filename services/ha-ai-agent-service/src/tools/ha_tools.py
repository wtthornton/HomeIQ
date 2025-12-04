"""
Home Assistant Tool Implementations

Simplified to a single tool: create_automation_from_prompt
This tool handles the complete automation creation workflow:
1. Validates YAML syntax
2. Creates the automation in Home Assistant
3. Returns success/error status
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

    Implements the single unified tool: create_automation_from_prompt
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

    async def create_automation_from_prompt(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Create a Home Assistant automation from a user prompt.

        This is the ONLY tool available. It handles:
        - YAML validation
        - Automation creation in Home Assistant
        - Error handling and reporting

        Args:
            arguments: Tool arguments containing:
                - user_prompt: The user's natural language request
                - automation_yaml: The complete automation YAML
                - alias: Automation alias/name

        Returns:
            Dictionary with automation creation result
        """
        user_prompt = arguments.get("user_prompt")
        automation_yaml = arguments.get("automation_yaml")
        alias = arguments.get("alias")

        if not user_prompt or not automation_yaml or not alias:
            return {
                "success": False,
                "error": "user_prompt, automation_yaml, and alias are all required",
                "user_prompt": user_prompt,
                "alias": alias
            }

        logger.info(
            f"Creating automation from prompt: '{user_prompt[:100]}...' "
            f"with alias: '{alias}'"
        )

        # Step 1: Validate YAML syntax
        validation_result = await self._validate_yaml(automation_yaml)
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": "YAML validation failed",
                "validation_errors": validation_result.get("errors", []),
                "validation_warnings": validation_result.get("warnings", []),
                "user_prompt": user_prompt,
                "alias": alias
            }

        # Step 2: Create automation in Home Assistant
        try:
            automation_dict = yaml.safe_load(automation_yaml)
            if not isinstance(automation_dict, dict):
                return {
                    "success": False,
                    "error": "Automation YAML must be a dictionary",
                    "user_prompt": user_prompt,
                    "alias": alias
                }

            # Ensure required fields
            if "trigger" not in automation_dict:
                return {
                    "success": False,
                    "error": "Automation must have a 'trigger' field",
                    "user_prompt": user_prompt,
                    "alias": alias
                }
            if "action" not in automation_dict:
                return {
                    "success": False,
                    "error": "Automation must have an 'action' field",
                    "user_prompt": user_prompt,
                    "alias": alias
                }

            # Set alias if not provided in YAML
            if "alias" not in automation_dict:
                automation_dict["alias"] = alias

            # Create automation via HA API
            session = await self.ha_client._get_session()
            
            # Generate a safe config ID from alias
            config_id = re.sub(r'[^a-z0-9_]', '_', alias.lower().replace(' ', '_'))
            url = f"{self.ha_client.ha_url}/api/config/automation/config/{config_id}"

            # Home Assistant expects automation config in specific format
            automation_config = {
                "alias": alias,
                **automation_dict
            }

            async with session.post(url, json=automation_config) as response:
                if response.status in (200, 201):
                    result = await response.json()
                    automation_id = result.get("id", f"automation.{config_id}")
                    
                    logger.info(
                        f"✅ Automation created successfully: {automation_id} "
                        f"for prompt: '{user_prompt[:100]}...'"
                    )
                    
                    return {
                        "success": True,
                        "automation_id": automation_id,
                        "alias": alias,
                        "user_prompt": user_prompt,
                        "message": "Automation created successfully",
                        "validation_warnings": validation_result.get("warnings", [])
                    }
                else:
                    error_text = await response.text()
                    logger.error(
                        f"❌ Failed to create automation: {response.status} - {error_text} "
                        f"for prompt: '{user_prompt[:100]}...'"
                    )
                    return {
                        "success": False,
                        "error": f"Failed to create automation: {response.status} - {error_text}",
                        "user_prompt": user_prompt,
                        "alias": alias,
                        "http_status": response.status
                    }
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            return {
                "success": False,
                "error": f"YAML parsing error: {str(e)}",
                "user_prompt": user_prompt,
                "alias": alias
            }
        except Exception as e:
            logger.error(f"Error creating automation: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "user_prompt": user_prompt,
                "alias": alias
            }

    async def _validate_yaml(self, automation_yaml: str) -> dict[str, Any]:
        """
        Validate Home Assistant automation YAML syntax.

        Args:
            automation_yaml: YAML string to validate

        Returns:
            Dictionary with validation result
        """
        errors = []
        warnings = []

        try:
            # Parse YAML
            automation_dict = yaml.safe_load(automation_yaml)

            if not isinstance(automation_dict, dict):
                errors.append("Automation YAML must be a dictionary")
                return {
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

            if "initial_state" not in automation_dict:
                warnings.append("Missing recommended field: 'initial_state' (should be 'true' for 2025.10+ compliance)")

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
                elif isinstance(action, dict):
                    if "service" not in action and "scene" not in action:
                        errors.append("Action must have either 'service' or 'scene' field")

            valid = len(errors) == 0

            return {
                "valid": valid,
                "errors": errors,
                "warnings": warnings
            }

        except yaml.YAMLError as e:
            return {
                "valid": False,
                "errors": [f"YAML syntax error: {str(e)}"],
                "warnings": warnings
            }
        except Exception as e:
            logger.error(f"Error validating automation YAML: {e}", exc_info=True)
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": warnings
            }
