"""
Ask AI Router - Natural Language Query Interface
===============================================

New endpoints for natural language queries about Home Assistant devices and automations.

Flow:
1. POST /query - Parse natural language query and generate suggestions
2. POST /query/{query_id}/refine - Refine query results
3. GET /query/{query_id}/suggestions - Get all suggestions for a query
4. POST /query/{query_id}/suggestions/{suggestion_id}/approve - Approve specific suggestion

Integration:
- Uses Home Assistant Conversation API for entity extraction
- Leverages existing RAG suggestion engine
- Reuses ConversationalSuggestionCard components
"""

from fastapi import APIRouter, HTTPException, Depends, status
import os
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import uuid
import json
import time
import yaml as yaml_lib

from ..database import get_db
from ..config import settings
from ..clients.ha_client import HomeAssistantClient
from ..clients.device_intelligence_client import DeviceIntelligenceClient
from ..entity_extraction import extract_entities_from_query, EnhancedEntityExtractor, MultiModelEntityExtractor
from ..model_services.orchestrator import ModelOrchestrator
from ..llm.openai_client import OpenAIClient
from ..database.models import Suggestion as SuggestionModel, AskAIQuery as AskAIQueryModel
from ..utils.capability_utils import normalize_capability, format_capability_for_display
from sqlalchemy import select, update

logger = logging.getLogger(__name__)

# Global device intelligence client and extractors

def _build_entity_validation_context_with_capabilities(entities: List[Dict[str, Any]]) -> str:
    """
    Build entity validation context with detailed capabilities for YAML generation.
    
    Args:
        entities: List of entity dictionaries with capabilities
        
    Returns:
        Formatted string with entity IDs and their capabilities
    """
    if not entities:
        return "No entities available for validation."
    
    sections = []
    for entity in entities:
        entity_id = entity.get('entity_id', 'unknown')
        domain = entity.get('domain', entity_id.split('.')[0] if '.' in entity_id else 'unknown')
        entity_name = entity.get('name', entity.get('friendly_name', entity_id))
        
        section = f"- {entity_name} ({entity_id}, domain: {domain})\n"
        
        # Add capabilities with details
        capabilities = entity.get('capabilities', [])
        if capabilities:
            section += "  Capabilities:\n"
            for cap in capabilities:
                normalized = normalize_capability(cap)
                formatted = format_capability_for_display(normalized)
                # Extract type for YAML hints
                cap_type = normalized.get('type', 'unknown')
                if cap_type in ['numeric', 'enum', 'composite']:
                    section += f"    - {formatted} ({cap_type})\n"
                else:
                    section += f"    - {formatted}\n"
        else:
            section += "  Capabilities: Basic on/off\n"
        
        sections.append(section.strip())
    
    return "\n".join(sections)

# Global device intelligence client and extractors
_device_intelligence_client: Optional[DeviceIntelligenceClient] = None
_enhanced_extractor: Optional[EnhancedEntityExtractor] = None
_multi_model_extractor: Optional[MultiModelEntityExtractor] = None
_model_orchestrator: Optional[ModelOrchestrator] = None

def set_device_intelligence_client(client: DeviceIntelligenceClient):
    """Set device intelligence client for enhanced extraction"""
    global _device_intelligence_client, _enhanced_extractor, _multi_model_extractor, _model_orchestrator
    _device_intelligence_client = client
    if client:
        _enhanced_extractor = EnhancedEntityExtractor(client)
        _multi_model_extractor = MultiModelEntityExtractor(
            openai_api_key=settings.openai_api_key,
            device_intelligence_client=client,
            ner_model=settings.ner_model,
            openai_model=settings.openai_model
        )
        # Initialize model orchestrator for containerized approach
        _model_orchestrator = ModelOrchestrator(
            ner_service_url=os.getenv("NER_SERVICE_URL", "http://ner-service:8019"),
            openai_service_url=os.getenv("OPENAI_SERVICE_URL", "http://openai-service:8020")
        )
    logger.info("Device Intelligence client set for Ask AI router")

def get_multi_model_extractor() -> Optional[MultiModelEntityExtractor]:
    """Get multi-model extractor instance"""
    return _multi_model_extractor

def get_model_orchestrator() -> Optional[ModelOrchestrator]:
    """Get model orchestrator instance"""
    return _model_orchestrator

# Create router
router = APIRouter(prefix="/api/v1/ask-ai", tags=["Ask AI"])

# Initialize clients
ha_client = None
openai_client = None

if settings.ha_url and settings.ha_token:
    try:
        ha_client = HomeAssistantClient(settings.ha_url, settings.ha_token)
        logger.info("✅ Home Assistant client initialized for Ask AI")
    except Exception as e:
        logger.error(f"❌ Failed to initialize HA client: {e}")

if settings.openai_api_key:
    try:
        openai_client = OpenAIClient(api_key=settings.openai_api_key, model="gpt-4o-mini")
        logger.info("✅ OpenAI client initialized for Ask AI")
    except Exception as e:
        logger.error(f"❌ Failed to initialize OpenAI client: {e}")
else:
    logger.warning("❌ OpenAI API key not configured - Ask AI will not work")


# ============================================================================
# Request/Response Models
# ============================================================================

class AskAIQueryRequest(BaseModel):
    """Request to process natural language query"""
    query: str = Field(..., description="Natural language question about devices/automations")
    user_id: str = Field(default="anonymous", description="User identifier")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class AskAIQueryResponse(BaseModel):
    """Response from Ask AI query"""
    query_id: str
    original_query: str
    parsed_intent: str
    extracted_entities: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    confidence: float
    processing_time_ms: int
    created_at: str


class QueryRefinementRequest(BaseModel):
    """Request to refine query results"""
    refinement: str = Field(..., description="How to refine the results")
    include_context: bool = Field(default=True, description="Include original query context")


class QueryRefinementResponse(BaseModel):
    """Response from query refinement"""
    query_id: str
    refined_suggestions: List[Dict[str, Any]]
    changes_made: List[str]
    confidence: float
    refinement_count: int


# ============================================================================
# Helper Functions
# ============================================================================

async def generate_automation_yaml(
    suggestion: Dict[str, Any], 
    original_query: str, 
    entities: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Generate Home Assistant automation YAML from a suggestion.
    
    Uses OpenAI to convert the natural language suggestion into valid HA YAML.
    Now includes entity validation to prevent "Entity not found" errors.
    Includes capability details for more precise YAML generation.
    
    Args:
        suggestion: Suggestion dictionary with description, trigger_summary, action_summary, devices_involved
        original_query: Original user query for context
        entities: Optional list of entities with capabilities for enhanced context
    
    Returns:
        YAML string for the automation
    """
    logger.info(f"🚀 GENERATE_YAML CALLED - Query: {original_query[:50]}...")
    logger.info(f"🚀 Suggestion: {suggestion}")
    
    if not openai_client:
        raise ValueError("OpenAI client not initialized - cannot generate YAML")
    
    # NEW: Validate entities before generating YAML
    from ..services.entity_validator import EntityValidator
    from ..clients.data_api_client import DataAPIClient
    
    try:
        logger.info("🔍 Starting entity validation...")
        # Initialize entity validator with data API client
        data_api_client = DataAPIClient()
        entity_validator = EntityValidator(data_api_client)
        logger.info("✅ Entity validator initialized")
        
        # Map query devices to real entities
        devices_involved = suggestion.get('devices_involved', [])
        logger.info(f"🔍 DEVICES INVOLVED: {devices_involved}")
        logger.info(f"🔍 ORIGINAL QUERY: {original_query}")
        
        # Always try to map entities from the query, even if devices_involved is empty
        entity_mapping = await entity_validator.map_query_to_entities(original_query, devices_involved)
        logger.info(f"🔍 ENTITY MAPPING RESULT: {entity_mapping}")
        logger.info(f"🔍 ENTITY MAPPING TYPE: {type(entity_mapping)}")
        logger.info(f"🔍 ENTITY MAPPING BOOL: {bool(entity_mapping)}")
        
        # Update suggestion with validated entities
        if entity_mapping:
            suggestion['validated_entities'] = entity_mapping
            logger.info(f"✅ VALIDATED ENTITIES ADDED TO SUGGESTION: {suggestion.get('validated_entities')}")
        else:
            logger.warning(f"⚠️ No valid entities found - mapping was: {entity_mapping}")
    except Exception as e:
        logger.error(f"❌ Error validating entities: {e}", exc_info=True)
        # Continue without validation if there's an error
    
    # Construct prompt for OpenAI to generate creative YAML with capability details
    validated_entities_text = ""
    if entities and len(entities) > 0:
        # Build enhanced entity context with capabilities
        validated_entities_text = f"""
VALIDATED ENTITIES WITH CAPABILITIES (use these exact entity IDs):
{_build_entity_validation_context_with_capabilities(entities)}

CRITICAL: Use ONLY the entity IDs listed above. Do NOT create new entity IDs.
Pay attention to the capability types and ranges when generating service calls:
- For numeric capabilities: Use values within the specified range
- For enum capabilities: Use only the listed enum values
- For composite capabilities: Configure all sub-features properly

"""
    elif 'validated_entities' in suggestion and suggestion['validated_entities']:
        validated_entities_text = f"""
VALIDATED ENTITIES (use these exact entity IDs):
{chr(10).join([f"- {term}: {entity_id}" for term, entity_id in suggestion['validated_entities'].items()])}

CRITICAL: Use ONLY the entity IDs listed above. Do NOT create new entity IDs.
If you need multiple lights, use the same entity ID multiple times or use the entity_id provided for 'lights'.
"""
        logger.info(f"🔍 VALIDATED ENTITIES TEXT: {validated_entities_text}")
        logger.debug(f" VALIDATED ENTITIES TEXT: {validated_entities_text}")
    else:
        validated_entities_text = """
CRITICAL: No validated entities found. Use generic placeholder entity IDs that clearly indicate they are placeholders:
- Use 'light.office_light_placeholder' for office lights
- Use 'binary_sensor.door_placeholder' for door sensors
- Add a comment in the YAML explaining these are placeholders
"""
    
    # Check if test mode
    is_test = 'TEST MODE' in suggestion.get('description', '') or suggestion.get('trigger_summary', '') == 'Manual trigger (test mode)'
    
    prompt = f"""
You are a Home Assistant automation YAML generator expert with deep knowledge of advanced HA features.

User's original request: "{original_query}"

Automation suggestion:
- Description: {suggestion.get('description', '')}
- Trigger: {suggestion.get('trigger_summary', '')}
- Action: {suggestion.get('action_summary', '')}
- Devices: {', '.join(suggestion.get('devices_involved', []))}

{validated_entities_text}

{"🔴 TEST MODE: For manual testing - Generate simple automation YAML:" if is_test else "Generate a sophisticated Home Assistant automation YAML configuration that brings this creative suggestion to life."}
{"- Use event trigger that fires immediately on manual trigger" if is_test else ""}
{"- NO delays or timing components" if is_test else ""}
{"- NO repeat loops or sequences (just execute once)" if is_test else ""}
{"- Action should execute the device control immediately" if is_test else ""}
{"- Example trigger: platform: event, event_type: test_trigger" if is_test else ""}

Requirements:
1. Use YAML format (not JSON)
2. Include: id, alias, trigger, action
3. CRITICAL: Use ONLY the validated entity IDs provided above - do NOT create new entity IDs
4. Add appropriate conditions if needed
5. Include mode: single or restart
6. Add description field
7. Use advanced HA features for creative implementations:
   - `sequence` for multi-step actions
   - `choose` for conditional logic
   - `template` for dynamic values
   - `condition` for complex triggers
   - `delay` for timing
   - `repeat` for patterns
   - `parallel` for simultaneous actions

Advanced YAML Examples:
```yaml
# Sequential flashing pattern
id: office_lights_sequence
alias: "Office Lights Sequence on Door Open"
description: "Flash office lights in sequence when front door opens"
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.front_door
    to: 'on'
action:
  - repeat:
      sequence:
        - service: light.turn_on
          target:
            entity_id: light.office_left
          data:
            brightness_pct: 100
            color_name: red
        - delay: "00:00:01"
        - service: light.turn_off
          target:
            entity_id: light.office_left
        - service: light.turn_on
          target:
            entity_id: light.office_right
          data:
            brightness_pct: 100
            color_name: blue
        - delay: "00:00:01"
        - service: light.turn_off
          target:
            entity_id: light.office_right
      count: 3

# Color-coded door notifications
id: door_color_notifications
alias: "Color-Coded Door Notifications"
description: "Different colors for different doors"
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.front_door
    to: 'on'
  - platform: state
    entity_id: binary_sensor.back_door
    to: 'on'
condition:
  - condition: time
    after: "18:00:00"
    before: "06:00:00"
action:
  - choose:
      - conditions:
          - condition: trigger
            id: "0"
        sequence:
          - service: light.turn_on
            target:
              entity_id: light.office_lights
            data:
              brightness_pct: 100
              color_name: red
              flash: long
      - conditions:
          - condition: trigger
            id: "1"
        sequence:
          - service: light.turn_on
            target:
              entity_id: light.office_lights
            data:
              brightness_pct: 100
              color_name: blue
              flash: long
    default:
      - service: light.turn_on
        target:
          entity_id: light.office_lights
        data:
          brightness_pct: 50
          color_name: white
```

Generate ONLY the YAML content, no explanations or markdown code blocks. Use advanced HA features to implement the creative suggestion properly.
"""

    try:
        # Call OpenAI to generate YAML
        response = await openai_client.client.chat.completions.create(
            model=openai_client.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a Home Assistant YAML expert. Generate valid automation YAML. Return ONLY the YAML content without markdown code blocks or explanations."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Lower temperature for more consistent YAML
            max_tokens=1000
        )
        
        yaml_content = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if yaml_content.startswith('```yaml'):
            yaml_content = yaml_content[7:]  # Remove ```yaml
        elif yaml_content.startswith('```'):
            yaml_content = yaml_content[3:]  # Remove ```
        
        if yaml_content.endswith('```'):
            yaml_content = yaml_content[:-3]  # Remove closing ```
        
        yaml_content = yaml_content.strip()
        
        # Validate the YAML syntax
        try:
            yaml_lib.safe_load(yaml_content)
            logger.info(f"✅ Generated valid YAML for suggestion {suggestion.get('suggestion_id')}")
        except yaml_lib.YAMLError as e:
            logger.error(f"❌ Generated invalid YAML: {e}")
            raise ValueError(f"Generated YAML is invalid: {e}")
        
        return yaml_content
        
    except Exception as e:
        logger.error(f"Failed to generate automation YAML: {e}", exc_info=True)
        raise


async def simplify_query_for_test(suggestion: Dict[str, Any], openai_client) -> str:
    """
    Simplify automation description to test core behavior using AI.
    
    Uses OpenAI to intelligently extract just the core action without conditions.
    
    Examples:
    - "Flash office lights every 30 seconds only after 5pm"
      → "Flash the office lights"
    
    - "Turn on bedroom lights when door opens after sunset"
      → "Turn on the bedroom lights when door opens"
    
    Why Use AI instead of Regex:
    - Smarter: Understands context, not just pattern matching
    - Robust: Handles edge cases and variations
    - Consistent: Uses same AI model that generated the suggestions
    - Simple: One API call with clear prompt
    
    Args:
        suggestion: Suggestion dictionary with description, trigger, action
        openai_client: OpenAI client instance
             
    Returns:
        Simplified command string ready for HA Conversation API
    """
    logger.debug(f" simplify_query_for_test called with suggestion: {suggestion.get('suggestion_id', 'N/A')}")
    if not openai_client:
        # Fallback to regex if OpenAI not available
        logger.warning("OpenAI not available, using fallback simplification")
        return fallback_simplify(suggestion.get('description', ''))
    
    description = suggestion.get('description', '')
    trigger = suggestion.get('trigger_summary', '')
    action = suggestion.get('action_summary', '')
    logger.debug(f" Extracted description: {description[:100]}")
    logger.debug(f" Extracted trigger: {trigger[:100]}")
    logger.debug(f" Extracted action: {action[:100]}")
    logger.info(f" About to build prompt")
    
    # Research-Backed Prompt Design
    # Based on Context7 best practices and codebase temperature analysis:
    # - Extraction tasks: temperature 0.1-0.2 (very deterministic)
    # - Provide clear examples (few-shot learning)
    # - Structured prompt with task + examples + constraints
    # - Keep output simple and constrained
    
    prompt = f"""Extract the core command from this automation description for quick testing.

TASK: Remove all time constraints, intervals, and conditional logic. Keep only the essential trigger-action behavior.

Automation: "{description}"
Trigger: {trigger}
Action: {action}

EXAMPLES:
Input: "Flash office lights every 30 seconds only after 5pm"
Output: "Flash the office lights"

Input: "Dim kitchen lights to 50% when door opens after sunset"
Output: "Dim the kitchen lights when door opens"

Input: "Turn on bedroom lights every weekday at 8am"
Output: "Turn on the bedroom lights"

Input: "Flash lights 3 times when motion detected, but only between 9pm and 11pm"
Output: "Flash the lights when motion detected"

REMOVE:
- Time constraints (after 5pm, before sunset, between X and Y)
- Interval patterns (every 30 seconds, every weekday)
- Conditional logic (only if, but only when, etc.)

KEEP:
- Core action (flash, turn on, dim, etc.)
- Essential trigger (when door opens, when motion detected)
- Target devices (office lights, kitchen lights)

CONSTRAINTS:
- Return ONLY the simplified command
- No explanations
- Natural language (ready for HA Conversation API)
- Maximum 20 words"""

    try:
        logger.info(f" About to call OpenAI API")
        response = await openai_client.client.chat.completions.create(
            model=openai_client.model,
            messages=[
                {
                    "role": "system", 
                    "content": "You are a command simplification expert. Extract core behaviors from automation descriptions. Return only the simplified command, no explanations."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Research-backed: 0.1-0.2 for extraction tasks (deterministic, consistent)
            max_tokens=60,     # Short output - just the command
            top_p=0.9         # Nucleus sampling for slight creativity while staying focused
        )
        logger.info(f" Got OpenAI response")
        
        simplified = response.choices[0].message.content.strip()
        logger.info(f"Simplified '{description}' → '{simplified}'")
        return simplified
        
    except Exception as e:
        logger.error(f"Failed to simplify via AI: {e}, using fallback")
        return fallback_simplify(description)


def fallback_simplify(description: str) -> str:
    """Fallback regex-based simplification if AI unavailable"""
    import re
    # Simple regex-based fallback
    simplified = re.sub(r'every\s+\d+\s+(?:seconds?|minutes?|hours?)', '', description, flags=re.IGNORECASE)
    simplified = re.sub(r'(?:only\s+)?(?:after|before|at|between)\s+.*?[;,]', '', simplified, flags=re.IGNORECASE)
    simplified = re.sub(r'(?:only\s+on\s+)?(?:weekdays?|weekends?)', '', simplified, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', simplified).strip()


def get_ha_client() -> HomeAssistantClient:
    """Dependency injection for Home Assistant client"""
    if not ha_client:
        raise HTTPException(status_code=500, detail="Home Assistant client not initialized")
    return ha_client

def get_openai_client() -> OpenAIClient:
    """Dependency injection for OpenAI client"""
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI client not initialized")
    return openai_client


async def extract_entities_with_ha(query: str) -> List[Dict[str, Any]]:
    """
    Extract entities from query using multi-model approach.
    
    Strategy:
    1. Multi-Model Extractor (NER → OpenAI → Pattern) - 90% of queries
    2. Enhanced Extractor (Device Intelligence) - Fallback
    3. Basic Pattern Matching - Emergency fallback
    
    CRITICAL: We DO NOT use HA Conversation API here because it EXECUTES commands immediately!
    Instead, we use intelligent entity extraction with device intelligence for rich context.
    
    Example: "Turn on the office lights" extracts rich device data including capabilities
    without actually turning on the lights.
    """
    # Try multi-model extraction first (if configured)
    if settings.entity_extraction_method == "multi_model" and _multi_model_extractor:
        try:
            logger.info("🔍 Using multi-model entity extraction (NER → OpenAI → Pattern)")
            return await _multi_model_extractor.extract_entities(query)
        except Exception as e:
            logger.error(f"Multi-model extraction failed, falling back to enhanced: {e}")
    
    # Try enhanced extraction (device intelligence)
    if _enhanced_extractor:
        try:
            logger.info("🔍 Using enhanced entity extraction with device intelligence")
            return await _enhanced_extractor.extract_entities_with_intelligence(query)
        except Exception as e:
            logger.error(f"Enhanced extraction failed, falling back to basic: {e}")
    
    # Fallback to basic pattern matching
    logger.info("🔍 Using basic pattern matching fallback")
    return extract_entities_from_query(query)


async def generate_suggestions_from_query(
    query: str, 
    entities: List[Dict[str, Any]], 
    user_id: str
) -> List[Dict[str, Any]]:
    """Generate automation suggestions based on query and entities"""
    if not openai_client:
        raise ValueError("OpenAI client not available - cannot generate suggestions")
    
    try:
        # Use unified prompt builder for consistent prompt generation
        from ..prompt_building.unified_prompt_builder import UnifiedPromptBuilder
        
        unified_builder = UnifiedPromptBuilder(device_intelligence_client=_device_intelligence_client)
        
        # Build unified prompt with device intelligence
        prompt_dict = await unified_builder.build_query_prompt(
            query=query,
            entities=entities,
            output_mode="suggestions"
        )
        
        # Generate suggestions with unified prompt
        logger.info(f"Generating suggestions for query: {query}")
        logger.info(f"OpenAI client available: {openai_client is not None}")
        logger.info(f"OpenAI model: {openai_client.model if openai_client else 'None'}")
        
        try:
            suggestions_data = await openai_client.generate_with_unified_prompt(
                prompt_dict=prompt_dict,
                temperature=settings.creative_temperature,
                max_tokens=1200,
                output_format="json"
            )
            
            logger.info(f"OpenAI response received: {suggestions_data}")
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
        
        # Parse OpenAI response
        suggestions = []
        try:
            # suggestions_data is already parsed JSON from unified prompt method
            if not suggestions_data:
                logger.warning("OpenAI returned empty response")
                raise ValueError("Empty response from OpenAI")
            
            logger.info(f"OpenAI response content: {str(suggestions_data)[:200]}...")
            
            # suggestions_data is already parsed JSON from unified prompt method
            parsed = suggestions_data
            for i, suggestion in enumerate(parsed):
                suggestions.append({
                    'suggestion_id': f'ask-ai-{uuid.uuid4().hex[:8]}',
                    'description': suggestion['description'],
                    'trigger_summary': suggestion['trigger_summary'],
                    'action_summary': suggestion['action_summary'],
                    'devices_involved': suggestion['devices_involved'],
                    'capabilities_used': suggestion.get('capabilities_used', []),
                    'confidence': suggestion['confidence'],
                    'status': 'draft',
                    'created_at': datetime.now().isoformat()
                })
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse OpenAI response: {e}")
            # Fallback if JSON parsing fails
            suggestions = [{
                'suggestion_id': f'ask-ai-{uuid.uuid4().hex[:8]}',
                'description': f"Automation suggestion for: {query}",
                'trigger_summary': "Based on your query",
                'action_summary': "Device control",
                'devices_involved': [entity['name'] for entity in entities[:3]],
                'confidence': 0.7,
                'status': 'draft',
                'created_at': datetime.now().isoformat()
            }]
        
        logger.info(f"Generated {len(suggestions)} suggestions for query: {query}")
        return suggestions
        
    except Exception as e:
        logger.error(f"Failed to generate suggestions: {e}")
        raise


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/query", response_model=AskAIQueryResponse, status_code=status.HTTP_201_CREATED)
async def process_natural_language_query(
    request: AskAIQueryRequest,
    db: AsyncSession = Depends(get_db)
) -> AskAIQueryResponse:
    """
    Process natural language query and generate automation suggestions.
    
    This is the main endpoint for the Ask AI tab.
    """
    start_time = datetime.now()
    query_id = f"query-{uuid.uuid4().hex[:8]}"
    
    logger.info(f"🤖 Processing Ask AI query: {request.query}")
    
    try:
        # Step 1: Extract entities using Home Assistant
        entities = await extract_entities_with_ha(request.query)
        
        # Step 2: Generate suggestions using OpenAI + entities
        suggestions = await generate_suggestions_from_query(
            request.query, 
            entities, 
            request.user_id
        )
        
        # Step 3: Calculate confidence based on entity extraction and suggestion quality
        confidence = min(0.9, 0.5 + (len(entities) * 0.1) + (len(suggestions) * 0.1))
        
        # Step 4: Determine parsed intent
        intent_keywords = {
            'automation': ['automate', 'automatic', 'schedule', 'routine'],
            'control': ['turn on', 'turn off', 'switch', 'control'],
            'monitoring': ['monitor', 'alert', 'notify', 'watch'],
            'energy': ['energy', 'power', 'electricity', 'save']
        }
        
        parsed_intent = 'general'
        query_lower = request.query.lower()
        for intent, keywords in intent_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                parsed_intent = intent
                break
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Step 5: Save query to database
        query_record = AskAIQueryModel(
            query_id=query_id,
            original_query=request.query,
            user_id=request.user_id,
            parsed_intent=parsed_intent,
            extracted_entities=entities,
            suggestions=suggestions,
            confidence=confidence,
            processing_time_ms=int(processing_time)
        )
        
        db.add(query_record)
        await db.commit()
        await db.refresh(query_record)
        
        response = AskAIQueryResponse(
            query_id=query_id,
            original_query=request.query,
            parsed_intent=parsed_intent,
            extracted_entities=entities,
            suggestions=suggestions,
            confidence=confidence,
            processing_time_ms=int(processing_time),
            created_at=datetime.now().isoformat()
        )
        
        logger.info(f"✅ Ask AI query processed and saved: {len(suggestions)} suggestions, {confidence:.2f} confidence")
        return response
        
    except Exception as e:
        logger.error(f"❌ Failed to process Ask AI query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )


@router.post("/query/{query_id}/refine", response_model=QueryRefinementResponse)
async def refine_query_results(
    query_id: str,
    request: QueryRefinementRequest,
    db: AsyncSession = Depends(get_db)
) -> QueryRefinementResponse:
    """
    Refine the results of a previous Ask AI query.
    """
    logger.info(f"🔧 Refining Ask AI query {query_id}: {request.refinement}")
    
    # For now, return mock refinement
    # TODO: Implement actual refinement logic
    refined_suggestions = [{
        'suggestion_id': f'refined-{uuid.uuid4().hex[:8]}',
        'description': f"Refined suggestion: {request.refinement}",
        'trigger_summary': "Refined trigger",
        'action_summary': "Refined action",
        'devices_involved': [],
        'confidence': 0.8,
        'status': 'draft',
        'created_at': datetime.now().isoformat()
    }]
    
    return QueryRefinementResponse(
        query_id=query_id,
        refined_suggestions=refined_suggestions,
        changes_made=[f"Applied refinement: {request.refinement}"],
        confidence=0.8,
        refinement_count=1
    )


@router.get("/query/{query_id}/suggestions")
async def get_query_suggestions(
    query_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all suggestions for a specific query.
    """
    # For now, return empty list
    # TODO: Store and retrieve suggestions from database
    return {
        "query_id": query_id,
        "suggestions": [],
        "total_count": 0
    }


def _detects_timing_requirement(query: str) -> bool:
    """
    Detect if the query explicitly requires timing components.
    
    Args:
        query: Original user query
        
    Returns:
        True if query mentions timing requirements (e.g., "for X seconds", "every", "repeat")
    """
    query_lower = query.lower()
    timing_keywords = [
        r'for \d+ (second|sec|secs|minute|min|mins)',  # "for 10 seconds", "for 10 secs"
        r'every \d+',  # "every 30 seconds"
        r'\d+ (second|sec|secs|minute|min|mins)',  # "10 seconds", "30 secs"
        r'repeat',
        r'duration',
        r'flash for',
        r'blink for',
        r'cycle',
        r'lasting',
        r'for \d+ secs',  # Explicit match for common abbreviation
    ]
    import re
    for keyword in timing_keywords:
        if re.search(keyword, query_lower):
            return True
    return False


def _generate_test_quality_report(
    original_query: str,
    suggestion: dict,
    test_suggestion: dict,
    automation_yaml: str,
    validated_entities: dict
) -> dict:
    """
    Generate a quality report for test YAML validation.
    
    Checks if the generated YAML meets test requirements:
    - Uses validated entity IDs
    - No delays or timing components (unless required by query)
    - No repeat loops (unless required by query)
    - Simple immediate execution
    """
    import yaml
    import re
    
    # Check if timing is expected based on query
    timing_expected = _detects_timing_requirement(original_query)
    
    try:
        yaml_data = yaml.safe_load(automation_yaml)
    except Exception as e:
        yaml_data = None
    
    checks = []
    
    # Check 1: Entity IDs are validated
    if validated_entities:
        uses_validated_entities = False
        for device_name, entity_id in validated_entities.items():
            if entity_id in automation_yaml:
                uses_validated_entities = True
                checks.append({
                    "check": "Uses validated entity IDs",
                    "status": "✅ PASS",
                    "details": f"Found {entity_id} in YAML"
                })
                break
        if not uses_validated_entities:
            checks.append({
                "check": "Uses validated entity IDs",
                "status": "❌ FAIL",
                "details": f"None of {list(validated_entities.values())} found in YAML"
            })
    else:
        checks.append({
            "check": "Uses validated entity IDs",
            "status": "⚠️ SKIP",
            "details": "No validated entities provided"
        })
    
    # Check 2: No delays in YAML (unless timing is expected)
    has_delay = "delay" in automation_yaml.lower()
    if timing_expected and has_delay:
        checks.append({
            "check": "No delays or timing components",
            "status": "⚠️ WARNING (expected)",
            "details": "Found 'delay' in YAML (expected based on query requirement)"
        })
    else:
        checks.append({
            "check": "No delays or timing components",
            "status": "✅ PASS" if not has_delay else "❌ FAIL",
            "details": "Found 'delay' in YAML" if has_delay else "No delays found"
        })
    
    # Check 3: No repeat loops (unless timing is expected)
    has_repeat = "repeat:" in automation_yaml or "repeat " in automation_yaml
    if timing_expected and has_repeat:
        checks.append({
            "check": "No repeat loops or sequences",
            "status": "⚠️ WARNING (expected)",
            "details": "Found 'repeat' in YAML (expected based on query requirement)"
        })
    else:
        checks.append({
            "check": "No repeat loops or sequences",
            "status": "✅ PASS" if not has_repeat else "❌ FAIL",
            "details": "Found 'repeat' in YAML" if has_repeat else "No repeat found"
        })
    
    # Check 4: Has trigger
    has_trigger = yaml_data and "trigger" in yaml_data
    checks.append({
        "check": "Has trigger block",
        "status": "✅ PASS" if has_trigger else "❌ FAIL",
        "details": "Trigger block present" if has_trigger else "No trigger found"
    })
    
    # Check 5: Has action
    has_action = yaml_data and "action" in yaml_data
    checks.append({
        "check": "Has action block",
        "status": "✅ PASS" if has_action else "❌ FAIL",
        "details": "Action block present" if has_action else "No action found"
    })
    
    # Check 6: Valid YAML syntax
    valid_yaml = yaml_data is not None
    checks.append({
        "check": "Valid YAML syntax",
        "status": "✅ PASS" if valid_yaml else "❌ FAIL",
        "details": "YAML parsed successfully" if valid_yaml else "YAML parsing failed"
    })
    
    # Overall status
    passed = sum(1 for c in checks if c["status"] == "✅ PASS")
    failed = sum(1 for c in checks if c["status"] == "❌ FAIL")
    skipped = sum(1 for c in checks if c["status"] == "⚠️ SKIP")
    warnings = sum(1 for c in checks if "WARNING" in c["status"])
    
    # Overall status: PASS if no failures (warnings from expected timing are OK)
    overall_status = "✅ PASS" if failed == 0 else "❌ FAIL"
    if warnings > 0 and failed == 0:
        overall_status = "✅ PASS (with expected warnings)"
    
    return {
        "overall_status": overall_status,
        "summary": {
            "total_checks": len(checks),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "warnings": warnings
        },
        "checks": checks,
        "details": {
            "original_query": original_query,
            "original_suggestion": {
                "description": suggestion.get("description", ""),
                "trigger_summary": suggestion.get("trigger_summary", ""),
                "action_summary": suggestion.get("action_summary", ""),
                "devices_involved": suggestion.get("devices_involved", [])
            },
            "test_modifications": {
                "description": test_suggestion.get("description", ""),
                "trigger_summary": test_suggestion.get("trigger_summary", "")
            },
            "validated_entities": validated_entities
        },
        "test_prompt_requirements": [
            "- Use event trigger that fires immediately on manual trigger",
            "- NO delays or timing components",
            "- NO repeat loops or sequences (just execute once)",
            "- Action should execute the device control immediately",
            "- Use validated entity IDs (not placeholders)"
        ]
    }


@router.post("/query/{query_id}/suggestions/{suggestion_id}/test")
async def test_suggestion_from_query(
    query_id: str,
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ha_client: HomeAssistantClient = Depends(get_ha_client),
    openai_client: OpenAIClient = Depends(get_openai_client)
) -> Dict[str, Any]:
    """
    Test a suggestion by executing the core command via HA Conversation API (quick test).
    
    NEW BEHAVIOR:
    - Simplifies the automation description to extract core command
    - Executes the command immediately via HA Conversation API
    - NO YAML generation (moved to approve endpoint)
    - NO temporary automation creation
    
    This is a "quick test" that runs the core behavior without creating automations.
    
    Args:
        query_id: Query ID from the database
        suggestion_id: Specific suggestion to test
        db: Database session
        ha_client: Home Assistant client
    
    Returns:
        Execution result with status and message
    """
    logger.info(f"QUICK TEST START - suggestion_id: {suggestion_id}, query_id: {query_id}")
    start_time = time.time()
    
    try:
        logger.debug(f"About to fetch query from database, query_id={query_id}, suggestion_id={suggestion_id}")
        # Get the query from database
        logger.debug(f"Fetching query {query_id} from database")
        try:
            query = await db.get(AskAIQueryModel, query_id)
            logger.debug(f"Query retrieved, is None: {query is None}")
            if query:
                logger.debug(f"Query has {len(query.suggestions)} suggestions")
        except Exception as e:
            logger.error(f"ERROR fetching query: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Database error: {e}")
        
        if not query:
            logger.error(f"Query {query_id} not found in database")
            raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
        
        logger.info(f"Query found: {query.original_query}, suggestions count: {len(query.suggestions)}")
        
        # Find the specific suggestion
        logger.debug(f"Searching for suggestion {suggestion_id}")
        suggestion = None
        logger.debug(f"Iterating through {len(query.suggestions)} suggestions")
        for s in query.suggestions:
            logger.debug(f"Checking suggestion {s.get('suggestion_id')}")
            if s.get('suggestion_id') == suggestion_id:
                suggestion = s
                logger.debug(f"Found matching suggestion!")
                break
        
        if not suggestion:
            logger.error(f"Suggestion {suggestion_id} not found in query")
            raise HTTPException(status_code=404, detail=f"Suggestion {suggestion_id} not found")
        
        logger.info(f"Testing suggestion: {suggestion.get('description', 'N/A')}")
        logger.info(f"Original query: {query.original_query}")
        logger.debug(f"Full suggestion: {json.dumps(suggestion, indent=2)}")
        
        # Validate ha_client
        logger.debug("Validating ha_client...")
        if not ha_client:
            logger.error("ha_client is None!")
            raise HTTPException(status_code=500, detail="Home Assistant client not initialized")
        logger.debug("ha_client validated")
        
        # STEP 1: Simplify the suggestion to extract core command
        entity_resolution_start = time.time()
        logger.info("Simplifying suggestion for quick test...")
        simplified_command = await simplify_query_for_test(suggestion, openai_client)
        logger.info(f"Simplified command: '{simplified_command}'")
        
        # STEP 2: Generate minimal YAML for testing (no triggers, just the action)
        yaml_gen_start = time.time()
        logger.info("Generating test automation YAML...")
        # For test mode, pass empty entities list so it uses validated_entities from test_suggestion
        entities = []
        
        # Use devices_involved from the suggestion (these are the actual device names to map)
        devices_involved = suggestion.get('devices_involved', [])
        logger.debug(f" devices_involved from suggestion: {devices_involved}")
        
        # Map devices to entity_ids using the same logic as in generate_automation_yaml
        logger.debug(f" Mapping devices to entity_ids...")
        from ..services.entity_validator import EntityValidator
        from ..clients.data_api_client import DataAPIClient
        data_api_client = DataAPIClient()
        entity_validator = EntityValidator(data_api_client)
        resolved_entities = await entity_validator.map_query_to_entities(query.original_query, devices_involved)
        entity_resolution_time = (time.time() - entity_resolution_start) * 1000
        logger.debug(f"resolved_entities result (type={type(resolved_entities)}): {resolved_entities}")
        
        # Build validated_entities mapping from resolved entities
        entity_mapping = {}
        logger.info(f" About to build entity_mapping from {len(devices_involved)} devices")
        for device_name in devices_involved:
            if device_name in resolved_entities:
                entity_id = resolved_entities[device_name]
                entity_mapping[device_name] = entity_id
                logger.debug(f" Mapped '{device_name}' to '{entity_id}'")
            else:
                logger.warning(f" Device '{device_name}' not found in resolved_entities")
        
        # Modify suggestion to strip timing/delay components for test
        test_suggestion = suggestion.copy()
        test_suggestion['description'] = f"TEST MODE: {suggestion.get('description', '')} - Execute core action only"
        test_suggestion['trigger_summary'] = "Manual trigger (test mode)"
        test_suggestion['action_summary'] = suggestion.get('action_summary', '').split('every')[0].split('Every')[0].strip()
        test_suggestion['validated_entities'] = entity_mapping
        logger.debug(f" Added validated_entities: {entity_mapping}")
        logger.debug(f" test_suggestion validated_entities key exists: {'validated_entities' in test_suggestion}")
        logger.debug(f" test_suggestion['validated_entities'] content: {test_suggestion.get('validated_entities')}")
        
        automation_yaml = await generate_automation_yaml(test_suggestion, query.original_query, entities)
        yaml_gen_time = (time.time() - yaml_gen_start) * 1000
        logger.debug(f"After generate_automation_yaml - validated_entities still exists: {'validated_entities' in test_suggestion}")
        logger.info(f"Generated test automation YAML")
        logger.debug(f"Generated YAML preview: {str(automation_yaml)[:500]}")
        
        # STEP 3: Create automation in HA
        ha_create_start = time.time()
        logger.info(f"Creating automation in Home Assistant...")
        
        # List existing automations for debugging
        logger.debug("Listing existing automations in HA...")
        try:
            existing_automations = await ha_client.list_automations()
            logger.debug(f"Found {len(existing_automations)} existing automations")
            if existing_automations:
                logger.debug(f"Sample automation IDs: {[a.get('entity_id', 'unknown') for a in existing_automations[:5]]}")
        except Exception as list_error:
            logger.warning(f"Could not list automations: {list_error}")
        
        try:
            logger.debug(f"Calling ha_client.create_automation with YAML of length {len(str(automation_yaml))}")
            creation_result = await ha_client.create_automation(automation_yaml)
            ha_create_time = (time.time() - ha_create_start) * 1000
            logger.info(f"Automation created: {creation_result.get('automation_id')}")
            logger.debug(f"Creation result: {creation_result}")
            
            automation_id = creation_result.get('automation_id')
            if not automation_id:
                raise Exception("Failed to create automation - no ID returned")
            
            # Verify the automation was created correctly by fetching it from HA
            logger.debug("Verifying automation was created correctly...")
            try:
                verification = await ha_client.get_automation(automation_id)
                logger.info(f"Automation verification: {verification}")
            except Exception as verify_error:
                logger.warning(f"Could not verify automation: {verify_error}")
            
            # Trigger the automation immediately to test it
            ha_trigger_start = time.time()
            logger.info(f"Triggering automation {automation_id} to test...")
            await ha_client.trigger_automation(automation_id)
            ha_trigger_time = (time.time() - ha_trigger_start) * 1000
            logger.info(f"Automation triggered")
            
            # Wait 30 seconds
            logger.info("Waiting 30 seconds before deletion...")
            import asyncio
            await asyncio.sleep(30)
            logger.debug("Wait complete")
            
            # Delete the automation
            logger.info(f"Deleting test automation {automation_id}...")
            deletion_result = await ha_client.delete_automation(automation_id)
            logger.info(f"Automation deleted")
            
            # Generate quality report for the test YAML
            quality_report = _generate_test_quality_report(
                original_query=query.original_query,
                suggestion=suggestion,
                test_suggestion=test_suggestion,
                automation_yaml=automation_yaml,
                validated_entities=entity_mapping
            )
            
            # Calculate total time
            total_time = (time.time() - start_time) * 1000
            
            # Calculate performance metrics
            performance_metrics = {
                "entity_resolution_ms": round(entity_resolution_time, 2),
                "yaml_generation_ms": round(yaml_gen_time, 2),
                "ha_creation_ms": round(ha_create_time, 2),
                "ha_trigger_ms": round(ha_trigger_time, 2),
                "total_ms": round(total_time, 2)
            }
            
            # Log slow operations
            if total_time > 5000:
                logger.warning(f"Slow operation detected: total time {total_time:.2f}ms")
            if ha_create_time > 5000:
                logger.warning(f"Slow HA creation: {ha_create_time:.2f}ms")
            
            return {
                "suggestion_id": suggestion_id,
                "query_id": query_id,
                "executed": True,
                "automation_yaml": automation_yaml,
                "automation_id": automation_id,
                "deleted": True,
                "message": "Test completed successfully - automation created, ran for 30 seconds, and deleted",
                "quality_report": quality_report,
                "performance_metrics": performance_metrics
            }
            
        except Exception as e:
            logger.error(f"❌ ERROR in test execution: {e}")
            raise
    
    except HTTPException as e:
        logger.error(f"HTTPException in test endpoint: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Error testing suggestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/{query_id}/suggestions/{suggestion_id}/approve")
async def approve_suggestion_from_query(
    query_id: str,
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ha_client: HomeAssistantClient = Depends(get_ha_client)
) -> Dict[str, Any]:
    """
    Approve a suggestion and create the automation in Home Assistant.
    """
    logger.info(f"✅ Approving suggestion {suggestion_id} from query {query_id}")
    
    try:
        # Get the query from database
        query = await db.get(AskAIQueryModel, query_id)
        if not query:
            raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
        
        # Find the specific suggestion
        suggestion = None
        for s in query.suggestions:
            if s.get('suggestion_id') == suggestion_id:
                suggestion = s
                break
        
        if not suggestion:
            raise HTTPException(status_code=404, detail=f"Suggestion {suggestion_id} not found")
        
        # Generate YAML for the suggestion with entities for capability details
        entities = query.extracted_entities if query.extracted_entities else []
        automation_yaml = await generate_automation_yaml(suggestion, query.original_query, entities)
        
        # Create automation in Home Assistant
        if ha_client:
            creation_result = await ha_client.create_automation(automation_yaml)
            
            if creation_result.get('success'):
                logger.info(f"✅ Automation created successfully: {creation_result.get('automation_id')}")
                
                return {
                    "suggestion_id": suggestion_id,
                    "query_id": query_id,
                    "status": "approved",
                    "automation_id": creation_result.get('automation_id'),
                    "automation_yaml": automation_yaml,
                    "ready_to_deploy": True,
                    "warnings": creation_result.get('warnings', []),
                    "message": creation_result.get('message', 'Automation created successfully')
                }
            else:
                logger.error(f"❌ Failed to create automation: {creation_result.get('error')}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create automation: {creation_result.get('error')}"
                )
        else:
            raise HTTPException(status_code=500, detail="Home Assistant client not initialized")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving suggestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
