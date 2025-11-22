"""
OpenAI Client for Automation Suggestion Generation

Uses GPT-4o to convert detected patterns into natural language
automation suggestions with valid Home Assistant YAML.

**Model:** GPT-4o (latest and best model)
**Temperature:** 0.7 (balanced creativity + consistency)
**Typical Cost:** Varies based on GPT-4o pricing

**Complete Documentation:**
See implementation/analysis/AI_AUTOMATION_CALL_TREE_INDEX.md for:
- Complete prompt templates (time-of-day, co-occurrence, anomaly)
- API call flow and examples
- Token usage and cost analysis
- Response parsing strategies
- Error handling and retry logic

**Prompt Templates:**
- Time-of-Day: Device activates consistently at specific time
- Co-Occurrence: Two devices frequently used together
- Anomaly: Unusual activity detection (future)
"""

import logging
import re
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..utils.token_counter import count_message_tokens, get_token_breakdown
from .cost_tracker import CostTracker

logger = logging.getLogger(__name__)

# Import settings for prompt caching (lazy import to avoid circular dependency)
def _get_settings():
    try:
        from ..config import settings
        return settings
    except ImportError:
        return None


class AutomationSuggestion(BaseModel):
    """Structured output for automation suggestion"""
    alias: str = Field(description="Automation name/alias")
    description: str = Field(description="User-friendly description")
    automation_yaml: str = Field(description="Valid Home Assistant automation YAML")
    rationale: str = Field(description="Explanation of why this automation makes sense")
    category: str = Field(description="Category: energy, comfort, security, convenience")
    priority: str = Field(description="Priority: high, medium, low")
    confidence: float = Field(description="Pattern confidence score")


class OpenAIClient:
    """Client for generating automation suggestions via OpenAI API"""

    def __init__(self, api_key: str, model: str = "gpt-4o", enable_token_counting: bool = True):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o - latest and best model for accuracy)
            enable_token_counting: Enable token counting before API calls (default: True)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.api_key = api_key  # Store API key for creating new client instances
        self.model = model
        self.total_tokens_used = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.last_usage = None  # Store last token usage for debug panel
        self._token_counter_enabled = enable_token_counting

        # Phase 5: Endpoint-level tracking (in-memory)
        self.endpoint_stats: dict[str, dict[str, Any]] = {}  # endpoint_name -> {tokens, cost, calls}

        logger.info(f"OpenAI client initialized with model={model}")

    def _parse_automation_response(self, llm_response: str, pattern: dict) -> AutomationSuggestion:
        """
        Parse LLM response into structured AutomationSuggestion.
        
        Args:
            llm_response: Raw text response from OpenAI
            pattern: Original pattern (for fallback values)
        
        Returns:
            AutomationSuggestion object
        """
        # Extract components from response
        alias = self._extract_alias(llm_response) or "AI Suggested Automation"
        description = self._extract_description(llm_response) or "Automation based on detected pattern"
        yaml_content = self._extract_yaml(llm_response) or self._generate_fallback_yaml(pattern)
        rationale = self._extract_rationale(llm_response) or "Based on observed usage patterns"
        category = self._extract_category(llm_response) or self._infer_category(pattern)
        priority = self._extract_priority(llm_response) or "medium"

        return AutomationSuggestion(
            alias=alias,
            description=description,
            automation_yaml=yaml_content,
            rationale=rationale,
            category=category,
            priority=priority,
            confidence=pattern.get('confidence', 0.0)
        )

    def _extract_alias(self, text: str) -> str | None:
        """Extract alias from LLM response"""
        # Look for 'alias: "..."' in YAML block
        match = re.search(r'alias:\s*["\']?([^"\'\n]+)["\']?', text, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_description(self, text: str) -> str | None:
        """Extract description from LLM response"""
        match = re.search(r'description:\s*["\']?([^"\'\n]+)["\']?', text, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_yaml(self, text: str) -> str | None:
        """Extract YAML block from LLM response"""
        # Look for YAML code block
        match = re.search(r'```(?:yaml)?\n(.*?)\n```', text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Fallback: Look for alias: as start of YAML
        lines = text.split('\n')
        yaml_lines = []
        in_yaml = False

        for line in lines:
            if line.strip().startswith('alias:'):
                in_yaml = True

            if in_yaml:
                yaml_lines.append(line)

                # Stop at RATIONALE or CATEGORY markers
                if any(marker in line.upper() for marker in ['RATIONALE:', 'CATEGORY:', 'PRIORITY:']):
                    break

        return '\n'.join(yaml_lines).strip() if yaml_lines else None

    def _extract_rationale(self, text: str) -> str | None:
        """Extract rationale explanation from LLM response"""
        match = re.search(r'RATIONALE:\s*(.+?)(?:CATEGORY:|PRIORITY:|$)', text, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else None

    def _extract_category(self, text: str) -> str | None:
        """Extract category from LLM response"""
        match = re.search(r'CATEGORY:\s*(\w+)', text, re.IGNORECASE)
        if match:
            category = match.group(1).lower()
            if category in ['energy', 'comfort', 'security', 'convenience']:
                return category
        return None

    def _extract_priority(self, text: str) -> str | None:
        """Extract priority from LLM response"""
        match = re.search(r'PRIORITY:\s*(\w+)', text, re.IGNORECASE)
        if match:
            priority = match.group(1).lower()
            if priority in ['high', 'medium', 'low']:
                return priority
        return None

    def _infer_category(self, pattern: dict) -> str:
        """
        Infer category from pattern and device type.
        
        Args:
            pattern: Pattern dictionary
        
        Returns:
            Category string
        """
        device_id = pattern.get('device_id', '').lower()

        # Simple heuristics based on device type
        if any(keyword in device_id for keyword in ['light', 'switch']):
            return 'convenience'
        elif any(keyword in device_id for keyword in ['climate', 'thermostat', 'temperature', 'hvac']):
            return 'comfort'
        elif any(keyword in device_id for keyword in ['alarm', 'lock', 'door', 'camera', 'motion']):
            return 'security'
        elif any(keyword in device_id for keyword in ['energy', 'power', 'electricity']):
            return 'energy'
        else:
            return 'convenience'

    def _parse_description_response(self, text: str) -> dict:
        """
        Parse LLM description response into structured format.
        
        Args:
            text: Raw description text from OpenAI
        
        Returns:
            Dictionary with title, description, rationale, category, priority
        """
        # Initialize with defaults
        result = {
            'title': None,
            'description': text.strip(),
            'rationale': '',
            'category': 'convenience',
            'priority': 'medium'
        }

        # Try to extract structured fields if present
        # Look for title/heading pattern
        title_match = re.search(r'^#?\s*(.+?)(?::|\n)', text, re.MULTILINE)
        if title_match:
            result['title'] = title_match.group(1).strip()

        # Look for rationale section
        rationale_match = re.search(r'(?:RATIONALE|WHY|REASON):\s*(.+?)(?:\n\n|$)', text, re.IGNORECASE | re.DOTALL)
        if rationale_match:
            result['rationale'] = rationale_match.group(1).strip()

        # Look for category
        category_match = re.search(r'CATEGORY:\s*(\w+)', text, re.IGNORECASE)
        if category_match:
            category = category_match.group(1).lower()
            if category in ['convenience', 'comfort', 'security', 'energy']:
                result['category'] = category

        # Look for priority
        priority_match = re.search(r'PRIORITY:\s*(high|medium|low)', text, re.IGNORECASE)
        if priority_match:
            result['priority'] = priority_match.group(1).lower()

        # If no title extracted, use first sentence
        if not result['title']:
            first_sentence = text.strip().split('.')[0]
            result['title'] = first_sentence[:100]  # Limit length

        return result

    def _generate_fallback_yaml(self, pattern: dict) -> str:
        """
        Generate fallback YAML if LLM parsing fails.
        
        Args:
            pattern: Pattern dictionary
        
        Returns:
            Basic valid Home Assistant automation YAML
        """
        pattern_type = pattern.get('pattern_type', 'unknown')
        device_id = pattern.get('device_id', 'unknown.entity')

        if pattern_type == 'time_of_day':
            hour = pattern.get('hour', 0)
            minute = pattern.get('minute', 0)

            return f"""id: '{hash(f"{device_id}_{hour}_{minute}") % 10000000000}'
alias: "AI Suggested: {device_id} at {hour:02d}:{minute:02d}"
description: "Activate device at consistent time"
mode: single
triggers:
  - trigger: time
    at: "{hour:02d}:{minute:02d}:00"
conditions: []
actions:
  - action: homeassistant.turn_on
    target:
      entity_id: {device_id}
"""

        elif pattern_type == 'co_occurrence':
            device1 = pattern.get('device1', 'unknown')
            device2 = pattern.get('device2', 'unknown')

            # Try to extract friendly names for fallback
            device1_name = device1.split('.')[-1].replace('_', ' ').title() if '.' in device1 else device1
            device2_name = device2.split('.')[-1].replace('_', ' ').title() if '.' in device2 else device2

            return f"""id: '{hash(f"{device1}_{device2}") % 10000000000}'
alias: "AI Suggested: Turn On {device2_name} When {device1_name} Activates"
description: "Activate {device2_name} when {device1_name} changes"
mode: single
triggers:
  - trigger: state
    entity_id: {device1}
    to: 'on'
conditions: []
actions:
  - action: homeassistant.turn_on
    target:
      entity_id: {device2}
"""

        else:
            return f"""id: '{hash(device_id) % 10000000000}'
alias: "AI Suggested Automation"
description: "Pattern-based automation"
mode: single
triggers:
  - trigger: state
    entity_id: {device_id}
conditions: []
actions:
  - action: homeassistant.turn_on
    target:
      entity_id: {device_id}
"""

    def get_usage_stats(self) -> dict:
        """
        Get API usage statistics.
        
        Returns:
            Dictionary with token counts, estimated cost, and endpoint breakdown
        """
        cost = CostTracker.calculate_cost(
            self.total_input_tokens,
            self.total_output_tokens,
            model=self.model
        )

        # Phase 5: Format endpoint stats (enhanced with model breakdown)
        endpoint_breakdown = {}
        model_breakdown = {}  # Aggregate by model across all endpoints

        for endpoint_key, stats in self.endpoint_stats.items():
            # Extract endpoint and model from composite key
            if ':' in endpoint_key:
                endpoint, model = endpoint_key.rsplit(':', 1)
            else:
                endpoint = endpoint_key
                model = stats.get('model', self.model)

            # Endpoint breakdown (grouped by endpoint)
            if endpoint not in endpoint_breakdown:
                endpoint_breakdown[endpoint] = {
                    'calls': 0,
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'total_tokens': 0,
                    'cost_usd': 0.0,
                    'models': {}  # Per-model breakdown within endpoint
                }

            endpoint_breakdown[endpoint]['calls'] += stats['calls']
            endpoint_breakdown[endpoint]['input_tokens'] += stats['input_tokens']
            endpoint_breakdown[endpoint]['output_tokens'] += stats['output_tokens']
            endpoint_breakdown[endpoint]['total_tokens'] += stats['total_tokens']
            endpoint_breakdown[endpoint]['cost_usd'] += stats['cost_usd']

            # Per-model breakdown within endpoint
            endpoint_breakdown[endpoint]['models'][model] = {
                'calls': stats['calls'],
                'input_tokens': stats['input_tokens'],
                'output_tokens': stats['output_tokens'],
                'total_tokens': stats['total_tokens'],
                'cost_usd': round(stats['cost_usd'], 4),
                'avg_cost_per_call': round(stats['cost_usd'] / stats['calls'], 4) if stats['calls'] > 0 else 0.0
            }

            # Model-level aggregation (across all endpoints)
            if model not in model_breakdown:
                model_breakdown[model] = {
                    'calls': 0,
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'total_tokens': 0,
                    'cost_usd': 0.0
                }

            model_breakdown[model]['calls'] += stats['calls']
            model_breakdown[model]['input_tokens'] += stats['input_tokens']
            model_breakdown[model]['output_tokens'] += stats['output_tokens']
            model_breakdown[model]['total_tokens'] += stats['total_tokens']
            model_breakdown[model]['cost_usd'] += stats['cost_usd']

        # Calculate averages for endpoint breakdown
        for endpoint in endpoint_breakdown.values():
            if endpoint['calls'] > 0:
                endpoint['avg_cost_per_call'] = round(endpoint['cost_usd'] / endpoint['calls'], 4)
            else:
                endpoint['avg_cost_per_call'] = 0.0

        return {
            'total_tokens': self.total_tokens_used,
            'input_tokens': self.total_input_tokens,
            'output_tokens': self.total_output_tokens,
            'estimated_cost_usd': round(cost, 4),
            'total_cost_usd': round(self.total_cost_usd, 4),
            'model': self.model,
            'endpoint_breakdown': endpoint_breakdown,  # Phase 5: Add endpoint breakdown
            'model_breakdown': model_breakdown  # Model-level aggregation
        }

    def reset_usage_stats(self):
        """Reset usage statistics (for testing or daily reset)"""
        self.total_tokens_used = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.endpoint_stats = {}  # Phase 5: Reset endpoint stats
        logger.info("Usage statistics reset")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    async def generate_with_unified_prompt(
        self,
        prompt_dict: dict[str, str],
        temperature: float = 0.7,
        max_tokens: int = 600,
        output_format: str = "yaml",  # "yaml" | "description" | "json"
        endpoint: str | None = None,  # Phase 5: Track which endpoint made the call
        gpt51_use_case: str | None = None  # GPT-5.1 use case: "deterministic", "creative", "structured", "extraction"
    ) -> dict:
        """
        Generate automation suggestion using unified prompt format.
        
        Args:
            prompt_dict: {"system_prompt": ..., "user_prompt": ..., "pattern_summary": ..., "synergy_context": ..., "feedback_hint": ...}
                Additional context keys are optional and used to build developer-role messages.
            temperature: Creativity level
            max_tokens: Response limit
            output_format: Expected output format
        
        Returns:
            Parsed suggestion based on output_format
        
        Best Practices (from Context7):
        - Use AsyncOpenAI client for async/await patterns
        - Track token usage via response.usage
        - Handle streaming with async context managers if needed
        - Parse responses based on expected format
        """
        try:
            messages = [
                {"role": "system", "content": prompt_dict["system_prompt"]}
            ]

            developer_notes = []
            pattern_summary = prompt_dict.get("pattern_summary")
            if pattern_summary:
                developer_notes.append(f"Pattern Summary:\n{pattern_summary}")

            synergy_context = prompt_dict.get("synergy_context")
            if synergy_context:
                developer_notes.append(f"Synergy Context:\n{synergy_context}")

            feedback_hint = prompt_dict.get("feedback_hint")
            if feedback_hint:
                developer_notes.append(f"Recent Feedback:\n{feedback_hint}")

            if developer_notes:
                messages.append({
                    "role": "developer",
                    "content": "\n\n".join(developer_notes)
                })

            messages.append({"role": "user", "content": prompt_dict["user_prompt"]})

            # Count tokens before API call for logging and budgeting
            if hasattr(self, '_token_counter_enabled') and self._token_counter_enabled:
                try:
                    estimated_tokens = count_message_tokens(messages, model=self.model)
                    token_breakdown = get_token_breakdown(messages, model=self.model)
                    logger.info(
                        f"📊 Token estimate before API call: {estimated_tokens} tokens "
                        f"(breakdown: {token_breakdown})"
                    )
                except Exception as e:
                    logger.warning(f"Failed to count tokens before API call: {e}")

            # OpenAI Native Prompt Caching (Phase 4) - 90% discount on cached inputs
            # NOTE: Prompt caching via cache_control parameter is not currently supported
            # in the OpenAI Python SDK. This feature may be available in future SDK versions
            # or via extra_headers. For now, we log the cache intent but don't pass it to the API.
            settings = _get_settings()
            if settings and getattr(settings, 'enable_prompt_caching', True):
                # Generate cache key from system prompt (most stable part)
                system_prompt = messages[0].get('content', '') if messages else ''
                if system_prompt:
                    import hashlib
                    cache_key = hashlib.md5(system_prompt.encode()).hexdigest()
                    # Log cache intent (cache_control parameter not supported in current SDK)
                    logger.debug(f"Prompt caching requested (cache key: {cache_key[:8]}...) - not implemented in current SDK version")

            # Build API call parameters
            api_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_completion_tokens": max_tokens  # Use max_completion_tokens for newer models (gpt-4o+)
            }

            # Add GPT-5.1 parameters if applicable
            from ..utils.gpt51_params import (
                is_gpt51_model, 
                get_gpt51_params_for_use_case, 
                merge_gpt51_params,
                remove_unsupported_gpt51_params
            )
            
            if is_gpt51_model(self.model):
                # Determine use case if not specified
                if gpt51_use_case is None:
                    # Infer from output_format and temperature
                    if output_format == "json" or output_format == "yaml":
                        gpt51_use_case = "structured" if temperature < 0.5 else "creative"
                    else:
                        gpt51_use_case = "deterministic" if temperature < 0.5 else "creative"
                
                # Get GPT-5.1 parameters
                gpt51_params = get_gpt51_params_for_use_case(
                    model=self.model,
                    use_case=gpt51_use_case,
                    enable_prompt_caching=getattr(settings, 'enable_prompt_caching', True) if settings else True
                )
                
                # Merge GPT-5.1 parameters (handles temperature conflict automatically)
                # Note: merge_gpt51_params() already removes temperature/top_p/logprobs
                # when reasoning.effort != 'none', so no additional check needed
                api_params = merge_gpt51_params(api_params, gpt51_params)
            
            # NOTE: cache_control parameter is not supported in OpenAI Python SDK
            # Remove if present to avoid TypeError
            api_params.pop("cache_control", None)
            
            # Remove GPT-5.1 parameters that may not be supported by the SDK
            # TODO: Re-enable when OpenAI SDK fully supports GPT-5.1 parameters
            api_params = remove_unsupported_gpt51_params(api_params)

            response = await self.client.chat.completions.create(**api_params)

            # Track token usage (OpenAI best practice)
            usage = response.usage
            self.total_input_tokens += usage.prompt_tokens
            self.total_output_tokens += usage.completion_tokens
            self.total_tokens_used += usage.total_tokens

            # Calculate cost for this request
            request_cost = CostTracker.calculate_cost(
                usage.prompt_tokens,
                usage.completion_tokens,
                model=self.model
            )
            self.total_cost_usd += request_cost

            # Phase 5: Track endpoint-level stats (enhanced with model name)
            if endpoint:
                # Use composite key to track model per endpoint
                endpoint_key = f"{endpoint}:{self.model}"
                if endpoint_key not in self.endpoint_stats:
                    self.endpoint_stats[endpoint_key] = {
                        'calls': 0,
                        'input_tokens': 0,
                        'output_tokens': 0,
                        'total_tokens': 0,
                        'cost_usd': 0.0,
                        'model': self.model  # Include model name in stats
                    }
                self.endpoint_stats[endpoint_key]['calls'] += 1
                self.endpoint_stats[endpoint_key]['input_tokens'] += usage.prompt_tokens
                self.endpoint_stats[endpoint_key]['output_tokens'] += usage.completion_tokens
                self.endpoint_stats[endpoint_key]['total_tokens'] += usage.total_tokens
                self.endpoint_stats[endpoint_key]['cost_usd'] += request_cost

            # Store last usage for debug panel
            self.last_usage = {
                'prompt_tokens': usage.prompt_tokens,
                'completion_tokens': usage.completion_tokens,
                'total_tokens': usage.total_tokens,
                'cost_usd': round(request_cost, 4),
                'model': self.model,
                'endpoint': endpoint  # Phase 5: Include endpoint in last usage
            }

            logger.info(
                f"✅ Unified prompt generation successful: {usage.total_tokens} tokens "
                f"(input: {usage.prompt_tokens}, output: {usage.completion_tokens})"
            )
            logger.info(f"OpenAI response has {len(response.choices)} choices")
            logger.info(f"Response finish reason: {response.choices[0].finish_reason}")

            # Parse based on output_format
            content = response.choices[0].message.content

            # Enhanced error handling for empty responses
            if not content:
                finish_reason = response.choices[0].finish_reason if response.choices else "unknown"
                logger.error(f"❌ Empty content from OpenAI API. Finish reason: {finish_reason}, Model: {self.model}")
                logger.error(f"Response object: {response}")

                # Check if it's a model error (invalid model name)
                if finish_reason == "stop" and not content:
                    raise ValueError(
                        f"Empty content from OpenAI API. This may indicate an invalid model name '{self.model}'. "
                        f"Please verify the model name is correct (e.g., 'gpt-4o', 'gpt-4o-mini'). "
                        f"Finish reason: {finish_reason}"
                    )
                else:
                    raise ValueError(
                        f"Empty content from OpenAI API. Finish reason: {finish_reason}. "
                        f"This may be due to API rate limiting, content filtering, or model unavailability."
                    )

            logger.info(f"OpenAI response content (length={len(content)}): {content[:200]}")

            pattern_source = prompt_dict.get("pattern_source", {})

            if output_format == "json":
                import json
                # Handle markdown code blocks
                if content.startswith('```json'):
                    content = content[7:]
                elif content.startswith('```'):
                    content = content[3:]
                if content.endswith('```'):
                    content = content[:-3]
                return json.loads(content.strip())
            elif output_format == "yaml":
                # Parse as full automation suggestion
                return self._parse_automation_response(content, pattern_source)
            else:  # description
                # Parse structured description response
                return self._parse_description_response(content.strip())

        except Exception as e:
            logger.error(f"❌ Unified prompt generation error: {e}")
            import traceback
            logger.error(f"Stack trace:\n{traceback.format_exc()}")
            raise

    async def generate_automation_suggestion(
        self,
        pattern: dict,
        device_context: dict | None = None,
        output_mode: str = "yaml"
    ):
        """
        Convenience wrapper that builds a unified pattern prompt and generates a suggestion.
        """
        from ..prompt_building.unified_prompt_builder import UnifiedPromptBuilder

        builder = UnifiedPromptBuilder()
        prompt_dict = await builder.build_pattern_prompt(
            pattern=pattern,
            device_context=device_context,
            output_mode=output_mode
        )

        result = await self.generate_with_unified_prompt(
            prompt_dict=prompt_dict,
            temperature=0.7,
            max_tokens=600 if output_mode == "yaml" else 400,
            output_format="yaml" if output_mode == "yaml" else "description"
        )

        return result

    async def infer_category_and_priority(self, description: str) -> dict[str, str]:
        """
        Infer category and priority from automation description.
        
        Used for regenerating category when description changes during redeploy.
        Uses GPT-4o-mini for classification (cost savings vs GPT-4o).
        
        Args:
            description: Automation description
            
        Returns:
            Dictionary with 'category' and 'priority' keys
        """
        # Use classification model (GPT-4o-mini) for cost efficiency
        from ..config import settings
        classification_model = getattr(settings, 'classification_model', 'gpt-5.1')

        # Create temporary client with classification model if different
        original_model = self.model
        if classification_model != self.model:
            # Temporarily switch model for this call
            self.model = classification_model

        try:
            result = await self.generate_with_unified_prompt(
                prompt_dict={
                    "system_prompt": "You are a Home Assistant automation classifier. Classify automations into categories and priorities based on their primary purpose.",
                    "user_prompt": f"""Analyze this automation description and classify it.

Description: "{description}"

Return ONLY a JSON object with:
{{
    "category": "energy|comfort|security|convenience",
    "priority": "high|medium|low"
}}

Guidelines:
- energy: Saving power, efficiency, cost reduction
- comfort: Temperature, lighting ambiance, personal preferences
- security: Safety, alarms, monitoring, locks
- convenience: Time-saving, automation of routine tasks

Choose the category that BEST fits the primary purpose of this automation."""
                },
                temperature=0.2,  # Low temperature for consistency
                max_tokens=100,
                output_format="json"
            )

            category = result.get('category', 'convenience')
            priority = result.get('priority', 'medium')

            # Validate category
            if category not in ['energy', 'comfort', 'security', 'convenience']:
                logger.warning(f"Invalid category '{category}' from LLM, defaulting to 'convenience'")
                category = 'convenience'

            # Validate priority
            if priority not in ['high', 'medium', 'low']:
                logger.warning(f"Invalid priority '{priority}' from LLM, defaulting to 'medium'")
                priority = 'medium'

            logger.info(f"✅ Inferred category: {category}, priority: {priority}")

            return {
                'category': category,
                'priority': priority
            }

        except Exception as e:
            logger.error(f"❌ Failed to infer category: {e}")
            # Return safe defaults
            return {
                'category': 'convenience',
                'priority': 'medium'
            }
        finally:
            # Restore original model
            self.model = original_model

