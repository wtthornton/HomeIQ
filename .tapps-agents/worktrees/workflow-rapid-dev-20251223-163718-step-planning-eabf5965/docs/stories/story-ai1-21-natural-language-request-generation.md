# Story AI1.21: Natural Language Request Generation

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.21  
**Priority:** High  
**Estimated Effort:** 10-12 hours  
**Dependencies:** Story AI1.7 (OpenAI Integration), Story AI1.8 (Suggestion Pipeline)

---

## User Story

**As a** user  
**I want** to create automations from natural language requests  
**so that** I can get custom automations without waiting for pattern detection

---

## Business Value

- **On-demand automation creation** - Users don't wait for daily batch analysis
- **User-driven customization** - Create specific automations not discoverable by patterns
- **Improved user experience** - Natural language is easier than writing YAML
- **Complements pattern detection** - Automatic suggestions + user requests
- **Faster time-to-value** - Immediate automation generation vs 24-hour wait

---

## Acceptance Criteria

1. ✅ Accepts natural language automation requests (text input)
2. ✅ Generates valid Home Assistant automation YAML from request
3. ✅ Validates generated automation for safety before presenting to user
4. ✅ Provides device/entity suggestions based on available devices
5. ✅ Handles context: "when window opens" → fetches actual window sensors
6. ✅ Generates confidence score based on request clarity
7. ✅ Supports follow-up questions to clarify ambiguous requests
8. ✅ Processing time <5 seconds for typical requests
9. ✅ Success rate >85% (valid, deployable automations)
10. ✅ Provides explanation of generated automation

---

## Technical Implementation Notes

### Natural Language Automation Generator

**Create: services/ai-automation-service/src/nl_automation_generator.py**

```python
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging
import openai
import yaml
from src.data_api_client import DataAPIClient
from src.safety_validator import SafetyValidator

logger = logging.getLogger(__name__)


@dataclass
class NLAutomationRequest:
    """User's natural language automation request"""
    request_text: str
    user_id: str
    context: Optional[Dict] = None  # Additional context (location, devices, etc.)


@dataclass
class GeneratedAutomation:
    """Result of NL automation generation"""
    automation_yaml: str
    title: str
    description: str
    confidence: float  # 0-1
    explanation: str  # How it works
    clarification_needed: Optional[str] = None  # Questions to ask user
    warnings: List[str] = None  # Potential issues


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
        openai_api_key: str,
        data_api_client: DataAPIClient,
        safety_validator: SafetyValidator,
        model: str = "gpt-4o-mini"
    ):
        self.openai_api_key = openai_api_key
        self.data_api_client = data_api_client
        self.safety_validator = safety_validator
        self.model = model
        openai.api_key = openai_api_key
    
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
        logger.info(f"Generating automation from NL request: {request.request_text}")
        
        # 1. Fetch available devices and entities
        automation_context = await self._build_automation_context()
        
        # 2. Build prompt for OpenAI
        prompt = self._build_prompt(request, automation_context)
        
        # 3. Call OpenAI to generate automation
        try:
            response = await self._call_openai(prompt)
            automation_data = self._parse_openai_response(response)
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return GeneratedAutomation(
                automation_yaml="",
                title="Generation Failed",
                description=f"Failed to generate automation: {e}",
                confidence=0.0,
                explanation="",
                clarification_needed="Could you rephrase your request more specifically?"
            )
        
        # 4. Validate YAML syntax
        try:
            automation_dict = yaml.safe_load(automation_data['yaml'])
        except yaml.YAMLError as e:
            logger.error(f"Generated invalid YAML: {e}")
            # Retry with error feedback
            return await self._retry_generation(request, automation_context, str(e))
        
        # 5. Validate safety
        safety_result = await self.safety_validator.validate(automation_data['yaml'])
        
        # 6. Calculate confidence based on clarity and safety
        confidence = self._calculate_confidence(
            request,
            automation_data,
            safety_result
        )
        
        # 7. Extract warnings from safety validation
        warnings = [
            issue.message
            for issue in safety_result.issues
            if issue.severity in ['warning', 'critical']
        ]
        
        logger.info(
            f"Generated automation '{automation_data['title']}' "
            f"(confidence: {confidence:.0%})"
        )
        
        return GeneratedAutomation(
            automation_yaml=automation_data['yaml'],
            title=automation_data['title'],
            description=automation_data['description'],
            confidence=confidence,
            explanation=automation_data['explanation'],
            clarification_needed=automation_data.get('clarification'),
            warnings=warnings if warnings else None
        )
    
    async def _build_automation_context(self) -> Dict:
        """
        Fetch available devices and entities from data-api.
        
        Provides context to OpenAI about what devices are available.
        """
        try:
            # Fetch from data-api
            devices = await self.data_api_client.get_devices()
            entities = await self.data_api_client.get_entities()
            
            # Organize by domain for easier reference
            devices_by_domain = {}
            for entity in entities:
                domain = entity['entity_id'].split('.')[0]
                if domain not in devices_by_domain:
                    devices_by_domain[domain] = []
                devices_by_domain[domain].append({
                    'entity_id': entity['entity_id'],
                    'friendly_name': entity.get('friendly_name', entity['entity_id']),
                    'area': entity.get('area')
                })
            
            return {
                'devices': devices,
                'entities_by_domain': devices_by_domain,
                'domains': list(devices_by_domain.keys())
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
        
        Includes:
        - Available devices and entities
        - Home Assistant automation structure
        - Safety guidelines
        - Request text
        """
        # Summarize available devices
        device_summary = self._summarize_devices(automation_context)
        
        prompt = f"""You are a Home Assistant automation expert. Generate a valid Home Assistant automation from the user's natural language request.

**Available Devices:**
{device_summary}

**User Request:**
"{request.request_text}"

**Instructions:**
1. Generate a COMPLETE, VALID Home Assistant automation in YAML format
2. Use ONLY devices that exist in the available devices list above
3. If the request is ambiguous, ask for clarification
4. Include appropriate triggers, conditions (if needed), and actions
5. Use friendly, descriptive alias names
6. Add time constraints or conditions for safety where appropriate
7. Explain how the automation works

**Output Format (JSON):**
{{
    "yaml": "alias: Automation Name\\ntrigger:\\n  - platform: ...",
    "title": "Brief title (max 60 chars)",
    "description": "One sentence description",
    "explanation": "Detailed explanation of triggers and actions",
    "clarification": "Questions if request is ambiguous (or null if clear)",
    "confidence": 0.95
}}

**Safety Guidelines:**
- NEVER disable security systems or alarms
- Avoid extreme climate changes (>5°F/2.5°C at once)
- Add time or condition constraints for destructive actions
- Use reasonable defaults for brightness, temperature, etc.
- Avoid "turn off all" unless explicitly requested

Generate the automation now:"""
        
        return prompt
    
    def _summarize_devices(self, automation_context: Dict) -> str:
        """Create human-readable summary of available devices"""
        summary_lines = []
        
        entities_by_domain = automation_context.get('entities_by_domain', {})
        
        # Summarize by domain
        priority_domains = ['light', 'switch', 'climate', 'binary_sensor', 'sensor', 'lock', 'cover']
        
        for domain in priority_domains:
            if domain in entities_by_domain:
                entities = entities_by_domain[domain]
                count = len(entities)
                examples = [e['friendly_name'] for e in entities[:3]]
                
                summary_lines.append(
                    f"- {domain.title()}s ({count}): {', '.join(examples)}"
                    + (f", ..." if count > 3 else "")
                )
        
        return "\n".join(summary_lines) if summary_lines else "No devices found"
    
    async def _call_openai(self, prompt: str) -> Dict:
        """Call OpenAI API with retry logic"""
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Home Assistant automation expert. Generate valid YAML automations from natural language requests."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent output
                max_tokens=1000
            )
            
            return response['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def _parse_openai_response(self, response: str) -> Dict:
        """Parse JSON response from OpenAI"""
        import json
        
        # Try to extract JSON from response (may have markdown formatting)
        if '```json' in response:
            json_start = response.find('```json') + 7
            json_end = response.find('```', json_start)
            response = response[json_start:json_end].strip()
        elif '```' in response:
            json_start = response.find('```') + 3
            json_end = response.find('```', json_start)
            response = response[json_start:json_end].strip()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            logger.debug(f"Response: {response}")
            raise ValueError("OpenAI returned invalid JSON")
    
    async def _retry_generation(
        self,
        request: NLAutomationRequest,
        automation_context: Dict,
        error_message: str
    ) -> GeneratedAutomation:
        """Retry generation with error feedback"""
        retry_prompt = f"""The previous generation failed with error: {error_message}

Please try again, ensuring the YAML is valid and follows Home Assistant automation syntax exactly.

Original request: "{request.request_text}"

{self._build_prompt(request, automation_context)}"""
        
        try:
            response = await self._call_openai(retry_prompt)
            automation_data = self._parse_openai_response(response)
            
            # Validate YAML again
            yaml.safe_load(automation_data['yaml'])
            
            return GeneratedAutomation(
                automation_yaml=automation_data['yaml'],
                title=automation_data['title'],
                description=automation_data['description'],
                confidence=max(0.0, automation_data.get('confidence', 0.7) - 0.2),  # Lower confidence after retry
                explanation=automation_data['explanation']
            )
        except Exception as e:
            logger.error(f"Retry generation also failed: {e}")
            return GeneratedAutomation(
                automation_yaml="",
                title="Generation Failed",
                description=f"Could not generate valid automation: {e}",
                confidence=0.0,
                explanation="",
                clarification_needed="Please describe your automation in more detail or try a simpler request."
            )
    
    def _calculate_confidence(
        self,
        request: NLAutomationRequest,
        automation_data: Dict,
        safety_result
    ) -> float:
        """
        Calculate confidence score for generated automation.
        
        Factors:
        - Request clarity (length, specificity)
        - OpenAI's confidence
        - Safety validation score
        - Presence of clarification questions
        """
        # Start with OpenAI's confidence
        confidence = automation_data.get('confidence', 0.7)
        
        # Reduce if clarification needed
        if automation_data.get('clarification'):
            confidence *= 0.8
        
        # Reduce if safety issues found
        if safety_result.safety_score < 80:
            confidence *= (safety_result.safety_score / 100)
        
        # Reduce if request is very short (ambiguous)
        if len(request.request_text.split()) < 5:
            confidence *= 0.9
        
        return min(1.0, max(0.0, confidence))
```

### REST API Endpoint

**Create: services/ai-automation-service/src/api/nl_generation.py**

```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.nl_automation_generator import NLAutomationGenerator, NLAutomationRequest
from src.database.crud import create_suggestion
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nl", tags=["natural-language"])


class NLGenerationRequest(BaseModel):
    """Request body for NL automation generation"""
    request_text: str
    user_id: str = "default"
    context: dict = {}


@router.post("/generate")
async def generate_automation_from_nl(
    request: NLGenerationRequest,
    generator: NLAutomationGenerator = Depends(get_nl_generator),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate automation from natural language request.
    
    Example request:
    {
        "request_text": "Turn off the heater when any window is open for more than 10 minutes",
        "user_id": "user123"
    }
    
    Returns:
        Generated automation with YAML, explanation, and confidence score
    """
    if not request.request_text or len(request.request_text) < 10:
        raise HTTPException(
            status_code=400,
            detail="Request text must be at least 10 characters"
        )
    
    logger.info(f"NL generation request from {request.user_id}: {request.request_text}")
    
    # Generate automation
    try:
        nl_request = NLAutomationRequest(
            request_text=request.request_text,
            user_id=request.user_id,
            context=request.context
        )
        
        generated = await generator.generate(nl_request)
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate automation: {str(e)}"
        )
    
    # Store as suggestion (status=pending)
    if generated.automation_yaml:
        suggestion = await create_suggestion(
            db,
            title=generated.title,
            description=generated.description,
            automation_yaml=generated.automation_yaml,
            confidence=generated.confidence,
            pattern_id=None,  # No pattern, it's from NL request
            source='nl_request',
            metadata={
                'original_request': request.request_text,
                'explanation': generated.explanation,
                'warnings': generated.warnings
            }
        )
        
        suggestion_id = suggestion.id
    else:
        suggestion_id = None
    
    return {
        "success": generated.automation_yaml != "",
        "suggestion_id": suggestion_id,
        "automation": {
            "yaml": generated.automation_yaml,
            "title": generated.title,
            "description": generated.description,
            "explanation": generated.explanation,
            "confidence": generated.confidence
        },
        "clarification_needed": generated.clarification_needed,
        "warnings": generated.warnings,
        "next_steps": "Review the automation and approve for deployment" if generated.automation_yaml else "Please clarify your request"
    }


@router.post("/clarify")
async def clarify_automation_request(
    suggestion_id: int,
    clarification_text: str,
    generator: NLAutomationGenerator = Depends(get_nl_generator),
    db: AsyncSession = Depends(get_db)
):
    """
    Provide clarification for ambiguous automation request.
    
    Regenerates automation with additional context.
    """
    # Get original suggestion
    suggestion = await get_suggestion_by_id(db, suggestion_id)
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    original_request = suggestion.metadata.get('original_request', '')
    
    # Build new request with clarification
    combined_request = f"{original_request}\n\nClarification: {clarification_text}"
    
    nl_request = NLAutomationRequest(
        request_text=combined_request,
        user_id="default"
    )
    
    # Regenerate
    generated = await generator.generate(nl_request)
    
    # Update suggestion
    await update_suggestion(
        db,
        suggestion_id,
        automation_yaml=generated.automation_yaml,
        description=generated.description,
        confidence=generated.confidence,
        metadata={
            'original_request': combined_request,
            'explanation': generated.explanation,
            'warnings': generated.warnings,
            'clarifications': [clarification_text]
        }
    )
    
    return {
        "success": True,
        "suggestion_id": suggestion_id,
        "automation": {
            "yaml": generated.automation_yaml,
            "title": generated.title,
            "description": generated.description,
            "explanation": generated.explanation,
            "confidence": generated.confidence
        },
        "warnings": generated.warnings
    }
```

### Configuration

**Update: infrastructure/env.ai-automation**

```bash
# Natural Language Generation
AI_NL_GENERATION_ENABLED=true
AI_NL_MODEL=gpt-4o-mini  # or gpt-4o for higher quality
AI_NL_MAX_TOKENS=1000
AI_NL_TEMPERATURE=0.3
```

---

## Integration Verification

**IV1: Generates valid automation from simple request**
- Request: "Turn on kitchen light at 7 AM"
- Verify valid YAML generated
- Verify correct trigger (time) and action (light.turn_on)

**IV2: Uses available devices correctly**
- Request mentions "window sensor"
- Verify uses actual window sensor entity_id from HA
- Verify doesn't hallucinate non-existent devices

**IV3: Handles ambiguous requests**
- Request: "Turn on lights when dark"
- Verify asks clarification (which lights? what time?)

**IV4: Validates safety**
- Request: "Turn off all lights and locks"
- Verify generates automation
- Verify safety warnings included

**IV5: Performance within limits**
- Submit 10 requests
- Verify average processing time <5s
- Check OpenAI API usage

---

## Tasks Breakdown

1. **Create NLAutomationGenerator class** (2.5 hours)
2. **Implement context building (fetch devices)** (1 hour)
3. **Implement prompt engineering** (1.5 hours)
4. **Implement OpenAI integration** (1 hour)
5. **Implement confidence calculation** (1 hour)
6. **Create REST API endpoints** (1.5 hours)
7. **Integrate with suggestion storage** (0.5 hours)
8. **Unit tests** (1.5 hours)
9. **Integration tests with OpenAI** (1 hour)

**Total:** 10-12 hours

---

## Definition of Done

- [ ] NLAutomationGenerator class implemented
- [ ] Context building from data-api working
- [ ] OpenAI integration functional
- [ ] Confidence scoring implemented
- [ ] REST API endpoints created
- [ ] Suggestions stored in database
- [ ] Clarification flow working
- [ ] Unit tests >75% coverage
- [ ] Integration test with OpenAI passes
- [ ] Processing time <5s verified
- [ ] Success rate >85% validated (sample test set)
- [ ] Documentation updated
- [ ] Code reviewed and approved

---

## Testing Strategy

### Unit Tests

```python
# tests/test_nl_generator.py
import pytest
from src.nl_automation_generator import NLAutomationGenerator, NLAutomationRequest

@pytest.fixture
def mock_automation_context():
    return {
        'entities_by_domain': {
            'light': [
                {'entity_id': 'light.kitchen', 'friendly_name': 'Kitchen Light'},
                {'entity_id': 'light.bedroom', 'friendly_name': 'Bedroom Light'}
            ],
            'binary_sensor': [
                {'entity_id': 'binary_sensor.front_door', 'friendly_name': 'Front Door'}
            ]
        }
    }

async def test_simple_request_generation(mock_automation_context):
    """Test generating automation from simple request"""
    generator = NLAutomationGenerator(...)
    
    request = NLAutomationRequest(
        request_text="Turn on kitchen light at 7 AM",
        user_id="test"
    )
    
    result = await generator.generate(request)
    
    assert result.automation_yaml != ""
    assert "light.kitchen" in result.automation_yaml
    assert "07:00" in result.automation_yaml or "07:00:00" in result.automation_yaml
    assert result.confidence > 0.7

async def test_device_context_used(mock_automation_context):
    """Test that available devices are used in generation"""
    # Mock data-api to return specific devices
    # Generate automation mentioning "kitchen light"
    # Verify uses entity_id from mock_automation_context
    pass

async def test_ambiguous_request_asks_clarification():
    """Test that ambiguous requests trigger clarification"""
    request = NLAutomationRequest(
        request_text="Turn on lights",  # Which lights?
        user_id="test"
    )
    
    result = await generator.generate(request)
    
    assert result.clarification_needed is not None
    assert "which" in result.clarification_needed.lower()
```

### Integration Tests

```python
# tests/test_nl_api.py
async def test_nl_generation_endpoint():
    """Test complete NL generation flow via API"""
    response = client.post(
        "/api/nl/generate",
        json={
            "request_text": "Turn on kitchen light when front door opens",
            "user_id": "test_user"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] == True
    assert "suggestion_id" in data
    assert data["automation"]["confidence"] > 0.5
    
    # Verify stored in database
    suggestion = await get_suggestion_by_id(db, data["suggestion_id"])
    assert suggestion is not None
    assert suggestion.source == 'nl_request'
```

---

## Reference Files

**Copy patterns from:**
- Story AI1.7 (OpenAI Integration) for LLM usage
- Story AI1.8 (Suggestion Generation) for suggestion storage
- Story AI1.3 (Data API Integration) for device fetching
- Story AI1.19 (Safety Validation) for validation integration

**Documentation:**
- OpenAI API: https://platform.openai.com/docs/api-reference
- Home Assistant Automation: https://www.home-assistant.io/docs/automation/
- Prompt Engineering: https://platform.openai.com/docs/guides/prompt-engineering

---

## Notes

- **GPT-4o-mini** provides good balance of cost and quality for this task
- **Prompt engineering critical** - include device context and safety guidelines
- **Retry logic important** - OpenAI may generate invalid YAML on first try
- **Cost monitoring** - Track OpenAI API usage and costs
- Future enhancement: Fine-tune model on HA automation examples
- Future enhancement: Support multi-turn conversation for complex automations
- Future enhancement: Learn from user corrections to improve prompts

---

**Story Status:** Ready for Development  
**Assigned To:** TBD  
**Created:** 2025-10-16  
**Updated:** 2025-10-16

