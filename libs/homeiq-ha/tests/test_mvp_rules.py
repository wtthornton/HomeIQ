"""ha_automation_lint MVP rules against modern-schema automations."""

import sys
from pathlib import Path

LINT_DIR = Path(__file__).resolve().parents[1] / "src" / "homeiq_ha" / "ha_automation_lint"
if str(LINT_DIR) not in sys.path:
    sys.path.insert(0, str(LINT_DIR))

from parsers.yaml_parser import AutomationParser  # noqa: E402
from rules.mvp_rules import (  # noqa: E402
    InvalidServiceFormatRule,
    MissingActionRule,
    MissingTriggerRule,
    UnknownTopLevelKeysRule,
)

MODERN = """
- alias: Modern
  triggers:
    - trigger: state
      entity_id: binary_sensor.g
      to: "on"
  actions:
    - action: light.turn_on
      target: {entity_id: light.x}
"""


def parse_one(yaml_text):
    autos, _ = AutomationParser().parse(yaml_text)
    assert len(autos) == 1
    return autos[0]


def test_modern_schema_not_flagged_missing_trigger_or_action():
    ir = parse_one(MODERN)
    assert MissingTriggerRule().check(ir) == []
    assert MissingActionRule().check(ir) == []


def test_modern_plural_keys_are_known_top_level():
    ir = parse_one(MODERN)
    assert UnknownTopLevelKeysRule().check(ir) == []


def test_missing_sections_still_flagged():
    ir = parse_one("- alias: Broken\n  triggers: []\n  actions: []\n")
    assert len(MissingTriggerRule().check(ir)) == 1
    assert len(MissingActionRule().check(ir)) == 1


def test_invalid_service_format_flagged_for_modern_action():
    ir = parse_one("- alias: Bad\n  triggers:\n    - trigger: time\n      at: '07:00'\n  actions:\n    - action: turnon\n")
    findings = InvalidServiceFormatRule().check(ir)
    assert len(findings) == 1
    assert "turnon" in findings[0].message
