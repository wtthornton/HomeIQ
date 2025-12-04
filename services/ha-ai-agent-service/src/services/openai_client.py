"""
OpenAI Client Service
Epic AI-20 Story AI20.1: OpenAI Client Integration with 2025 best practices

Provides async OpenAI API client with:
- Retry logic with exponential backoff
- Rate limiting handling (429 errors)
- Token counting and budget management
- Error handling for API failures
"""

import logging
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
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
    OpenAI API client with 2025 best practices.

    Features:
    - Async operations
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
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is required")

        self.settings = settings
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout,
            max_retries=0,  # We handle retries ourselves with tenacity
        )
        self.model = settings.openai_model
        self.max_tokens = settings.openai_max_tokens
        self.temperature = settings.openai_temperature

        # Token tracking
        self.total_tokens_used = 0
        self.total_requests = 0
        self.total_errors = 0

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ChatCompletion:
        """
        Create a chat completion with OpenAI API.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            tools: Optional list of tool schemas for function calling
            tool_choice: Optional tool choice mode ('auto', 'none', or tool name)
            max_tokens: Optional max tokens (overrides config default)
            temperature: Optional temperature (overrides config default)
        
        Returns:
            ChatCompletion response from OpenAI
        """
        # Verify messages before sending
        if not messages:
            logger.error("❌ CRITICAL: No messages provided to OpenAI API!")
            raise ValueError("Messages list is empty")
        
        # Verify system message is first
        system_msg = messages[0] if messages else None
        if not system_msg or system_msg.get("role") != "system":
            logger.error(
                f"❌ CRITICAL: System message missing or not first! "
                f"First message: {system_msg}, Total messages: {len(messages)}"
            )
            raise ValueError("System message must be first message")
        
        system_content = system_msg.get("content", "")
        logger.info(
            f"[OpenAI API] Sending {len(messages)} messages to OpenAI. "
            f"System message: {len(system_content)} chars, "
            f"Contains 'CRITICAL': {'CRITICAL' in system_content}, "
            f"Contains 'HOME ASSISTANT CONTEXT': {'HOME ASSISTANT CONTEXT' in system_content}, "
            f"Tools: {len(tools) if tools else 0}"
        )
        
        self.total_requests += 1

        @retry(
            retry=retry_if_exception_type((OpenAIRateLimitError, Exception)),
            stop=stop_after_attempt(self.settings.openai_max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True,
        )
        async def _make_request():
            """Internal function to make API request with retry logic"""
            # Verify messages before sending
            if not messages:
                logger.error("❌ CRITICAL: No messages provided to OpenAI API!")
                raise ValueError("Messages list is empty")
            
            # Verify system message is first
            system_msg = messages[0] if messages else None
            if not system_msg or system_msg.get("role") != "system":
                logger.error(
                    f"❌ CRITICAL: System message missing or not first! "
                    f"First message: {system_msg}, Total messages: {len(messages)}"
                )
                raise ValueError("System message must be first message")
            
            system_content = system_msg.get("content", "")
            logger.info(
                f"[OpenAI API] Sending {len(messages)} messages to OpenAI. "
                f"System message: {len(system_content)} chars, "
                f"Contains 'CRITICAL': {'CRITICAL' in system_content}, "
                f"Contains 'HOME ASSISTANT CONTEXT': {'HOME ASSISTANT CONTEXT' in system_content}, "
                f"Tools: {len(tools) if tools else 0}"
            )
            
            # Prepare request parameters
            # GPT-5.1 and newer models use max_completion_tokens instead of max_tokens
            request_params: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or self.temperature,
            }
            
            # Use max_completion_tokens for GPT-5.1, max_tokens for older models
            if self.model.startswith("gpt-5"):
                request_params["max_completion_tokens"] = max_tokens or self.max_tokens
            else:
                request_params["max_tokens"] = max_tokens or self.max_tokens

            # Add tools if provided
            if tools:
                request_params["tools"] = tools
                if tool_choice:
                    request_params["tool_choice"] = tool_choice

            logger.debug(
                f"OpenAI API request: model={self.model}, "
                f"messages={len(messages)}, tools={len(tools) if tools else 0}"
            )

            try:
                # Make API call
                response = await self.client.chat.completions.create(**request_params)

                # Track token usage
                if response.usage:
                    self.total_tokens_used += response.usage.total_tokens
                    logger.info(
                        f"OpenAI API response: {response.usage.total_tokens} tokens "
                        f"(prompt: {response.usage.prompt_tokens}, "
                        f"completion: {response.usage.completion_tokens})"
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
            # Only count error once after all retries exhausted
            self.total_errors += 1
            raise

    async def chat_completion_simple(
        self, system_prompt: str, user_message: str
    ) -> str:
        """
        Simple chat completion helper (no function calling).

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
        return response.choices[0].message.content or ""

    def get_token_stats(self) -> dict[str, Any]:
        """
        Get token usage statistics.

        Returns:
            Dict with token usage stats
        """
        return {
            "total_tokens_used": self.total_tokens_used,
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
        self.total_requests = 0
        self.total_errors = 0
        logger.info("OpenAI client statistics reset")

