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
from ..database.models import CompiledArtifact
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

    def __init__(self, template_library: TemplateLibrary, data_api_client: DataAPIClient):
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
        db: AsyncSession | None = None,
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
            template.compilation_mapping.alias_template or template.template_id, all_params
        )

        # Compile description
        description = self._compile_template_string(
            template.compilation_mapping.description_template or template.description, all_params
        )

        # Use mode from template compilation_mapping, default to "single"
        mode = template.compilation_mapping.mode or "single"

        # Build HA automation structure
        automation = {
            "alias": alias,
            "description": description,
            "initial_state": True,  # Required field for HA 2025.10+
            "mode": mode,
            "trigger": trigger,
            "action": action,
        }

        if condition:
            automation["condition"] = condition

        # Strip unresolved {{placeholders}} — HA rejects them
        # Required placeholders raise CompilationError; optional ones are stripped
        automation = self._strip_unresolved(automation, template)

        # Remove incomplete trigger/condition/action entries
        automation = self._remove_incomplete_entries(automation, template)

        # Generate YAML
        yaml_content = yaml.dump(automation, default_flow_style=False, sort_keys=False)

        # Generate human summary
        human_summary = self._generate_human_summary(template, parameters, resolved_context)

        # Generate diff summary (empty for new automations)
        diff_summary = []

        # Generate risk notes
        risk_notes = []
        if template.safety_class.value in ["high", "critical"]:
            risk_notes.append(
                {
                    "level": template.safety_class.value,
                    "message": f"This automation has {template.safety_class.value} safety classification",
                }
            )

        # Generate compiled_id
        compiled_id = f"c_{uuid.uuid4().hex[:8]}"

        # Extract area_id from resolved context for update-vs-create lookup
        area_id = resolved_context.get("matched_area_id")

        # Create compiled artifact
        compiled_artifact = CompiledArtifact(
            compiled_id=compiled_id,
            plan_id=plan_id,
            template_id=template_id,
            area_id=area_id,
            yaml=yaml_content,
            human_summary=human_summary,
            diff_summary=diff_summary,
            risk_notes=risk_notes,
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
            "template_id": template_id,
            "area_id": area_id,
            "yaml": yaml_content,
            "human_summary": human_summary,
            "diff_summary": diff_summary,
            "risk_notes": risk_notes,
        }

    def _compile_trigger(
        self, trigger_mapping: dict[str, Any], params: dict[str, Any]
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Compile trigger from mapping."""
        # Handle array of triggers
        if isinstance(trigger_mapping, list):
            return [self._compile_trigger_item(item, params) for item in trigger_mapping]

        # Single trigger
        return self._compile_trigger_item(trigger_mapping, params)

    def _compile_trigger_item(
        self, trigger_mapping: dict[str, Any], params: dict[str, Any]
    ) -> dict[str, Any]:
        """Compile single trigger item."""
        trigger = {}

        # Copy platform
        if "platform" in trigger_mapping:
            trigger["platform"] = self._compile_template_string(trigger_mapping["platform"], params)

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
        self, condition_mapping: dict[str, Any], params: dict[str, Any]
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Compile condition from mapping."""
        if isinstance(condition_mapping, list):
            return [self._compile_condition_item(item, params) for item in condition_mapping]

        return self._compile_condition_item(condition_mapping, params)

    def _compile_condition_item(
        self, condition_mapping: dict[str, Any], params: dict[str, Any]
    ) -> dict[str, Any]:
        """Compile single condition item."""
        condition = {}

        # Copy all fields with template substitution
        for key, value in condition_mapping.items():
            condition[key] = self._compile_value(value, params)

        return condition

    def _compile_action(
        self, action_mapping: dict[str, Any], params: dict[str, Any]
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Compile action from mapping."""
        if isinstance(action_mapping, list):
            return [self._compile_action_item(item, params) for item in action_mapping]

        return self._compile_action_item(action_mapping, params)

    def _compile_action_item(
        self, action_mapping: dict[str, Any], params: dict[str, Any]
    ) -> dict[str, Any]:
        """Compile single action item."""
        action = {}

        # Copy all fields with template substitution
        for key, value in action_mapping.items():
            action[key] = self._compile_value(value, params)

        return action

    def _compile_value(self, value: Any, params: dict[str, Any]) -> Any:
        """Compile a value (recursive)."""
        if isinstance(value, str):
            return self._compile_template_string(value, params)
        elif isinstance(value, dict):
            return self._compile_dict(value, params)
        elif isinstance(value, list):
            return [self._compile_value(item, params) for item in value]
        else:
            return value

    def _compile_dict(self, mapping: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        """Compile a dictionary (recursive)."""
        result = {}
        for key, value in mapping.items():
            compiled_key = self._compile_template_string(key, params)
            result[compiled_key] = self._compile_value(value, params)
        return result

    def _compile_template_string(self, template: str, params: dict[str, Any]) -> Any:
        """
        Compile template string with parameter substitution.

        Supports:
        - {{param_name}} — simple substitution
        - {{param[0]}} — array indexing
        - {{ceil(255 / param)}} — math expressions (ceil, floor, round, //, %)

        If the entire template is a single placeholder and resolves to a
        non-string (e.g. list), the native type is returned so YAML
        serialization produces the correct structure.
        """
        pattern = r"\{\{([^}]+)\}\}"
        matches = re.findall(pattern, template)

        if not matches:
            return template

        # Single-placeholder optimisation: return native type when the whole
        # string is just "{{expr}}" (preserves lists, ints, etc.)
        single_placeholder = re.fullmatch(pattern, template.strip())

        for match in matches:
            expr = match.strip()
            resolved = self._resolve_expression(expr, params)

            if resolved is not None:
                # If the whole template is this one placeholder, return the
                # native value directly (list stays list, int stays int).
                if single_placeholder and match == single_placeholder.group(1):
                    return resolved
                # Otherwise, splice the string representation into the result
                template = template.replace(f"{{{{{match}}}}}", str(resolved))
            else:
                logger.warning(f"Parameter '{expr}' not found in params, leaving placeholder")

        return template

    def _resolve_expression(self, expr: str, params: dict[str, Any]) -> Any:
        """Resolve a template expression against params.

        Handles:
        - Simple lookup: ``motion_sensor_entities``
        - Array index:   ``motion_sensor_entities[0]``
        - Math:          ``ceil(255 / dim_step)``, ``timeout // 60``
        """
        import math as _math

        # 1. Simple param lookup
        if expr in params:
            return params[expr]

        # 2. Array indexing — e.g. "motion_sensor_entities[0]"
        idx_match = re.match(r"^(\w+)\[(\d+)\]$", expr)
        if idx_match:
            name, idx = idx_match.group(1), int(idx_match.group(2))
            arr = params.get(name)
            if isinstance(arr, list) and idx < len(arr):
                return arr[idx]

        # 3. Math expression — safe eval with only math + params
        try:
            safe_ns: dict[str, Any] = {
                "ceil": _math.ceil,
                "floor": _math.floor,
                "round": round,
                "min": min,
                "max": max,
            }
            safe_ns.update({k: v for k, v in params.items() if isinstance(v, (int, float))})
            return eval(expr, {"__builtins__": {}}, safe_ns)  # noqa: S307
        except Exception:
            pass

        return None

    # HA Jinja functions that should NOT be treated as unresolved placeholders
    _HA_JINJA_FUNCS = re.compile(
        r"is_state\(|states\(|state_attr\(|now\(\)|utcnow\(\)|as_timestamp\("
    )

    def _strip_unresolved(self, obj: Any, template: Template | None = None) -> Any:
        """Remove or reject keys whose values still contain {{...}} placeholders.

        Required placeholders raise CompilationError.
        Optional placeholders are silently stripped.
        Empty containers left after stripping are also removed.
        Values containing HA Jinja functions (is_state, states, etc.) are kept.
        """
        _PH = re.compile(r"\{\{([^}]+)\}\}")

        # Build set of required parameter names from the template schema
        required_params: set[str] = set()
        if template:
            for param_name, param_schema in template.parameter_schema.items():
                if param_schema.required:
                    required_params.add(param_name)

        return self._strip_unresolved_recursive(obj, _PH, required_params)

    def _strip_unresolved_recursive(
        self, obj: Any, pattern: re.Pattern, required_params: set[str]
    ) -> Any:
        """Recursive implementation of placeholder stripping."""
        if isinstance(obj, dict):
            cleaned = {}
            for k, v in obj.items():
                if isinstance(v, str):
                    match = pattern.search(v)
                    if match:
                        # Skip HA Jinja expressions (is_state, states, etc.)
                        if self._HA_JINJA_FUNCS.search(v):
                            cleaned[k] = v
                            continue
                        # Extract base param name (handle nested like time_window.after)
                        param_name = match.group(1).strip().split(".")[0]
                        if param_name in required_params:
                            raise CompilationError(
                                f"Cannot compile: required parameter '{param_name}' "
                                f"is unresolved (key='{k}', value='{v}')"
                            )
                        logger.debug(f"Stripping optional unresolved placeholder: {k}={v!r}")
                        continue
                stripped = self._strip_unresolved_recursive(v, pattern, required_params)
                # Drop empty dicts/lists produced by stripping
                if isinstance(stripped, dict) and not stripped:
                    continue
                if isinstance(stripped, list) and not stripped:
                    continue
                cleaned[k] = stripped
            return cleaned

        if isinstance(obj, list):
            result = []
            for item in obj:
                stripped = self._strip_unresolved_recursive(item, pattern, required_params)
                if isinstance(stripped, dict) and not stripped:
                    continue
                if isinstance(stripped, str):
                    match = pattern.search(stripped)
                    if match:
                        param_name = match.group(1).strip().split(".")[0]
                        if param_name in required_params:
                            raise CompilationError(
                                f"Cannot compile: required parameter '{param_name}' is unresolved"
                            )
                        continue
                result.append(stripped)
            return result

        return obj

    def _remove_incomplete_entries(
        self, automation: dict[str, Any], template: Template | None = None
    ) -> dict[str, Any]:
        """Remove trigger/condition/action items that are structurally incomplete.

        HA requires triggers to have more than just ``platform``, and
        conditions to have more than just ``condition``.  If stripping
        left only the type key, drop the entire entry.

        Raises CompilationError if ALL trigger entries are incomplete
        (triggers are always required for a valid automation).
        """
        # Keys that are just type identifiers, not meaningful on their own
        type_only_keys = {"trigger": {"platform"}, "condition": {"condition"}}

        for section, min_keys in type_only_keys.items():
            items = automation.get(section)
            if not isinstance(items, list):
                continue
            cleaned = [
                item for item in items if not isinstance(item, dict) or set(item.keys()) != min_keys
            ]
            if cleaned:
                automation[section] = cleaned
            else:
                if section == "trigger":
                    template_name = template.template_id if template else "unknown"
                    raise CompilationError(
                        f"All trigger entries are incomplete after compilation. "
                        f"Template '{template_name}' cannot produce valid YAML "
                        f"for the given parameters."
                    )
                automation.pop(section, None)

        return automation

    def _generate_human_summary(
        self, template: Template, parameters: dict[str, Any], resolved_context: dict[str, Any]
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
