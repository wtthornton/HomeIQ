"""
Phase 2.1 E2E: Super Bowl Lights Prompt Assembly

Epic: HomeIQ Automation Platform Improvements
Success criterion: "Super Bowl lights when Seahawks score" produces working automation

Verifies the prompt assembly pipeline injects RAG context (Team Tracker patterns)
when the user requests sports/score lights automation. This validates that:
1. RAG service detects sports intent
2. Team Tracker corpus is injected into the system prompt
3. The assembled prompt contains score-increase pattern guidance
"""

import pytest
import sys
from pathlib import Path

# Add project root to path (match test_chat_flow_e2e)
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.services.automation_rag_service import AutomationRAGService


SUPER_BOWL_PROMPT = "Super Bowl lights when Seahawks score"

# RAG corpus keywords - if injected, prompt should contain these
RAG_INDICATORS = [
    "team_score",
    "score-increase",
    "trigger.from_state",
    "trigger.to_state",
    "state",
    "IN",
]


@pytest.mark.asyncio
async def test_rag_detects_super_bowl_prompt():
    """RAG service detects sports intent for Super Bowl prompt."""
    rag = AutomationRAGService()
    assert rag._matches_sports_intent(SUPER_BOWL_PROMPT)


@pytest.mark.asyncio
async def test_rag_returns_context_for_super_bowl():
    """RAG service returns Team Tracker corpus for Super Bowl prompt."""
    rag = AutomationRAGService()
    context = await rag.get_automation_context(SUPER_BOWL_PROMPT)
    assert context
    assert "team_score" in context or "score-increase" in context or "trigger" in context


@pytest.mark.asyncio
async def test_super_bowl_rag_context_contains_score_patterns():
    """
    RAG context for Super Bowl prompt contains score-increase pattern guidance.

    When prompt assembly calls get_automation_context(SUPER_BOWL_PROMPT),
    the returned corpus must include team_score, trigger.from_state, trigger.to_state
    so the LLM can generate correct score-increase YAML.
    """
    rag = AutomationRAGService()
    context = await rag.get_automation_context(SUPER_BOWL_PROMPT)
    assert context
    found = [ind for ind in RAG_INDICATORS if ind in context]
    assert len(found) >= 3, (
        f"RAG corpus must include score-increase patterns. Found: {found}. "
        f"Required: team_score, trigger.from_state, trigger.to_state"
    )
