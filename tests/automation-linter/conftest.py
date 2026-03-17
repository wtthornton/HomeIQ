"""
Pytest configuration and shared fixtures for automation-linter tests.
"""

import sys
from pathlib import Path

import pytest

# Add shared library source directories to path
_project_root = Path(__file__).parent.parent.parent
for _lib_src in [
    _project_root / "libs" / "homeiq-ha" / "src",
    _project_root / "libs" / "homeiq-observability" / "src",
    _project_root / "libs" / "homeiq-data" / "src",
]:
    if str(_lib_src) not in sys.path:
        sys.path.insert(0, str(_lib_src))

# Override async fixtures from parent conftest since these tests are synchronous
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Override async cleanup fixture with synchronous version for these tests."""
    yield
    # No async cleanup needed for synchronous tests

from ha_automation_lint.constants import Severity
from ha_automation_lint.engine import LintEngine
from ha_automation_lint.fixers.auto_fixer import AutoFixer
from ha_automation_lint.models import (
    ActionIR,
    AutomationIR,
    Finding,
    SuggestedFix,
    TriggerIR,
)
from ha_automation_lint.parsers.yaml_parser import AutomationParser
from ha_automation_lint.renderers.yaml_renderer import YAMLRenderer


@pytest.fixture
def valid_automation_yaml() -> str:
    """Return valid automation YAML."""
    return """
alias: "Test Automation"
description: "Test description"
id: "test_automation"
trigger:
  - platform: state
    entity_id: sensor.temperature
    above: 25
action:
  - service: climate.set_temperature
    target:
      entity_id: climate.living_room
    data:
      temperature: 22
"""


@pytest.fixture
def invalid_automation_yaml() -> str:
    """Return invalid automation YAML (missing trigger)."""
    return """
alias: "Broken Automation"
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
"""


@pytest.fixture
def automation_with_delay() -> str:
    """Return automation with delay and single mode."""
    return """
alias: "Delay Single Mode"
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.hallway
  - delay: "00:05:00"
  - service: light.turn_off
    target:
      entity_id: light.hallway
"""


@pytest.fixture
def automation_missing_description() -> str:
    """Return automation missing description."""
    return """
alias: "No Description"
id: "no_desc"
trigger:
  - platform: state
    entity_id: sensor.test
action:
  - service: light.turn_on
    target:
      entity_id: light.test
"""


@pytest.fixture
def sample_automation_ir() -> AutomationIR:
    """Return sample AutomationIR for testing."""
    return AutomationIR(
        id="test_auto",
        alias="Test Automation",
        description="Test description",
        trigger=[
            TriggerIR(
                platform="state",
                raw={"platform": "state", "entity_id": "sensor.test"},
                path="automations[0].trigger[0]"
            )
        ],
        action=[
            ActionIR(
                service="light.turn_on",
                raw={"service": "light.turn_on", "target": {"entity_id": "light.test"}},
                path="automations[0].action[0]"
            )
        ],
        mode="single",
        source_index=0,
        raw_source={
            "id": "test_auto",
            "alias": "Test Automation",
            "description": "Test description",
            "trigger": [{"platform": "state", "entity_id": "sensor.test"}],
            "action": [{"service": "light.turn_on", "target": {"entity_id": "light.test"}}]
        },
        path="automations[0]"
    )


@pytest.fixture
def sample_finding() -> Finding:
    """Return sample Finding for testing."""
    return Finding(
        rule_id="TEST001",
        severity=Severity.WARN,
        message="Test finding message",
        why_it_matters="This is a test finding",
        path="automations[0]",
        suggested_fix=SuggestedFix(
            type="manual",
            summary="Fix manually"
        )
    )


@pytest.fixture
def lint_engine() -> LintEngine:
    """Return configured LintEngine instance."""
    return LintEngine()


@pytest.fixture
def parser() -> AutomationParser:
    """Return AutomationParser instance."""
    return AutomationParser()


@pytest.fixture
def renderer() -> YAMLRenderer:
    """Return YAMLRenderer instance."""
    return YAMLRenderer()


@pytest.fixture
def auto_fixer() -> AutoFixer:
    """Return AutoFixer instance."""
    return AutoFixer()


@pytest.fixture
def corpus_dir() -> Path:
    """Return path to test corpus directory."""
    return Path(__file__).parent.parent.parent / "simulation" / "automation-linter"


@pytest.fixture
def valid_corpus_files(corpus_dir: Path) -> list[Path]:
    """Return list of valid corpus YAML files."""
    valid_dir = corpus_dir / "valid"
    return list(valid_dir.glob("*.yaml"))


@pytest.fixture
def invalid_corpus_files(corpus_dir: Path) -> list[Path]:
    """Return list of invalid corpus YAML files."""
    invalid_dir = corpus_dir / "invalid"
    return list(invalid_dir.glob("*.yaml"))


@pytest.fixture
def edge_corpus_files(corpus_dir: Path) -> list[Path]:
    """Return list of edge case corpus YAML files."""
    edge_dir = corpus_dir / "edge"
    return list(edge_dir.glob("*.yaml"))
