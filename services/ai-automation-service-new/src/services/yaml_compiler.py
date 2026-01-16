"""
YAML Compiler Service

Hybrid Flow Implementation: Deterministic YAML compilation from templates
NEVER calls LLM - pure deterministic compilation from template + plan + resolved context.
"""

import logging
import re
import uuid
from typing import Any

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.data_api_client import DataAPIClient
from ..database.models import CompiledArtifact, Plan
from ..templates.template_library import TemplateLibrary
from ..templates.template_schema import Template

logger = logging.getLogger(__name__)


class CompilationError(Exception):
    """Raised when compilation fails."""
    pass


class YAMLCompiler:
    """
    Service for compiling HA automation YAML from templates.
    
    Responsibilities:
    - Accept validated plan + resolved context
    - Load template compilation mapping
    - Resolve device graph to HA entity IDs/area IDs (via Data API)
    - Generate HA automation YAML (2025.10+ format)
    - Generate human_summary and diff_summary
    - NEVER call LLM - pure deterministic compilation
    """
    
    def __init__(
        self,
        template_library: TemplateLibrary,
        data_api_client: DataAPIClient
    ):
        """
        Initialize YAML compiler.
        
        Args:
            template_library: Template library for template lookups
            data_api_client: Data API client for entity/device lookups
        """
        self.template_library = template_library
        self.data_api_client = data_api_client
    
    async def compile_plan(
        self,
        plan_id: str,
        template_id: str,
        template_version: int,
        parameters: dict[str, Any],
        resolved_context: dict[str, Any],
        db: AsyncSession | None = None
    ) -> dict[str, Any]:
        """
        Compile automation YAML from plan.
        
        Args:
            plan_id: Plan identifier
            template_id: Template identifier
            template_version: Template version
            parameters: Template parameters
            resolved_context: Resolved context (from validator)
            db: Optional database session for storing compiled artifact
        
        Returns:
            Compiled artifact dictionary with compiled_id, yaml, human_summary, etc.
        
        Raises:
            CompilationError: If compilation fails
        """
        # Get template
        template = self.template_library.get_template(template_id, template_version)
        if not template:
            raise CompilationError(f"Template '{template_id}' version {template_version} not found")
        
        # Merge parameters and resolved context
        all_params = {**parameters, **resolved_context}
        
        # Compile trigger
        trigger = self._compile_trigger(template.compilation_mapping.trigger, all_params)
        
        # Compile condition (if present)
        condition = None
        if template.compilation_mapping.condition:
            condition = self._compile_condition(template.compilation_mapping.condition, all_params)
        
        # Compile action
        action = self._compile_action(template.compilation_mapping.action, all_params)
        
        # Compile alias
        alias = self._compile_template_string(
            template.compilation_mapping.alias_template or template.template_id,
            all_params
        )
        
        # Compile description
        description = self._compile_template_string(
            template.compilation_mapping.description_template or template.description,
            all_params
        )
        
        # Build HA automation structure
        automation = {
            "alias": alias,
            "description": description,
            "initial_state": True,  # Required field for HA 2025.10+
            "mode": "single",  # Default mode
            "trigger": trigger,
            "action": action
        }
        
        if condition:
            automation["condition"] = condition
        
        # Generate YAML
        yaml_content = yaml.dump(automation, default_flow_style=False, sort_keys=False)
        
        # Generate human summary
        human_summary = self._generate_human_summary(template, parameters, resolved_context)
        
        # Generate diff summary (empty for new automations)
        diff_summary = []
        
        # Generate risk notes
        risk_notes = []
        if template.safety_class.value in ["high", "critical"]:
            risk_notes.append({
                "level": template.safety_class.value,
                "message": f"This automation has {template.safety_class.value} safety classification"
            })
        
        # Generate compiled_id
        compiled_id = f"c_{uuid.uuid4().hex[:8]}"
        
        # Create compiled artifact
        compiled_artifact = CompiledArtifact(
            compiled_id=compiled_id,
            plan_id=plan_id,
            yaml=yaml_content,
            human_summary=human_summary,
            diff_summary=diff_summary,
            risk_notes=risk_notes
        )
        
        # Store in database if session provided
        if db:
            db.add(compiled_artifact)
            await db.commit()
            await db.refresh(compiled_artifact)
        
        logger.info(f"Compiled automation {compiled_id} from plan {plan_id}")
        
        return {
            "compiled_id": compiled_id,
            "plan_id": plan_id,
            "yaml": yaml_content,
            "human_summary": human_summary,
            "diff_summary": diff_summary,
            "risk_notes": risk_notes
        }
    
    def _compile_trigger(
        self,
        trigger_mapping: dict[str, Any],
        params: dict[str, Any]
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Compile trigger from mapping."""
        # Handle array of triggers
        if isinstance(trigger_mapping, list):
            return [self._compile_trigger_item(item, params) for item in trigger_mapping]
        
        # Single trigger
        return self._compile_trigger_item(trigger_mapping, params)
    
    def _compile_trigger_item(
        self,
        trigger_mapping: dict[str, Any],
        params: dict[str, Any]
    ) -> dict[str, Any]:
        """Compile single trigger item."""
        trigger = {}
        
        # Copy platform
        if "platform" in trigger_mapping:
            trigger["platform"] = self._compile_template_string(
                trigger_mapping["platform"],
                params
            )
        
        # Copy other fields with template substitution
        for key, value in trigger_mapping.items():
            if key == "platform":
                continue  # Already handled
            
            if isinstance(value, str):
                # Template string substitution
                trigger[key] = self._compile_template_string(value, params)
            elif isinstance(value, dict):
                # Recursive compilation
                trigger[key] = self._compile_dict(value, params)
            elif isinstance(value, list):
                # List compilation
                trigger[key] = [self._compile_value(item, params) for item in value]
            else:
                # Direct value
                trigger[key] = value
        
        return trigger
    
    def _compile_condition(
        self,
        condition_mapping: dict[str, Any],
        params: dict[str, Any]
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Compile condition from mapping."""
        if isinstance(condition_mapping, list):
            return [self._compile_condition_item(item, params) for item in condition_mapping]
        
        return self._compile_condition_item(condition_mapping, params)
    
    def _compile_condition_item(
        self,
        condition_mapping: dict[str, Any],
        params: dict[str, Any]
    ) -> dict[str, Any]:
        """Compile single condition item."""
        condition = {}
        
        # Copy all fields with template substitution
        for key, value in condition_mapping.items():
            condition[key] = self._compile_value(value, params)
        
        return condition
    
    def _compile_action(
        self,
        action_mapping: dict[str, Any],
        params: dict[str, Any]
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Compile action from mapping."""
        if isinstance(action_mapping, list):
            return [self._compile_action_item(item, params) for item in action_mapping]
        
        return self._compile_action_item(action_mapping, params)
    
    def _compile_action_item(
        self,
        action_mapping: dict[str, Any],
        params: dict[str, Any]
    ) -> dict[str, Any]:
        """Compile single action item."""
        action = {}
        
        # Copy all fields with template substitution
        for key, value in action_mapping.items():
            action[key] = self._compile_value(value, params)
        
        return action
    
    def _compile_value(
        self,
        value: Any,
        params: dict[str, Any]
    ) -> Any:
        """Compile a value (recursive)."""
        if isinstance(value, str):
            return self._compile_template_string(value, params)
        elif isinstance(value, dict):
            return self._compile_dict(value, params)
        elif isinstance(value, list):
            return [self._compile_value(item, params) for item in value]
        else:
            return value
    
    def _compile_dict(
        self,
        mapping: dict[str, Any],
        params: dict[str, Any]
    ) -> dict[str, Any]:
        """Compile a dictionary (recursive)."""
        result = {}
        for key, value in mapping.items():
            compiled_key = self._compile_template_string(key, params)
            result[compiled_key] = self._compile_value(value, params)
        return result
    
    def _compile_template_string(
        self,
        template: str,
        params: dict[str, Any]
    ) -> str:
        """
        Compile template string with parameter substitution.
        
        Supports {{param_name}} syntax for parameter substitution.
        """
        result = template
        
        # Find all {{param}} patterns
        pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(pattern, template)
        
        for match in matches:
            param_name = match.strip()
            param_value = params.get(param_name)
            
            if param_value is not None:
                # Replace {{param}} with value
                result = result.replace(f"{{{{{param_name}}}}}", str(param_value))
            else:
                # Parameter not found - leave as is or raise error?
                logger.warning(f"Parameter '{param_name}' not found in params, leaving placeholder")
        
        return result
    
    def _generate_human_summary(
        self,
        template: Template,
        parameters: dict[str, Any],
        resolved_context: dict[str, Any]
    ) -> str:
        """Generate human-readable summary of compiled automation."""
        summary_parts = []
        
        # Template description
        summary_parts.append(f"Template: {template.description}")
        
        # Key parameters
        key_params = []
        for param_name, param_value in parameters.items():
            if param_name not in ["room_type", "target_area"]:  # Skip context params
                key_params.append(f"{param_name}={param_value}")
        
        if key_params:
            summary_parts.append(f"Parameters: {', '.join(key_params)}")
        
        # Resolved context
        if resolved_context:
            context_parts = []
            if "matched_area_id" in resolved_context:
                context_parts.append(f"Area: {resolved_context['matched_area_id']}")
            if "presence_sensor_entity" in resolved_context:
                context_parts.append(f"Sensor: {resolved_context['presence_sensor_entity']}")
            
            if context_parts:
                summary_parts.append(f"Context: {', '.join(context_parts)}")
        
        return " | ".join(summary_parts)
