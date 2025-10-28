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
    else:
        validated_entities_text = """
CRITICAL: No validated entities found. Use generic placeholder entity IDs that clearly indicate they are placeholders:
- Use 'light.office_light_placeholder' for office lights
- Use 'binary_sensor.door_placeholder' for door sensors
- Add a comment in the YAML explaining these are placeholders
"""
    
    prompt = f"""
You are a Home Assistant automation YAML generator expert with deep knowledge of advanced HA features.

User's original request: "{original_query}"

Automation suggestion:
- Description: {suggestion.get('description', '')}
- Trigger: {suggestion.get('trigger_summary', '')}
- Action: {suggestion.get('action_summary', '')}
- Devices: {', '.join(suggestion.get('devices_involved', []))}

{validated_entities_text}

Generate a sophisticated Home Assistant automation YAML configuration that brings this creative suggestion to life.

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
    if not openai_client:
        # Fallback to regex if OpenAI not available
        logger.warning("OpenAI not available, using fallback simplification")
        return fallback_simplify(suggestion.get('description', ''))
    
    description = suggestion.get('description', '')
    trigger = suggestion.get('trigger_summary', '')
    action = suggestion.get('action_summary', '')
    
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


@router.post("/query/{query_id}/suggestions/{suggestion_id}/test")
async def test_suggestion_from_query(
    query_id: str,
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ha_client: HomeAssistantClient = Depends(get_ha_client)
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
    logger.info(f"🧪 QUICK TEST - suggestion_id: {suggestion_id}, query_id: {query_id}")
    
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
        
        logger.info(f"🔍 Testing suggestion: {suggestion.get('description', 'N/A')}")
        logger.info(f"🔍 Original query: {query.original_query}")
        
        # Validate ha_client
        if not ha_client:
            raise HTTPException(status_code=500, detail="Home Assistant client not initialized")
        
        # STEP 1: Simplify the suggestion to extract core command
        logger.info("🔧 Simplifying suggestion for quick test...")
        simplified_command = await simplify_query_for_test(suggestion, openai_client)
        logger.info(f"✅ Simplified command: '{simplified_command}'")
        
        # STEP 2: Execute the command via HA Conversation API
        logger.info(f"⚡ Executing command via HA Conversation API: '{simplified_command}'")
        conversation_result = await ha_client.conversation_process(simplified_command)
        
        # STEP 3: Parse the conversation result and return
        # HA Conversation API returns: {response: str, language: str, entities: [], etc.}
        response_text = conversation_result.get('response', 'No response from HA')
        # If we got a response, the command was likely executed
        executed = bool(response_text and response_text != 'No response from HA')
        
        logger.info(f"🔍 Conversation result: {conversation_result}")
        logger.info(f"{'✅' if executed else '⚠️'} Command executed: {executed}")
        
        return {
            "suggestion_id": suggestion_id,
            "query_id": query_id,
            "executed": executed,
            "command": simplified_command,
            "original_description": suggestion.get('description', ''),
            "response": response_text,
            "message": (
                f"✅ Quick test successful! Command '{simplified_command}' was executed. "
                f"{response_text}"
            ) if executed else (
                f"⚠️ Quick test failed. Command '{simplified_command}' could not be executed. "
                f"Error: {response_text}"
            )
        }
    
    except HTTPException:
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
