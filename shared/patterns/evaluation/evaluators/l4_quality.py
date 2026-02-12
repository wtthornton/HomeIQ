"""
L4 Quality Evaluators — Response quality assessment.

Evaluators:
  - CorrectnessEvaluator: Information matches API/tool responses
  - FaithfulnessEvaluator: Response stays true to conversation context
  - CoherenceEvaluator: No self-contradictions
  - HelpfulnessEvaluator: Clear, actionable responses
  - ConcisenessEvaluator: Appropriate response length
  - ResponseRelevanceEvaluator: Addresses user's question
  - InstructionFollowingEvaluator: Follows system prompt
  - SystemPromptRuleEvaluator: Per-rule compliance (3 check modes)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..base_evaluator import QualityEvaluator
from ..config import AgentEvalConfig, PromptRule
from ..llm_judge import JudgeRubric, LLMJudge
from ..models import EvaluationResult, SessionTrace

_RUBRICS_DIR = Path(__file__).resolve().parent.parent / "rubrics"


class _LLMJudgedQualityEvaluator(QualityEvaluator):
    """Base for quality evaluators that delegate to LLMJudge."""

    _rubric_filename: str = ""
    _default_labels: list[str] = []
    _default_score_mapping: dict[str, float] = {}
    _default_prompt: str = ""

    def __init__(
        self,
        llm_judge: LLMJudge | None = None,
        rubric: JudgeRubric | None = None,
    ):
        self._judge = llm_judge or LLMJudge()
        self._rubric = rubric or self._load_rubric()

    async def evaluate(self, session: SessionTrace) -> EvaluationResult:
        result = await self._judge.judge(session, self._rubric)
        return self._result(
            score=result.score,
            label=result.label,
            explanation=result.explanation,
        )

    def _load_rubric(self) -> JudgeRubric:
        rubric_path = _RUBRICS_DIR / self._rubric_filename
        if rubric_path.exists():
            return JudgeRubric.from_yaml(rubric_path)
        return JudgeRubric(
            name=self.name,
            prompt_template=self._default_prompt,
            output_labels=self._default_labels,
            score_mapping=self._default_score_mapping,
        )


# ---------------------------------------------------------------------------
# Sprint 2: Core Quality (Correctness, Faithfulness, Coherence)
# ---------------------------------------------------------------------------


class CorrectnessEvaluator(_LLMJudgedQualityEvaluator):
    """
    L4 — Checks that agent responses match API/tool data (no fabrication).
    """

    name = "correctness"
    _rubric_filename = "correctness.yaml"
    _default_labels = ["Perfectly Correct", "Partially Correct", "Incorrect"]
    _default_score_mapping = {
        "Perfectly Correct": 1.0,
        "Partially Correct": 0.5,
        "Incorrect": 0.0,
    }
    _default_prompt = (
        "Evaluate whether the agent's response contains only information "
        "that is supported by the tool call results. Check for fabricated "
        "data, incorrect numbers, or hallucinated details.\n\n"
        "User input: {{ user_input }}\n"
        "Agent response: {{ agent_response }}\n"
        "Tool calls and results: {{ tool_calls }}\n\n"
        "Is the response factually correct based on the tool results?"
    )


class FaithfulnessEvaluator(_LLMJudgedQualityEvaluator):
    """
    L4 — Checks that the response stays true to conversation context.
    """

    name = "faithfulness"
    _rubric_filename = "faithfulness.yaml"
    _default_labels = ["Completely Yes", "Generally Yes", "Generally No", "Completely No"]
    _default_score_mapping = {
        "Completely Yes": 1.0,
        "Generally Yes": 0.75,
        "Generally No": 0.25,
        "Completely No": 0.0,
    }
    _default_prompt = (
        "Evaluate whether the agent's response is faithful to the "
        "conversation context. Check that the agent does not hallucinate "
        "user preferences, fabricate prior statements, or introduce "
        "information not present in the conversation.\n\n"
        "User input: {{ user_input }}\n"
        "Agent response: {{ agent_response }}\n"
        "Tool calls and results: {{ tool_calls }}\n\n"
        "Is the response faithful to the conversation context?"
    )


class CoherenceEvaluator(_LLMJudgedQualityEvaluator):
    """
    L4 — Checks for self-contradictions and logical consistency.
    """

    name = "coherence"
    _rubric_filename = "coherence.yaml"
    _default_labels = ["Completely Yes", "Generally Yes", "Generally No", "Completely No"]
    _default_score_mapping = {
        "Completely Yes": 1.0,
        "Generally Yes": 0.75,
        "Generally No": 0.25,
        "Completely No": 0.0,
    }
    _default_prompt = (
        "Evaluate whether the agent's response is internally coherent. "
        "Check for self-contradictions, inconsistent numbers, times, or "
        "names, and logical flow.\n\n"
        "User input: {{ user_input }}\n"
        "Agent response: {{ agent_response }}\n"
        "Tool calls and results: {{ tool_calls }}\n\n"
        "Is the response logically coherent?"
    )


# ---------------------------------------------------------------------------
# Sprint 4: Response Quality (Helpfulness, Conciseness, Relevance)
# ---------------------------------------------------------------------------


class HelpfulnessEvaluator(_LLMJudgedQualityEvaluator):
    """
    L4 — Checks whether the response is helpful, actionable, and guides
    the user toward their goal.
    """

    name = "helpfulness"
    _rubric_filename = "helpfulness.yaml"
    _default_labels = ["Very Helpful", "Somewhat Helpful", "Neutral/Mixed", "Not Helpful"]
    _default_score_mapping = {
        "Very Helpful": 1.0,
        "Somewhat Helpful": 0.66,
        "Neutral/Mixed": 0.33,
        "Not Helpful": 0.0,
    }
    _default_prompt = (
        "Evaluate whether the agent's response is helpful to the user. "
        "Consider: Does it present clear options? Does it guide the user "
        "to their next step? Is the information actionable?\n\n"
        "User input: {{ user_input }}\n"
        "Agent response: {{ agent_response }}\n"
        "Tool calls and results: {{ tool_calls }}\n\n"
        "How helpful is the response?"
    )


class ConcisenessEvaluator(_LLMJudgedQualityEvaluator):
    """
    L4 — Checks whether the response is appropriately concise for the
    complexity of the query.
    """

    name = "conciseness"
    _rubric_filename = "conciseness.yaml"
    _default_labels = ["Concise", "Partially Concise", "Not Concise"]
    _default_score_mapping = {
        "Concise": 1.0,
        "Partially Concise": 0.5,
        "Not Concise": 0.0,
    }
    _default_prompt = (
        "Evaluate whether the agent's response is appropriately concise. "
        "A concise response addresses the question without unnecessary "
        "rambling, repetition, or filler. The appropriate length depends "
        "on query complexity.\n\n"
        "User input: {{ user_input }}\n"
        "Agent response: {{ agent_response }}\n\n"
        "Is the response appropriately concise?"
    )


class ResponseRelevanceEvaluator(_LLMJudgedQualityEvaluator):
    """
    L4 — Checks whether the response directly addresses the user's
    question and stays on topic.
    """

    name = "response_relevance"
    _rubric_filename = "response_relevance.yaml"
    _default_labels = ["Completely Yes", "Neutral/Mixed", "Completely No"]
    _default_score_mapping = {
        "Completely Yes": 1.0,
        "Neutral/Mixed": 0.5,
        "Completely No": 0.0,
    }
    _default_prompt = (
        "Evaluate whether the agent's response is relevant to the user's "
        "question. Does it address the user's request directly? Does it "
        "stay on topic without introducing unrelated information?\n\n"
        "User input: {{ user_input }}\n"
        "Agent response: {{ agent_response }}\n"
        "Tool calls and results: {{ tool_calls }}\n\n"
        "Is the response relevant to the user's question?"
    )


# ---------------------------------------------------------------------------
# Sprint 4: InstructionFollowing + SystemPromptRuleEvaluator
# ---------------------------------------------------------------------------


class InstructionFollowingEvaluator(_LLMJudgedQualityEvaluator):
    """
    L4 — Checks whether the agent followed its system prompt instructions.

    Generic instruction-following check — agent-specific rule evaluators
    (like ``NoMarkdownHeadings``) are built via ``SystemPromptRuleEvaluator``.
    """

    name = "instruction_following"
    _rubric_filename = "instruction_following.yaml"
    _default_labels = ["Yes", "Partial", "No"]
    _default_score_mapping = {
        "Yes": 1.0,
        "Partial": 0.5,
        "No": 0.0,
    }
    _default_prompt = (
        "Evaluate whether the agent followed its system prompt instructions "
        "in this conversation. Consider formatting rules, workflow steps, "
        "response structure, and behavioral constraints.\n\n"
        "User input: {{ user_input }}\n"
        "Agent response: {{ agent_response }}\n"
        "Tool calls: {{ tool_calls }}\n\n"
        "Did the agent follow its instructions?"
    )

    def __init__(
        self,
        llm_judge: LLMJudge | None = None,
        rubric: JudgeRubric | None = None,
        system_prompt: str = "",
    ):
        super().__init__(llm_judge=llm_judge, rubric=rubric)
        self._system_prompt = system_prompt

    async def evaluate(self, session: SessionTrace) -> EvaluationResult:
        # If a system prompt is provided, augment the rubric prompt
        if self._system_prompt:
            augmented_rubric = JudgeRubric(
                name=self._rubric.name,
                prompt_template=(
                    f"System prompt instructions:\n{self._system_prompt}\n\n"
                    + self._rubric.prompt_template
                ),
                output_labels=self._rubric.output_labels,
                score_mapping=self._rubric.score_mapping,
            )
            result = await self._judge.judge(session, augmented_rubric)
        else:
            result = await self._judge.judge(session, self._rubric)
        return self._result(
            score=result.score,
            label=result.label,
            explanation=result.explanation,
        )


class SystemPromptRuleEvaluator(QualityEvaluator):
    """
    L4 — Reusable evaluator for individual system prompt rules.

    Supports three ``check_type`` modes:

    - ``path_validation`` — checks tool call sequence (rule-based, no LLM)
    - ``response_check`` — regex or keyword check on response text (rule-based)
    - ``llm_judge`` — sends rule description + session to LLM for assessment

    Instantiated from ``AgentEvalConfig.system_prompt_rules[]`` — one
    instance per rule.  Each rule has ``name``, ``description``,
    ``check_type``, and ``severity`` (critical | warning | info).
    """

    name = "system_prompt_rule"  # Overridden per-instance

    def __init__(
        self,
        rule: PromptRule,
        llm_judge: LLMJudge | None = None,
    ):
        self._rule = rule
        self._judge = llm_judge or LLMJudge()
        # Override name with rule-specific name
        self.name = rule.name

    async def evaluate(self, session: SessionTrace) -> EvaluationResult:
        check_type = self._rule.check_type

        if check_type == "path_validation":
            return self._check_path(session)
        elif check_type == "response_check":
            return self._check_response(session)
        elif check_type == "llm_judge":
            return await self._check_llm(session)
        else:
            return self._result(
                score=0.0,
                label="Error",
                explanation=f"Unknown check_type: {check_type}",
                passed=False,
            )

    def _check_path(self, session: SessionTrace) -> EvaluationResult:
        """Rule-based path validation — check tool call sequence."""
        expected = self._rule.tool_sequence
        if not expected:
            return self._result(
                score=1.0,
                label="Pass",
                explanation=f"Rule '{self._rule.name}': no tool sequence to validate",
            )

        actual = [tc.tool_name for tc in session.tool_calls]

        # Check subsequence: all expected tools appear in order
        exp_idx = 0
        for tool_name in actual:
            if exp_idx < len(expected) and tool_name == expected[exp_idx]:
                exp_idx += 1

        if exp_idx == len(expected):
            return self._result(
                score=1.0,
                label="Pass",
                explanation=f"Rule '{self._rule.name}': tool sequence satisfied",
            )

        return self._result(
            score=0.0,
            label="Fail",
            explanation=(
                f"Rule '{self._rule.name}': expected sequence {expected}, "
                f"got {actual}"
            ),
            passed=False,
        )

    def _check_response(self, session: SessionTrace) -> EvaluationResult:
        """Rule-based response check — regex or keyword on response text.

        Story 1.4: Also checks ``metadata["generated_yaml"]`` when present
        so that the ``yaml_safety_check`` rule still scans the actual YAML
        even after Story 1.3 moved it out of agent responses.
        """
        pattern = self._rule.pattern
        if not pattern:
            return self._result(
                score=1.0,
                label="Pass",
                explanation=f"Rule '{self._rule.name}': no pattern to check",
            )

        texts_to_check: list[str] = []

        # Only scan generated_yaml metadata for safety-related rules
        # (e.g. yaml_safety_check). Other response_check rules should
        # only inspect agent response text — generated_yaml is produced
        # by the deterministic compile step, not by the LLM.
        if self._rule.name == "yaml_safety_check":
            generated_yaml = session.metadata.get("generated_yaml", "")
            if generated_yaml:
                texts_to_check.append(generated_yaml)

        # Check agent responses
        for resp in session.agent_responses:
            texts_to_check.append(resp.content)

        violations = 0
        total = len(texts_to_check)
        for text in texts_to_check:
            if re.search(pattern, text, re.MULTILINE):
                violations += 1

        if violations == 0:
            return self._result(
                score=1.0,
                label="Pass",
                explanation=f"Rule '{self._rule.name}': no violations found",
            )

        score = 1.0 - (violations / total) if total > 0 else 0.0
        return self._result(
            score=score,
            label="Fail",
            explanation=(
                f"Rule '{self._rule.name}': pattern matched in "
                f"{violations}/{total} texts checked"
            ),
            passed=False,
        )

    async def _check_llm(self, session: SessionTrace) -> EvaluationResult:
        """LLM-judged rule check — sends rule description + session to LLM."""
        labels = self._rule.labels or ["Pass", "Fail"]
        score_mapping = {labels[0]: 1.0}
        if len(labels) > 1:
            score_mapping[labels[-1]] = 0.0
        # Fill intermediate labels evenly
        for i, lbl in enumerate(labels[1:-1], start=1):
            score_mapping[lbl] = 1.0 - (i / (len(labels) - 1))

        rubric = JudgeRubric(
            name=self._rule.name,
            prompt_template=(
                f"Evaluate compliance with this system prompt rule:\n"
                f"Rule: {self._rule.name}\n"
                f"Description: {self._rule.description}\n\n"
                "User input: {{ user_input }}\n"
                "Agent response: {{ agent_response }}\n"
                "Tool calls: {{ tool_calls }}\n\n"
                f"Did the agent comply with this rule?"
            ),
            output_labels=labels,
            score_mapping=score_mapping,
        )

        result = await self._judge.judge(session, rubric)
        return self._result(
            score=result.score,
            label=result.label,
            explanation=result.explanation,
        )
