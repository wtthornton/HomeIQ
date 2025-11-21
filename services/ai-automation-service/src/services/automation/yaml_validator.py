"""
Automation YAML Validator

Multi-stage validation pipeline for automation YAML.
Consolidates validation logic from yaml_structure_validator and other sources.

Created: Phase 2 - Core Service Refactoring
"""

import logging
from dataclasses import dataclass
from typing import Any

from ...clients.ha_client import HomeAssistantClient
from ...services.yaml_structure_validator import YAMLStructureValidator

logger = logging.getLogger(__name__)


@dataclass
class ValidationStage:
    """Result of a single validation stage"""
    name: str
    valid: bool
    errors: list[str]
    warnings: list[str]


@dataclass
class ValidationPipelineResult:
    """Result of multi-stage validation"""
    valid: bool
    stages: list[ValidationStage]
    all_checks_passed: bool


class AutomationYAMLValidator:
    """
    Multi-stage validation pipeline for automation YAML.

    Stages:
    1. Syntax validation (YAML parsing)
    2. Structure validation (HA format)
    3. Entity existence validation
    4. Logic validation (no circular triggers, etc.)
    5. Safety checks (no destructive actions without confirmation)
    """

    def __init__(
        self,
        ha_client: HomeAssistantClient | None = None,
    ):
        """
        Initialize YAML validator.

        Args:
            ha_client: Home Assistant client for entity validation
        """
        self.ha_client = ha_client
        self.structure_validator = YAMLStructureValidator()

        logger.info("AutomationYAMLValidator initialized")

    async def validate(
        self,
        yaml_content: str,
        context: dict[str, Any] | None = None,
    ) -> ValidationPipelineResult:
        """
        Run multi-stage validation pipeline.

        Args:
            yaml_content: YAML string to validate
            context: Optional context (validated entities, etc.)

        Returns:
            ValidationPipelineResult with all stage results
        """
        stages = []

        # Stage 1: Syntax validation
        syntax_result = await self._validate_syntax(yaml_content)
        stages.append(syntax_result)

        if not syntax_result.valid:
            return ValidationPipelineResult(
                valid=False,
                stages=stages,
                all_checks_passed=False,
            )

        # Stage 2: Structure validation
        structure_result = await self._validate_structure(yaml_content)
        stages.append(structure_result)

        if not structure_result.valid:
            return ValidationPipelineResult(
                valid=False,
                stages=stages,
                all_checks_passed=False,
            )

        # Stage 3: Entity existence (if HA client available)
        if self.ha_client:
            entity_result = await self._validate_entities(yaml_content, context)
            stages.append(entity_result)

            if not entity_result.valid:
                return ValidationPipelineResult(
                    valid=False,
                    stages=stages,
                    all_checks_passed=False,
                )

        # Stage 4: Logic validation
        logic_result = await self._validate_logic(yaml_content)
        stages.append(logic_result)

        # Stage 5: Safety checks
        safety_result = await self._validate_safety(yaml_content)
        stages.append(safety_result)

        all_passed = all(stage.valid for stage in stages)

        return ValidationPipelineResult(
            valid=all_passed,
            stages=stages,
            all_checks_passed=all_passed,
        )

    async def _validate_syntax(self, yaml_content: str) -> ValidationStage:
        """Stage 1: Validate YAML syntax"""
        import yaml

        try:
            yaml.safe_load(yaml_content)
            return ValidationStage(
                name="syntax",
                valid=True,
                errors=[],
                warnings=[],
            )
        except yaml.YAMLError as e:
            return ValidationStage(
                name="syntax",
                valid=False,
                errors=[f"YAML syntax error: {e}"],
                warnings=[],
            )

    async def _validate_structure(self, yaml_content: str) -> ValidationStage:
        """Stage 2: Validate HA automation structure"""
        result = self.structure_validator.validate(yaml_content)

        return ValidationStage(
            name="structure",
            valid=result.is_valid,
            errors=result.errors,
            warnings=result.warnings,
        )

    async def _validate_entities(self, yaml_content: str, context: dict | None) -> ValidationStage:
        """Stage 3: Validate entities exist in HA"""

        import yaml

        errors = []
        warnings = []

        try:
            data = yaml.safe_load(yaml_content)

            # Extract entity IDs from YAML
            entity_ids = set()

            # Check triggers
            triggers = data.get("trigger", [])
            if isinstance(triggers, list):
                for trigger in triggers:
                    if isinstance(trigger, dict) and "entity_id" in trigger:
                        entity_id = trigger["entity_id"]
                        if isinstance(entity_id, str):
                            entity_ids.add(entity_id)
                        elif isinstance(entity_id, list):
                            entity_ids.update(entity_id)

            # Check conditions
            conditions = data.get("condition", [])
            if isinstance(conditions, list):
                for condition in conditions:
                    if isinstance(condition, dict) and "entity_id" in condition:
                        entity_id = condition["entity_id"]
                        if isinstance(entity_id, str):
                            entity_ids.add(entity_id)

            # Check actions
            actions = data.get("action", [])
            if isinstance(actions, list):
                for action in actions:
                    if isinstance(action, dict):
                        # Check target.entity_id
                        if "target" in action and isinstance(action["target"], dict):
                            if "entity_id" in action["target"]:
                                entity_id = action["target"]["entity_id"]
                                if isinstance(entity_id, str):
                                    entity_ids.add(entity_id)
                                elif isinstance(entity_id, list):
                                    entity_ids.update(entity_id)

            # Validate entities exist (if HA client available)
            if entity_ids and self.ha_client:
                from ...clients.data_api_client import DataAPIClient
                from ...services.entity.validator import EntityValidator

                validator = EntityValidator(
                    ha_client=self.ha_client,
                    data_api_client=DataAPIClient(),
                )

                validation_results = await validator.validate_entities(list(entity_ids))

                invalid_entities = [eid for eid, valid in validation_results.items() if not valid]
                if invalid_entities:
                    errors.append(f"Entities not found in HA: {', '.join(invalid_entities)}")

            return ValidationStage(
                name="entities",
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
            )

        except Exception as e:
            return ValidationStage(
                name="entities",
                valid=False,
                errors=[f"Entity validation error: {e}"],
                warnings=[],
            )

    async def _validate_logic(self, yaml_content: str) -> ValidationStage:
        """Stage 4: Validate automation logic"""
        # Placeholder for logic validation
        # Will check for circular triggers, impossible conditions, etc.
        return ValidationStage(
            name="logic",
            valid=True,
            errors=[],
            warnings=[],
        )

    async def _validate_safety(self, yaml_content: str) -> ValidationStage:
        """Stage 5: Safety checks"""
        # Placeholder for safety validation
        # Will check for destructive actions, security issues, etc.
        return ValidationStage(
            name="safety",
            valid=True,
            errors=[],
            warnings=[],
        )

