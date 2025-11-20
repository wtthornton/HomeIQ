"""
Description-Only Generator - Story AI1.23 Phase 2
==================================================

Generates human-readable descriptions from patterns without YAML.
This is the first step in the conversational automation flow.

Flow:
1. Pattern detected → 2. Generate description (HERE) → 3. User refines → 4. Generate YAML

Key Principles:
- NO YAML generation (that happens in Phase 4)
- Use friendly device names, not entity IDs
- Keep descriptions to 1-2 sentences
- Temperature 0.7 for natural language
- Target ~200 tokens per description
"""

import logging

from openai import AsyncOpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


# ============================================================================
# Prompt Templates
# ============================================================================

SYSTEM_PROMPT_DESCRIPTION = """You are a home automation expert creating human-readable automation suggestions.

Your goal: Create a clear, conversational description of what the automation will do.
DO NOT generate YAML. Only describe the automation in plain English.

Guidelines:
- Use device friendly names, not entity IDs
- Be specific about triggers and actions
- Include timing and conditions naturally
- Write like you're explaining to a friend
- Keep it to 1-2 sentences maximum
- Focus on WHAT it does, not HOW it's implemented

Examples:
✓ "When motion is detected in the Kitchen after 6PM, turn on the Kitchen Light to 50% brightness"
✓ "Turn off the Coffee Maker automatically at 10 AM every weekday"
✓ "When the Front Door opens, turn on the Hallway Light for 5 minutes"

✗ "alias: Kitchen Motion Light\ntrigger:\n..." (NO YAML!)
✗ "light.kitchen turns on when binary_sensor.kitchen_motion..." (Use friendly names!)
✗ "This automation will create a trigger that monitors the motion sensor and..." (Too wordy!)
"""


class DescriptionGenerator:
    """
    Generates human-readable descriptions from detected patterns.
    
    Phase 2: Description-Only Generation
    Story AI1.23: Conversational Suggestion Refinement
    
    Usage:
        generator = DescriptionGenerator(openai_client)
        description = await generator.generate_description(pattern, device_context)
    """

    def __init__(self, openai_client: AsyncOpenAI, model: str = "gpt-4o-mini"):
        """
        Initialize description generator.
        
        Args:
            openai_client: AsyncOpenAI client instance
            model: Model to use (default: gpt-4o-mini for cost efficiency)
        """
        self.client = openai_client
        self.model = model
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        logger.info(f"DescriptionGenerator initialized with model={model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    async def generate_description(
        self,
        pattern: dict,
        device_context: dict | None = None
    ) -> str:
        """
        Generate human-readable description from pattern.
        
        Args:
            pattern: Detected pattern dict with type, device_id, metadata
            device_context: Optional device metadata (name, area, capabilities)
        
        Returns:
            Human-readable description (NO YAML)
        
        Raises:
            Exception: If OpenAI API call fails after retries
        """
        try:
            # Build prompt based on pattern type
            prompt = self._build_prompt(pattern, device_context)

            logger.info(f"📝 Generating description for {pattern.get('pattern_type')} pattern: {pattern.get('device_id', 'N/A')}")

            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT_DESCRIPTION
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,  # Higher for natural, creative language
                max_completion_tokens=200    # Short descriptions only (use max_completion_tokens for newer models)
            )

            # Track token usage
            usage = response.usage
            self.total_input_tokens += usage.prompt_tokens
            self.total_output_tokens += usage.completion_tokens
            self.total_tokens += usage.total_tokens

            logger.info(
                f"✅ Description generated: {usage.total_tokens} tokens "
                f"(input: {usage.prompt_tokens}, output: {usage.completion_tokens})"
            )

            # Extract description
            description = response.choices[0].message.content.strip()

            # Validate: ensure no YAML was generated
            if any(yaml_marker in description.lower() for yaml_marker in ['alias:', 'trigger:', 'action:', 'condition:']):
                logger.warning("⚠️ OpenAI returned YAML despite instructions! Cleaning...")
                # Extract only the descriptive text before any YAML
                description = description.split('alias:')[0].split('trigger:')[0].strip()

            logger.info(f"✅ Final description: {description[:80]}...")
            return description

        except Exception as e:
            logger.error(f"❌ OpenAI API error for pattern {pattern.get('pattern_type')}: {e}")
            raise

    def _build_prompt(self, pattern: dict, device_context: dict | None = None) -> str:
        """
        Build prompt for description generation.
        
        Args:
            pattern: Pattern dictionary
            device_context: Optional device metadata
        
        Returns:
            Formatted prompt for OpenAI
        """
        pattern_type = pattern.get('pattern_type', 'unknown')

        if pattern_type == 'time_of_day':
            return self._build_time_of_day_prompt(pattern, device_context)
        elif pattern_type == 'co_occurrence':
            return self._build_co_occurrence_prompt(pattern, device_context)
        elif pattern_type == 'anomaly':
            return self._build_anomaly_prompt(pattern, device_context)
        else:
            logger.warning(f"Unknown pattern type: {pattern_type}, using generic prompt")
            return self._build_generic_prompt(pattern, device_context)

    def _build_time_of_day_prompt(self, pattern: dict, device_context: dict | None = None) -> str:
        """Build prompt for time-of-day pattern"""
        device_id = pattern.get('device_id', 'unknown')
        hour = pattern.get('hour', pattern.get('metadata', {}).get('hour', 0))
        minute = pattern.get('minute', pattern.get('metadata', {}).get('minute', 0))
        occurrences = pattern.get('occurrences', 0)
        confidence = pattern.get('confidence', 0.0)

        # Extract friendly name from device_context
        device_name = device_id
        area = ''
        domain = device_id.split('.')[0] if '.' in device_id else 'unknown'

        if device_context:
            device_name = device_context.get('name', device_context.get('friendly_name', device_id))
            area = device_context.get('area', device_context.get('area_id', ''))
            domain = device_context.get('domain', domain)

        # Build device description
        device_desc = f"{device_name}"
        if area:
            device_desc += f" in {area}"

        return f"""Create a 1-2 sentence description for this automation pattern:

PATTERN DETECTED:
- Type: Time-of-day pattern
- Device: {device_desc}
- Entity ID: {device_id}
- Device Type: {domain}
- Consistent time: {hour:02d}:{minute:02d}
- Occurrences: {occurrences} times in last 30 days
- Confidence: {confidence:.0%}

TASK:
Write a simple, natural description of what automation this suggests.
Use the device name "{device_name}" (NOT the entity ID).
Include WHEN it should happen and WHAT action to take.

Format: "When [condition], [action with device name]"
Example: "At 7:00 AM every morning, turn on the {device_name} to wake up gradually"

Your description (1-2 sentences, NO YAML):"""

    def _build_co_occurrence_prompt(self, pattern: dict, device_context: dict | None = None) -> str:
        """Build prompt for co-occurrence pattern"""
        device1 = pattern.get('device1', pattern.get('device_id', 'unknown'))
        device2 = pattern.get('device2', pattern.get('metadata', {}).get('device2', 'unknown'))
        occurrences = pattern.get('occurrences', 0)
        confidence = pattern.get('confidence', 0.0)
        avg_delta = pattern.get('metadata', {}).get('avg_time_delta_seconds', 30)

        # Extract friendly names
        device1_name = device1
        device2_name = device2

        if device_context:
            if 'device1' in device_context:
                device1_name = device_context['device1'].get('name', device1)
            if 'device2' in device_context:
                device2_name = device_context['device2'].get('name', device2)

        return f"""Create a 1-2 sentence description for this automation pattern:

PATTERN DETECTED:
- Type: Co-occurrence pattern (devices used together)
- First device: {device1_name} (entity: {device1})
- Second device: {device2_name} (entity: {device2})
- Co-occurrences: {occurrences} times in last 30 days
- Confidence: {confidence:.0%}
- Average time between: {avg_delta:.0f} seconds

USER BEHAVIOR:
When the user activates "{device1_name}", they typically also activate "{device2_name}" about {int(avg_delta)} seconds later.

TASK:
Write a simple description suggesting to automate this pattern.
Use both device names "{device1_name}" and "{device2_name}" (NOT entity IDs).

Format: "When [first device] is activated, automatically [action with second device]"
Example: "When you turn on the {device1_name}, automatically turn on the {device2_name} shortly after"

Your description (1-2 sentences, NO YAML):"""

    def _build_anomaly_prompt(self, pattern: dict, device_context: dict | None = None) -> str:
        """Build prompt for anomaly pattern"""
        device_id = pattern.get('device_id', 'unknown')
        anomaly_score = pattern.get('metadata', {}).get('anomaly_score', 0)

        device_name = device_id
        if device_context:
            device_name = device_context.get('name', device_context.get('friendly_name', device_id))

        return f"""Create a 1-2 sentence description for this automation pattern:

PATTERN DETECTED:
- Type: Anomaly detection
- Device: {device_name} (entity: {device_id})
- Anomaly Score: {anomaly_score:.2f}
- Pattern: Device shows unusual activity outside normal usage patterns

TASK:
Write a simple description suggesting a notification when unusual activity occurs.
Use the device name "{device_name}" (NOT the entity ID).

Format: "Send notification when [device] shows unusual activity"
Example: "Get notified when the {device_name} is activated at unexpected times"

Your description (1-2 sentences, NO YAML):"""

    def _build_generic_prompt(self, pattern: dict, device_context: dict | None = None) -> str:
        """Build generic prompt for unknown pattern types"""
        device_id = pattern.get('device_id', 'unknown')
        pattern_type = pattern.get('pattern_type', 'detected usage')

        device_name = device_id
        if device_context:
            device_name = device_context.get('name', device_context.get('friendly_name', device_id))

        return f"""Create a 1-2 sentence description for this automation pattern:

PATTERN DETECTED:
- Type: {pattern_type}
- Device: {device_name} (entity: {device_id})

TASK:
Write a simple description of what automation this pattern suggests.
Use the device name "{device_name}" (NOT the entity ID).
Keep it natural and conversational.

Your description (1-2 sentences, NO YAML):"""

    def get_usage_stats(self) -> dict:
        """
        Get token usage statistics.
        
        Returns:
            Dictionary with token counts and estimated cost
        """
        # Use CostTracker for consistent cost calculation
        from .cost_tracker import CostTracker

        total_cost = CostTracker.calculate_cost(
            self.total_input_tokens,
            self.total_output_tokens,
            model=self.model
        )

        return {
            'total_tokens': self.total_tokens,
            'input_tokens': self.total_input_tokens,
            'output_tokens': self.total_output_tokens,
            'estimated_cost_usd': round(total_cost, 6),
            'total_cost_usd': round(total_cost, 6),
            'model': self.model
        }

    def reset_usage_stats(self):
        """Reset usage statistics"""
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        logger.info("Usage statistics reset")

