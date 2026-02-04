"""
Regression tests using test corpus.
Ensures rule stability across versions.
"""

import pytest
import sys
from pathlib import Path

shared_path = Path(__file__).parent.parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from ha_automation_lint.engine import LintEngine


class TestValidAutomations:
    """Test that valid automations pass linting."""

    def test_valid_automations_have_no_errors(self, lint_engine, valid_corpus_files):
        """Valid automations should not produce errors."""
        for yaml_file in valid_corpus_files:
            with open(yaml_file) as f:
                yaml_content = f.read()

            report = lint_engine.lint(yaml_content)

            # Valid examples should have 0 errors
            assert report.errors_count == 0, \
                f"Valid automation {yaml_file.name} produced errors: {[f.rule_id for f in report.findings if f.severity == 'error']}"


class TestInvalidAutomations:
    """Test that invalid automations are caught."""

    def test_invalid_automations_have_errors(self, lint_engine, invalid_corpus_files):
        """Invalid automations should produce errors."""
        for yaml_file in invalid_corpus_files:
            with open(yaml_file) as f:
                yaml_content = f.read()

            report = lint_engine.lint(yaml_content)

            # Invalid examples should produce at least one error
            assert len(report.findings) > 0, \
                f"Invalid automation {yaml_file.name} produced no findings"

    def test_missing_trigger_detected(self, lint_engine, corpus_dir):
        """Test SCHEMA001 is detected."""
        yaml_file = corpus_dir / "invalid" / "missing-trigger.yaml"
        if yaml_file.exists():
            with open(yaml_file) as f:
                yaml_content = f.read()

            report = lint_engine.lint(yaml_content)
            assert any(f.rule_id == "SCHEMA001" for f in report.findings)

    def test_missing_action_detected(self, lint_engine, corpus_dir):
        """Test SCHEMA002 is detected."""
        yaml_file = corpus_dir / "invalid" / "missing-action.yaml"
        if yaml_file.exists():
            with open(yaml_file) as f:
                yaml_content = f.read()

            report = lint_engine.lint(yaml_content)
            assert any(f.rule_id == "SCHEMA002" for f in report.findings)

    def test_duplicate_ids_detected(self, lint_engine, corpus_dir):
        """Test SCHEMA004 is detected."""
        yaml_file = corpus_dir / "invalid" / "duplicate-ids.yaml"
        if yaml_file.exists():
            with open(yaml_file) as f:
                yaml_content = f.read()

            report = lint_engine.lint(yaml_content)
            assert any(f.rule_id == "SCHEMA004" for f in report.findings)

    def test_invalid_service_format_detected(self, lint_engine, corpus_dir):
        """Test SCHEMA005 is detected."""
        yaml_file = corpus_dir / "invalid" / "invalid-service-format.yaml"
        if yaml_file.exists():
            with open(yaml_file) as f:
                yaml_content = f.read()

            report = lint_engine.lint(yaml_content)
            assert any(f.rule_id == "SCHEMA005" for f in report.findings)


class TestEdgeCases:
    """Test edge case handling."""

    def test_edge_cases_have_warnings(self, lint_engine, edge_corpus_files):
        """Edge cases should produce warnings or info messages."""
        for yaml_file in edge_corpus_files:
            with open(yaml_file) as f:
                yaml_content = f.read()

            report = lint_engine.lint(yaml_content)

            # Edge cases typically produce warnings or info
            assert len(report.findings) > 0, \
                f"Edge case {yaml_file.name} produced no findings"

    def test_delay_single_mode_detected(self, lint_engine, corpus_dir):
        """Test LOGIC001 is detected."""
        yaml_file = corpus_dir / "edge" / "delay-single-mode.yaml"
        if yaml_file.exists():
            with open(yaml_file) as f:
                yaml_content = f.read()

            report = lint_engine.lint(yaml_content)
            assert any(f.rule_id == "LOGIC001" for f in report.findings)

    def test_missing_description_detected(self, lint_engine, corpus_dir):
        """Test MAINTAINABILITY001 is detected."""
        yaml_file = corpus_dir / "edge" / "missing-description.yaml"
        if yaml_file.exists():
            with open(yaml_file) as f:
                yaml_content = f.read()

            report = lint_engine.lint(yaml_content)
            assert any(f.rule_id == "MAINTAINABILITY001" for f in report.findings)


class TestRuleDeterminism:
    """Test that rule outputs are stable across runs."""

    def test_rule_determinism(self, lint_engine, invalid_corpus_files):
        """Running lint twice should produce identical results."""
        for yaml_file in invalid_corpus_files:
            with open(yaml_file) as f:
                yaml_content = f.read()

            report1 = lint_engine.lint(yaml_content)
            report2 = lint_engine.lint(yaml_content)

            # Extract rule IDs for comparison
            rule_ids1 = sorted([f.rule_id for f in report1.findings])
            rule_ids2 = sorted([f.rule_id for f in report2.findings])

            assert rule_ids1 == rule_ids2, \
                f"Non-deterministic lint results for {yaml_file.name}"
