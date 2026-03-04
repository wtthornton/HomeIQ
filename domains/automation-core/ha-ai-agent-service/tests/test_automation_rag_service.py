"""Tests for Automation RAG Service (Story 9: Comprehensive Sports Keyword Coverage)"""

import pytest
from src.services.automation_rag_service import SPORTS_KEYWORDS, AutomationRAGService


@pytest.fixture
def automation_rag_service():
    """Create AutomationRAGService instance."""
    return AutomationRAGService()


class TestSportsIntentMatching:
    """Verify key phrases match sports intent for RAG retrieval."""

    @pytest.mark.parametrize("prompt", [
        "Lakers score lights",
        "PGA birdie automation",
        "Super Bowl lights when Seahawks score",
        "Flash lights when my team scores a touchdown",
        "NBA playoff lights",
        "MLB home run notification",
        "NHL hat trick celebration",
        "World Cup goal lights",
        "UFC fight started automation",
        "F1 lap notification",
        "Tennis set won lights",
        "March Madness bracket lights",
        "game day kickoff flash",
        "team colors when Chiefs win",
    ])
    def test_sports_prompts_match(self, automation_rag_service: AutomationRAGService, prompt: str):
        """Key phrases from various sports/leagues should match sports intent."""
        assert automation_rag_service._matches_sports_intent(prompt), f"Expected match for: {prompt}"

    @pytest.mark.parametrize("prompt", [
        "Turn on the living room lights",
        "Adjust thermostat to 72",
        "Lock the front door",
        "Play music in the kitchen",
        "Open the garage door",
    ])
    def test_non_sports_prompts_no_match(self, automation_rag_service: AutomationRAGService, prompt: str):
        """Non-sports prompts should not match sports intent."""
        assert not automation_rag_service._matches_sports_intent(prompt), f"Expected no match for: {prompt}"

    def test_empty_prompt_no_match(self, automation_rag_service: AutomationRAGService):
        """Empty prompt should not match."""
        assert not automation_rag_service._matches_sports_intent("")

    def test_case_insensitive(self, automation_rag_service: AutomationRAGService):
        """Matching should be case-insensitive."""
        assert automation_rag_service._matches_sports_intent("SUPER BOWL LIGHTS")
        assert automation_rag_service._matches_sports_intent("NFL Score Flash")


class TestGetAutomationContext:
    """Verify get_automation_context returns corpus when matched."""

    @pytest.mark.asyncio
    async def test_returns_context_for_sports_prompt(self, automation_rag_service: AutomationRAGService):
        """Sports prompts should return RAG context with corpus."""
        result = await automation_rag_service.get_automation_context("Lakers score lights")
        assert "AUTOMATION RAG CONTEXT" in result
        assert "Sports/Team Tracker patterns" in result
        assert len(result) > 100

    @pytest.mark.asyncio
    async def test_returns_empty_for_non_sports_prompt(self, automation_rag_service: AutomationRAGService):
        """Non-sports prompts should return empty string."""
        result = await automation_rag_service.get_automation_context("Turn on kitchen lights")
        assert result == ""


class TestSportsKeywordsCoverage:
    """Verify SPORTS_KEYWORDS covers required leagues and terms."""

    def test_major_leagues_present(self):
        """All ha-teamtracker major leagues should be in keywords."""
        required = ("nfl", "nba", "mlb", "nhl", "mls", "ncaa")
        for league in required:
            assert league in SPORTS_KEYWORDS, f"Missing league: {league}"

    def test_college_and_alternate_leagues_present(self):
        """College and alternate leagues should be in keywords."""
        required = ("ncaaf", "ncaam", "wnba", "xfl", "pga", "ufc", "epl", "f1")
        for league in required:
            assert league in SPORTS_KEYWORDS, f"Missing league: {league}"

    def test_sport_specific_scoring_terms_present(self):
        """Sport-specific scoring terms should be in keywords."""
        required = ("touchdown", "goal", "home run", "basket", "inning", "birdie")
        for term in required:
            assert term in SPORTS_KEYWORDS, f"Missing term: {term}"
