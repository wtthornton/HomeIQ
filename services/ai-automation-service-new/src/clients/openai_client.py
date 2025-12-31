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
        entity_context: dict[str, Any] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate automation YAML from prompt.
        
        DEPRECATED: Use generate_structured_plan() instead (Epic 51, Story 51.8).
        This method is kept for backward compatibility.
        R2: Entity context is included to ensure LLM uses only real entities.
        
        Args:
            prompt: Prompt describing the automation
            entity_context: Optional entity context (R2: entities grouped by domain)
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
        
        # R2: Build entity context section for system prompt
        entity_context_section = ""
        if entity_context and entity_context.get("entities"):
            entity_context_section = "\n\nCRITICAL: You MUST use ONLY the entity IDs listed below. Do NOT create fictional entity IDs.\n"
            entities_by_domain = entity_context["entities"]
            for domain, entity_list in sorted(entities_by_domain.items()):
                if not entity_list:
                    continue
                limited = entity_list[:30]
                entity_ids = [e.get("entity_id", "") for e in limited if e.get("entity_id")]
                if entity_ids:
                    entity_context_section += f"{domain.upper()}: {', '.join(entity_ids)}\n"
        
        system_prompt = f"""You are a Home Assistant automation expert. Generate valid Home Assistant automation YAML only, no explanations.
{entity_context_section}"""
        
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
        entity_context: dict[str, Any] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> dict[str, Any]:
        """
        Generate structured automation plan (JSON) from prompt.
        
        Epic 51, Story 51.8: Structured Plan Generation
        R2: Entity context is included to ensure LLM uses only real entities.
        
        LLM generates structured JSON/object instead of YAML directly.
        This plan is then parsed into AutomationSpec and rendered to YAML server-side.
        
        Args:
            prompt: Prompt describing the automation
            entity_context: Optional entity context (R2: entities grouped by domain)
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
        
        # R2: Add entity context to system prompt
        entity_context_section = ""
        if entity_context and entity_context.get("entities"):
            entity_context_section = "\n\nCRITICAL: You MUST use ONLY the entity IDs listed below. Do NOT create fictional entity IDs.\n"
            entities_by_domain = entity_context["entities"]
            for domain, entity_list in sorted(entities_by_domain.items()):
                if not entity_list:
                    continue
                limited = entity_list[:30]
                entity_ids = [e.get("entity_id", "") for e in limited if e.get("entity_id")]
                if entity_ids:
                    entity_context_section += f"{domain.upper()}: {', '.join(entity_ids)}\n"
        
        system_prompt = f"""You are a Home Assistant automation expert. Generate a structured JSON plan for the automation described by the user.

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
{entity_context_section}

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

    async def generate_homeiq_automation_json(
        self,
        prompt: str,
        homeiq_context: dict[str, Any] | None = None,
        entity_context: dict[str, Any] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 3000
    ) -> dict[str, Any]:
        """
        Generate HomeIQ JSON Automation format from prompt.
        
        Uses structured output with JSON schema to generate comprehensive
        HomeIQ automation JSON including metadata, device context, and patterns.
        
        R2: Entity context is included in system prompt to ensure LLM uses only real entities.
        
        Args:
            prompt: Prompt describing the automation
            homeiq_context: Optional HomeIQ context (patterns, devices, areas)
            entity_context: Optional entity context (R2: entities grouped by domain)
            temperature: Sampling temperature (default: 0.1 for deterministic output)
            max_tokens: Maximum tokens in response
        
        Returns:
            Dictionary containing HomeIQ JSON Automation
        
        Raises:
            ValueError: If API key not configured or JSON cannot be parsed
            APIError: If OpenAI API call fails
        """
        if not self.client:
            raise ValueError("OpenAI API key not configured")
        
        # Build context section
        context_section = ""
        if homeiq_context:
            if "patterns" in homeiq_context:
                context_section += f"\n\nPatterns Available:\n{json.dumps(homeiq_context['patterns'], indent=2)}"
            if "devices" in homeiq_context:
                context_section += f"\n\nDevices Available:\n{json.dumps(homeiq_context['devices'], indent=2)}"
            if "areas" in homeiq_context:
                context_section += f"\n\nAreas Available:\n{json.dumps(homeiq_context['areas'], indent=2)}"
        
        # R2: Add entity context to system prompt
        entity_context_section = ""
        if entity_context and entity_context.get("entities"):
            entity_context_section = "\n\nCRITICAL ENTITY REQUIREMENTS:\n"
            entity_context_section += "You MUST use ONLY the entity IDs listed below. Do NOT create fictional entity IDs.\n"
            entity_context_section += "If you need an entity that doesn't exist in the list, use the closest matching entity.\n"
            entity_context_section += "Entity IDs are in format: domain.entity_name (e.g., light.office, binary_sensor.motion)\n\n"
            
            entities_by_domain = entity_context["entities"]
            for domain, entity_list in sorted(entities_by_domain.items()):
                if not entity_list:
                    continue
                # Limit to top 30 per domain to avoid token limits
                limited = entity_list[:30]
                entity_ids = [e.get("entity_id", "") for e in limited if e.get("entity_id")]
                if entity_ids:
                    entity_context_section += f"{domain.upper()}: {', '.join(entity_ids)}\n"
                    if len(entity_list) > 30:
                        entity_context_section += f"  ... and {len(entity_list) - 30} more {domain} entities\n"
        
        # HomeIQ JSON schema (simplified for LLM - full validation happens server-side)
        system_prompt = f"""You are a Home Assistant automation expert generating HomeIQ JSON Automation format.

Generate a comprehensive JSON automation that includes:
1. Core automation fields: id (optional), alias (required), description, triggers, conditions, actions, mode, initial_state
2. HomeIQ metadata: created_by, created_at, pattern_id (if from pattern), suggestion_id, confidence_score, safety_score, use_case, complexity
3. Device context: device_ids, entity_ids, device_types, area_ids, device_capabilities
4. Pattern context (if applicable): pattern_type, pattern_id, pattern_metadata, confidence, occurrences
5. Safety checks: requires_confirmation, critical_devices, time_constraints, safety_warnings
6. Energy impact: estimated_power_w, estimated_daily_kwh, peak_hours
7. Dependencies: list of automation IDs this depends on
8. Tags: list of tags for categorization

Return ONLY valid JSON matching the HomeIQ Automation schema. Include all relevant HomeIQ metadata and context.
{context_section}
{entity_context_section}

Important:
- Use exact entity IDs and device IDs from the context provided
- Set use_case to one of: "energy", "comfort", "security", "convenience"
- Set complexity to one of: "low", "medium", "high"
- Include device_capabilities if devices have special features (effects, presets, modes)
- Set safety_checks.requires_confirmation=true for critical devices (locks, security systems)
- Calculate energy_impact if automation involves power-consuming devices
- Include pattern_context if automation is generated from a pattern

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
            automation_json = json.loads(json_content)
            
            logger.debug(f"Generated HomeIQ JSON automation: {automation_json.get('alias', 'unknown')}")
            return automation_json
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse HomeIQ JSON: {e}")
            raise ValueError(f"Invalid JSON in HomeIQ automation response: {e}")
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating HomeIQ JSON: {e}")
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

