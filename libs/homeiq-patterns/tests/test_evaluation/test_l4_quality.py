"""
Tests for L4 Quality Evaluators
Sprint 2: Correctness, Faithfulness, Coherence
Sprint 4: Helpfulness, Conciseness, ResponseRelevance, InstructionFollowing, SystemPromptRuleEvaluator
"""

import pytest
from homeiq_patterns.evaluation.config import PromptRule
from homeiq_patterns.evaluation.evaluators.l4_quality import (
    CoherenceEvaluator,
    ConcisenessEvaluator,
    CorrectnessEvaluator,
    FaithfulnessEvaluator,
    HelpfulnessEvaluator,
    InstructionFollowingEvaluator,
    ResponseRelevanceEvaluator,
    SystemPromptRuleEvaluator,
)
from homeiq_patterns.evaluation.llm_judge import LLMJudge, LLMProvider
from homeiq_patterns.evaluation.models import (
    AgentResponse,
    EvalLevel,
    EvalScope,
    SessionTrace,
    ToolCall,
    UserMessage,
)


class MockProvider(LLMProvider):
    def __init__(self, response: str = ""):
        self._response = response

    async def complete(self, _prompt: str) -> str:
        return self._response


# ---------------------------------------------------------------------------
# CorrectnessEvaluator
# ---------------------------------------------------------------------------


class TestCorrectnessEvaluator:
    @pytest.mark.asyncio
    async def test_perfectly_correct(self):
        provider = MockProvider('{"label": "Perfectly Correct", "explanation": "All data matches."}')
        evaluator = CorrectnessEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="What's the temp?")],
            agent_responses=[AgentResponse(content="It's 72°F.")],
            tool_calls=[ToolCall(tool_name="get_state", result={"temperature": 72})],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Perfectly Correct"
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_partially_correct(self):
        provider = MockProvider('{"label": "Partially Correct", "explanation": "Some data fabricated."}')
        evaluator = CorrectnessEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Status?")],
            agent_responses=[AgentResponse(content="72°F and 45% humidity")],
            tool_calls=[ToolCall(tool_name="get_state", result={"temperature": 72})],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.5

    @pytest.mark.asyncio
    async def test_incorrect(self):
        provider = MockProvider('{"label": "Incorrect", "explanation": "Wrong temperature."}')
        evaluator = CorrectnessEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Temp?")],
            agent_responses=[AgentResponse(content="It's 80°F.")],
            tool_calls=[ToolCall(tool_name="get_state", result={"temperature": 72})],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.passed is False

    def test_name_and_level(self):
        evaluator = CorrectnessEvaluator(llm_judge=LLMJudge(provider=MockProvider()))
        assert evaluator.name == "correctness"
        assert evaluator.level == EvalLevel.QUALITY
        assert evaluator.scope == EvalScope.RESPONSE


# ---------------------------------------------------------------------------
# FaithfulnessEvaluator
# ---------------------------------------------------------------------------


class TestFaithfulnessEvaluator:
    @pytest.mark.asyncio
    async def test_completely_faithful(self):
        provider = MockProvider('{"label": "Completely Yes", "explanation": "Faithful."}')
        evaluator = FaithfulnessEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Turn on lights")],
            agent_responses=[AgentResponse(content="Lights are on.")],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_generally_faithful(self):
        provider = MockProvider('{"label": "Generally Yes", "explanation": "Mostly ok."}')
        evaluator = FaithfulnessEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        assert result.score == 0.75

    @pytest.mark.asyncio
    async def test_unfaithful(self):
        provider = MockProvider('{"label": "Completely No", "explanation": "Hallucinated prefs."}')
        evaluator = FaithfulnessEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.passed is False

    def test_name_and_level(self):
        evaluator = FaithfulnessEvaluator(llm_judge=LLMJudge(provider=MockProvider()))
        assert evaluator.name == "faithfulness"
        assert evaluator.level == EvalLevel.QUALITY


# ---------------------------------------------------------------------------
# CoherenceEvaluator
# ---------------------------------------------------------------------------


class TestCoherenceEvaluator:
    @pytest.mark.asyncio
    async def test_fully_coherent(self):
        provider = MockProvider('{"label": "Completely Yes", "explanation": "Consistent."}')
        evaluator = CoherenceEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Set temp to 72")],
            agent_responses=[AgentResponse(content="Thermostat set to 72°F.")],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_incoherent(self):
        provider = MockProvider('{"label": "Generally No", "explanation": "Contradicts itself."}')
        evaluator = CoherenceEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        assert result.score == 0.25
        assert result.passed is False

    def test_name_and_level(self):
        evaluator = CoherenceEvaluator(llm_judge=LLMJudge(provider=MockProvider()))
        assert evaluator.name == "coherence"
        assert evaluator.level == EvalLevel.QUALITY


# ---------------------------------------------------------------------------
# HelpfulnessEvaluator
# ---------------------------------------------------------------------------


class TestHelpfulnessEvaluator:
    @pytest.mark.asyncio
    async def test_very_helpful(self):
        provider = MockProvider('{"label": "Very Helpful", "explanation": "Clear and actionable."}')
        evaluator = HelpfulnessEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Turn on lights")],
            agent_responses=[AgentResponse(content="Lights are on! Brightness is at 100%. Want to adjust?")],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Very Helpful"

    @pytest.mark.asyncio
    async def test_not_helpful(self):
        provider = MockProvider('{"label": "Not Helpful", "explanation": "Vague and unhelpful."}')
        evaluator = HelpfulnessEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_somewhat_helpful(self):
        provider = MockProvider('{"label": "Somewhat Helpful", "explanation": "OK."}')
        evaluator = HelpfulnessEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        assert result.score == 0.66

    def test_name_and_level(self):
        evaluator = HelpfulnessEvaluator(llm_judge=LLMJudge(provider=MockProvider()))
        assert evaluator.name == "helpfulness"
        assert evaluator.level == EvalLevel.QUALITY


# ---------------------------------------------------------------------------
# ConcisenessEvaluator
# ---------------------------------------------------------------------------


class TestConcisenessEvaluator:
    @pytest.mark.asyncio
    async def test_concise(self):
        provider = MockProvider('{"label": "Concise", "explanation": "Brief and complete."}')
        evaluator = ConcisenessEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Turn on lights")],
            agent_responses=[AgentResponse(content="Done!")],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_not_concise(self):
        provider = MockProvider('{"label": "Not Concise", "explanation": "Too verbose."}')
        evaluator = ConcisenessEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        assert result.score == 0.0

    def test_name_and_level(self):
        evaluator = ConcisenessEvaluator(llm_judge=LLMJudge(provider=MockProvider()))
        assert evaluator.name == "conciseness"
        assert evaluator.level == EvalLevel.QUALITY


# ---------------------------------------------------------------------------
# ResponseRelevanceEvaluator
# ---------------------------------------------------------------------------


class TestResponseRelevanceEvaluator:
    @pytest.mark.asyncio
    async def test_completely_relevant(self):
        provider = MockProvider('{"label": "Completely Yes", "explanation": "On topic."}')
        evaluator = ResponseRelevanceEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="What's the temp?")],
            agent_responses=[AgentResponse(content="It's 72°F.")],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_completely_irrelevant(self):
        provider = MockProvider('{"label": "Completely No", "explanation": "Off topic."}')
        evaluator = ResponseRelevanceEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        assert result.score == 0.0

    def test_name_and_level(self):
        evaluator = ResponseRelevanceEvaluator(llm_judge=LLMJudge(provider=MockProvider()))
        assert evaluator.name == "response_relevance"
        assert evaluator.level == EvalLevel.QUALITY


# ---------------------------------------------------------------------------
# InstructionFollowingEvaluator
# ---------------------------------------------------------------------------


class TestInstructionFollowingEvaluator:
    @pytest.mark.asyncio
    async def test_fully_compliant(self):
        provider = MockProvider('{"label": "Yes", "explanation": "Followed all rules."}')
        evaluator = InstructionFollowingEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Make an automation")],
            agent_responses=[AgentResponse(content="Here's a preview...")],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Yes"

    @pytest.mark.asyncio
    async def test_partial_compliance(self):
        provider = MockProvider('{"label": "Partial", "explanation": "Missed some rules."}')
        evaluator = InstructionFollowingEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        assert result.score == 0.5

    @pytest.mark.asyncio
    async def test_non_compliance(self):
        provider = MockProvider('{"label": "No", "explanation": "Ignored instructions."}')
        evaluator = InstructionFollowingEvaluator(llm_judge=LLMJudge(provider=provider))
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_with_system_prompt(self):
        provider = MockProvider('{"label": "Yes", "explanation": "Followed system prompt."}')
        evaluator = InstructionFollowingEvaluator(
            llm_judge=LLMJudge(provider=provider),
            system_prompt="Always show preview before creating.",
        )
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Create automation")],
            agent_responses=[AgentResponse(content="Here's a preview...")],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0

    def test_name_and_level(self):
        evaluator = InstructionFollowingEvaluator(llm_judge=LLMJudge(provider=MockProvider()))
        assert evaluator.name == "instruction_following"
        assert evaluator.level == EvalLevel.QUALITY


# ---------------------------------------------------------------------------
# SystemPromptRuleEvaluator
# ---------------------------------------------------------------------------


class TestSystemPromptRuleEvaluator:
    # -- path_validation tests --

    @pytest.mark.asyncio
    async def test_path_validation_pass(self):
        rule = PromptRule(
            name="preview_before_execute",
            check_type="path_validation",
            severity="critical",
            tool_sequence=["preview_automation", "create_automation"],
        )
        evaluator = SystemPromptRuleEvaluator(rule=rule)
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(tool_name="preview_automation"),
                ToolCall(tool_name="create_automation"),
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Pass"
        assert evaluator.name == "preview_before_execute"

    @pytest.mark.asyncio
    async def test_path_validation_fail(self):
        rule = PromptRule(
            name="preview_before_execute",
            check_type="path_validation",
            severity="critical",
            tool_sequence=["preview_automation", "create_automation"],
        )
        evaluator = SystemPromptRuleEvaluator(rule=rule)
        session = SessionTrace(
            agent_name="test",
            tool_calls=[
                ToolCall(tool_name="create_automation"),  # Missing preview
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.label == "Fail"
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_path_validation_empty_sequence(self):
        rule = PromptRule(
            name="empty_rule",
            check_type="path_validation",
            severity="info",
        )
        evaluator = SystemPromptRuleEvaluator(rule=rule)
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        assert result.score == 1.0

    # -- response_check tests --

    @pytest.mark.asyncio
    async def test_response_check_no_violation(self):
        rule = PromptRule(
            name="no_markdown_headings",
            check_type="response_check",
            severity="warning",
            pattern=r"^#{1,3}\s",
        )
        evaluator = SystemPromptRuleEvaluator(rule=rule)
        session = SessionTrace(
            agent_name="test",
            agent_responses=[
                AgentResponse(content="Here's your automation preview."),
                AgentResponse(content="Done! Created successfully."),
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Pass"

    @pytest.mark.asyncio
    async def test_response_check_violation(self):
        rule = PromptRule(
            name="no_markdown_headings",
            check_type="response_check",
            severity="warning",
            pattern=r"^#{1,3}\s",
        )
        evaluator = SystemPromptRuleEvaluator(rule=rule)
        session = SessionTrace(
            agent_name="test",
            agent_responses=[
                AgentResponse(content="# Automation Preview\nHere's your preview."),
                AgentResponse(content="Done! Created successfully."),
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.5
        assert result.label == "Fail"
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_response_check_all_violations(self):
        rule = PromptRule(
            name="no_markdown_headings",
            check_type="response_check",
            severity="warning",
            pattern=r"^#{1,3}\s",
        )
        evaluator = SystemPromptRuleEvaluator(rule=rule)
        session = SessionTrace(
            agent_name="test",
            agent_responses=[
                AgentResponse(content="# Bad heading"),
                AgentResponse(content="## Another bad heading"),
            ],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_response_check_no_pattern(self):
        rule = PromptRule(
            name="empty_pattern",
            check_type="response_check",
            severity="info",
        )
        evaluator = SystemPromptRuleEvaluator(rule=rule)
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        assert result.score == 1.0

    # -- llm_judge tests --

    @pytest.mark.asyncio
    async def test_llm_judge_pass(self):
        rule = PromptRule(
            name="no_hallucinated_entities",
            description="Entity IDs must come from context",
            check_type="llm_judge",
            severity="critical",
            labels=["Pass", "Fail"],
        )
        provider = MockProvider('{"label": "Pass", "explanation": "All entities from context."}')
        evaluator = SystemPromptRuleEvaluator(
            rule=rule,
            llm_judge=LLMJudge(provider=provider),
        )
        session = SessionTrace(
            agent_name="test",
            user_messages=[UserMessage(content="Turn on office lights")],
            agent_responses=[AgentResponse(content="Turning on light.office")],
        )
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Pass"

    @pytest.mark.asyncio
    async def test_llm_judge_fail(self):
        rule = PromptRule(
            name="no_hallucinated_entities",
            description="Entity IDs must come from context",
            check_type="llm_judge",
            severity="critical",
            labels=["Pass", "Fail"],
        )
        provider = MockProvider('{"label": "Fail", "explanation": "Hallucinated entity."}')
        evaluator = SystemPromptRuleEvaluator(
            rule=rule,
            llm_judge=LLMJudge(provider=provider),
        )
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.passed is False

    # -- unknown check_type --

    @pytest.mark.asyncio
    async def test_unknown_check_type(self):
        rule = PromptRule(
            name="bad_rule",
            check_type="unknown_type",
            severity="info",
        )
        evaluator = SystemPromptRuleEvaluator(rule=rule)
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert "Unknown" in result.explanation

    # -- evaluator properties --

    def test_name_matches_rule(self):
        rule = PromptRule(name="my_custom_rule", check_type="response_check")
        evaluator = SystemPromptRuleEvaluator(rule=rule)
        assert evaluator.name == "my_custom_rule"
        assert evaluator.level == EvalLevel.QUALITY
        assert evaluator.scope == EvalScope.RESPONSE
