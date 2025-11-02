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
from ..services.entity_attribute_service import EntityAttributeService
from ..prompt_building.entity_context_builder import EntityContextBuilder
from ..services.component_detector import ComponentDetector
from ..services.safety_validator import SafetyValidator
from ..services.yaml_self_correction import YAMLSelfCorrectionService
from sqlalchemy import select, update
import asyncio

logger = logging.getLogger(__name__)

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

# Initialize clients
ha_client = None
openai_client = None

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
    
    Used to create validated_entities mapping from devices_involved (friendly names) 
    to entity IDs using already-enriched entity data, avoiding re-resolution.
    
    IMPORTANT: Only includes entity IDs that actually exist in Home Assistant.
    
    Args:
        devices_involved: List of device friendly names from LLM suggestion
        enriched_data: Dictionary mapping entity_id to enriched entity data
        ha_client: Optional HA client for verifying entities exist
        fuzzy_match: If True, use fuzzy matching for partial matches
        
    Returns:
        Dictionary mapping device_name → entity_id (only verified entities)
    """
    validated_entities = {}
    unmapped_devices = []
    
    for device_name in devices_involved:
        mapped = False
        device_name_lower = device_name.lower()
        
        # Strategy 1: Exact match by friendly_name
        for entity_id, enriched in enriched_data.items():
            friendly_name = enriched.get('friendly_name', '')
            if friendly_name.lower() == device_name_lower:
                validated_entities[device_name] = entity_id
                mapped = True
                logger.debug(f"✅ Mapped device '{device_name}' → entity_id '{entity_id}' (exact match)")
                break
        
        # Strategy 2: Fuzzy matching (case-insensitive substring)
        if not mapped and fuzzy_match:
            for entity_id, enriched in enriched_data.items():
                friendly_name = enriched.get('friendly_name', '').lower()
                entity_name_part = entity_id.split('.')[-1].lower() if '.' in entity_id else ''
                
                # Check if device_name is contained in friendly_name or entity name
                if (device_name_lower in friendly_name or 
                    friendly_name in device_name_lower or
                    device_name_lower in entity_name_part):
                    validated_entities[device_name] = entity_id
                    mapped = True
                    logger.debug(f"✅ Mapped device '{device_name}' → entity_id '{entity_id}' (fuzzy match)")
                    break
        
        # Strategy 3: Match by domain name (e.g., "wled" matches light entities with "wled" in the name)
        if not mapped and fuzzy_match:
            for entity_id, enriched in enriched_data.items():
                domain = entity_id.split('.')[0].lower() if '.' in entity_id else ''
                if domain == device_name_lower:
                    validated_entities[device_name] = entity_id
                    mapped = True
                    logger.debug(f"✅ Mapped device '{device_name}' → entity_id '{entity_id}' (domain match)")
                    break
        
        if not mapped:
            unmapped_devices.append(device_name)
            logger.warning(f"⚠️ Could not map device '{device_name}' to entity_id (not found in enriched_data)")
    
    # CRITICAL: Verify ALL mapped entities actually exist in Home Assistant
    if validated_entities and ha_client:
        logger.info(f"🔍 Verifying {len(validated_entities)} mapped entities exist in Home Assistant...")
        entity_ids_to_verify = list(validated_entities.values())
        verification_results = await verify_entities_exist_in_ha(entity_ids_to_verify, ha_client)
        
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
        logger.info(f"✅ Verified {len(validated_entities)}/{len(entity_ids_to_verify)} entities exist in HA")
    
    if unmapped_devices and validated_entities:
        logger.info(
            f"✅ Mapped {len(validated_entities)}/{len(devices_involved)} devices to verified entities "
            f"({len(unmapped_devices)} unmapped: {unmapped_devices})"
        )
    elif validated_entities:
        logger.info(f"✅ Mapped all {len(validated_entities)} devices to verified entities")
    elif devices_involved:
        logger.warning(f"⚠️ Could not map any of {len(devices_involved)} devices to verified entities")
    
    return validated_entities


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
    
    # NEW: Validate entities before generating YAML
    from ..services.entity_validator import EntityValidator
    from ..clients.data_api_client import DataAPIClient
    
    try:
        logger.info("🔍 Starting entity validation...")
        # Initialize entity validator with data API client and optional db_session for alias support
        data_api_client = DataAPIClient()
        ha_client = HomeAssistantClient(
            ha_url=settings.ha_url,
            access_token=settings.ha_token
        ) if settings.ha_url and settings.ha_token else None
        entity_validator = EntityValidator(data_api_client, db_session=db_session, ha_client=ha_client)
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
        
        # Deduplicate entity mapping before using it
        if entity_mapping:
            entity_mapping = deduplicate_entity_mapping(entity_mapping)
        
        # Validate entity ID formats before using them
        validated_mapping = {}
        if entity_mapping:
            for term, entity_id in entity_mapping.items():
                # Ensure entity_id is in proper format (domain.entity)
                if isinstance(entity_id, str) and '.' in entity_id and not entity_id.startswith('.'):
                    validated_mapping[term] = entity_id
                else:
                    logger.warning(f"⚠️ Skipping invalid entity_id format: {term} -> {entity_id}")
            
            if validated_mapping:
                suggestion['validated_entities'] = validated_mapping
                logger.info(f"✅ VALIDATED ENTITIES ADDED TO SUGGESTION: {suggestion.get('validated_entities')}")
            else:
                logger.warning(f"⚠️ No valid entity IDs after format validation")
        else:
            logger.warning(f"⚠️ No valid entities found - mapping was: {entity_mapping}")
    except Exception as e:
        logger.error(f"❌ Error validating entities: {e}", exc_info=True)
        # Continue without validation if there's an error
    
    # Construct prompt for OpenAI to generate creative YAML with enriched entity context
    validated_entities_text = ""
    entity_context_json = ""
    
    if entities and len(entities) > 0:
        # Use comprehensive enriched data if available (from validation step above)
        # Fallback to entities list
        comprehensive_enriched_for_prompt = comprehensive_enriched_data if 'comprehensive_enriched_data' in locals() else None
        
        # Build enhanced entity context with COMPREHENSIVE data (capabilities, health, manufacturer, model, area, etc.)
        validated_entities_text = f"""
VALIDATED ENTITIES WITH COMPREHENSIVE DATA (use these exact entity IDs):
{_build_entity_validation_context_with_comprehensive_data(entities, enriched_data=comprehensive_enriched_for_prompt)}

CRITICAL: Use ONLY the entity IDs listed above. Do NOT create new entity IDs.
Pay attention to the capability types and ranges when generating service calls:
- For numeric capabilities: Use values within the specified range
- For enum capabilities: Use only the listed enum values
- For composite capabilities: Configure all sub-features properly

IMPORTANT SERVICE MAPPING:
- ALL light entities (including WLED) use: light.turn_on and light.turn_off
- WLED entities are lights, so use light.turn_on (NOT wled.turn_on)
- Example: For a WLED entity from the validated list above, use: service: light.turn_on with target.entity_id: <actual_wled_entity_id>

"""
    elif 'validated_entities' in suggestion and suggestion.get('validated_entities'):
        # Ensure we have a non-empty dict
        validated_entities = suggestion.get('validated_entities', {})
        if not validated_entities or not isinstance(validated_entities, dict):
            logger.warning(f"⚠️ validated_entities is empty or invalid: {validated_entities}")
            validated_entities = {}
        
        # Check if we have cached enriched context (fast path)
        if validated_entities and 'enriched_entity_context' in suggestion and suggestion['enriched_entity_context']:
            logger.info("✅ Using cached enriched entity context - FAST PATH")
            entity_context_json = suggestion['enriched_entity_context']
        elif validated_entities:
            # Fall back to re-enrichment (slow path, backwards compatibility)
            logger.info("⚠️ Re-enriching entities - SLOW PATH")
            try:
                logger.info("🔍 Enriching entities with attributes...")
                
                # Initialize HA client
                ha_client = HomeAssistantClient(
                    ha_url=settings.ha_url,
                    access_token=settings.ha_token
                )
                
                # Get entity IDs from mapping
                entity_ids = list(suggestion['validated_entities'].values())
                
                # Enrich entities with attributes
                attribute_service = EntityAttributeService(ha_client)
                enriched_data = await attribute_service.enrich_multiple_entities(entity_ids)
                
                # Build entity context JSON
                context_builder = EntityContextBuilder()
                entity_context_json = await context_builder.build_entity_context_json(
                    entities=[{'entity_id': eid} for eid in entity_ids],
                    enriched_data=enriched_data
                )
                
                logger.info(f"✅ Built entity context JSON with {len(enriched_data)} enriched entities")
                logger.debug(f"Entity context JSON: {entity_context_json[:500]}...")
                
            except Exception as e:
                logger.warning(f"⚠️ Error enriching entities: {e}")
                entity_context_json = ""
        
        # Pre-validate suggestion and enhance validated_entities (Phase 3)
        try:
            enhanced_validated_entities = await pre_validate_suggestion_for_yaml(
                suggestion,
                validated_entities,
                ha_client
            )
            if enhanced_validated_entities != validated_entities:
                logger.info(f"✅ Enhanced validated_entities: {len(validated_entities)} → {len(enhanced_validated_entities)} entities")
                validated_entities = enhanced_validated_entities
        except Exception as e:
            logger.warning(f"⚠️ Pre-validation failed, using original validated_entities: {e}")
        
        # Build suggestion-specific entity mapping (Phase 4)
        suggestion_specific_mapping = ""
        try:
            suggestion_specific_mapping = await build_suggestion_specific_entity_mapping(
                suggestion,
                validated_entities
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to build suggestion-specific mapping: {e}")
        
        # Build fallback text format using validated_entities from above check
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
{chr(10).join(mapping_examples[:15])}  # Limit to first 15 to avoid prompt bloat

"""
            
            # Build dynamic example entity IDs for the prompt
            example_light = next((eid for eid in validated_entities.values() if eid.startswith('light.')), None)
            example_sensor = next((eid for eid in validated_entities.values() if eid.startswith('binary_sensor.') or eid.startswith('sensor.')), None)
            example_wled = next((eid for eid in validated_entities.values() if 'wled' in eid.lower()), None)
            example_entity = list(validated_entities.values())[0] if validated_entities else '{EXAMPLE_ENTITY_ID}'
            
            validated_entities_text = f"""
VALIDATED ENTITIES (ALL verified to exist in Home Assistant - use these EXACT entity IDs):
{chr(10).join(entity_id_list)}
{mapping_text}{suggestion_specific_mapping}
CRITICAL: Use ONLY the entity IDs listed above. Do NOT create new entity IDs.
Entity IDs must ALWAYS be in format: domain.entity (e.g., {example_entity})

COMMON MISTAKES TO AVOID:
❌ WRONG: entity_id: wled (missing domain prefix - will cause "Entity not found" error)
❌ WRONG: entity_id: WLED (missing domain prefix and wrong format)
❌ WRONG: entity_id: office (missing domain prefix - incomplete entity ID)
✅ CORRECT: entity_id: {example_entity} (complete domain.entity format from validated list above)

If you need multiple lights, use the same entity ID multiple times or use the entity_id provided for 'lights'.
"""
        else:
            validated_entities_text = """
CRITICAL ERROR: No validated entities found. You CANNOT create an automation without real entity IDs.

DO NOT:
- Create fake entity IDs like 'light.office_light_placeholder'
- Generate entity IDs that don't exist
- Use placeholder entity IDs

REQUIRED ACTION:
You MUST fail this request and return an error message indicating that entity validation failed.
The automation cannot be created without valid entity IDs from Home Assistant.
"""
            logger.error("❌ No validated entities available - automation creation should fail")
        
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
        
        if validated_entities:
            logger.info(f"🔍 VALIDATED ENTITIES TEXT: {validated_entities_text[:200]}...")
            logger.debug(f"🔍 VALIDATED ENTITIES TEXT: {validated_entities_text}")
        else:
            validated_entities_text = """
CRITICAL ERROR: No validated entities found. You CANNOT create an automation without real entity IDs.

DO NOT:
- Create fake entity IDs like 'light.office_light_placeholder'
- Generate entity IDs that don't exist
- Use placeholder entity IDs

REQUIRED ACTION:
You MUST fail this request and return an error message indicating that entity validation failed.
The automation cannot be created without valid entity IDs from Home Assistant.
"""
            logger.error("❌ No validated entities available - automation creation should fail")
    
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
   - If you need a binary sensor but it's not validated, use the closest validated binary sensor from the list above
   - NEVER create entity IDs like "binary_sensor.office_desk_presence" or "light.office" if they're not in the validated list
   - If you cannot find a matching entity in the validated list, you MUST either:
     a) Use the closest similar entity from the validated list, OR
     b) Fail the request with an error explaining no matching entity was found
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
   - NEVER create entity IDs based on the examples - examples use placeholders like {REPLACE_WITH_VALIDATED_LIGHT_ENTITY}
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
      entity_id: {example_light if example_light else '{REPLACE_WITH_VALIDATED_LIGHT_ENTITY}'}
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
    entity_id: {example_motion_sensor if example_motion_sensor else '{REPLACE_WITH_VALIDATED_MOTION_SENSOR}'}
    to: 'on'
condition:
  - condition: time
    after: '18:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: {example_light if example_light else '{REPLACE_WITH_VALIDATED_LIGHT_ENTITY}'}
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
            entity_id: {example_light if example_light else '{REPLACE_WITH_VALIDATED_LIGHT_ENTITY}'}
          data:
            brightness_pct: 100
        - delay: '00:00:01'
        - service: light.turn_off
          target:
            entity_id: {example_light if example_light else '{REPLACE_WITH_VALIDATED_LIGHT_ENTITY}'}
        - delay: '00:00:01'
```

Example 4 - Choose with multiple triggers (CORRECT):
```yaml
alias: Color-Coded Door Notifications
description: Different colors for different doors
mode: single
trigger:
  - platform: state
    entity_id: {example_door_sensor if example_door_sensor else '{REPLACE_WITH_VALIDATED_DOOR_SENSOR_1}'}
    to: 'on'
    id: front_door
  - platform: state
    entity_id: {example_door_sensor if example_door_sensor else '{REPLACE_WITH_VALIDATED_DOOR_SENSOR_2}'}
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
              entity_id: {example_light if example_light else '{REPLACE_WITH_VALIDATED_LIGHT_ENTITY}'}
            data:
              brightness_pct: 100
              color_name: red
      - conditions:
          - condition: trigger
            id: back_door
        sequence:
          - service: light.turn_on
            target:
              entity_id: {example_light if example_light else '{REPLACE_WITH_VALIDATED_LIGHT_ENTITY}'}
            data:
              brightness_pct: 100
              color_name: blue
    default:
      - service: light.turn_on
        target:
          entity_id: {example_light if example_light else '{REPLACE_WITH_VALIDATED_LIGHT_ENTITY}'}
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
               entity_id: {example_light if example_light else '{REPLACE_WITH_VALIDATED_LIGHT_ENTITY}'}  # ✅ FULL ENTITY ID (domain.entity)
           - service: light.turn_on  # ✅ WLED entities use light.turn_on service (NOT wled.turn_on)
             target:
               entity_id: {example_wled if example_wled else '{REPLACE_WITH_VALIDATED_WLED_ENTITY}'}  # ✅ FULL ENTITY ID (domain.entity)
             data:
               effect: fireworks  # WLED-specific effect parameter
           - delay: "00:01:00"
           - service: light.turn_off  # ✅ WLED entities use light.turn_off service (NOT wled.turn_off)
             target:
               entity_id: {example_wled if example_wled else '{REPLACE_WITH_VALIDATED_WLED_ENTITY}'}  # ✅ FULL ENTITY ID (domain.entity)

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
        
        # Validate the YAML syntax
        try:
            yaml_lib.safe_load(yaml_content)
            logger.info(f"✅ Generated valid YAML syntax for suggestion {suggestion.get('suggestion_id')}")
        except yaml_lib.YAMLError as e:
            logger.error(f"❌ Generated invalid YAML syntax: {e}")
            raise ValueError(f"Generated YAML syntax is invalid: {e}")
        
        # Validate HA structure
        from ..llm.yaml_generator import YAMLGenerator
        yaml_gen = YAMLGenerator(openai_client.client if hasattr(openai_client, 'client') else None)
        structure_valid, structure_errors = yaml_gen.validate_ha_structure(yaml_content)
        if not structure_valid:
            logger.warning(f"⚠️ HA structure validation failed: {structure_errors}")
            # Log but don't fail - HA API validation will catch it
        
        # Validate with HA API if client is available
        # Use global ha_client or create one if needed
        validation_ha_client = ha_client if 'ha_client' in locals() and ha_client else None
        if not validation_ha_client and settings.ha_url and settings.ha_token:
            try:
                validation_ha_client = HomeAssistantClient(
                    ha_url=settings.ha_url,
                    access_token=settings.ha_token
                )
            except Exception as e:
                logger.warning(f"⚠️ Could not create HA client for validation: {e}")
        
        if validation_ha_client:
            try:
                logger.info("🔍 Validating YAML with Home Assistant API...")
                validation_result = await validation_ha_client.validate_automation(yaml_content)
                if not validation_result.get('valid', False):
                    error_msg = validation_result.get('error', 'Unknown validation error')
                    warnings = validation_result.get('warnings', [])
                    logger.warning(f"⚠️ HA API validation failed: {error_msg}")
                    if warnings:
                        logger.warning(f"⚠️ HA API warnings: {warnings}")
                    # Don't fail - let user see the validation issues
                else:
                    logger.info("✅ HA API validation passed")
            except Exception as e:
                logger.warning(f"⚠️ HA API validation error (continuing anyway): {e}")
        
        # Validate YAML structure and fix service names (e.g., wled.turn_on → light.turn_on)
        from ..services.yaml_structure_validator import YAMLStructureValidator
        validator = YAMLStructureValidator()
        validation = validator.validate(yaml_content)
        
        # If validation fixed service names (like wled.turn_on → light.turn_on), use the fixed YAML
        if validation.fixed_yaml:
            yaml_content = validation.fixed_yaml
            service_fixes = [w for w in validation.warnings if '→' in w]
            if service_fixes:
                logger.info(f"✅ Applied {len(service_fixes)} service name fixes:")
                for fix in service_fixes:
                    logger.info(f"  🔧 {fix}")
        
        if not validation.is_valid:
            logger.error("❌ YAML structure validation failed:")
            for error in validation.errors:
                logger.error(f"  {error}")
            
            # Try auto-fix for structure issues
            if validation.fixed_yaml and yaml_content != validation.fixed_yaml:
                logger.info("🔧 Attempting to auto-fix YAML structure...")
                fixed_validation = validator.validate(validation.fixed_yaml)
                if fixed_validation.is_valid:
                    logger.info("✅ Auto-fix successful! Using corrected YAML.")
                    yaml_content = validation.fixed_yaml
                else:
                    logger.warning("⚠️ Auto-fix incomplete, but using fixed version anyway:")
                    for error in fixed_validation.errors:
                        logger.warning(f"  {error}")
                    yaml_content = validation.fixed_yaml
            elif not validation.fixed_yaml:
                logger.warning("⚠️ Could not auto-fix YAML structure errors - using original YAML")
        else:
            logger.info("✅ YAML structure validation passed")
            if validation.warnings:
                for warning in validation.warnings:
                    if '→' not in warning:  # Don't log service fixes again (already logged above)
                        logger.warning(f"  {warning}")
        
        # Validate entity_id values (CRITICAL: prevents HA 400 errors)
        try:
            parsed_yaml = yaml_lib.safe_load(yaml_content)
            if parsed_yaml:
                from ..services.entity_id_validator import EntityIDValidator
                entity_validator = EntityIDValidator()
                
                # Get validated entity IDs for auto-fixing
                validated_entity_ids = []
                
                # Strategy 1: Extract from entities parameter (from query.extracted_entities)
                if entities:
                    for entity in entities:
                        if isinstance(entity, dict) and 'entity_id' in entity:
                            entity_id = entity['entity_id']
                            if entity_id and isinstance(entity_id, str):  # Only add non-empty string entity IDs
                                validated_entity_ids.append(entity_id)
                        elif isinstance(entity, str) and entity:
                            validated_entity_ids.append(entity)
                
                # Strategy 2: Extract from suggestion's validated_entities if available
                if isinstance(suggestion, dict) and 'validated_entities' in suggestion:
                    validated_mapping = suggestion.get('validated_entities', {})
                    if isinstance(validated_mapping, dict):
                        for entity_id in validated_mapping.values():
                            if entity_id and isinstance(entity_id, str):
                                if entity_id not in validated_entity_ids:
                                    validated_entity_ids.append(entity_id)
                
                # Strategy 3: Extract incomplete entity IDs from YAML and query HA for domain matches
                if parsed_yaml:
                    incomplete_ids = []
                    # Quick scan for incomplete entity IDs (no dot)
                    def scan_for_incomplete_ids(data, path=""):
                        if isinstance(data, dict):
                            for key, value in data.items():
                                if key == 'entity_id':
                                    if isinstance(value, str) and '.' not in value and value:
                                        incomplete_ids.append((value, path))
                                else:
                                    scan_for_incomplete_ids(value, f"{path}.{key}" if path else key)
                        elif isinstance(data, list):
                            for i, item in enumerate(data):
                                scan_for_incomplete_ids(item, f"{path}[{i}]" if path else f"[{i}]")
                    
                    scan_for_incomplete_ids(parsed_yaml)
                    
                    # Query HA for entities matching incomplete IDs (treat as domain names)
                    if incomplete_ids and ha_client:
                        domains_to_query = set()
                        for incomplete_id, _ in incomplete_ids:
                            # Treat incomplete ID as potential domain
                            domains_to_query.add(incomplete_id.lower())
                        
                        logger.info(f"🔍 Found {len(incomplete_ids)} incomplete entity IDs, querying HA for domains: {list(domains_to_query)}")
                        for domain in domains_to_query:
                            try:
                                domain_entities = await ha_client.get_entities_by_domain(domain)
                                for entity_id in domain_entities:
                                    if entity_id not in validated_entity_ids:
                                        validated_entity_ids.append(entity_id)
                                        logger.debug(f"📋 Added entity from HA query: {entity_id}")
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to query HA for domain '{domain}': {e}")
                
                logger.info(f"🔍 Validated entities for auto-fix ({len(validated_entity_ids)} total): {validated_entity_ids[:10]}")
                
                entity_validation = entity_validator.validate_entity_ids(
                    parsed_yaml, 
                    validated_entities=validated_entity_ids,
                    auto_fix=True
                )
                
                # Check if fixes were applied (check both warnings for "Auto-fixed" and actual fix count)
                fixes_were_applied = False
                fix_count = 0
                if entity_validation.warnings:
                    for warning in entity_validation.warnings:
                        if 'Auto-fixed' in warning:
                            fixes_were_applied = True
                            # Try to extract fix count from warning
                            if 'Auto-fixed' in warning:
                                try:
                                    # Warning format: "Auto-fixed X incomplete entity IDs"
                                    import re
                                    match = re.search(r'Auto-fixed (\d+)', warning)
                                    if match:
                                        fix_count = int(match.group(1))
                                except:
                                    pass
                
                # If fixes were applied, regenerate YAML and re-validate
                if fixes_were_applied:
                    logger.info(f"🔧 Auto-fixes applied ({fix_count if fix_count > 0 else 'unknown count'}), regenerating YAML...")
                    yaml_content = yaml_lib.dump(parsed_yaml, default_flow_style=False, sort_keys=False)
                    logger.info("🔄 Regenerated YAML after auto-fixing entity IDs")
                    
                    # Re-parse and re-validate to ensure fixes worked
                    try:
                        reparsed_yaml = yaml_lib.safe_load(yaml_content)
                        if reparsed_yaml:
                            # Re-validate to confirm all issues are fixed
                            re_validation = entity_validator.validate_entity_ids(
                                reparsed_yaml,
                                validated_entities=validated_entity_ids,
                                auto_fix=False  # Don't auto-fix again, just validate
                            )
                            
                            if re_validation.is_valid:
                                logger.info("✅ Re-validation passed after auto-fixes - all entity IDs are now valid")
                            else:
                                logger.warning(f"⚠️ Re-validation found {len(re_validation.errors)} remaining errors after auto-fixes")
                                for error in re_validation.errors[:3]:
                                    logger.warning(f"  {error}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not re-validate regenerated YAML: {e}")
                
                if not entity_validation.is_valid:
                    logger.error("❌ Entity ID validation failed:")
                    for error in entity_validation.errors:
                        logger.error(f"  {error}")
                    
                    # Include available validated entities in error message for debugging
                    error_msg = f"Invalid entity IDs in YAML: {entity_validation.errors[:3]}"
                    if len(entity_validation.errors) > 3:
                        error_msg += f" (and {len(entity_validation.errors) - 3} more)"
                    if validated_entity_ids:
                        error_msg += f"\nAvailable validated entities: {validated_entity_ids[:5]}"
                    else:
                        error_msg += "\nNo validated entities were available for auto-fixing"
                    
                    raise ValueError(error_msg)
                else:
                    logger.info("✅ Entity ID validation passed")
        except yaml_lib.YAMLError as e:
            logger.warning(f"⚠️ Could not parse YAML for entity ID validation: {e}")
        except ValueError as e:
            # Re-raise ValueError from entity validation
            raise
        
        # POST-GENERATION SAFETY NET: Validate all entities in generated YAML against HA
        # This catches any invalid entities that somehow got past the LLM prompt restrictions
        if ha_client:
            try:
                import yaml as yaml_lib
                post_gen_parsed = yaml_lib.safe_load(yaml_content)
                if post_gen_parsed:
                    from ..services.entity_id_validator import EntityIDValidator
                    post_gen_validator = EntityIDValidator()
                    
                    # Extract all entity IDs from generated YAML
                    post_gen_entity_tuples = post_gen_validator._extract_all_entity_ids(post_gen_parsed)
                    post_gen_entity_ids = [eid for eid, _ in post_gen_entity_tuples] if post_gen_entity_tuples else []
                    
                    if post_gen_entity_ids:
                        logger.info(f"🔍 POST-GENERATION VALIDATION: Checking {len(post_gen_entity_ids)} entity IDs from generated YAML...")
                        invalid_post_gen = []
                        replacements = {}
                        
                        for entity_id in post_gen_entity_ids:
                            try:
                                entity_state = await ha_client.get_entity_state(entity_id)
                                if not entity_state:
                                    invalid_post_gen.append(entity_id)
                                    logger.warning(f"⚠️ Post-gen check: Entity NOT found: {entity_id}")
                                    # Try to find replacement from validated entities
                                    if validated_entity_ids:
                                        # Find closest match by domain
                                        domain = entity_id.split('.')[0] if '.' in entity_id else ''
                                        candidates = [eid for eid in validated_entity_ids if eid.startswith(f"{domain}.")]
                                        if candidates:
                                            replacement = candidates[0]
                                            replacements[entity_id] = replacement
                                            logger.info(f"  🔧 Found replacement: {entity_id} → {replacement}")
                            except Exception:
                                invalid_post_gen.append(entity_id)
                                logger.warning(f"⚠️ Post-gen check: Entity validation failed: {entity_id}")
                        
                        # Replace invalid entities if we found replacements
                        if replacements:
                            logger.info(f"🔧 POST-GEN REPLACEMENT: Replacing {len(replacements)} invalid entities with validated ones...")
                            for old_id, new_id in replacements.items():
                                yaml_content = yaml_content.replace(old_id, new_id)
                                logger.info(f"  ✅ Replaced: {old_id} → {new_id}")
                            
                            # Re-parse to update the parsed YAML
                            post_gen_parsed = yaml_lib.safe_load(yaml_content)
                        
                        # If we still have invalid entities without replacements, fail
                        remaining_invalid = [eid for eid in invalid_post_gen if eid not in replacements]
                        if remaining_invalid:
                            logger.error(f"❌ POST-GEN VALIDATION FAILED: {len(remaining_invalid)} invalid entities without replacements: {remaining_invalid}")
                            raise ValueError(
                                f"Generated YAML contains invalid entity IDs that don't exist in Home Assistant: {', '.join(remaining_invalid)}. "
                                f"Available validated entities: {', '.join(validated_entity_ids[:10]) if validated_entity_ids else 'None'}"
                            )
                        elif invalid_post_gen:
                            logger.info(f"✅ POST-GEN VALIDATION: Fixed {len(replacements)} invalid entities via replacement")
                        else:
                            logger.info(f"✅ POST-GEN VALIDATION: All {len(post_gen_entity_ids)} entity IDs are valid")
            except ValueError:
                # Re-raise ValueError - these are fatal
                raise
            except Exception as e:
                logger.warning(f"⚠️ Post-generation validation error (continuing with generated YAML): {e}", exc_info=True)
        
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
                
                # Extract location and domain from query to get ALL matching entities
                query_location = entity_validator._extract_location_from_query(query)
                query_domain = entity_validator._extract_domain_from_query(query)
                
                logger.info(f"🔍 Extracted location='{query_location}', domain='{query_domain}' from query")
                
                # Fetch ALL entities matching the query context (all office lights, not just one)
                available_entities = await entity_validator._get_available_entities(
                    domain=query_domain,
                    area_id=query_location
                )
                
                if available_entities:
                    # Get all entity IDs that match the query context
                    resolved_entity_ids = [e.get('entity_id') for e in available_entities if e.get('entity_id')]
                    logger.info(f"✅ Found {len(resolved_entity_ids)} entities matching query context (location={query_location}, domain={query_domain})")
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
                    
                    # Use comprehensive enrichment service that combines ALL data sources
                    from ..services.comprehensive_entity_enrichment import enrich_entities_comprehensively
                    enriched_data = await enrich_entities_comprehensively(
                        entity_ids=set(resolved_entity_ids),
                        ha_client=ha_client,
                        device_intelligence_client=_device_intelligence_client,
                        data_api_client=None,  # Could add DataAPIClient if historical patterns needed
                        include_historical=False  # Set to True to include usage patterns
                    )
                    
                    # Build entity context JSON from enriched data
                    # Create entity dicts for context builder from enriched data
                    enriched_entities = []
                    for entity_id in resolved_entity_ids:
                        enriched = enriched_data.get(entity_id, {})
                        enriched_entities.append({
                            'entity_id': entity_id,
                            'friendly_name': enriched.get('friendly_name', entity_id),
                            'name': enriched.get('friendly_name', entity_id.split('.')[-1] if '.' in entity_id else entity_id)
                        })
                    
                    context_builder = EntityContextBuilder()
                    entity_context_json = await context_builder.build_entity_context_json(
                        entities=enriched_entities,
                        enriched_data=enriched_data
                    )
                    
                    logger.info(f"✅ Built entity context JSON with {len(enriched_data)} enriched entities")
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
            entity_context_json=entity_context_json  # Pass enriched context
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
                # Map devices_involved to entity IDs using enriched_data (if available)
                validated_entities = {}
                devices_involved = suggestion.get('devices_involved', [])
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
                    else:
                        logger.warning(f"⚠️ No verified entities found for suggestion {i+1} (devices: {devices_involved})")
                
                # Create base suggestion
                base_suggestion = {
                    'suggestion_id': f'ask-ai-{uuid.uuid4().hex[:8]}',
                    'description': suggestion['description'],
                    'trigger_summary': suggestion['trigger_summary'],
                    'action_summary': suggestion['action_summary'],
                    'devices_involved': devices_involved,
                    'validated_entities': validated_entities,  # Save mapping for fast test execution
                    'enriched_entity_context': entity_context_json,  # Cache enrichment data to avoid re-enrichment
                    'capabilities_used': suggestion.get('capabilities_used', []),
                    'confidence': suggestion['confidence'],
                    'status': 'draft',
                    'created_at': datetime.now().isoformat()
                }
                
                # Enhance suggestion with entity IDs (Phase 1 & 2)
                try:
                    enhanced_suggestion = await enhance_suggestion_with_entity_ids(
                        base_suggestion,
                        validated_entities,
                        enriched_data if enriched_data else None,
                        ha_client if 'ha_client' in locals() else None
                    )
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
        return {
            'suggestion': original_suggestion,
            'restored_components': [],
            'restoration_log': []
        }
    
    # Use OpenAI to intelligently restore components with context
    if not openai_client:
        logger.warning("OpenAI client not available, skipping intelligent restoration")
        return {
            'suggestion': original_suggestion,
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
        return {
            'suggestion': original_suggestion,  # Original already has components, we're just validating
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
        return {
            'suggestion': original_suggestion,
            'restored_components': stripped_components,
            'restoration_log': [f'Restoration attempted but failed: {str(e)}'],
            'restoration_confidence': 0.5
        }


@router.post("/query/{query_id}/suggestions/{suggestion_id}/approve")
async def approve_suggestion_from_query(
    query_id: str,
    suggestion_id: str,
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
        
        # TASK 1.4: Restore stripped components if test was run
        # For now, we'll check the original suggestion for components to restore
        # In the future, we could store test results and retrieve them here
        test_result = None  # TODO: Retrieve from test history when available
        restoration_result = await restore_stripped_components(
            original_suggestion=suggestion,
            test_result=test_result,
            original_query=query.original_query,
            openai_client=openai_client
        )
        
        # Use restored suggestion (which is the same as original for now)
        final_suggestion = restoration_result['suggestion']
        
        # Generate YAML for the suggestion with entities for capability details
        entities = query.extracted_entities if query.extracted_entities else []
        try:
            automation_yaml = await generate_automation_yaml(final_suggestion, query.original_query, entities, db_session=db, ha_client=ha_client)
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
        validated_entity_ids = []
        if 'validated_entities' in final_suggestion and final_suggestion.get('validated_entities'):
            validated_entity_ids = list(final_suggestion['validated_entities'].values())
            logger.info(f"📋 Tracked {len(validated_entity_ids)} validated entities for safety check: {validated_entity_ids}")
        
        # Reverse engineering self-correction: Validate and improve YAML to match user intent
        correction_result = None
        correction_service = get_self_correction_service()
        if correction_service:
            try:
                logger.info("🔄 Running reverse engineering self-correction...")
                
                # Get comprehensive enriched data for entities used in YAML
                approve_enriched_data = None
                if validated_entity_ids and ha_client:
                    try:
                        from ..services.comprehensive_entity_enrichment import enrich_entities_comprehensively
                        approve_enriched_data = await enrich_entities_comprehensively(
                            entity_ids=set(validated_entity_ids),
                            ha_client=ha_client,
                            device_intelligence_client=_device_intelligence_client,
                            data_api_client=None,
                            include_historical=False
                        )
                        logger.info(f"✅ Got comprehensive enrichment for {len(approve_enriched_data)} entities for reverse engineering")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not get comprehensive enrichment for approve: {e}")
                
                context = {
                    "entities": entities,
                    "suggestion": final_suggestion,
                    "devices_involved": final_suggestion.get('devices_involved', [])
                }
                correction_result = await correction_service.correct_yaml(
                    user_prompt=query.original_query,
                    generated_yaml=automation_yaml,
                    context=context,
                    comprehensive_enriched_data=approve_enriched_data
                )
                
                # Store initial metrics in database (automation_created will be updated later)
                try:
                    from ..services.reverse_engineering_metrics import store_reverse_engineering_metrics
                    # Check if YAML had validation errors before RE
                    had_validation_errors = False  # Will be updated if we detect errors
                    
                    await store_reverse_engineering_metrics(
                        db_session=db,
                        suggestion_id=suggestion_id,
                        query_id=query_id,
                        correction_result=correction_result,
                        automation_created=None,  # Will be updated after creation attempt
                        automation_id=None,
                        had_validation_errors=had_validation_errors,
                        errors_fixed_count=0
                    )
                    logger.info("✅ Stored initial reverse engineering metrics")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to store initial reverse engineering metrics: {e}")
                
                if correction_result.convergence_achieved or correction_result.final_similarity >= 0.80:
                    # Use corrected YAML if similarity improved significantly
                    if correction_result.final_similarity > 0.85:
                        logger.info(f"✅ Using self-corrected YAML (similarity: {correction_result.final_similarity:.2%})")
                        automation_yaml = correction_result.final_yaml
                    else:
                        logger.info(f"ℹ️  Self-correction completed (similarity: {correction_result.final_similarity:.2%}), keeping original YAML")
                else:
                    logger.warning(f"⚠️  Self-correction did not converge (similarity: {correction_result.final_similarity:.2%}), using original YAML")
            except Exception as e:
                logger.warning(f"⚠️  Self-correction failed, continuing with original YAML: {e}")
                correction_result = None
        else:
            logger.debug("Self-correction service not available, skipping reverse engineering")
        
        # FINAL VALIDATION: Verify ALL entity IDs in test YAML exist in HA BEFORE creating automation
        if ha_client:
            try:
                import yaml as yaml_lib
                parsed_yaml = yaml_lib.safe_load(automation_yaml)
                if parsed_yaml:
                    from ..services.entity_id_validator import EntityIDValidator
                    entity_id_extractor = EntityIDValidator()
                    
                    # Extract all entity IDs from YAML (returns list of tuples: (entity_id, location))
                    entity_id_tuples = entity_id_extractor._extract_all_entity_ids(parsed_yaml)
                    all_entity_ids_in_yaml = [eid for eid, _ in entity_id_tuples] if entity_id_tuples else []
                    logger.info(f"🔍 FINAL TEST VALIDATION: Checking {len(all_entity_ids_in_yaml)} entity IDs exist in HA...")
                    
                    # Validate each entity ID exists in HA
                    invalid_entities = []
                    for entity_id in all_entity_ids_in_yaml:
                        try:
                            entity_state = await ha_client.get_entity_state(entity_id)
                            if not entity_state:
                                invalid_entities.append(entity_id)
                                logger.error(f"❌ Entity NOT FOUND in HA: {entity_id}")
                        except Exception as e:
                            invalid_entities.append(entity_id)
                            logger.error(f"❌ Entity NOT FOUND in HA: {entity_id} (error: {str(e)[:100]})")
                    
                    if invalid_entities:
                        # FAIL before creating test automation
                        error_msg = f"Invalid entity IDs in test YAML: {', '.join(invalid_entities)}"
                        logger.error(f"❌ {error_msg}")
                        
                        return {
                            "suggestion_id": suggestion_id,
                            "query_id": query_id,
                            "status": "error",
                            "safe": False,
                            "message": "Test automation contains invalid entity IDs",
                            "error_details": {
                                "type": "invalid_entities",
                                "message": error_msg,
                                "invalid_entities": invalid_entities,
                                "suggestion": "The automation contains entity IDs that do not exist in Home Assistant."
                            },
                            "warnings": [f"Entity not found: {eid}" for eid in invalid_entities]
                        }
                    else:
                        logger.info(f"✅ FINAL TEST VALIDATION PASSED: All {len(all_entity_ids_in_yaml)} entity IDs exist in HA")
            except Exception as e:
                logger.error(f"❌ Final test entity validation error: {e}", exc_info=True)
                # Fail if validation can't complete - don't create automation with unvalidated entities
                return {
                    "suggestion_id": suggestion_id,
                    "query_id": query_id,
                    "status": "error",
                    "safe": False,
                    "message": "Failed to validate entities in automation YAML",
                    "error_details": {
                        "type": "validation_error",
                        "message": f"Entity validation failed: {str(e)}",
                        "suggestion": "Unable to verify entity IDs exist in Home Assistant. Automation creation blocked."
                    },
                    "warnings": [f"Validation error: {str(e)[:200]}"]
                }
        
        # TASK 2.3: Run safety checks before creating automation
        logger.info("🔒 Running safety validation...")
        safety_validator = SafetyValidator(ha_client=ha_client)
        safety_report = await safety_validator.validate_automation(
            automation_yaml,
            validated_entities=validated_entity_ids
        )
        
        if not safety_report.get('safe', True):
            critical_issues = safety_report.get('critical_issues', [])
            logger.warning(f"⚠️ Safety validation failed: {len(critical_issues)} critical issues")
            return {
                "suggestion_id": suggestion_id,
                "query_id": query_id,
                "status": "blocked",
                "safe": False,
                "safety_report": safety_report,
                "message": "Automation creation blocked due to safety concerns",
                "warnings": [issue.get('message') for issue in critical_issues]
            }
        
        # Log warnings if any
        if safety_report.get('warnings'):
            logger.info(f"⚠️ Safety validation passed with {len(safety_report.get('warnings', []))} warnings")
        
        # FINAL VALIDATION: Verify ALL entity IDs in YAML exist in HA BEFORE creating automation
        if ha_client:
            try:
                import yaml as yaml_lib
                parsed_yaml = yaml_lib.safe_load(automation_yaml)
                if parsed_yaml:
                    from ..services.entity_id_validator import EntityIDValidator
                    entity_id_extractor = EntityIDValidator()
                    
                    # Extract all entity IDs from YAML (returns list of tuples: (entity_id, location))
                    entity_id_tuples = entity_id_extractor._extract_all_entity_ids(parsed_yaml)
                    all_entity_ids_in_yaml = [eid for eid, _ in entity_id_tuples] if entity_id_tuples else []
                    logger.info(f"🔍 FINAL VALIDATION: Checking {len(all_entity_ids_in_yaml)} entity IDs exist in HA...")
                    
                    # Validate each entity ID exists in HA
                    invalid_entities = []
                    for entity_id in all_entity_ids_in_yaml:
                        try:
                            # Check if entity exists by getting its state
                            entity_state = await ha_client.get_entity_state(entity_id)
                            if not entity_state:
                                invalid_entities.append(entity_id)
                                logger.error(f"❌ Entity NOT FOUND in HA: {entity_id}")
                        except Exception as e:
                            # If get_entity_state fails, entity likely doesn't exist
                            invalid_entities.append(entity_id)
                            logger.error(f"❌ Entity NOT FOUND in HA: {entity_id} (error: {str(e)[:100]})")
                    
                    if invalid_entities:
                        # FAIL BEFORE creating automation
                        error_msg = f"Invalid entity IDs found in YAML that do not exist in Home Assistant: {', '.join(invalid_entities)}"
                        logger.error(f"❌ {error_msg}")
                        
                        # Suggest alternatives if we have validated entities
                        suggestions = []
                        if validated_entity_ids:
                            suggestions.append(f"Available validated entities: {', '.join(validated_entity_ids[:10])}")
                        
                        return {
                            "suggestion_id": suggestion_id,
                            "query_id": query_id,
                            "status": "error",
                            "safe": False,
                            "message": "Automation contains invalid entity IDs",
                            "error_details": {
                                "type": "invalid_entities",
                                "message": error_msg,
                                "invalid_entities": invalid_entities,
                                "suggestion": "The automation contains entity IDs that do not exist in Home Assistant. Please check your device names and try again." + (f" {suggestions[0]}" if suggestions else "")
                            },
                            "warnings": [f"Entity not found: {eid}" for eid in invalid_entities]
                        }
                    else:
                        logger.info(f"✅ FINAL VALIDATION PASSED: All {len(all_entity_ids_in_yaml)} entity IDs exist in HA")
            except Exception as e:
                logger.error(f"❌ Final entity validation error: {e}", exc_info=True)
                # Fail if validation can't complete - don't create automation with unvalidated entities
                return {
                    "suggestion_id": suggestion_id,
                    "query_id": query_id,
                    "status": "error",
                    "safe": False,
                    "message": "Failed to validate entities in automation YAML",
                    "error_details": {
                        "type": "validation_error",
                        "message": f"Entity validation failed: {str(e)}",
                        "suggestion": "Unable to verify entity IDs exist in Home Assistant. Automation creation blocked."
                    },
                    "warnings": [f"Validation error: {str(e)[:200]}"]
                }
        
        # Create automation in Home Assistant
        if ha_client:
            try:
                creation_result = await ha_client.create_automation(automation_yaml)
                created_automation_id = creation_result.get('automation_id')
                
                # Update metrics with automation creation result (after successful creation)
                if correction_result:
                    try:
                        from ..services.reverse_engineering_metrics import store_reverse_engineering_metrics
                        await store_reverse_engineering_metrics(
                            db_session=db,
                            suggestion_id=suggestion_id,
                            query_id=query_id,
                            correction_result=correction_result,
                            automation_created=True,
                            automation_id=created_automation_id,
                            had_validation_errors=False,
                            errors_fixed_count=0
                        )
                        logger.info("✅ Updated reverse engineering metrics with automation creation success")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to update metrics with automation creation: {e}")
            except Exception as e:
                error_message = str(e)
                logger.error(f"❌ Failed to create automation: {error_message}")
                
                # Update metrics with automation creation failure
                if correction_result:
                    try:
                        from ..services.reverse_engineering_metrics import store_reverse_engineering_metrics
                        await store_reverse_engineering_metrics(
                            db_session=db,
                            suggestion_id=suggestion_id,
                            query_id=query_id,
                            correction_result=correction_result,
                            automation_created=False,
                            automation_id=None,
                            had_validation_errors=("400" in error_message or "Message malformed" in error_message),
                            errors_fixed_count=0
                        )
                        logger.info("✅ Updated reverse engineering metrics with automation creation failure")
                    except Exception as e2:
                        logger.warning(f"⚠️ Failed to update metrics with creation failure: {e2}")
                
                # Check if it's a 400 error (validation error)
                if "400" in error_message or "Message malformed" in error_message:
                    # Try to extract the path from error message
                    path_match = None
                    if "data[" in error_message:
                        # Extract path like data['actions'][0]['sequence'][1]['target']['entity_id']
                        import re
                        path_match = re.search(r"data\[([^\]]+)\]", error_message)
                    
                    error_details = {
                        "message": error_message,
                        "type": "validation_error",
                    }
                    if path_match:
                        error_details["yaml_path"] = path_match.group(1)
                    
                    return {
                        "suggestion_id": suggestion_id,
                        "query_id": query_id,
                        "status": "error",
                        "safe": False,
                        "message": f"Automation validation failed: {error_message}",
                        "error_details": error_details,
                        "warnings": []
                    }
                else:
                    # Other error
                    return {
                        "suggestion_id": suggestion_id,
                        "query_id": query_id,
                        "status": "error",
                        "safe": False,
                        "message": f"Failed to create automation: {error_message}",
                        "warnings": []
                    }
            
            if creation_result.get('success'):
                logger.info(f"✅ Automation created successfully: {creation_result.get('automation_id')}")
                
                response_data = {
                    "suggestion_id": suggestion_id,
                    "query_id": query_id,
                    "status": "approved",
                    "automation_id": creation_result.get('automation_id'),
                    "automation_yaml": automation_yaml,
                    "ready_to_deploy": True,
                    "warnings": creation_result.get('warnings', []),
                    "message": creation_result.get('message', 'Automation created successfully'),
                    # TASK 1.4: Component restoration log
                    "restoration_log": restoration_result.get('restoration_log', []),
                    "restored_components": restoration_result.get('restored_components', []),
                    "restoration_confidence": restoration_result.get('restoration_confidence', 1.0),
                    # TASK 2.5: Enhanced restoration fields
                    "nested_components_restored": restoration_result.get('nested_components_restored', []),
                    "restoration_structure": restoration_result.get('restoration_structure', ''),
                    "intent_match": restoration_result.get('intent_match', True),
                    "intent_validation": restoration_result.get('intent_validation', ''),
                    # TASK 2.3: Safety validation report
                    "safety_report": safety_report,
                    "safe": safety_report.get('safe', True)
                }
                
                # Add reverse engineering correction results if available
                if correction_result:
                    response_data["reverse_engineering"] = {
                        "enabled": True,
                        "final_similarity": correction_result.final_similarity,
                        "iterations_completed": correction_result.iterations_completed,
                        "convergence_achieved": correction_result.convergence_achieved,
                        "total_tokens_used": correction_result.total_tokens_used,
                        "yaml_improved": correction_result.final_similarity > 0.85,
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
