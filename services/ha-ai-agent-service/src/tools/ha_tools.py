"""
Home Assistant Tool Implementations

2025 Preview-and-Approval Workflow:
1. preview_automation_from_prompt - Generate detailed preview (no execution)
2. create_automation_from_prompt - Execute approved automation creation
"""

import logging
import re
from typing import Any

import yaml

from ..clients.ai_automation_client import AIAutomationClient
from ..clients.data_api_client import DataAPIClient
from ..clients.ha_client import HomeAssistantClient

logger = logging.getLogger(__name__)


class HAToolHandler:
    """
    Handler for Home Assistant tool execution.

    2025 Preview-and-Approval Workflow:
    - preview_automation_from_prompt: Generate detailed preview
    - create_automation_from_prompt: Execute automation creation
    """

    def __init__(
        self,
        ha_client: HomeAssistantClient,
        data_api_client: DataAPIClient,
        ai_automation_client: AIAutomationClient | None = None
    ):
        """
        Initialize tool handler.

        Args:
            ha_client: Home Assistant API client
            data_api_client: Data API client for entity queries
            ai_automation_client: AI Automation Service client for YAML validation (optional)
        """
        self.ha_client = ha_client
        self.data_api_client = data_api_client
        self.ai_automation_client = ai_automation_client

    async def preview_automation_from_prompt(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Generate a detailed preview of a Home Assistant automation.

        This tool ONLY generates a preview - it does NOT create the automation.
        The preview includes automation details, YAML validation, entities affected,
        and safety considerations.

        Args:
            arguments: Tool arguments containing:
                - user_prompt: The user's natural language request
                - automation_yaml: The complete automation YAML
                - alias: Automation alias/name

        Returns:
            Dictionary with preview details (no automation created)
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
            f"Generating preview for automation: '{user_prompt[:100]}...' "
            f"with alias: '{alias}'"
        )

        # Step 1: Validate YAML syntax
        validation_result = await self._validate_yaml(automation_yaml)
        
        # Step 2: Extract automation details for preview
        try:
            automation_dict = yaml.safe_load(automation_yaml)
            if not isinstance(automation_dict, dict):
                return {
                    "success": False,
                    "error": "Automation YAML must be a dictionary",
                    "user_prompt": user_prompt,
                    "alias": alias
                }

            # Extract entities, areas, and services from YAML for preview
            entities_affected = self._extract_entities_from_yaml(automation_dict)
            areas_affected = self._extract_areas_from_yaml(automation_dict)
            services_used = self._extract_services_from_yaml(automation_dict)
            
            # Determine safety considerations
            safety_warnings = self._analyze_safety(automation_dict, entities_affected)
            
            # Build detailed preview
            preview = {
                "success": True,
                "preview": True,  # Flag indicating this is a preview
                "alias": alias,
                "user_prompt": user_prompt,
                "automation_yaml": automation_yaml,
                "validation": {
                    "valid": validation_result["valid"],
                    "errors": validation_result.get("errors", []),
                    "warnings": validation_result.get("warnings", [])
                },
                "details": {
                    "trigger_description": self._describe_trigger(automation_dict.get("trigger")),
                    "action_description": self._describe_action(automation_dict.get("action")),
                    "mode": automation_dict.get("mode", "single"),
                    "initial_state": automation_dict.get("initial_state", None)
                },
                "entities_affected": entities_affected,
                "areas_affected": areas_affected,
                "services_used": services_used,
                "safety_warnings": safety_warnings,
                "message": "Preview generated successfully. Review the details above and approve to create the automation."
            }
            
            logger.info(
                f"✅ Preview generated for automation '{alias}'. "
                f"Entities: {len(entities_affected)}, Areas: {len(areas_affected)}, "
                f"Safety warnings: {len(safety_warnings)}"
            )
            
            return preview
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in preview: {e}")
            return {
                "success": False,
                "error": f"YAML parsing error: {str(e)}",
                "user_prompt": user_prompt,
                "alias": alias
            }
        except Exception as e:
            logger.error(f"Error generating preview: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "user_prompt": user_prompt,
                "alias": alias
            }

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
        Validate Home Assistant automation YAML using consolidated validation endpoint.

        Uses AI Automation Service validation endpoint if available, with fallback to basic validation.

        Args:
            automation_yaml: YAML string to validate

        Returns:
            Dictionary with validation result
        """
        # Use consolidated validation endpoint if available
        if self.ai_automation_client:
            try:
                logger.debug("Using consolidated YAML validation endpoint")
                result = await self.ai_automation_client.validate_yaml(
                    automation_yaml,
                    validate_entities=True,
                    validate_safety=True
                )
                
                # Convert consolidated validation result to expected format
                errors = [err.get("message", "") for err in result.get("errors", [])]
                warnings = [warn.get("message", "") for warn in result.get("warnings", [])]
                
                # Include fixed YAML if available
                response = {
                    "valid": result.get("valid", False),
                    "errors": errors,
                    "warnings": warnings
                }
                
                if result.get("fixed_yaml"):
                    response["fixed_yaml"] = result["fixed_yaml"]
                
                if result.get("summary"):
                    response["summary"] = result["summary"]
                
                return response
                
            except Exception as e:
                logger.warning(f"Consolidated validation failed, falling back to basic validation: {e}")
                # Fall through to basic validation
        
        # Fallback to basic validation
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

    def _extract_entities_from_yaml(self, automation_dict: dict) -> list[str]:
        """Extract entity IDs from automation YAML"""
        entities = []
        
        # Extract from triggers
        trigger = automation_dict.get("trigger", [])
        if isinstance(trigger, list):
            for t in trigger:
                if "entity_id" in t:
                    entity_id = t["entity_id"]
                    if isinstance(entity_id, list):
                        entities.extend(entity_id)
                    elif isinstance(entity_id, str):
                        entities.append(entity_id)
        elif isinstance(trigger, dict):
            if "entity_id" in trigger:
                entity_id = trigger["entity_id"]
                if isinstance(entity_id, list):
                    entities.extend(entity_id)
                elif isinstance(entity_id, str):
                    entities.append(entity_id)
        
        # Extract from conditions
        condition = automation_dict.get("condition", [])
        if isinstance(condition, list):
            for c in condition:
                if "entity_id" in c:
                    entity_id = c["entity_id"]
                    if isinstance(entity_id, list):
                        entities.extend(entity_id)
                    elif isinstance(entity_id, str):
                        entities.append(entity_id)
        elif isinstance(condition, dict):
            if "entity_id" in condition:
                entity_id = condition["entity_id"]
                if isinstance(entity_id, list):
                    entities.extend(entity_id)
                elif isinstance(entity_id, str):
                    entities.append(entity_id)
        
        # Extract from actions
        action = automation_dict.get("action", [])
        if isinstance(action, list):
            for a in action:
                if "entity_id" in a:
                    entity_id = a["entity_id"]
                    if isinstance(entity_id, list):
                        entities.extend(entity_id)
                    elif isinstance(entity_id, str):
                        entities.append(entity_id)
                # Check target.entity_id
                if "target" in a and isinstance(a["target"], dict):
                    if "entity_id" in a["target"]:
                        entity_id = a["target"]["entity_id"]
                        if isinstance(entity_id, list):
                            entities.extend(entity_id)
                        elif isinstance(entity_id, str):
                            entities.append(entity_id)
        elif isinstance(action, dict):
            if "entity_id" in action:
                entity_id = action["entity_id"]
                if isinstance(entity_id, list):
                    entities.extend(entity_id)
                elif isinstance(entity_id, str):
                    entities.append(entity_id)
        
        return list(set(entities))  # Remove duplicates

    def _extract_areas_from_yaml(self, automation_dict: dict) -> list[str]:
        """Extract area IDs from automation YAML"""
        areas = []
        
        # Extract from actions (target.area_id)
        action = automation_dict.get("action", [])
        if isinstance(action, list):
            for a in action:
                if "target" in a and isinstance(a["target"], dict):
                    if "area_id" in a["target"]:
                        area_id = a["target"]["area_id"]
                        if isinstance(area_id, list):
                            areas.extend(area_id)
                        elif isinstance(area_id, str):
                            areas.append(area_id)
        elif isinstance(action, dict):
            if "target" in action and isinstance(action["target"], dict):
                if "area_id" in action["target"]:
                    area_id = action["target"]["area_id"]
                    if isinstance(area_id, list):
                        areas.extend(area_id)
                    elif isinstance(area_id, str):
                        areas.append(area_id)
        
        return list(set(areas))  # Remove duplicates

    def _extract_services_from_yaml(self, automation_dict: dict) -> list[str]:
        """Extract service names from automation YAML"""
        services = []
        
        action = automation_dict.get("action", [])
        if isinstance(action, list):
            for a in action:
                if "service" in a:
                    service = a["service"]
                    if isinstance(service, str):
                        services.append(service)
        elif isinstance(action, dict):
            if "service" in action:
                service = action["service"]
                if isinstance(service, str):
                    services.append(service)
        
        return list(set(services))  # Remove duplicates

    def _describe_trigger(self, trigger: Any) -> str:
        """Generate human-readable description of trigger"""
        if not trigger:
            return "No trigger specified"
        
        if isinstance(trigger, list):
            descriptions = []
            for t in trigger:
                platform = t.get("platform", "unknown")
                if platform == "state":
                    entity = t.get("entity_id", "unknown")
                    to_state = t.get("to", "")
                    from_state = t.get("from", "")
                    if from_state:
                        desc = f"State change: {entity} from '{from_state}' to '{to_state}'"
                    else:
                        desc = f"State change: {entity} to '{to_state}'"
                    descriptions.append(desc)
                elif platform == "time":
                    at = t.get("at", "")
                    desc = f"Time trigger at {at}"
                    descriptions.append(desc)
                elif platform == "time_pattern":
                    minutes = t.get("minutes", "")
                    hours = t.get("hours", "")
                    desc = f"Time pattern: minutes={minutes}, hours={hours}"
                    descriptions.append(desc)
                else:
                    descriptions.append(f"{platform} trigger")
            return "; ".join(descriptions)
        elif isinstance(trigger, dict):
            platform = trigger.get("platform", "unknown")
            return f"{platform} trigger"
        
        return "Unknown trigger type"

    def _describe_action(self, action: Any) -> str:
        """Generate human-readable description of action"""
        if not action:
            return "No action specified"
        
        if isinstance(action, list):
            descriptions = []
            for a in action:
                if "service" in a:
                    service = a["service"]
                    target = a.get("target", {})
                    if isinstance(target, dict):
                        if "area_id" in target:
                            area = target["area_id"]
                            descriptions.append(f"{service} on area {area}")
                        elif "entity_id" in target:
                            entity = target["entity_id"]
                            descriptions.append(f"{service} on {entity}")
                        else:
                            descriptions.append(f"{service}")
                    else:
                        descriptions.append(f"{service}")
                elif "scene" in a:
                    scene = a.get("scene", "")
                    descriptions.append(f"Activate scene {scene}")
                elif "delay" in a:
                    delay = a.get("delay", "")
                    descriptions.append(f"Wait {delay}")
                else:
                    descriptions.append("Unknown action")
            return "; ".join(descriptions)
        elif isinstance(action, dict):
            if "service" in action:
                service = action["service"]
                return f"{service}"
            elif "scene" in action:
                scene = action.get("scene", "")
                return f"Activate scene {scene}"
        
        return "Unknown action type"

    def _analyze_safety(self, automation_dict: dict, entities: list[str]) -> list[str]:
        """Analyze automation for safety considerations"""
        warnings = []
        
        # Check for security-related entities
        security_domains = ["lock", "alarm", "camera", "person", "device_tracker"]
        security_entities = [e for e in entities if any(e.startswith(f"{domain}.") for domain in security_domains)]
        if security_entities:
            warnings.append(f"Security-sensitive entities detected: {', '.join(security_entities)}. Ensure time-based constraints are appropriate.")
        
        # Check for critical services
        action = automation_dict.get("action", [])
        critical_services = ["lock.lock", "lock.unlock", "alarm_control_panel.alarm_arm"]
        if isinstance(action, list):
            for a in action:
                service = a.get("service", "")
                if any(service.startswith(cs) for cs in critical_services):
                    warnings.append(f"Critical service used: {service}. Verify automation logic carefully.")
        elif isinstance(action, dict):
            service = action.get("service", "")
            if any(service.startswith(cs) for cs in critical_services):
                warnings.append(f"Critical service used: {service}. Verify automation logic carefully.")
        
        # Check for time-based triggers without conditions
        trigger = automation_dict.get("trigger", [])
        has_time_trigger = False
        if isinstance(trigger, list):
            has_time_trigger = any(t.get("platform") in ["time", "time_pattern"] for t in trigger)
        elif isinstance(trigger, dict):
            has_time_trigger = trigger.get("platform") in ["time", "time_pattern"]
        
        if has_time_trigger and security_entities and not automation_dict.get("condition"):
            warnings.append("Time-based trigger with security entities detected. Consider adding conditions for safety.")
        
        return warnings
