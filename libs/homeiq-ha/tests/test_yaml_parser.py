"""ha_automation_lint parser: modern (2024.10+) and legacy automation schemas.

Locks in the normalization added for HA 2026.x: plural triggers:/conditions:/
actions: with per-item 'trigger:'/'action:' keys must parse into the same IR
as the legacy singular forms.
"""

import sys
from pathlib import Path

LINT_DIR = Path(__file__).resolve().parents[1] / "src" / "homeiq_ha" / "ha_automation_lint"
if str(LINT_DIR) not in sys.path:
    sys.path.insert(0, str(LINT_DIR))

from parsers.yaml_parser import AutomationParser  # noqa: E402

MODERN = """
- alias: Office Presence Lighting
  id: office_presence_lighting
  mode: restart
  triggers:
    - trigger: state
      entity_id: binary_sensor.office_presence_group
      to: "on"
  conditions: []
  actions:
    - action: light.turn_on
      target:
        entity_id: light.office
"""

LEGACY = """
- alias: Legacy form
  trigger:
    - platform: state
      entity_id: binary_sensor.x
      to: "on"
  condition: []
  action:
    - service: light.turn_on
      entity_id: light.y
"""


def test_modern_plural_schema_parses_into_ir():
    autos, findings = AutomationParser().parse(MODERN)
    assert len(autos) == 1
    ir = autos[0]
    assert [t.platform for t in ir.trigger] == ["state"]
    assert [a.service for a in ir.action] == ["light.turn_on"]
    assert not [f for f in findings if str(f.severity).lower().endswith("error")]


def test_legacy_singular_schema_still_parses():
    autos, _ = AutomationParser().parse(LEGACY)
    assert len(autos) == 1
    assert [t.platform for t in autos[0].trigger] == ["state"]
    assert [a.service for a in autos[0].action] == ["light.turn_on"]


def test_single_dict_modern_form_detected_as_automation():
    autos, _ = AutomationParser().parse(
        'triggers:\n  - trigger: time\n    at: "07:00:00"\nactions:\n  - action: light.turn_on\n'
    )
    assert len(autos) == 1


def test_modern_and_legacy_produce_equivalent_ir():
    modern_ir, _ = AutomationParser().parse(MODERN)
    legacy_equiv = (
        MODERN.replace("triggers:", "trigger:")
        .replace("conditions:", "condition:")
        .replace("actions:", "action:")
        .replace("trigger: state", "platform: state")
        .replace("action: light.turn_on", "service: light.turn_on")
    )
    legacy_ir, _ = AutomationParser().parse(legacy_equiv)
    assert [t.platform for t in modern_ir[0].trigger] == [t.platform for t in legacy_ir[0].trigger]
    assert [a.service for a in modern_ir[0].action] == [a.service for a in legacy_ir[0].action]
