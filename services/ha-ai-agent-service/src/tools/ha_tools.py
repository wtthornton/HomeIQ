"""
Home Assistant Tool Implementations

2025 Preview-and-Approval Workflow:
1. preview_automation_from_prompt - Generate detailed preview (no execution)
2. create_automation_from_prompt - Execute approved automation creation
"""

import logging
import re
from typing import Any, Optional

import yaml

from ..clients.ai_automation_client import AIAutomationClient
from ..clients.data_api_client import DataAPIClient
from ..clients.ha_client import HomeAssistantClient
from ..clients.yaml_validation_client import YAMLValidationClient
from ..models.automation_models import (
    AutomationPreview,
    AutomationPreviewRequest,
    AutomationPreviewResponse,
)
from ..services.business_rules.rule_validator import BusinessRuleValidator
from ..services.entity_resolution.entity_resolution_service import EntityResolutionService
from ..services.enhancement_service import AutomationEnhancementService
from ..services.validation.ai_automation_validation_strategy import (
    AIAutomationValidationStrategy,
)
from ..services.validation.basic_validation_strategy import BasicValidationStrategy
from ..services.validation.validation_chain import ValidationChain
from ..services.validation.yaml_validation_strategy import YAMLValidationStrategy

# Type hint for OpenAI client (optional import)
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = Any  # type: ignore

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
        ai_automation_client: AIAutomationClient | None = None,
        yaml_validation_client: YAMLValidationClient | None = None,
        openai_client: Optional[AsyncOpenAI] = None,
        entity_resolution_service: Optional[EntityResolutionService] = None,
        business_rule_validator: Optional[BusinessRuleValidator] = None,
        validation_chain: Optional[ValidationChain] = None,
    ):
        """
        Initialize tool handler.

        Args:
            ha_client: Home Assistant API client
            data_api_client: Data API client for entity queries
            ai_automation_client: AI Automation Service client (legacy, optional)
            yaml_validation_client: YAML Validation Service client for comprehensive validation (Epic 51, optional)
            openai_client: OpenAI client for enhancement generation (optional)
            entity_resolution_service: Entity resolution service (optional, auto-created if None)
            business_rule_validator: Business rule validator (optional, auto-created if None)
            validation_chain: Validation chain (optional, auto-created if None)
        """
        self.ha_client = ha_client
        self.data_api_client = data_api_client
        self.ai_automation_client = ai_automation_client
        self.yaml_validation_client = yaml_validation_client
        self.openai_client = openai_client
        self._enhancement_service = None

        # Initialize services (create if not provided)
        if entity_resolution_service is None:
            entity_resolution_service = EntityResolutionService(
                data_api_client=data_api_client
            )
        self.entity_resolution_service = entity_resolution_service

        if business_rule_validator is None:
            business_rule_validator = BusinessRuleValidator(
                entity_resolution_service=entity_resolution_service
            )
        self.business_rule_validator = business_rule_validator

        if validation_chain is None:
            # Create validation chain with strategies
            strategies = []
            if yaml_validation_client:
                strategies.append(YAMLValidationStrategy(yaml_validation_client))
            if ai_automation_client:
                strategies.append(AIAutomationValidationStrategy(ai_automation_client))
            # Always add basic validation as fallback
            strategies.append(BasicValidationStrategy(self))
            validation_chain = ValidationChain(strategies)
        self.validation_chain = validation_chain

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
                - conversation_id: Optional conversation ID for traceability

        Returns:
            Dictionary with preview details (no automation created)
        """
        # Extract conversation_id for traceability
        conversation_id = arguments.get("conversation_id")
        
        # Create and validate request
        request = AutomationPreviewRequest.from_dict(arguments)
        validation_error = self._validate_preview_request(request)
        if validation_error:
            return validation_error

        logger.info(
            f"[Preview] Generating preview for automation: '{request.user_prompt[:100]}...' "
            f"with alias: '{request.alias}' "
            f"(conversation_id={conversation_id or 'N/A'})"
        )

        # Validate YAML and process automation
        try:
            validation_result = await self.validation_chain.validate(request.automation_yaml)
            logger.debug(
                f"[Preview] 🔍 Validation chain result: valid={validation_result.valid}, "
                f"errors={len(validation_result.errors or [])}, "
                f"warnings={len(validation_result.warnings or [])}, "
                f"strategy={validation_result.strategy_name if hasattr(validation_result, 'strategy_name') else 'unknown'} "
                f"(conversation_id={conversation_id or 'N/A'})"
            )
            
            automation_dict = self._parse_automation_yaml(request.automation_yaml, request)

            # Extract automation details
            extraction_result = self._extract_automation_details(automation_dict)
            logger.debug(
                f"[Preview] 🔍 Extracted {len(extraction_result['entities'])} entities, "
                f"{len(extraction_result['areas'])} areas, "
                f"{len(extraction_result['services'])} services "
                f"(conversation_id={conversation_id or 'N/A'})"
            )
            safety_warnings = self._check_safety_requirements(
                extraction_result["entities"],
                extraction_result["services"],
                automation_dict,
            )

            # Calculate safety score (recommendation #4)
            safety_score = self.business_rule_validator.calculate_safety_score(
                extraction_result["entities"],
                extraction_result["services"],
                automation_dict,
            )
            logger.debug(
                f"[Preview] 🔍 Safety score calculated: {safety_score:.2f} "
                f"(conversation_id={conversation_id or 'N/A'})"
            )

            # Extract device context (recommendation #5)
            device_context = await self._extract_device_context(automation_dict)
            logger.debug(
                f"[Preview] 🔍 Device context: {len(device_context.get('device_ids', []))} devices, "
                f"{len(device_context.get('device_types', []))} types, "
                f"{len(device_context.get('area_ids', []))} areas "
                f"(conversation_id={conversation_id or 'N/A'})"
            )

            # Validate devices (recommendation #3)
            device_errors = await self._validate_devices(automation_dict)
            if device_errors:
                # Add device errors to validation result
                if validation_result.errors:
                    validation_result.errors.extend(device_errors)
                else:
                    validation_result.errors = device_errors
                validation_result.valid = False

            # Validate consistency (recommendation #6)
            consistency_warnings = self._validate_consistency(automation_dict, device_context)
            if consistency_warnings:
                safety_warnings.extend(consistency_warnings)

            # Build and return preview response
            return self._build_preview_response(
                request=request,
                automation_dict=automation_dict,
                validation_result=validation_result,
                extraction_result=extraction_result,
                safety_warnings=safety_warnings,
                conversation_id=conversation_id,
            )
            
        except (yaml.YAMLError, ValueError) as e:
            return self._handle_yaml_error(e, request, conversation_id)
        except Exception as e:
            return self._handle_unexpected_error(e, request, "preview", conversation_id)

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
                - conversation_id: Optional conversation ID for traceability

        Returns:
            Dictionary with automation creation result
        """
        # Extract conversation_id for traceability
        conversation_id = arguments.get("conversation_id")
        
        # Validate required arguments
        validation_error = self._validate_create_arguments(arguments)
        if validation_error:
            return validation_error

        user_prompt = arguments["user_prompt"]
        automation_yaml = arguments["automation_yaml"]
        alias = arguments["alias"]

        logger.info(
            f"[Create] Creating automation from prompt: '{user_prompt[:100]}...' "
            f"with alias: '{alias}' "
            f"(conversation_id={conversation_id or 'N/A'})"
        )

        # Validate YAML
        validation_result = await self.validation_chain.validate(automation_yaml)
        if not validation_result.valid:
            return self._build_validation_error_response(
                validation_result, user_prompt, alias
            )

        # Create automation in Home Assistant
        try:
            automation_dict = yaml.safe_load(automation_yaml)
            if not isinstance(automation_dict, dict):
                return self._build_error_response(
                    "Automation YAML must be a dictionary", user_prompt, alias
                )

            # Validate required fields
            field_error = self._validate_required_fields(automation_dict, user_prompt, alias)
            if field_error:
                return field_error

            # Prepare and create automation
            automation_dict = self._prepare_automation_dict(automation_dict, alias)
            return await self._create_automation_in_ha(
                automation_dict, alias, user_prompt, validation_result, conversation_id
            )

        except yaml.YAMLError as e:
            logger.error(
                f"[Create] ❌ YAML parsing error for automation '{alias}' "
                f"(conversation_id={conversation_id or 'N/A'}): {e}. "
                f"Prompt: '{user_prompt[:100]}...'",
                exc_info=True
            )
            return self._build_error_response(
                f"YAML parsing error: {str(e)}", user_prompt, alias
            )
        except Exception as e:
            logger.error(
                f"[Create] ❌ Error creating automation '{alias}' "
                f"(conversation_id={conversation_id or 'N/A'}): {e}. "
                f"Prompt: '{user_prompt[:100]}...'",
                exc_info=True
            )
            return self._build_error_response(
                f"Unexpected error: {str(e)}", user_prompt, alias
            )


    def _is_group_entity(self, entity_id: str) -> bool:
        """Check if entity ID is a group entity."""
        return isinstance(entity_id, str) and entity_id.startswith("group.")

    def _validate_preview_request(
        self, request: AutomationPreviewRequest
    ) -> dict[str, Any] | None:
        """
        Validate preview request parameters.

        Args:
            request: Automation preview request to validate

        Returns:
            Error response dictionary if validation fails, None if valid
        """
        is_valid, error_message = request.validate()
        if not is_valid:
            return AutomationPreviewResponse.error_response(
                error=error_message or "Invalid request parameters",
                user_prompt=request.user_prompt,
                alias=request.alias,
            ).to_dict()
        return None

    def _parse_automation_yaml(
        self, automation_yaml: str, request: AutomationPreviewRequest
    ) -> dict[str, Any]:
        """
        Parse automation YAML and validate structure.

        Args:
            automation_yaml: YAML string to parse
            request: Request object for error responses

        Returns:
            Parsed automation dictionary

        Raises:
            ValueError: If YAML is not a valid dictionary
        """
        automation_dict = yaml.safe_load(automation_yaml)
        if not isinstance(automation_dict, dict):
            raise ValueError("Automation YAML must be a dictionary")
        return automation_dict

    def _extract_automation_details(
        self, automation_dict: dict[str, Any]
    ) -> dict[str, list[str]]:
        """
        Extract entities, areas, and services from automation YAML.

        Args:
            automation_dict: Parsed automation dictionary

        Returns:
            Dictionary with 'entities', 'areas', and 'services' lists
        """
        return {
            "entities": self._extract_entities_from_yaml(automation_dict),
            "areas": self._extract_areas_from_yaml(automation_dict),
            "services": self._extract_services_from_yaml(automation_dict),
        }

    def _check_safety_requirements(
        self,
        entities: list[str],
        services: list[str],
        automation_dict: dict[str, Any],
    ) -> list[str]:
        """
        Check safety requirements for automation.

        Args:
            entities: List of entity IDs
            services: List of service names
            automation_dict: Parsed automation dictionary

        Returns:
            List of safety warnings
        """
        _, safety_warnings = self.business_rule_validator.check_safety_requirements(
            entities=entities,
            services=services,
            automation_dict=automation_dict,
        )
        return safety_warnings

    def _build_preview_response(
        self,
        request: AutomationPreviewRequest,
        automation_dict: dict[str, Any],
        validation_result: Any,
        extraction_result: dict[str, list[str]],
        safety_warnings: list[str],
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Build preview response DTO.

        Args:
            request: Original preview request
            automation_dict: Parsed automation dictionary
            validation_result: YAML validation result
            extraction_result: Extracted entities, areas, and services
            safety_warnings: List of safety warnings

        Returns:
            Preview response dictionary
        """
        preview = AutomationPreview(
            alias=request.alias,
            trigger_description=self._describe_trigger(automation_dict.get("trigger")),
            action_description=self._describe_action(automation_dict.get("action")),
            mode=automation_dict.get("mode", "single"),
            initial_state=automation_dict.get("initial_state", None),
        )

        # Use normalized YAML if available (recommendation #10 from HA_AGENT_API_FLOW_ANALYSIS.md)
        # Prefer fixed_yaml (normalized) over original YAML for consistent formatting
        yaml_to_use = request.automation_yaml
        if validation_result and hasattr(validation_result, 'fixed_yaml') and validation_result.fixed_yaml:
            yaml_to_use = validation_result.fixed_yaml
            logger.debug(
                f"[Preview] 🔍 Using normalized YAML from validation result "
                f"(conversation_id={conversation_id or 'N/A'})"
            )

        # Build response with safety score (recommendation #4)
        response = AutomationPreviewResponse(
            success=True,
            preview=preview,
            validation=validation_result,
            entities_affected=extraction_result["entities"],
            areas_affected=extraction_result["areas"],
            services_used=extraction_result["services"],
            safety_warnings=safety_warnings,
            user_prompt=request.user_prompt,
            automation_yaml=yaml_to_use,  # Use normalized YAML if available
            alias=request.alias,
            message="Preview generated successfully. Review the details above and approve to create the automation.",
        )
        
        # Add safety score to response metadata if available (enhanced validation)
        # Note: This may require updating AutomationPreviewResponse model to include safety_score

        logger.info(
            f"[Preview] ✅ Preview generated for automation '{request.alias}' "
            f"(conversation_id={conversation_id or 'N/A'}). "
            f"Entities: {len(extraction_result['entities'])}, "
            f"Areas: {len(extraction_result['areas'])}, "
            f"Safety warnings: {len(safety_warnings)}"
        )

        return response.to_dict()

    def _handle_yaml_error(
        self, error: Exception, request: AutomationPreviewRequest, conversation_id: str | None = None
    ) -> dict[str, Any]:
        """
        Handle YAML parsing errors.

        Args:
            error: YAML parsing exception
            request: Original preview request
            conversation_id: Optional conversation ID for traceability

        Returns:
            Error response dictionary
        """
        logger.error(
            f"[Preview] ❌ YAML parsing error for automation '{request.alias}' "
            f"(conversation_id={conversation_id or 'N/A'}): {error}. "
            f"Prompt: '{request.user_prompt[:100]}...'",
            exc_info=True
        )
        return AutomationPreviewResponse.error_response(
            error=f"YAML parsing error: {str(error)}",
            user_prompt=request.user_prompt,
            alias=request.alias,
        ).to_dict()

    def _handle_unexpected_error(
        self, error: Exception, request: AutomationPreviewRequest, operation: str, conversation_id: str | None = None
    ) -> dict[str, Any]:
        """
        Handle unexpected errors during automation operations.

        Args:
            error: Unexpected exception
            request: Original request (preview or create)
            operation: Operation name ('preview' or 'create')
            conversation_id: Optional conversation ID for traceability

        Returns:
            Error response dictionary
        """
        logger.error(
            f"[{operation.capitalize()}] ❌ Unexpected error for automation '{request.alias}' "
            f"(conversation_id={conversation_id or 'N/A'}): {error}. "
            f"Prompt: '{request.user_prompt[:100]}...'",
            exc_info=True
        )
        return AutomationPreviewResponse.error_response(
            error=f"Unexpected error: {str(error)}",
            user_prompt=request.user_prompt,
            alias=request.alias,
        ).to_dict()

    def _validate_create_arguments(self, arguments: dict[str, Any]) -> dict[str, Any] | None:
        """
        Validate required arguments for create_automation_from_prompt.

        Args:
            arguments: Tool arguments dictionary

        Returns:
            Error response dictionary if validation fails, None if valid
        """
        user_prompt = arguments.get("user_prompt")
        automation_yaml = arguments.get("automation_yaml")
        alias = arguments.get("alias")

        if not user_prompt or not automation_yaml or not alias:
            return {
                "success": False,
                "error": "user_prompt, automation_yaml, and alias are all required",
                "user_prompt": user_prompt,
                "alias": alias,
            }
        return None

    def _build_validation_error_response(
        self,
        validation_result: Any,
        user_prompt: str,
        alias: str,
    ) -> dict[str, Any]:
        """
        Build error response for YAML validation failures.

        Args:
            validation_result: Validation result with errors
            user_prompt: Original user prompt
            alias: Automation alias

        Returns:
            Error response dictionary
        """
        return {
            "success": False,
            "error": "YAML validation failed",
            "validation_errors": validation_result.errors,
            "validation_warnings": validation_result.warnings,
            "user_prompt": user_prompt,
            "alias": alias,
        }

    def _build_error_response(
        self, error_message: str, user_prompt: str, alias: str
    ) -> dict[str, Any]:
        """
        Build generic error response.

        Args:
            error_message: Error message
            user_prompt: Original user prompt
            alias: Automation alias

        Returns:
            Error response dictionary
        """
        return {
            "success": False,
            "error": error_message,
            "user_prompt": user_prompt,
            "alias": alias,
        }

    def _validate_required_fields(
        self, automation_dict: dict[str, Any], user_prompt: str, alias: str
    ) -> dict[str, Any] | None:
        """
        Validate that automation has required fields.

        Args:
            automation_dict: Parsed automation dictionary
            user_prompt: Original user prompt
            alias: Automation alias

        Returns:
            Error response dictionary if validation fails, None if valid
        """
        if "trigger" not in automation_dict:
            return self._build_error_response(
                "Automation must have a 'trigger' field", user_prompt, alias
            )
        if "action" not in automation_dict:
            return self._build_error_response(
                "Automation must have an 'action' field", user_prompt, alias
            )
        return None

    def _prepare_automation_dict(
        self, automation_dict: dict[str, Any], alias: str
    ) -> dict[str, Any]:
        """
        Prepare automation dictionary for Home Assistant API.

        Args:
            automation_dict: Parsed automation dictionary
            alias: Automation alias

        Returns:
            Prepared automation dictionary with alias set
        """
        if "alias" not in automation_dict:
            automation_dict["alias"] = alias
        return automation_dict

    def _extract_scene_create_actions(
        self, automation_dict: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Extract scene.create actions from automation YAML.
        
        Returns list of scene definitions with:
        - scene_id: Scene ID (without 'scene.' prefix)
        - snapshot_entities: List of entity IDs to snapshot
        - scene_entity_id: Full scene entity ID (scene.{scene_id})
        
        Args:
            automation_dict: Parsed automation dictionary
            
        Returns:
            List of scene definitions
        """
        scenes = []
        
        def extract_from_actions(actions: Any) -> None:
            """Recursively extract scene.create actions from action list."""
            if isinstance(actions, list):
                for action in actions:
                    if isinstance(action, dict):
                        # Check for scene.create action
                        # Automation format uses "action" field (not "service")
                        action_type = action.get("action") or action.get("service")
                        if action_type == "scene.create":
                            # Get scene_id and snapshot_entities from data field
                            data = action.get("data", {})
                            scene_id = data.get("scene_id")
                            snapshot_entities = data.get("snapshot_entities", [])
                            
                            if scene_id:
                                scenes.append({
                                    "scene_id": scene_id,
                                    "snapshot_entities": snapshot_entities if isinstance(snapshot_entities, list) else [],
                                    "scene_entity_id": f"scene.{scene_id}",
                                })
                        
                        # Check for nested actions (choose, repeat, etc.)
                        if "sequence" in action:
                            extract_from_actions(action["sequence"])
                        if "choose" in action:
                            for choice in action["choose"]:
                                if isinstance(choice, dict) and "sequence" in choice:
                                    extract_from_actions(choice["sequence"])
                        if "repeat" in action:
                            repeat = action["repeat"]
                            if isinstance(repeat, dict) and "sequence" in repeat:
                                extract_from_actions(repeat["sequence"])
        
        # Extract from action section
        if "action" in automation_dict:
            extract_from_actions(automation_dict["action"])
        
        return scenes

    async def _pre_create_scenes(
        self,
        scenes: list[dict[str, Any]],
        conversation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Pre-create scenes in Home Assistant before automation deployment.
        
        This prevents "Unknown entity" warnings in Home Assistant UI
        by creating scenes that will be referenced by scene.turn_on actions.
        
        Args:
            scenes: List of scene definitions from _extract_scene_create_actions
            conversation_id: Optional conversation ID for traceability
            
        Returns:
            List of creation results with scene_id and success status
        """
        if not scenes:
            return []
        
        session = await self.ha_client._get_session()
        results = []
        
        for scene_def in scenes:
            scene_id = scene_def["scene_id"]
            scene_entity_id = scene_def["scene_entity_id"]
            snapshot_entities = scene_def["snapshot_entities"]
            
            try:
                # Create scene using Home Assistant scene.create service
                # POST /api/services/scene/create
                # This creates a scene with a snapshot of current entity states
                # This pre-creates the scene entity so it exists when the automation is deployed
                url = f"{self.ha_client.ha_url}/api/services/scene/create"
                
                # Prepare scene data for service call
                # scene.create service accepts scene_id and snapshot_entities
                # This captures the current state of entities and creates the scene
                scene_data = {
                    "scene_id": scene_id,
                    "snapshot_entities": snapshot_entities,
                }
                
                async with session.post(url, json=scene_data) as response:
                    if response.status in (200, 201):
                        logger.info(
                            f"[Create] ✅ Pre-created scene: {scene_entity_id} "
                            f"with {len(snapshot_entities)} entities "
                            f"(conversation_id={conversation_id or 'N/A'})"
                        )
                        results.append({
                            "scene_id": scene_id,
                            "scene_entity_id": scene_entity_id,
                            "success": True,
                            "message": "Scene pre-created successfully",
                        })
                    elif response.status == 409:
                        # Scene already exists - this is OK
                        logger.debug(
                            f"[Create] ℹ️  Scene already exists: {scene_entity_id} "
                            f"(conversation_id={conversation_id or 'N/A'})"
                        )
                        results.append({
                            "scene_id": scene_id,
                            "scene_entity_id": scene_entity_id,
                            "success": True,
                            "message": "Scene already exists",
                            "already_exists": True,
                        })
                    else:
                        error_text = await response.text()
                        logger.warning(
                            f"[Create] ⚠️  Failed to pre-create scene {scene_entity_id}: "
                            f"{response.status} - {error_text} "
                            f"(conversation_id={conversation_id or 'N/A'}). "
                            f"Scene will be created dynamically at runtime."
                        )
                        results.append({
                            "scene_id": scene_id,
                            "scene_entity_id": scene_entity_id,
                            "success": False,
                            "error": f"Failed to pre-create: {response.status} - {error_text}",
                        })
            except Exception as e:
                logger.warning(
                    f"[Create] ⚠️  Error pre-creating scene {scene_entity_id}: {e} "
                    f"(conversation_id={conversation_id or 'N/A'}). "
                    f"Scene will be created dynamically at runtime."
                )
                results.append({
                    "scene_id": scene_id,
                    "scene_entity_id": scene_entity_id,
                    "success": False,
                    "error": str(e),
                })
        
        return results

    async def _create_automation_in_ha(
        self,
        automation_dict: dict[str, Any],
        alias: str,
        user_prompt: str,
        validation_result: Any,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create automation in Home Assistant via API.

        Args:
            automation_dict: Prepared automation dictionary
            alias: Automation alias
            user_prompt: Original user prompt
            validation_result: YAML validation result
            conversation_id: Optional conversation ID for traceability

        Returns:
            Success or error response dictionary
        """
        # Extract scenes that will be created dynamically
        scenes_to_precreate = self._extract_scene_create_actions(automation_dict)
        
        # Pre-create scenes before deploying automation
        # This prevents "Unknown entity" warnings in Home Assistant UI
        scene_results = []
        if scenes_to_precreate:
            logger.info(
                f"[Create] Pre-creating {len(scenes_to_precreate)} scenes before automation deployment "
                f"(conversation_id={conversation_id or 'N/A'})"
            )
            scene_results = await self._pre_create_scenes(
                scenes_to_precreate, conversation_id
            )
            logger.info(
                f"[Create] Pre-created {sum(1 for r in scene_results if r['success'])}/{len(scene_results)} scenes"
            )
        
        session = await self.ha_client._get_session()

        # Generate a safe config ID from alias
        config_id = re.sub(r"[^a-z0-9_]", "_", alias.lower().replace(" ", "_"))
        url = f"{self.ha_client.ha_url}/api/config/automation/config/{config_id}"

        # Home Assistant expects automation config in specific format
        automation_config = {"alias": alias, **automation_dict}

        async with session.post(url, json=automation_config) as response:
            if response.status in (200, 201):
                result = await response.json()
                automation_id = result.get("id", f"automation.{config_id}")

                logger.info(
                    f"[Create] ✅ Automation created successfully: {automation_id} "
                    f"for prompt: '{user_prompt[:100]}...' "
                    f"(conversation_id={conversation_id or 'N/A'}, "
                    f"validation_warnings: {len(validation_result.warnings or [])}, "
                    f"scenes_precreated: {sum(1 for r in scene_results if r['success'])})"
                )

                return {
                    "success": True,
                    "automation_id": automation_id,
                    "alias": alias,
                    "user_prompt": user_prompt,
                    "message": "Automation created successfully",
                    "validation_warnings": validation_result.warnings,
                    "scenes_precreated": [
                        {
                            "scene_entity_id": r["scene_entity_id"],
                            "success": r["success"],
                            "message": r.get("message", ""),
                        }
                        for r in scene_results
                    ],
                }
            else:
                error_text = await response.text()
                logger.error(
                    f"[Create] ❌ Failed to create automation '{alias}': {response.status} - {error_text} "
                    f"(conversation_id={conversation_id or 'N/A'}). "
                    f"Prompt: '{user_prompt[:100]}...'",
                    exc_info=False
                )
                return {
                    "success": False,
                    "error": f"Failed to create automation: {response.status} - {error_text}",
                    "user_prompt": user_prompt,
                    "alias": alias,
                    "http_status": response.status,
                    "scenes_precreated": scene_results,  # Return scene results even if automation creation failed
                }
    
    def _extract_from_yaml(
        self,
        automation_dict: dict[str, Any],
        field_path: list[str],
        sections: list[str] = None,
    ) -> list[str]:
        """
        Generic helper to extract values from automation YAML by field path.

        Args:
            automation_dict: Automation YAML as dictionary
            field_path: List of field names to navigate (e.g., ["target", "area_id"] or ["entity_id"])
            sections: List of sections to search (default: ["trigger", "condition", "action"])

        Returns:
            List of extracted string values (deduplicated)
        """
        if sections is None:
            sections = ["trigger", "condition", "action"]

        results = []

        def extract_from_section(section: Any, path_index: int) -> None:
            """Recursively extract values from section."""
            if path_index >= len(field_path):
                return

            field_name = field_path[path_index]
            is_last_field = path_index == len(field_path) - 1

            if isinstance(section, list):
                for item in section:
                    extract_from_section(item, path_index)
            elif isinstance(section, dict):
                if field_name in section:
                    value = section[field_name]
                    if is_last_field:
                        # Extract value
                        if isinstance(value, list):
                            for v in value:
                                if isinstance(v, str):
                                    results.append(v)
                        elif isinstance(value, str):
                            results.append(value)
                    else:
                        # Continue navigation
                        extract_from_section(value, path_index + 1)

        # Extract from specified sections
        for section_name in sections:
            if section_name in automation_dict:
                extract_from_section(automation_dict[section_name], 0)

        return list(set(results))  # Remove duplicates

    def _extract_entities_from_yaml(self, automation_dict: dict[str, Any]) -> list[str]:
        """Extract entity IDs from automation YAML"""
        entities = []
        
        # Extract from entity_id fields (triggers, conditions, actions)
        entities.extend(self._extract_from_yaml(automation_dict, ["entity_id"]))

        # Extract from target.entity_id in actions
        entities.extend(
            self._extract_from_yaml(
                automation_dict, ["target", "entity_id"], sections=["action"]
            )
        )
        
        return list(set(entities))  # Remove duplicates

    def _extract_areas_from_yaml(self, automation_dict: dict[str, Any]) -> list[str]:
        """Extract area IDs from automation YAML"""
        # Extract from target.area_id in actions
        return self._extract_from_yaml(
            automation_dict, ["target", "area_id"], sections=["action"]
        )

    def _extract_services_from_yaml(self, automation_dict: dict[str, Any]) -> list[str]:
        """Extract service names from automation YAML"""
        # Extract from service field in actions
        return self._extract_from_yaml(automation_dict, ["service"], sections=["action"])

    async def _extract_device_context(
        self, automation_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Extract device context from automation (recommendation #5 from HA_AGENT_API_FLOW_ANALYSIS.md).

        Extracts device_ids, device_types, area_ids from entities in the automation.

        Args:
            automation_dict: Parsed automation dictionary

        Returns:
            Dictionary with device_ids, device_types, area_ids, and entity_ids lists
        """
        entity_ids = self._extract_entities_from_yaml(automation_dict)

        if not entity_ids or not self.data_api_client:
            return {
                "device_ids": [],
                "device_types": [],
                "area_ids": [],
                "entity_ids": entity_ids
            }

        try:
            entities = await self.data_api_client.fetch_entities()
            entity_map = {e.get("entity_id"): e for e in entities if e.get("entity_id")}

            device_ids = set()
            device_types = set()
            area_ids = set()

            for entity_id in entity_ids:
                entity = entity_map.get(entity_id)
                if entity:
                    if entity.get("device_id"):
                        device_ids.add(entity.get("device_id"))
                    if entity.get("device_type"):
                        device_types.add(entity.get("device_type"))
                    if entity.get("area_id"):
                        area_ids.add(entity.get("area_id"))

            return {
                "device_ids": list(device_ids),
                "device_types": list(device_types),
                "area_ids": list(area_ids),
                "entity_ids": entity_ids
            }
        except Exception as e:
            logger.warning(
                f"[Preview] ⚠️ Failed to extract device context: {e}. "
                f"Impact: Device validation will be skipped. Automation may proceed with limited validation. "
                f"Consider: Manual device verification before deployment."
            )
            return {
                "device_ids": [],
                "device_types": [],
                "area_ids": [],
                "entity_ids": entity_ids
            }

    async def _validate_devices(self, automation_dict: dict[str, Any]) -> list[str]:
        """
        Validate device IDs and capabilities (recommendation #3 from HA_AGENT_API_FLOW_ANALYSIS.md).

        Args:
            automation_dict: Parsed automation dictionary

        Returns:
            List of error messages for invalid devices or capabilities
        """
        errors = []

        if not self.data_api_client:
            return errors

        try:
            # Extract device context to get device IDs
            device_context = await self._extract_device_context(automation_dict)
            device_ids = device_context.get("device_ids", [])

            if not device_ids:
                # No devices to validate
                return errors

            # Fetch all devices from Data API
            all_devices = await self.data_api_client.get_devices()
            valid_device_ids = {d.get("device_id") for d in all_devices if d.get("device_id")}
            device_map = {d.get("device_id"): d for d in all_devices if d.get("device_id")}

            # Validate device IDs exist
            invalid_devices = [did for did in device_ids if did not in valid_device_ids]
            if invalid_devices:
                errors.append(f"Invalid device IDs: {', '.join(invalid_devices)}")

            # Check device health scores (recommendation #3 - prioritize devices with health_score > 70)
            low_health_devices = []
            for device_id in device_ids:
                device = device_map.get(device_id)
                if device:
                    health_score = device.get("health_score")
                    if health_score is not None and health_score < 70:
                        low_health_devices.append(f"{device_id} (health_score: {health_score})")

            if low_health_devices:
                errors.append(
                    f"Devices with low health scores (< 70): {', '.join(low_health_devices)}. "
                    "Consider using devices with health_score > 70 for better reliability."
                )

        except Exception as e:
            logger.warning(
                f"[Preview] ⚠️ Failed to validate devices: {e}. "
                f"Impact: Device health scores and capability checks will be skipped. "
                f"Consider: Manual verification before deployment."
            )
            errors.append(f"Could not validate devices: {str(e)}")

        return errors

    def _validate_consistency(
        self,
        automation_dict: dict[str, Any],
        device_context: dict[str, Any]
    ) -> list[str]:
        """
        Validate consistency between automation and metadata (recommendation #6 from HA_AGENT_API_FLOW_ANALYSIS.md).

        Args:
            automation_dict: Parsed automation dictionary
            device_context: Device context dictionary from _extract_device_context

        Returns:
            List of warning messages for inconsistencies
        """
        warnings = []

        # Check device context matches entities
        automation_entities = set(self._extract_entities_from_yaml(automation_dict))
        context_entities = set(device_context.get("entity_ids", []))

        if automation_entities != context_entities:
            warnings.append(
                f"Entity mismatch: automation has {len(automation_entities)} entities, "
                f"device context has {len(context_entities)} entities"
            )

        return warnings

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

    
    @property
    def enhancement_service(self) -> AutomationEnhancementService | None:
        """Get or create enhancement service"""
        if self._enhancement_service is None and self.openai_client:
            from ..config import Settings
            settings = Settings()
            self._enhancement_service = AutomationEnhancementService(
                openai_client=self.openai_client,
                settings=settings
            )
        return self._enhancement_service
    
    async def suggest_automation_enhancements(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Generate 5 enhancement suggestions for an automation.
        
        Supports two modes:
        - Prompt Enhancement Mode: Enhance user prompts before YAML generation (no YAML required)
        - YAML Enhancement Mode: Enhance existing automation YAML (YAML required)
        
        Uses:
        - LLM for small/medium/large
        - Patterns API for advanced
        - Synergies API for fun/crazy
        
        Args:
            arguments: Tool arguments containing:
                - automation_yaml: The automation YAML to enhance (optional)
                - original_prompt: User's original request (required)
                - conversation_id: Conversation ID for tracking
                - creativity_level: Creativity level - "conservative", "balanced", or "creative" (optional, default: "balanced")
                
        Returns:
            Dictionary with 5 enhancement suggestions and mode indicator
        """
        automation_yaml = arguments.get("automation_yaml")  # Optional
        original_prompt = arguments.get("original_prompt")  # Required
        conversation_id = arguments.get("conversation_id")
        creativity_level = arguments.get("creativity_level", "balanced")  # Optional, default to balanced
        
        if not original_prompt:
            return {
                "success": False,
                "error": "original_prompt is required",
                "conversation_id": conversation_id
            }
        
        if not self.enhancement_service:
            return {
                "success": False,
                "error": "Enhancement service not available (OpenAI client not initialized)",
                "conversation_id": conversation_id
            }
        
        try:
            logger.info(
                f"[Enhancement] Generating enhancements (mode: {'yaml' if automation_yaml else 'prompt'}) "
                f"for conversation {conversation_id or 'N/A'}"
            )
            
            if automation_yaml:
                # YAML Enhancement Mode (existing behavior)
                entities = AutomationEnhancementService.extract_entities_from_yaml(automation_yaml)
                areas = AutomationEnhancementService.extract_areas_from_yaml(automation_yaml)
                
                enhancements = await self.enhancement_service.generate_enhancements(
                    automation_yaml=automation_yaml,
                    original_prompt=original_prompt,
                    entities=entities,
                    areas=areas
                )
                mode = "yaml"
            else:
                # Prompt Enhancement Mode (new behavior)
                # Try to extract entities/areas from prompt for pattern/synergy lookup
                entities = None
                areas = None
                # For now, we'll skip entity extraction from prompt text (could be enhanced later)
                
                enhancements = await self.enhancement_service.generate_prompt_enhancements(
                    original_prompt=original_prompt,
                    creativity_level=creativity_level,
                    entities=entities,
                    areas=areas
                )
                mode = "prompt"
            
            return {
                "success": True,
                "enhancements": [e.to_dict() for e in enhancements],
                "conversation_id": conversation_id,
                "mode": mode  # Indicate which mode was used
            }
            
        except Exception as e:
            logger.error(
                f"[Enhancement] ❌ Error generating enhancements "
                f"(conversation_id={conversation_id or 'N/A'}): {e}",
                exc_info=True
            )
            return {
                "success": False,
                "error": f"Failed to generate enhancements: {str(e)}",
                "conversation_id": conversation_id
            }
