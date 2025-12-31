"""
Multi-Stage Validation Pipeline

Epic 51, Story 51.2: Implement Multi-Stage Validation Pipeline

6-stage validation:
1. Syntax - YAML parsing
2. Schema - Required keys, structure
3. Referential Integrity - Entities, areas, devices exist
4. Service Schema - Service exists, parameters valid
5. Safety - Critical device checks
6. Style/Maintainability - Best practices
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Validation result with errors, warnings, score, and fixes."""
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    score: float = 100.0  # 0-100 quality score
    fixed_yaml: str | None = None
    fixes_applied: list[str] = field(default_factory=list)
    summary: str | None = None


class ValidationPipeline:
    """
    Multi-stage validation pipeline for Home Assistant automation YAML.
    
    Stages:
    1. Syntax - YAML parsing validation
    2. Schema - Required keys, correct structure
    3. Referential Integrity - Entities, areas, devices exist
    4. Service Schema - Service exists, parameters valid
    5. Safety - Critical device checks
    6. Style/Maintainability - Best practices
    """
    
    def __init__(
        self,
        data_api_client=None,
        ha_client=None,
        validation_level: str = "moderate"  # strict, moderate, permissive
    ):
        """
        Initialize validation pipeline.
        
        Args:
            data_api_client: Data API client for entity/area queries (optional)
            ha_client: Home Assistant client for service validation (optional)
            validation_level: Validation strictness level
        """
        self.data_api_client = data_api_client
        self.ha_client = ha_client
        self.validation_level = validation_level

    async def validate(
        self,
        yaml_content: str,
        normalize: bool = True
    ) -> ValidationResult:
        """
        Validate YAML through multi-stage pipeline.
        
        Args:
            yaml_content: YAML string to validate
            normalize: Whether to normalize YAML before validation
            
        Returns:
            ValidationResult with errors, warnings, score, and fixes
        """
        result = ValidationResult()
        
        # Stage 1: Syntax Validation
        syntax_result = self._validate_syntax(yaml_content)
        if not syntax_result["valid"]:
            result.valid = False
            result.errors.extend(syntax_result["errors"])
            result.score = 0.0
            return result
        
        # Normalize if requested
        normalized_yaml = yaml_content
        if normalize:
            from .normalizer import YAMLNormalizer
            normalizer = YAMLNormalizer()
            normalized_yaml, fixes = normalizer.normalize(yaml_content)
            if fixes:
                result.fixed_yaml = normalized_yaml
                result.fixes_applied = fixes
                result.warnings.append(f"Applied {len(fixes)} normalization fixes")
        
        # Parse normalized YAML
        try:
            data = yaml.safe_load(normalized_yaml)
        except yaml.YAMLError as e:
            result.valid = False
            result.errors.append(f"Failed to parse normalized YAML: {e}")
            result.score = 0.0
            return result
        
        # Stage 2: Schema Validation
        schema_result = self._validate_schema(data)
        if not schema_result["valid"]:
            result.valid = False
            result.errors.extend(schema_result["errors"])
            result.score = max(0.0, result.score - 30.0)
            if self.validation_level == "strict":
                return result
        
        result.warnings.extend(schema_result.get("warnings", []))
        
        # Stage 3: Referential Integrity (async, requires data_api_client)
        if self.data_api_client:
            ref_result = await self._validate_referential_integrity(data)
            if not ref_result["valid"]:
                result.errors.extend(ref_result["errors"])
                result.score = max(0.0, result.score - 20.0)
                if self.validation_level == "strict":
                    result.valid = False
            
            result.warnings.extend(ref_result.get("warnings", []))
        
        # Stage 4: Service Schema (async, requires ha_client)
        if self.ha_client:
            service_result = await self._validate_service_schema(data)
            if not service_result["valid"]:
                result.errors.extend(service_result["errors"])
                result.score = max(0.0, result.score - 15.0)
                if self.validation_level == "strict":
                    result.valid = False
            
            result.warnings.extend(service_result.get("warnings", []))
        
        # Stage 5: Safety Checks
        safety_result = self._validate_safety(data)
        if not safety_result["valid"]:
            result.warnings.extend(safety_result["warnings"])
            result.score = max(0.0, result.score - 10.0)
        
        # Stage 6: Style/Maintainability
        style_result = self._validate_style(data)
        if not style_result["valid"]:
            # Template syntax errors are critical - add to errors, not warnings
            if style_result.get("errors"):
                result.errors.extend(style_result["errors"])
                result.score = max(0.0, result.score - 15.0)
            result.warnings.extend(style_result.get("warnings", []))
            if not style_result.get("errors"):
                # Only reduce score for warnings if no errors
                result.score = max(0.0, result.score - 5.0)
        
        # Calculate final score
        if result.errors:
            result.valid = False
            result.score = max(0.0, result.score - len(result.errors) * 10.0)
        
        # Generate summary
        result.summary = self._generate_summary(result)
        
        return result

    def _validate_syntax(self, yaml_content: str) -> dict[str, Any]:
        """Stage 1: Syntax validation."""
        errors = []
        
        try:
            yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            errors.append(f"YAML syntax error: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    def _validate_schema(self, data: dict[str, Any]) -> dict[str, Any]:
        """Stage 2: Schema validation."""
        errors = []
        warnings = []
        
        if not isinstance(data, dict):
            errors.append("YAML root must be a dictionary")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Check required fields
        if "trigger" not in data:
            errors.append("Missing required field: 'trigger'")
        elif not data["trigger"]:
            errors.append("Field 'trigger' cannot be empty")
        elif not isinstance(data["trigger"], list):
            errors.append("Field 'trigger' must be a list")
        
        if "action" not in data:
            errors.append("Missing required field: 'action'")
        elif not data["action"]:
            errors.append("Field 'action' cannot be empty")
        elif not isinstance(data["action"], list):
            errors.append("Field 'action' must be a list")
        
        # Check for deprecated plural keys
        if "triggers" in data:
            errors.append("Use 'trigger' (singular) not 'triggers' (plural)")
        if "actions" in data:
            errors.append("Use 'action' (singular) not 'actions' (plural)")
        
        # Recommended fields
        if "alias" not in data:
            warnings.append("Missing recommended field: 'alias'")
        if "description" not in data:
            warnings.append("Missing recommended field: 'description'")
        if "initial_state" not in data:
            errors.append("Missing required field: 'initial_state' (must be 'true' for 2025.10+ compliance)")
        
        # Validate trigger structure
        if "trigger" in data and isinstance(data["trigger"], list):
            for i, trigger in enumerate(data["trigger"]):
                if not isinstance(trigger, dict):
                    errors.append(f"Trigger {i} must be a dictionary")
                elif "platform" not in trigger:
                    errors.append(
                        f"Trigger {i} must have 'platform' field (2025.10+ format requires 'platform:' field in triggers, "
                        "e.g., platform: state, platform: time, platform: time_pattern)"
                    )
        
        # Validate action structure
        if "action" in data and isinstance(data["action"], list):
            for i, action in enumerate(data["action"]):
                if not isinstance(action, dict):
                    errors.append(f"Action {i} must be a dictionary")
                elif "service" not in action and "scene" not in action and "delay" not in action:
                    # Check for advanced actions
                    if "choose" not in action and "repeat" not in action and "parallel" not in action and "sequence" not in action:
                        errors.append(
                            f"Action {i} must have 'service', 'scene', 'delay', or advanced action type "
                            "(2025.10+ format requires 'service:' field in actions, e.g., service: light.turn_on)"
                        )
                # Validate target structure for service actions
                if "service" in action and "target" in action:
                    if not isinstance(action["target"], dict):
                        errors.append(
                            f"Action {i}: 'target' must be a dictionary (2025.10+ format uses target: {{entity_id: ...}} or target: {{area_id: ...}})"
                        )
                elif "service" in action and "entity_id" in action and "target" not in action:
                    warnings.append(
                        f"Action {i}: entity_id should be inside 'target:' structure for 2025.10+ compliance. "
                        "Use target: {entity_id: ...} instead of entity_id: ... directly in action."
                    )
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    async def _validate_referential_integrity(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Stage 3: Referential integrity validation (Epic 51.7: Enhanced validation).
        
        Validates:
        - Entity IDs exist in Home Assistant
        - Area IDs exist
        - State values are valid for entities (if entity state available)
        """
        errors = []
        warnings = []
        
        if not self.data_api_client:
            return {"valid": True, "errors": errors, "warnings": warnings}
        
        try:
            # Extract entity IDs (enhanced extraction - only known locations)
            entity_ids = self._extract_entity_ids(data)
            
            if entity_ids:
                # Fetch entities from Data API
                entities = await self.data_api_client.fetch_entities()
                valid_entity_ids = {e.get("entity_id") for e in entities if e.get("entity_id")}
                
                # Build entity state map for state validation
                entity_states = {e.get("entity_id"): e.get("state") for e in entities if e.get("entity_id") and e.get("state")}
                
                # Check which entities are invalid
                invalid_entities = [eid for eid in entity_ids if eid not in valid_entity_ids]
                if invalid_entities:
                    errors.append(f"Invalid entity IDs: {', '.join(invalid_entities)}")
                
                # Validate state values (Epic 51.7: State validation)
                state_validation = self._validate_entity_states(data, entity_ids, entity_states)
                if state_validation["errors"]:
                    errors.extend(state_validation["errors"])
                if state_validation["warnings"]:
                    warnings.extend(state_validation["warnings"])
            
            # Extract area IDs
            area_ids = self._extract_area_ids(data)
            if area_ids:
                areas = await self.data_api_client.fetch_areas()
                valid_area_ids = {a.get("area_id") for a in areas if a.get("area_id")}
                
                invalid_areas = [aid for aid in area_ids if aid not in valid_area_ids]
                if invalid_areas:
                    warnings.append(f"Unknown area IDs: {', '.join(invalid_areas)}")
        
        except Exception as e:
            logger.error(f"Referential integrity validation failed: {e}")
            warnings.append(f"Could not validate entities/areas: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_entity_states(
        self, 
        data: dict[str, Any], 
        entity_ids: list[str], 
        entity_states: dict[str, str]
    ) -> dict[str, list[str]]:
        """
        Validate state values against known entity states (Epic 51.7).
        
        Checks:
        - State triggers reference valid states for the entity
        - Condition states are valid for the entity
        
        Args:
            data: Automation data
            entity_ids: List of entity IDs in automation
            entity_states: Map of entity_id -> current state
        
        Returns:
            Dictionary with errors and warnings
        """
        errors = []
        warnings = []
        
        # Known valid states for common domains
        # This is a simplified check - full validation would require Home Assistant API
        valid_states_by_domain = {
            "binary_sensor": ["on", "off"],
            "sensor": ["unavailable", "unknown"],  # Sensors have various states
            "light": ["on", "off", "unavailable"],
            "switch": ["on", "off", "unavailable"],
            "lock": ["locked", "unlocked", "unavailable"],
            "cover": ["open", "closed", "opening", "closing", "stopped", "unavailable"],
            "climate": ["heat", "cool", "auto", "off", "unavailable"],
            "fan": ["on", "off", "unavailable"],
        }
        
        # Extract state triggers and validate
        if "trigger" in data and isinstance(data["trigger"], list):
            for trigger in data["trigger"]:
                if isinstance(trigger, dict) and trigger.get("platform") == "state":
                    entity_id = trigger.get("entity_id")
                    to_state = trigger.get("to")
                    from_state = trigger.get("from")
                    
                    if entity_id and to_state:
                        # Get domain from entity_id
                        if "." in entity_id:
                            domain = entity_id.split(".")[0]
                            
                            # Check if state is valid for domain
                            if domain in valid_states_by_domain:
                                valid_states = valid_states_by_domain[domain]
                                if isinstance(to_state, str) and to_state not in valid_states:
                                    # Check if it's a list (multiple states)
                                    if not (isinstance(to_state, list) and all(s in valid_states for s in to_state)):
                                        warnings.append(
                                            f"State trigger for {entity_id}: 'to' state '{to_state}' may be invalid "
                                            f"(expected one of: {', '.join(valid_states)})"
                                        )
        
        # Extract condition states and validate
        if "condition" in data:
            conditions = data["condition"]
            if isinstance(conditions, list):
                for condition in conditions:
                    if isinstance(condition, dict) and "entity_id" in condition:
                        entity_id = condition.get("entity_id")
                        state = condition.get("state")
                        
                        if entity_id and state and "." in entity_id:
                            domain = entity_id.split(".")[0]
                            
                            if domain in valid_states_by_domain:
                                valid_states = valid_states_by_domain[domain]
                                if isinstance(state, str) and state not in valid_states:
                                    warnings.append(
                                        f"Condition for {entity_id}: state '{state}' may be invalid "
                                        f"(expected one of: {', '.join(valid_states)})"
                                    )
        
        return {"errors": errors, "warnings": warnings}

    async def _validate_service_schema(self, data: dict[str, Any]) -> dict[str, Any]:
        """Stage 4: Service schema validation."""
        errors = []
        warnings = []
        
        if not self.ha_client:
            return {"valid": True, "errors": errors, "warnings": warnings}
        
        # Extract services from actions
        services = self._extract_services(data)
        
        # TODO: Validate services against Home Assistant API
        # For now, just check format
        for service in services:
            if "." not in service:
                warnings.append(f"Service '{service}' may be invalid (expected format: domain.service)")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def _validate_safety(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Stage 5: Safety checks (Epic 51.10: Enhanced critical device validation).
        
        Identifies:
        - Critical devices (locks, alarms, heating, doors/windows)
        - Risky automation patterns
        - Safety scoring algorithm
        
        Returns:
            Dictionary with valid flag, warnings, and safety score
        """
        warnings = []
        safety_score = 100.0  # Start with perfect score, deduct for risks
        
        # Extract entities and services
        entity_ids = self._extract_entity_ids(data)
        services = self._extract_services(data)
        
        # Critical device domains (Epic 51.10)
        critical_domains = {
            "lock": {"risk_level": "high", "description": "Door locks"},
            "alarm_control_panel": {"risk_level": "high", "description": "Security alarms"},
            "climate": {"risk_level": "medium", "description": "Heating/cooling systems"},
            "cover": {"risk_level": "medium", "description": "Doors/windows"},
            "switch": {"risk_level": "low", "description": "Switches (if critical)"},
        }
        
        # Critical services (Epic 51.10)
        critical_services = {
            "lock.lock": {"risk_level": "high", "description": "Lock doors"},
            "lock.unlock": {"risk_level": "high", "description": "Unlock doors"},
            "alarm_control_panel.alarm_arm_away": {"risk_level": "high", "description": "Arm alarm (away)"},
            "alarm_control_panel.alarm_arm_home": {"risk_level": "high", "description": "Arm alarm (home)"},
            "alarm_control_panel.alarm_disarm": {"risk_level": "high", "description": "Disarm alarm"},
            "climate.set_temperature": {"risk_level": "medium", "description": "Set temperature"},
            "cover.open_cover": {"risk_level": "medium", "description": "Open doors/windows"},
            "cover.close_cover": {"risk_level": "medium", "description": "Close doors/windows"},
        }
        
        # Check for critical entities
        critical_entities = []
        for entity_id in entity_ids:
            if "." in entity_id:
                domain = entity_id.split(".")[0]
                if domain in critical_domains:
                    risk_info = critical_domains[domain]
                    critical_entities.append({
                        "entity_id": entity_id,
                        "risk_level": risk_info["risk_level"],
                        "description": risk_info["description"]
                    })
                    
                    # Deduct safety score based on risk level
                    if risk_info["risk_level"] == "high":
                        safety_score -= 20.0
                    elif risk_info["risk_level"] == "medium":
                        safety_score -= 10.0
                    else:
                        safety_score -= 5.0
        
        if critical_entities:
            high_risk = [e for e in critical_entities if e["risk_level"] == "high"]
            medium_risk = [e for e in critical_entities if e["risk_level"] == "medium"]
            
            if high_risk:
                warnings.append(
                    f"⚠️ HIGH RISK: Critical devices detected: {', '.join([e['entity_id'] for e in high_risk])}. "
                    f"Review automation carefully before deployment."
                )
            if medium_risk:
                warnings.append(
                    f"⚠️ MEDIUM RISK: Important devices detected: {', '.join([e['entity_id'] for e in medium_risk])}. "
                    f"Ensure automation behavior is correct."
                )
        
        # Check for critical services
        critical_services_used = []
        for service in services:
            if service in critical_services:
                risk_info = critical_services[service]
                critical_services_used.append({
                    "service": service,
                    "risk_level": risk_info["risk_level"],
                    "description": risk_info["description"]
                })
                
                # Deduct safety score
                if risk_info["risk_level"] == "high":
                    safety_score -= 25.0
                elif risk_info["risk_level"] == "medium":
                    safety_score -= 15.0
        
        if critical_services_used:
            high_risk_services = [s for s in critical_services_used if s["risk_level"] == "high"]
            medium_risk_services = [s for s in critical_services_used if s["risk_level"] == "medium"]
            
            if high_risk_services:
                warnings.append(
                    f"⚠️ HIGH RISK: Critical services used: {', '.join([s['service'] for s in high_risk_services])}. "
                    f"These operations affect security and safety. Admin approval recommended."
                )
            if medium_risk_services:
                warnings.append(
                    f"⚠️ MEDIUM RISK: Important services used: {', '.join([s['service'] for s in medium_risk_services])}. "
                    f"Review automation behavior."
                )
        
        # Check for risky patterns (Epic 51.10)
        risky_patterns = self._detect_risky_patterns(data, entity_ids, services)
        if risky_patterns:
            warnings.extend(risky_patterns)
            safety_score -= len(risky_patterns) * 10.0
        
        # Ensure safety score doesn't go below 0
        safety_score = max(0.0, safety_score)
        
        # Add safety score to warnings if below threshold
        if safety_score < 70.0:
            warnings.append(
                f"⚠️ Safety Score: {safety_score:.1f}/100.0 (Low - review automation carefully)"
            )
        elif safety_score < 85.0:
            warnings.append(
                f"ℹ️ Safety Score: {safety_score:.1f}/100.0 (Moderate - review recommended)"
            )
        
        return {
            "valid": True,  # Safety checks are warnings, not errors
            "warnings": warnings,
            "safety_score": safety_score
        }
    
    def _detect_risky_patterns(
        self, 
        data: dict[str, Any], 
        entity_ids: list[str], 
        services: list[str]
    ) -> list[str]:
        """
        Detect risky automation patterns (Epic 51.10).
        
        Patterns checked:
        - Unlocking doors without conditions
        - Disarming alarms without conditions
        - Temperature changes without limits
        - Critical operations without delays/confirmations
        
        Args:
            data: Automation data
            entity_ids: List of entity IDs
            services: List of service names
        
        Returns:
            List of warning messages for risky patterns
        """
        warnings = []
        
        # Check for unlock without conditions
        if "lock.unlock" in services:
            # Check if there are conditions before unlock
            has_conditions = "condition" in data and data.get("condition")
            if not has_conditions:
                warnings.append(
                    "⚠️ RISKY PATTERN: Unlock service used without conditions. "
                    "Consider adding conditions (time, presence, etc.) for security."
                )
        
        # Check for disarm without conditions
        if "alarm_control_panel.alarm_disarm" in services:
            has_conditions = "condition" in data and data.get("condition")
            if not has_conditions:
                warnings.append(
                    "⚠️ RISKY PATTERN: Alarm disarm used without conditions. "
                    "Consider adding conditions (time, presence, etc.) for security."
                )
        
        # Check for temperature changes without limits
        if "climate.set_temperature" in services:
            # Check if temperature is within reasonable bounds (would need to parse data)
            # For now, just warn if no conditions
            has_conditions = "condition" in data and data.get("condition")
            if not has_conditions:
                warnings.append(
                    "⚠️ RISKY PATTERN: Temperature change without conditions. "
                    "Consider adding limits or conditions to prevent extreme temperatures."
                )
        
        # Check for critical operations without delays
        critical_operations = ["lock.unlock", "alarm_control_panel.alarm_disarm"]
        critical_used = [s for s in services if s in critical_operations]
        if critical_used:
            # Check if there's a delay before critical operations
            has_delay = self._has_delay_before_action(data, critical_used)
            if not has_delay:
                warnings.append(
                    "⚠️ RISKY PATTERN: Critical operations without delay. "
                    "Consider adding a delay to allow for manual intervention."
                )
        
        return warnings
    
    def _has_delay_before_action(self, data: dict[str, Any], services: list[str]) -> bool:
        """
        Check if there's a delay before critical actions.
        
        Args:
            data: Automation data
            services: List of critical services to check
        
        Returns:
            True if delay found before critical actions
        """
        if "action" not in data or not isinstance(data["action"], list):
            return False
        
        # Check if delay appears before critical services in action sequence
        for i, action in enumerate(data["action"]):
            if isinstance(action, dict):
                # Check if this is a critical service
                service = action.get("service")
                if service in services:
                    # Check previous actions for delay
                    for j in range(i):
                        prev_action = data["action"][j]
                        if isinstance(prev_action, dict):
                            if "delay" in prev_action:
                                return True
                            # Check for delay in sequence/parallel
                            if "sequence" in prev_action or "parallel" in prev_action:
                                # Recursively check nested actions
                                nested_actions = prev_action.get("sequence") or prev_action.get("parallel", [])
                                if isinstance(nested_actions, list):
                                    for nested_action in nested_actions:
                                        if isinstance(nested_action, dict) and "delay" in nested_action:
                                            return True
        
        return False

    def _validate_template_syntax(self, template_string: str) -> list[str]:
        """
        Validate Jinja2 template syntax.
        
        Args:
            template_string: Template string to validate
            
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        try:
            from jinja2 import Environment, TemplateSyntaxError
            env = Environment()
            env.parse(template_string)
        except ImportError:
            # Jinja2 not available - skip validation but log warning
            logger.warning("Jinja2 not available - skipping template syntax validation")
            return []
        except TemplateSyntaxError as e:
            errors.append(f"Template syntax error: {e.message} at line {e.lineno}")
        except Exception as e:
            errors.append(f"Template validation error: {str(e)}")
        return errors
    
    def _extract_templates_from_data(self, data: Any, templates: list[tuple[str, str]] | None = None, path: str = "root") -> list[tuple[str, str]]:
        """
        Extract template strings from automation data.
        
        Args:
            data: Automation data structure
            templates: Accumulated (path, template_string) tuples
            path: Current path in data structure
            
        Returns:
            List of (path, template_string) tuples
        """
        if templates is None:
            templates = []
        
        if isinstance(data, dict):
            # Check for value_template in conditions (handled separately to avoid duplicates)
            if "value_template" in data:
                template_str = data["value_template"]
                if isinstance(template_str, str):
                    templates.append((f"{path}.value_template", template_str))
            
            # Check for templates in other fields that might contain templates
            for key, value in data.items():
                # Skip value_template since we handle it above
                if key == "value_template":
                    continue
                if isinstance(value, str) and ("{{" in value or "{%" in value):
                    # Potential template string
                    templates.append((f"{path}.{key}", value))
                elif isinstance(value, (dict, list)):
                    self._extract_templates_from_data(value, templates, f"{path}.{key}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._extract_templates_from_data(item, templates, f"{path}[{i}]")
        
        return templates

    def _validate_style(self, data: dict[str, Any]) -> dict[str, Any]:
        """Stage 6: Style/maintainability checks."""
        warnings = []
        errors = []
        
        # Check for deprecated error handling
        if "continue_on_error" in data:
            warnings.append("Use 'error' field instead of deprecated 'continue_on_error'")
        
        # Check action items for deprecated error handling
        if "action" in data and isinstance(data["action"], list):
            for i, action in enumerate(data["action"]):
                if isinstance(action, dict) and "continue_on_error" in action:
                    warnings.append(f"Action {i}: Use 'error' field instead of deprecated 'continue_on_error'")
        
        # Validate Jinja2 template syntax
        templates = self._extract_templates_from_data(data)
        for path, template_str in templates:
            template_errors = self._validate_template_syntax(template_str)
            for error in template_errors:
                errors.append(f"Template at {path}: {error}")
        
        # Check for templates accessing group.last_changed (common issue)
        for path, template_str in templates:
            if "group." in template_str and ".last_changed" in template_str:
                warnings.append(
                    f"Template at {path} accesses group.last_changed - groups don't have this attribute. "
                    "Use condition: state with for: option instead for continuous occupancy detection."
                )
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def _extract_entity_ids(self, data: Any, entity_ids: list[str] | None = None, context: str = "root") -> list[str]:
        """
        Extract entity IDs from automation data (Epic 51.7: Enhanced extraction).
        
        Only extracts from known entity ID locations to reduce false positives:
        - entity_id fields (direct or in target)
        - state triggers (entity_id)
        - condition entity_id
        - NOT from service names, descriptions, or arbitrary strings
        
        Args:
            data: Automation data structure
            entity_ids: Accumulated entity IDs
            context: Current context (root, trigger, action, condition, target)
        
        Returns:
            List of extracted entity IDs
        """
        if entity_ids is None:
            entity_ids = []
        
        if isinstance(data, dict):
            # Known entity_id locations
            if "entity_id" in data:
                entity_id = data["entity_id"]
                if isinstance(entity_id, str) and "." in entity_id:
                    # Validate format: domain.entity_name
                    if self._is_valid_entity_id(entity_id):
                        entity_ids.append(entity_id)
                elif isinstance(entity_id, list):
                    entity_ids.extend([
                        eid for eid in entity_id 
                        if isinstance(eid, str) and "." in eid and self._is_valid_entity_id(eid)
                    ])
            
            # Extract from state triggers (platform: state)
            if context == "trigger" and "platform" in data and data.get("platform") == "state":
                if "entity_id" in data:
                    entity_id = data["entity_id"]
                    if isinstance(entity_id, str) and "." in entity_id and self._is_valid_entity_id(entity_id):
                        entity_ids.append(entity_id)
                    elif isinstance(entity_id, list):
                        entity_ids.extend([
                            eid for eid in entity_id 
                            if isinstance(eid, str) and "." in eid and self._is_valid_entity_id(eid)
                        ])
            
            # Extract from conditions
            if context == "condition" and "entity_id" in data:
                entity_id = data["entity_id"]
                if isinstance(entity_id, str) and "." in entity_id and self._is_valid_entity_id(entity_id):
                    entity_ids.append(entity_id)
                elif isinstance(entity_id, list):
                    entity_ids.extend([
                        eid for eid in entity_id 
                        if isinstance(eid, str) and "." in eid and self._is_valid_entity_id(eid)
                    ])
            
            # Extract from target.entity_id (actions)
            if "target" in data and isinstance(data["target"], dict):
                if "entity_id" in data["target"]:
                    entity_id = data["target"]["entity_id"]
                    if isinstance(entity_id, str) and "." in entity_id and self._is_valid_entity_id(entity_id):
                        entity_ids.append(entity_id)
                    elif isinstance(entity_id, list):
                        entity_ids.extend([
                            eid for eid in entity_id 
                            if isinstance(eid, str) and "." in eid and self._is_valid_entity_id(eid)
                        ])
            
            # Recursively process nested structures, but skip service names
            for key, value in data.items():
                # Skip service names (not entities)
                if key == "service" and isinstance(value, str):
                    continue
                # Skip descriptions and aliases (may contain entity-like strings)
                if key in ("description", "alias", "name"):
                    continue
                # Process with context awareness
                new_context = key if key in ("trigger", "action", "condition", "target") else context
                self._extract_entity_ids(value, entity_ids, new_context)
        
        elif isinstance(data, list):
            for item in data:
                self._extract_entity_ids(item, entity_ids, context)
        
        return list(set(entity_ids))  # Remove duplicates
    
    def _is_valid_entity_id(self, entity_id: str) -> bool:
        """
        Validate entity ID format (Epic 51.7: Reduce false positives).
        
        Entity IDs must:
        - Contain exactly one dot (domain.entity_name)
        - Domain must be alphanumeric with underscores
        - Entity name must be alphanumeric with underscores
        - Not be a service name (domain.service format)
        
        Args:
            entity_id: Entity ID string to validate
        
        Returns:
            True if valid entity ID format
        """
        if not isinstance(entity_id, str):
            return False
        
        # Must contain exactly one dot
        if entity_id.count(".") != 1:
            return False
        
        parts = entity_id.split(".")
        if len(parts) != 2:
            return False
        
        domain, entity_name = parts
        
        # Domain must be alphanumeric with underscores
        if not domain or not domain.replace("_", "").isalnum():
            return False
        
        # Entity name must be alphanumeric with underscores
        if not entity_name or not entity_name.replace("_", "").isalnum():
            return False
        
        # Common false positives: service-like patterns
        # Services are typically: domain.service_name (but we check in _extract_services)
        # For now, accept all valid domain.entity patterns
        
        return True

    def _extract_area_ids(self, data: Any, area_ids: list[str] | None = None) -> list[str]:
        """Extract area IDs from automation data."""
        if area_ids is None:
            area_ids = []
        
        if isinstance(data, dict):
            if "area_id" in data:
                area_id = data["area_id"]
                if isinstance(area_id, str):
                    area_ids.append(area_id)
                elif isinstance(area_id, list):
                    area_ids.extend([aid for aid in area_id if isinstance(aid, str)])
            
            # Check target.area_id
            if "target" in data and isinstance(data["target"], dict):
                if "area_id" in data["target"]:
                    area_id = data["target"]["area_id"]
                    if isinstance(area_id, str):
                        area_ids.append(area_id)
                    elif isinstance(area_id, list):
                        area_ids.extend([aid for aid in area_id if isinstance(aid, str)])
            
            for value in data.values():
                self._extract_area_ids(value, area_ids)
        
        elif isinstance(data, list):
            for item in data:
                self._extract_area_ids(item, area_ids)
        
        return list(set(area_ids))  # Remove duplicates

    def _extract_services(self, data: Any, services: list[str] | None = None) -> list[str]:
        """
        Extract service names from automation data (Epic 51.7: Enhanced extraction).
        
        Only extracts from known service locations:
        - service field in actions
        - NOT from entity_id fields or descriptions
        
        Args:
            data: Automation data structure
            services: Accumulated service names
        
        Returns:
            List of extracted service names
        """
        if services is None:
            services = []
        
        if isinstance(data, dict):
            # Extract from service field (actions)
            if "service" in data:
                service = data["service"]
                if isinstance(service, str) and "." in service:
                    # Validate service format: domain.service_name
                    if self._is_valid_service_name(service):
                        services.append(service)
            
            # Recursively process, but skip entity_id fields
            for key, value in data.items():
                # Skip entity_id fields (not services)
                if key == "entity_id":
                    continue
                # Skip descriptions and aliases
                if key in ("description", "alias", "name"):
                    continue
                self._extract_services(value, services)
        
        elif isinstance(data, list):
            for item in data:
                self._extract_services(item, services)
        
        return list(set(services))  # Remove duplicates
    
    def _is_valid_service_name(self, service: str) -> bool:
        """
        Validate service name format (Epic 51.7: Distinguish from entities).
        
        Service names must:
        - Contain exactly one dot (domain.service_name)
        - Domain must be alphanumeric with underscores
        - Service name must be alphanumeric with underscores
        
        Args:
            service: Service name string to validate
        
        Returns:
            True if valid service name format
        """
        if not isinstance(service, str):
            return False
        
        # Must contain exactly one dot
        if service.count(".") != 1:
            return False
        
        parts = service.split(".")
        if len(parts) != 2:
            return False
        
        domain, service_name = parts
        
        # Domain must be alphanumeric with underscores
        if not domain or not domain.replace("_", "").isalnum():
            return False
        
        # Service name must be alphanumeric with underscores
        if not service_name or not service_name.replace("_", "").isalnum():
            return False
        
        return True

    def _generate_summary(self, result: ValidationResult) -> str:
        """Generate validation summary."""
        if result.valid and not result.warnings:
            return "✅ Validation passed with no issues"
        elif result.valid:
            return f"✅ Validation passed with {len(result.warnings)} warning(s)"
        else:
            return f"❌ Validation failed with {len(result.errors)} error(s) and {len(result.warnings)} warning(s)"

