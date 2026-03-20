"""Tests for system prompt safety section — Epic 93 Story 93.4."""

from src.prompts.system_prompt import SYSTEM_PROMPT


class TestSystemPromptSafety:
    """93.4 AC: System prompt Section 7 reflects enforcement."""

    def test_blocked_entities_section_present(self):
        assert "Blocked Entities" in SYSTEM_PROMPT

    def test_locks_described_as_blocked(self):
        assert "NOT provided in your context" in SYSTEM_PROMPT
        assert "cannot be used in automations" in SYSTEM_PROMPT

    def test_redirect_message_present(self):
        assert "created directly in Home Assistant" in SYSTEM_PROMPT

    def test_lock_no_longer_requires_confirmation(self):
        """Old language said 'Require explicit confirmation' for locks — should be gone."""
        # The old text was: "Require explicit confirmation, no bulk operations, add warning"
        assert "Require explicit confirmation" not in SYSTEM_PROMPT

    def test_cover_still_has_warning(self):
        """Covers (garage doors) should still be present with caution, not blocked."""
        assert "Caution" in SYSTEM_PROMPT
        assert "Garage doors" in SYSTEM_PROMPT or "covers" in SYSTEM_PROMPT.lower()

    def test_safety_classification_table_present(self):
        assert "Safety Classification" in SYSTEM_PROMPT
        assert "Blocked" in SYSTEM_PROMPT
