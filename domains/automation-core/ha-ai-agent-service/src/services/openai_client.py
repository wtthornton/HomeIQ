"""
OpenAI Client Service
Epic AI-20 Story AI20.1: OpenAI Client Integration

Provides async OpenAI API client with:
- Retry logic with exponential backoff
- Rate limiting handling (429 errors)
- Token counting and budget management
- Error handling for API failures

Migrated to Responses API (Feb 2026):
- client.responses.create() replaces client.chat.completions.create()
- System messages passed as `instructions` parameter
- User/assistant messages passed as `input` items
- Response parsed from `output` items instead of `choices[0].message`
"""

import logging
from typing import Any

from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import Settings

logger = logging.getLogger(__name__)


class OpenAIError(Exception):
    """Base exception for OpenAI client errors"""

    pass


class OpenAIRateLimitError(OpenAIError):
    """Raised when rate limit is exceeded"""

    pass


class OpenAITokenBudgetExceededError(OpenAIError):
    """Raised when token budget is exceeded"""

    pass


class OpenAIClient:
    """
    OpenAI API client with async support.

    Features:
    - Async operations via Responses API
    - Retry logic with exponential backoff
    - Rate limiting handling
    - Token counting and budget management
    - Comprehensive error handling
    """

    def __init__(self, settings: Settings):
        """
        Initialize OpenAI client.

        Args:
            settings: Application settings with OpenAI configuration
        """
        if not settings.openai_api_key or not settings.openai_api_key.get_secret_value():
            raise ValueError("OpenAI API key is required")

        self.settings = settings
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.openai_timeout,
            max_retries=0,  # We handle retries ourselves with tenacity
        )
        self.model = settings.openai_model
        self.max_tokens = settings.openai_max_tokens
        self.temperature = settings.openai_temperature
        self.reasoning_effort = getattr(settings, "openai_reasoning_effort", "high")

        # Token tracking
        self.total_tokens_used = 0
        self.total_reasoning_tokens = 0
        self.total_requests = 0
        self.total_errors = 0

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        _tool_choice: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Any:
        """
        Create a response using the OpenAI Responses API.

        Accepts the same message-based interface for backward compatibility,
        internally converts to Responses API format.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            tools: Optional list of tool schemas for function calling
            tool_choice: Ignored (Responses API auto-detects tool usage)
            max_tokens: Optional max tokens (overrides config default)
            temperature: Optional temperature (overrides config default)

        Returns:
            Response object from OpenAI Responses API
        """
        # Verify messages before sending
        if not messages:
            logger.error("CRITICAL: No messages provided to OpenAI API!")
            raise ValueError("Messages list is empty")

        # Verify system message is first
        system_msg = messages[0] if messages else None
        if not system_msg or system_msg.get("role") != "system":
            logger.error(
                f"CRITICAL: System message missing or not first! "
                f"First message: {system_msg}, Total messages: {len(messages)}"
            )
            raise ValueError("System message must be first message")

        system_content = system_msg.get("content", "")
        logger.info(
            f"[OpenAI API] Sending {len(messages)} messages to OpenAI. "
            f"System message: {len(system_content)} chars, "
            f"Contains 'YAML Deployment Assistant': {'YAML Deployment Assistant' in system_content}, "
            f"Contains 'HOME ASSISTANT CONTEXT': {'HOME ASSISTANT CONTEXT' in system_content}, "
            f"Tools: {len(tools) if tools else 0}"
        )

        self.total_requests += 1

        # Use settings from config (set via environment variables)
        effective_model = self.model
        effective_reasoning = self.reasoning_effort
        effective_max_tokens = max_tokens or self.max_tokens
        effective_temperature = temperature or self.temperature

        @retry(
            retry=retry_if_exception_type((OpenAIRateLimitError, Exception)),
            stop=stop_after_attempt(self.settings.openai_max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True,
        )
        async def _make_request(
            model: str = effective_model,
            reasoning_effort: str | None = effective_reasoning,
            req_max_tokens: int = effective_max_tokens,
            req_temperature: float = effective_temperature,
        ):
            """Internal function to make API request with retry logic"""
            # Extract system message as instructions, rest as input
            instructions = system_content
            input_items = _messages_to_input(messages[1:])

            # Prepare request parameters for Responses API
            request_params: dict[str, Any] = {
                "model": model,
                "instructions": instructions,
                "input": input_items,
                "store": False,  # Privacy: don't store responses
            }

            # GPT-5.x reasoning models: use max_output_tokens and reasoning config
            if model.startswith("gpt-5"):
                request_params["max_output_tokens"] = req_max_tokens
                is_reasoning_model = "mini" in model or model >= "gpt-5.2"
                if is_reasoning_model:
                    # Reasoning models don't support temperature (only default 1)
                    if reasoning_effort and not model.startswith("gpt-5.1"):
                        request_params["reasoning"] = {"effort": reasoning_effort}
                else:
                    # Non-reasoning GPT-5.x models support temperature
                    request_params["temperature"] = req_temperature
            else:
                request_params["max_output_tokens"] = req_max_tokens
                request_params["temperature"] = req_temperature

            # Add tools if provided
            if tools:
                request_params["tools"] = tools

            logger.debug(
                f"OpenAI API request: model={model}, "
                f"reasoning_effort={reasoning_effort}, "
                f"input_items={len(input_items)}, tools={len(tools) if tools else 0}"
            )

            try:
                # Make Responses API call
                response = await self.client.responses.create(**request_params)

                # Track token usage
                if response.usage:
                    input_tokens = getattr(response.usage, "input_tokens", 0)
                    output_tokens = getattr(response.usage, "output_tokens", 0)
                    total = input_tokens + output_tokens
                    self.total_tokens_used += total

                    # Track reasoning tokens if available
                    output_details = getattr(response.usage, "output_tokens_details", None)
                    reasoning_count = (
                        getattr(output_details, "reasoning_tokens", 0)
                        if output_details else 0
                    )
                    if reasoning_count:
                        self.total_reasoning_tokens += reasoning_count
                    logger.info(
                        f"OpenAI API response: {total} tokens "
                        f"(input: {input_tokens}, "
                        f"output: {output_tokens}"
                        f"{f', reasoning: {reasoning_count}' if reasoning_count else ''})"
                    )

                return response

            except Exception as e:
                error_msg = str(e).lower()

                # Handle rate limiting (429 errors)
                if "rate limit" in error_msg or "429" in error_msg:
                    logger.warning("OpenAI rate limit exceeded, will retry")
                    raise OpenAIRateLimitError(f"Rate limit exceeded: {e}") from e

                # Handle token budget errors
                if "token" in error_msg and ("budget" in error_msg or "limit" in error_msg):
                    logger.error("OpenAI token budget exceeded")
                    raise OpenAITokenBudgetExceededError(f"Token budget exceeded: {e}") from e

                # Handle other errors
                logger.error(f"OpenAI API error: {e}", exc_info=True)
                raise OpenAIError(f"OpenAI API error: {e}") from e

        try:
            return await _make_request()
        except (OpenAIRateLimitError, OpenAITokenBudgetExceededError, OpenAIError):
            # Count error after all retries exhausted
            self.total_errors += 1
            raise

    async def chat_completion_simple(
        self, system_prompt: str, user_message: str
    ) -> str:
        """
        Simple completion helper (no function calling).

        Args:
            system_prompt: System prompt message
            user_message: User message

        Returns:
            Assistant response content as string
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        response = await self.chat_completion(messages)
        return response.output_text or ""

    def get_token_stats(self) -> dict[str, Any]:
        """
        Get token usage statistics.

        Returns:
            Dict with token usage stats
        """
        return {
            "total_tokens_used": self.total_tokens_used,
            "total_reasoning_tokens": self.total_reasoning_tokens,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "average_tokens_per_request": (
                self.total_tokens_used / self.total_requests
                if self.total_requests > 0
                else 0
            ),
        }

    def reset_stats(self) -> None:
        """Reset token usage statistics."""
        self.total_tokens_used = 0
        self.total_reasoning_tokens = 0
        self.total_requests = 0
        self.total_errors = 0
        logger.info("OpenAI client statistics reset")


def _messages_to_input(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Chat Completions message format to Responses API input items.

    Args:
        messages: List of message dicts (excluding system message).

    Returns:
        List of input items for the Responses API.
    """
    input_items: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "user":
            input_items.append({
                "type": "message",
                "role": "user",
                "content": content,
            })
        elif role == "assistant":
            # Assistant messages with tool calls need special handling
            tool_calls = msg.get("tool_calls")
            if content:
                input_items.append({
                    "type": "message",
                    "role": "assistant",
                    "content": content,
                })
            if tool_calls:
                for tc in tool_calls:
                    func = tc.get("function", tc)
                    input_items.append({
                        "type": "function_call",
                        "name": func.get("name", ""),
                        "arguments": func.get("arguments", "{}"),
                        "call_id": tc.get("id", ""),
                    })
        elif role == "tool_call":
            # Responses API function_call item passed through from chat loop
            fc = msg.get("_function_call")
            if fc:
                input_items.append({
                    "type": "function_call",
                    "name": getattr(fc, "name", ""),
                    "arguments": getattr(fc, "arguments", "{}"),
                    "call_id": getattr(fc, "call_id", ""),
                })
        elif role == "tool":
            # Tool result messages
            input_items.append({
                "type": "function_call_output",
                "call_id": msg.get("tool_call_id", ""),
                "output": content if isinstance(content, str) else str(content),
            })

    return input_items
