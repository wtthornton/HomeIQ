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

from fastapi import APIRouter, HTTPException, Depends, status, Body, Query
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
from ..services.entity_attribute_service import EntityAttributeService
from ..prompt_building.entity_context_builder import EntityContextBuilder
from ..services.component_detector import ComponentDetector
from ..services.safety_validator import SafetyValidator
from ..services.yaml_self_correction import YAMLSelfCorrectionService
from ..services.clarification import (
    ClarificationDetector,
    QuestionGenerator,
    AnswerValidator,
    ConfidenceCalculator,
    ClarificationSession,
    ClarificationQuestion,
    ClarificationAnswer
)
from sqlalchemy import select, update
import asyncio

# Use service logger instead of module logger for proper JSON logging
logger = logging.getLogger("ai-automation-service")
# Also log to stderr to ensure we see output
import sys
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
console_handler.setFormatter(console_formatter)
if console_handler not in logger.handlers:
    logger.addHandler(console_handler)
logger.info("🔧 Ask AI Router logger initialized")

# Global device intelligence client and extractors

def _build_entity_validation_context_with_comprehensive_data(entities: List[Dict[str, Any]], enriched_data: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
    """
    Build entity validation context with COMPREHENSIVE data from ALL sources.
    
    Uses enriched_data (comprehensive enrichment) when available, falls back to entities list.
    
    Args:
        entities: List of entity dictionaries (fallback if enriched_data not available)
        enriched_data: Comprehensive enriched data dictionary mapping entity_id to all available data
        
    Returns:
        Formatted string with ALL available entity information
    """
    from ..services.comprehensive_entity_enrichment import format_comprehensive_enrichment_for_prompt
    
    # Use comprehensive enrichment if available
    if enriched_data:
        logger.info(f"📋 Building context from comprehensive enrichment ({len(enriched_data)} entities)")
        return format_comprehensive_enrichment_for_prompt(enriched_data)
    
    # Fallback to basic entities list
    if not entities:
        return "No entities available for validation."
    
    logger.info(f"📋 Building context from entities list ({len(entities)} entities)")
    sections = []
    for entity in entities:
        entity_id = entity.get('entity_id', 'unknown')
        domain = entity.get('domain', entity_id.split('.')[0] if '.' in entity_id else 'unknown')
        entity_name = entity.get('name', entity.get('friendly_name', entity_id))
        
        section = f"- {entity_name} ({entity_id}, domain: {domain})\n"
        
        # Add location if available
        if entity.get('area_name'):
            section += f"  Location: {entity['area_name']}\n"
        elif entity.get('area_id'):
            section += f"  Location: {entity['area_id']}\n"
        
        # Add device info if available
        device_info = []
        if entity.get('manufacturer'):
            device_info.append(entity['manufacturer'])
        if entity.get('model'):
            device_info.append(entity['model'])
        if device_info:
            section += f"  Device: {' '.join(device_info)}\n"
        
        # Add health score if available
        if entity.get('health_score') is not None:
            health_status = "Excellent" if entity['health_score'] > 80 else "Good" if entity['health_score'] > 60 else "Fair"
            section += f"  Health: {entity['health_score']}/100 ({health_status})\n"
        
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
        
        # Add integration if available
        if entity.get('integration') and entity.get('integration') != 'unknown':
            section += f"  Integration: {entity['integration']}\n"
        
        # Add supported features if available
        if entity.get('supported_features'):
            section += f"  Supported Features: {entity['supported_features']}\n"
        
        sections.append(section.strip())
    
    return "\n".join(sections)


def _build_entity_validation_context_with_capabilities(entities: List[Dict[str, Any]]) -> str:
    """Backwards compatibility wrapper."""
    return _build_entity_validation_context_with_comprehensive_data(entities, enriched_data=None)

# Global device intelligence client and extractors
_device_intelligence_client: Optional[DeviceIntelligenceClient] = None
_enhanced_extractor: Optional[EnhancedEntityExtractor] = None
_multi_model_extractor: Optional[MultiModelEntityExtractor] = None
_model_orchestrator: Optional[ModelOrchestrator] = None
_self_correction_service: Optional[YAMLSelfCorrectionService] = None

def get_self_correction_service() -> Optional[YAMLSelfCorrectionService]:
    """Get self-correction service singleton"""
    global _self_correction_service
    if _self_correction_service is None:
        if openai_client and hasattr(openai_client, 'client'):
            # Pass the AsyncOpenAI client from OpenAIClient wrapper
            # Also pass HA client and device intelligence client for device name lookup
            _self_correction_service = YAMLSelfCorrectionService(
                openai_client.client,
                ha_client=ha_client,
                device_intelligence_client=_device_intelligence_client
            )
            logger.info("✅ YAML self-correction service initialized with device DB access")
        else:
            logger.warning("⚠️ Cannot initialize self-correction service - OpenAI client not available")
    return _self_correction_service

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

# Initialize clients (will be set later)
ha_client = None
openai_client = None

# Dependency injection functions (use closures to access global variables)
def get_ha_client() -> HomeAssistantClient:
    """Dependency injection for Home Assistant client"""
    global ha_client
    if not ha_client:
        raise HTTPException(status_code=500, detail="Home Assistant client not initialized")
    return ha_client

def get_openai_client() -> OpenAIClient:
    """Dependency injection for OpenAI client"""
    global openai_client
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI client not initialized")
    return openai_client


# ============================================================================
# Reverse Engineering Analytics Endpoint
# ============================================================================

@router.get("/analytics/reverse-engineering")
async def get_reverse_engineering_analytics(
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    Get analytics and insights for reverse engineering performance.
    
    Provides aggregated metrics including:
    - Similarity improvements
    - Performance metrics (iterations, time, cost)
    - Automation success rates
    - Value indicators and KPIs
    
    Args:
        days: Number of days to analyze (default: 30)
        db: Database session
        
    Returns:
        Dictionary with comprehensive analytics
    """
    try:
        from ..services.reverse_engineering_metrics import get_reverse_engineering_analytics
        
        analytics = await get_reverse_engineering_analytics(db_session=db, days=days)
        
        return {
            "status": "success",
            "analytics": analytics
        }
    except Exception as e:
        logger.error(f"❌ Failed to get reverse engineering analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analytics: {str(e)}"
        )


@router.get("/entities/search")
async def search_entities(
    domain: Optional[str] = Query(None, description="Filter by domain (light, switch, sensor, etc.)"),
    search_term: Optional[str] = Query(None, description="Search term to match against entity_id or friendly_name"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    ha_client: HomeAssistantClient = Depends(get_ha_client)
) -> List[Dict[str, Any]]:
    """
    Search available entities for device mapping.
    
    Used by the frontend to show alternative entities when users want to change
    which entity_id maps to a friendly_name in an automation suggestion.
    
    Args:
        domain: Optional domain filter (e.g., "light", "switch", "sensor")
        search_term: Optional search term to filter by entity_id or friendly_name
        limit: Maximum number of results to return
        ha_client: Home Assistant client for fetching entities
        
    Returns:
        List of entity dictionaries with entity_id, friendly_name, domain, state, and attributes
    """
    try:
        from ..clients.data_api_client import DataAPIClient
        
        logger.info(f"🔍 Searching entities - domain: {domain}, search_term: {search_term}, limit: {limit}")
        
        # Use DataAPIClient to fetch entities
        data_api_client = DataAPIClient()
        
        # Fetch entities from data-api
        entities = await data_api_client.fetch_entities(
            domain=domain,
            limit=limit * 2  # Fetch more than needed for filtering
        )
        
        # Filter by search_term if provided
        if search_term:
            search_lower = search_term.lower()
            entities = [
                e for e in entities
                if search_lower in e.get('entity_id', '').lower() or
                   search_lower in e.get('friendly_name', '').lower()
            ]
        
        # Limit results
        entities = entities[:limit]
        
        # Enrich with state and attributes from HA if available
        enriched_entities = []
        for entity in entities:
            entity_id = entity.get('entity_id')
            if not entity_id:
                continue
                
            enriched = {
                'entity_id': entity_id,
                'friendly_name': entity.get('friendly_name', entity_id),
                'domain': entity.get('domain', entity_id.split('.')[0] if '.' in entity_id else 'unknown'),
                'device_id': entity.get('device_id'),
                'area_id': entity.get('area_id'),
                'platform': entity.get('platform')
            }
            
            # Try to get current state and attributes from HA
            if ha_client:
                try:
                    state_data = await ha_client.get_entity_state(entity_id)
                    if state_data:
                        enriched['state'] = state_data.get('state')
                        enriched['attributes'] = state_data.get('attributes', {})
                        
                        # Extract capabilities from attributes if available
                        supported_features = enriched['attributes'].get('supported_features', 0)
                        capabilities = []
                        if enriched['domain'] == 'light':
                            if supported_features & 1:  # SUPPORT_BRIGHTNESS
                                capabilities.append('brightness')
                            if supported_features & 2:  # SUPPORT_COLOR_TEMP
                                capabilities.append('color_temp')
                            if supported_features & 16:  # SUPPORT_EFFECT
                                capabilities.append('effect')
                            if supported_features & 32:  # SUPPORT_RGB_COLOR
                                capabilities.append('rgb_color')
                        enriched['capabilities'] = capabilities
                except Exception as e:
                    logger.debug(f"Could not fetch state for {entity_id}: {e}")
            
            enriched_entities.append(enriched)
        
        logger.info(f"✅ Found {len(enriched_entities)} entities matching search criteria")
        return enriched_entities
        
    except Exception as e:
        logger.error(f"❌ Failed to search entities: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search entities: {str(e)}"
        )


# Initialize clients (reassign global variables)
if settings.ha_url and settings.ha_token:
    try:
        ha_client = HomeAssistantClient(settings.ha_url, access_token=settings.ha_token)
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
    conversation_history: Optional[List[Dict[str, Any]]] = Field(default=None, description="Conversation history for context")


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
    # NEW: Clarification fields
    clarification_needed: bool = False
    clarification_session_id: Optional[str] = None
    questions: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None


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


class ClarificationRequest(BaseModel):
    """Request to provide clarification answers"""
    session_id: str = Field(..., description="Clarification session ID")
    answers: List[Dict[str, Any]] = Field(..., description="Answers to clarification questions")
    
class ClarificationResponse(BaseModel):
    """Response from clarification"""
    session_id: str
    confidence: float
    confidence_threshold: float
    clarification_complete: bool
    message: str
    suggestions: Optional[List[Dict[str, Any]]] = None
    questions: Optional[List[Dict[str, Any]]] = None  # If more questions needed


# ============================================================================
# Helper Functions
# ============================================================================

# Global clarification service instances
_clarification_detector: Optional[ClarificationDetector] = None
_question_generator: Optional[QuestionGenerator] = None
_answer_validator: Optional[AnswerValidator] = None
_confidence_calculator: Optional[ConfidenceCalculator] = None
_clarification_sessions: Dict[str, ClarificationSession] = {}  # In-memory storage (TODO: persist to DB)

def get_clarification_services():
    """Get or initialize clarification services"""
    global _clarification_detector, _question_generator, _answer_validator, _confidence_calculator
    
    if _clarification_detector is None:
        _clarification_detector = ClarificationDetector()
    if _question_generator is None and openai_client:
        _question_generator = QuestionGenerator(openai_client)
    if _answer_validator is None:
        _answer_validator = AnswerValidator()
    if _confidence_calculator is None:
        _confidence_calculator = ConfidenceCalculator(default_threshold=0.85)
    
    return _clarification_detector, _question_generator, _answer_validator, _confidence_calculator

async def expand_group_entities_to_members(
    entity_ids: List[str],
    ha_client: Optional[HomeAssistantClient],
    entity_validator: Optional[Any] = None
) -> List[str]:
    """
    Generic function to expand group entities to their individual member entities.
    
    For example, if entity_ids contains a light entity and that entity is a group
    with members ["light.hue_go_1", "light.hue_color_downlight_2_2", ...], 
    this function will return the individual light entity IDs instead.
    
    Args:
        entity_ids: List of entity IDs that may include group entities
        ha_client: Home Assistant client for fetching entity state
        entity_validator: Optional EntityValidator instance for group detection
        
    Returns:
        Expanded list with group entities replaced by their member entity IDs
    """
    if not ha_client:
        logger.warning("⚠️ No HA client available, cannot expand group entities")
        return entity_ids
    
    expanded_entity_ids = []
    
    # Always enrich entities to check for group indicators (is_group, is_hue_group, entity_id attribute)
    from ..services.entity_attribute_service import EntityAttributeService
    attribute_service = EntityAttributeService(ha_client)
    
    # Batch enrich all entities to get attributes for group detection
    enriched_data = await attribute_service.enrich_multiple_entities(entity_ids)
    
    for entity_id in entity_ids:
        try:
            # Check if this is a group entity
            is_group = False
            
            # Method 1: Check enriched attributes (is_group flag, is_hue_group, entity_id attribute)
            if entity_id in enriched_data:
                enriched = enriched_data[entity_id]
                is_group = enriched.get('is_group', False)
                # Also check for group indicators in attributes
                attributes = enriched.get('attributes', {})
                # Group entities have an 'entity_id' attribute containing member list
                if attributes.get('is_hue_group') or attributes.get('entity_id'):
                    is_group = True
            
            # Method 2: Use entity validator's heuristic-based group detection if available
            if not is_group and entity_validator:
                # Create minimal entity dict from enriched data for group detection
                enriched = enriched_data.get(entity_id, {})
                entity_dict = {
                    'entity_id': entity_id,
                    'device_id': enriched.get('device_id'),
                    'friendly_name': enriched.get('friendly_name')
                }
                is_group = entity_validator._is_group_entity(entity_dict)
            
            if is_group:
                logger.info(f"🔍 Group entity detected: {entity_id}, fetching members...")
                
                # Fetch entity state to get member entity IDs
                state_data = await ha_client.get_entity_state(entity_id)
                if state_data:
                    attributes = state_data.get('attributes', {})
                    
                    # Group entities store member IDs in 'entity_id' attribute
                    member_entity_ids = attributes.get('entity_id')
                    
                    if member_entity_ids:
                        if isinstance(member_entity_ids, list):
                            # List of entity IDs
                            expanded_entity_ids.extend(member_entity_ids)
                            logger.info(f"✅ Expanded group {entity_id} to {len(member_entity_ids)} members: {member_entity_ids[:5]}...")
                        elif isinstance(member_entity_ids, str):
                            # Single entity ID as string
                            expanded_entity_ids.append(member_entity_ids)
                            logger.info(f"✅ Expanded group {entity_id} to member: {member_entity_ids}")
                        else:
                            # Fallback: keep the group entity if we can't extract members
                            logger.warning(f"⚠️ Group {entity_id} has unexpected entity_id format: {type(member_entity_ids)}")
                            expanded_entity_ids.append(entity_id)
                    else:
                        # Not actually a group, or no members - keep it
                        logger.debug(f"No members found for {entity_id}, treating as individual entity")
                        expanded_entity_ids.append(entity_id)
                else:
                    # Couldn't fetch state - keep the entity ID
                    logger.warning(f"⚠️ Could not fetch state for {entity_id}, treating as individual entity")
                    expanded_entity_ids.append(entity_id)
            else:
                # Not a group entity - keep it as-is
                expanded_entity_ids.append(entity_id)
                
        except Exception as e:
            logger.warning(f"⚠️ Error checking/expanding entity {entity_id}: {e}, keeping original")
            expanded_entity_ids.append(entity_id)
    
    # Deduplicate the expanded list
    expanded_entity_ids = list(dict.fromkeys(expanded_entity_ids))  # Preserves order while deduplicating
    
    if len(expanded_entity_ids) != len(entity_ids):
        logger.info(f"✅ Expanded {len(entity_ids)} entities to {len(expanded_entity_ids)} individual entities")
    
    return expanded_entity_ids


async def verify_entities_exist_in_ha(
    entity_ids: List[str],
    ha_client: Optional[HomeAssistantClient],
    use_ensemble: bool = True,
    query_context: Optional[str] = None,
    available_entities: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, bool]:
    """
    Verify which entity IDs actually exist in Home Assistant.
    
    Uses ensemble validation (all models) when available, falls back to HA API check.
    
    Args:
        entity_ids: List of entity IDs to verify
        ha_client: Optional HA client for verification
        use_ensemble: If True, use ensemble validation (HF, OpenAI, embeddings)
        query_context: Optional query context for ensemble validation
        available_entities: Optional available entities for ensemble validation
        
    Returns:
        Dictionary mapping entity_id -> exists (True/False)
    """
    if not ha_client or not entity_ids:
        return {eid: False for eid in entity_ids} if entity_ids else {}
    
    # Try ensemble validation if enabled and models available
    if use_ensemble:
        try:
            from ..services.ensemble_entity_validator import EnsembleEntityValidator
            
            # Get models if available
            sentence_model = None
            if _self_correction_service and hasattr(_self_correction_service, 'similarity_model'):
                sentence_model = _self_correction_service.similarity_model
            elif _multi_model_extractor:
                # Could also get from multi_model_extractor if needed
                pass
            
            # Initialize ensemble validator
            ensemble_validator = EnsembleEntityValidator(
                ha_client=ha_client,
                openai_client=openai_client,
                sentence_transformer_model=sentence_model,
                device_intelligence_client=_device_intelligence_client,
                min_consensus_threshold=0.5  # Moderate threshold - HA API is ground truth
            )
            
            # Validate using ensemble
            logger.info(f"🔍 Using ensemble validation for {len(entity_ids)} entities")
            ensemble_results = await ensemble_validator.validate_entities_batch(
                entity_ids=entity_ids,
                query_context=query_context,
                available_entities=available_entities
            )
            
            # Extract existence results
            verified = {eid: result.exists for eid, result in ensemble_results.items()}
            
            # Log warnings for low consensus entities
            for eid, result in ensemble_results.items():
                if result.exists and result.consensus_score < 0.7:
                    logger.warning(
                        f"⚠️ Entity {eid} validated but low consensus ({result.consensus_score:.2f}) "
                        f"- methods: {[r.method.value for r in result.method_results]}"
                    )
            
            logger.info(f"✅ Ensemble validation: {sum(verified.values())}/{len(verified)} entities valid")
            return verified
            
        except Exception as e:
            logger.warning(f"⚠️ Ensemble validation failed, falling back to HA API check: {e}")
            # Fall through to simple HA API check
    
    # Fallback: Simple HA API verification (parallel for performance)
    import asyncio
    async def verify_one(entity_id: str) -> tuple[str, bool]:
        try:
            state = await ha_client.get_entity_state(entity_id)
            return (entity_id, state is not None)
        except Exception:
            return (entity_id, False)
    
    tasks = [verify_one(eid) for eid in entity_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    verified = {}
    for result in results:
        if isinstance(result, Exception):
            continue
        entity_id, exists = result
        verified[entity_id] = exists
    
    return verified


async def map_devices_to_entities(
    devices_involved: List[str], 
    enriched_data: Dict[str, Dict[str, Any]],
    ha_client: Optional[HomeAssistantClient] = None,
    fuzzy_match: bool = True
) -> Dict[str, str]:
    """
    Map device friendly names to entity IDs from enriched data.
    
    Optimized for single-home local solutions:
    - Deduplicates redundant mappings (multiple friendly names → same entity_id)
    - Prioritizes exact matches over fuzzy matches
    - Uses area context for better matching in single-home scenarios
    - Consolidates devices_involved to unique entity mappings
    
    IMPORTANT: Only includes entity IDs that actually exist in Home Assistant.
    
    Args:
        devices_involved: List of device friendly names from LLM suggestion
        enriched_data: Dictionary mapping entity_id to enriched entity data
        ha_client: Optional HA client for verifying entities exist
        fuzzy_match: If True, use fuzzy matching for partial matches
        
    Returns:
        Dictionary mapping device_name → entity_id (only verified entities, deduplicated)
    """
    # 🔍 DETAILED DEBUGGING for approval flow
    logger.info(f"🔍 [MAP_DEVICES] Called with {len(devices_involved)} devices and {len(enriched_data) if enriched_data else 0} enriched entities")
    logger.info(f"🔍 [MAP_DEVICES] Devices to map: {devices_involved}")
    if enriched_data:
        logger.info(f"🔍 [MAP_DEVICES] Enriched entity IDs: {list(enriched_data.keys())[:10]}")
        # Log structure of first enriched entity
        first_entity_id = list(enriched_data.keys())[0] if enriched_data else None
        if first_entity_id:
            first_entity = enriched_data[first_entity_id]
            logger.info(f"🔍 [MAP_DEVICES] First enriched entity structure - ID: {first_entity_id}")
            logger.info(f"               Keys: {list(first_entity.keys())}")
            logger.info(f"               friendly_name: {first_entity.get('friendly_name')}")
            logger.info(f"               entity_id: {first_entity.get('entity_id')}")
            logger.info(f"               name: {first_entity.get('name')}")
    
    validated_entities = {}
    unmapped_devices = []
    entity_id_to_best_device_name = {}  # Track best device name for each entity_id
    
    # Handle None or empty enriched_data - try to query HA directly as fallback
    if not enriched_data:
        logger.warning(f"⚠️ map_devices_to_entities called with empty/None enriched_data for {len(devices_involved)} devices")
        # Fallback: Query HA directly for entities if we have a client
        if ha_client:
            logger.info(f"🔄 Attempting to query Home Assistant directly for {len(devices_involved)} devices...")
            try:
                # Get all states from HA
                session = await ha_client._get_session()
                url = f"{ha_client.ha_url}/api/states"
                async with session.get(url) as response:
                    if response.status == 200:
                        all_states = await response.json()
                        # Build enriched_data from HA states
                        enriched_data = {}
                        for state in all_states:
                            if isinstance(state, dict):
                                entity_id = state.get('entity_id')
                                if entity_id and '.' in entity_id:  # Valid entity ID format
                                    attributes = state.get('attributes', {})
                                    friendly_name = attributes.get('friendly_name') or attributes.get('name') or entity_id.split('.')[-1].replace('_', ' ').title()
                                    enriched_data[entity_id] = {
                                        'entity_id': entity_id,
                                        'friendly_name': friendly_name,
                                        'state': state.get('state'),
                                        'attributes': attributes
                                    }
                        logger.info(f"✅ Built enriched_data from {len(enriched_data)} HA entities for fallback mapping")
                    else:
                        logger.warning(f"⚠️ Failed to query HA states: HTTP {response.status}")
            except Exception as e:
                logger.error(f"❌ Error querying HA for fallback entities: {e}", exc_info=True)
        
        # If still no enriched_data, return empty
        if not enriched_data:
            logger.error(f"❌ Cannot map devices: no enriched_data and HA query failed")
            return {}
    
    for device_name in devices_involved:
        mapped = False
        device_name_lower = device_name.lower()
        matched_entity_id = None
        match_quality = 0  # 3=exact, 2=fuzzy, 1=domain
        
        # Strategy 1: Exact match by friendly_name (highest priority)
        for entity_id, enriched in enriched_data.items():
            friendly_name = enriched.get('friendly_name', '')
            if friendly_name.lower() == device_name_lower:
                matched_entity_id = entity_id
                match_quality = 3
                logger.debug(f"✅ Mapped device '{device_name}' → entity_id '{entity_id}' (exact match)")
                break
        
        # Strategy 2: Fuzzy matching (case-insensitive substring) - area-aware for single-home
        if not matched_entity_id and fuzzy_match:
            best_fuzzy_match = None
            best_fuzzy_score = 0
            
            for entity_id, enriched in enriched_data.items():
                friendly_name = enriched.get('friendly_name', '').lower()
                entity_name_part = entity_id.split('.')[-1].lower() if '.' in entity_id else ''
                area_name = enriched.get('area_name', '').lower() if enriched.get('area_name') else ''
                
                # Calculate fuzzy match score (higher = better)
                score = 0
                if device_name_lower in friendly_name or friendly_name in device_name_lower:
                    score += 2  # Strong match
                if device_name_lower in entity_name_part:
                    score += 1  # Weak match
                # Area context bonus for single-home scenarios
                if area_name and device_name_lower in area_name:
                    score += 1  # Area context bonus
                
                if score > best_fuzzy_score:
                    best_fuzzy_score = score
                    best_fuzzy_match = entity_id
            
            if best_fuzzy_match and best_fuzzy_score > 0:
                matched_entity_id = best_fuzzy_match
                match_quality = 2
                logger.debug(f"✅ Mapped device '{device_name}' → entity_id '{matched_entity_id}' (fuzzy match, score: {best_fuzzy_score})")
        
        # Strategy 3: Match by domain name (lowest priority)
        if not matched_entity_id and fuzzy_match:
            for entity_id, enriched in enriched_data.items():
                domain = entity_id.split('.')[0].lower() if '.' in entity_id else ''
                if domain == device_name_lower:
                    matched_entity_id = entity_id
                    match_quality = 1
                    logger.debug(f"✅ Mapped device '{device_name}' → entity_id '{entity_id}' (domain match)")
                    break
        
        # Store mapping if found, but only keep best device name for each entity_id
        if matched_entity_id:
            existing_quality = entity_id_to_best_device_name.get(matched_entity_id, {}).get('quality', 0)
            if match_quality > existing_quality:
                # Replace existing mapping with better match
                if matched_entity_id in entity_id_to_best_device_name:
                    old_device_name = entity_id_to_best_device_name[matched_entity_id]['device_name']
                    logger.debug(f"🔄 Replacing '{old_device_name}' → '{device_name}' for entity_id '{matched_entity_id}' (better match quality)")
                    validated_entities.pop(old_device_name, None)
                
                entity_id_to_best_device_name[matched_entity_id] = {
                    'device_name': device_name,
                    'quality': match_quality
                }
                validated_entities[device_name] = matched_entity_id
                mapped = True
            elif match_quality == existing_quality:
                # Same quality - keep both, but log for consolidation
                validated_entities[device_name] = matched_entity_id
                mapped = True
                logger.debug(f"📋 Duplicate mapping: '{device_name}' → '{matched_entity_id}' (same quality as existing)")
        else:
            unmapped_devices.append(device_name)
            logger.warning(f"⚠️ Could not map device '{device_name}' to entity_id (not found in enriched_data)")
    
    # CRITICAL: Verify ALL mapped entities actually exist in Home Assistant
    if validated_entities and ha_client:
        logger.info(f"🔍 Verifying {len(validated_entities)} mapped entities exist in Home Assistant...")
        unique_entity_ids = list(set(validated_entities.values()))  # Get unique entity IDs
        verification_results = await verify_entities_exist_in_ha(unique_entity_ids, ha_client)
        
        # Filter out entities that don't exist
        verified_validated_entities = {}
        invalid_entities = []
        for device_name, entity_id in validated_entities.items():
            if verification_results.get(entity_id, False):
                verified_validated_entities[device_name] = entity_id
            else:
                invalid_entities.append(f"{device_name} → {entity_id}")
                logger.warning(f"❌ Entity {entity_id} (mapped from '{device_name}') does NOT exist in HA - removed from validated_entities")
        
        if invalid_entities:
            logger.warning(f"⚠️ Removed {len(invalid_entities)} invalid entity mappings: {', '.join(invalid_entities[:5])}")
        
        validated_entities = verified_validated_entities
        logger.info(f"✅ Verified {len(validated_entities)}/{len(unique_entity_ids)} unique entities exist in HA")
    
    # Log consolidation stats
    unique_entity_count = len(set(validated_entities.values()))
    if len(validated_entities) > unique_entity_count:
        logger.info(
            f"🔄 Consolidated {len(devices_involved)} devices → {unique_entity_count} unique entities "
            f"({len(validated_entities)} device names mapped, {len(devices_involved) - len(validated_entities)} redundant)"
        )
    
    # Fallback: Query HA directly for unmapped devices if we have a client
    if unmapped_devices and ha_client:
        logger.info(f"🔄 Querying HA directly for {len(unmapped_devices)} unmapped devices...")
        try:
            # Get all states from HA
            session = await ha_client._get_session()
            url = f"{ha_client.ha_url}/api/states"
            async with session.get(url) as response:
                if response.status == 200:
                    all_states = await response.json()
                    # Build enriched_data from HA states for unmapped devices
                    ha_enriched_data = {}
                    for state in all_states:
                        if isinstance(state, dict):
                            entity_id = state.get('entity_id')
                            if entity_id and '.' in entity_id:  # Valid entity ID format
                                attributes = state.get('attributes', {})
                                friendly_name = attributes.get('friendly_name') or attributes.get('name') or entity_id.split('.')[-1].replace('_', ' ').title()
                                ha_enriched_data[entity_id] = {
                                    'entity_id': entity_id,
                                    'friendly_name': friendly_name,
                                    'state': state.get('state'),
                                    'attributes': attributes
                                }
                    
                    # Try to map unmapped devices using HA entities
                    logger.info(f"🔍 Attempting to map {len(unmapped_devices)} devices against {len(ha_enriched_data)} HA entities...")
                    
                    # Track which entities have already been matched to avoid duplicates
                    matched_entity_ids = set(validated_entities.values())
                    
                    for device_name in unmapped_devices:
                        device_name_lower = device_name.lower()
                        best_match = None
                        best_score = 0
                        
                        # Search through HA entities for best match
                        for entity_id, entity_data in ha_enriched_data.items():
                            # Skip if this entity is already mapped to another device (unless it's an exact match)
                            if entity_id in matched_entity_ids:
                                # Still allow exact matches even if entity is already mapped (might be a group)
                                friendly_name = entity_data.get('friendly_name', '').lower()
                                if device_name_lower != friendly_name:
                                    continue  # Skip already-matched entities for non-exact matches
                            
                            friendly_name = entity_data.get('friendly_name', '').lower()
                            entity_name_part = entity_id.split('.')[-1].lower() if '.' in entity_id else ''
                            
                            # Calculate match score (higher = better)
                            score = 0
                            
                            # Exact match gets highest priority
                            if device_name_lower == friendly_name:
                                score = 10
                            # Check for word matches (e.g., "LR Front Left Ceiling" matches "LR Front Left Ceiling Light")
                            elif device_words := set(device_name_lower.split()):
                                friendly_words = set(friendly_name.split())
                                # All words from device name must be in friendly name
                                if device_words.issubset(friendly_words):
                                    # Prefer matches where all words are present and in order
                                    device_words_list = device_name_lower.split()
                                    friendly_words_list = friendly_name.split()
                                    # Check if words appear in same order
                                    order_match = True
                                    last_idx = -1
                                    for word in device_words_list:
                                        try:
                                            idx = friendly_words_list.index(word)
                                            if idx <= last_idx:
                                                order_match = False
                                                break
                                            last_idx = idx
                                        except ValueError:
                                            order_match = False
                                            break
                                    
                                    if order_match:
                                        score = 8  # All words match in order
                                    else:
                                        score = 7  # All words match but not in order
                                # Check for substring matches
                                elif device_name_lower in friendly_name:
                                    score = 5  # Device name is substring of friendly name
                                elif friendly_name in device_name_lower:
                                    score = 4  # Friendly name is substring of device name
                            
                            # Entity ID part match (lower priority)
                            if device_name_lower in entity_name_part:
                                score = max(score, 3)
                            
                            # Prefer matches that haven't been used yet
                            if entity_id not in matched_entity_ids:
                                score += 1  # Bonus for unmapped entities
                            
                            if score > best_score:
                                best_score = score
                                best_match = entity_id
                        
                        if best_match and best_score >= 3:  # Minimum threshold
                            # Verify entity exists
                            if ha_client:
                                exists = await verify_entities_exist_in_ha([best_match], ha_client)
                                if exists.get(best_match, False):
                                    validated_entities[device_name] = best_match
                                    matched_entity_ids.add(best_match)  # Mark as used
                                    logger.info(f"✅ Mapped unmapped device '{device_name}' → {best_match} (score: {best_score})")
                                else:
                                    logger.warning(f"⚠️ Best match {best_match} for '{device_name}' does not exist in HA")
                            else:
                                validated_entities[device_name] = best_match
                                matched_entity_ids.add(best_match)  # Mark as used
                                logger.info(f"✅ Mapped unmapped device '{device_name}' → {best_match} (score: {best_score}, unverified)")
                    
                    logger.info(f"✅ HA direct query mapped {len([d for d in unmapped_devices if d in validated_entities])}/{len(unmapped_devices)} previously unmapped devices")
                else:
                    logger.warning(f"⚠️ Failed to query HA states for unmapped devices: HTTP {response.status}")
        except Exception as e:
            logger.error(f"❌ Error querying HA for unmapped devices: {e}", exc_info=True)
    
    if unmapped_devices and validated_entities:
        final_unmapped = [d for d in unmapped_devices if d not in validated_entities]
        unique_entity_count = len(set(validated_entities.values()))
        logger.info(
            f"✅ Mapped {len(validated_entities)}/{len(devices_involved)} devices to {unique_entity_count} verified entities "
            f"({len(final_unmapped)} still unmapped: {final_unmapped})"
        )
    elif validated_entities:
        unique_entity_count = len(set(validated_entities.values()))
        logger.info(f"✅ Mapped all {len(validated_entities)} devices to {unique_entity_count} verified entities")
    elif devices_involved:
        logger.warning(f"⚠️ Could not map any of {len(devices_involved)} devices to verified entities")
    
    return validated_entities


def _pre_consolidate_device_names(
    devices_involved: List[str],
    enriched_data: Optional[Dict[str, Dict[str, Any]]] = None
) -> List[str]:
    """
    Pre-consolidate device names by removing generic/redundant terms BEFORE entity mapping.
    
    This handles cases where OpenAI includes:
    - Generic domain names ("light", "switch")
    - Device type names ("wled", "hue")  
    - Area-only references that don't map to actual entities
    - Very short/generic terms (< 3 chars)
    
    Args:
        devices_involved: Original list of device names from OpenAI
        enriched_data: Optional enriched entity data for better filtering
        
    Returns:
        Filtered list with generic/redundant terms removed
    """
    if not devices_involved:
        return devices_involved
    
    # Generic terms to remove (domain names, device types, very short terms)
    generic_terms = {'light', 'switch', 'sensor', 'binary_sensor', 'climate', 'cover', 
                     'fan', 'lock', 'wled', 'hue', 'mqtt', 'zigbee', 'zwave'}
    
    filtered = []
    removed_terms = []
    
    for device_name in devices_involved:
        device_lower = device_name.lower().strip()
        
        # Skip empty or very short terms
        if len(device_lower) < 3:
            removed_terms.append(device_name)
            continue
        
        # Skip generic domain/integration terms
        if device_lower in generic_terms:
            removed_terms.append(device_name)
            continue
        
        # Skip terms that are just numbers or single words without spaces (likely incomplete)
        # BUT keep proper entity names like "Office" or "Living Room"
        if device_lower.isdigit():
            removed_terms.append(device_name)
            continue
        
        # Keep all other terms (they're likely actual device names)
        filtered.append(device_name)
    
    if removed_terms:
        logger.debug(f"📋 Pre-consolidation removed generic terms: {removed_terms}")
    
    return filtered if filtered else devices_involved  # Return original if we filtered everything


def consolidate_devices_involved(
    devices_involved: List[str],
    validated_entities: Dict[str, str]
) -> List[str]:
    """
    Consolidate devices_involved array by removing redundant device names that map to the same entity.
    
    Optimized for single-home local solutions:
    - Removes duplicate device names that map to the same entity_id
    - Keeps the most specific/descriptive device name for each unique entity
    - Preserves order while deduplicating
    
    Args:
        devices_involved: Original list of device friendly names
        validated_entities: Dictionary mapping device_name → entity_id
        
    Returns:
        Consolidated list of unique device names (one per entity_id)
    """
    if not devices_involved or not validated_entities:
        return devices_involved
    
    # Group device names by their mapped entity_id
    entity_id_to_devices = {}
    for device_name in devices_involved:
        entity_id = validated_entities.get(device_name)
        if entity_id:
            if entity_id not in entity_id_to_devices:
                entity_id_to_devices[entity_id] = []
            entity_id_to_devices[entity_id].append(device_name)
    
    # For each entity_id, keep the most specific device name
    # Priority: longer names > exact matches > shorter names
    consolidated = []
    entity_ids_seen = set()
    
    for device_name in devices_involved:
        entity_id = validated_entities.get(device_name)
        if entity_id and entity_id not in entity_ids_seen:
            # If multiple devices map to same entity, choose the best one
            if len(entity_id_to_devices.get(entity_id, [])) > 1:
                candidates = entity_id_to_devices[entity_id]
                # Prefer longer, more specific names
                best_name = max(candidates, key=lambda x: (len(x), x.count(' '), x.lower()))
                consolidated.append(best_name)
                logger.debug(
                    f"🔄 Consolidated {len(candidates)} devices ({', '.join(candidates)}) "
                    f"→ '{best_name}' for entity_id '{entity_id}'"
                )
            else:
                consolidated.append(device_name)
            entity_ids_seen.add(entity_id)
        elif entity_id not in validated_entities:
            # Keep unmapped devices (they might be groups or areas)
            consolidated.append(device_name)
    
    if len(consolidated) < len(devices_involved):
        logger.info(
            f"🔄 Consolidated devices_involved: {len(devices_involved)} → {len(consolidated)} "
            f"({len(devices_involved) - len(consolidated)} redundant entries removed)"
        )
    
    return consolidated


def extract_device_mentions_from_text(
    text: str,
    validated_entities: Dict[str, str],
    enriched_data: Optional[Dict[str, Dict[str, Any]]] = None
) -> Dict[str, str]:
    """
    Extract device mentions from text and map them to entity IDs.
    
    Args:
        text: Text to scan (description, trigger_summary, action_summary)
        validated_entities: Dictionary mapping friendly_name → entity_id
        enriched_data: Optional enriched entity data for fuzzy matching
        
    Returns:
        Dictionary mapping mention → entity_id
    """
    if not text:
        return {}
    
    mentions = {}
    text_lower = text.lower()
    
    # Extract mentions from validated_entities
    for friendly_name, entity_id in validated_entities.items():
        friendly_name_lower = friendly_name.lower()
        # Check if friendly name appears in text (word boundary matching)
        import re
        pattern = r'\b' + re.escape(friendly_name_lower) + r'\b'
        if re.search(pattern, text_lower):
            mentions[friendly_name] = entity_id
            logger.debug(f"🔍 Found mention '{friendly_name}' in text → {entity_id}")
        
        # Also check for partial matches (e.g., "wled" matches "WLED" or "wled strip")
        if friendly_name_lower in text_lower or text_lower in friendly_name_lower:
            if friendly_name not in mentions:
                mentions[friendly_name] = entity_id
                logger.debug(f"🔍 Found partial mention '{friendly_name}' in text → {entity_id}")
    
    # If enriched_data available, also check entity names and domains
    if enriched_data:
        for entity_id, enriched in enriched_data.items():
            friendly_name = enriched.get('friendly_name', '').lower()
            domain = entity_id.split('.')[0].lower() if '.' in entity_id else ''
            entity_name = entity_id.split('.')[-1].lower() if '.' in entity_id else ''
            
            # Check domain matches (e.g., "wled" text matches light entities with "wled" in the name)
            if domain and domain in text_lower and len(domain) >= 3:
                if domain not in [m.lower() for m in mentions.keys()]:
                    mentions[domain] = entity_id
                    logger.debug(f"🔍 Found domain mention '{domain}' in text → {entity_id}")
            
            # Check entity name matches
            if entity_name and entity_name in text_lower:
                if entity_name not in [m.lower() for m in mentions.keys()]:
                    mentions[entity_name] = entity_id
                    logger.debug(f"🔍 Found entity name mention '{entity_name}' in text → {entity_id}")
    
    return mentions


async def enhance_suggestion_with_entity_ids(
    suggestion: Dict[str, Any],
    validated_entities: Dict[str, str],
    enriched_data: Optional[Dict[str, Dict[str, Any]]] = None,
    ha_client: Optional[HomeAssistantClient] = None
) -> Dict[str, Any]:
    """
    Enhance suggestion by adding entity IDs directly.
    
    Adds:
    - entity_ids_used: List of actual entity IDs
    - entity_id_annotations: Detailed mapping with context
    - device_mentions: Maps description terms → entity IDs
    
    Args:
        suggestion: Suggestion dictionary
        validated_entities: Mapping friendly_name → entity_id
        enriched_data: Optional enriched entity data
        ha_client: Optional HA client for querying entities
        
    Returns:
        Enhanced suggestion dictionary
    """
    enhanced = suggestion.copy()
    
    # Extract all device mentions from suggestion text fields
    device_mentions = {}
    text_fields = [
        enhanced.get('description', ''),
        enhanced.get('trigger_summary', ''),
        enhanced.get('action_summary', '')
    ]
    
    for text in text_fields:
        mentions = extract_device_mentions_from_text(text, validated_entities, enriched_data)
        device_mentions.update(mentions)
    
    # Get entity IDs used
    entity_ids_used = list(set(validated_entities.values()))
    
    # Build entity_id_annotations with context
    entity_id_annotations = {}
    for friendly_name, entity_id in validated_entities.items():
        entity_id_annotations[friendly_name] = {
            'entity_id': entity_id,
            'domain': entity_id.split('.')[0] if '.' in entity_id else '',
            'mentioned_in': []
        }
        
        # Track where this device is mentioned
        for field in ['description', 'trigger_summary', 'action_summary']:
            text = enhanced.get(field, '').lower()
            if friendly_name.lower() in text:
                entity_id_annotations[friendly_name]['mentioned_in'].append(field)
    
    # Add device_mentions (from text extraction)
    enhanced['device_mentions'] = device_mentions
    enhanced['entity_ids_used'] = entity_ids_used
    enhanced['entity_id_annotations'] = entity_id_annotations
    
    logger.info(f"✅ Enhanced suggestion with {len(entity_ids_used)} entity IDs and {len(device_mentions)} device mentions")
    
    return enhanced


def deduplicate_entity_mapping(entity_mapping: Dict[str, str]) -> Dict[str, str]:
    """
    Deduplicate entity mapping - if multiple device names map to same entity_id,
    keep only unique entity_ids.
    
    Args:
        entity_mapping: Dictionary mapping device names to entity_ids
        
    Returns:
        Deduplicated mapping with only unique entity_ids
    """
    seen_entities = {}
    deduplicated = {}
    
    for device_name, entity_id in entity_mapping.items():
        if entity_id not in seen_entities:
            # First occurrence of this entity_id
            deduplicated[device_name] = entity_id
            seen_entities[entity_id] = device_name
        else:
            # Duplicate - log and skip
            logger.debug(
                f"⚠️ Duplicate entity mapping: '{device_name}' → {entity_id} "
                f"(already mapped as '{seen_entities[entity_id]}')"
            )
    
    if len(deduplicated) < len(entity_mapping):
        logger.info(
            f"✅ Deduplicated entities: {len(deduplicated)} unique from {len(entity_mapping)} total "
            f"({len(entity_mapping) - len(deduplicated)} duplicates removed)"
        )
    
    return deduplicated


async def pre_validate_suggestion_for_yaml(
    suggestion: Dict[str, Any],
    validated_entities: Dict[str, str],
    ha_client: Optional[HomeAssistantClient] = None
) -> Dict[str, str]:
    """
    Pre-validate and enhance suggestion before YAML generation.
    
    Extracts all device mentions from description/trigger/action summaries,
    maps them to entity IDs, and queries HA for domain entities if device name is incomplete.
    
    Args:
        suggestion: Suggestion dictionary
        validated_entities: Mapping friendly_name → entity_id
        ha_client: Optional HA client for querying entities
        
    Returns:
        Enhanced validated_entities dictionary with all mentions mapped
    """
    enhanced_validated_entities = validated_entities.copy()
    
    # Extract device mentions from all text fields
    text_fields = {
        'description': suggestion.get('description', ''),
        'trigger_summary': suggestion.get('trigger_summary', ''),
        'action_summary': suggestion.get('action_summary', '')
    }
    
    all_mentions = {}
    for field, text in text_fields.items():
        mentions = extract_device_mentions_from_text(text, validated_entities, None)
        all_mentions.update(mentions)
    
    # Add mentions to enhanced_validated_entities, but collect for verification first
    new_mentions = {}
    for mention, entity_id in all_mentions.items():
        if mention not in enhanced_validated_entities:
            new_mentions[mention] = entity_id
            logger.debug(f"🔍 Found mention '{mention}' → {entity_id}")
    
    # Check for incomplete entity IDs (domain-only mentions like "wled", "office")
    if ha_client and new_mentions:
        incomplete_mentions = {}
        complete_mentions = {}
        for mention, entity_id in new_mentions.items():
            if '.' not in entity_id or entity_id.startswith('.') or entity_id.endswith('.'):  # Incomplete entity ID
                incomplete_mentions[mention] = entity_id
            else:
                complete_mentions[mention] = entity_id
        
        # Query HA for domain entities if we found incomplete mentions
        if incomplete_mentions:
            domains_to_query = set()
            for mention, entity_id in incomplete_mentions.items():
                domains_to_query.add(entity_id.lower().strip('.'))
            
            logger.info(f"🔍 Found {len(incomplete_mentions)} incomplete mentions, querying HA for domains: {list(domains_to_query)}")
            for domain in domains_to_query:
                try:
                    domain_entities = await ha_client.get_entities_by_domain(domain)
                    if domain_entities:
                        # Verify the first entity exists before using it
                        first_entity = domain_entities[0]
                        state = await ha_client.get_entity_state(first_entity)
                        if state:
                            # Use first entity from domain if it exists
                            for mention in incomplete_mentions:
                                if incomplete_mentions[mention].lower().strip('.') == domain:
                                    complete_mentions[mention] = first_entity
                                    logger.info(f"✅ Queried HA for '{domain}', verified and using: {first_entity}")
                        else:
                            logger.warning(f"⚠️ Entity {first_entity} from domain '{domain}' query does not exist in HA")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to query HA for domain '{domain}': {e}")
        
        # CRITICAL: Verify ALL complete mentions exist in HA before adding
        if complete_mentions and ha_client:
            logger.info(f"🔍 Verifying {len(complete_mentions)} extracted mentions exist in HA...")
            entity_ids_to_verify = list(complete_mentions.values())
            verification_results = await verify_entities_exist_in_ha(entity_ids_to_verify, ha_client)
            
            # Only add verified entities
            for mention, entity_id in complete_mentions.items():
                if verification_results.get(entity_id, False):
                    enhanced_validated_entities[mention] = entity_id
                    logger.debug(f"✅ Added verified mention '{mention}' → {entity_id} to validated entities")
                else:
                    logger.warning(f"❌ Mention '{mention}' → {entity_id} does NOT exist in HA - skipped")
    
    return enhanced_validated_entities


async def build_suggestion_specific_entity_mapping(
    suggestion: Dict[str, Any],
    validated_entities: Dict[str, str]
) -> str:
    """
    Build suggestion-specific entity ID mapping text for LLM prompt.
    
    Creates explicit mapping table for devices mentioned in THIS specific suggestion.
    
    Args:
        suggestion: Suggestion dictionary
        validated_entities: Mapping friendly_name → entity_id
        
    Returns:
        Formatted text for LLM prompt
    """
    if not validated_entities:
        return ""
    
    # Extract devices mentioned in this suggestion
    description = suggestion.get('description', '').lower()
    trigger = suggestion.get('trigger_summary', '').lower()
    action = suggestion.get('action_summary', '').lower()
    combined_text = f"{description} {trigger} {action}"
    
    # Build mapping for devices mentioned in this suggestion
    mappings = []
    for friendly_name, entity_id in validated_entities.items():
        friendly_name_lower = friendly_name.lower()
        # Check if this device is mentioned in the suggestion
        if (friendly_name_lower in combined_text or 
            friendly_name_lower in description or
            friendly_name_lower in trigger or
            friendly_name_lower in action):
            domain = entity_id.split('.')[0] if '.' in entity_id else ''
            mappings.append(f"  - \"{friendly_name}\" or \"{friendly_name_lower}\" → {entity_id} (domain: {domain})")
    
    if not mappings:
        # Fallback: include all validated entities
        for friendly_name, entity_id in validated_entities.items():
            domain = entity_id.split('.')[0] if '.' in entity_id else ''
            mappings.append(f"  - \"{friendly_name}\" → {entity_id} (domain: {domain})")
    
    if mappings:
        return f"""
SUGGESTION-SPECIFIC ENTITY ID MAPPINGS:
For THIS specific automation suggestion, use these exact mappings:

Description: "{suggestion.get('description', '')[:100]}..."
Trigger mentions: "{suggestion.get('trigger_summary', '')[:100]}..."
Action mentions: "{suggestion.get('action_summary', '')[:100]}..."

ENTITY ID MAPPINGS FOR THIS AUTOMATION:
{chr(10).join(mappings[:10])}  # Limit to first 10 to avoid prompt bloat

CRITICAL: When generating YAML, use the entity IDs above. For example, if you see "wled" in the description, use the full entity ID from above (NOT just "wled").
"""
    
    return ""


async def generate_automation_yaml(
    suggestion: Dict[str, Any], 
    original_query: str, 
    entities: Optional[List[Dict[str, Any]]] = None,
    db_session: Optional[AsyncSession] = None,
    ha_client: Optional[HomeAssistantClient] = None
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
        db_session: Optional database session for alias support
    
    Returns:
        YAML string for the automation
    """
    logger.info(f"🚀 GENERATE_YAML CALLED - Query: {original_query[:50]}...")
    logger.info(f"🚀 Suggestion: {suggestion}")
    
    if not openai_client:
        raise ValueError("OpenAI client not initialized - cannot generate YAML")
    
    # Get validated_entities from suggestion (already set during suggestion creation)
    validated_entities = suggestion.get('validated_entities', {})
    if not validated_entities or not isinstance(validated_entities, dict):
        devices_involved = suggestion.get('devices_involved', [])
        error_msg = (
            f"Cannot generate automation YAML: No validated entities found. "
            f"The system could not map any of {len(devices_involved)} requested devices "
            f"({', '.join(devices_involved[:5])}{'...' if len(devices_involved) > 5 else ''}) "
            f"to actual Home Assistant entities."
        )
        logger.error(f"❌ {error_msg}")
        raise ValueError(error_msg)
    
    # Use enriched_entity_context from suggestion (already computed during creation)
    entity_context_json = suggestion.get('enriched_entity_context', '')
    if entity_context_json:
        logger.info("✅ Using cached enriched entity context from suggestion")
    else:
        logger.warning("⚠️ No enriched_entity_context in suggestion (should be set during creation)")
    
    # Build validated entities text for prompt
    if validated_entities:
        # Build explicit mapping examples GENERICALLY (not hardcoded for specific terms)
        mapping_examples = []
        entity_id_list = []
        
        for term, entity_id in validated_entities.items():
            entity_id_list.append(f"- {term}: {entity_id}")
            # Build generic mapping instructions
            domain = entity_id.split('.')[0] if '.' in entity_id else 'unknown'
            term_variations = [term, term.lower(), term.upper(), term.title()]
            mapping_examples.append(
                f"  - If you see any variation of '{term}' (or domain '{domain}') in the description → use EXACTLY: {entity_id}"
            )
        
        mapping_text = ""
        if mapping_examples:
            mapping_text = f"""
EXPLICIT ENTITY ID MAPPINGS (use these EXACT mappings - ALL have been verified to exist in Home Assistant):
{chr(10).join(mapping_examples[:15])}

"""
        
        # Build dynamic example entity IDs for the prompt
        example_light = next((eid for eid in validated_entities.values() if eid.startswith('light.')), None)
        example_entity = list(validated_entities.values())[0] if validated_entities else '{EXAMPLE_ENTITY_ID}'
        
        validated_entities_text = f"""
VALIDATED ENTITIES (ALL verified to exist in Home Assistant - use these EXACT entity IDs):
{chr(10).join(entity_id_list)}
{mapping_text}
CRITICAL: Use ONLY the entity IDs listed above. Do NOT create new entity IDs.
Entity IDs must ALWAYS be in format: domain.entity (e.g., {example_entity})

COMMON MISTAKES TO AVOID:
❌ WRONG: entity_id: wled (missing domain prefix - will cause "Entity not found" error)
❌ WRONG: entity_id: WLED (missing domain prefix and wrong format)
❌ WRONG: entity_id: office (missing domain prefix - incomplete entity ID)
✅ CORRECT: entity_id: {example_entity} (complete domain.entity format from validated list above)
"""
        
        # Add entity context JSON if available
        if entity_context_json:
            # Escape any curly braces in JSON to prevent f-string formatting errors
            escaped_json = entity_context_json.replace('{', '{{').replace('}', '}}')
            validated_entities_text += f"""

ENTITY CONTEXT (Complete Information):
{escaped_json}

Use this entity information to:
1. Choose the right entity type (group vs individual)
2. Understand device capabilities
3. Generate appropriate actions
4. Respect device limitations (e.g., brightness range, color modes)
"""
    else:
        # This should not happen - validated_entities check above should catch this
        raise ValueError("No validated entities available - cannot generate YAML")
    
    # Check if test mode
    is_test = 'TEST MODE' in suggestion.get('description', '') or suggestion.get('trigger_summary', '') == 'Manual trigger (test mode)'
    
    # TASK 2.4: Check if sequence test mode (shortened delays instead of stripping)
    is_sequence_test = suggestion.get('test_mode') == 'sequence'
    
    # Build dynamic example entity IDs for prompt examples (use validated entities, or generic placeholders)
    if validated_entities:
        example_light = next((eid for eid in validated_entities.values() if eid.startswith('light.')), None)
        example_sensor = next((eid for eid in validated_entities.values() if eid.startswith('binary_sensor.')), None)
        example_door_sensor = next((eid for eid in validated_entities.values() if 'door' in eid.lower() and eid.startswith('binary_sensor.')), example_sensor)
        example_motion_sensor = next((eid for eid in validated_entities.values() if 'motion' in eid.lower() and eid.startswith('binary_sensor.')), example_sensor)
        example_wled = next((eid for eid in validated_entities.values() if 'wled' in eid.lower()), example_light)
        example_entity_1 = example_light or example_entity
        example_entity_2 = next((eid for eid in list(validated_entities.values())[1:2] if eid.startswith('light.')), example_light) or example_entity_1
    else:
        example_light = '{LIGHT_ENTITY}'
        example_sensor = '{SENSOR_ENTITY}'
        example_door_sensor = '{DOOR_SENSOR_ENTITY}'
        example_motion_sensor = '{MOTION_SENSOR_ENTITY}'
        example_wled = '{WLED_ENTITY}'
        example_entity_1 = '{ENTITY_1}'
        example_entity_2 = '{ENTITY_2}'
    
    prompt = f"""
You are a Home Assistant automation YAML generator expert with deep knowledge of advanced HA features.

User's original request: "{original_query}"

Automation suggestion:
- Description: {suggestion.get('description', '')}
- Trigger: {suggestion.get('trigger_summary', '')}
- Action: {suggestion.get('action_summary', '')}
- Devices: {', '.join(suggestion.get('devices_involved', []))}

{validated_entities_text}

{"🔴 TEST MODE WITH SEQUENCES: For quick testing - Generate automation YAML with shortened delays (10x faster):" if is_sequence_test else ("🔴 TEST MODE: For manual testing - Generate simple automation YAML:" if is_test else "Generate a sophisticated Home Assistant automation YAML configuration that brings this creative suggestion to life.")}
{"- Use event trigger that fires immediately on manual trigger" if is_test else ""}
{"- SHORTEN all delays by 10x (e.g., 2 seconds → 0.2 seconds, 30 seconds → 3 seconds)" if is_sequence_test else ("- NO delays or timing components" if is_test else "")}
{"- REDUCE repeat counts (e.g., 5 times → 2 times, 10 times → 3 times) for quick preview" if is_sequence_test else ("- NO repeat loops or sequences (just execute once)" if is_test else "")}
{"- Keep sequences and repeat blocks but execute faster" if is_sequence_test else ("- Action should execute the device control immediately" if is_test else "")}
{"- Example: If original has 'delay: 00:00:05', use 'delay: 00:00:00.5' (or 0.5 seconds)" if is_sequence_test else ("- Example trigger: platform: event, event_type: test_trigger" if is_test else "")}

Requirements:
1. Use YAML format (not JSON)
2. Include: id, alias, trigger, action
3. **ABSOLUTELY CRITICAL - READ THIS CAREFULLY:**
   - Use ONLY the validated entity IDs provided in the VALIDATED ENTITIES list above
   - DO NOT create new entity IDs - this will cause automation creation to FAIL
   - DO NOT use entity IDs from examples below - those are just formatting examples
   - DO NOT invent entity IDs based on device names - ONLY use the validated list
   - If an entity is NOT in the validated list, DO NOT invent it
   - NEVER create entity IDs like "binary_sensor.office_desk_presence" or "light.office" if they're not in the validated list
   - If the suggestion requires entities that are NOT in the validated list above:
     a) SIMPLIFY THE AUTOMATION to only use validated entities, OR
     b) Use a time-based trigger instead of missing sensor triggers, OR
     c) Return an error explaining which entities are missing from the validated list
   - Example: If suggestion needs "presence sensor" but none exists in validated entities → use time trigger instead
   - Creating fake entity IDs will cause automation creation to FAIL with "Entity not found" errors
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

CRITICAL YAML STRUCTURE RULES:
1. **Entity IDs MUST ALWAYS be in format: domain.entity (use ONLY validated entities from the list above)**
   - **DO NOT use the example entity IDs shown below** - those are just formatting examples
   - **MUST use actual entity IDs from the VALIDATED ENTITIES list above**
   - NEVER use incomplete entity IDs like "wled", "office", or "WLED"
   - NEVER create entity IDs based on the examples - examples use placeholders like PLACEHOLDER_ENTITY_ID
   - If you see "wled" in the description, find the actual WLED entity ID from the VALIDATED ENTITIES list above
   - IMPORTANT: The examples below show YAML STRUCTURE only - replace ALL example entity IDs with real ones from the validated list above
2. Service calls ALWAYS use target.entity_id structure:
   ```yaml
   - service: light.turn_on
     target:
       entity_id: {example_light if example_light else '{LIGHT_ENTITY}'}
   ```
   NEVER use entity_id directly in the action!
   NOTE: Replace the entity ID above with an actual validated entity ID from the list above
3. Multiple entities use list format:
   ```yaml
   target:
     entity_id:
       - {example_entity_1 if example_entity_1 else '{ENTITY_1}'}
       - {example_entity_2 if example_entity_2 else '{ENTITY_2}'}
   ```
   NOTE: Replace these with actual validated entity IDs from the list above
4. Required fields: alias, trigger, action
5. Always include mode: single (or restart, queued, parallel)

Advanced YAML Examples (NOTE: Replace entity IDs with validated ones from above):

Example 1 - Simple time trigger (CORRECT):
```yaml
alias: Morning Light
description: Turn on light at 7 AM
mode: single
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: {example_light if example_light else '{{REPLACE_WITH_VALIDATED_LIGHT_ENTITY}}'}
    data:
      brightness_pct: 100
```

Example 2 - State trigger with condition (CORRECT):
```yaml
alias: Motion-Activated Light
description: Turn on light when motion detected after 6 PM
mode: single
trigger:
  - platform: state
    entity_id: {example_motion_sensor if example_motion_sensor else '{{REPLACE_WITH_VALIDATED_MOTION_SENSOR}}'}
    to: 'on'
condition:
  - condition: time
    after: '18:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: {example_light if example_light else '{{REPLACE_WITH_VALIDATED_LIGHT_ENTITY}}'}
    data:
      brightness_pct: 75
      color_name: warm_white
```

Example 3 - Repeat with sequence (CORRECT):
```yaml
alias: Flash Pattern
description: Flash lights 3 times
mode: single
trigger:
  - platform: event
    event_type: test_trigger
action:
  - repeat:
      count: 3
      sequence:
        - service: light.turn_on
          target:
            entity_id: {example_light if example_light else '{{REPLACE_WITH_VALIDATED_LIGHT_ENTITY}}'}
          data:
            brightness_pct: 100
        - delay: '00:00:01'
        - service: light.turn_off
          target:
            entity_id: {example_light if example_light else '{{REPLACE_WITH_VALIDATED_LIGHT_ENTITY}}'}
        - delay: '00:00:01'
```

Example 4 - Choose with multiple triggers (CORRECT):
```yaml
alias: Color-Coded Door Notifications
description: Different colors for different doors
mode: single
trigger:
  - platform: state
    entity_id: {example_door_sensor if example_door_sensor else '{{REPLACE_WITH_VALIDATED_DOOR_SENSOR_1}}'}
    to: 'on'
    id: front_door
  - platform: state
    entity_id: {example_door_sensor if example_door_sensor else '{{REPLACE_WITH_VALIDATED_DOOR_SENSOR_2}}'}
    to: 'on'
    id: back_door
condition:
  - condition: time
    after: "18:00:00"
    before: "06:00:00"
action:
  - choose:
      - conditions:
          - condition: trigger
            id: front_door
        sequence:
          - service: light.turn_on
            target:
              entity_id: {example_light if example_light else '{{REPLACE_WITH_VALIDATED_LIGHT_ENTITY}}'}
            data:
              brightness_pct: 100
              color_name: red
      - conditions:
          - condition: trigger
            id: back_door
        sequence:
          - service: light.turn_on
            target:
              entity_id: {example_light if example_light else '{{REPLACE_WITH_VALIDATED_LIGHT_ENTITY}}'}
            data:
              brightness_pct: 100
              color_name: blue
    default:
      - service: light.turn_on
        target:
          entity_id: {example_light if example_light else '{{REPLACE_WITH_VALIDATED_LIGHT_ENTITY}}'}
        data:
          brightness_pct: 50
          color_name: white
```

CRITICAL STRUCTURE RULES - DO NOT MAKE THESE MISTAKES:

1. TRIGGER STRUCTURE:
   ❌ WRONG: triggers: (plural) or trigger: state
   ✅ CORRECT: trigger: (singular) and platform: state
   
   Example (replace entity IDs with validated ones from above):
   ❌ WRONG:
     triggers:
       - entity_id: {example_sensor if example_sensor else '{SENSOR_ENTITY}'}
         trigger: state
   ✅ CORRECT:
     trigger:
       - platform: state
         entity_id: {example_sensor if example_sensor else '{SENSOR_ENTITY}'}

2. ACTION STRUCTURE:
   ❌ WRONG: actions: (plural) or action: light.turn_on (inside action list)
   ✅ CORRECT: action: (singular) and service: light.turn_on (inside actions)
   
   Example:
   ❌ WRONG:
     actions:
       - action: light.turn_on
   ✅ CORRECT:
     action:
       - service: light.turn_on

3. SEQUENCE STRUCTURE:
   ❌ WRONG:
     action:
       - sequence:
           - action: light.turn_on  # ❌ WRONG FIELD NAME
  ✅ CORRECT:
    action:
      - sequence:
          - service: light.turn_on  # ✅ CORRECT FIELD NAME
            target:
              entity_id: {example_light if example_light else '{{REPLACE_WITH_VALIDATED_LIGHT_ENTITY}}'}  # ✅ FULL ENTITY ID (domain.entity)
          - service: light.turn_on  # ✅ WLED entities use light.turn_on service (NOT wled.turn_on)
            target:
              entity_id: {example_wled if example_wled else '{{REPLACE_WITH_VALIDATED_WLED_ENTITY}}'}  # ✅ FULL ENTITY ID (domain.entity)
            data:
              effect: fireworks  # WLED-specific effect parameter
          - delay: "00:01:00"
          - service: light.turn_off  # ✅ WLED entities use light.turn_off service (NOT wled.turn_off)
            target:
              entity_id: {example_wled if example_wled else '{{REPLACE_WITH_VALIDATED_WLED_ENTITY}}'}  # ✅ FULL ENTITY ID (domain.entity)

4. FIELD NAMES IN ACTIONS:
   - Top level: Use "action:" (singular)
   - Inside action list: Use "service:" NOT "action:"
   - In triggers: Use "platform:" NOT "trigger:"

COMMON MISTAKES TO AVOID:
❌ WRONG: entity_id: {example_light if example_light else '{LIGHT_ENTITY}'} (in action directly, missing target wrapper)
✅ CORRECT: target: {{ entity_id: {example_light if example_light else '{LIGHT_ENTITY}'} }}

❌ WRONG: entity_id: wled (INCOMPLETE - missing entity name, will cause "Entity not found" error)
✅ CORRECT: target: {{ entity_id: {example_wled if example_wled else '{WLED_ENTITY}'} }} (COMPLETE - domain.entity format from validated list)

❌ WRONG: entity_id: office (INCOMPLETE - missing domain prefix, will cause "Entity not found" error)
✅ CORRECT: target: {{ entity_id: {example_light if example_light else '{LIGHT_ENTITY}'} }} (COMPLETE - domain.entity format from validated list)

❌ WRONG: service: wled.turn_on (WLED entities use light.turn_on service - wled.turn_on does NOT exist)
✅ CORRECT: service: light.turn_on with target.entity_id: {example_wled if example_wled else '{WLED_ENTITY}'} (WLED entities are lights, use validated entity ID)

REMEMBER:
1. Every entity_id MUST have BOTH domain AND entity name separated by a dot!
2. ALL light entities (including WLED) use light.turn_on/light.turn_off services
3. If the description mentions "wled", look up the full entity ID from the VALIDATED ENTITIES section above.
4. Use light.turn_on service for WLED entities, NOT wled.turn_on (that service doesn't exist in HA)
5. NEVER create entity IDs - ONLY use the validated entity IDs provided in the list above

❌ WRONG: entity_id: "office" (missing domain, NOT from validated list)
✅ CORRECT: entity_id: {example_light if example_light else 'USE_VALIDATED_ENTITY'} (from validated list above)

❌ WRONG: service: light.turn_on without target
✅ CORRECT: service: light.turn_on with target.entity_id

❌ WRONG: trigger: state (in trigger definition)
✅ CORRECT: platform: state (in trigger definition)

❌ WRONG: action: light.turn_on (inside action list)
✅ CORRECT: service: light.turn_on (inside action list)

**FINAL REMINDER BEFORE GENERATING YAML:**
1. The examples above show YAML STRUCTURE ONLY - DO NOT copy their entity IDs
2. ALL entity IDs MUST come from the VALIDATED ENTITIES list at the top
3. If an entity ID isn't in that validated list, DO NOT use it - find a similar one from the list or fail
4. Creating entity IDs that don't exist will cause automation creation to FAIL

Generate ONLY the YAML content, no explanations or markdown code blocks. Use ONLY the validated entity IDs from the list above. Follow the structure examples exactly for YAML syntax, but replace ALL entity IDs with real ones from the validated list. DOUBLE-CHECK that you use "platform:" in triggers and "service:" in actions.
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
            max_tokens=2000  # Increased to prevent truncation of complex automations
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
        
        # Validate YAML syntax
        try:
            yaml_lib.safe_load(yaml_content)
            logger.info(f"✅ Generated valid YAML syntax")
        except yaml_lib.YAMLError as e:
            logger.error(f"❌ Generated invalid YAML syntax: {e}")
            raise ValueError(f"Generated YAML syntax is invalid: {e}")
        
        # Validate YAML structure and fix service names (e.g., wled.turn_on → light.turn_on)
        from ..services.yaml_structure_validator import YAMLStructureValidator
        validator = YAMLStructureValidator()
        validation = validator.validate(yaml_content)
        
        # Use fixed YAML if validation made fixes
        if validation.fixed_yaml:
            yaml_content = validation.fixed_yaml
            service_fixes = [w for w in validation.warnings if '→' in w]
            if service_fixes:
                logger.info(f"✅ Applied {len(service_fixes)} service name fixes")
        
        if not validation.is_valid:
            logger.warning(f"⚠️ YAML structure validation found issues: {validation.errors[:3]}")
            # Log but don't fail - will be caught by HA API when creating automation
        
        # Debug: Print the final YAML content
        logger.info("=" * 80)
        logger.info("📋 FINAL HA AUTOMATION YAML")
        logger.info("=" * 80)
        logger.info(yaml_content)
        logger.info("=" * 80)
        
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


async def build_device_selection_debug_data(
    devices_involved: List[str],
    validated_entities: Dict[str, str],
    enriched_data: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Build debug data explaining why each device was selected.
    
    Args:
        devices_involved: List of device friendly names
        validated_entities: Mapping of device_name -> entity_id
        enriched_data: Enriched entity data
        
    Returns:
        List of device debug objects with selection reasoning
    """
    device_debug = []
    
    for device_name in devices_involved:
        entity_id = validated_entities.get(device_name)
        if not entity_id:
            device_debug.append({
                'device_name': device_name,
                'entity_id': None,
                'selection_reason': 'Not mapped to any entity',
                'entity_type': None,
                'entities': [],
                'capabilities': [],
                'actions_suggested': []
            })
            continue
        
        enriched = enriched_data.get(entity_id, {})
        friendly_name = enriched.get('friendly_name', entity_id)
        entity_type = enriched.get('entity_type', 'individual')
        
        # Build selection reason
        reasons = []
        if device_name.lower() == friendly_name.lower():
            reasons.append(f"Exact match: '{device_name}' matches entity friendly_name")
        elif device_name.lower() in friendly_name.lower():
            reasons.append(f"Partial match: '{device_name}' found in '{friendly_name}'")
        else:
            reasons.append(f"Fuzzy match: '{device_name}' mapped to '{friendly_name}'")
        
        # Get all entities for groups
        entities = []
        if entity_type == 'group':
            member_entities = enriched.get('member_entities', [])
            entities = [{'entity_id': eid, 'friendly_name': enriched_data.get(eid, {}).get('friendly_name', eid)} 
                       for eid in member_entities]
        else:
            entities = [{'entity_id': entity_id, 'friendly_name': friendly_name}]
        
        # Get capabilities
        capabilities = enriched.get('capabilities', [])
        capabilities_list = []
        for cap in capabilities:
            if isinstance(cap, dict):
                feature = cap.get('feature', 'unknown')
                supported = cap.get('supported', False)
                if supported:
                    capabilities_list.append(feature)
            else:
                capabilities_list.append(str(cap))
        
        # Determine suggested actions based on domain and capabilities
        domain = entity_id.split('.')[0] if '.' in entity_id else 'unknown'
        actions_suggested = []
        if domain == 'light':
            actions_suggested.append('light.turn_on')
            if 'brightness' in capabilities_list:
                actions_suggested.append('light.set_brightness')
            if 'color' in capabilities_list or 'rgb' in capabilities_list:
                actions_suggested.append('light.set_color')
        elif domain == 'switch':
            actions_suggested.append('switch.turn_on')
            actions_suggested.append('switch.turn_off')
        elif domain == 'binary_sensor':
            actions_suggested.append('state_change_trigger')
        elif domain == 'sensor':
            actions_suggested.append('state_reading')
        
        device_debug.append({
            'device_name': device_name,
            'entity_id': entity_id,
            'selection_reason': '; '.join(reasons),
            'entity_type': entity_type,
            'entities': entities,
            'capabilities': capabilities_list,
            'actions_suggested': actions_suggested
        })
    
    return device_debug


async def generate_technical_prompt(
    suggestion: Dict[str, Any],
    validated_entities: Dict[str, str],
    enriched_data: Dict[str, Dict[str, Any]],
    query: str
) -> Dict[str, Any]:
    """
    Generate technical prompt for YAML generation.
    
    This prompt contains structured information about:
    - Trigger entities and their states
    - Action entities and their service calls
    - Conditions and logic
    - Entity capabilities and constraints
    
    Args:
        suggestion: Suggestion dictionary
        validated_entities: Mapping of device_name -> entity_id
        enriched_data: Enriched entity data
        query: Original user query
        
    Returns:
        Dictionary with technical prompt details
    """
    import re
    
    # Extract trigger entities from suggestion
    trigger_entities = []
    trigger_summary = suggestion.get('trigger_summary', '').lower()
    action_summary = suggestion.get('action_summary', '').lower()
    description = suggestion.get('description', '').lower()
    
    # Classify entities as triggers or actions based on domain and summary
    for device_name, entity_id in validated_entities.items():
        enriched = enriched_data.get(entity_id, {})
        if not enriched:
            continue
            
        domain = enriched.get('domain', entity_id.split('.')[0] if '.' in entity_id else 'unknown')
        friendly_name = enriched.get('friendly_name', device_name)
        
        # Check if this entity is mentioned in trigger context
        device_lower = device_name.lower()
        friendly_lower = friendly_name.lower()
        
        # Check if entity appears in trigger-related text
        is_trigger = (
            device_lower in trigger_summary or 
            friendly_lower in trigger_summary or
            device_lower in description or
            friendly_lower in description
        ) and (
            domain in ['binary_sensor', 'sensor', 'button', 'event'] or
            'sensor' in device_lower or
            'detect' in trigger_summary or
            'when' in trigger_summary or
            'trigger' in trigger_summary
        )
        
        # Check if entity appears in action context
        is_action = (
            device_lower in action_summary or 
            friendly_lower in action_summary or
            device_lower in description or
            friendly_lower in description
        ) and (
            domain in ['light', 'switch', 'fan', 'climate', 'cover', 'lock', 'media_player']
        )
        
        # Default: if domain suggests it's a sensor, it's a trigger; if it's a control domain, it's an action
        if not is_trigger and not is_action:
            if domain in ['binary_sensor', 'sensor', 'button', 'event']:
                is_trigger = True
            elif domain in ['light', 'switch', 'fan', 'climate', 'cover', 'lock', 'media_player']:
                is_action = True
        
        # Add as trigger entity
        if is_trigger:
            trigger_entity = {
                'entity_id': entity_id,
                'friendly_name': friendly_name,
                'domain': domain,
                'platform': 'state',  # Default
                'from': None,
                'to': None
            }
            
            # Extract state transitions from trigger_summary
            if 'on' in trigger_summary or 'detect' in trigger_summary or 'trigger' in trigger_summary:
                trigger_entity['to'] = 'on'
                trigger_entity['from'] = 'off'
            elif 'off' in trigger_summary:
                trigger_entity['to'] = 'off'
                trigger_entity['from'] = 'on'
            
            trigger_entities.append(trigger_entity)
    
    # Extract action entities and determine service calls
    action_entities = []
    all_service_calls = []
    
    for device_name, entity_id in validated_entities.items():
        enriched = enriched_data.get(entity_id, {})
        if not enriched:
            continue
            
        domain = enriched.get('domain', entity_id.split('.')[0] if '.' in entity_id else 'unknown')
        friendly_name = enriched.get('friendly_name', device_name)
        
        # Check if this entity should be in actions
        device_lower = device_name.lower()
        friendly_lower = friendly_name.lower()
        
        is_action_entity = (
            device_lower in action_summary or 
            friendly_lower in action_summary or
            device_lower in description or
            friendly_lower in description
        ) or domain in ['light', 'switch', 'fan', 'climate', 'cover', 'lock', 'media_player']
        
        if not is_action_entity:
            continue
        
        # Get capabilities to determine service calls
        capabilities = enriched.get('capabilities', [])
        capabilities_list = []
        for cap in capabilities:
            if isinstance(cap, dict):
                # Try different field names for capability name
                cap_name = cap.get('name') or cap.get('feature') or cap.get('capability_name', '')
                cap_supported = cap.get('supported', cap.get('exposed', True))
                if cap_supported and cap_name:
                    capabilities_list.append(cap_name.lower())
            elif isinstance(cap, str):
                capabilities_list.append(cap.lower())
        
        # Determine service calls based on domain, capabilities, and action summary
        service_calls = []
        
        if domain == 'light':
            # Check action summary for specific actions
            if 'flash' in action_summary or 'flash' in description:
                service_calls.append({
                    'service': 'light.turn_on',
                    'parameters': {'flash': 'short'}
                })
            elif 'turn on' in action_summary or 'on' in action_summary or 'activate' in action_summary:
                service_calls.append({
                    'service': 'light.turn_on',
                    'parameters': {}
                })
            elif 'turn off' in action_summary or 'off' in action_summary:
                service_calls.append({
                    'service': 'light.turn_off',
                    'parameters': {}
                })
            else:
                # Default: turn on
                service_calls.append({
                    'service': 'light.turn_on',
                    'parameters': {}
                })
            
            # Add brightness if mentioned and capability exists
            if ('brightness' in action_summary or 'dim' in action_summary or 'bright' in action_summary) and 'brightness' in capabilities_list:
                brightness_match = re.search(r'(\d+)%', action_summary)
                brightness_pct = int(brightness_match.group(1)) if brightness_match else 100
                service_calls.append({
                    'service': 'light.turn_on',
                    'parameters': {'brightness_pct': brightness_pct}
                })
            
            # Add color if mentioned and capability exists
            if ('color' in action_summary or 'rgb' in action_summary or 'multi-color' in action_summary or 'multicolor' in action_summary) and ('color' in capabilities_list or 'rgb' in capabilities_list):
                service_calls.append({
                    'service': 'light.turn_on',
                    'parameters': {'rgb_color': [255, 255, 255]}  # Default white
                })
            
            # Add effect if mentioned (e.g., "fireworks" for WLED)
            if 'effect' in capabilities_list:
                action_lower = action_summary.lower() + ' ' + description.lower()
                # Check for common WLED effects
                wled_effects = ['fireworks', 'sparkle', 'rainbow', 'strobe', 'pulse', 'cylon', 'bpm', 'chase', 'police', 'twinkle']
                for effect_name in wled_effects:
                    if effect_name in action_lower:
                        service_calls.append({
                            'service': 'light.turn_on',
                            'parameters': {'effect': effect_name}
                        })
                        logger.info(f"✅ Detected WLED effect '{effect_name}' from action summary")
                        break
                
        elif domain == 'switch':
            if 'turn on' in action_summary or 'on' in action_summary:
                service_calls.append({
                    'service': 'switch.turn_on',
                    'parameters': {}
                })
            elif 'turn off' in action_summary or 'off' in action_summary:
                service_calls.append({
                    'service': 'switch.turn_off',
                    'parameters': {}
                })
            else:
                service_calls.append({
                    'service': 'switch.turn_on',
                    'parameters': {}
                })
                
        elif domain == 'fan':
            if 'turn on' in action_summary or 'on' in action_summary:
                service_calls.append({
                    'service': 'fan.turn_on',
                    'parameters': {}
                })
            elif 'turn off' in action_summary or 'off' in action_summary:
                service_calls.append({
                    'service': 'fan.turn_off',
                    'parameters': {}
                })
        
        elif domain == 'climate':
            if 'turn on' in action_summary or 'on' in action_summary:
                service_calls.append({
                    'service': 'climate.turn_on',
                    'parameters': {}
                })
            elif 'turn off' in action_summary or 'off' in action_summary:
                service_calls.append({
                    'service': 'climate.turn_off',
                    'parameters': {}
                })
        
        # If no service calls determined, add default based on domain
        if not service_calls and domain in ['light', 'switch', 'fan', 'climate']:
            service_calls.append({
                'service': f'{domain}.turn_on',
                'parameters': {}
            })
        
        if service_calls:
            action_entity = {
                'entity_id': entity_id,
                'friendly_name': friendly_name,
                'domain': domain,
                'service_calls': service_calls
            }
            action_entities.append(action_entity)
            all_service_calls.extend(service_calls)
    
    # Build entity capabilities mapping for ALL entities
    entity_capabilities = {}
    for entity_id in validated_entities.values():
        enriched = enriched_data.get(entity_id, {})
        if not enriched:
            continue
            
        capabilities = enriched.get('capabilities', [])
        capabilities_list = []
        
        for cap in capabilities:
            if isinstance(cap, dict):
                # Try different field names
                cap_name = cap.get('name') or cap.get('feature') or cap.get('capability_name', '')
                cap_supported = cap.get('supported', cap.get('exposed', True))
                if cap_supported and cap_name:
                    # Include full capability info if available
                    cap_info = {
                        'name': cap_name,
                        'type': cap.get('type', 'unknown'),
                        'properties': cap.get('properties', {})
                    }
                    capabilities_list.append(cap_info)
            elif isinstance(cap, str):
                capabilities_list.append({'name': cap, 'type': 'unknown', 'properties': {}})
        
        # Also include supported_features if available
        supported_features = enriched.get('supported_features')
        if supported_features is not None:
            # supported_features is typically a bitmask, but we can include it
            entity_capabilities[entity_id] = {
                'capabilities': capabilities_list,
                'supported_features': supported_features,
                'domain': enriched.get('domain', entity_id.split('.')[0] if '.' in entity_id else 'unknown'),
                'friendly_name': enriched.get('friendly_name', entity_id),
                'attributes': enriched.get('attributes', {})
            }
        else:
            entity_capabilities[entity_id] = {
                'capabilities': capabilities_list,
                'domain': enriched.get('domain', entity_id.split('.')[0] if '.' in entity_id else 'unknown'),
                'friendly_name': enriched.get('friendly_name', entity_id),
                'attributes': enriched.get('attributes', {})
            }
    
    technical_prompt = {
        'alias': suggestion.get('description', 'AI Generated Automation')[:100],
        'description': suggestion.get('description', ''),
        'trigger': {
            'entities': trigger_entities,
            'platform': 'state' if trigger_entities else None
        },
        'action': {
            'entities': action_entities,
            'service_calls': all_service_calls
        },
        'conditions': [],
        'entity_capabilities': entity_capabilities,
        'metadata': {
            'query': query,
            'devices_involved': list(validated_entities.keys()),
            'confidence': suggestion.get('confidence', 0.8),
            'trigger_summary': suggestion.get('trigger_summary', ''),
            'action_summary': suggestion.get('action_summary', '')
        }
    }
    
    return technical_prompt


async def generate_suggestions_from_query(
    query: str, 
    entities: List[Dict[str, Any]], 
    user_id: str,
    clarification_context: Optional[Dict[str, Any]] = None  # NEW: Clarification Q&A
) -> List[Dict[str, Any]]:
    """Generate automation suggestions based on query and entities"""
    if not openai_client:
        raise ValueError("OpenAI client not available - cannot generate suggestions")
    
    try:
        # Use unified prompt builder for consistent prompt generation
        from ..prompt_building.unified_prompt_builder import UnifiedPromptBuilder
        
        unified_builder = UnifiedPromptBuilder(device_intelligence_client=_device_intelligence_client)
        
        # NEW: Resolve and enrich entities with full attribute data (like YAML generation does)
        entity_context_json = ""
        resolved_entity_ids = []
        enriched_data = {}  # Initialize at function level for use in suggestion building
        
        try:
            logger.info("🔍 Resolving and enriching entities for suggestion generation...")
            
            # Initialize HA client and entity validator
            ha_client = HomeAssistantClient(
                ha_url=settings.ha_url,
                access_token=settings.ha_token
            ) if settings.ha_url and settings.ha_token else None
            
            if ha_client:
                # Step 1: Fetch ALL entities matching query context (location + domain)
                # This finds all lights in the office (e.g., all 6 lights including WLED)
                # instead of just mapping generic names to single entities
                from ..services.entity_validator import EntityValidator
                from ..clients.data_api_client import DataAPIClient
                
                data_api_client = DataAPIClient()
                entity_validator = EntityValidator(data_api_client, db_session=None, ha_client=ha_client)
                
                # Extract location and ALL domains from query to get ALL matching entities
                query_location = entity_validator._extract_location_from_query(query)
                query_domains = entity_validator._extract_all_domains_from_query(query)  # Get ALL domains
                query_domain = query_domains[0] if query_domains else None  # Keep single domain for logging
                
                # NEW: If clarification context has selected entities, prioritize those
                qa_selected_entity_ids = []
                if clarification_context and clarification_context.get('questions_and_answers'):
                    for qa in clarification_context['questions_and_answers']:
                        selected = qa.get('selected_entities', [])
                        if selected:
                            for entity_ref in selected:
                                # Check if it's an entity_id (contains '.')
                                if '.' in entity_ref and (entity_ref.startswith('light.') or 
                                                          entity_ref.startswith('switch.') or
                                                          entity_ref.startswith('binary_sensor.') or
                                                          entity_ref.startswith('sensor.')):
                                    qa_selected_entity_ids.append(entity_ref)
                
                if qa_selected_entity_ids:
                    logger.info(f"🔍 Found {len(qa_selected_entity_ids)} selected entity IDs from Q&A: {qa_selected_entity_ids}")
                
                logger.info(f"🔍 Extracted location='{query_location}', domains={query_domains} from query")
                
                # Fetch ALL entities matching the query context (all domains, all office lights, all sensors)
                resolved_entity_ids = []
                all_available_entities = []
                
                # NEW: If Q&A selected entities exist, start with those
                if qa_selected_entity_ids:
                    logger.info(f"🔍 Prioritizing {len(qa_selected_entity_ids)} Q&A-selected entities")
                    # Verify these entities exist and fetch their details
                    for entity_id in qa_selected_entity_ids:
                        try:
                            # Get entity state to verify it exists
                            state = await ha_client.get_entity_state(entity_id)
                            if state:
                                # Build entity dict from state
                                attributes = state.get('attributes', {})
                                entity_dict = {
                                    'entity_id': entity_id,
                                    'friendly_name': attributes.get('friendly_name', entity_id.split('.')[-1].replace('_', ' ').title()),
                                    'area_id': attributes.get('area_id'),
                                    'domain': entity_id.split('.')[0] if '.' in entity_id else 'unknown'
                                }
                                all_available_entities.append(entity_dict)
                                logger.info(f"✅ Verified Q&A-selected entity: {entity_id} ({entity_dict['friendly_name']})")
                        except Exception as e:
                            logger.warning(f"⚠️ Q&A-selected entity {entity_id} not found or invalid: {e}")
                
                # Fetch entities for each domain found in query
                for domain in query_domains:
                    available_entities = await entity_validator._get_available_entities(
                        domain=domain,
                        area_id=query_location
                    )
                    if available_entities:
                        # Add only if not already in Q&A-selected entities
                        for entity in available_entities:
                            entity_id = entity.get('entity_id')
                            if entity_id and entity_id not in qa_selected_entity_ids:
                                all_available_entities.append(entity)
                        logger.info(f"✅ Found {len(available_entities)} entities for domain '{domain}' in location '{query_location}'")
                
                # If no domains found, try fetching without domain filter (location only)
                if not all_available_entities and query_location:
                    logger.info(f"⚠️ No entities found for specific domains, trying location-only fetch...")
                    all_available_entities = await entity_validator._get_available_entities(
                        domain=None,
                        area_id=query_location
                    )
                    if all_available_entities:
                        logger.info(f"✅ Found {len(all_available_entities)} entities in location '{query_location}' (no domain filter)")
                
                if all_available_entities:
                    # Get all entity IDs that match the query context
                    resolved_entity_ids = [e.get('entity_id') for e in all_available_entities if e.get('entity_id')]
                    # Remove duplicates while preserving order
                    seen = set()
                    unique_entity_ids = []
                    for eid in resolved_entity_ids:
                        if eid not in seen:
                            seen.add(eid)
                            unique_entity_ids.append(eid)
                    resolved_entity_ids = unique_entity_ids
                    
                    logger.info(f"✅ Found {len(resolved_entity_ids)} unique entities matching query context (location={query_location}, domains={query_domains})")
                    logger.debug(f"Resolved entity IDs: {resolved_entity_ids[:10]}...")  # Log first 10
                    
                    # Expand group entities to their individual member entities (generic, no hardcoding)
                    resolved_entity_ids = await expand_group_entities_to_members(
                        resolved_entity_ids,
                        ha_client,
                        entity_validator
                    )
                else:
                    # Fallback: try mapping device names (may only return one per term)
                    device_names = [e.get('name') for e in entities if e.get('name')]
                    if device_names:
                        logger.info(f"🔍 No entities found by location/domain, trying device name mapping...")
                        entity_mapping = await entity_validator.map_query_to_entities(query, device_names)
                        if entity_mapping:
                            resolved_entity_ids = list(entity_mapping.values())
                            logger.info(f"✅ Resolved {len(entity_mapping)} device names to {len(resolved_entity_ids)} entity IDs")
                            
                            # Expand group entities to individual members
                            resolved_entity_ids = await expand_group_entities_to_members(
                                resolved_entity_ids,
                                ha_client,
                                entity_validator
                            )
                        else:
                            # Last fallback: extract entity IDs directly from entities
                            resolved_entity_ids = [e.get('entity_id') for e in entities if e.get('entity_id')]
                            if resolved_entity_ids:
                                logger.info(f"⚠️ Using {len(resolved_entity_ids)} entity IDs from extracted entities")
                            else:
                                logger.warning("⚠️ No entity IDs found for enrichment")
                                resolved_entity_ids = []
                    else:
                        resolved_entity_ids = []
                        logger.warning("⚠️ No entities found and no device names to map")
                
                # Step 2: Enrich resolved entity IDs with COMPREHENSIVE data from ALL sources
                if resolved_entity_ids:
                    logger.info(f"🔍 Comprehensively enriching {len(resolved_entity_ids)} resolved entities...")

                    # NEW: Fetch enrichment context (weather, carbon, energy, air quality)
                    # Feature flag: Enable/disable enrichment context
                    enable_enrichment = os.getenv('ENABLE_ENRICHMENT_CONTEXT', 'true').lower() == 'true'
                    enrichment_context = None

                    if enable_enrichment:
                        try:
                            logger.info("🌍 Fetching enrichment context (weather, carbon, energy, air quality)...")
                            from ..services.enrichment_context_fetcher import (
                                EnrichmentContextFetcher,
                                should_include_weather,
                                should_include_carbon,
                                should_include_energy,
                                should_include_air_quality
                            )

                            # Initialize enrichment fetcher with InfluxDB client
                            if data_api_client and hasattr(data_api_client, 'influxdb_client'):
                                enrichment_fetcher = EnrichmentContextFetcher(data_api_client.influxdb_client)

                                # Selective enrichment based on query and entities
                                enrichment_tasks = []
                                enrichment_types = []
                                entity_id_set = set(resolved_entity_ids)

                                if should_include_weather(query, entity_id_set):
                                    enrichment_tasks.append(enrichment_fetcher.get_current_weather())
                                    enrichment_types.append('weather')

                                if should_include_carbon(query, entity_id_set):
                                    enrichment_tasks.append(enrichment_fetcher.get_carbon_intensity())
                                    enrichment_types.append('carbon')

                                if should_include_energy(query, entity_id_set):
                                    enrichment_tasks.append(enrichment_fetcher.get_electricity_pricing())
                                    enrichment_types.append('energy')

                                if should_include_air_quality(query, entity_id_set):
                                    enrichment_tasks.append(enrichment_fetcher.get_air_quality())
                                    enrichment_types.append('air_quality')

                                # Fetch selected enrichment in parallel
                                if enrichment_tasks:
                                    import asyncio
                                    results = await asyncio.gather(*enrichment_tasks, return_exceptions=True)

                                    enrichment_context = {}
                                    for i, result in enumerate(results):
                                        if isinstance(result, dict) and result:
                                            enrichment_context[enrichment_types[i]] = result

                                    logger.info(f"✅ Fetched {len(enrichment_context)}/{len(enrichment_types)} enrichment types: {list(enrichment_context.keys())}")
                                else:
                                    logger.info("ℹ️  No relevant enrichment for this query")
                            else:
                                logger.warning("⚠️ Data API client or InfluxDB client not available for enrichment")
                        except Exception as e:
                            logger.warning(f"⚠️ Enrichment context fetch failed (continuing without enrichment): {e}")
                            enrichment_context = None
                    else:
                        logger.info("ℹ️  Enrichment context disabled via ENABLE_ENRICHMENT_CONTEXT=false")

                    # Use comprehensive enrichment service that combines ALL data sources
                    from ..services.comprehensive_entity_enrichment import enrich_entities_comprehensively
                    enriched_data = await enrich_entities_comprehensively(
                        entity_ids=set(resolved_entity_ids),
                        ha_client=ha_client,
                        device_intelligence_client=_device_intelligence_client,
                        data_api_client=None,  # Could add DataAPIClient if historical patterns needed
                        include_historical=False,  # Set to True to include usage patterns
                        enrichment_context=enrichment_context  # NEW: Add enrichment context
                    )
                    
                    # ========================================================================
                    # LOCATION-AWARE ENTITY EXPANSION (NEW)
                    # ========================================================================
                    # Extract locations mentioned in query and clarification context
                    mentioned_locations = set()
                    query_lower = query.lower()
                    
                    # Common location keywords
                    location_keywords = [
                        'office', 'living room', 'bedroom', 'kitchen', 'bathroom', 'dining room',
                        'garage', 'basement', 'attic', 'hallway', 'entryway', 'patio', 'deck',
                        'outdoor', 'outdoors', 'garden', 'yard', 'backyard', 'front yard'
                    ]
                    
                    # Extract locations from query
                    for keyword in location_keywords:
                        if keyword in query_lower:
                            # Normalize location name (e.g., "living room" -> "living_room")
                            normalized = keyword.replace(' ', '_')
                            mentioned_locations.add(normalized)
                            # Also try the original format
                            mentioned_locations.add(keyword)
                    
                    # Extract locations from clarification context
                    if clarification_context:
                        qa_list = clarification_context.get('questions_and_answers', [])
                        for qa in qa_list:
                            answer = qa.get('answer', '').lower()
                            for keyword in location_keywords:
                                if keyword in answer:
                                    normalized = keyword.replace(' ', '_')
                                    mentioned_locations.add(normalized)
                                    mentioned_locations.add(keyword)
                    
                    # Extract device domain/type from query and entities
                    mentioned_domains = set()
                    if entities:
                        for entity in entities:
                            domain = entity.get('domain', '').lower()
                            if domain and domain != 'unknown':
                                mentioned_domains.add(domain)
                            # Also check name for domain hints
                            name = entity.get('name', '').lower()
                            if 'light' in name or 'lamp' in name:
                                mentioned_domains.add('light')
                            elif 'sensor' in name:
                                mentioned_domains.add('binary_sensor')
                            elif 'switch' in name:
                                mentioned_domains.add('switch')
                    
                    # Expand entities by location if location is mentioned
                    location_expanded_entity_ids = set(resolved_entity_ids)
                    if mentioned_locations and ha_client:
                        logger.info(f"📍 Location-aware expansion: Found locations {mentioned_locations}")
                        for location in mentioned_locations:
                            # Try to expand for each mentioned domain
                            for domain in mentioned_domains:
                                try:
                                    area_entities = await ha_client.get_entities_by_area_and_domain(
                                        area_id=location,
                                        domain=domain
                                    )
                                    if area_entities:
                                        area_entity_ids = [e.get('entity_id') for e in area_entities if e.get('entity_id')]
                                        location_expanded_entity_ids.update(area_entity_ids)
                                        logger.info(f"✅ Expanded by location '{location}' + domain '{domain}': Added {len(area_entity_ids)} entities")
                                        
                                        # Also enrich these new entities
                                        for area_entity in area_entities:
                                            entity_id = area_entity.get('entity_id')
                                            if entity_id and entity_id not in enriched_data:
                                                # Add to enriched_data with basic info
                                                enriched_data[entity_id] = {
                                                    'entity_id': entity_id,
                                                    'friendly_name': area_entity.get('friendly_name', entity_id),
                                                    'area_id': area_entity.get('area_id'),
                                                    'area_name': area_entity.get('area_id'),  # Use area_id as area_name
                                                    'domain': domain,
                                                    'state': area_entity.get('state'),
                                                    'attributes': area_entity.get('attributes', {})
                                                }
                                except Exception as e:
                                    logger.warning(f"⚠️ Error expanding entities for location '{location}' + domain '{domain}': {e}")
                            
                            # If no specific domain, try to get all entities in the area
                            if not mentioned_domains:
                                try:
                                    area_entities = await ha_client.get_entities_by_area_and_domain(
                                        area_id=location,
                                        domain=None
                                    )
                                    if area_entities:
                                        area_entity_ids = [e.get('entity_id') for e in area_entities if e.get('entity_id')]
                                        location_expanded_entity_ids.update(area_entity_ids)
                                        logger.info(f"✅ Expanded by location '{location}' (all domains): Added {len(area_entity_ids)} entities")
                                        
                                        # Enrich new entities
                                        for area_entity in area_entities:
                                            entity_id = area_entity.get('entity_id')
                                            if entity_id and entity_id not in enriched_data:
                                                enriched_data[entity_id] = {
                                                    'entity_id': entity_id,
                                                    'friendly_name': area_entity.get('friendly_name', entity_id),
                                                    'area_id': area_entity.get('area_id'),
                                                    'area_name': area_entity.get('area_id'),
                                                    'domain': area_entity.get('domain', 'unknown'),
                                                    'state': area_entity.get('state'),
                                                    'attributes': area_entity.get('attributes', {})
                                                }
                                except Exception as e:
                                    logger.warning(f"⚠️ Error expanding entities for location '{location}': {e}")
                        
                        # Re-enrich all expanded entities comprehensively
                        if location_expanded_entity_ids != set(resolved_entity_ids):
                            new_entity_ids = location_expanded_entity_ids - set(resolved_entity_ids)
                            logger.info(f"🔄 Re-enriching {len(new_entity_ids)} location-expanded entities")
                            try:
                                from ..services.comprehensive_entity_enrichment import enrich_entities_comprehensively
                                new_enriched = await enrich_entities_comprehensively(
                                    entity_ids=new_entity_ids,
                                    ha_client=ha_client,
                                    device_intelligence_client=_device_intelligence_client,
                                    data_api_client=None,
                                    include_historical=False,
                                    enrichment_context=enrichment_context
                                )
                                enriched_data.update(new_enriched)
                            except Exception as e:
                                logger.warning(f"⚠️ Error re-enriching location-expanded entities: {e}")
                    
                    # Update resolved_entity_ids to include location-expanded entities
                    resolved_entity_ids = list(location_expanded_entity_ids)
                    
                    # ========================================================================
                    # LOCATION-PRIORITY FILTERING (NEW)
                    # ========================================================================
                    # OPTIMIZATION: Filter entity context to reduce token usage
                    # Priority: Location matching > Device name matching
                    # Only include entities that match location OR extracted device names
                    # BUT: Don't filter if extracted names are generic domain terms (e.g., "lights", "sensor", "led")
                    # This reduces prompt size while still giving AI enough context
                    filtered_entity_ids_for_prompt = set(resolved_entity_ids)
                    
                    # Generic domain terms that should NOT trigger filtering (too broad)
                    generic_terms = {
                        'light', 'lights', 'lamp', 'lamps', 'bulb', 'bulbs', 'led', 'leds',
                        'sensor', 'sensors', 'motion', 'presence', 'occupancy', 'contact',
                        'switch', 'switches', 'outlet', 'outlets', 'plug', 'plugs',
                        'door', 'doors', 'window', 'windows', 'blind', 'blinds',
                        'fan', 'fans', 'climate', 'thermostat', 'thermostats',
                        'tv', 'television', 'speaker', 'speakers', 'lock', 'locks'
                    }
                    
                    # Step 1: Filter by location if location is mentioned (HIGHEST PRIORITY)
                    if mentioned_locations:
                        location_filtered_entity_ids = set()
                        for entity_id in resolved_entity_ids:
                            enriched = enriched_data.get(entity_id, {})
                            # Handle None values: get() returns None if key exists but value is None
                            entity_area_id_raw = enriched.get('area_id') or ''
                            entity_area_name_raw = enriched.get('area_name') or ''
                            entity_area_id = entity_area_id_raw.lower() if isinstance(entity_area_id_raw, str) else ''
                            entity_area_name = entity_area_name_raw.lower() if isinstance(entity_area_name_raw, str) else ''
                            
                            # Check if entity is in any mentioned location
                            entity_matches_location = False
                            for location in mentioned_locations:
                                location_lower = location.lower().replace('_', ' ')
                                # Check area_id and area_name
                                if (location_lower in entity_area_id or 
                                    entity_area_id in location_lower or
                                    location_lower in entity_area_name or
                                    entity_area_name in location_lower):
                                    entity_matches_location = True
                                    break
                            
                            if entity_matches_location:
                                location_filtered_entity_ids.add(entity_id)
                        
                        if location_filtered_entity_ids:
                            filtered_entity_ids_for_prompt = location_filtered_entity_ids
                            logger.info(f"📍 Location-filtered: {len(location_filtered_entity_ids)}/{len(resolved_entity_ids)} entities match locations {mentioned_locations}")
                        else:
                            logger.warning(f"⚠️ No entities matched locations {mentioned_locations}, using all entities")
                    
                    # Step 2: Further filter by device name if specific names are mentioned (SECONDARY)
                    if entities:
                        extracted_device_names = [e.get('name', '').lower().strip() for e in entities if e.get('name')]
                        if extracted_device_names:
                            # Check if extracted names are generic domain terms
                            specific_names = [name for name in extracted_device_names if name not in generic_terms]
                            
                            if specific_names and not mentioned_locations:
                                # Only filter by name if no location was mentioned (location takes priority)
                                # We have specific device names, filter to match them
                                matching_entity_ids = set()
                                for entity_id in filtered_entity_ids_for_prompt:
                                    enriched = enriched_data.get(entity_id, {})
                                    friendly_name = enriched.get('friendly_name', '').lower()
                                    entity_id_lower = entity_id.lower()
                                    
                                    # Check if entity matches any specific extracted device name
                                    for device_name in specific_names:
                                        if (device_name in friendly_name or 
                                            friendly_name in device_name or
                                            device_name in entity_id_lower):
                                            matching_entity_ids.add(entity_id)
                                            break
                                
                                # If we found matches, use them; otherwise use all (fallback)
                                if matching_entity_ids:
                                    filtered_entity_ids_for_prompt = matching_entity_ids
                                    logger.info(f"🔍 Name-filtered: {len(matching_entity_ids)}/{len(resolved_entity_ids)} entities match specific extracted device names: {specific_names}")
                                else:
                                    logger.info(f"⚠️ No entities matched specific names {specific_names}, using all {len(resolved_entity_ids)} entities")
                            elif specific_names and mentioned_locations:
                                # Location was mentioned, but also check device names within location-filtered entities
                                # This ensures we don't include wrong device types in the location
                                device_name_filtered = set()
                                for entity_id in filtered_entity_ids_for_prompt:
                                    enriched = enriched_data.get(entity_id, {})
                                    friendly_name = enriched.get('friendly_name', '').lower()
                                    entity_id_lower = entity_id.lower()
                                    
                                    # Check if entity matches any specific extracted device name
                                    for device_name in specific_names:
                                        if (device_name in friendly_name or 
                                            friendly_name in device_name or
                                            device_name in entity_id_lower):
                                            device_name_filtered.add(entity_id)
                                            break
                                    
                                    # Also check if entity domain matches mentioned domains
                                    entity_domain = enriched.get('domain', '').lower()
                                    if entity_domain in mentioned_domains:
                                        device_name_filtered.add(entity_id)
                                
                                if device_name_filtered:
                                    filtered_entity_ids_for_prompt = device_name_filtered
                                    logger.info(f"🔍 Location + Name filtered: {len(device_name_filtered)} entities match both location and device names")
                            else:
                                # All extracted names are generic terms - don't filter by name
                                if mentioned_locations:
                                    logger.info(f"ℹ️ Generic device names {extracted_device_names} but location specified - using location-filtered entities")
                                else:
                                    logger.info(f"ℹ️ Extracted names are generic terms {extracted_device_names}, not filtering - using all {len(resolved_entity_ids)} query-context entities")
                    
                    # Build entity context JSON from filtered entities
                    # Create entity dicts for context builder from enriched data
                    enriched_entities = []
                    for entity_id in filtered_entity_ids_for_prompt:
                        enriched = enriched_data.get(entity_id, {})
                        enriched_entities.append({
                            'entity_id': entity_id,
                            'friendly_name': enriched.get('friendly_name', entity_id),
                            'name': enriched.get('friendly_name', entity_id.split('.')[-1] if '.' in entity_id else entity_id)
                        })
                    
                    # Filter enriched_data to only include entities in prompt
                    filtered_enriched_data_for_prompt = {
                        entity_id: enriched_data[entity_id]
                        for entity_id in filtered_entity_ids_for_prompt
                        if entity_id in enriched_data
                    }
                    
                    context_builder = EntityContextBuilder()
                    entity_context_json = await context_builder.build_entity_context_json(
                        entities=enriched_entities,
                        enriched_data=filtered_enriched_data_for_prompt
                    )
                    
                    logger.info(f"✅ Built entity context JSON with {len(filtered_enriched_data_for_prompt)}/{len(enriched_data)} enriched entities (filtered for prompt)")
                    logger.debug(f"Entity context JSON: {entity_context_json[:500]}...")
                else:
                    logger.warning("⚠️ No entity IDs to enrich - skipping enrichment")
            else:
                logger.warning("⚠️ Home Assistant client not available, skipping entity enrichment")
                
        except Exception as e:
            logger.warning(f"⚠️ Error resolving/enriching entities for suggestions: {e}", exc_info=True)
            entity_context_json = ""
            enriched_data = {}  # Ensure enriched_data is empty on error
        
        # Build unified prompt with device intelligence AND enriched entity context
        prompt_dict = await unified_builder.build_query_prompt(
            query=query,
            entities=entities,
            output_mode="suggestions",
            entity_context_json=entity_context_json,  # Pass enriched context
            clarification_context=clarification_context  # NEW: Pass clarification Q&A
        )
        
        # Generate suggestions with unified prompt
        logger.info(f"Generating suggestions for query: {query}")
        logger.info(f"OpenAI client available: {openai_client is not None}")
        logger.info(f"OpenAI model: {openai_client.model if openai_client else 'None'}")
        
        # Capture OpenAI prompts for debug panel
        openai_debug_data = {
            'system_prompt': prompt_dict.get('system_prompt', ''),
            'user_prompt': prompt_dict.get('user_prompt', ''),
            'openai_response': None,
            'token_usage': None,
            'clarification_context': clarification_context  # NEW: Include clarification in debug
        }
        
        try:
            suggestions_data = await openai_client.generate_with_unified_prompt(
                prompt_dict=prompt_dict,
                temperature=settings.creative_temperature,
                max_tokens=1200,
                output_format="json"
            )
            
            # Store OpenAI response (parsed JSON)
            openai_debug_data['openai_response'] = suggestions_data
            
            # Capture token usage from last API call
            if openai_client.last_usage:
                openai_debug_data['token_usage'] = openai_client.last_usage
            
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
            logger.info(f"🔍 [CONSOLIDATION DEBUG] Processing {len(parsed)} suggestions from OpenAI")
            for i, suggestion in enumerate(parsed):
                # Map devices_involved to entity IDs using enriched_data (if available)
                validated_entities = {}
                devices_involved = suggestion.get('devices_involved', [])
                original_devices_count = len(devices_involved)
                logger.info(f"🔍 [CONSOLIDATION DEBUG] Suggestion {i+1}: devices_involved BEFORE processing = {devices_involved}")
                
                # PRE-CONSOLIDATION: Remove generic/redundant terms before entity mapping
                # This handles cases where OpenAI includes generic terms like "light", "wled", domain names, etc.
                if devices_involved:
                    devices_involved = _pre_consolidate_device_names(devices_involved, enriched_data)
                    if len(devices_involved) < original_devices_count:
                        logger.info(
                            f"🔄 Pre-consolidated devices for suggestion {i+1}: "
                            f"{original_devices_count} → {len(devices_involved)} "
                            f"(removed {original_devices_count - len(devices_involved)} generic/redundant terms)"
                        )
                        original_devices_count = len(devices_involved)  # Update for next consolidation
                    
                    # DEDUPLICATION: Remove exact duplicate device names (case-insensitive) while preserving order
                    seen = set()
                    seen_lower = set()  # Track lowercase versions for case-insensitive dedup
                    deduplicated = []
                    duplicates_removed = []
                    for device in devices_involved:
                        device_lower = device.lower().strip()
                        if device_lower not in seen_lower:
                            seen.add(device)
                            seen_lower.add(device_lower)
                            deduplicated.append(device)
                        else:
                            duplicates_removed.append(device)
                    
                    if len(deduplicated) < len(devices_involved):
                        logger.info(
                            f"🔄 Deduplicated devices for suggestion {i+1}: "
                            f"{len(devices_involved)} → {len(deduplicated)} "
                            f"(removed {len(duplicates_removed)} duplicates: {duplicates_removed})"
                        )
                    else:
                        logger.info(
                            f"✅ No duplicates found in suggestion {i+1} devices_involved: {devices_involved}"
                        )
                    devices_involved = deduplicated
                    original_devices_count = len(devices_involved)  # Update for next consolidation
                
                if enriched_data and devices_involved:
                    # Initialize HA client for verification if needed
                    ha_client_for_mapping = ha_client if 'ha_client' in locals() else (
                        HomeAssistantClient(
                            ha_url=settings.ha_url,
                            access_token=settings.ha_token
                        ) if settings.ha_url and settings.ha_token else None
                    )
                    validated_entities = await map_devices_to_entities(
                        devices_involved, 
                        enriched_data, 
                        ha_client=ha_client_for_mapping,
                        fuzzy_match=True
                    )
                    if validated_entities:
                        logger.info(f"✅ Mapped {len(validated_entities)}/{len(devices_involved)} devices to VERIFIED entities for suggestion {i+1}")
                        
                        # NEW: Validate location context for matched devices
                        location_mismatch_detected = False
                        query_location = None
                        try:
                            logger.info(f"🔍 [LOCATION VALIDATION] Starting location validation for suggestion {i+1}")
                            # Extract location from query
                            from ..services.entity_validator import EntityValidator
                            from ..clients.data_api_client import DataAPIClient
                            data_api_client = DataAPIClient()
                            entity_validator = EntityValidator(data_api_client, db_session=None, ha_client=ha_client_for_mapping)
                            query_location = entity_validator._extract_location_from_query(query)
                            logger.info(f"🔍 [LOCATION VALIDATION] Extracted query_location: '{query_location}' from query: '{query}'")
                            
                            # Check if any matched devices are in wrong location
                            if query_location:
                                logger.info(f"🔍 [LOCATION VALIDATION] Query has location '{query_location}', checking {len(validated_entities)} matched devices")
                                query_location_lower = query_location.lower()
                                mismatched_devices = []
                                
                                for device_name, entity_id in validated_entities.items():
                                    entity_data = enriched_data.get(entity_id, {})
                                    entity_area_raw = (
                                        entity_data.get('area_id') or 
                                        entity_data.get('device_area_id') or
                                        entity_data.get('area_name')
                                    )
                                    entity_area = entity_area_raw.lower() if entity_area_raw else ''
                                    
                                    logger.info(f"🔍 [LOCATION VALIDATION] Device '{device_name}' (entity_id: {entity_id}) has area: '{entity_area}' (query expects: '{query_location_lower}')")
                                    
                                    # Normalize area names for comparison
                                    import re
                                    normalized_query = re.sub(r'\b(room|area|space)\b', '', query_location_lower).strip()
                                    normalized_entity = re.sub(r'\b(room|area|space)\b', '', entity_area).strip()
                                    
                                    # Check if entity area matches query location
                                    area_matches = (
                                        query_location_lower in entity_area or
                                        entity_area in query_location_lower or
                                        normalized_query in normalized_entity or
                                        normalized_entity in normalized_query
                                    )
                                    
                                    logger.info(f"🔍 [LOCATION VALIDATION] Area match check: entity_area='{entity_area}', query_location='{query_location_lower}', normalized_query='{normalized_query}', normalized_entity='{normalized_entity}', matches={area_matches}")
                                    
                                    # If entity has an area but doesn't match, flag it
                                    if entity_area and not area_matches:
                                        logger.warning(f"🔍 [LOCATION VALIDATION] MISMATCH DETECTED: Device '{device_name}' is in '{entity_area}' but query expects '{query_location_lower}'")
                                        mismatched_devices.append({
                                            'device': device_name,
                                            'entity_id': entity_id,
                                            'entity_area': entity_area,
                                            'expected_location': query_location
                                        })
                                        location_mismatch_detected = True
                                
                                if location_mismatch_detected:
                                    logger.warning(
                                        f"⚠️ LOCATION MISMATCH detected in suggestion {i+1}: "
                                        f"Query mentions '{query_location}' but matched devices are in different locations: "
                                        f"{[m['entity_area'] for m in mismatched_devices]}"
                                    )
                                    # Lower confidence for location mismatches
                                    suggestion['confidence'] = max(0.3, suggestion.get('confidence', 0.9) * 0.5)
                                    logger.info(f"📉 Lowered confidence to {suggestion['confidence']:.2f} due to location mismatch")
                            else:
                                logger.info(f"🔍 [LOCATION VALIDATION] No location extracted from query, skipping validation")
                        except Exception as e:
                            logger.error(f"❌ Error validating location context: {e}", exc_info=True)
                        
                        # Consolidate devices_involved to remove redundant entries (single-home optimization)
                        devices_involved = consolidate_devices_involved(devices_involved, validated_entities)
                        if len(devices_involved) < original_devices_count:
                            logger.info(
                                f"🔄 Optimized devices_involved for suggestion {i+1}: "
                                f"{original_devices_count} → {len(devices_involved)} entries "
                                f"({original_devices_count - len(devices_involved)} redundant entries removed)"
                            )
                    else:
                        logger.warning(f"⚠️ No verified entities found for suggestion {i+1} (devices: {devices_involved})")
                
                # Create base suggestion
                # FINAL CHECK: Ensure no duplicates in devices_involved before storing
                devices_set = set()
                devices_lower_set = set()
                final_devices = []
                for device in devices_involved:
                    device_lower = device.lower().strip()
                    if device_lower not in devices_lower_set:
                        devices_set.add(device)
                        devices_lower_set.add(device_lower)
                        final_devices.append(device)
                
                if len(final_devices) < len(devices_involved):
                    removed = [d for d in devices_involved if d.lower().strip() not in devices_lower_set]
                    logger.warning(
                        f"⚠️ FINAL DEDUP: Removed {len(devices_involved) - len(final_devices)} duplicates "
                        f"from suggestion {i+1} before storing: {removed}"
                    )
                    devices_involved = final_devices
                
                logger.info(
                    f"📦 Suggestion {i+1} FINAL devices_involved to be stored: {devices_involved} "
                    f"(count: {len(devices_involved)}, unique: {len(set(d.lower() for d in devices_involved))})"
                )
                
                base_suggestion = {
                    'suggestion_id': f'ask-ai-{uuid.uuid4().hex[:8]}',
                    'description': suggestion['description'],
                    'trigger_summary': suggestion['trigger_summary'],
                    'action_summary': suggestion['action_summary'],
                    'devices_involved': devices_involved,  # Consolidated (deduplicated) - FINAL
                    'validated_entities': validated_entities,  # Save mapping for fast test execution
                    'enriched_entity_context': entity_context_json,  # Cache enrichment data to avoid re-enrichment
                    'capabilities_used': suggestion.get('capabilities_used', []),
                    'confidence': suggestion['confidence'],
                    'status': 'draft',
                    'created_at': datetime.now().isoformat()
                }
                
                # Build device selection debug data
                device_debug = []
                if devices_involved and validated_entities and enriched_data:
                    device_debug = await build_device_selection_debug_data(
                        devices_involved,
                        validated_entities,
                        enriched_data
                    )
                
                # Generate technical prompt for this suggestion
                technical_prompt = None
                if validated_entities and enriched_data:
                    try:
                        technical_prompt = await generate_technical_prompt(
                            suggestion,
                            validated_entities,
                            enriched_data,
                            query
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to generate technical prompt for suggestion {i+1}: {e}")
                
                # Build filtered entity context JSON for this suggestion (only entities actually used)
                filtered_entity_context_json = None
                filtered_user_prompt = None
                entity_context_stats = {
                    'total_entities_available': len(enriched_data) if enriched_data else 0,
                    'entities_used_in_suggestion': len(validated_entities) if validated_entities else 0,
                    'filtered_entity_context_json': None
                }
                
                if validated_entities and enriched_data:
                    try:
                        # Filter enriched_data to only validated entities
                        filtered_enriched_data = {
                            entity_id: enriched_data[entity_id]
                            for entity_id in validated_entities.values()
                            if entity_id in enriched_data
                        }
                        
                        # Rebuild entity context JSON with filtered entities
                        filtered_enriched_entities = []
                        for entity_id in validated_entities.values():
                            if entity_id in enriched_data:
                                enriched = enriched_data[entity_id]
                                filtered_enriched_entities.append({
                                    'entity_id': entity_id,
                                    'friendly_name': enriched.get('friendly_name', entity_id),
                                    'name': enriched.get('friendly_name', entity_id.split('.')[-1] if '.' in entity_id else entity_id)
                                })
                        
                        if filtered_enriched_entities:
                            context_builder = EntityContextBuilder()
                            filtered_entity_context_json = await context_builder.build_entity_context_json(
                                entities=filtered_enriched_entities,
                                enriched_data=filtered_enriched_data
                            )
                            
                            # Build filtered user prompt (replace entity context JSON with filtered version)
                            original_user_prompt = openai_debug_data.get('user_prompt', '')
                            if filtered_entity_context_json:
                                # Try to find and replace the entity context JSON section
                                # The entity context JSON appears in the "ENRICHED ENTITY CONTEXT" section
                                import json
                                import re
                                
                                # Try to extract the JSON from the original prompt
                                # Look for "ENRICHED ENTITY CONTEXT" section
                                pattern = r'(ENRICHED ENTITY CONTEXT.*?:\n)(\{[\s\S]*?\n\})'
                                match = re.search(pattern, original_user_prompt, re.MULTILINE)
                                
                                if match:
                                    # Replace the JSON portion with filtered version
                                    filtered_user_prompt = original_user_prompt[:match.start(2)] + filtered_entity_context_json + original_user_prompt[match.end(2):]
                                else:
                                    # Fallback: Try simple replacement
                                    # Find JSON object in the prompt (look for {...} pattern)
                                    json_pattern = r'(\{[\s\S]*?"entities"[\s\S]*?\})'
                                    json_match = re.search(json_pattern, original_user_prompt)
                                    if json_match:
                                        filtered_user_prompt = original_user_prompt[:json_match.start(1)] + filtered_entity_context_json + original_user_prompt[json_match.end(1):]
                                    else:
                                        # Last fallback: Just append filtered context
                                        filtered_user_prompt = original_user_prompt + f"\n\n[FILTERED ENTITY CONTEXT - Only entities used in suggestion]:\n{filtered_entity_context_json}"
                                
                                # Add note about filtering
                                note = f"\n\n[NOTE: Entity context filtered to show only {len(validated_entities)} entities used in this suggestion out of {len(enriched_data)} available]"
                                filtered_user_prompt = filtered_user_prompt + note
                                
                                logger.debug(f"✅ Built filtered user prompt for suggestion {i+1}")
                            
                            entity_context_stats['filtered_entity_context_json'] = filtered_entity_context_json
                            logger.info(f"✅ Built filtered entity context for suggestion {i+1}: {len(validated_entities)}/{len(enriched_data)} entities")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to build filtered entity context for suggestion {i+1}: {e}")
                
                # Add debug data and technical prompt to suggestion
                base_suggestion['debug'] = {
                    'device_selection': device_debug,
                    'system_prompt': openai_debug_data.get('system_prompt', ''),
                    'user_prompt': openai_debug_data.get('user_prompt', ''),  # Original full prompt
                    'filtered_user_prompt': filtered_user_prompt,  # NEW: Filtered prompt (only entities used)
                    'openai_response': openai_debug_data.get('openai_response'),
                    'token_usage': openai_debug_data.get('token_usage'),
                    'entity_context_stats': entity_context_stats,  # NEW: Context statistics
                    'clarification_context': openai_debug_data.get('clarification_context')  # NEW: Clarification Q&A
                }
                base_suggestion['technical_prompt'] = technical_prompt
                
                # Enhance suggestion with entity IDs (Phase 1 & 2)
                try:
                    enhanced_suggestion = await enhance_suggestion_with_entity_ids(
                        base_suggestion,
                        validated_entities,
                        enriched_data if enriched_data else None,
                        ha_client if 'ha_client' in locals() else None
                    )
                    # Ensure debug data and technical prompt are preserved
                    enhanced_suggestion['debug'] = base_suggestion.get('debug', {})
                    enhanced_suggestion['technical_prompt'] = base_suggestion.get('technical_prompt')
                    suggestions.append(enhanced_suggestion)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to enhance suggestion {i+1} with entity IDs: {e}, using base suggestion")
                    suggestions.append(base_suggestion)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse OpenAI response: {e}")
            # Fallback if JSON parsing fails
            suggestions = [{
                'suggestion_id': f'ask-ai-{uuid.uuid4().hex[:8]}',
                'description': f"Automation suggestion for: {query}",
                'trigger_summary': "Based on your query",
                'action_summary': "Device control",
                'devices_involved': [entity['name'] for entity in entities[:3]],
                'validated_entities': {},  # Empty mapping for fallback (backwards compatible)
                'enriched_entity_context': entity_context_json,  # Use any available context
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
        
        # Step 1.5: Check for clarification needs (NEW)
        clarification_detector, question_generator, _, confidence_calculator = get_clarification_services()
        
        # Build automation context for clarification detection
        automation_context = {}
        try:
            from ..clients.data_api_client import DataAPIClient
            import pandas as pd
            data_api_client = DataAPIClient()
            devices_result = await data_api_client.fetch_devices(limit=100)
            entities_result = await data_api_client.fetch_entities(limit=200)
            
            # Handle both DataFrame and list responses
            devices_df = devices_result if isinstance(devices_result, pd.DataFrame) else pd.DataFrame(devices_result if isinstance(devices_result, list) else [])
            entities_df = entities_result if isinstance(entities_result, pd.DataFrame) else pd.DataFrame(entities_result if isinstance(entities_result, list) else [])
            
            # Convert to dict format for clarification
            automation_context = {
                'devices': devices_df.to_dict('records') if isinstance(devices_df, pd.DataFrame) and not devices_df.empty else (devices_result if isinstance(devices_result, list) else []),
                'entities': entities_df.to_dict('records') if isinstance(entities_df, pd.DataFrame) and not entities_df.empty else (entities_result if isinstance(entities_result, list) else []),
                'entities_by_domain': {}
            }
            
            # Organize entities by domain
            if isinstance(entities_df, pd.DataFrame) and not entities_df.empty:
                for _, entity in entities_df.iterrows():
                    entity_id = entity.get('entity_id', '')
                    if entity_id:
                        domain = entity_id.split('.')[0]
                        if domain not in automation_context['entities_by_domain']:
                            automation_context['entities_by_domain'][domain] = []
                        automation_context['entities_by_domain'][domain].append({
                            'entity_id': entity_id,
                            'friendly_name': entity.get('friendly_name', entity_id),
                            'area': entity.get('area_id', 'unknown')
                        })
            elif isinstance(entities_result, list):
                # Handle list response
                for entity in entities_result:
                    if isinstance(entity, dict):
                        entity_id = entity.get('entity_id', '')
                        if entity_id:
                            domain = entity_id.split('.')[0]
                            if domain not in automation_context['entities_by_domain']:
                                automation_context['entities_by_domain'][domain] = []
                            automation_context['entities_by_domain'][domain].append({
                                'entity_id': entity_id,
                                'friendly_name': entity.get('friendly_name', entity_id),
                                'area': entity.get('area_id', 'unknown')
                            })
        except Exception as e:
            logger.error(f"❌ Failed to build automation context for clarification: {e}", exc_info=True)
            automation_context = {}
        
        # Detect ambiguities
        ambiguities = []
        questions = []
        clarification_session_id = None
        
        if clarification_detector:
            try:
                ambiguities = await clarification_detector.detect_ambiguities(
                    query=request.query,
                    extracted_entities=entities,
                    available_devices=automation_context,
                    automation_context=automation_context
                )
                
                # Calculate base confidence
                base_confidence = min(0.9, 0.5 + (len(entities) * 0.1))
                confidence = confidence_calculator.calculate_confidence(
                    query=request.query,
                    extracted_entities=entities,
                    ambiguities=ambiguities,
                    base_confidence=base_confidence
                )
                
                # Check if clarification is needed
                if confidence_calculator.should_ask_clarification(confidence, ambiguities):
                    # Generate questions
                    if question_generator:
                        questions = await question_generator.generate_questions(
                            ambiguities=ambiguities,
                            query=request.query,
                            context=automation_context
                        )
                    
                    # Create clarification session
                    if questions:
                        clarification_session_id = f"clarify-{uuid.uuid4().hex[:8]}"
                        session = ClarificationSession(
                            session_id=clarification_session_id,
                            original_query=request.query,
                            questions=questions,
                            current_confidence=confidence,
                            ambiguities=ambiguities,
                            query_id=query_id
                        )
                        _clarification_sessions[clarification_session_id] = session
                        
                        logger.info(f"🔍 Clarification needed: {len(questions)} questions generated")
                        for i, q in enumerate(questions, 1):
                            logger.info(f"  Question {i}: {q.question_text if hasattr(q, 'question_text') else str(q)}")
                    else:
                        logger.warning(f"⚠️ Clarification needed but no questions generated! Ambiguities: {len(ambiguities)}")
            except Exception as e:
                logger.error(f"Failed to detect ambiguities: {e}", exc_info=True)
                # Continue with normal flow if clarification fails
                confidence = min(0.9, 0.5 + (len(entities) * 0.1))
        else:
            # Fallback confidence calculation
            confidence = min(0.9, 0.5 + (len(entities) * 0.1))
        
        # Step 2: Generate suggestions if no clarification needed
        suggestions = []
        if not questions:  # Only generate suggestions if clarification not needed
            suggestions = await generate_suggestions_from_query(
                request.query, 
                entities, 
                request.user_id
            )
            
            # Recalculate confidence with suggestions
            if suggestions:
                confidence = min(0.9, confidence + (len(suggestions) * 0.1))
                
                # NEW: Check for location mismatches in generated suggestions
                # If any suggestion has low confidence due to location mismatch, trigger clarification
                location_mismatch_found = False
                query_location = None
                for suggestion in suggestions:
                    # Check if confidence was lowered due to location mismatch
                    # We lowered it to max(0.3, original * 0.5), so if it's <= 0.5, likely a mismatch
                    if suggestion.get('confidence', 1.0) <= 0.5:
                        # Check if this is a location mismatch by examining validated_entities
                        validated_entities = suggestion.get('validated_entities', {})
                        if validated_entities and clarification_detector:
                            try:
                                # Extract location from query
                                from ..services.entity_validator import EntityValidator
                                from ..clients.data_api_client import DataAPIClient
                                data_api_client = DataAPIClient()
                                ha_client_check = ha_client if 'ha_client' in locals() else get_ha_client()
                                entity_validator = EntityValidator(data_api_client, db_session=None, ha_client=ha_client_check)
                                query_location = entity_validator._extract_location_from_query(request.query)
                                
                                if query_location:
                                    # Check if any matched entities are in wrong location
                                    location_mismatch_found = True
                                    logger.warning(
                                        f"⚠️ Location mismatch detected in suggestions - triggering clarification. "
                                        f"Query location: '{query_location}'"
                                    )
                                    break
                            except Exception as e:
                                logger.warning(f"⚠️ Error checking for location mismatch: {e}", exc_info=True)
                
                # If location mismatch found, generate clarification questions
                if location_mismatch_found and not questions and clarification_detector and question_generator and query_location:
                    try:
                        # Create a location mismatch ambiguity
                        from ..services.clarification.models import Ambiguity, AmbiguityType, AmbiguitySeverity
                        location_ambiguity = Ambiguity(
                            id="amb-location-mismatch",
                            type=AmbiguityType.DEVICE,
                            severity=AmbiguitySeverity.CRITICAL,
                            description=f"Device location mismatch: Query mentions '{query_location}' but matched devices are in different areas",
                            context={
                                'query_location': query_location,
                                'suggestions_with_mismatch': len([s for s in suggestions if s.get('confidence', 1.0) <= 0.5])
                            },
                            detected_text="location mismatch"
                        )
                        
                        # Generate questions for location mismatch
                        location_questions = await question_generator.generate_questions(
                            ambiguities=[location_ambiguity],
                            query=request.query,
                            context=automation_context
                        )
                        
                        if location_questions:
                            questions.extend(location_questions)
                            # Create clarification session
                            clarification_session_id = f"clarify-{uuid.uuid4().hex[:8]}"
                            session = ClarificationSession(
                                session_id=clarification_session_id,
                                original_query=request.query,
                                questions=questions,
                                current_confidence=confidence,
                                ambiguities=[location_ambiguity],
                                query_id=query_id
                            )
                            _clarification_sessions[clarification_session_id] = session
                            logger.info(f"🔍 Generated {len(location_questions)} clarification questions for location mismatch")
                    except Exception as e:
                        logger.warning(f"⚠️ Error generating location mismatch clarification: {e}", exc_info=True)
        
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
        
        # Convert questions to dict format for response
        questions_dict = None
        if questions:
            questions_dict = [
                {
                    'id': q.id,
                    'category': q.category,
                    'question_text': q.question_text,
                    'question_type': q.question_type.value,
                    'options': q.options,
                    'priority': q.priority,
                    'related_entities': q.related_entities
                }
                for q in questions
            ]
        
        message = None
        if questions:
            # Build a detailed message explaining what was found and what's ambiguous
            device_names = [e.get('name', e.get('friendly_name', '')) for e in entities if e.get('type') == 'device']
            area_names = [e.get('name', '') for e in entities if e.get('type') == 'area']
            
            device_info = f" I detected these devices: {', '.join(device_names) if device_names else 'none'}." if device_names else ""
            area_info = f" I detected these locations: {', '.join(area_names)}." if area_names else ""
            
            message = f"I found some ambiguities in your request.{device_info}{area_info} Please answer {len(questions)} question(s) to help me create the automation accurately."
        elif suggestions:
            device_names = [e.get('name', e.get('friendly_name', '')) for e in entities if e.get('type') == 'device']
            device_info = f" I detected these devices: {', '.join(device_names)}." if device_names else ""
            message = f"I found {len(suggestions)} automation suggestion(s) for your request.{device_info}"
        else:
            # No suggestions and no questions - explain why
            device_names = [e.get('name', e.get('friendly_name', '')) for e in entities if e.get('type') == 'device']
            area_names = [e.get('name', '') for e in entities if e.get('type') == 'area']
            
            device_info = f" I detected these devices: {', '.join(device_names)}." if device_names else " I couldn't identify specific devices."
            area_info = f" I detected these locations: {', '.join(area_names)}." if area_names else ""
            
            message = f"I couldn't generate automation suggestions for your request.{device_info}{area_info} Please provide more details about the devices and locations you want to use."
        
        response = AskAIQueryResponse(
            query_id=query_id,
            original_query=request.query,
            parsed_intent=parsed_intent,
            extracted_entities=entities,
            suggestions=suggestions,
            confidence=confidence,
            processing_time_ms=int(processing_time),
            created_at=datetime.now().isoformat(),
            clarification_needed=bool(questions),
            clarification_session_id=clarification_session_id,
            questions=questions_dict,
            message=message
        )
        
        # Log response details for debugging
        logger.info(f"✅ Ask AI query processed and saved: {len(suggestions)} suggestions, {confidence:.2f} confidence")
        logger.info(f"📋 Response details: clarification_needed={bool(questions)}, questions_count={len(questions) if questions else 0}, message='{message}'")
        if questions_dict:
            logger.info(f"📋 Questions being returned: {[q.get('question_text', 'NO TEXT') for q in questions_dict]}")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Failed to process Ask AI query: {e}", exc_info=True)
        logger.error(f"❌ Error type: {type(e).__name__}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )


def _rebuild_user_query_from_qa(
    original_query: str,
    clarification_context: Dict[str, Any]
) -> str:
    """
    Rebuild enriched user query from original question + Q&A answers.
    
    This creates a comprehensive prompt that includes:
    - Original user question
    - All clarification questions and answers
    - Selected entities from Q&A answers
    - Device details from selected entities
    
    Args:
        original_query: Original user question
        clarification_context: Dictionary with questions_and_answers
        
    Returns:
        Enriched query string with all Q&A information
    """
    # Start with original query
    enriched_parts = [f"Original request: {original_query}"]
    
    # Add all Q&A pairs
    qa_list = clarification_context.get('questions_and_answers', [])
    if qa_list:
        enriched_parts.append("\nUser clarifications:")
        for i, qa in enumerate(qa_list, 1):
            qa_text = f"{i}. Question: {qa['question']}"
            qa_text += f"\n   Answer: {qa['answer']}"
            
            # Add selected entities if available
            if qa.get('selected_entities'):
                entities_str = ', '.join(qa['selected_entities'])
                qa_text += f"\n   Selected devices/entities: {entities_str}"
            
            enriched_parts.append(qa_text)
    
    # Build final enriched query
    enriched_query = "\n".join(enriched_parts)
    
    logger.info(f"📝 Rebuilt enriched query from {len(qa_list)} Q&A pairs")
    logger.debug(f"Enriched query preview: {enriched_query[:200]}...")
    
    return enriched_query


async def _re_enrich_entities_from_qa(
    entities: List[Dict[str, Any]],
    clarification_context: Dict[str, Any],
    ha_client: Optional[HomeAssistantClient] = None
) -> List[Dict[str, Any]]:
    """
    Re-enrich entities based on selected entities from Q&A answers.
    
    This function:
    - Extracts selected entities from Q&A answers
    - Detects "all X lights in Y area" patterns and expands to find ALL matching entities
    - Adds them to the entities list if not already present
    - Enriches entities with device information from selected entities
    - Updates entity data with Q&A context
    
    Args:
        entities: List of extracted entities
        clarification_context: Dictionary with questions_and_answers
        ha_client: Optional Home Assistant client for location-based expansion
        
    Returns:
        Re-enriched entities list with Q&A information
    """
    import re
    
    # Collect all selected entities from Q&A answers
    selected_entity_ids = set()
    selected_entity_names = []
    
    qa_list = clarification_context.get('questions_and_answers', [])
    for qa in qa_list:
        # Extract selected entities from answer
        selected = qa.get('selected_entities', [])
        if selected:
            for entity_ref in selected:
                # Entity ref could be entity_id or friendly_name
                if entity_ref.startswith('light.') or entity_ref.startswith('switch.') or '.' in entity_ref:
                    # Likely an entity_id
                    selected_entity_ids.add(entity_ref)
                else:
                    # Likely a friendly_name
                    selected_entity_names.append(entity_ref)
        
        # NEW: Check for "all X lights in Y area" patterns
        answer_text = qa.get('answer', '').lower()
        
        # Pattern: "all four lights in office", "all 4 lights in office", "all the lights in office"
        # Try patterns in order of specificity
        patterns_to_try = [
            # Pattern 1: "all 4 lights in office" or "all four lights in office"
            (r'all\s+(?:the\s+)?(\d+|four|five|six|seven|eight|nine|ten)\s*(lights?|lamps?|sensors?|switches?|devices?)\s+in\s+([\w\s]+)', 
             lambda m: (m.group(1) if m.group(1) and m.group(1).isdigit() else {'four': '4', 'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10'}.get(m.group(1).lower(), None), m.group(2), m.group(3))),
            # Pattern 2: "all lights in office" (no count)
            (r'all\s+(?:the\s+)?(lights?|lamps?|sensors?|switches?|devices?)\s+in\s+([\w\s]+)',
             lambda m: (None, m.group(1), m.group(2))),
        ]
        
        for pattern, extractor in patterns_to_try:
            match = re.search(pattern, answer_text)
            if match:
                try:
                    count_str, device_type, area = extractor(match)
                
                    if device_type and area:
                        count = int(count_str) if count_str else None
                        # Normalize area name
                        area = area.strip().replace(' ', '_')
                    
                        # Map device type to domain
                        domain_map = {
                            'light': 'light',
                            'lights': 'light',
                            'lamp': 'light',
                            'lamps': 'light',
                            'sensor': 'binary_sensor',
                            'sensors': 'binary_sensor',
                            'switch': 'switch',
                            'switches': 'switch',
                            'device': None,  # All domains
                            'devices': None  # All domains
                        }
                        domain = domain_map.get(device_type.lower(), 'light')
                        
                        logger.info(f"🔍 Detected pattern: 'all {count or 'all'} {device_type} in {area}' - expanding entities")
                        
                        # Expand to find ALL matching entities in the area
                        if ha_client:
                            try:
                                area_entities = await ha_client.get_entities_by_area_and_domain(
                                    area_id=area,
                                    domain=domain
                                )
                                
                                if area_entities:
                                    # Limit to count if specified
                                    if count:
                                        area_entities = area_entities[:count]
                                    
                                    # Add entity IDs to selected_entity_ids
                                    for area_entity in area_entities:
                                        entity_id = area_entity.get('entity_id')
                                        if entity_id:
                                            selected_entity_ids.add(entity_id)
                                            logger.info(f"✅ Added entity from Q&A expansion: {entity_id}")
                                    
                                    logger.info(f"✅ Expanded Q&A pattern to {len(area_entities)} entities in area '{area}'")
                                else:
                                    logger.warning(f"⚠️ No entities found in area '{area}' for domain '{domain}'")
                            except Exception as e:
                                logger.warning(f"⚠️ Error expanding entities for Q&A pattern 'all {device_type} in {area}': {e}")
                        break  # Found a match, stop trying other patterns
                except Exception as e:
                    logger.warning(f"⚠️ Error processing pattern match: {e}")
                    continue
        
        # Also extract entities mentioned in the answer text (original logic)
        # Look for entity patterns in answer (e.g., "office lights", "hue light 1")
        device_patterns = re.findall(r'\b([a-z]+(?:\s+[a-z]+){1,3})\s+(?:light|lights|sensor|sensors|switch|switches|device|devices)\b', answer_text)
        selected_entity_names.extend(device_patterns)
    
    # Create entity lookup from existing entities
    entity_by_id = {e.get('entity_id'): e for e in entities if e.get('entity_id')}
    entity_by_name = {e.get('name', '').lower(): e for e in entities if e.get('name')}
    entity_by_friendly_name = {e.get('friendly_name', '').lower(): e for e in entities if e.get('friendly_name')}
    
    # Add selected entities that aren't already in the list
    new_entities = []
    for entity_id in selected_entity_ids:
        if entity_id not in entity_by_id:
            # Create new entity entry
            new_entity = {
                'entity_id': entity_id,
                'name': entity_id.split('.')[-1] if '.' in entity_id else entity_id,
                'friendly_name': entity_id.split('.')[-1].replace('_', ' ').title() if '.' in entity_id else entity_id,
                'type': 'device',
                'domain': entity_id.split('.')[0] if '.' in entity_id else 'unknown',
                'source': 'qa_selected'
            }
            new_entities.append(new_entity)
            entity_by_id[entity_id] = new_entity
    
    # Add entities by name if not found
    for entity_name in selected_entity_names:
        entity_name_lower = entity_name.lower()
        if (entity_name_lower not in entity_by_name and 
            entity_name_lower not in entity_by_friendly_name):
            # Try to find by partial match
            found = False
            for existing_entity in entities:
                existing_name = existing_entity.get('name', '').lower()
                existing_friendly = existing_entity.get('friendly_name', '').lower()
                if (entity_name_lower in existing_name or 
                    entity_name_lower in existing_friendly or
                    existing_name in entity_name_lower):
                    found = True
                    break
            
            if not found:
                # Create new entity entry
                new_entity = {
                    'name': entity_name,
                    'friendly_name': entity_name,
                    'type': 'device',
                    'domain': 'unknown',
                    'source': 'qa_mentioned'
                }
                new_entities.append(new_entity)
    
    # Combine existing and new entities
    enriched_entities = list(entities) + new_entities
    
    # Add Q&A context to entities
    for entity in enriched_entities:
        if 'qa_context' not in entity:
            entity['qa_context'] = {}
        
        # Mark entities that were explicitly selected
        entity_id = entity.get('entity_id', '')
        entity_name = entity.get('name', '').lower()
        entity_friendly = entity.get('friendly_name', '').lower()
        
        for qa in qa_list:
            selected = qa.get('selected_entities', [])
            if selected:
                for selected_ref in selected:
                    selected_lower = selected_ref.lower()
                    if (entity_id and selected_lower == entity_id.lower()) or \
                       (entity_name and selected_lower in entity_name) or \
                       (entity_friendly and selected_lower in entity_friendly):
                        entity['qa_context']['explicitly_selected'] = True
                        entity['qa_context']['selected_in_qa'] = qa.get('question', '')
                        break
    
    logger.info(f"✅ Re-enriched {len(enriched_entities)} entities ({len(new_entities)} new from Q&A)")
    
    return enriched_entities


@router.post("/clarify", response_model=ClarificationResponse)
async def provide_clarification(
    request: ClarificationRequest,
    db: AsyncSession = Depends(get_db)
) -> ClarificationResponse:
    """
    Provide clarification answers to questions.
    
    Processes user answers and either:
    - Generates more questions if needed
    - Generates suggestions if confidence threshold is met
    """
    logger.info(f"🔍 Processing clarification for session {request.session_id}")
    
    try:
        # Get session
        session = _clarification_sessions.get(request.session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Clarification session {request.session_id} not found"
            )
        
        # Get clarification services
        _, _, answer_validator, confidence_calculator = get_clarification_services()
        
        # Validate answers
        validated_answers = []
        for answer_data in request.answers:
            question_id = answer_data.get('question_id')
            question = next((q for q in session.questions if q.id == question_id), None)
            
            if not question:
                logger.warning(f"Question {question_id} not found in session")
                continue
            
            # Create answer object
            answer = ClarificationAnswer(
                question_id=question_id,
                answer_text=answer_data.get('answer_text', ''),
                selected_entities=answer_data.get('selected_entities')
            )
            
            # Validate answer
            validated_answer = await answer_validator.validate_answer(
                answer=answer,
                question=question,
                available_entities=None  # TODO: Pass available entities
            )
            validated_answers.append(validated_answer)
        
        # Add answers to session
        session.answers.extend(validated_answers)
        session.rounds_completed += 1
        
        # NEW: Recalculate confidence with ALL answers (including previous rounds)
        # This ensures confidence properly reflects all clarification progress
        
        # Map answered questions to ambiguities to track which ambiguities are resolved
        answered_question_ids = {a.question_id for a in session.answers}
        resolved_ambiguity_ids = set()
        for question in session.questions:
            if question.id in answered_question_ids and question.ambiguity_id:
                resolved_ambiguity_ids.add(question.ambiguity_id)
        
        # Find remaining (unresolved) ambiguities for confidence calculation
        remaining_ambiguities_for_confidence = [
            amb for amb in session.ambiguities
            if amb.id not in resolved_ambiguity_ids
        ]
        
        all_answers = session.answers  # Includes all previous answers + new ones
        session.current_confidence = confidence_calculator.calculate_confidence(
            query=session.original_query,
            extracted_entities=[],  # TODO: Get from session
            ambiguities=remaining_ambiguities_for_confidence,  # Only count unresolved ambiguities
            clarification_answers=all_answers,  # Use ALL answers, not just new ones
            base_confidence=0.5  # Reset base confidence to recalculate from scratch
        )
        logger.info(f"📊 Confidence recalculated: {session.current_confidence:.2f} (threshold: {session.confidence_threshold:.2f}, answers: {len(all_answers)}, resolved ambiguities: {len(resolved_ambiguity_ids)}, remaining: {len(remaining_ambiguities_for_confidence)})")
        
        # Check if we should proceed or ask more questions
        if (session.current_confidence >= session.confidence_threshold or 
            session.rounds_completed >= session.max_rounds):
            # Generate suggestions
            session.status = "complete"
            
            # Build clarification context for prompt
            clarification_context = {
                'original_query': session.original_query,
                'questions_and_answers': [
                    {
                        'question': next((q.question_text for q in session.questions if q.id == answer.question_id), 'Unknown question'),
                        'answer': answer.answer_text,
                        'selected_entities': answer.selected_entities,
                        'category': next((q.category for q in session.questions if q.id == answer.question_id), 'unknown')
                    }
                    for answer in validated_answers
                ]
            }
            logger.info(f"📝 Built clarification context with {len(clarification_context['questions_and_answers'])} Q&A pairs for prompt")
            for i, qa in enumerate(clarification_context['questions_and_answers'], 1):
                logger.info(f"  Q&A {i}: Q: {qa['question']} | A: {qa['answer']} | Entities: {qa.get('selected_entities', [])}")
            
            # NEW: Rebuild enriched user query from original question + Q&A answers
            enriched_query = _rebuild_user_query_from_qa(
                original_query=session.original_query,
                clarification_context=clarification_context
            )
            logger.info(f"📝 Rebuilt enriched query: '{enriched_query}'")
            
            # NEW: Re-extract entities from enriched query (original + Q&A)
            entities = await extract_entities_with_ha(enriched_query)
            logger.info(f"🔍 Re-extracted {len(entities)} entities from enriched query")
            
            # NEW: Re-enrich devices based on selected entities from Q&A answers
            entities = await _re_enrich_entities_from_qa(
                entities=entities,
                clarification_context=clarification_context,
                ha_client=ha_client
            )
            logger.info(f"✅ Re-enriched entities with Q&A information: {len(entities)} entities")
            
            # Generate suggestions WITH enriched query and clarification context
            suggestions = await generate_suggestions_from_query(
                enriched_query,  # NEW: Use enriched query instead of original
                entities,  # NEW: Re-extracted and re-enriched entities
                "anonymous",  # TODO: Get from session
                clarification_context=clarification_context  # Pass structured clarification
            )
            
            # Add conversation history to suggestions
            for suggestion in suggestions:
                suggestion['conversation_history'] = {
                    'original_query': session.original_query,
                    'questions': [
                        {
                            'id': q.id,
                            'question_text': q.question_text,
                            'category': q.category
                        }
                        for q in session.questions
                    ],
                    'answers': [
                        {
                            'question_id': a.question_id,
                            'answer_text': a.answer_text,
                            'selected_entities': a.selected_entities
                        }
                        for a in validated_answers
                    ]
                }
            
            return ClarificationResponse(
                session_id=request.session_id,
                confidence=session.current_confidence,
                confidence_threshold=session.confidence_threshold,
                clarification_complete=True,
                message=f"Great! Based on your answers, I'll create the automation. Confidence: {int(session.current_confidence * 100)}%",
                suggestions=suggestions
            )
        else:
            # Need more clarification
            # NEW: Build enriched query from original + all previous answers
            all_qa_context = {
                'original_query': session.original_query,
                'questions_and_answers': [
                    {
                        'question': q.question_text,
                        'answer': next((a.answer_text for a in session.answers if a.question_id == q.id), ''),
                        'selected_entities': next((a.selected_entities for a in session.answers if a.question_id == q.id), []),
                        'category': q.category
                    }
                    for q in session.questions
                    if any(a.question_id == q.id for a in session.answers)
                ]
            }
            enriched_query = _rebuild_user_query_from_qa(
                original_query=session.original_query,
                clarification_context=all_qa_context
            )
            
            # NEW: Re-detect ambiguities based on enriched query (original + all previous answers)
            # This ensures we find new ambiguities that may have emerged from the answers
            clarification_detector, question_generator, _, _ = get_clarification_services()
            
            # Re-extract entities from enriched query
            entities = await extract_entities_with_ha(enriched_query)
            
            # Get automation context for re-detection
            automation_context = {}
            try:
                from ..clients.data_api_client import DataAPIClient
                import pandas as pd
                data_api_client = DataAPIClient()
                devices_result = await data_api_client.fetch_devices(limit=100)
                entities_result = await data_api_client.fetch_entities(limit=200)
                
                devices_df = devices_result if isinstance(devices_result, pd.DataFrame) else pd.DataFrame(devices_result if isinstance(devices_result, list) else [])
                entities_df = entities_result if isinstance(entities_result, pd.DataFrame) else pd.DataFrame(entities_result if isinstance(entities_result, list) else [])
                
                automation_context = {
                    'devices': devices_df.to_dict('records') if isinstance(devices_df, pd.DataFrame) and not devices_df.empty else (devices_result if isinstance(devices_result, list) else []),
                    'entities': entities_df.to_dict('records') if isinstance(entities_df, pd.DataFrame) and not entities_df.empty else (entities_result if isinstance(entities_result, list) else []),
                    'entities_by_domain': {}
                }
                
                # Organize entities by domain
                if isinstance(entities_df, pd.DataFrame) and not entities_df.empty:
                    for _, entity in entities_df.iterrows():
                        entity_id = entity.get('entity_id', '')
                        if entity_id:
                            domain = entity_id.split('.')[0]
                            if domain not in automation_context['entities_by_domain']:
                                automation_context['entities_by_domain'][domain] = []
                            automation_context['entities_by_domain'][domain].append({
                                'entity_id': entity_id,
                                'friendly_name': entity.get('friendly_name', entity_id),
                                'area': entity.get('area_id', 'unknown')
                            })
                elif isinstance(entities_result, list):
                    for entity in entities_result:
                        if isinstance(entity, dict):
                            entity_id = entity.get('entity_id', '')
                            if entity_id:
                                domain = entity_id.split('.')[0]
                                if domain not in automation_context['entities_by_domain']:
                                    automation_context['entities_by_domain'][domain] = []
                                automation_context['entities_by_domain'][domain].append({
                                    'entity_id': entity_id,
                                    'friendly_name': entity.get('friendly_name', entity_id),
                                    'area': entity.get('area_id', 'unknown')
                                })
            except Exception as e:
                logger.warning(f"Failed to build automation context for re-detection: {e}")
            
            # NEW: Re-detect ambiguities from enriched query (this finds new ambiguities based on answers)
            new_ambiguities = []
            if clarification_detector:
                try:
                    new_ambiguities = await clarification_detector.detect_ambiguities(
                        query=enriched_query,
                        extracted_entities=entities,
                        available_devices=automation_context,
                        automation_context=automation_context
                    )
                    logger.info(f"🔍 Re-detected {len(new_ambiguities)} ambiguities from enriched query")
                except Exception as e:
                    logger.warning(f"Failed to re-detect ambiguities: {e}")
            
            # NEW: Find remaining ambiguities by excluding those that have been answered
            # Track which ambiguities have been answered by checking question-ambiguity mappings
            answered_question_ids = {a.question_id for a in session.answers}
            answered_ambiguity_ids = set()
            
            # Map answered questions to their ambiguity IDs
            for question in session.questions:
                if question.id in answered_question_ids and question.ambiguity_id:
                    answered_ambiguity_ids.add(question.ambiguity_id)
            
            # Also check if ambiguity was resolved by answers (e.g., device selection resolved device ambiguity)
            for answer in session.answers:
                question = next((q for q in session.questions if q.id == answer.question_id), None)
                if question and question.category == 'device' and answer.selected_entities:
                    # If user selected specific devices, mark device ambiguities as resolved
                    for amb in session.ambiguities:
                        if amb.type.value == 'device' and amb.id not in answered_ambiguity_ids:
                            # Check if this ambiguity is about the same devices
                            amb_entities = amb.context.get('matches', [])
                            if amb_entities:
                                amb_entity_ids = [e.get('entity_id') for e in amb_entities if isinstance(e, dict)]
                                if any(eid in answer.selected_entities for eid in amb_entity_ids):
                                    answered_ambiguity_ids.add(amb.id)
                                    logger.info(f"✅ Marked ambiguity {amb.id} as resolved by device selection")
            
            # Combine original and new ambiguities, excluding answered ones
            all_ambiguities = session.ambiguities + new_ambiguities
            remaining_ambiguities = [
                amb for amb in all_ambiguities
                if amb.id not in answered_ambiguity_ids
            ]
            
            # Remove duplicates by ambiguity ID
            seen_ambiguity_ids = set()
            unique_remaining = []
            for amb in remaining_ambiguities:
                if amb.id not in seen_ambiguity_ids:
                    seen_ambiguity_ids.add(amb.id)
                    unique_remaining.append(amb)
            remaining_ambiguities = unique_remaining
            
            logger.info(f"📋 Remaining ambiguities: {len(remaining_ambiguities)} (answered: {len(answered_ambiguity_ids)}, total: {len(all_ambiguities)})")
            
            # NEW: Track which questions have already been asked to prevent duplicates
            asked_question_texts = {q.question_text.lower().strip() for q in session.questions}
            
            # Generate new questions if needed
            new_questions = []
            if remaining_ambiguities and question_generator:
                # Generate questions with previous Q&A context
                new_questions = await question_generator.generate_questions(
                    ambiguities=remaining_ambiguities[:2],  # Limit to 2 more questions
                    query=enriched_query,  # Use enriched query instead of original
                    context=automation_context,
                    previous_qa=all_qa_context.get('questions_and_answers', []),  # NEW: Pass previous Q&A
                    asked_questions=session.questions  # NEW: Pass asked questions to prevent duplicates
                )
                
                # Filter out questions that are too similar to already-asked questions
                filtered_new_questions = []
                for new_q in new_questions:
                    new_q_text_lower = new_q.question_text.lower().strip()
                    # Check if this question is too similar to an already-asked question
                    is_duplicate = False
                    for asked_text in asked_question_texts:
                        # Simple similarity check: if 80% of words match, consider it duplicate
                        new_words = set(new_q_text_lower.split())
                        asked_words = set(asked_text.split())
                        if len(new_words) > 0 and len(asked_words) > 0:
                            similarity = len(new_words.intersection(asked_words)) / max(len(new_words), len(asked_words))
                            if similarity > 0.8:
                                is_duplicate = True
                                logger.info(f"🚫 Filtered duplicate question: '{new_q.question_text}' (similarity: {similarity:.2f})")
                                break
                    
                    if not is_duplicate:
                        filtered_new_questions.append(new_q)
                        asked_question_texts.add(new_q_text_lower)  # Track this question
                
                new_questions = filtered_new_questions
                
                # Update session with new ambiguities and questions
                session.ambiguities.extend(new_ambiguities)
                session.questions.extend(new_questions)
            
            questions_dict = None
            if new_questions:
                questions_dict = [
                    {
                        'id': q.id,
                        'category': q.category,
                        'question_text': q.question_text,
                        'question_type': q.question_type.value,
                        'options': q.options,
                        'priority': q.priority
                    }
                    for q in new_questions
                ]
            
            message = f"Thanks for your answers! " if validated_answers else ""
            message += f"Confidence is now {int(session.current_confidence * 100)}% (need {int(session.confidence_threshold * 100)}%)."
            if new_questions:
                message += f" I have {len(new_questions)} more question(s)."
            else:
                message += " Generating suggestions now..."
            
            return ClarificationResponse(
                session_id=request.session_id,
                confidence=session.current_confidence,
                confidence_threshold=session.confidence_threshold,
                clarification_complete=False,
                message=message,
                questions=questions_dict
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to process clarification: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process clarification: {str(e)}"
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


# ============================================================================
# Task 1.1: State Capture & Validation Functions
# ============================================================================

async def capture_entity_states(
    ha_client: HomeAssistantClient,
    entity_ids: List[str],
    timeout: float = 5.0
) -> Dict[str, Dict[str, Any]]:
    """
    Capture current state of entities before test execution.
    
    Task 1.1: State Capture & Validation
    
    Args:
        ha_client: Home Assistant client
        entity_ids: List of entity IDs to capture
        timeout: Maximum time to wait for state retrieval
        
    Returns:
        Dictionary mapping entity_id to state dictionary
    """
    states = {}
    
    for entity_id in entity_ids:
        try:
            state = await ha_client.get_entity_state(entity_id)
            if state:
                states[entity_id] = {
                    'state': state.get('state'),
                    'attributes': state.get('attributes', {}),
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.warning(f"Failed to capture state for {entity_id}: {e}")
            states[entity_id] = {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    logger.info(f"📸 Captured states for {len(states)} entities")
    return states


async def validate_state_changes(
    ha_client: HomeAssistantClient,
    before_states: Dict[str, Dict[str, Any]],
    entity_ids: List[str],
    wait_timeout: float = 5.0,
    check_interval: float = 0.5
) -> Dict[str, Any]:
    """
    Validate that state changes occurred after test execution.
    
    Task 1.1: State Capture & Validation
    
    Args:
        ha_client: Home Assistant client
        before_states: States captured before execution
        entity_ids: List of entity IDs to check
        wait_timeout: Maximum time to wait for changes (seconds)
        check_interval: Interval between checks (seconds)
        
    Returns:
        Validation report with before/after states and success flags
    """
    validation_results = {}
    start_time = time.time()
    
    # Wait and poll for state changes
    while (time.time() - start_time) < wait_timeout:
        for entity_id in entity_ids:
            if entity_id not in validation_results:
                try:
                    after_state = await ha_client.get_entity_state(entity_id)
                    before_state_data = before_states.get(entity_id, {})
                    before_state = before_state_data.get('state')
                    
                    if after_state:
                        after_state_value = after_state.get('state')
                        
                        # Check if state changed
                        if before_state != after_state_value:
                            validation_results[entity_id] = {
                                'success': True,
                                'before_state': before_state,
                                'after_state': after_state_value,
                                'changed': True,
                                'timestamp': datetime.now().isoformat()
                            }
                            logger.info(f"✅ State change detected for {entity_id}: {before_state} → {after_state_value}")
                        # Also check attribute changes for entities that might not change state
                        elif before_state == after_state_value:
                            # Check common attributes that might change (brightness, color, etc.)
                            before_attrs = before_state_data.get('attributes', {})
                            after_attrs = after_state.get('attributes', {})
                            
                            # Check for meaningful attribute changes
                            changed_attrs = {}
                            for key in ['brightness', 'color_name', 'rgb_color', 'temperature']:
                                if before_attrs.get(key) != after_attrs.get(key):
                                    changed_attrs[key] = {
                                        'before': before_attrs.get(key),
                                        'after': after_attrs.get(key)
                                    }
                            
                            if changed_attrs:
                                validation_results[entity_id] = {
                                    'success': True,
                                    'before_state': before_state,
                                    'after_state': after_state_value,
                                    'changed': True,
                                    'attribute_changes': changed_attrs,
                                    'timestamp': datetime.now().isoformat()
                                }
                                logger.info(f"✅ Attribute changes detected for {entity_id}: {changed_attrs}")
                            # If no changes detected yet, mark as pending
                            elif entity_id not in validation_results:
                                validation_results[entity_id] = {
                                    'success': False,
                                    'before_state': before_state,
                                    'after_state': after_state_value,
                                    'changed': False,
                                    'pending': True,
                                    'timestamp': datetime.now().isoformat()
                                }
                
                except Exception as e:
                    logger.warning(f"Error validating state for {entity_id}: {e}")
                    if entity_id not in validation_results:
                        validation_results[entity_id] = {
                            'success': False,
                            'error': str(e),
                            'timestamp': datetime.now().isoformat()
                        }
        
        # Check if all entities have been validated with changes
        all_validated = all(
            entity_id in validation_results and validation_results[entity_id].get('changed', False)
            for entity_id in entity_ids
        )
        
        if all_validated:
            break
        
        # Wait before next check
        await asyncio.sleep(check_interval)
    
    # Final validation - mark pending entities as no change
    for entity_id in entity_ids:
        if entity_id not in validation_results:
            before_state_data = before_states.get(entity_id, {})
            validation_results[entity_id] = {
                'success': False,
                'before_state': before_state_data.get('state'),
                'after_state': None,
                'changed': False,
                'note': 'No state change detected within timeout',
                'timestamp': datetime.now().isoformat()
            }
    
    success_count = sum(1 for r in validation_results.values() if r.get('success', False))
    total_count = len(validation_results)
    
    logger.info(f"✅ State validation complete: {success_count}/{total_count} entities changed")
    
    return {
        'entities': validation_results,
        'summary': {
            'total_checked': total_count,
            'changed': success_count,
            'unchanged': total_count - success_count,
            'validation_time_ms': round((time.time() - start_time) * 1000, 2)
        }
    }


# ============================================================================
# Task 1.3: OpenAI JSON Mode Test Result Analyzer
# ============================================================================

class TestResultAnalyzer:
    """
    Analyzes test execution results using OpenAI with JSON mode.
    
    Task 1.3: OpenAI JSON Mode for Test Result Analysis
    """
    
    def __init__(self, openai_client: OpenAIClient):
        """Initialize analyzer with OpenAI client"""
        self.client = openai_client
    
    async def analyze_test_execution(
        self,
        test_yaml: str,
        state_validation: Dict[str, Any],
        execution_logs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze test execution and return structured JSON results.
        
        Args:
            test_yaml: Test automation YAML
            state_validation: State validation results
            execution_logs: Optional execution logs
            
        Returns:
            Structured analysis with success, issues, and recommendations
        """
        if not self.client:
            logger.warning("OpenAI client not available, skipping analysis")
            return {
                'success': True,
                'issues': [],
                'recommendations': ['Test executed, but AI analysis unavailable'],
                'confidence': 0.7
            }
        
        # Build analysis prompt
        state_summary = state_validation.get('summary', {})
        changed_count = state_summary.get('changed', 0)
        total_count = state_summary.get('total_checked', 0)
        
        prompt = f"""Analyze this test automation execution and provide structured feedback.

TEST YAML:
{test_yaml[:500]}

STATE VALIDATION RESULTS:
- Entities checked: {total_count}
- Entities changed: {changed_count}
- Entities unchanged: {total_count - changed_count}
- Validation time: {state_summary.get('validation_time_ms', 0)}ms

ENTITY CHANGES:
{json.dumps(state_validation.get('entities', {}), indent=2)[:1000]}

EXECUTION LOGS:
{execution_logs or 'No logs available'}

TASK: Analyze the test execution and determine:
1. Did the automation execute successfully?
2. Were the expected state changes detected?
3. Are there any issues or warnings?
4. What recommendations do you have?

Response format: ONLY JSON, no other text:
{{
  "success": true/false,
  "issues": ["List of issues found"],
  "recommendations": ["List of recommendations"],
  "confidence": 0.0-1.0
}}"""

        try:
            response = await self.client.client.chat.completions.create(
                model=self.client.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a test automation analysis expert. Analyze execution results and provide structured feedback in JSON format only."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Low temperature for consistent analysis
                max_tokens=400,
                response_format={"type": "json_object"}  # Force JSON mode
            )
            
            content = response.choices[0].message.content.strip()
            analysis = json.loads(content)
            
            logger.info(f"✅ Test analysis complete: success={analysis.get('success', False)}")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze test execution: {e}")
            return {
                'success': True,  # Default to success if analysis fails
                'issues': [f'Analysis unavailable: {str(e)}'],
                'recommendations': [],
                'confidence': 0.5
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
        
        # Check if validated_entities already exists (fast path)
        if suggestion.get('validated_entities'):
            entity_mapping = suggestion['validated_entities']
            entity_resolution_time = 0  # No time spent on resolution
            logger.info(f"✅ Using saved validated_entities mapping ({len(entity_mapping)} entities) - FAST PATH")
        else:
            # Fall back to re-resolution (slow path, backwards compatibility)
            logger.info(f"⚠️ Re-resolving entities (validated_entities not saved) - SLOW PATH")
            # Use devices_involved from the suggestion (these are the actual device names to map)
            devices_involved = suggestion.get('devices_involved', [])
            logger.debug(f" devices_involved from suggestion: {devices_involved}")
            
            # Map devices to entity_ids using the same logic as in generate_automation_yaml
            logger.debug(f" Mapping devices to entity_ids...")
            from ..services.entity_validator import EntityValidator
            from ..clients.data_api_client import DataAPIClient
            data_api_client = DataAPIClient()
            ha_client = HomeAssistantClient(
                ha_url=settings.ha_url,
                access_token=settings.ha_token
            ) if settings.ha_url and settings.ha_token else None
            entity_validator = EntityValidator(data_api_client, db_session=db, ha_client=ha_client)
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
            
            # Deduplicate entities - if multiple device names map to same entity_id, keep only unique ones
            entity_mapping = deduplicate_entity_mapping(entity_mapping)
        
        # TASK 2.4: Check if suggestion has sequences for testing with shortened delays
        component_detector_preview = ComponentDetector()
        detected_components_preview = component_detector_preview.detect_stripped_components(
            "",
            suggestion.get('description', '')
        )
        
        # Check if we have sequences/repeats that can be tested with shortened delays
        has_sequences = any(
            comp.component_type in ['repeat', 'delay'] 
            for comp in detected_components_preview
        )
        
        # TASK 2.4: Modify suggestion for test - use sequence mode if applicable
        test_suggestion = suggestion.copy()
        if has_sequences:
            # Sequence testing mode: shorten delays instead of removing
            test_suggestion['description'] = f"TEST MODE WITH SEQUENCES: {suggestion.get('description', '')} - Execute with shortened delays (10x faster)"
            test_suggestion['trigger_summary'] = "Manual trigger (test mode)"
            test_suggestion['action_summary'] = suggestion.get('action_summary', '')
            test_suggestion['test_mode'] = 'sequence'  # Mark for sequence-aware YAML generation
        else:
            # Simple test mode: strip timing components
            test_suggestion['description'] = f"TEST MODE: {suggestion.get('description', '')} - Execute core action only"
            test_suggestion['trigger_summary'] = "Manual trigger (test mode)"
            test_suggestion['action_summary'] = suggestion.get('action_summary', '').split('every')[0].split('Every')[0].strip()
            test_suggestion['test_mode'] = 'simple'
        
        test_suggestion['validated_entities'] = entity_mapping
        logger.debug(f" Added validated_entities: {entity_mapping}")
        logger.debug(f" test_suggestion validated_entities key exists: {'validated_entities' in test_suggestion}")
        logger.debug(f" test_suggestion['validated_entities'] content: {test_suggestion.get('validated_entities')}")
        
        automation_yaml = await generate_automation_yaml(test_suggestion, query.original_query, entities, db_session=db, ha_client=ha_client)
        yaml_gen_time = (time.time() - yaml_gen_start) * 1000
        logger.debug(f"After generate_automation_yaml - validated_entities still exists: {'validated_entities' in test_suggestion}")
        logger.info(f"Generated test automation YAML")
        logger.debug(f"Generated YAML preview: {str(automation_yaml)[:500]}")
        
        # Reverse engineering self-correction: Validate and improve YAML to match user intent
        correction_result = None
        correction_service = get_self_correction_service()
        if correction_service:
            try:
                logger.info("🔄 Running reverse engineering self-correction (test mode)...")
                
                # Get comprehensive enriched data for entities used in YAML
                test_enriched_data = None
                if entity_mapping and ha_client:
                    try:
                        from ..services.comprehensive_entity_enrichment import enrich_entities_comprehensively
                        entity_ids_for_enrichment = set(entity_mapping.values())
                        test_enriched_data = await enrich_entities_comprehensively(
                            entity_ids=entity_ids_for_enrichment,
                            ha_client=ha_client,
                            device_intelligence_client=_device_intelligence_client,
                            data_api_client=None,
                            include_historical=False
                        )
                        logger.info(f"✅ Got comprehensive enrichment for {len(test_enriched_data)} entities for reverse engineering")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not get comprehensive enrichment for test: {e}")
                
                context = {
                    "entities": entities,
                    "suggestion": test_suggestion,
                    "devices_involved": test_suggestion.get('devices_involved', []),
                    "test_mode": True
                }
                correction_result = await correction_service.correct_yaml(
                    user_prompt=query.original_query,
                    generated_yaml=automation_yaml,
                    context=context,
                    comprehensive_enriched_data=test_enriched_data
                )
                
                # Store initial metrics for test mode (test automations are temporary, so automation_created stays None)
                try:
                    from ..services.reverse_engineering_metrics import store_reverse_engineering_metrics
                    await store_reverse_engineering_metrics(
                        db_session=db,
                        suggestion_id=suggestion_id,
                        query_id=query_id,
                        correction_result=correction_result,
                        automation_created=None,  # Test automations are temporary
                        automation_id=None,
                        had_validation_errors=False,
                        errors_fixed_count=0
                    )
                    logger.info("✅ Stored reverse engineering metrics for test")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to store test metrics: {e}")
                
                if correction_result.convergence_achieved or correction_result.final_similarity >= 0.80:
                    # Use corrected YAML if similarity improved significantly (lower threshold for test mode)
                    if correction_result.final_similarity > 0.80:
                        logger.info(f"✅ Using self-corrected test YAML (similarity: {correction_result.final_similarity:.2%})")
                        automation_yaml = correction_result.final_yaml
                    else:
                        logger.info(f"ℹ️  Self-correction completed (similarity: {correction_result.final_similarity:.2%}), keeping original test YAML")
                else:
                    logger.warning(f"⚠️  Self-correction did not converge (similarity: {correction_result.final_similarity:.2%}), using original test YAML")
            except Exception as e:
                logger.warning(f"⚠️  Self-correction failed in test mode, continuing with original YAML: {e}")
                correction_result = None
        else:
            logger.debug("Self-correction service not available for test, skipping reverse engineering")
        
        # TASK 1.2: Detect stripped components for restoration tracking
        component_detector = ComponentDetector()
        stripped_components = component_detector.detect_stripped_components(
            automation_yaml,
            suggestion.get('description', '')
        )
        logger.info(f"🔍 Detected {len(stripped_components)} stripped components")
        
        # Extract entity IDs from mapping for state capture
        entity_ids = list(entity_mapping.values()) if entity_mapping else []
        
        # TASK 1.1: Capture entity states BEFORE test execution
        logger.info(f"📸 Capturing entity states before test execution...")
        before_states = await capture_entity_states(ha_client, entity_ids)
        
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
            
            # TASK 1.1: Wait and validate state changes (reduced wait time since we're checking)
            logger.info("Waiting for state changes (max 5 seconds)...")
            state_validation = await validate_state_changes(
                ha_client,
                before_states,
                entity_ids,
                wait_timeout=5.0
            )
            
            # Additional wait only if needed for delayed actions (reduced from 30s)
            remaining_wait = max(0, 2.0 - state_validation['summary']['validation_time_ms'] / 1000)
            if remaining_wait > 0:
                await asyncio.sleep(remaining_wait)
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
            
            # TASK 1.3: Analyze test execution with OpenAI JSON mode
            logger.info("🔍 Analyzing test execution results...")
            analyzer = TestResultAnalyzer(openai_client)
            test_analysis = await analyzer.analyze_test_execution(
                test_yaml=automation_yaml,
                state_validation=state_validation,
                execution_logs=f"Automation {automation_id} triggered successfully"
            )
            
            # TASK 1.5: Format stripped components for preview
            stripped_components_preview = component_detector.format_components_for_preview(stripped_components)
            
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
            
            response_data = {
                "suggestion_id": suggestion_id,
                "query_id": query_id,
                "executed": True,
                "automation_yaml": automation_yaml,
                "automation_id": automation_id,
                "deleted": True,
                "message": "Test completed successfully - automation created, executed, and deleted",
                "quality_report": quality_report,
                "performance_metrics": performance_metrics,
                # TASK 1.1: State capture and validation results
                "state_validation": state_validation,
                # TASK 1.3: AI analysis results
                "test_analysis": test_analysis,
                # TASK 1.5: Stripped components preview
                "stripped_components": stripped_components_preview,
                "restoration_hint": "These components will be added back when you approve"
            }
            
            # Add reverse engineering correction results if available
            if correction_result:
                response_data["reverse_engineering"] = {
                    "enabled": True,
                    "final_similarity": correction_result.final_similarity,
                    "iterations_completed": correction_result.iterations_completed,
                    "convergence_achieved": correction_result.convergence_achieved,
                    "total_tokens_used": correction_result.total_tokens_used,
                    "yaml_improved": correction_result.final_similarity > 0.80,
                    "iteration_history": [
                        {
                            "iteration": iter_result.iteration,
                            "similarity_score": iter_result.similarity_score,
                            "reverse_engineered_prompt": iter_result.reverse_engineered_prompt[:200] + "..." if len(iter_result.reverse_engineered_prompt) > 200 else iter_result.reverse_engineered_prompt,
                            "improvement_actions": iter_result.improvement_actions[:3]  # Limit to first 3 actions
                        }
                        for iter_result in correction_result.iteration_history
                    ]
                }
            else:
                response_data["reverse_engineering"] = {
                    "enabled": False,
                    "reason": "Service not available or failed"
                }
            
            return response_data
            
        except Exception as e:
            logger.error(f"❌ ERROR in test execution: {e}")
            raise
    
    except HTTPException as e:
        logger.error(f"HTTPException in test endpoint: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Error testing suggestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Task 1.4: Component Restoration Function
# ============================================================================

async def restore_stripped_components(
    original_suggestion: Dict[str, Any],
    test_result: Optional[Dict[str, Any]],
    original_query: str,
    openai_client: OpenAIClient
) -> Dict[str, Any]:
    """
    Restore components that were stripped during testing.
    
    Task 1.4 + Task 2.5: Explicit Component Restoration with Enhanced Support
    
    Task 2.5 Enhancements:
    - Support nested components (delays within repeats)
    - Better context understanding from original query
    - Validate restored components match user intent
    
    Args:
        original_suggestion: Original suggestion dictionary
        test_result: Test result containing stripped_components (if available)
        original_query: Original user query for context
        openai_client: OpenAI client for intelligent restoration
        
    Returns:
        Updated suggestion with restoration log
    """
    # Extract stripped components from test result if available
    stripped_components = []
    if test_result and 'stripped_components' in test_result:
        stripped_components = test_result['stripped_components']
    
    # If no test result, try to detect components from original suggestion
    if not stripped_components:
        logger.info("No test result found, detecting components from original suggestion...")
        component_detector = ComponentDetector()
        detected = component_detector.detect_stripped_components(
            "",  # No YAML available
            original_suggestion.get('description', '')
        )
        stripped_components = component_detector.format_components_for_preview(detected)
    
    if not stripped_components:
        logger.info("No components to restore")
        # Preserve all original suggestion data including validated_entities
        return {
            'suggestion': original_suggestion.copy(),  # Make copy to preserve validated_entities
            'restored_components': [],
            'restoration_log': []
        }
    
    # Use OpenAI to intelligently restore components with context
    if not openai_client:
        logger.warning("OpenAI client not available, skipping intelligent restoration")
        # Preserve all original suggestion data including validated_entities
        return {
            'suggestion': original_suggestion.copy(),  # Make copy to preserve validated_entities
            'restored_components': stripped_components,
            'restoration_log': [f"Found {len(stripped_components)} components to restore (restoration skipped)"]
        }
    
    # TASK 2.5: Analyze component nesting (delays within repeats)
    nested_components = []
    simple_components = []
    
    for comp in stripped_components:
        comp_type = comp.get('type', '')
        original_value = comp.get('original_value', '')
        
        # Check if component appears to be nested (e.g., delay mentioned with repeat)
        if comp_type == 'delay' and any(
            'repeat' in str(other_comp.get('original_value', '')).lower() or other_comp.get('type') == 'repeat'
            for other_comp in stripped_components
        ):
            nested_components.append(comp)
        elif comp_type == 'repeat':
            # Repeats may contain delays - check original description for context
            if 'delay' in original_value.lower() or 'wait' in original_value.lower():
                nested_components.append(comp)
            else:
                simple_components.append(comp)
        else:
            simple_components.append(comp)
    
    # Build restoration prompt with enhanced context
    components_text = "\n".join([
        f"- {comp.get('type', 'unknown')}: {comp.get('original_value', 'N/A')} (confidence: {comp.get('confidence', 0.8):.2f})"
        for comp in stripped_components
    ])
    
    nesting_info = ""
    if nested_components:
        nesting_info = f"\n\nNESTED COMPONENTS DETECTED: {len(nested_components)} component(s) may be nested (e.g., delays within repeat blocks). Pay special attention to restore them in the correct order and context."
    
    prompt = f"""Restore these automation components that were stripped during testing.

ORIGINAL USER QUERY:
"{original_query}"

ORIGINAL SUGGESTION:
Description: {original_suggestion.get('description', '')}
Trigger: {original_suggestion.get('trigger_summary', '')}
Action: {original_suggestion.get('action_summary', '')}

STRIPPED COMPONENTS TO RESTORE:
{components_text}{nesting_info}

TASK 2.5 ENHANCED RESTORATION:
1. Analyze the original query context to understand user intent
2. Identify nested components (e.g., delays within repeat blocks)
3. Restore components in the correct structure and order
4. Validate that restored components match the original user intent
5. For nested components: ensure delays/repeats are properly structured (e.g., delay inside repeat.sequence)

The original suggestion should already contain these components naturally. Your job is to verify they are properly included and able to be restored with correct nesting.

Response format: ONLY JSON, no other text:
{{
  "restored": true/false,
  "restored_components": ["list of component types that were restored"],
  "restoration_details": ["detailed description of what was restored, including nesting information"],
  "nested_components_restored": ["list of nested components if any"],
  "restoration_structure": "description of component hierarchy (e.g., 'delay: 2s within repeat: 3 times')",
  "confidence": 0.0-1.0,
  "intent_match": true/false,
  "intent_validation": "explanation of how restored components match user intent"
}}"""

    try:
        response = await openai_client.client.chat.completions.create(
            model=openai_client.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an automation expert. Restore timing, delay, and repeat components that were removed for testing, ensuring they match the original user intent. Pay special attention to nested components (delays within repeats) and restore them with correct structure."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Low temperature for consistent restoration
            max_tokens=500,  # Increased for nested component descriptions
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content.strip()
        restoration_result = json.loads(content)
        
        logger.info(f"✅ Component restoration complete: {restoration_result.get('restored_components', [])}")
        
        # TASK 2.5: Enhanced return with nesting and intent validation
        # Preserve all original suggestion data including validated_entities
        restored_suggestion = original_suggestion.copy()
        return {
            'suggestion': restored_suggestion,  # Original already has components, we're just validating
            'restored_components': stripped_components,
            'restoration_log': restoration_result.get('restoration_details', []),
            'restoration_confidence': restoration_result.get('confidence', 0.9),
            'nested_components_restored': restoration_result.get('nested_components_restored', []),
            'restoration_structure': restoration_result.get('restoration_structure', ''),
            'intent_match': restoration_result.get('intent_match', True),
            'intent_validation': restoration_result.get('intent_validation', '')
        }
        
    except Exception as e:
        logger.error(f"Failed to restore components: {e}")
        # Preserve all original suggestion data including validated_entities
        return {
            'suggestion': original_suggestion.copy(),  # Make copy to preserve validated_entities
            'restored_components': stripped_components,
            'restoration_log': [f'Restoration attempted but failed: {str(e)}'],
            'restoration_confidence': 0.5
        }


class ApproveSuggestionRequest(BaseModel):
    """Request body for approving a suggestion with optional selected entity IDs and custom entity mappings."""
    selected_entity_ids: Optional[List[str]] = Field(default=None, description="List of entity IDs selected by user to include in automation")
    custom_entity_mapping: Optional[Dict[str, str]] = Field(
        default=None,
        description="Custom mapping of friendly_name → entity_id overrides. Allows users to change which entity_id maps to a device name."
    )

@router.post("/query/{query_id}/suggestions/{suggestion_id}/approve")
async def approve_suggestion_from_query(
    query_id: str,
    suggestion_id: str,
    request: Optional[ApproveSuggestionRequest] = Body(default=None),
    db: AsyncSession = Depends(get_db),
    ha_client: HomeAssistantClient = Depends(get_ha_client),
    openai_client: OpenAIClient = Depends(get_openai_client)
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
        
        # Fail fast if validated_entities is missing - should already be set during suggestion creation
        validated_entities = suggestion.get('validated_entities')
        if not validated_entities or not isinstance(validated_entities, dict) or len(validated_entities) == 0:
            logger.error(f"❌ Suggestion {suggestion_id} missing validated_entities - should be set during creation")
            raise HTTPException(
                status_code=400,
                detail=f"Suggestion {suggestion_id} is missing validated entities. This should be set during suggestion creation. Please regenerate the suggestion."
            )
        
        logger.info(f"✅ Using validated_entities from suggestion: {len(validated_entities)} entities")
        
        # Start with suggestion as-is (no component restoration - not implemented)
        final_suggestion = suggestion.copy()
        
        # Apply user filters if provided
        if request:
            # Filter by selected_entity_ids if provided
            if request.selected_entity_ids and len(request.selected_entity_ids) > 0:
                logger.info(f"🎯 Filtering validated_entities to selected devices: {request.selected_entity_ids}")
                final_suggestion['validated_entities'] = {
                    friendly_name: entity_id 
                    for friendly_name, entity_id in validated_entities.items()
                    if entity_id in request.selected_entity_ids
                }
                logger.info(f"✅ Filtered to {len(final_suggestion['validated_entities'])} selected entities")
            
            # Apply custom entity mappings if provided
            if request.custom_entity_mapping and len(request.custom_entity_mapping) > 0:
                logger.info(f"🔧 Applying custom entity mappings: {request.custom_entity_mapping}")
                # Verify custom entity IDs exist in Home Assistant
                custom_entity_ids = list(request.custom_entity_mapping.values())
                if ha_client:
                    verification_results = await verify_entities_exist_in_ha(custom_entity_ids, ha_client)
                    # Apply only verified mappings
                    for friendly_name, new_entity_id in request.custom_entity_mapping.items():
                        if verification_results.get(new_entity_id, False):
                            final_suggestion['validated_entities'][friendly_name] = new_entity_id
                            logger.info(f"✅ Applied custom mapping: '{friendly_name}' → {new_entity_id}")
                        else:
                            logger.warning(f"⚠️ Custom entity_id {new_entity_id} for '{friendly_name}' does not exist in HA - skipped")
                else:
                    # No HA client - apply without verification
                    logger.warning(f"⚠️ No HA client - applying custom mappings without verification")
                    final_suggestion['validated_entities'].update(request.custom_entity_mapping)
        
        # Generate YAML for the suggestion (validated_entities already in final_suggestion)
        try:
            automation_yaml = await generate_automation_yaml(final_suggestion, query.original_query, [], db_session=db, ha_client=ha_client)
        except ValueError as e:
            # Catch validation errors and return proper error response
            error_msg = str(e)
            logger.error(f"❌ YAML generation failed: {error_msg}")
            
            # Extract available entities from error message if present
            suggestion_text = "The automation contains invalid entity IDs. Please check the automation description and try again."
            if "Available validated entities" in error_msg:
                suggestion_text += " The system attempted to auto-fix incomplete entity IDs but could not find matching entities in Home Assistant."
            elif "No validated entities were available" in error_msg:
                suggestion_text += " No validated entities were available for auto-fixing. Please ensure device names in your query match existing Home Assistant entities."
            
            return {
                "suggestion_id": suggestion_id,
                "query_id": query_id,
                "status": "error",
                "safe": False,
                "message": "Failed to generate valid automation YAML",
                "error_details": {
                    "type": "validation_error",
                    "message": error_msg,
                    "suggestion": suggestion_text
                }
            }
        
        # Track validated entities for safety validator
        validated_entity_ids = list(final_suggestion['validated_entities'].values())
        logger.info(f"📋 Using {len(validated_entity_ids)} validated entities for safety check")
        
        # Final validation: Verify ALL entity IDs in YAML exist in HA BEFORE creating automation
        if ha_client:
            try:
                # yaml_lib already imported at top of file
                parsed_yaml = yaml_lib.safe_load(automation_yaml)
                if parsed_yaml:
                    from ..services.entity_id_validator import EntityIDValidator
                    entity_id_extractor = EntityIDValidator()
                    
                    # Extract all entity IDs from YAML (returns list of tuples: (entity_id, location))
                    entity_id_tuples = entity_id_extractor._extract_all_entity_ids(parsed_yaml)
                    all_entity_ids_in_yaml = [eid for eid, _ in entity_id_tuples] if entity_id_tuples else []
                    logger.info(f"🔍 Final validation: Checking {len(all_entity_ids_in_yaml)} entity IDs exist in HA...")
                    
                    # Validate each entity ID exists in HA
                    invalid_entities = []
                    for entity_id in all_entity_ids_in_yaml:
                        try:
                            entity_state = await ha_client.get_entity_state(entity_id)
                            if not entity_state:
                                invalid_entities.append(entity_id)
                        except Exception:
                            invalid_entities.append(entity_id)
                    
                    if invalid_entities:
                        error_msg = f"Invalid entity IDs in YAML: {', '.join(invalid_entities)}"
                        logger.error(f"❌ {error_msg}")
                        return {
                            "suggestion_id": suggestion_id,
                            "query_id": query_id,
                            "status": "error",
                            "safe": False,
                            "message": "Automation contains invalid entity IDs",
                            "error_details": {
                                "type": "invalid_entities",
                                "message": error_msg,
                                "invalid_entities": invalid_entities
                            }
                        }
                    else:
                        logger.info(f"✅ Final validation passed: All {len(all_entity_ids_in_yaml)} entity IDs exist in HA")
            except Exception as e:
                logger.error(f"❌ Entity validation error: {e}", exc_info=True)
                return {
                    "suggestion_id": suggestion_id,
                    "query_id": query_id,
                    "status": "error",
                    "safe": False,
                    "message": "Failed to validate entities in automation YAML",
                    "error_details": {
                        "type": "validation_error",
                        "message": f"Entity validation failed: {str(e)}"
                    }
                }
        
        # Run safety checks
        logger.info("🔒 Running safety validation...")
        safety_validator = SafetyValidator(ha_client=ha_client)
        safety_report = await safety_validator.validate_automation(
            automation_yaml,
            validated_entities=validated_entity_ids
        )
        
        # Log warnings but don't block unless critical
        if safety_report.get('warnings'):
            logger.info(f"⚠️ Safety validation warnings: {len(safety_report.get('warnings', []))}")
        if not safety_report.get('safe', True):
            logger.warning(f"⚠️ Safety validation found issues, but continuing (user can review)")
        
        # Create automation in Home Assistant
        if not ha_client:
            raise HTTPException(status_code=500, detail="Home Assistant client not initialized")
        
        try:
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
                    "message": creation_result.get('message', 'Automation created successfully'),
                    "safety_report": safety_report,
                    "safe": safety_report.get('safe', True)
                }
            else:
                # Deployment failed but return YAML for user review
                error_message = creation_result.get('error', 'Unknown error')
                logger.error(f"❌ Failed to create automation: {error_message}")
                return {
                    "suggestion_id": suggestion_id,
                    "query_id": query_id,
                    "status": "yaml_generated",
                    "automation_id": None,
                    "automation_yaml": automation_yaml,
                    "ready_to_deploy": False,
                    "safe": safety_report.get('safe', True),
                    "safety_report": safety_report,
                    "message": f"YAML generated but deployment failed: {error_message}",
                    "error_details": {
                        "type": "deployment_error",
                        "message": error_message
                    },
                    "warnings": [f"Deployment failed: {error_message}"]
                }
        except Exception as e:
            error_message = str(e)
            logger.error(f"❌ Failed to create automation: {error_message}")
            return {
                "suggestion_id": suggestion_id,
                "query_id": query_id,
                "status": "yaml_generated",
                "automation_id": None,
                "automation_yaml": automation_yaml,
                "ready_to_deploy": False,
                "safe": safety_report.get('safe', True),
                "safety_report": safety_report,
                "message": f"YAML generated but deployment failed: {error_message}",
                "error_details": {
                    "type": "deployment_error",
                    "message": error_message
                },
                "warnings": [f"Deployment failed: {error_message}"]
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving suggestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Entity Alias Management Endpoints
# ============================================================================

class AliasCreateRequest(BaseModel):
    """Request to create an alias"""
    entity_id: str = Field(..., description="Entity ID to alias")
    alias: str = Field(..., description="Alias/nickname for the entity")
    user_id: str = Field(default="anonymous", description="User ID")


class AliasDeleteRequest(BaseModel):
    """Request to delete an alias"""
    alias: str = Field(..., description="Alias to delete")
    user_id: str = Field(default="anonymous", description="User ID")


class AliasResponse(BaseModel):
    """Response with alias information"""
    entity_id: str
    alias: str
    user_id: str
    created_at: datetime
    updated_at: datetime


@router.post("/aliases", response_model=AliasResponse, status_code=status.HTTP_201_CREATED)
async def create_alias(
    request: AliasCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new alias for an entity.
    
    Example:
        POST /api/v1/ask-ai/aliases
        {
            "entity_id": "light.bedroom_1",
            "alias": "sleepy light",
            "user_id": "user123"
        }
    """
    try:
        from ..services.alias_service import AliasService
        
        alias_service = AliasService(db)
        entity_alias = await alias_service.create_alias(
            entity_id=request.entity_id,
            alias=request.alias,
            user_id=request.user_id
        )
        
        if not entity_alias:
            raise HTTPException(
                status_code=400,
                detail=f"Alias '{request.alias}' already exists for user {request.user_id}"
            )
        
        return AliasResponse(
            entity_id=entity_alias.entity_id,
            alias=entity_alias.alias,
            user_id=entity_alias.user_id,
            created_at=entity_alias.created_at,
            updated_at=entity_alias.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating alias: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/aliases/{alias}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alias(
    alias: str,
    user_id: str = "anonymous",
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an alias.
    
    Args:
        alias: Alias to delete
        user_id: User ID (default: "anonymous")
    
    Example:
        DELETE /api/v1/ask-ai/aliases/sleepy%20light?user_id=user123
    """
    try:
        from ..services.alias_service import AliasService
        
        alias_service = AliasService(db)
        deleted = await alias_service.delete_alias(alias, user_id)
        
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Alias '{alias}' not found for user {user_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alias: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aliases", response_model=Dict[str, List[str]])
async def list_aliases(
    user_id: str = "anonymous",
    db: AsyncSession = Depends(get_db)
):
    """
    Get all aliases for a user, grouped by entity_id.
    
    Returns a dictionary mapping entity_id → list of aliases.
    
    Example:
        GET /api/v1/ask-ai/aliases?user_id=user123
        {
            "light.bedroom_1": ["sleepy light", "bedroom main"],
            "light.living_room_1": ["living room lamp"]
        }
    """
    try:
        from ..services.alias_service import AliasService
        
        alias_service = AliasService(db)
        aliases_by_entity = await alias_service.get_all_aliases(user_id)
        
        return aliases_by_entity
    except Exception as e:
        logger.error(f"Error listing aliases: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reverse-engineer-yaml", response_model=Dict[str, Any])
async def reverse_engineer_yaml(request: Dict[str, Any]):
    """
    Reverse engineer YAML and self-correct with iterative refinement.
    
    Uses advanced self-correction techniques to iteratively improve YAML quality:
    - Reverse Prompt Engineering (RPE) to understand generated YAML
    - Semantic similarity comparison using embeddings
    - ProActive Self-Refinement (PASR) for feedback-driven improvement
    - Up to 5 iterations until convergence or min similarity achieved
    
    Request:
    {
        "yaml": "automation yaml content",
        "original_prompt": "user's original request",
        "context": {} (optional)
    }
    
    Returns:
    {
        "final_yaml": "refined yaml",
        "final_similarity": 0.95,
        "iterations_completed": 3,
        "convergence_achieved": true,
        "iteration_history": [
            {
                "iteration": 1,
                "similarity_score": 0.72,
                "reverse_engineered_prompt": "description of what yaml does",
                "feedback": "explanation of issues",
                "improvement_actions": ["specific actions to improve"]
            },
            ...
        ]
    }
    """
    try:
        yaml_content = request.get("yaml", "")
        original_prompt = request.get("original_prompt", "")
        context = request.get("context")
        
        if not yaml_content or not original_prompt:
            raise ValueError("yaml and original_prompt are required")
        
        # Get self-correction service
        correction_service = get_self_correction_service()
        if not correction_service:
            raise HTTPException(
                status_code=503,
                detail="Self-correction service not available - OpenAI client not configured"
            )
        
        logger.info(f"🔄 Starting reverse engineering for prompt: {original_prompt[:60]}...")
        
        # Run self-correction
        result = await correction_service.correct_yaml(
            user_prompt=original_prompt,
            generated_yaml=yaml_content,
            context=context
        )
        
        logger.info(
            f"✅ Self-correction complete: "
            f"similarity={result.final_similarity:.2%}, "
            f"iterations={result.iterations_completed}, "
            f"converged={result.convergence_achieved}"
        )
        
        # Format response
        return {
            "final_yaml": result.final_yaml,
            "final_similarity": result.final_similarity,
            "iterations_completed": result.iterations_completed,
            "max_iterations": result.max_iterations,
            "convergence_achieved": result.convergence_achieved,
            "iteration_history": [
                {
                    "iteration": iter_result.iteration,
                    "similarity_score": iter_result.similarity_score,
                    "reverse_engineered_prompt": iter_result.reverse_engineered_prompt,
                    "feedback": iter_result.correction_feedback,
                    "improvement_actions": iter_result.improvement_actions
                }
                for iter_result in result.iteration_history
            ]
        }
        
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Reverse engineering failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
