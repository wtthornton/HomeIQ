"""
OpenAI Provider Implementation
Uses OpenAI's JSON mode for deterministic schema-valid outputs.
"""

from typing import Dict, List, Optional, Any
import json
import logging
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base import BaseProvider
from ..contracts.models import AutomationPlan, AutomationMetadata

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """
    OpenAI provider using JSON mode for schema-enforced outputs.
    
    Uses OpenAI's response_format={"type": "json_object"} to ensure
    JSON-only responses that can be validated against schema.
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: Model identifier (default: gpt-4o - latest and best model)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._provider_id = "openai"
        logger.info(f"OpenAIProvider initialized with model={model}")
    
    def provider_id(self) -> str:
        return self._provider_id
    
    def model_id(self) -> str:
        return self._model
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    async def generate_json(
        self,
        *,
        schema: Dict[str, Any],
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Generate JSON output using OpenAI's JSON mode.
        
        Uses response_format={"type": "json_object"} to enforce JSON-only responses.
        Validates output against schema before returning.
        
        Args:
            schema: JSON Schema definition
            prompt: User prompt (should include schema requirement)
            tools: Not used (OpenAI JSON mode doesn't support tools)
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            
        Returns:
            Validated JSON dict conforming to schema
            
        Raises:
            ValueError: If output doesn't conform to schema
            RuntimeError: If API call fails
        """
        try:
            # Build system prompt with schema requirement
            system_prompt = f"""You are a JSON generator. You MUST return ONLY valid JSON that conforms to this schema:
{json.dumps(schema, indent=2)}

CRITICAL RULES:
1. Return ONLY valid JSON (no markdown, no code blocks, no explanations)
2. All fields must conform to the schema exactly
3. No extra fields beyond what's defined in the schema
4. All required fields must be present
5. Enum values must match exactly
"""
            
            # User prompt should include the actual request
            user_prompt = prompt
            
            # Use JSON mode for deterministic output
            response = await self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_completion_tokens=max_tokens,  # Use max_completion_tokens for newer models (gpt-4o+)
                response_format={"type": "json_object"}  # JSON mode enforcement
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI API")
            
            # Parse JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON from OpenAI: {e}. Content: {content[:200]}") from e
            
            # Validate against schema (basic validation - full validation in contracts)
            # Check required fields
            required_fields = schema.get("required", [])
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")
            
            # Check no extra fields if additionalProperties is false
            if schema.get("additionalProperties") is False:
                allowed_props = set(schema.get("properties", {}).keys())
                result_props = set(result.keys())
                extra_props = result_props - allowed_props
                if extra_props:
                    raise ValueError(f"Extra fields not allowed: {extra_props}")
            
            logger.info(f"✅ OpenAI generated valid JSON with {len(result)} fields")
            return result
            
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"❌ OpenAI API error: {e}")
            raise RuntimeError(f"OpenAI API call failed: {e}") from e
    
    async def generate_automation_plan(
        self,
        *,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> AutomationPlan:
        """
        Generate AutomationPlan using OpenAI with schema enforcement.
        
        This is a convenience method that:
        1. Loads the automation schema
        2. Calls generate_json with the schema
        3. Validates and returns AutomationPlan
        
        Args:
            prompt: User prompt for automation generation
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            
        Returns:
            Validated AutomationPlan
            
        Raises:
            ValueError: If output doesn't conform to schema
        """
        import os
        import json as json_lib
        from pathlib import Path
        
        # Load automation schema
        schema_path = Path(__file__).parent.parent / "contracts" / "automation.schema.json"
        with open(schema_path) as f:
            schema = json_lib.load(f)
        
        # Generate JSON
        json_result = await self.generate_json(
            schema=schema,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Create metadata
        metadata = AutomationMetadata(
            provider_id=self.provider_id(),
            model_id=self.model_id(),
            prompt_pack_id=None  # Can be set by caller
        )
        
        # Validate and return AutomationPlan
        return AutomationPlan.from_json(
            json_lib.dumps(json_result),
            metadata=metadata
        )

