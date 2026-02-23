"""
Agent Evaluation Framework — LLM-as-Judge Engine

Sends session data and a rubric to an LLM and parses the structured
evaluation response.  Supports OpenAI and Anthropic backends via a
provider abstraction.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import SessionTrace

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rubric model
# ---------------------------------------------------------------------------


@dataclass
class JudgeRubric:
    """
    Template for an LLM-judged evaluation.

    Attributes:
        name:           Rubric identifier (e.g. "correctness").
        prompt_template: Jinja2-style prompt with ``{{ var }}`` placeholders.
        output_labels:  Ordered list of label strings the LLM should pick from.
        score_mapping:  Maps each label → float score (0.0 – 1.0).
        examples:       Optional pass/fail examples for few-shot.
    """

    name: str = ""
    prompt_template: str = ""
    output_labels: list[str] = field(default_factory=list)
    score_mapping: dict[str, float] = field(default_factory=dict)
    examples: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> JudgeRubric:
        """Load a rubric from a YAML file."""
        import yaml  # lazy — yaml only needed when loading rubrics

        data = Path(path).read_text(encoding="utf-8")
        parsed = yaml.safe_load(data)
        return cls(
            name=parsed.get("name", ""),
            prompt_template=parsed.get("prompt_template", ""),
            output_labels=parsed.get("output_labels", []),
            score_mapping=parsed.get("score_mapping", {}),
            examples=parsed.get("examples", []),
        )


# ---------------------------------------------------------------------------
# Judge result
# ---------------------------------------------------------------------------


@dataclass
class JudgeResult:
    """Result from a single LLM judge evaluation."""

    score: float = 0.0
    label: str = ""
    explanation: str = ""
    raw_response: str = ""


# ---------------------------------------------------------------------------
# Provider abstraction
# ---------------------------------------------------------------------------


class LLMProvider:
    """Abstract provider interface for LLM calls."""

    async def complete(self, prompt: str) -> str:
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible provider (gpt-4o, gpt-4o-mini, etc.)."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        self.model = model
        self.api_key = api_key

    async def complete(self, prompt: str) -> str:
        import openai  # lazy import

        client = openai.AsyncOpenAI(api_key=self.api_key)
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return response.choices[0].message.content or ""


class AnthropicProvider(LLMProvider):
    """Anthropic provider (claude-sonnet-4-5, etc.)."""

    def __init__(self, model: str = "claude-sonnet-4-5-20250929", api_key: str | None = None):
        self.model = model
        self.api_key = api_key

    async def complete(self, prompt: str) -> str:
        import anthropic  # lazy import

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        response = await client.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text if response.content else ""


# ---------------------------------------------------------------------------
# LLMJudge engine
# ---------------------------------------------------------------------------

# Pre-compiled regex for extracting JSON blocks from LLM responses
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


class LLMJudge:
    """
    Reusable LLM-as-Judge engine.

    Takes a ``SessionTrace`` and a ``JudgeRubric``, renders the prompt,
    calls the LLM, and parses the structured response into a ``JudgeResult``.
    """

    def __init__(
        self,
        provider: LLMProvider | None = None,
        max_retries: int = 2,
    ):
        self.provider = provider or OpenAIProvider()
        self.max_retries = max_retries
        self._compiled_rubrics: dict[str, str] = {}

    # -- public API ---------------------------------------------------------

    async def judge(
        self,
        session: SessionTrace,
        rubric: JudgeRubric,
    ) -> JudgeResult:
        """Evaluate a session against a rubric using an LLM."""
        prompt = self._render_prompt(session, rubric)

        raw_response = ""
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                raw_response = await self.provider.complete(prompt)
                break
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "LLMJudge attempt %d/%d failed: %s",
                    attempt,
                    self.max_retries,
                    exc,
                )

        if not raw_response:
            logger.error("LLMJudge exhausted retries: %s", last_error)
            return JudgeResult(
                score=0.0,
                label="ERROR",
                explanation=f"LLM call failed after {self.max_retries} retries: {last_error}",
                raw_response="",
            )

        return self._parse_response(raw_response, rubric)

    # -- internals ----------------------------------------------------------

    def _render_prompt(self, session: SessionTrace, rubric: JudgeRubric) -> str:
        """Render the rubric prompt template with session data."""
        # Build context variables for template substitution
        user_input = "\n".join(m.content for m in session.user_messages) or "(no user input)"
        agent_response = "\n".join(r.content for r in session.agent_responses) or "(no response)"
        tool_calls = json.dumps(
            [
                {
                    "tool_name": tc.tool_name,
                    "parameters": tc.parameters,
                    "result": tc.result,
                }
                for tc in session.tool_calls
            ],
            indent=2,
            default=str,
        )

        labels_str = ", ".join(rubric.output_labels) if rubric.output_labels else ""

        # Simple {{ var }} replacement (Jinja2-compatible subset)
        prompt = rubric.prompt_template
        prompt = prompt.replace("{{ user_input }}", user_input)
        prompt = prompt.replace("{{ agent_response }}", agent_response)
        prompt = prompt.replace("{{ tool_calls }}", tool_calls)
        prompt = prompt.replace("{{ output_labels }}", labels_str)
        prompt = prompt.replace("{{user_input}}", user_input)
        prompt = prompt.replace("{{agent_response}}", agent_response)
        prompt = prompt.replace("{{tool_calls}}", tool_calls)
        prompt = prompt.replace("{{output_labels}}", labels_str)

        # Append structured output instruction
        prompt += (
            "\n\nRespond with a JSON object containing exactly these keys:\n"
            '- "label": one of [' + labels_str + "]\n"
            '- "explanation": brief justification\n'
        )

        return prompt

    def _parse_response(self, raw: str, rubric: JudgeRubric) -> JudgeResult:
        """Parse the LLM response into a JudgeResult."""
        parsed = self._extract_json(raw)

        label = parsed.get("label", "").strip()
        explanation = parsed.get("explanation", "").strip()

        # Map label → score
        score = rubric.score_mapping.get(label, 0.0)

        # If label not in mapping, try case-insensitive match
        if label and label not in rubric.score_mapping:
            for rubric_label, rubric_score in rubric.score_mapping.items():
                if rubric_label.lower() == label.lower():
                    label = rubric_label
                    score = rubric_score
                    break

        return JudgeResult(
            score=score,
            label=label,
            explanation=explanation,
            raw_response=raw,
        )

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        """Extract a JSON object from LLM output (handles markdown fences)."""
        # Try extracting from ```json ... ``` block
        match = _JSON_BLOCK_RE.search(text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try parsing the whole text as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try finding first { ... } in text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        logger.warning("Could not extract JSON from LLM response: %.200s", text)
        return {}
