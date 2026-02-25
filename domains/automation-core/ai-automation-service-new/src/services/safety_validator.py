"""
Safety Validator

Epic 39, Story 39.11: Automation Safety Validation
Validates automation YAML for safety issues before deployment.
"""

import logging
import re
from enum import Enum
from typing import Any

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SafetySeverity(str, Enum):
    """Severity levels for safety issues."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class SafetyIssue(BaseModel):
    """A single safety issue found during validation."""

    severity: SafetySeverity
    category: str = Field(description="Category of the safety check that found this issue")
    message: str = Field(description="Human-readable description of the issue")
    detail: str | None = Field(default=None, description="Additional technical detail")
    deduction: int = Field(description="Points deducted from the safety score")


class SafetyResult(BaseModel):
    """Result of safety validation on automation YAML."""

    score: int = Field(ge=0, le=100, description="Safety score from 0 to 100")
    issues: list[SafetyIssue] = Field(default_factory=list)
    passed: bool = Field(description="Whether the safety score meets the minimum threshold (>= 60)")


# Deduction constants
_CRITICAL_DEDUCTION = 50
_MAJOR_DEDUCTION = 20
_MINOR_DEDUCTION = 10

# Threshold for passing
SAFETY_PASS_THRESHOLD = 60


class SafetyValidator:
    """Validates automation YAML for safety issues before deployment.

    Checks performed:
    1. Dangerous service detection (shell_command, python_script, HA restart/stop)
    2. Infinite loop detection (repeat without count limit)
    3. Excessive delay detection (delays > 1 hour)
    4. Entity scope check (targeting 'all' entities without area filter)
    5. Trigger safety (time_pattern triggers firing more than once per minute)
    6. Missing conditions (broad triggers without conditions)
    """

    DANGEROUS_SERVICES: set[str] = {
        "shell_command",
        "python_script",
        "homeassistant.restart",
        "homeassistant.stop",
    }

    RISKY_SERVICES: set[str] = {
        "script.turn_on",
        "homeassistant.reload_all",
        "homeassistant.reload_core_config",
    }

    MAX_DELAY_SECONDS = 3600  # 1 hour
    MAX_REPEAT_COUNT = 100

    async def validate(self, yaml_content: str | dict[str, Any]) -> SafetyResult:
        """Run all safety checks on automation YAML.

        Args:
            yaml_content: YAML string or already-parsed dictionary.

        Returns:
            SafetyResult with score, issues list, and pass/fail.
        """
        issues: list[SafetyIssue] = []

        # Parse YAML if string
        if isinstance(yaml_content, str):
            try:
                data = yaml.safe_load(yaml_content)
            except yaml.YAMLError as exc:
                return SafetyResult(
                    score=0,
                    issues=[
                        SafetyIssue(
                            severity=SafetySeverity.CRITICAL,
                            category="yaml_parse",
                            message="Failed to parse YAML",
                            detail=str(exc),
                            deduction=100,
                        )
                    ],
                    passed=False,
                )
        else:
            data = yaml_content

        if not isinstance(data, dict):
            return SafetyResult(
                score=0,
                issues=[
                    SafetyIssue(
                        severity=SafetySeverity.CRITICAL,
                        category="yaml_structure",
                        message="YAML root must be a dictionary",
                        deduction=100,
                    )
                ],
                passed=False,
            )

        # Run all checks
        issues.extend(self._check_dangerous_services(data))
        issues.extend(self._check_infinite_loops(data))
        issues.extend(self._check_excessive_delays(data))
        issues.extend(self._check_entity_scope(data))
        issues.extend(self._check_trigger_safety(data))
        issues.extend(self._check_missing_conditions(data))

        # Calculate score
        total_deduction = sum(issue.deduction for issue in issues)
        score = max(0, 100 - total_deduction)
        passed = score >= SAFETY_PASS_THRESHOLD

        # Log issues
        for issue in issues:
            if issue.severity == SafetySeverity.CRITICAL:
                logger.warning(
                    "Safety CRITICAL: %s - %s", issue.category, issue.message
                )
            elif issue.severity == SafetySeverity.MAJOR:
                logger.warning(
                    "Safety MAJOR: %s - %s", issue.category, issue.message
                )
            else:
                logger.warning(
                    "Safety %s: %s - %s",
                    issue.severity.value.upper(),
                    issue.category,
                    issue.message,
                )

        if not passed:
            logger.warning(
                "Safety validation FAILED: score=%d (threshold=%d), issues=%d",
                score,
                SAFETY_PASS_THRESHOLD,
                len(issues),
            )
        else:
            logger.info("Safety validation passed: score=%d, issues=%d", score, len(issues))

        return SafetyResult(score=score, issues=issues, passed=passed)

    # ------------------------------------------------------------------
    # Individual check methods
    # ------------------------------------------------------------------

    def _check_dangerous_services(self, data: dict[str, Any]) -> list[SafetyIssue]:
        """Check for dangerous service calls (shell_command, python_script, HA restart/stop)."""
        issues: list[SafetyIssue] = []
        services = self._extract_services(data)

        for service in services:
            service_lower = service.lower()
            # Check exact matches and prefixes
            if service_lower in self.DANGEROUS_SERVICES or service_lower.startswith(
                ("shell_command.", "python_script.")
            ):
                issues.append(
                    SafetyIssue(
                        severity=SafetySeverity.CRITICAL,
                        category="dangerous_service",
                        message=f"Dangerous service detected: {service}",
                        detail=(
                            "This service can execute arbitrary code or stop Home Assistant. "
                            "Requires explicit force_deploy override."
                        ),
                        deduction=_CRITICAL_DEDUCTION,
                    )
                )
            elif service_lower in self.RISKY_SERVICES:
                issues.append(
                    SafetyIssue(
                        severity=SafetySeverity.MINOR,
                        category="risky_service",
                        message=f"Risky service detected: {service}",
                        detail="This service has elevated permissions. Review carefully.",
                        deduction=_MINOR_DEDUCTION,
                    )
                )

        return issues

    def _check_infinite_loops(self, data: dict[str, Any]) -> list[SafetyIssue]:
        """Check for repeat actions without count limits."""
        issues: list[SafetyIssue] = []
        repeat_nodes = self._find_nodes_by_key(data, "repeat")

        for node in repeat_nodes:
            if not isinstance(node, dict):
                continue

            has_count = "count" in node
            has_while = "while" in node
            has_until = "until" in node

            if not has_count and not has_while and not has_until:
                issues.append(
                    SafetyIssue(
                        severity=SafetySeverity.MAJOR,
                        category="infinite_loop",
                        message="Repeat action has no termination condition",
                        detail=(
                            "The repeat block has no 'count', 'while', or 'until' condition. "
                            "This may run indefinitely."
                        ),
                        deduction=_MAJOR_DEDUCTION,
                    )
                )
            elif has_count:
                count = node.get("count")
                if isinstance(count, int) and count > self.MAX_REPEAT_COUNT:
                    issues.append(
                        SafetyIssue(
                            severity=SafetySeverity.MINOR,
                            category="excessive_repeat",
                            message=f"Repeat count ({count}) exceeds maximum ({self.MAX_REPEAT_COUNT})",
                            detail="High repeat counts may cause performance issues.",
                            deduction=_MINOR_DEDUCTION,
                        )
                    )

        return issues

    def _check_excessive_delays(self, data: dict[str, Any]) -> list[SafetyIssue]:
        """Check for delays exceeding 1 hour."""
        issues: list[SafetyIssue] = []
        delay_nodes = self._find_nodes_by_key(data, "delay")

        for node in delay_nodes:
            seconds = self._parse_delay_seconds(node)
            if seconds is not None and seconds > self.MAX_DELAY_SECONDS:
                issues.append(
                    SafetyIssue(
                        severity=SafetySeverity.MAJOR,
                        category="excessive_delay",
                        message=f"Delay of {seconds}s exceeds maximum ({self.MAX_DELAY_SECONDS}s)",
                        detail="Long delays block the automation execution thread.",
                        deduction=_MAJOR_DEDUCTION,
                    )
                )

        return issues

    def _check_entity_scope(self, data: dict[str, Any]) -> list[SafetyIssue]:
        """Check for automations targeting all entities without area filter."""
        issues: list[SafetyIssue] = []
        actions = self._get_actions(data)

        for action in actions:
            if not isinstance(action, dict):
                continue

            target = action.get("target", {})
            entity_id = action.get("entity_id") or (target.get("entity_id") if isinstance(target, dict) else None)

            if not isinstance(target, dict):
                target = {}

            has_area = bool(target.get("area_id"))
            has_device = bool(target.get("device_id"))

            # Check for "all" targeting: entity_id is "all" or missing entity/area/device
            if isinstance(entity_id, str) and entity_id.lower() == "all" and not has_area:
                issues.append(
                    SafetyIssue(
                        severity=SafetySeverity.MAJOR,
                        category="broad_entity_scope",
                        message="Action targets 'all' entities without area filter",
                        detail=(
                            "Targeting all entities can have unintended effects. "
                            "Add an area_id or device_id to limit scope."
                        ),
                        deduction=_MAJOR_DEDUCTION,
                    )
                )
            elif isinstance(entity_id, str) and entity_id.lower() == "all" and (has_area or has_device):
                # All with area filter is still worth a minor note
                pass

        return issues

    def _check_trigger_safety(self, data: dict[str, Any]) -> list[SafetyIssue]:
        """Check for time_pattern triggers that fire too frequently (> 1/minute)."""
        issues: list[SafetyIssue] = []
        triggers = data.get("trigger", [])
        if isinstance(triggers, dict):
            triggers = [triggers]
        if not isinstance(triggers, list):
            return issues

        for trigger in triggers:
            if not isinstance(trigger, dict):
                continue

            platform = trigger.get("platform", "")
            if platform != "time_pattern":
                continue

            seconds = trigger.get("seconds")
            minutes = trigger.get("minutes")
            hours = trigger.get("hours")

            # If seconds pattern fires more than once per minute
            if seconds is not None and minutes is None and hours is None:
                # seconds could be "/5" (every 5 seconds) or a number
                interval = self._parse_time_pattern_interval(seconds)
                if interval is not None and interval < 60:
                    issues.append(
                        SafetyIssue(
                            severity=SafetySeverity.MAJOR,
                            category="rapid_trigger",
                            message=f"time_pattern trigger fires every {interval}s (more than once per minute)",
                            detail=(
                                "Rapid triggers can overload Home Assistant. "
                                "Consider using a longer interval."
                            ),
                            deduction=_MAJOR_DEDUCTION,
                        )
                    )

        return issues

    def _check_missing_conditions(self, data: dict[str, Any]) -> list[SafetyIssue]:
        """Check for automations with broad triggers but no conditions."""
        issues: list[SafetyIssue] = []
        triggers = data.get("trigger", [])
        conditions = data.get("condition", [])

        if isinstance(triggers, dict):
            triggers = [triggers]
        if not isinstance(triggers, list):
            return issues

        has_conditions = bool(conditions)

        # Check for broad triggers: state triggers without specific entity
        for trigger in triggers:
            if not isinstance(trigger, dict):
                continue

            platform = trigger.get("platform", "")

            if platform == "state" and not has_conditions:
                entity_id = trigger.get("entity_id")
                # A state trigger on a specific entity is narrower
                # But a state trigger without entity_id or on a broad entity is risky
                if not entity_id:
                    issues.append(
                        SafetyIssue(
                            severity=SafetySeverity.MINOR,
                            category="missing_conditions",
                            message="State trigger without entity_id and no conditions",
                            detail="Broad triggers without conditions may fire unexpectedly.",
                            deduction=_MINOR_DEDUCTION,
                        )
                    )
                else:
                    # Specific entity but no conditions -- still worth flagging
                    from_state = trigger.get("from")
                    to_state = trigger.get("to")
                    if from_state is None and to_state is None:
                        issues.append(
                            SafetyIssue(
                                severity=SafetySeverity.MINOR,
                                category="missing_conditions",
                                message=(
                                    f"State trigger on '{entity_id}' with no "
                                    "from/to filter and no conditions"
                                ),
                                detail=(
                                    "This fires on every state change. "
                                    "Add 'from', 'to', or a condition to reduce false triggers."
                                ),
                                deduction=_MINOR_DEDUCTION,
                            )
                        )

            elif platform == "event" and not has_conditions:
                event_type = trigger.get("event_type")
                event_data = trigger.get("event_data")
                if not event_data:
                    issues.append(
                        SafetyIssue(
                            severity=SafetySeverity.MINOR,
                            category="missing_conditions",
                            message=(
                                f"Event trigger '{event_type or 'unknown'}' "
                                "with no event_data filter and no conditions"
                            ),
                            detail="Broad event triggers may fire on unrelated events.",
                            deduction=_MINOR_DEDUCTION,
                        )
                    )

        return issues

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _extract_services(self, data: Any) -> list[str]:
        """Recursively extract all service names from the automation data."""
        services: list[str] = []
        if isinstance(data, dict):
            if "service" in data:
                svc = data["service"]
                if isinstance(svc, str):
                    services.append(svc)
            # Also check for action shorthand
            if "action" in data and isinstance(data["action"], str):
                action_val = data["action"]
                # HA 2024.x uses "action" field as service name in some contexts
                if "." in action_val:
                    services.append(action_val)
            for value in data.values():
                services.extend(self._extract_services(value))
        elif isinstance(data, list):
            for item in data:
                services.extend(self._extract_services(item))
        return services

    def _find_nodes_by_key(self, data: Any, key: str) -> list[Any]:
        """Recursively find all values for a given key in nested data."""
        results: list[Any] = []
        if isinstance(data, dict):
            if key in data:
                results.append(data[key])
            for value in data.values():
                results.extend(self._find_nodes_by_key(value, key))
        elif isinstance(data, list):
            for item in data:
                results.extend(self._find_nodes_by_key(item, key))
        return results

    def _get_actions(self, data: dict[str, Any]) -> list[Any]:
        """Extract the action list from automation data."""
        actions = data.get("action", [])
        if isinstance(actions, dict):
            return [actions]
        if isinstance(actions, list):
            return actions
        return []

    def _parse_delay_seconds(self, delay_value: Any) -> int | None:
        """Parse a delay value into total seconds.

        Supports:
        - dict with hours/minutes/seconds/milliseconds
        - string "HH:MM:SS"
        - int (seconds)
        """
        if isinstance(delay_value, int):
            return delay_value

        if isinstance(delay_value, dict):
            hours = int(delay_value.get("hours", 0) or 0)
            minutes = int(delay_value.get("minutes", 0) or 0)
            seconds = int(delay_value.get("seconds", 0) or 0)
            milliseconds = int(delay_value.get("milliseconds", 0) or 0)
            return hours * 3600 + minutes * 60 + seconds + (milliseconds // 1000)

        if isinstance(delay_value, str):
            # Try HH:MM:SS format
            match = re.match(r"^(\d+):(\d+):(\d+)$", delay_value)
            if match:
                hours, minutes, seconds = int(match.group(1)), int(match.group(2)), int(match.group(3))
                return hours * 3600 + minutes * 60 + seconds
            # Try seconds only
            try:
                return int(delay_value)
            except ValueError:
                return None

        return None

    def _parse_time_pattern_interval(self, value: Any) -> int | None:
        """Parse a time_pattern seconds value into interval in seconds.

        Supports:
        - "/5" (every 5 seconds)
        - "5" or 5 (at second 5 -- treated as every 60s since it fires once per minute)
        """
        if isinstance(value, int):
            # Specific second means fires once per minute
            return 60

        if isinstance(value, str):
            value = value.strip()
            if value.startswith("/"):
                try:
                    return int(value[1:])
                except ValueError:
                    return None
            # Specific second
            try:
                int(value)
                return 60
            except ValueError:
                return None

        return None
