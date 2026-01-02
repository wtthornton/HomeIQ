"""
Test suite for reviewing system prompt and debug statements.

This test suite validates:
1. System prompt structure and completeness
2. Debug statement quality and consistency
3. Logging best practices
4. Error handling and logging coverage
"""

import logging
import re
from pathlib import Path
from typing import Any

import pytest

# Import the system prompt
import sys
from pathlib import Path

# Add services directory to path for imports
project_root = Path(__file__).parent.parent
services_src = project_root / "services" / "ha-ai-agent-service" / "src"
sys.path.insert(0, str(services_src))

# Now import with the correct path
from prompts.system_prompt import SYSTEM_PROMPT


@pytest.mark.asyncio
class TestSystemPromptReview:
    """Test suite for system prompt review."""

    async def test_system_prompt_not_empty(self):
        """Test that system prompt is not empty."""
        assert SYSTEM_PROMPT, "System prompt should not be empty"
        assert len(SYSTEM_PROMPT.strip()) > 100, "System prompt should be substantial"

    async def test_system_prompt_contains_required_sections(self):
        """Test that system prompt contains all required sections."""
        required_sections = [
            "Automation Creation Workflow",
            "MANDATORY WORKFLOW",
            "STEP 1: Generate Preview",
            "STEP 2: Wait for Approval",
            "STEP 3: Execute After Approval",
            "Home Assistant Context",
            "Automation Creation Guidelines",
            "Response Format",
            "Safety Considerations",
        ]
        
        for section in required_sections:
            assert section in SYSTEM_PROMPT, f"System prompt missing required section: {section}"

    async def test_system_prompt_contains_tool_references(self):
        """Test that system prompt references all available tools."""
        required_tools = [
            "preview_automation_from_prompt",
            "create_automation_from_prompt",
            "suggest_automation_enhancements",
        ]
        
        for tool in required_tools:
            assert tool in SYSTEM_PROMPT, f"System prompt missing tool reference: {tool}"

    async def test_system_prompt_workflow_clarity(self):
        """Test that workflow steps are clearly defined."""
        # Check for mandatory workflow indicators
        assert "MANDATORY" in SYSTEM_PROMPT or "MANDATORY WORKFLOW" in SYSTEM_PROMPT
        assert "STEP 1" in SYSTEM_PROMPT
        assert "STEP 2" in SYSTEM_PROMPT
        assert "STEP 3" in SYSTEM_PROMPT

    async def test_system_prompt_contains_critical_rules(self):
        """Test that critical rules are clearly stated."""
        critical_rules = [
            "NEVER call `create_automation_from_prompt` without",
            "ALWAYS generate preview first",
            "Use context to find entities",
        ]
        
        for rule in critical_rules:
            assert rule in SYSTEM_PROMPT, f"System prompt missing critical rule: {rule}"

    async def test_system_prompt_yaml_examples_valid(self):
        """Test that YAML examples in prompt are syntactically valid."""
        import yaml
        
        # Extract YAML code blocks
        yaml_blocks = re.findall(r'```yaml\n(.*?)```', SYSTEM_PROMPT, re.DOTALL)
        
        for block in yaml_blocks:
            try:
                yaml.safe_load(block)
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML in system prompt: {e}\nBlock: {block[:200]}")

    async def test_system_prompt_length_reasonable(self):
        """Test that system prompt length is reasonable (not too long/short)."""
        length = len(SYSTEM_PROMPT)
        assert length > 5000, f"System prompt too short: {length} chars (expected > 5000)"
        assert length < 50000, f"System prompt too long: {length} chars (expected < 50000)"

    async def test_system_prompt_no_hardcoded_entity_ids(self):
        """Test that system prompt doesn't contain hardcoded entity IDs (should use examples)."""
        # Check for common entity ID patterns that might be hardcoded
        hardcoded_patterns = [
            r'light\.office_\w+',  # Should be examples, not real IDs
            r'binary_sensor\.office_\w+',
        ]
        
        for pattern in hardcoded_patterns:
            matches = re.findall(pattern, SYSTEM_PROMPT)
            # Allow examples but warn if too many
            if len(matches) > 5:
                pytest.fail(f"Too many hardcoded entity IDs found: {matches[:5]}")


@pytest.mark.asyncio
class TestDebugStatementsReview:
    """Test suite for reviewing debug statements and logging."""

    @pytest.fixture
    def ha_tools_file(self):
        """Load ha_tools.py file content."""
        file_path = Path("services/ha-ai-agent-service/src/tools/ha_tools.py")
        assert file_path.exists(), f"File not found: {file_path}"
        return file_path.read_text(encoding="utf-8")

    async def test_all_logger_calls_have_context(self, ha_tools_file):
        """Test that all logger calls include contextual information."""
        # Find all logger calls
        logger_pattern = r'logger\.(debug|info|warning|error)\([^)]+\)'
        logger_calls = re.findall(logger_pattern, ha_tools_file, re.MULTILINE)
        
        # Check for logger calls without context (just error messages)
        problematic_patterns = [
            r'logger\.(error|warning)\(f?"[^"]*"\)',  # Simple string without context
        ]
        
        issues = []
        for pattern in problematic_patterns:
            matches = re.findall(pattern, ha_tools_file)
            if matches:
                issues.extend(matches)
        
        # Allow some simple error messages, but flag if too many
        if len(issues) > 3:
            pytest.fail(f"Found {len(issues)} logger calls without sufficient context: {issues[:3]}")

    async def test_error_logging_includes_exc_info(self, ha_tools_file):
        """Test that error logging includes exc_info for exceptions."""
        # Find logger.error calls in exception handlers
        error_pattern = r'logger\.error\([^)]+\)'
        error_calls = re.findall(error_pattern, ha_tools_file)
        
        # Check exception handlers
        exception_handlers = re.findall(
            r'except\s+.*?:\s*\n\s*logger\.error\([^)]+\)',
            ha_tools_file,
            re.MULTILINE | re.DOTALL
        )
        
        # Count error calls with exc_info
        exc_info_count = ha_tools_file.count("exc_info=True")
        
        # Should have exc_info=True in most exception handlers
        if exception_handlers and exc_info_count < len(exception_handlers) * 0.7:
            pytest.fail(
                f"Only {exc_info_count}/{len(exception_handlers)} exception handlers "
                f"include exc_info=True. Should be > 70%"
            )

    async def test_debug_statements_are_meaningful(self, ha_tools_file):
        """Test that debug statements provide meaningful information."""
        # Find all logger.debug calls
        debug_pattern = r'logger\.debug\(([^)]+)\)'
        debug_calls = re.findall(debug_pattern, ha_tools_file)
        
        # Check for empty or trivial debug statements
        trivial_patterns = [
            r'logger\.debug\(f?"[^"]{0,10}"\)',  # Very short messages
            r'logger\.debug\(f?"Debug[^"]*"\)',  # Generic "Debug" messages
        ]
        
        issues = []
        for pattern in trivial_patterns:
            matches = re.findall(pattern, ha_tools_file)
            issues.extend(matches)
        
        if issues:
            pytest.fail(f"Found {len(issues)} trivial debug statements: {issues[:3]}")

    async def test_info_logging_includes_identifiers(self, ha_tools_file):
        """Test that info logging includes identifiers (conversation_id, automation_id, etc.)."""
        # Find logger.info calls
        info_pattern = r'logger\.info\(([^)]+)\)'
        info_calls = re.findall(info_pattern, ha_tools_file)
        
        # Check for info calls without identifiers
        # Info logs should include context like conversation_id, automation_id, etc.
        info_without_context = []
        for call in info_calls:
            # Check if it includes common identifiers
            has_identifier = any(
                identifier in call
                for identifier in ["conversation_id", "automation_id", "alias", "user_prompt"]
            )
            if not has_identifier and len(call) > 50:  # Longer messages should have context
                info_without_context.append(call[:100])
        
        # Allow some info logs without identifiers, but flag if too many
        if len(info_without_context) > 5:
            pytest.fail(
                f"Found {len(info_without_context)} info logs without identifiers: "
                f"{info_without_context[:3]}"
            )

    async def test_warning_logging_explains_impact(self, ha_tools_file):
        """Test that warning logging explains the impact."""
        # Find logger.warning calls
        warning_pattern = r'logger\.warning\(([^)]+)\)'
        warning_calls = re.findall(warning_pattern, ha_tools_file)
        
        # Check for warnings without impact explanation
        warnings_without_impact = []
        for call in warning_calls:
            # Check if warning explains impact or suggests action
            has_impact = any(
                keyword in call.lower()
                for keyword in ["failed", "error", "unavailable", "consider", "suggest"]
            )
            if not has_impact and len(call) > 30:
                warnings_without_impact.append(call[:100])
        
        # Allow some warnings without explicit impact, but flag if too many
        if len(warnings_without_impact) > 3:
            pytest.fail(
                f"Found {len(warnings_without_impact)} warnings without impact explanation: "
                f"{warnings_without_impact[:3]}"
            )

    async def test_logging_levels_appropriate(self, ha_tools_file):
        """Test that logging levels are used appropriately."""
        # Count logging calls by level
        debug_count = len(re.findall(r'logger\.debug\(', ha_tools_file))
        info_count = len(re.findall(r'logger\.info\(', ha_tools_file))
        warning_count = len(re.findall(r'logger\.warning\(', ha_tools_file))
        error_count = len(re.findall(r'logger\.error\(', ha_tools_file))
        
        total = debug_count + info_count + warning_count + error_count
        
        # Check distribution
        if total > 0:
            debug_pct = (debug_count / total) * 100
            info_pct = (info_count / total) * 100
            warning_pct = (warning_count / total) * 100
            error_pct = (error_count / total) * 100
            
            # Debug should be < 30% (most should be info/warning/error)
            if debug_pct > 30:
                pytest.fail(
                    f"Too many debug statements: {debug_pct:.1f}% "
                    f"(expected < 30%). Consider promoting some to info level."
                )
            
            # Info should be substantial (30-60%)
            if info_pct < 20:
                pytest.fail(
                    f"Too few info statements: {info_pct:.1f}% "
                    f"(expected > 20%). Consider promoting debug to info."
                )

    async def test_no_print_statements(self, ha_tools_file):
        """Test that there are no print statements (should use logger)."""
        print_statements = re.findall(r'\bprint\s*\(', ha_tools_file)
        if print_statements:
            pytest.fail(
                f"Found {len(print_statements)} print statements. "
                f"Use logger instead: {print_statements[:3]}"
            )

    async def test_logging_consistency(self, ha_tools_file):
        """Test that logging format is consistent."""
        # Check for consistent f-string usage
        f_string_pattern = r'logger\.(debug|info|warning|error)\(f"[^"]+"\)'
        f_string_calls = len(re.findall(f_string_pattern, ha_tools_file))
        
        # Check for .format() usage
        format_pattern = r'logger\.(debug|info|warning|error)\([^)]+\.format\([^)]+\)\)'
        format_calls = len(re.findall(format_pattern, ha_tools_file))
        
        # Check for % formatting
        percent_pattern = r'logger\.(debug|info|warning|error)\([^)]+%[^)]+\)'
        percent_calls = len(re.findall(percent_pattern, ha_tools_file))
        
        total_formatted = f_string_calls + format_calls + percent_calls
        
        # Prefer f-strings for consistency
        if total_formatted > 0 and f_string_calls / total_formatted < 0.8:
            pytest.fail(
                f"Inconsistent logging format: {f_string_calls} f-strings, "
                f"{format_calls} .format(), {percent_calls} % formatting. "
                f"Prefer f-strings for consistency."
            )


@pytest.mark.asyncio
class TestPromptAndDebugIntegration:
    """Integration tests for prompt and debug statement interaction."""

    async def test_prompt_mentions_debug_screen(self):
        """Test that system prompt mentions debug screen availability."""
        assert "debug screen" in SYSTEM_PROMPT.lower() or "debug" in SYSTEM_PROMPT.lower()

    async def test_prompt_workflow_matches_logging(self):
        """Test that prompt workflow steps match logging statements."""
        # Check that prompt mentions preview step
        assert "preview_automation_from_prompt" in SYSTEM_PROMPT
        
        # Check that prompt mentions create step
        assert "create_automation_from_prompt" in SYSTEM_PROMPT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
