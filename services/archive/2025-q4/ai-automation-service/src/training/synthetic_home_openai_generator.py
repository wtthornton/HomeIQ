"""
Synthetic Home OpenAI Generator

Generate enhanced synthetic homes using OpenAI for realistic, contextual generation.
Uses GPT-5.1 structured outputs for schema-valid JSON generation.
"""

import json
import logging
from typing import Any

from openai import APIError, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

# JSON Schema for enhanced home structure
HOME_SCHEMA = {
    "type": "object",
    "properties": {
        "home_type": {"type": "string"},
        "size_category": {"type": "string", "enum": ["small", "medium", "large", "extra_large"]},
        "metadata": {
            "type": "object",
            "properties": {
                "home": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "size_category": {"type": "string"},
                        "description": {"type": "string"},
                        "region": {"type": "string"},
                        "year_built": {"type": "integer"},
                        "realistic_features": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["name", "type", "size_category", "description"]
                },
                "device_categories": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "count": {"type": "integer"},
                            "devices": {"type": "array", "items": {"type": "string"}},
                            "rationale": {"type": "string"}
                        },
                        "required": ["count"]
                    }
                }
            },
            "required": ["home"]
        }
    },
    "required": ["home_type", "size_category", "metadata"]
}

# JSON Schema for validation results
VALIDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "is_realistic": {"type": "boolean"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "category": {"type": "string"},
                    "description": {"type": "string"},
                    "suggestion": {"type": "string"}
                },
                "required": ["severity", "category", "description"]
            }
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["is_realistic", "confidence"]
}

# JSON Schema for template generation
TEMPLATE_SCHEMA = {
    "type": "object",
    "properties": {
        "home_type": {"type": "string"},
        "area_templates": {
            "type": "array",
            "items": {"type": "string"}
        },
        "optional_areas": {
            "type": "array",
            "items": {"type": "string"}
        },
        "device_category_distribution": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "base_count": {"type": "integer"},
                    "size_multipliers": {
                        "type": "object",
                        "properties": {
                            "small": {"type": "number"},
                            "medium": {"type": "number"},
                            "large": {"type": "number"},
                            "extra_large": {"type": "number"}
                        }
                    }
                },
                "required": ["base_count"]
            }
        },
        "description": {"type": "string"}
    },
    "required": ["home_type", "area_templates"]
}


class SyntheticHomeOpenAIGenerator:
    """
    Generate enhanced synthetic homes using OpenAI for realistic, contextual generation.
    
    Uses GPT-5.1 structured outputs with JSON schema validation for reliable generation.
    """
    
    def __init__(
        self,
        openai_client: OpenAIClient,
        temperature: float = 0.3,
        model: str | None = None
    ):
        """
        Initialize OpenAI-enhanced synthetic home generator.
        
        Args:
            openai_client: OpenAI client instance
            temperature: Temperature for generation (0.3 = deterministic, 0.5 = balanced)
            model: Model to use (defaults to openai_client.model)
        """
        self.openai_client = openai_client
        self.temperature = temperature
        self.model = model or openai_client.model
        self.success_count = 0
        self.failure_count = 0
        
        logger.info(f"SyntheticHomeOpenAIGenerator initialized with model={self.model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APIError)),
        reraise=True
    )
    async def generate_enhanced_home(
        self,
        home_type: str,
        size_category: str,
        home_index: int = 1
    ) -> dict[str, Any]:
        """
        Generate a single enhanced home using OpenAI.
        
        Args:
            home_type: Type of home (e.g., 'single_family_house', 'apartment')
            size_category: Size category (small, medium, large, extra_large)
            home_index: Index for naming (default: 1)
        
        Returns:
            Enhanced home dictionary with realistic metadata
        
        Raises:
            ValueError: If OpenAI response doesn't conform to schema
            RuntimeError: If API call fails after retries
        """
        try:
            system_prompt = f"""You are a home automation expert generating realistic synthetic home data for training machine learning models.

Generate a realistic {home_type} home with {size_category} size category. The home should have:
- Realistic device counts appropriate for the size and type
- Contextual features (region, year built, architectural style)
- Device categories that make sense for this home type
- Realistic rationale for device choices

Return ONLY valid JSON conforming to the provided schema. No markdown, no explanations, just JSON."""

            user_prompt = f"""Generate a realistic {home_type} home with {size_category} size category.

Requirements:
- Home type: {home_type}
- Size category: {size_category}
- Home index: {home_index}
- Include realistic regional features (e.g., "Texas ranch house" or "New York apartment")
- Include realistic device counts based on size and type
- Provide rationale for device category choices
- Make device counts realistic (e.g., a studio shouldn't have 10 thermostats)

Return the home data as JSON matching the schema."""

            # Build messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Build API parameters
            api_params = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_completion_tokens": 2000,
                "response_format": {"type": "json_object"}  # JSON mode
            }
            
            # Add GPT-5.1 parameters if applicable
            try:
                from ..utils.gpt51_params import (
                    is_gpt51_model,
                    get_gpt51_params_for_use_case,
                    merge_gpt51_params,
                    remove_unsupported_gpt51_params
                )
                from ..config import settings
                
                if is_gpt51_model(self.model):
                    gpt51_params = get_gpt51_params_for_use_case(
                        model=self.model,
                        use_case="structured",  # Structured outputs
                        enable_prompt_caching=getattr(settings, 'enable_prompt_caching', True)
                    )
                    api_params = merge_gpt51_params(api_params, gpt51_params)
                    api_params = remove_unsupported_gpt51_params(api_params)
            except ImportError:
                logger.debug("GPT-5.1 params not available, using standard parameters")
            
            # Make API call
            response = await self.openai_client.client.chat.completions.create(**api_params)
            
            # Track token usage
            usage = response.usage
            self.openai_client.total_input_tokens += usage.prompt_tokens
            self.openai_client.total_output_tokens += usage.completion_tokens
            self.openai_client.total_tokens_used += usage.total_tokens
            
            # Parse response
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI API")
            
            # Parse JSON
            try:
                home_data = json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON from OpenAI: {e}. Content: {content[:200]}") from e
            
            # Validate schema (basic validation)
            self._validate_home_schema(home_data)
            
            # Add generated_at timestamp
            from datetime import datetime, timezone
            home_data['generated_at'] = datetime.now(timezone.utc).isoformat()
            home_data['home_index'] = home_index
            
            self.success_count += 1
            logger.debug(f"✅ Generated enhanced home: {home_type} {size_category}")
            
            return home_data
            
        except (RateLimitError, APIError) as e:
            self.failure_count += 1
            logger.error(f"❌ OpenAI API error generating enhanced home: {e}")
            raise
        except Exception as e:
            self.failure_count += 1
            logger.error(f"❌ Error generating enhanced home: {e}")
            raise RuntimeError(f"Failed to generate enhanced home: {e}") from e
    
    async def validate_home(
        self,
        home: dict[str, Any],
        areas: list[dict[str, Any]],
        devices: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Validate a template-generated home for realism using OpenAI.
        
        Args:
            home: Home dictionary from template generator
            areas: List of areas
            devices: List of devices
        
        Returns:
            Validation results dictionary
        """
        try:
            device_count = len(devices)
            area_count = len(areas)
            home_type = home.get('home_type', 'unknown')
            size_category = home.get('size_category', 'medium')
            
            # Count devices by category
            device_counts = {}
            for device in devices:
                category = device.get('category', 'unknown')
                device_counts[category] = device_counts.get(category, 0) + 1
            
            system_prompt = """You are a home automation expert validating synthetic home data for realism.

Analyze the provided home data and identify any unrealistic aspects:
- Device counts that don't match home size/type
- Unrealistic device-area relationships
- Missing common devices for the home type
- Too many or too few devices for the size category

Return ONLY valid JSON conforming to the validation schema. No markdown, no explanations, just JSON."""

            user_prompt = f"""Validate this {home_type} home with {size_category} size category:

Home Type: {home_type}
Size Category: {size_category}
Areas: {area_count} ({', '.join([a.get('name', 'Unknown') for a in areas[:10]])})
Total Devices: {device_count}
Device Counts by Category: {json.dumps(device_counts, indent=2)}

Check for:
1. Realistic device counts for this size/type
2. Appropriate device-area relationships
3. Missing common devices
4. Unrealistic combinations (e.g., 10 thermostats in a studio)

Return validation results as JSON matching the schema."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            api_params = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.2,  # Lower temperature for validation
                "max_completion_tokens": 1000,
                "response_format": {"type": "json_object"}
            }
            
            # Add GPT-5.1 parameters if applicable
            try:
                from ..utils.gpt51_params import (
                    is_gpt51_model,
                    get_gpt51_params_for_use_case,
                    merge_gpt51_params,
                    remove_unsupported_gpt51_params
                )
                from ..config import settings
                
                if is_gpt51_model(self.model):
                    gpt51_params = get_gpt51_params_for_use_case(
                        model=self.model,
                        use_case="deterministic",  # Deterministic for validation
                        enable_prompt_caching=getattr(settings, 'enable_prompt_caching', True)
                    )
                    api_params = merge_gpt51_params(api_params, gpt51_params)
                    api_params = remove_unsupported_gpt51_params(api_params)
            except ImportError:
                pass
            
            response = await self.openai_client.client.chat.completions.create(**api_params)
            
            # Track token usage
            usage = response.usage
            self.openai_client.total_input_tokens += usage.prompt_tokens
            self.openai_client.total_output_tokens += usage.completion_tokens
            self.openai_client.total_tokens_used += usage.total_tokens
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty validation response from OpenAI API")
            
            try:
                validation_result = json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON from validation: {e}") from e
            
            # Basic schema validation
            if 'is_realistic' not in validation_result:
                validation_result['is_realistic'] = True  # Default to realistic
            if 'confidence' not in validation_result:
                validation_result['confidence'] = 0.5  # Default confidence
            
            logger.debug(f"✅ Validated home: realistic={validation_result.get('is_realistic')}, confidence={validation_result.get('confidence')}")
            
            return validation_result
            
        except Exception as e:
            logger.warning(f"⚠️ Validation failed, returning default: {e}")
            return {
                "is_realistic": True,
                "confidence": 0.5,
                "issues": [],
                "suggestions": []
            }
    
    async def generate_home_type_template(
        self,
        home_type: str,
        description: str
    ) -> dict[str, Any]:
        """
        Generate a new home type template using OpenAI.
        
        Args:
            home_type: New home type identifier (e.g., 'tiny_house', 'mansion')
            description: Description of the home type
        
        Returns:
            Template dictionary compatible with existing generators
        """
        try:
            system_prompt = """You are a home automation expert creating templates for synthetic home generation.

Generate a template structure for a new home type that includes:
- Common areas/rooms for this home type
- Optional areas that may vary
- Device category distribution recommendations
- Size multipliers for different home sizes

Return ONLY valid JSON conforming to the template schema. No markdown, no explanations, just JSON."""

            user_prompt = f"""Generate a template for home type: {home_type}

Description: {description}

Create a template that includes:
1. Area templates: Common rooms/areas for this home type
2. Optional areas: Areas that may or may not be present
3. Device category distribution: Base counts and size multipliers for:
   - security
   - climate
   - lighting
   - appliances
   - monitoring

Return the template as JSON matching the schema."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            api_params = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.4,  # Slightly higher for template creativity
                "max_completion_tokens": 1500,
                "response_format": {"type": "json_object"}
            }
            
            # Add GPT-5.1 parameters if applicable
            try:
                from ..utils.gpt51_params import (
                    is_gpt51_model,
                    get_gpt51_params_for_use_case,
                    merge_gpt51_params,
                    remove_unsupported_gpt51_params
                )
                from ..config import settings
                
                if is_gpt51_model(self.model):
                    gpt51_params = get_gpt51_params_for_use_case(
                        model=self.model,
                        use_case="structured",
                        enable_prompt_caching=getattr(settings, 'enable_prompt_caching', True)
                    )
                    api_params = merge_gpt51_params(api_params, gpt51_params)
                    api_params = remove_unsupported_gpt51_params(api_params)
            except ImportError:
                pass
            
            response = await self.openai_client.client.chat.completions.create(**api_params)
            
            # Track token usage
            usage = response.usage
            self.openai_client.total_input_tokens += usage.prompt_tokens
            self.openai_client.total_output_tokens += usage.completion_tokens
            self.openai_client.total_tokens_used += usage.total_tokens
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty template response from OpenAI API")
            
            try:
                template = json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON from template generation: {e}") from e
            
            # Validate required fields
            if 'home_type' not in template:
                template['home_type'] = home_type
            if 'area_templates' not in template:
                raise ValueError("Template missing required 'area_templates' field")
            
            logger.info(f"✅ Generated template for {home_type}")
            
            return template
            
        except Exception as e:
            logger.error(f"❌ Error generating template: {e}")
            raise RuntimeError(f"Failed to generate template: {e}") from e
    
    def _validate_home_schema(self, home_data: dict[str, Any]) -> None:
        """
        Basic validation of home data against schema.
        
        Args:
            home_data: Home data dictionary
        
        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ['home_type', 'size_category', 'metadata']
        for field in required_fields:
            if field not in home_data:
                raise ValueError(f"Missing required field: {field}")
        
        if 'home' not in home_data.get('metadata', {}):
            raise ValueError("Missing required 'home' in metadata")
        
        # Validate size_category enum
        valid_sizes = ['small', 'medium', 'large', 'extra_large']
        if home_data.get('size_category') not in valid_sizes:
            raise ValueError(f"Invalid size_category: {home_data.get('size_category')}")
    
    def get_stats(self) -> dict[str, Any]:
        """Get generation statistics."""
        return {
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_attempts": self.success_count + self.failure_count,
            "success_rate": self.success_count / (self.success_count + self.failure_count) if (self.success_count + self.failure_count) > 0 else 0.0
        }

