"""
Tests for E1.S4: LLM-as-Judge Engine (shared/patterns/evaluation/llm_judge.py)
"""


import pytest
from homeiq_patterns.evaluation.llm_judge import (
    JudgeRubric,
    LLMJudge,
    LLMProvider,
)
from homeiq_patterns.evaluation.models import (
    AgentResponse,
    SessionTrace,
    ToolCall,
    UserMessage,
)

# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------


class MockProvider(LLMProvider):
    """Returns a pre-configured response."""

    def __init__(self, response: str = ""):
        self._response = response
        self.call_count = 0
        self.last_prompt: str = ""

    async def complete(self, prompt: str) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        return self._response


class FailingProvider(LLMProvider):
    """Raises on every call."""

    def __init__(self, error: Exception | None = None):
        self._error = error or RuntimeError("API error")
        self.call_count = 0

    async def complete(self, _prompt: str) -> str:
        self.call_count += 1
        raise self._error


class FailThenSucceedProvider(LLMProvider):
    """Fails N times, then succeeds."""

    def __init__(self, fail_count: int, success_response: str):
        self._fail_count = fail_count
        self._success_response = success_response
        self.call_count = 0

    async def complete(self, _prompt: str) -> str:
        self.call_count += 1
        if self.call_count <= self._fail_count:
            raise RuntimeError(f"Fail #{self.call_count}")
        return self._success_response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_rubric() -> JudgeRubric:
    return JudgeRubric(
        name="correctness",
        prompt_template=(
            "Evaluate the agent response for correctness.\n\n"
            "User input: {{ user_input }}\n"
            "Agent response: {{ agent_response }}\n"
            "Tool calls: {{ tool_calls }}\n\n"
            "Choose one of: {{ output_labels }}"
        ),
        output_labels=["Perfectly Correct", "Partially Correct", "Incorrect"],
        score_mapping={
            "Perfectly Correct": 1.0,
            "Partially Correct": 0.5,
            "Incorrect": 0.0,
        },
    )


@pytest.fixture
def sample_session() -> SessionTrace:
    return SessionTrace(
        agent_name="test-agent",
        user_messages=[UserMessage(content="Turn on the living room lights")],
        agent_responses=[AgentResponse(content="I've turned on the living room lights.")],
        tool_calls=[
            ToolCall(
                tool_name="call_service",
                parameters={"entity_id": "light.living_room", "action": "turn_on"},
                result={"success": True},
            )
        ],
    )


# ---------------------------------------------------------------------------
# Tests: JudgeRubric
# ---------------------------------------------------------------------------


class TestJudgeRubric:
    def test_create_minimal(self):
        rubric = JudgeRubric(name="test")
        assert rubric.name == "test"
        assert rubric.output_labels == []

    def test_create_full(self, sample_rubric):
        assert sample_rubric.name == "correctness"
        assert len(sample_rubric.output_labels) == 3
        assert sample_rubric.score_mapping["Perfectly Correct"] == 1.0


# ---------------------------------------------------------------------------
# Tests: LLMJudge — prompt rendering
# ---------------------------------------------------------------------------


class TestPromptRendering:
    @pytest.mark.asyncio
    async def test_renders_user_input(self, sample_session, sample_rubric):
        provider = MockProvider(response='{"label": "Perfectly Correct", "explanation": "ok"}')
        judge = LLMJudge(provider=provider)
        await judge.judge(sample_session, sample_rubric)
        assert "Turn on the living room lights" in provider.last_prompt

    @pytest.mark.asyncio
    async def test_renders_agent_response(self, sample_session, sample_rubric):
        provider = MockProvider(response='{"label": "Perfectly Correct", "explanation": "ok"}')
        judge = LLMJudge(provider=provider)
        await judge.judge(sample_session, sample_rubric)
        assert "I've turned on the living room lights" in provider.last_prompt

    @pytest.mark.asyncio
    async def test_renders_tool_calls(self, sample_session, sample_rubric):
        provider = MockProvider(response='{"label": "Perfectly Correct", "explanation": "ok"}')
        judge = LLMJudge(provider=provider)
        await judge.judge(sample_session, sample_rubric)
        assert "call_service" in provider.last_prompt
        assert "light.living_room" in provider.last_prompt

    @pytest.mark.asyncio
    async def test_renders_output_labels(self, sample_session, sample_rubric):
        provider = MockProvider(response='{"label": "Perfectly Correct", "explanation": "ok"}')
        judge = LLMJudge(provider=provider)
        await judge.judge(sample_session, sample_rubric)
        assert "Perfectly Correct" in provider.last_prompt
        assert "Incorrect" in provider.last_prompt

    @pytest.mark.asyncio
    async def test_handles_no_space_in_template_vars(self, sample_session):
        rubric = JudgeRubric(
            name="nospace",
            prompt_template="Input: {{user_input}} Response: {{agent_response}}",
            output_labels=["Yes", "No"],
            score_mapping={"Yes": 1.0, "No": 0.0},
        )
        provider = MockProvider(response='{"label": "Yes", "explanation": "ok"}')
        judge = LLMJudge(provider=provider)
        await judge.judge(sample_session, rubric)
        assert "Turn on the living room lights" in provider.last_prompt


# ---------------------------------------------------------------------------
# Tests: LLMJudge — response parsing
# ---------------------------------------------------------------------------


class TestResponseParsing:
    @pytest.mark.asyncio
    async def test_parse_clean_json(self, sample_session, sample_rubric):
        provider = MockProvider(
            response='{"label": "Perfectly Correct", "explanation": "All correct."}'
        )
        judge = LLMJudge(provider=provider)
        result = await judge.judge(sample_session, sample_rubric)
        assert result.score == 1.0
        assert result.label == "Perfectly Correct"
        assert result.explanation == "All correct."

    @pytest.mark.asyncio
    async def test_parse_json_in_markdown_fence(self, sample_session, sample_rubric):
        provider = MockProvider(
            response='```json\n{"label": "Partially Correct", "explanation": "Mostly ok."}\n```'
        )
        judge = LLMJudge(provider=provider)
        result = await judge.judge(sample_session, sample_rubric)
        assert result.score == 0.5
        assert result.label == "Partially Correct"

    @pytest.mark.asyncio
    async def test_parse_json_embedded_in_text(self, sample_session, sample_rubric):
        provider = MockProvider(
            response='Here is my evaluation:\n{"label": "Incorrect", "explanation": "Wrong."}\nEnd.'
        )
        judge = LLMJudge(provider=provider)
        result = await judge.judge(sample_session, sample_rubric)
        assert result.score == 0.0
        assert result.label == "Incorrect"

    @pytest.mark.asyncio
    async def test_case_insensitive_label_matching(self, sample_session, sample_rubric):
        provider = MockProvider(
            response='{"label": "perfectly correct", "explanation": "ok"}'
        )
        judge = LLMJudge(provider=provider)
        result = await judge.judge(sample_session, sample_rubric)
        assert result.score == 1.0
        assert result.label == "Perfectly Correct"  # normalized

    @pytest.mark.asyncio
    async def test_unknown_label_scores_zero(self, sample_session, sample_rubric):
        provider = MockProvider(
            response='{"label": "Unknown Label", "explanation": "hmm"}'
        )
        judge = LLMJudge(provider=provider)
        result = await judge.judge(sample_session, sample_rubric)
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_unparseable_response(self, sample_session, sample_rubric):
        provider = MockProvider(response="I cannot evaluate this.")
        judge = LLMJudge(provider=provider)
        result = await judge.judge(sample_session, sample_rubric)
        assert result.score == 0.0
        assert result.label == ""


# ---------------------------------------------------------------------------
# Tests: LLMJudge — retry logic
# ---------------------------------------------------------------------------


class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_retries_on_failure(self, sample_session, sample_rubric):
        provider = FailThenSucceedProvider(
            fail_count=1,
            success_response='{"label": "Perfectly Correct", "explanation": "ok"}',
        )
        judge = LLMJudge(provider=provider, max_retries=3)
        result = await judge.judge(sample_session, sample_rubric)
        assert result.score == 1.0
        assert provider.call_count == 2

    @pytest.mark.asyncio
    async def test_exhausted_retries_returns_error(self, sample_session, sample_rubric):
        provider = FailingProvider()
        judge = LLMJudge(provider=provider, max_retries=2)
        result = await judge.judge(sample_session, sample_rubric)
        assert result.score == 0.0
        assert result.label == "ERROR"
        assert "failed after 2 retries" in result.explanation
        assert provider.call_count == 2


# ---------------------------------------------------------------------------
# Tests: LLMJudge._extract_json
# ---------------------------------------------------------------------------


class TestExtractJson:
    def test_plain_json(self):
        result = LLMJudge._extract_json('{"label": "Yes"}')
        assert result["label"] == "Yes"

    def test_fenced_json(self):
        text = '```json\n{"label": "No"}\n```'
        result = LLMJudge._extract_json(text)
        assert result["label"] == "No"

    def test_json_in_text(self):
        text = 'Evaluation: {"label": "Yes", "explanation": "good"} Done.'
        result = LLMJudge._extract_json(text)
        assert result["label"] == "Yes"

    def test_no_json(self):
        result = LLMJudge._extract_json("No JSON here.")
        assert result == {}
