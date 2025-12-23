"""
OpenAI Client for YAML Generation (2025 Patterns)

Epic 39, Story 39.10: Automation Service Foundation
Epic 51, Story 51.8: Structured Plan Generation
Async client for generating Home Assistant automation YAML using OpenAI.
"""

import json
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
        
        DEPRECATED: Use generate_structured_plan() instead (Epic 51, Story 51.8).
        This method is kept for backward compatibility.
        
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

    async def generate_structured_plan(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> dict[str, Any]:
        """
        Generate structured automation plan (JSON) from prompt.
        
        Epic 51, Story 51.8: Structured Plan Generation
        
        LLM generates structured JSON/object instead of YAML directly.
        This plan is then parsed into AutomationSpec and rendered to YAML server-side.
        
        Args:
            prompt: Prompt describing the automation
            temperature: Sampling temperature (default: 0.1 for deterministic output)
            max_tokens: Maximum tokens in response
        
        Returns:
            Dictionary containing structured automation plan
        
        Raises:
            ValueError: If API key not configured or plan cannot be parsed
            APIError: If OpenAI API call fails
        """
        if not self.client:
            raise ValueError("OpenAI API key not configured")
        
        # Structured plan JSON schema
        plan_schema = {
            "type": "object",
            "properties": {
                "alias": {"type": "string", "description": "Automation name"},
                "description": {"type": "string", "description": "What this automation does"},
                "trigger": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "platform": {"type": "string"},
                            "entity_id": {"type": ["string", "array"]},
                            "at": {"type": "string"},
                            "to": {"type": "string"},
                            "from": {"type": "string"}
                        },
                        "required": ["platform"]
                    }
                },
                "action": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "service": {"type": "string"},
                            "target": {"type": "object"},
                            "data": {"type": "object"}
                        },
                        "required": ["service"]
                    }
                },
                "condition": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "condition": {"type": "string"},
                            "entity_id": {"type": ["string", "array"]},
                            "state": {"type": "string"}
                        }
                    }
                },
                "mode": {"type": "string", "enum": ["single", "restart", "queued", "parallel"]},
                "initial_state": {"type": "boolean"},
                "max_exceeded": {"type": "string", "enum": ["silent", "warning", "error"]},
                "tags": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["alias", "trigger", "action"]
        }
        
        system_prompt = """You are a Home Assistant automation expert. Generate a structured JSON plan for the automation described by the user.

Return ONLY valid JSON matching this schema:
- alias: string (required) - Automation name
- description: string (optional) - What this automation does
- trigger: array (required) - List of triggers, each with platform and trigger-specific fields
- action: array (required) - List of actions, each with service and action-specific fields
- condition: array (optional) - List of conditions
- mode: string (optional) - "single", "restart", "queued", or "parallel" (default: "single")
- initial_state: boolean (optional) - Whether automation starts enabled (default: true)
- max_exceeded: string (optional) - "silent", "warning", or "error" (default: "silent")
- tags: array (optional) - List of tags

Return ONLY the JSON object, no explanations or markdown code blocks."""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}  # Force JSON output
            )
            
            # Track usage
            if response.usage:
                self.total_tokens_used += response.usage.total_tokens
            
            # Extract JSON from response
            json_content = response.choices[0].message.content or "{}"
            
            # Parse JSON
            plan_dict = json.loads(json_content)
            
            logger.debug(f"Generated structured plan: {plan_dict.get('alias', 'unknown')}")
            return plan_dict
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON plan: {e}")
            raise ValueError(f"Invalid JSON in plan response: {e}")
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating structured plan: {e}")
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

