"""
OpenAI Client for YAML Generation (2025 Patterns)

Epic 39, Story 39.10: Automation Service Foundation
Async client for generating Home Assistant automation YAML using OpenAI.
"""

import logging
from typing import Any

from openai import AsyncOpenAI, APIError, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import settings

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    Async client for generating automation YAML via OpenAI API.
    
    Features:
    - Async OpenAI API calls
    - Automatic retry logic
    - Token usage tracking
    - Proper error handling
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key (defaults to settings.openai_api_key)
            model: Model to use (defaults to settings.openai_model)
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model or "gpt-4o-mini"
        
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=self.api_key)
            logger.info(f"OpenAI client initialized with model={self.model}")
        
        # Usage tracking
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIError, RateLimitError)),
        reraise=True
    )
    async def generate_yaml(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate automation YAML from prompt.
        
        Args:
            prompt: Prompt describing the automation
            temperature: Sampling temperature (default: 0.1 for deterministic YAML)
            max_tokens: Maximum tokens in response
        
        Returns:
            Generated YAML string
        
        Raises:
            ValueError: If API key not configured
            APIError: If OpenAI API call fails
        """
        if not self.client:
            raise ValueError("OpenAI API key not configured")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Home Assistant automation expert. Generate valid Home Assistant automation YAML only, no explanations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Track usage
            if response.usage:
                self.total_tokens_used += response.usage.total_tokens
            
            # Extract YAML from response
            yaml_content = response.choices[0].message.content or ""
            
            # Clean up YAML (remove markdown code blocks if present)
            if yaml_content.startswith("```"):
                lines = yaml_content.split("\n")
                # Remove first line (```yaml) and last line (```)
                yaml_content = "\n".join(lines[1:-1])
            
            logger.debug(f"Generated YAML ({len(yaml_content)} chars)")
            return yaml_content.strip()
        
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating YAML: {e}")
            raise

    async def generate_suggestion_description(
        self,
        pattern_data: dict[str, Any],
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """
        Generate human-readable suggestion description from pattern data.
        
        Args:
            pattern_data: Pattern data dictionary
            temperature: Sampling temperature (default: 0.7 for creativity)
            max_tokens: Maximum tokens in response
        
        Returns:
            Generated description string
        """
        if not self.client:
            raise ValueError("OpenAI API key not configured")
        
        # Build prompt from pattern data
        prompt = f"Generate a brief, user-friendly description for this automation pattern: {pattern_data}"
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates clear, concise automation descriptions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Track usage
            if response.usage:
                self.total_tokens_used += response.usage.total_tokens
            
            description = response.choices[0].message.content or ""
            return description.strip()
        
        except APIError as e:
            logger.error(f"OpenAI API error generating description: {e}")
            raise

    def get_usage_stats(self) -> dict[str, Any]:
        """
        Get token usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        return {
            "total_tokens": self.total_tokens_used,
            "total_cost_usd": self.total_cost_usd,
            "model": self.model
        }

    def reset_usage_stats(self):
        """Reset usage statistics."""
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
        logger.debug("Usage statistics reset")

