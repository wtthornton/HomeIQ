"""
Script Validation API

Epic: Platform-Wide Pattern Rollout, Story 5
Validates script definitions using the UnifiedValidationRouter pattern.
Checks YAML structure, entity references, service calls, and template syntax.
"""

import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..api.dependencies import get_ha_client
from ..api.error_handlers import handle_route_errors
from ..clients.ha_client import HomeAssistantClient

try:
    _project_root = str(Path(__file__).resolve().parents[4])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
except IndexError:
    pass  # Docker: PYTHONPATH already includes /app

from shared.patterns import (
    UnifiedValidationRouter,
    ValidationRequest,
    ValidationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scripts", tags=["script", "validation"])


class ValidateScriptRequest(BaseModel):
    yaml_content: str = Field(..., description="Script YAML content")
    normalize: bool = Field(True)
    validate_entities: bool = Field(True, description="Validate entity references")
    validate_services: bool = Field(True, description="Validate service calls")


class ValidateScriptResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    entity_validation: dict = Field(default_factory=dict)
    service_validation: dict = Field(default_factory=dict)
    score: float = 0.0


VALID_ACTION_KEYS = {
    "service",
    "target",
    "data",
    "delay",
    "wait_template",
    "event",
    "choose",
    "conditions",
    "sequence",
    "default",
    "repeat",
    "count",
    "while",
    "until",
    "if",
    "then",
    "else",
    "alias",
    "enabled",
    "variables",
    "stop",
    "parallel",
}


class ScriptValidationRouter(UnifiedValidationRouter):
    """Script validation using the UnifiedValidationRouter pattern."""

    domain = "script"

    error_categories = {
        "entity": ("entity", "Entity", "entity_id", "not found"),
        "service": ("service", "Service", "invalid service"),
    }

    def __init__(self, ha_client: HomeAssistantClient) -> None:
        self.ha_client = ha_client

    async def run_validation(
        self,
        request: ValidationRequest,
        **kwargs: Any,
    ) -> ValidationResponse:
        import yaml as yaml_lib

        errors: list[str] = []
        warnings: list[str] = []

        try:
            data = yaml_lib.safe_load(request.content)
        except yaml_lib.YAMLError as e:
            return ValidationResponse(valid=False, errors=[f"Invalid YAML: {e}"])

        if not isinstance(data, dict):
            return ValidationResponse(valid=False, errors=["Script YAML must be a mapping"])

        # Support both script: {name: {...}} and direct {alias, sequence} format
        scripts = {}
        if "script" in data and isinstance(data["script"], dict):
            scripts = data["script"]
        elif "sequence" in data:
            scripts = {"inline": data}
        else:
            scripts = data

        for script_name, script_def in scripts.items():
            if not isinstance(script_def, dict):
                errors.append(f"Script '{script_name}': definition must be a mapping")
                continue

            sequence = script_def.get("sequence", [])
            if not sequence:
                errors.append(f"Script '{script_name}': missing or empty 'sequence'")
                continue

            if not isinstance(sequence, list):
                errors.append(f"Script '{script_name}': 'sequence' must be a list")
                continue

            # Validate each action in the sequence
            for i, action in enumerate(sequence):
                if not isinstance(action, dict):
                    errors.append(f"Script '{script_name}', step {i + 1}: must be a mapping")
                    continue

                # Validate service calls
                if "service" in action:
                    svc = action["service"]
                    if request.validate_services and isinstance(svc, str):
                        parts = svc.split(".")
                        if len(parts) != 2:
                            errors.append(
                                f"Script '{script_name}', step {i + 1}: "
                                f"invalid service format '{svc}'"
                            )

                    # Validate entity references in targets
                    if request.validate_entities:
                        entity_errors = await self._validate_action_entities(
                            action, script_name, i + 1
                        )
                        errors.extend(entity_errors)

                # Validate template syntax
                self._validate_templates(action, script_name, i + 1, warnings)

        score = max(0.0, 100.0 - len(errors) * 15 - len(warnings) * 5)
        return self.build_response(
            {"valid": len(errors) == 0, "errors": errors, "warnings": warnings, "score": score},
            request,
        )

    async def _validate_action_entities(
        self, action: dict, script_name: str, step: int
    ) -> list[str]:
        """Validate entity_id references in an action's target."""
        errors: list[str] = []
        target = action.get("target", {})
        if not isinstance(target, dict):
            return errors

        entity_ids = []
        eid = target.get("entity_id")
        if isinstance(eid, str):
            entity_ids.append(eid)
        elif isinstance(eid, list):
            entity_ids.extend(str(e) for e in eid if isinstance(e, str))

        for entity_id in entity_ids:
            if entity_id.startswith("!input") or "{{" in entity_id:
                continue
            state = await self.ha_client.get_state(entity_id)
            if state is None:
                errors.append(
                    f"Script '{script_name}', step {step}: entity not found '{entity_id}'"
                )
        return errors

    def _validate_templates(
        self, action: dict, script_name: str, step: int, warnings: list[str]
    ) -> None:
        """Basic Jinja2 template syntax validation."""
        for key, val in action.items():
            if isinstance(val, str) and "{{" in val:
                # Check for matching braces
                open_count = val.count("{{")
                close_count = val.count("}}")
                if open_count != close_count:
                    warnings.append(
                        f"Script '{script_name}', step {step}: unmatched template braces in '{key}'"
                    )


@router.post("/validate", response_model=ValidateScriptResponse)
@handle_route_errors("validate script")
async def validate_script(
    request: ValidateScriptRequest,
    ha_client: HomeAssistantClient = Depends(get_ha_client),
) -> ValidateScriptResponse:
    """Validate a script definition."""
    try:
        validation_router = ScriptValidationRouter(ha_client)
        unified_request = ValidationRequest(
            content=request.yaml_content,
            normalize=request.normalize,
            validate_entities=request.validate_entities,
            validate_services=request.validate_services,
        )
        response = await validation_router.run_validation(unified_request)
    except Exception as e:
        logger.error(f"Script validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Validation error: {e}") from e

    entity_sub = response.subsections.get("entity_validation")
    service_sub = response.subsections.get("service_validation")

    return ValidateScriptResponse(
        valid=response.valid,
        errors=response.errors,
        warnings=response.warnings,
        entity_validation={
            "performed": entity_sub.performed if entity_sub else request.validate_entities,
            "passed": entity_sub.passed if entity_sub else True,
            "errors": entity_sub.errors if entity_sub else [],
        },
        service_validation={
            "performed": service_sub.performed if service_sub else request.validate_services,
            "passed": service_sub.passed if service_sub else True,
            "errors": service_sub.errors if service_sub else [],
        },
        score=response.score,
    )
