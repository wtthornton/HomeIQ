"""Provider-agnostic LLM response models.

Epic 97: Prompt Caching & Claude Provider
Story 97.1: LLMResponse dataclass for unified provider responses.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolCall:
    """A single tool/function call from the LLM."""

    id: str
    name: str
    arguments: str  # JSON string


@dataclass
class TokenUsage:
    """Token usage breakdown."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    cache_creation_tokens: int = 0
    reasoning_tokens: int = 0


@dataclass
class LLMResponse:
    """Provider-agnostic LLM response."""

    content: str
    tool_calls: list[ToolCall] | None = None
    usage: TokenUsage = field(default_factory=TokenUsage)
    model: str = ""
    provider: str = ""  # "openai" or "anthropic"
    cached_tokens: int = 0
    thinking: str | None = None  # Extended thinking content (Claude only)
