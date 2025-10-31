"""
OpenAI Client for Automation Suggestion Generation

Uses GPT-4o-mini to convert detected patterns into natural language
automation suggestions with valid Home Assistant YAML.

**Model:** GPT-4o-mini (cost-effective, sufficient for YAML generation)
**Temperature:** 0.7 (balanced creativity + consistency)
**Typical Cost:** $0.000137 per suggestion (~$0.50/year for daily runs)

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

from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import Dict, Optional
import logging
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


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
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o-mini for cost savings)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.total_tokens_used = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        logger.info(f"OpenAI client initialized with model={model}")
    
    def _parse_automation_response(self, llm_response: str, pattern: Dict) -> AutomationSuggestion:
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
    
    def _extract_alias(self, text: str) -> Optional[str]:
        """Extract alias from LLM response"""
        # Look for 'alias: "..."' in YAML block
        match = re.search(r'alias:\s*["\']?([^"\'\n]+)["\']?', text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    
    def _extract_description(self, text: str) -> Optional[str]:
        """Extract description from LLM response"""
        match = re.search(r'description:\s*["\']?([^"\'\n]+)["\']?', text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    
    def _extract_yaml(self, text: str) -> Optional[str]:
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
    
    def _extract_rationale(self, text: str) -> Optional[str]:
        """Extract rationale explanation from LLM response"""
        match = re.search(r'RATIONALE:\s*(.+?)(?:CATEGORY:|PRIORITY:|$)', text, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else None
    
    def _extract_category(self, text: str) -> Optional[str]:
        """Extract category from LLM response"""
        match = re.search(r'CATEGORY:\s*(\w+)', text, re.IGNORECASE)
        if match:
            category = match.group(1).lower()
            if category in ['energy', 'comfort', 'security', 'convenience']:
                return category
        return None
    
    def _extract_priority(self, text: str) -> Optional[str]:
        """Extract priority from LLM response"""
        match = re.search(r'PRIORITY:\s*(\w+)', text, re.IGNORECASE)
        if match:
            priority = match.group(1).lower()
            if priority in ['high', 'medium', 'low']:
                return priority
        return None
    
    def _infer_category(self, pattern: Dict) -> str:
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
    
    def _parse_description_response(self, text: str) -> Dict:
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
    
    def _generate_fallback_yaml(self, pattern: Dict) -> str:
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
            
            return f"""alias: "AI Suggested: {device_id} at {hour:02d}:{minute:02d}"
description: "Activate device at consistent time"
trigger:
  - platform: time
    at: "{hour:02d}:{minute:02d}:00"
action:
  - service: homeassistant.turn_on
    target:
      entity_id: {device_id}
"""
        
        elif pattern_type == 'co_occurrence':
            device1 = pattern.get('device1', 'unknown')
            device2 = pattern.get('device2', 'unknown')
            
            # Try to extract friendly names for fallback
            device1_name = device1.split('.')[-1].replace('_', ' ').title() if '.' in device1 else device1
            device2_name = device2.split('.')[-1].replace('_', ' ').title() if '.' in device2 else device2
            
            return f"""alias: "AI Suggested: Turn On {device2_name} When {device1_name} Activates"
description: "Activate {device2_name} when {device1_name} changes"
trigger:
  - platform: state
    entity_id: {device1}
    to: 'on'
action:
  - service: homeassistant.turn_on
    target:
      entity_id: {device2}
"""
        
        else:
            return f"""alias: "AI Suggested Automation"
description: "Pattern-based automation"
trigger:
  - platform: state
    entity_id: {device_id}
action:
  - service: homeassistant.turn_on
    target:
      entity_id: {device_id}
"""
    
    def get_usage_stats(self) -> Dict:
        """
        Get API usage statistics.
        
        Returns:
            Dictionary with token counts and estimated cost
        """
        from .cost_tracker import CostTracker
        
        cost = CostTracker.calculate_cost(
            self.total_input_tokens,
            self.total_output_tokens
        )
        
        return {
            'total_tokens': self.total_tokens_used,
            'input_tokens': self.total_input_tokens,
            'output_tokens': self.total_output_tokens,
            'estimated_cost_usd': round(cost, 4),
            'model': self.model
        }
    
    def reset_usage_stats(self):
        """Reset usage statistics (for testing or daily reset)"""
        self.total_tokens_used = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        logger.info("Usage statistics reset")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    async def generate_with_unified_prompt(
        self,
        prompt_dict: Dict[str, str],
        temperature: float = 0.7,
        max_tokens: int = 600,
        output_format: str = "yaml"  # "yaml" | "description" | "json"
    ) -> Dict:
        """
        Generate automation suggestion using unified prompt format.
        
        Args:
            prompt_dict: {"system_prompt": ..., "user_prompt": ...} from UnifiedPromptBuilder
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
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt_dict["system_prompt"]},
                    {"role": "user", "content": prompt_dict["user_prompt"]}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Track token usage (OpenAI best practice)
            usage = response.usage
            self.total_input_tokens += usage.prompt_tokens
            self.total_output_tokens += usage.completion_tokens
            self.total_tokens_used += usage.total_tokens
            
            logger.info(
                f"✅ Unified prompt generation successful: {usage.total_tokens} tokens "
                f"(input: {usage.prompt_tokens}, output: {usage.completion_tokens})"
            )
            logger.info(f"OpenAI response has {len(response.choices)} choices")
            logger.info(f"Response finish reason: {response.choices[0].finish_reason}")
            
            # Parse based on output_format
            content = response.choices[0].message.content
            logger.info(f"OpenAI response content (length={len(content) if content else 0}): {content[:200] if content else 'None'}")
            
            if output_format == "json":
                import json
                # Handle markdown code blocks
                if not content:
                    raise ValueError("Empty content from OpenAI API")
                if content.startswith('```json'):
                    content = content[7:]
                elif content.startswith('```'):
                    content = content[3:]
                if content.endswith('```'):
                    content = content[:-3]
                return json.loads(content.strip())
            elif output_format == "yaml":
                # Parse as full automation suggestion
                return self._parse_automation_response(content, {})
            else:  # description
                # Parse structured description response
                return self._parse_description_response(content.strip())
                
        except Exception as e:
            logger.error(f"❌ Unified prompt generation error: {e}")
            import traceback
            logger.error(f"Stack trace:\n{traceback.format_exc()}")
            raise
    
