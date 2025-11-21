"""
Unified Validation Pipeline
Validates automation plans through schema, entity resolution, capability checks, and policy evaluation.
"""

import logging
from dataclasses import dataclass
from typing import Any

import yaml

from src.contracts.models import AutomationPlan
from src.policy.engine import PolicyEngine, PolicyVerdict
from src.safety_validator import SafetyValidator

from .diffs import generate_yaml_diff
from .resolver import EntityResolver, ResolutionResult

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validation pipeline"""
    ok: bool
    verdict: str  # "allow", "warn", "deny"
    reasons: list[str]
    fixes: list[str]
    diff: dict[str, Any] | None = None
    entity_resolutions: dict[str, ResolutionResult] = None
    policy_verdict: PolicyVerdict | None = None
    safety_score: int | None = None
    schema_valid: bool = False

    def __post_init__(self):
        if self.entity_resolutions is None:
            self.entity_resolutions = {}
        if self.reasons is None:
            self.reasons = []
        if self.fixes is None:
            self.fixes = []


class AutomationValidator:
    """
    Unified validation pipeline for automation plans.

    Pipeline:
    1. Schema validation (contract enforcement)
    2. Entity resolution (user text → canonical entity_id)
    3. Capability/availability checks
    4. Policy evaluation (rules.yaml)
    5. Safety validation (existing SafetyValidator)
    6. Generate diff (if corrections applied)
    """

    def __init__(
        self,
        entity_resolver: EntityResolver | None = None,
        policy_engine: PolicyEngine | None = None,
        safety_validator: SafetyValidator | None = None,
    ):
        """
        Initialize validator.

        Args:
            entity_resolver: EntityResolver instance (optional)
            policy_engine: PolicyEngine instance (optional)
            safety_validator: SafetyValidator instance (optional)
        """
        self.entity_resolver = entity_resolver or EntityResolver()
        self.policy_engine = policy_engine or PolicyEngine()
        self.safety_validator = safety_validator
        logger.info("AutomationValidator initialized")

    async def validate(
        self,
        automation_input: Any,  # Can be AutomationPlan, dict, or YAML string
        original_automation: Any | None = None,
        overrides: dict[str, bool] | None = None,
    ) -> ValidationResult:
        """
        Validate automation plan through full pipeline.

        Args:
            automation_input: Automation plan (AutomationPlan, dict, or YAML string)
            original_automation: Optional original automation for diff generation
            overrides: Optional policy overrides

        Returns:
            ValidationResult with verdict, reasons, fixes, and diff
        """
        reasons = []
        fixes = []
        schema_valid = False
        entity_resolutions = {}

        # Step 1: Schema validation
        try:
            if isinstance(automation_input, str):
                # Parse YAML
                automation_dict = yaml.safe_load(automation_input)
                automation_plan = AutomationPlan.model_validate(automation_dict)
            elif isinstance(automation_input, AutomationPlan):
                automation_plan = automation_input
            elif isinstance(automation_input, dict):
                automation_plan = AutomationPlan.model_validate(automation_input)
            else:
                return ValidationResult(
                    ok=False,
                    verdict="deny",
                    reasons=["Invalid automation input type"],
                    fixes=[],
                )

            schema_valid = True
        except Exception as e:
            return ValidationResult(
                ok=False,
                verdict="deny",
                reasons=[f"Schema validation failed: {e}"],
                fixes=["Ensure automation conforms to schema (triggers, conditions, actions required)"],
                schema_valid=False,
            )

        # Step 2: Entity resolution
        automation_dict = automation_plan.model_dump(exclude_none=True)
        entity_texts = self._extract_entity_texts(automation_dict)

        for entity_text in entity_texts:
            resolution = await self.entity_resolver.resolve(entity_text)
            entity_resolutions[entity_text] = resolution

            if not resolution.resolved:
                reasons.append(f"Entity not found: {entity_text}")
                if resolution.alternatives:
                    fixes.append(f"Replace '{entity_text}' with one of: {', '.join(resolution.alternatives[:3])}")
            elif resolution.confidence < 0.7:
                reasons.append(f"Low confidence entity resolution: {entity_text} → {resolution.canonical_entity_id} (confidence: {resolution.confidence})")

        # Step 3: Policy evaluation
        policy_verdict = await self.policy_engine.evaluate(automation_dict, overrides or {})
        if not policy_verdict.passed:
            reasons.extend(policy_verdict.reasons)
            if policy_verdict.can_override:
                fixes.append("Apply required overrides or modify automation to comply with policy")

        # Step 4: Safety validation
        safety_score = None
        if self.safety_validator:
            try:
                automation_yaml = automation_plan.to_yaml()
                safety_result = await self.safety_validator.validate(automation_yaml)
                safety_score = safety_result.safety_score

                if not safety_result.passed:
                    reasons.append(f"Safety validation failed: {safety_result.summary}")
                    for issue in safety_result.issues:
                        if issue.suggested_fix:
                            fixes.append(issue.suggested_fix)
            except Exception as e:
                logger.warning(f"Safety validation error: {e}")

        # Step 5: Generate diff if original provided
        diff = None
        if original_automation:
            try:
                if isinstance(original_automation, str):
                    original_yaml = original_automation
                else:
                    original_yaml = automation_plan.to_yaml()

                new_yaml = automation_plan.to_yaml()
                diff = generate_yaml_diff(original_yaml, new_yaml)
            except Exception as e:
                logger.warning(f"Diff generation error: {e}")

        # Determine overall verdict
        if not schema_valid or policy_verdict.verdict.value == "deny" or any(not r.resolved for r in entity_resolutions.values()) or (safety_score is not None and safety_score < 60):
            verdict = "deny"
        elif policy_verdict.verdict.value == "warn" or (safety_score is not None and safety_score < 80):
            verdict = "warn"
        else:
            verdict = "allow"

        ok = verdict == "allow"

        return ValidationResult(
            ok=ok,
            verdict=verdict,
            reasons=reasons,
            fixes=fixes,
            diff=diff,
            entity_resolutions=entity_resolutions,
            policy_verdict=policy_verdict,
            safety_score=safety_score,
            schema_valid=schema_valid,
        )

    def _extract_entity_texts(self, automation: dict[str, Any]) -> list[str]:
        """Extract entity texts from automation for resolution"""
        entities = set()

        # Extract from triggers
        triggers = automation.get("triggers", automation.get("trigger", []))
        if not isinstance(triggers, list):
            triggers = [triggers]

        for trigger in triggers:
            entity_id = trigger.get("entity_id")
            if entity_id:
                if isinstance(entity_id, list):
                    entities.update(entity_id)
                else:
                    entities.add(entity_id)

        # Extract from conditions
        conditions = automation.get("conditions", automation.get("condition", []))
        if not isinstance(conditions, list):
            conditions = [conditions] if conditions else []

        for condition in conditions:
            entity_id = condition.get("entity_id")
            if entity_id:
                if isinstance(entity_id, list):
                    entities.update(entity_id)
                else:
                    entities.add(entity_id)

        # Extract from actions
        actions = automation.get("actions", automation.get("action", []))
        if not isinstance(actions, list):
            actions = [actions]

        for action in actions:
            entity_id = action.get("entity_id")
            if entity_id:
                if isinstance(entity_id, list):
                    entities.update(entity_id)
                else:
                    entities.add(entity_id)

            target = action.get("target", {})
            target_entity_id = target.get("entity_id")
            if target_entity_id:
                if isinstance(target_entity_id, list):
                    entities.update(target_entity_id)
                else:
                    entities.add(target_entity_id)

        return list(entities)

