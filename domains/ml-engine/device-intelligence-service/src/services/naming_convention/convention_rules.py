"""
Convention Rules — Scoring criteria for entity naming compliance.

Epic 64, Story 64.1: Defines the 100-point scoring rubric.
Each rule scores a dimension (0-max_points) with issues and suggestions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuleResult:
    """Result of evaluating a single convention rule."""

    rule_name: str
    max_points: int
    earned_points: int
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Title Case pattern: "Kitchen Light" not "kitchen light" or "KITCHEN LIGHT"
# ---------------------------------------------------------------------------
_TITLE_CASE_RE = re.compile(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+|\s+\d+|\s+[A-Z]{2,})*$")

# Common brand names to detect in friendly names
_BRAND_NAMES = frozenset({
    "philips", "hue", "ikea", "tradfri", "xiaomi", "aqara", "sonoff",
    "shelly", "tuya", "zigbee", "zwave", "z-wave", "esp32", "esp8266",
    "tasmota", "wled", "gosund", "meross", "kasa", "tp-link", "tplink",
})


def score_area_id(entity: dict[str, Any]) -> RuleResult:
    """area_id rule: +20 if entity has a non-empty area_id."""
    area_id = entity.get("area_id") or ""
    if area_id.strip():
        return RuleResult(rule_name="area_id", max_points=20, earned_points=20)
    return RuleResult(
        rule_name="area_id",
        max_points=20,
        earned_points=0,
        issues=["Entity has no area_id assigned"],
        suggestions=["Assign this entity to an area in Home Assistant"],
    )


def score_labels(entity: dict[str, Any]) -> RuleResult:
    """AI intent labels: +20 if entity has at least one label."""
    labels = entity.get("labels") or []
    if isinstance(labels, list) and len(labels) > 0:
        return RuleResult(rule_name="labels", max_points=20, earned_points=20)
    return RuleResult(
        rule_name="labels",
        max_points=20,
        earned_points=0,
        issues=["Entity has no labels"],
        suggestions=["Add labels like 'ai:lighting', 'ai:climate' for better AI understanding"],
    )


def score_aliases(entity: dict[str, Any]) -> RuleResult:
    """Aliases: +20 if entity has at least one alias."""
    aliases = entity.get("aliases") or []
    if isinstance(aliases, list) and len(aliases) > 0:
        points = 20 if len(aliases) >= 2 else 15
        return RuleResult(rule_name="aliases", max_points=20, earned_points=points)
    return RuleResult(
        rule_name="aliases",
        max_points=20,
        earned_points=0,
        issues=["Entity has no aliases"],
        suggestions=["Add aliases for voice and chat recognition (e.g., 'kitchen light', 'the big lamp')"],
    )


def score_friendly_name(entity: dict[str, Any]) -> RuleResult:
    """Friendly name convention: +20 for Title Case, no brand, area prefix."""
    friendly_name = entity.get("friendly_name") or ""
    if not friendly_name:
        return RuleResult(
            rule_name="friendly_name",
            max_points=20,
            earned_points=0,
            issues=["Entity has no friendly name"],
            suggestions=["Set a descriptive friendly name"],
        )

    points = 20
    issues: list[str] = []
    suggestions: list[str] = []

    # Check Title Case
    if not _TITLE_CASE_RE.match(friendly_name):
        points -= 5
        issues.append(f"Name '{friendly_name}' is not Title Case")
        suggestions.append(f"Rename to '{friendly_name.title()}'")

    # Check for brand names
    name_lower = friendly_name.lower()
    for brand in _BRAND_NAMES:
        if brand in name_lower:
            points -= 5
            issues.append(f"Name contains brand '{brand}'")
            suggestions.append("Remove brand names from friendly name")
            break

    # Check area prefix (if area_id available)
    area_id = entity.get("area_id") or ""
    if area_id and not name_lower.startswith(area_id.replace("_", " ")):
        points -= 5
        area_name = area_id.replace("_", " ").title()
        issues.append("Name does not start with area name")
        suggestions.append(f"Prefix with area: '{area_name} {friendly_name}'")

    # Minimum 0
    points = max(0, points)
    return RuleResult(
        rule_name="friendly_name",
        max_points=20,
        earned_points=points,
        issues=issues,
        suggestions=suggestions,
    )


def score_device_class(entity: dict[str, Any]) -> RuleResult:
    """device_class: +10 if set."""
    device_class = entity.get("device_class") or ""
    if device_class.strip():
        return RuleResult(rule_name="device_class", max_points=10, earned_points=10)
    return RuleResult(
        rule_name="device_class",
        max_points=10,
        earned_points=0,
        issues=["Entity has no device_class"],
        suggestions=["Set device_class in HA for proper icon/unit handling"],
    )


def score_sensor_role_label(entity: dict[str, Any]) -> RuleResult:
    """Sensor role label: +10 if sensor entities have a role label."""
    domain = entity.get("domain") or ""
    labels = entity.get("labels") or []

    # Only applies to sensor/binary_sensor
    if domain not in ("sensor", "binary_sensor"):
        return RuleResult(rule_name="sensor_role", max_points=10, earned_points=10)

    role_labels = [lb for lb in labels if isinstance(lb, str) and lb.startswith("role:")]
    if role_labels:
        return RuleResult(rule_name="sensor_role", max_points=10, earned_points=10)

    return RuleResult(
        rule_name="sensor_role",
        max_points=10,
        earned_points=0,
        issues=["Sensor entity has no role label"],
        suggestions=["Add a role label like 'role:temperature', 'role:motion', 'role:energy'"],
    )


# All rules in evaluation order
ALL_RULES = [
    score_area_id,
    score_labels,
    score_aliases,
    score_friendly_name,
    score_device_class,
    score_sensor_role_label,
]
