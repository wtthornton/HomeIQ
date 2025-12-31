"""
Business Rule Validator.

Extracts business rules from system prompt to testable code for validating
automation creation requests.
"""

import logging
from typing import Any, Optional

from ..entity_resolution.entity_resolution_service import EntityResolutionService
from ..entity_resolution.entity_resolution_result import EntityResolutionResult

logger = logging.getLogger(__name__)


class BusinessRuleValidator:
    """
    Validates business rules for automation creation.

    Extracts rules from system prompt:
    - Entity resolution validation
    - Effect name validation (exact, case-sensitive)
    - Context completeness validation
    - Safety rule validation (security domains, critical devices)
    """

    # Security-related domains
    SECURITY_DOMAINS = {"lock", "alarm", "camera", "person", "device_tracker"}

    # Critical services
    CRITICAL_SERVICES = {
        "lock.lock",
        "lock.unlock",
        "alarm_control_panel.alarm_arm",
        "alarm_control_panel.alarm_disarm",
    }

    def __init__(
        self,
        entity_resolution_service: Optional[EntityResolutionService] = None,
    ):
        """
        Initialize business rule validator.

        Args:
            entity_resolution_service: Entity resolution service (optional)
        """
        self.entity_resolution_service = entity_resolution_service

    async def validate_entity_resolution(
        self,
        user_prompt: str,
        context_entities: Optional[list[dict[str, Any]]] = None,
        target_domain: Optional[str] = None,
    ) -> EntityResolutionResult:
        """
        Validate entity resolution from user prompt.

        Business rule: Verify area + keywords + device type match.
        - 2-3 matches → list all
        - 4+ → use most specific
        - ambiguous → ask user

        Args:
            user_prompt: User's natural language request
            context_entities: Optional list of entities from context
            target_domain: Optional domain filter

        Returns:
            EntityResolutionResult with validation status
        """
        if not self.entity_resolution_service:
            return EntityResolutionResult(
                success=False,
                error="Entity resolution service not available",
            )

        return await self.entity_resolution_service.resolve_entities(
            user_prompt=user_prompt,
            context_entities=context_entities,
            target_domain=target_domain,
        )

    def validate_effect_names(
        self,
        effect_name: str,
        available_effects: list[str],
    ) -> tuple[bool, Optional[str], list[str]]:
        """
        Validate effect name is exact and case-sensitive.

        Business rule: Use EXACT names from effect_list/preset_list (case-sensitive).
        If not found, list top 5 similar and ask user.

        Args:
            effect_name: Effect name to validate
            available_effects: List of available effect names

        Returns:
            Tuple of (is_valid, error_message, similar_effects)
        """
        # Exact match (case-sensitive)
        if effect_name in available_effects:
            return True, None, []

        # Find similar effects (case-insensitive)
        effect_lower = effect_name.lower()
        similar = [
            e for e in available_effects if effect_lower in e.lower() or e.lower() in effect_lower
        ]

        if similar:
            # Return top 5 similar
            top_similar = similar[:5]
            return (
                False,
                f"Effect '{effect_name}' not found. Did you mean one of: {', '.join(top_similar)}?",
                top_similar,
            )

        return (
            False,
            f"Effect '{effect_name}' not found in available effects: {', '.join(available_effects[:10])}",
            [],
        )

    def validate_context_completeness(
        self,
        user_prompt: str,
        required_entities: list[str],
        context_entities: list[dict[str, Any]],
        required_areas: Optional[list[str]] = None,
        context_areas: Optional[list[dict[str, Any]]] = None,
    ) -> tuple[bool, list[str]]:
        """
        Validate that all mentioned entities/areas exist in context.

        Business rule: All mentioned entities/areas/effects must exist.
        If missing, state what's missing and suggest alternatives.

        Args:
            user_prompt: User's natural language request
            required_entities: List of entity IDs mentioned in prompt
            context_entities: List of entities from context
            required_areas: Optional list of area IDs mentioned
            context_areas: Optional list of areas from context

        Returns:
            Tuple of (is_complete, missing_items)
        """
        missing_items = []

        # Check entities
        context_entity_ids = {e.get("entity_id", "") for e in context_entities}
        for entity_id in required_entities:
            if entity_id not in context_entity_ids:
                missing_items.append(f"Entity '{entity_id}' not found in context")

        # Check areas
        if required_areas and context_areas:
            context_area_ids = {a.get("area_id", "") or a.get("id", "") for a in context_areas}
            for area_id in required_areas:
                if area_id not in context_area_ids:
                    missing_items.append(f"Area '{area_id}' not found in context")

        return len(missing_items) == 0, missing_items

    def check_safety_requirements(
        self,
        entities: list[str],
        services: list[str],
        automation_dict: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """
        Check safety requirements for automation.

        Business rule: Consider safety implications (security systems, locks, critical devices).
        Warn users about potential safety implications when relevant.

        Args:
            entities: List of entity IDs in automation
            services: List of service names in automation
            automation_dict: Automation YAML as dictionary

        Returns:
            Tuple of (is_safe, warnings)
        """
        warnings = []

        # Check for security-related entities
        security_entities = [
            e
            for e in entities
            if any(e.startswith(f"{domain}.") for domain in self.SECURITY_DOMAINS)
        ]
        if security_entities:
            warnings.append(
                f"Security-sensitive entities detected: {', '.join(security_entities)}. "
                "Ensure time-based constraints are appropriate."
            )

        # Check for critical services
        critical_services_used = [
            s for s in services if any(s.startswith(cs) for cs in self.CRITICAL_SERVICES)
        ]
        if critical_services_used:
            warnings.append(
                f"Critical service used: {', '.join(critical_services_used)}. "
                "Verify automation logic carefully."
            )

        # Enhanced safety validation (recommendation #4 from HA_AGENT_API_FLOW_ANALYSIS.md)
        # Check for time-based triggers with security entities
        trigger = automation_dict.get("trigger", [])
        has_time_trigger = False
        trigger_platforms = []
        if isinstance(trigger, list):
            has_time_trigger = any(
                t.get("platform") in ["time", "time_pattern", "sun", "calendar"]
                for t in trigger
            )
            trigger_platforms = [t.get("platform") for t in trigger]
        elif isinstance(trigger, dict):
            platform = trigger.get("platform")
            has_time_trigger = platform in ["time", "time_pattern", "sun", "calendar"]
            trigger_platforms = [platform] if platform else []

        # Enhanced time constraint validation for security automations
        if security_entities:
            if not has_time_trigger:
                warnings.append(
                    "Security automation without time constraints detected. "
                    "Consider adding time-based triggers (time, time_pattern, sun, calendar) for safety."
                )
            elif not automation_dict.get("condition"):
                warnings.append(
                    "Time-based trigger with security entities detected. "
                    "Consider adding conditions for additional safety."
                )

        return len(warnings) == 0, warnings

    def calculate_safety_score(
        self,
        entities: list[str],
        services: list[str],
        automation_dict: dict[str, Any],
    ) -> float:
        """
        Calculate safety score for automation (recommendation #4 from HA_AGENT_API_FLOW_ANALYSIS.md).

        Args:
            entities: List of entity IDs in automation
            services: List of service names in automation
            automation_dict: Automation YAML as dictionary

        Returns:
            Safety score from 0.0 (unsafe) to 10.0 (safe)
        """
        score = 10.0  # Start with perfect score

        # Check for security entities (deduct points)
        security_entities = [
            e
            for e in entities
            if any(e.startswith(f"{domain}.") for domain in self.SECURITY_DOMAINS)
        ]
        if security_entities:
            score -= 2.0  # Security entities reduce safety score

        # Check for critical services (deduct points)
        critical_services_used = [
            s for s in services if any(s.startswith(cs) for cs in self.CRITICAL_SERVICES)
        ]
        if critical_services_used:
            score -= 2.0  # Critical services reduce safety score

        # Check for time constraints (add points if present)
        trigger = automation_dict.get("trigger", [])
        has_time_trigger = False
        if isinstance(trigger, list):
            has_time_trigger = any(
                t.get("platform") in ["time", "time_pattern", "sun", "calendar"]
                for t in trigger
            )
        elif isinstance(trigger, dict):
            has_time_trigger = trigger.get("platform") in ["time", "time_pattern", "sun", "calendar"]

        if security_entities and has_time_trigger:
            score += 1.0  # Time constraints improve safety score

        # Check for conditions (add points if present)
        if automation_dict.get("condition"):
            score += 1.0  # Conditions improve safety score

        # Ensure score is in valid range
        return max(0.0, min(10.0, score))
