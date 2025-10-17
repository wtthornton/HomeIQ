"""
Natural Language Automation Generator
Story AI1.21: Natural Language Request Generation

Generates Home Assistant automations from user's natural language requests.
Uses OpenAI to convert text like "Turn on kitchen light at 7 AM" into valid YAML.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import logging
import yaml
import json

from .clients.data_api_client import DataAPIClient
from .llm.openai_client import OpenAIClient
from .safety_validator import SafetyValidator, SafetyResult

logger = logging.getLogger(__name__)


@dataclass
class NLAutomationRequest:
    """User's natural language automation request"""
    request_text: str
    user_id: str = "default"
    context: Optional[Dict] = None


@dataclass
class GeneratedAutomation:
    """Result of NL automation generation"""
    automation_yaml: str
    title: str
    description: str
    confidence: float  # 0-1
    explanation: str
    safety_result: Optional[SafetyResult] = None
    clarification_needed: Optional[str] = None
    warnings: Optional[List[str]] = None


class NLAutomationGenerator:
    """
    Generates Home Assistant automations from natural language requests.
    
    Process:
    1. Fetch available devices/entities from data-api
    2. Build context-rich prompt for OpenAI
    3. Generate automation YAML
    4. Validate syntax and safety
    5. Return automation with explanation
    """
    
    def __init__(
        self,
        data_api_client: DataAPIClient,
        openai_client: OpenAIClient,
        safety_validator: SafetyValidator
    ):
        """
        Initialize NL automation generator.
        
        Args:
            data_api_client: Client for fetching device/entity data
            openai_client: Client for OpenAI API calls
            safety_validator: Safety validation engine
        """
        self.data_api_client = data_api_client
        self.openai_client = openai_client
        self.safety_validator = safety_validator
    
    async def generate(
        self,
        request: NLAutomationRequest
    ) -> GeneratedAutomation:
        """
        Generate automation from natural language request.
        
        Args:
            request: User's natural language request
        
        Returns:
            GeneratedAutomation with YAML and explanation
        """
        logger.info(f"🤖 Generating automation from NL: '{request.request_text}'")
        
        # 1. Fetch available devices and entities for context
        automation_context = await self._build_automation_context()
        
        # 2. Build prompt for OpenAI
        prompt = self._build_prompt(request, automation_context)
        
        # 3. Call OpenAI to generate automation (with retry)
        try:
            openai_response = await self._call_openai(prompt)
            automation_data = self._parse_openai_response(openai_response)
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return GeneratedAutomation(
                automation_yaml="",
                title="Generation Failed",
                description=f"Failed to generate automation: {str(e)}",
                confidence=0.0,
                explanation="",
                clarification_needed="Could you rephrase your request more specifically? For example, include specific device names and times."
            )
        
        # 4. Validate YAML syntax
        try:
            yaml.safe_load(automation_data['yaml'])
        except yaml.YAMLError as e:
            logger.error(f"Generated invalid YAML: {e}")
            # Retry once with error feedback
            return await self._retry_generation(request, automation_context, str(e))
        
        # 5. Validate safety
        safety_result = await self.safety_validator.validate(automation_data['yaml'])
        
        # 6. Calculate confidence based on request clarity and safety
        confidence = self._calculate_confidence(
            request,
            automation_data,
            safety_result
        )
        
        # 7. Extract warnings from safety validation
        warnings = []
        if safety_result.issues:
            warnings = [
                f"{issue.severity.upper()}: {issue.message}"
                for issue in safety_result.issues
                if issue.severity in ['warning', 'critical']
            ]
        
        logger.info(
            f"✅ Generated automation '{automation_data['title']}' "
            f"(confidence: {confidence:.0%}, safety: {safety_result.safety_score})"
        )
        
        return GeneratedAutomation(
            automation_yaml=automation_data['yaml'],
            title=automation_data['title'],
            description=automation_data['description'],
            confidence=confidence,
            explanation=automation_data['explanation'],
            safety_result=safety_result,
            clarification_needed=automation_data.get('clarification'),
            warnings=warnings if warnings else None
        )
    
    async def _build_automation_context(self) -> Dict:
        """
        Fetch available devices and entities from data-api.
        Provides rich context to OpenAI about available hardware.
        """
        try:
            logger.debug("Fetching device context from data-api")
            
            # Fetch devices and entities
            devices = await self.data_api_client.fetch_devices(limit=100)
            entities = await self.data_api_client.fetch_entities(limit=200)
            
            # Organize entities by domain for easier reference
            entities_by_domain = {}
            
            if not entities.empty:
                for _, entity in entities.iterrows():
                    entity_id = entity.get('entity_id', '')
                    if not entity_id:
                        continue
                    
                    domain = entity_id.split('.')[0]
                    if domain not in entities_by_domain:
                        entities_by_domain[domain] = []
                    
                    entities_by_domain[domain].append({
                        'entity_id': entity_id,
                        'friendly_name': entity.get('friendly_name', entity_id),
                        'area': entity.get('area_id', 'unknown')
                    })
            
            logger.info(f"Built context with {len(devices)} devices, {len(entities)} entities")
            
            return {
                'devices': devices.to_dict('records') if not devices.empty else [],
                'entities_by_domain': entities_by_domain,
                'domains': list(entities_by_domain.keys())
            }
        except Exception as e:
            logger.error(f"Failed to fetch automation context: {e}")
            return {'devices': [], 'entities_by_domain': {}, 'domains': []}
    
    def _build_prompt(
        self,
        request: NLAutomationRequest,
        automation_context: Dict
    ) -> str:
        """
        Build comprehensive prompt for OpenAI.
        
        Includes available devices, HA automation structure, and safety guidelines.
        """
        # Summarize available devices for prompt
        device_summary = self._summarize_devices(automation_context)
        
        prompt = f"""You are a Home Assistant automation expert. Generate a valid Home Assistant automation from the user's natural language request.

**Available Devices:**
{device_summary}

**User Request:**
"{request.request_text}"

**Instructions:**
1. Generate a COMPLETE, VALID Home Assistant automation in YAML format
2. Use ONLY devices that exist in the available devices list above
3. If the request is ambiguous, ask for clarification in the 'clarification' field
4. Include appropriate triggers, conditions (if needed), and actions
5. Use a friendly, descriptive alias name
6. Add time constraints or conditions for safety where appropriate
7. Explain how the automation works in plain language

**Output Format (JSON):**
{{
    "yaml": "alias: Automation Name\\ntrigger:\\n  - platform: time\\n    at: '07:00:00'\\naction:\\n  - service: light.turn_on\\n    target:\\n      entity_id: light.kitchen",
    "title": "Brief title (max 60 chars)",
    "description": "One sentence description of what it does",
    "explanation": "Detailed explanation of triggers, conditions, and actions",
    "clarification": null,
    "confidence": 0.95
}}

**Safety Guidelines:**
- NEVER disable security systems, alarms, or locks
- Avoid extreme climate changes (keep 60-80°F range)
- Add time or condition constraints for destructive actions (turn_off, close, lock)
- Use reasonable defaults (brightness: 50%, temperature: 70°F)
- Avoid "turn off all" unless explicitly requested
- Add debounce ('for' duration) for frequently-changing sensors

**If the request is unclear or missing information:**
- Set "clarification" to a question asking for specific details
- Set confidence to 0.5 or lower
- Still try to generate a reasonable automation

Generate the automation now (respond ONLY with JSON, no other text):"""
        
        return prompt
    
    def _summarize_devices(self, automation_context: Dict) -> str:
        """Create human-readable summary of available devices"""
        summary_lines = []
        
        entities_by_domain = automation_context.get('entities_by_domain', {})
        
        # Priority domains (most commonly used)
        priority_domains = [
            'light', 'switch', 'climate', 'cover', 'lock',
            'binary_sensor', 'sensor', 'fan', 'camera'
        ]
        
        for domain in priority_domains:
            if domain in entities_by_domain:
                entities = entities_by_domain[domain]
                count = len(entities)
                
                # Show first 5 examples
                examples = [e['friendly_name'] for e in entities[:5]]
                
                summary_lines.append(
                    f"- {domain.replace('_', ' ').title()}s ({count}): {', '.join(examples)}"
                    + (f", and {count - 5} more" if count > 5 else "")
                )
        
        # Add other domains
        other_domains = [d for d in entities_by_domain.keys() if d not in priority_domains]
        if other_domains:
            summary_lines.append(f"- Other: {', '.join(other_domains)}")
        
        return "\n".join(summary_lines) if summary_lines else "No devices found (using default HA entities)"
    
    async def _call_openai(self, prompt: str, temperature: float = 0.3) -> str:
        """
        Call OpenAI API with retry logic.
        
        Args:
            prompt: Complete prompt for OpenAI
            temperature: Model temperature (0.3 = consistent, 0.7 = creative)
        
        Returns:
            Raw response content from OpenAI
        """
        try:
            response = await self.openai_client.client.chat.completions.create(
                model=self.openai_client.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Home Assistant automation expert. Generate valid YAML automations from natural language requests. Respond ONLY with JSON, no markdown formatting."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=1500,
                response_format={"type": "json_object"}  # Force JSON output
            )
            
            # Track token usage
            if hasattr(response, 'usage'):
                self.openai_client.total_input_tokens += response.usage.prompt_tokens
                self.openai_client.total_output_tokens += response.usage.completion_tokens
                self.openai_client.total_tokens_used += response.usage.total_tokens
            
            content = response.choices[0].message.content
            logger.debug(f"OpenAI response received ({len(content)} chars)")
            
            return content
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def _parse_openai_response(self, response: str) -> Dict:
        """
        Parse JSON response from OpenAI.
        
        Args:
            response: Raw response string (should be JSON)
        
        Returns:
            Parsed dict with yaml, title, description, etc.
        """
        try:
            # Clean response (remove markdown if present)
            cleaned = response.strip()
            
            # Remove markdown code blocks if present
            if '```json' in cleaned:
                start = cleaned.find('```json') + 7
                end = cleaned.find('```', start)
                cleaned = cleaned[start:end].strip()
            elif '```' in cleaned:
                start = cleaned.find('```') + 3
                end = cleaned.find('```', start)
                cleaned = cleaned[start:end].strip()
            
            # Parse JSON
            data = json.loads(cleaned)
            
            # Validate required fields
            required_fields = ['yaml', 'title', 'description', 'explanation']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            logger.debug(f"Response: {response[:200]}")
            raise ValueError(f"OpenAI returned invalid JSON: {e}")
    
    async def _retry_generation(
        self,
        request: NLAutomationRequest,
        automation_context: Dict,
        error_message: str
    ) -> GeneratedAutomation:
        """
        Retry generation with error feedback.
        
        Gives OpenAI the error from first attempt to help it correct mistakes.
        """
        logger.info(f"Retrying generation with error feedback: {error_message}")
        
        retry_prompt = f"""The previous generation attempt failed with this error:
ERROR: {error_message}

Please try again, ensuring:
1. The YAML is syntactically valid
2. All indentation is correct (use 2 spaces, not tabs)
3. All strings are properly quoted
4. The automation follows Home Assistant syntax exactly

Original request: "{request.request_text}"

Available devices:
{self._summarize_devices(automation_context)}

Generate a valid automation now (JSON only):"""
        
        try:
            response = await self._call_openai(retry_prompt, temperature=0.2)  # Lower temp for retry
            automation_data = self._parse_openai_response(response)
            
            # Validate YAML again
            yaml.safe_load(automation_data['yaml'])
            
            # Validate safety
            safety_result = await self.safety_validator.validate(automation_data['yaml'])
            
            logger.info("✅ Retry successful, valid YAML generated")
            
            return GeneratedAutomation(
                automation_yaml=automation_data['yaml'],
                title=automation_data['title'],
                description=automation_data['description'],
                confidence=max(0.0, automation_data.get('confidence', 0.7) - 0.15),  # Lower confidence after retry
                explanation=automation_data['explanation'],
                safety_result=safety_result
            )
        except Exception as e:
            logger.error(f"Retry generation also failed: {e}")
            return GeneratedAutomation(
                automation_yaml="",
                title="Generation Failed",
                description=f"Could not generate valid automation after retry: {str(e)}",
                confidence=0.0,
                explanation="",
                clarification_needed="Please try rephrasing your request. Be specific about:\n- Which device(s) you want to control\n- When it should trigger\n- What action it should take"
            )
    
    def _calculate_confidence(
        self,
        request: NLAutomationRequest,
        automation_data: Dict,
        safety_result: SafetyResult
    ) -> float:
        """
        Calculate confidence score for generated automation.
        
        Factors:
        - OpenAI's self-reported confidence
        - Request clarity (length, specificity)
        - Safety validation score
        - Presence of clarification questions
        """
        # Start with OpenAI's confidence (or default 0.75)
        confidence = automation_data.get('confidence', 0.75)
        
        # Reduce if clarification needed
        if automation_data.get('clarification'):
            confidence *= 0.75
        
        # Adjust based on safety score
        if safety_result:
            # Map safety score (0-100) to confidence multiplier (0.5-1.0)
            safety_multiplier = 0.5 + (safety_result.safety_score / 200.0)
            confidence *= safety_multiplier
        
        # Reduce if request is very short (likely ambiguous)
        word_count = len(request.request_text.split())
        if word_count < 5:
            confidence *= 0.85
        elif word_count < 8:
            confidence *= 0.95
        
        # Ensure within bounds
        return min(1.0, max(0.0, confidence))
    
    async def regenerate_with_clarification(
        self,
        original_request: str,
        clarification: str
    ) -> GeneratedAutomation:
        """
        Regenerate automation with additional clarification.
        
        Args:
            original_request: Original NL request
            clarification: User's clarification text
        
        Returns:
            New GeneratedAutomation incorporating clarification
        """
        # Combine original request with clarification
        enhanced_request = NLAutomationRequest(
            request_text=f"{original_request}\n\nAdditional details: {clarification}",
            user_id="default"
        )
        
        logger.info(f"Regenerating with clarification: {clarification}")
        
        # Generate with enhanced request
        return await self.generate(enhanced_request)


def get_nl_generator(
    data_api_client: DataAPIClient,
    openai_client: OpenAIClient,
    safety_validator: SafetyValidator
) -> NLAutomationGenerator:
    """
    Factory function to create NL automation generator.
    
    Args:
        data_api_client: Data API client instance
        openai_client: OpenAI client instance
        safety_validator: Safety validator instance
    
    Returns:
        Configured NLAutomationGenerator
    """
    return NLAutomationGenerator(
        data_api_client=data_api_client,
        openai_client=openai_client,
        safety_validator=safety_validator
    )

