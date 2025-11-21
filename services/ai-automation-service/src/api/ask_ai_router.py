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

import asyncio
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime
from typing import Any

import yaml as yaml_lib
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.device_intelligence_client import DeviceIntelligenceClient
from ..clients.ha_client import HomeAssistantClient
from ..config import settings
from ..database import get_db
from ..database.models import AskAIQuery as AskAIQueryModel
from ..database.models import ClarificationSessionDB
from ..services.automation.yaml_generation_service import (
    generate_automation_yaml,
    pre_validate_suggestion_for_yaml,
)
from ..entity_extraction import (
    EnhancedEntityExtractor,
    MultiModelEntityExtractor,
    extract_entities_from_query,
)
from ..guardrails.hf_guardrails import get_guardrail_checker
from ..llm.openai_client import OpenAIClient
from ..model_services.orchestrator import ModelOrchestrator
from ..model_services.soft_prompt_adapter import SoftPromptAdapter, get_soft_prompt_adapter
from ..prompt_building.entity_context_builder import EntityContextBuilder
from ..services.clarification import (
    AnswerValidator,
    ClarificationAnswer,
    ClarificationDetector,
    ClarificationSession,
    ConfidenceCalculator,
    QuestionGenerator,
)
from ..services.clarification.confidence_calibrator import ClarificationConfidenceCalibrator
from ..services.clarification.models import AmbiguitySeverity
from ..services.clarification.outcome_tracker import ClarificationOutcomeTracker
from ..services.component_detector import ComponentDetector
from ..services.entity_attribute_service import EntityAttributeService
from ..services.rag import RAGClient
from ..services.safety_validator import SafetyValidator
from ..services.service_container import ServiceContainer
from ..services.yaml_self_correction import YAMLSelfCorrectionService
from ..utils.capability_utils import format_capability_for_display, normalize_capability
from ..utils.fuzzy import fuzzy_match_with_context, fuzzy_score

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

# Constants for clarification retry logic
CLARIFICATION_RETRY_MAX_ATTEMPTS = 2
CLARIFICATION_RETRY_DELAY_SECONDS = 2
CLARIFICATION_SUGGESTION_TIMEOUT_SECONDS = 300.0  # Increased to 300s (5 minutes) to allow for longer OpenAI API calls


async def _update_model_comparison_metrics_on_approval(
    db: AsyncSession,
    suggestion_id: str,
    query_id: str | None,
    model_used: str,
    task_type: str = 'suggestion'
):
    """
    Update model comparison metrics when a suggestion is approved.
    
    Args:
        db: Database session
        suggestion_id: Suggestion ID
        query_id: Query ID (optional)
        model_used: Model name that generated the suggestion
        task_type: 'suggestion' or 'yaml'
    """
    try:
        from sqlalchemy import select

        from ..database.models import ModelComparisonMetrics

        # Find metrics record for this suggestion/query
        query_filter = select(ModelComparisonMetrics).where(
            ModelComparisonMetrics.task_type == task_type
        )

        if query_id:
            query_filter = query_filter.where(ModelComparisonMetrics.query_id == query_id)
        if suggestion_id:
            query_filter = query_filter.where(ModelComparisonMetrics.suggestion_id == suggestion_id)

        # Order by most recent
        query_filter = query_filter.order_by(ModelComparisonMetrics.created_at.desc()).limit(1)

        result = await db.execute(query_filter)
        metrics = result.scalar_one_or_none()

        if metrics:
            # Determine which model was used and update approval
            if metrics.model1_name == model_used:
                metrics.model1_approved = True
            elif metrics.model2_name == model_used:
                metrics.model2_approved = True

            await db.commit()
            logger.info(f"Updated model comparison metrics: {task_type} - {model_used} approved")
    except Exception as e:
        logger.warning(f"Failed to update model comparison metrics on approval: {e}")
        await db.rollback()


async def _update_model_comparison_metrics_on_yaml_validation(
    db: AsyncSession,
    suggestion_id: str,
    model_used: str,
    yaml_valid: bool
):
    """
    Update model comparison metrics when YAML is validated.
    
    Args:
        db: Database session
        suggestion_id: Suggestion ID
        model_used: Model name that generated the YAML
        yaml_valid: Whether YAML validation passed
    """
    try:
        from sqlalchemy import select

        from ..database.models import ModelComparisonMetrics

        # Find metrics record for this suggestion (YAML task)
        query = select(ModelComparisonMetrics).where(
            ModelComparisonMetrics.task_type == 'yaml',
            ModelComparisonMetrics.suggestion_id == suggestion_id
        ).order_by(ModelComparisonMetrics.created_at.desc()).limit(1)

        result = await db.execute(query)
        metrics = result.scalar_one_or_none()

        if metrics:
            # Determine which model was used and update validation
            if metrics.model1_name == model_used:
                metrics.model1_yaml_valid = yaml_valid
            elif metrics.model2_name == model_used:
                metrics.model2_yaml_valid = yaml_valid

            await db.commit()
            logger.info(f"Updated model comparison metrics: yaml - {model_used} validation={yaml_valid}")
    except Exception as e:
        logger.warning(f"Failed to update model comparison metrics on YAML validation: {e}")
        await db.rollback()

# Global device intelligence client and extractors

def _build_entity_validation_context_with_comprehensive_data(entities: list[dict[str, Any]], enriched_data: dict[str, dict[str, Any]] | None = None) -> str:
    """
    Build entity validation context with COMPREHENSIVE data from ALL sources.
    
    Uses enriched_data (comprehensive enrichment) when available, falls back to entities list.
    
    Args:
        entities: List of entity dictionaries (fallback if enriched_data not available)
        enriched_data: Comprehensive enriched data dictionary mapping entity_id to all available data
        
    Returns:
        Formatted string with ALL available entity information
    """
    from ..services.comprehensive_entity_enrichment import (
        format_comprehensive_enrichment_for_prompt,
    )

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


def _build_entity_validation_context_with_capabilities(entities: list[dict[str, Any]]) -> str:
    """Backwards compatibility wrapper."""
    return _build_entity_validation_context_with_comprehensive_data(entities, enriched_data=None)


def _get_ambiguity_id(amb: Any) -> str:
    """Safely get ambiguity ID from either Ambiguity object or dictionary."""
    if isinstance(amb, dict):
        return amb.get('id', '')
    return amb.id if hasattr(amb, 'id') else ''


def _get_ambiguity_type(amb: Any) -> str:
    """Safely get ambiguity type from either Ambiguity object or dictionary."""
    if isinstance(amb, dict):
        amb_type = amb.get('type', '')
        # Handle both string and enum value
        if isinstance(amb_type, str):
            return amb_type
        return amb_type.value if hasattr(amb_type, 'value') else str(amb_type)
    if hasattr(amb, 'type'):
        amb_type = amb.type
        return amb_type.value if hasattr(amb_type, 'value') else str(amb_type)
    return ''


def _get_ambiguity_context(amb: Any) -> dict[str, Any]:
    """Safely get ambiguity context from either Ambiguity object or dictionary."""
    if isinstance(amb, dict):
        return amb.get('context', {})
    return amb.context if hasattr(amb, 'context') else {}


def _get_temperature_for_model(model: str, desired_temperature: float = 0.1) -> float:
    """
    Get the appropriate temperature value for a given model.
    
    For GPT-4o models, use the desired temperature.
    
    Args:
        model: The model name (e.g., 'gpt-4o-mini', 'gpt-4o')
        desired_temperature: The desired temperature value (default: 0.1)
    
    Returns:
        The temperature value to use (desired_temperature for all GPT-4o models)
    """
    models_with_fixed_temperature = []  # No fixed-temperature models for GPT-4o
    if model in models_with_fixed_temperature:
        logger.debug(f"Using temperature=1.0 for {model} (model only supports default temperature)")
        return 1.0
    return desired_temperature

# Global device intelligence client and extractors
_device_intelligence_client: DeviceIntelligenceClient | None = None
_enhanced_extractor: EnhancedEntityExtractor | None = None
_multi_model_extractor: MultiModelEntityExtractor | None = None
_model_orchestrator: ModelOrchestrator | None = None
_self_correction_service: YAMLSelfCorrectionService | None = None
_soft_prompt_adapter_initialized = False
_guardrail_checker_initialized = False

def get_self_correction_service() -> YAMLSelfCorrectionService | None:
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
            openai_model=getattr(settings, 'entity_extraction_model', settings.openai_model)
        )
        # Initialize model orchestrator for containerized approach
        _model_orchestrator = ModelOrchestrator(
            ner_service_url=os.getenv("NER_SERVICE_URL", "http://ner-service:8031"),
            openai_service_url=os.getenv("OPENAI_SERVICE_URL", "http://openai-service:8020")
        )
    logger.info("Device Intelligence client set for Ask AI router")

def get_multi_model_extractor() -> MultiModelEntityExtractor | None:
    """Get multi-model extractor instance"""
    return _multi_model_extractor

def get_model_orchestrator() -> ModelOrchestrator | None:
    """Get model orchestrator instance"""
    return _model_orchestrator


def get_soft_prompt() -> SoftPromptAdapter | None:
    """Get cached soft prompt adapter when enabled."""
    global _soft_prompt_adapter_initialized

    if _soft_prompt_adapter_initialized:
        return getattr(get_soft_prompt, "_adapter", None)

    _soft_prompt_adapter_initialized = True

    if not getattr(settings, "soft_prompt_enabled", False):
        get_soft_prompt._adapter = None
        return None

    adapter = get_soft_prompt_adapter(settings.soft_prompt_model_dir)
    if adapter and adapter.is_ready:
        get_soft_prompt._adapter = adapter
        logger.info("Soft prompt fallback enabled with model %s", adapter.model_id)
    else:
        get_soft_prompt._adapter = None
        logger.info("Soft prompt fallback disabled - model not available")

    return get_soft_prompt._adapter


def reset_soft_prompt_adapter() -> None:
    """Clear cached soft prompt adapter so it will be reloaded on next access."""
    global _soft_prompt_adapter_initialized
    _soft_prompt_adapter_initialized = False
    if hasattr(get_soft_prompt, "_adapter"):
        get_soft_prompt._adapter = None


def reload_soft_prompt_adapter() -> SoftPromptAdapter | None:
    """Force reinitialization of the soft prompt adapter."""
    reset_soft_prompt_adapter()
    return get_soft_prompt()


def get_guardrail_checker_instance():
    """Initialise or return cached guardrail checker."""
    global _guardrail_checker_initialized

    if _guardrail_checker_initialized:
        return getattr(get_guardrail_checker_instance, "_checker", None)

    _guardrail_checker_initialized = True

    if not getattr(settings, "guardrail_enabled", False):
        get_guardrail_checker_instance._checker = None
        return None

    checker = get_guardrail_checker(
        settings.guardrail_model_name,
        settings.guardrail_threshold
    )
    if checker and checker.is_ready:
        get_guardrail_checker_instance._checker = checker
        logger.info(
            "Guardrail checks enabled with model %s",
            settings.guardrail_model_name
        )
    else:
        get_guardrail_checker_instance._checker = None
        logger.info("Guardrail checks disabled - model unavailable")

    return get_guardrail_checker_instance._checker


def reset_guardrail_checker() -> None:
    """Clear cached guardrail checker so it reloads with updated config."""
    global _guardrail_checker_initialized
    _guardrail_checker_initialized = False
    if hasattr(get_guardrail_checker_instance, "_checker"):
        get_guardrail_checker_instance._checker = None


def reload_guardrail_checker():
    """Force guardrail checker to reinitialize."""
    reset_guardrail_checker()
    return get_guardrail_checker_instance()

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
        ) from e


@router.get("/entities/search")
async def search_entities(
    domain: str | None = Query(None, description="Filter by domain (light, switch, sensor, etc.)"),
    search_term: str | None = Query(None, description="Search term to match against entity_id or friendly_name"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    ha_client: HomeAssistantClient = Depends(get_ha_client)
) -> list[dict[str, Any]]:
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
        ) from e


# Initialize clients (reassign global variables)
if settings.ha_url and settings.ha_token:
    try:
        ha_client = HomeAssistantClient(settings.ha_url, access_token=settings.ha_token)
        logger.info("✅ Home Assistant client initialized for Ask AI")
    except Exception as e:
        logger.error(f"❌ Failed to initialize HA client: {e}")

if settings.openai_api_key:
    try:
        openai_client = OpenAIClient(api_key=settings.openai_api_key, model=settings.openai_model)
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
    context: dict[str, Any] | None = Field(default=None, description="Additional context")
    conversation_history: list[dict[str, Any]] | None = Field(default=None, description="Conversation history for context")


class AskAIQueryResponse(BaseModel):
    """Response from Ask AI query"""
    query_id: str
    original_query: str
    parsed_intent: str
    extracted_entities: list[dict[str, Any]]
    suggestions: list[dict[str, Any]]
    confidence: float
    processing_time_ms: int
    created_at: str
    # NEW: Clarification fields
    clarification_needed: bool = False
    clarification_session_id: str | None = None
    questions: list[dict[str, Any]] | None = None
    message: str | None = None


class QueryRefinementRequest(BaseModel):
    """Request to refine query results"""
    refinement: str = Field(..., description="How to refine the results")
    include_context: bool = Field(default=True, description="Include original query context")


class QueryRefinementResponse(BaseModel):
    """Response from query refinement"""
    query_id: str
    refined_suggestions: list[dict[str, Any]]
    changes_made: list[str]
    confidence: float
    refinement_count: int


class ClarificationRequest(BaseModel):
    """Request to provide clarification answers"""
    session_id: str = Field(..., description="Clarification session ID")
    answers: list[dict[str, Any]] = Field(..., description="Answers to clarification questions")

class ClarificationResponse(BaseModel):
    """Response from clarification"""
    session_id: str
    confidence: float
    confidence_threshold: float
    clarification_complete: bool
    message: str
    suggestions: list[dict[str, Any]] | None = None
    questions: list[dict[str, Any]] | None = None  # If more questions needed
    previous_confidence: float | None = None  # Previous confidence before this round
    confidence_delta: float | None = None  # Change in confidence (positive = increase)
    confidence_summary: str | None = None  # Human-readable summary of what improved
    enriched_prompt: str | None = None  # User-friendly prompt showing all answers
    questions_and_answers: list[dict[str, Any]] | None = None  # Structured Q&A data


# ============================================================================
# Helper Functions
# ============================================================================

def _generate_confidence_summary(
    previous_confidence: float,
    current_confidence: float,
    confidence_delta: float | None,
    validated_answers: list[Any],
    session: Any,
    resolved_ambiguity_ids: set
) -> str | None:
    """
    Generate a human-readable summary of what contributed to confidence improvement.
    
    Args:
        previous_confidence: Confidence before this round
        current_confidence: Confidence after this round
        confidence_delta: Change in confidence
        validated_answers: Answers validated in this round
        session: Clarification session
        resolved_ambiguity_ids: Set of resolved ambiguity IDs
        
    Returns:
        Human-readable summary string or None
    """
    if confidence_delta is None or confidence_delta <= 0:
        return None

    summary_parts = []

    # Count critical and important questions answered
    critical_answered = 0
    important_answered = 0
    for answer in validated_answers:
        question = next((q for q in session.questions if q.id == answer.question_id), None)
        if question:
            if question.priority == 1:  # Critical
                critical_answered += 1
            elif question.priority == 2:  # Important
                important_answered += 1

    # Count resolved ambiguities by severity
    critical_resolved = 0
    important_resolved = 0
    for amb in session.ambiguities:
        amb_id = _get_ambiguity_id(amb)
        if amb_id in resolved_ambiguity_ids:
            # Get severity safely
            if isinstance(amb, dict):
                severity = amb.get('severity', '')
            else:
                severity = amb.severity.value if hasattr(amb.severity, 'value') else str(amb.severity) if hasattr(amb, 'severity') else ''

            if severity == "critical":
                critical_resolved += 1
            elif severity == "important":
                important_resolved += 1

    # Build summary based on what improved
    if critical_resolved > 0:
        summary_parts.append(f"Resolved {critical_resolved} critical ambiguities")
    if important_resolved > 0:
        summary_parts.append(f"Resolved {important_resolved} important ambiguities")

    # Check answer quality
    high_quality_answers = sum(1 for a in validated_answers if a.confidence > 0.8)
    if high_quality_answers > 0:
        summary_parts.append(f"Provided {high_quality_answers} high-quality answer{'s' if high_quality_answers > 1 else ''}")

    # If no specific improvements, use generic message
    if not summary_parts:
        summary_parts.append("Your answers helped clarify the automation requirements")

    # Add confidence change
    delta_percent = int(confidence_delta * 100)
    if delta_percent > 0:
        summary_parts.append(f"Confidence increased by {delta_percent}%")

    return " • ".join(summary_parts)

# Global clarification service instances
_clarification_detector: ClarificationDetector | None = None
_question_generator: QuestionGenerator | None = None
_answer_validator: AnswerValidator | None = None
_confidence_calculator: ConfidenceCalculator | None = None
_clarification_sessions: dict[str, ClarificationSession] = {}  # In-memory storage (TODO: persist to DB)

async def get_clarification_services(db: AsyncSession = None):
    """
    Get or initialize clarification services.
    
    Args:
        db: Optional database session for RAG client initialization.
            If provided and RAG is enabled, will create RAG client for semantic understanding.
    """
    global _clarification_detector, _question_generator, _answer_validator, _confidence_calculator

    if _clarification_detector is None:
        # Try to initialize with RAG client if database session is available
        rag_client = None
        if db:
            try:
                openvino_url = os.getenv("OPENVINO_SERVICE_URL", "http://openvino-service:8019")
                rag_client = RAGClient(
                    openvino_service_url=openvino_url,
                    db_session=db
                )
                logger.info("✅ RAG client initialized for ClarificationDetector (semantic understanding enabled)")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize RAG client, falling back to hardcoded rules: {e}")

        _clarification_detector = ClarificationDetector(rag_client=rag_client)
    if _question_generator is None and openai_client:
        _question_generator = QuestionGenerator(openai_client)
    if _answer_validator is None:
        _answer_validator = AnswerValidator()
    if _confidence_calculator is None:
        # Initialize confidence calculator with RAG client for historical success checking
        rag_client_for_confidence = None
        if db:
            try:
                openvino_url = os.getenv("OPENVINO_SERVICE_URL", "http://openvino-service:8019")
                rag_client_for_confidence = RAGClient(
                    openvino_service_url=openvino_url,
                    db_session=db
                )
                logger.info("✅ RAG client initialized for ConfidenceCalculator (historical learning enabled)")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize RAG client for confidence calculator: {e}")
        # Initialize calibrator if calibration is enabled
        calibrator = None
        if getattr(settings, "clarification_calibration_enabled", True):
            try:
                calibrator = ClarificationConfidenceCalibrator()
                # Try to load existing model
                calibrator.load()
                logger.info("✅ Clarification confidence calibrator initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize calibrator: {e}")

        _confidence_calculator = ConfidenceCalculator(
            default_threshold=0.85,
            rag_client=rag_client_for_confidence,
            calibrator=calibrator,
            calibration_enabled=getattr(settings, "clarification_calibration_enabled", True)
        )

    return _clarification_detector, _question_generator, _answer_validator, _confidence_calculator


async def _get_rag_client(db: AsyncSession) -> RAGClient | None:
    """
    Get or initialize RAG client for semantic knowledge storage and retrieval.
    
    Args:
        db: Database session for RAG client initialization
        
    Returns:
        RAG client instance or None if initialization fails
    """
    try:
        openvino_url = os.getenv("OPENVINO_SERVICE_URL", "http://openvino-service:8019")
        rag_client = RAGClient(
            openvino_service_url=openvino_url,
            db_session=db
        )
        return rag_client
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize RAG client: {e}")
        return None

async def expand_group_entities_to_members(
    entity_ids: list[str],
    ha_client: HomeAssistantClient | None,
    entity_validator: Any | None = None
) -> list[str]:
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
    entity_ids: list[str],
    ha_client: HomeAssistantClient | None,
    use_ensemble: bool = True,
    query_context: str | None = None,
    available_entities: list[dict[str, Any]] | None = None
) -> dict[str, bool]:
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
        return dict.fromkeys(entity_ids, False) if entity_ids else {}

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


def detect_device_types_fuzzy(
    text: str,
    device_type_aliases: dict[str, list[str]] | None = None,
    threshold: float | None = None
) -> list[tuple[str, float]]:
    """
    Detect device types in text using fuzzy matching with rapidfuzz.
    
    Uses rapidfuzz process.extract() for efficient batch matching that handles:
    - Typos: "wled" vs "wled" 
    - Variations: "philips hue" vs "hue"
    - Partial matches: "led strip" contains "led"
    - Word order: "hue philips" vs "philips hue"
    
    Args:
        text: Text to search for device types
        device_type_aliases: Optional dict mapping device_type -> list of aliases.
                           If None, uses default device type aliases.
        threshold: Minimum fuzzy match score (0.0-1.0) to consider a match.
                  If None, uses settings.fuzzy_matching_threshold.
    
    Returns:
        List of tuples: (device_type, confidence_score) sorted by confidence (highest first)
    
    Example:
        >>> detect_device_types_fuzzy("I want to control the wled in the office")
        [('wled', 0.95)]
        >>> detect_device_types_fuzzy("turn on philips hue lights")
        [('hue', 0.92)]
    """
    from ..utils.fuzzy import fuzzy_match_best, RAPIDFUZZ_AVAILABLE
    
    if not text:
        return []
    
    # Use default device type aliases if not provided
    if device_type_aliases is None:
        device_type_aliases = {
            'wled': ['wled', 'led', 'leds'],
            'hue': ['hue', 'philips hue'],
            'sonoff': ['sonoff', 'tasmota'],
            'tuya': ['tuya', 'smart life'],
            'tp-link': ['tp-link', 'kasa', 'tplink']
        }
    
    # Use configured threshold if not provided
    if threshold is None:
        threshold = settings.fuzzy_matching_threshold
    
    matches = []
    
    if RAPIDFUZZ_AVAILABLE:
        # Build flat list of all aliases with device type mapping
        all_aliases = []
        alias_to_device_type = {}
        
        for device_type, aliases in device_type_aliases.items():
            for alias in aliases:
                all_aliases.append(alias)
                alias_to_device_type[alias] = device_type
        
        # Use process.extract() for efficient batch matching
        # This is faster than manual loops for large alias lists
        alias_matches = fuzzy_match_best(
            text,
            all_aliases,
            threshold=threshold,
            limit=len(all_aliases)  # Get all matches above threshold
        )
        
        # Group matches by device type and keep best score per device type
        device_type_scores = {}
        for alias, score in alias_matches:
            device_type = alias_to_device_type[alias]
            if device_type not in device_type_scores or score > device_type_scores[device_type]:
                device_type_scores[device_type] = score
        
        # Convert to list of tuples and sort by score
        matches = [(device_type, score) for device_type, score in device_type_scores.items()]
        matches.sort(key=lambda x: x[1], reverse=True)
        
        if matches:
            logger.debug(f"🔍 Fuzzy device type matches: {[(dt, f'{s:.2f}') for dt, s in matches]}")
    else:
        # Fallback to simple substring matching if rapidfuzz unavailable
        text_lower = text.lower()
        for device_type, aliases in device_type_aliases.items():
            for alias in aliases:
                if alias in text_lower:
                    matches.append((device_type, 0.8))  # Lower confidence for substring match
                    break  # Only one match per device type in fallback
    
    return matches


async def map_devices_to_entities(
    devices_involved: list[str],
    enriched_data: dict[str, dict[str, Any]],
    ha_client: HomeAssistantClient | None = None,
    fuzzy_match: bool = True,
    clarification_context: dict[str, Any] | None = None,
    query_location: str | None = None
) -> dict[str, str]:
    """
    Map device friendly names to entity IDs from enriched data.
    
    Context-aware (2025 pattern): Uses clarification context and location hints for better matching.
    
    Optimized for single-home local solutions:
    - Deduplicates redundant mappings (multiple friendly names -> same entity_id)
    - Prioritizes exact matches over fuzzy matches
    - Uses area context for better matching in single-home scenarios
    - Consolidates devices_involved to unique entity mappings
    - Uses clarification context to resolve generic device names (e.g., "led" -> "office WLED")
    
    IMPORTANT: Only includes entity IDs that actually exist in Home Assistant.
    
    Args:
        devices_involved: List of device friendly names from LLM suggestion
        enriched_data: Dictionary mapping entity_id to enriched entity data
        ha_client: Optional HA client for verifying entities exist
        fuzzy_match: If True, use fuzzy matching for partial matches
        clarification_context: Optional clarification Q&A context for context-aware matching
        query_location: Optional location hint (e.g., "office") for location-aware matching
        
    Returns:
        Dictionary mapping device_name -> entity_id (only verified entities, deduplicated)
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
        # Fallback: Use EntityAttributeService to enrich entities if we have a client
        if ha_client:
            logger.info(f"🔄 Attempting to enrich entities using EntityAttributeService for {len(devices_involved)} devices...")
            try:
                # Use EntityAttributeService to get proper friendly names from Entity Registry
                attribute_service = EntityAttributeService(ha_client)
                # Get all states from HA first to get entity IDs
                session = await ha_client._get_session()
                url = f"{ha_client.ha_url}/api/states"
                async with session.get(url) as response:
                    if response.status == 200:
                        all_states = await response.json()
                        # Extract entity IDs
                        entity_ids = [state.get('entity_id') for state in all_states if isinstance(state, dict) and state.get('entity_id') and '.' in state.get('entity_id', '')]
                        # Enrich using EntityAttributeService (uses Entity Registry)
                        enriched_results = await attribute_service.enrich_multiple_entities(entity_ids)
                        # Build enriched_data from enriched results
                        enriched_data = {}
                        for entity_id, enriched in enriched_results:
                            if enriched:
                                enriched_data[entity_id] = enriched
                        logger.info(f"✅ Built enriched_data from {len(enriched_data)} HA entities using EntityAttributeService (Entity Registry)")
                    else:
                        logger.warning(f"⚠️ Failed to query HA states: HTTP {response.status}")
            except Exception as e:
                logger.error(f"❌ Error enriching entities with EntityAttributeService: {e}", exc_info=True)

        # If still no enriched_data, return empty
        if not enriched_data:
            logger.error("❌ Cannot map devices: no enriched_data and HA query failed")
            return {}

    for device_name in devices_involved:
        mapped = False
        device_name_lower = device_name.lower()
        matched_entity_id = None
        match_quality = 0  # 3=exact, 2=fuzzy, 1=domain

        # Strategy 1: Exact match by friendly_name or device_name (highest priority)
        for entity_id, enriched in enriched_data.items():
            friendly_name = enriched.get('friendly_name', '')
            device_name_from_enriched = enriched.get('device_name', '')  # Fallback to device name
            # Check friendly_name first, then device_name if friendly_name is empty
            name_to_check = friendly_name if friendly_name else device_name_from_enriched
            if name_to_check and name_to_check.lower() == device_name_lower:
                # Add area check for exact matches - boost priority for area matches
                area_name = (enriched.get('area_name') or '').lower()
                if area_name and device_name_lower in area_name:
                    # Boost priority for area matches (single-home optimization)
                    match_quality = 4  # Higher than regular exact match
                    matched_entity_id = entity_id
                    name_type = 'friendly_name' if friendly_name else 'device_name'
                    logger.debug(f"✅ Mapped device '{device_name}' -> entity_id '{entity_id}' (exact match by {name_type} with area match)")
                    break
                else:
                    matched_entity_id = entity_id
                    match_quality = 3
                    name_type = 'friendly_name' if friendly_name else 'device_name'
                    logger.debug(f"✅ Mapped device '{device_name}' -> entity_id '{entity_id}' (exact match by {name_type})")
                    break

        # Strategy 2: Fuzzy matching with rapidfuzz - context-aware for 2025
        if not matched_entity_id and fuzzy_match and settings.fuzzy_matching_enabled:
            best_fuzzy_match = None
            best_fuzzy_score = 0.0

            # Extract location and device hints from clarification context (2025: context-aware)
            context_location = query_location
            context_device_hints = set()
            if clarification_context:
                # Extract location from Q&A answers
                qa_list = clarification_context.get('questions_and_answers', [])
                for qa in qa_list:
                    answer_text = qa.get('answer', '').lower()
                    # Look for location mentions (office, living room, etc.)
                    if not context_location:
                        # Simple location extraction (can be enhanced)
                        location_keywords = ['office', 'living room', 'bedroom', 'kitchen', 'bathroom', 'garage']
                        for loc in location_keywords:
                            if loc in answer_text:
                                context_location = loc
                                break
                    
                    # Extract device type hints (WLED, Hue, etc.)
                    if device_name_lower in ['led', 'light']:
                        # Look for specific device types in answers
                        if 'wled' in answer_text:
                            context_device_hints.add('wled')
                        if 'hue' in answer_text:
                            context_device_hints.add('hue')

            for entity_id, enriched in enriched_data.items():
                friendly_name = enriched.get('friendly_name', '')
                device_name_from_enriched = enriched.get('device_name', '')  # Fallback to device name
                # Use friendly_name if available, otherwise use device_name
                name_to_check = friendly_name if friendly_name else device_name_from_enriched
                if not name_to_check:
                    continue
                entity_name_part = entity_id.split('.')[-1].lower() if '.' in entity_id else ''
                area_name = (enriched.get('area_name') or '').lower()

                # Build context bonuses for enhanced scoring
                context_bonuses = {}
                
                # Area context bonus for single-home scenarios (increased from 0.1 to 0.3)
                if area_name and device_name_lower in area_name:
                    context_bonuses['area'] = 0.3  # Increased for single-home optimization
                
                # 2025 ENHANCEMENT: Context-aware location matching
                if context_location:
                    location_lower = context_location.lower()
                    if location_lower in area_name or location_lower in name_to_check.lower():
                        context_bonuses['location'] = 0.2  # Strong location match bonus
                        logger.debug(f"📍 Location match bonus: '{device_name_lower}' matches location '{context_location}' for entity '{entity_id}'")
                
                # 2025 ENHANCEMENT: Context-aware device type matching
                if context_device_hints:
                    for hint in context_device_hints:
                        if hint in name_to_check.lower() or hint in entity_name_part:
                            context_bonuses['device_type'] = 0.2  # Strong device type match bonus
                            logger.debug(f"🔧 Device type match bonus: '{device_name_lower}' matches hint '{hint}' for entity '{entity_id}'")
                            break
                
                # Add area + device type combination bonus (single-home optimization)
                if context_location and context_device_hints:
                    location_lower = context_location.lower()
                    if location_lower in area_name:
                        for hint in context_device_hints:
                            if hint in entity_name_part or hint in name_to_check.lower():
                                context_bonuses['area_device_type'] = 0.4  # Strong combination match
                                logger.debug(f"🎯 Area+Device type combination bonus: '{device_name_lower}' ({hint}) in '{location_lower}' area -> '{entity_id}'")
                                break

                # Use fuzzy_match_with_context() for base similarity + context bonuses
                # Check both friendly_name and entity_name_part for better matching
                score1 = fuzzy_match_with_context(
                    device_name,
                    name_to_check,
                    context_bonuses if context_bonuses else None
                )
                score2 = fuzzy_match_with_context(
                    device_name,
                    entity_name_part,
                    context_bonuses if context_bonuses else None
                ) if entity_name_part else 0.0
                
                # Use the better of the two scores
                score = max(score1, score2)

                if score > best_fuzzy_score:
                    best_fuzzy_score = score
                    best_fuzzy_match = entity_id

            if best_fuzzy_match and best_fuzzy_score >= settings.fuzzy_matching_threshold:
                matched_entity_id = best_fuzzy_match
                match_quality = 2
                # Determine which name type was used for the match
                best_enriched = enriched_data.get(best_fuzzy_match, {})
                best_friendly_name = best_enriched.get('friendly_name', '')
                name_type = 'friendly_name' if best_friendly_name else 'device_name'
                logger.debug(f"✅ Mapped device '{device_name}' -> entity_id '{matched_entity_id}' (fuzzy match by {name_type}, score: {best_fuzzy_score:.2f})")

        # Strategy 3: Match by device type/integration (e.g., "WLED", "Hue") - NEW for 2025
        if not matched_entity_id and fuzzy_match:
            # Device type aliases mapping (common integration types)
            device_type_aliases = {
                'wled': ['wled', 'led', 'leds'],
                'hue': ['hue', 'philips hue'],
                'sonoff': ['sonoff', 'tasmota'],
                'tuya': ['tuya', 'smart life'],
                'tp-link': ['tp-link', 'kasa', 'tplink']
            }
            
            # Check if device_name matches any device type alias
            matching_device_types = []
            for device_type, aliases in device_type_aliases.items():
                if device_name_lower in aliases or any(alias in device_name_lower for alias in aliases):
                    matching_device_types.append(device_type)
            
            if matching_device_types:
                # Try to find entities matching this device type in the location context
                best_match_score = 0
                best_match_entity_id = None
                
                for entity_id, enriched in enriched_data.items():
                    entity_name_part = entity_id.split('.')[-1].lower() if '.' in entity_id else ''
                    platform = (enriched.get('platform') or '').lower()
                    integration = (enriched.get('integration') or '').lower()
                    area_name = (enriched.get('area_name') or '').lower()
                    
                    score = 0
                    
                    # Check if entity matches device type (platform, integration, or entity name)
                    for device_type in matching_device_types:
                        if device_type in entity_name_part:
                            score += 3  # Strong match: entity name contains device type
                        if platform and device_type in platform:
                            score += 2  # Strong match: platform matches
                        if integration and device_type in integration:
                            score += 2  # Strong match: integration matches
                    
                    # Location context bonus: prioritize entities in query_location (increased from +2 to +4)
                    if query_location:
                        location_lower = query_location.lower()
                        if location_lower in area_name or location_lower in entity_name_part:
                            score += 4  # Strong location match bonus (increased for single-home optimization)
                            logger.debug(f"📍 Device type + location match: '{device_name}' ({matching_device_types}) in '{query_location}' -> '{entity_id}'")
                    
                    # Add entity name pattern matching (e.g., "office" in entity_id when area is "office")
                    if query_location:
                        location_lower = query_location.lower()
                        if location_lower in entity_name_part:
                            score += 2  # Additional bonus for location in entity name
                            logger.debug(f"📍 Entity name pattern match: '{location_lower}' in entity_id '{entity_id}'")
                    
                    if score > best_match_score:
                        best_match_score = score
                        best_match_entity_id = entity_id
                
                if best_match_entity_id and best_match_score > 0:
                    matched_entity_id = best_match_entity_id
                    match_quality = 2 if best_match_score >= 3 else 1  # Quality 2 for strong matches, 1 for weak
                    logger.info(f"✅ Mapped device '{device_name}' ({matching_device_types}) -> entity_id '{matched_entity_id}' (device type match, score: {best_match_score})")
        
        # Strategy 4: Match by domain name (lowest priority)
        if not matched_entity_id and fuzzy_match:
            for entity_id, enriched in enriched_data.items():
                domain = entity_id.split('.')[0].lower() if '.' in entity_id else ''
                if domain == device_name_lower:
                    matched_entity_id = entity_id
                    match_quality = 1
                    logger.debug(f"✅ Mapped device '{device_name}' -> entity_id '{entity_id}' (domain match)")
                    break

        # Store mapping if found, but only keep best device name for each entity_id
        if matched_entity_id:
            existing_quality = entity_id_to_best_device_name.get(matched_entity_id, {}).get('quality', 0)
            if match_quality > existing_quality:
                # Replace existing mapping with better match
                if matched_entity_id in entity_id_to_best_device_name:
                    old_device_name = entity_id_to_best_device_name[matched_entity_id]['device_name']
                    logger.debug(f"🔄 Replacing '{old_device_name}' -> '{device_name}' for entity_id '{matched_entity_id}' (better match quality)")
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
                logger.debug(f"📋 Duplicate mapping: '{device_name}' -> '{matched_entity_id}' (same quality as existing)")
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
                invalid_entities.append(f"{device_name} -> {entity_id}")
                logger.warning(f"❌ Entity {entity_id} (mapped from '{device_name}') does NOT exist in HA - removed from validated_entities")

        if invalid_entities:
            logger.warning(f"⚠️ Removed {len(invalid_entities)} invalid entity mappings: {', '.join(invalid_entities[:5])}")

        validated_entities = verified_validated_entities
        logger.info(f"✅ Verified {len(validated_entities)}/{len(unique_entity_ids)} unique entities exist in HA")

    # Log consolidation stats
    unique_entity_count = len(set(validated_entities.values()))
    if len(validated_entities) > unique_entity_count:
        logger.info(
            f"🔄 Consolidated {len(devices_involved)} devices -> {unique_entity_count} unique entities "
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
                    # Extract entity IDs and enrich using EntityAttributeService (uses Entity Registry)
                    entity_ids = [state.get('entity_id') for state in all_states if isinstance(state, dict) and state.get('entity_id') and '.' in state.get('entity_id', '')]
                    # Use EntityAttributeService to get proper friendly names from Entity Registry
                    attribute_service = EntityAttributeService(ha_client)
                    enriched_results = await attribute_service.enrich_multiple_entities(entity_ids)
                    # Build enriched_data from enriched results
                    ha_enriched_data = {}
                    for entity_id, enriched in enriched_results:
                        if enriched:
                            ha_enriched_data[entity_id] = enriched

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
                                    logger.info(f"✅ Mapped unmapped device '{device_name}' -> {best_match} (score: {best_score})")
                                else:
                                    logger.warning(f"⚠️ Best match {best_match} for '{device_name}' does not exist in HA")
                            else:
                                validated_entities[device_name] = best_match
                                matched_entity_ids.add(best_match)  # Mark as used
                                logger.info(f"✅ Mapped unmapped device '{device_name}' -> {best_match} (score: {best_score}, unverified)")

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
    devices_involved: list[str],
    enriched_data: dict[str, dict[str, Any]] | None = None,
    clarification_context: dict[str, Any] | None = None
) -> list[str]:
    """
    Pre-consolidate device names by removing generic/redundant terms BEFORE entity mapping.
    
    Context-aware (2025 pattern): Uses clarification context to preserve terms mentioned by user.
    
    This handles cases where OpenAI includes:
    - Generic domain names ("light", "switch")
    - Device type names ("wled", "hue")  
    - Area-only references that don't map to actual entities
    - Very short/generic terms (< 3 chars)
    
    Args:
        devices_involved: Original list of device names from OpenAI
        enriched_data: Optional enriched entity data for better filtering
        clarification_context: Optional clarification Q&A context to preserve user-mentioned terms
        
    Returns:
        Filtered list with generic/redundant terms removed (but preserves context-relevant terms)
    """
    if not devices_involved:
        return devices_involved

    # Generic terms to remove (domain names, very short terms)
    # NOTE: Removed 'wled', 'hue' - they're specific device integration types users commonly reference
    # Keep truly generic domain-level terms like 'light', 'switch', etc.
    generic_terms = {'light', 'switch', 'sensor', 'binary_sensor', 'climate', 'cover',
                     'fan', 'lock', 'mqtt', 'zigbee', 'zwave'}

    # Extract user-mentioned terms from clarification context (2025: context-aware filtering)
    user_mentioned_terms = set()
    if clarification_context:
        # Check Q&A answers for device mentions
        qa_list = clarification_context.get('questions_and_answers', [])
        for qa in qa_list:
            answer_text = qa.get('answer', '').lower()
            # Extract potential device names from answers
            # Look for terms that match devices_involved
            for device in devices_involved:
                device_lower = device.lower()
                if device_lower in answer_text or answer_text.find(device_lower) != -1:
                    user_mentioned_terms.add(device_lower)
                    logger.debug(f"🔍 Preserving '{device}' - mentioned in clarification: '{answer_text[:50]}...'")
        
        # Also check original query (preserve terms mentioned by user in their original request)
        original_query = clarification_context.get('original_query', '').lower()
        for device in devices_involved:
            device_lower = device.lower()
            if device_lower in original_query:
                user_mentioned_terms.add(device_lower)
                logger.debug(f"🔍 Preserving '{device}' - mentioned in original query: '{original_query[:100]}...'")

    filtered = []
    removed_terms = []

    for device_name in devices_involved:
        device_lower = device_name.lower().strip()

        # Skip empty or very short terms
        if len(device_lower) < 3:
            removed_terms.append(device_name)
            continue

        # CONTEXT-AWARE: Don't remove terms mentioned by user in clarifications (2025 pattern)
        if device_lower in user_mentioned_terms:
            filtered.append(device_name)
            logger.debug(f"✅ Preserved '{device_name}' - user mentioned in clarification context")
            continue

        # Skip generic domain/integration terms (unless user mentioned them)
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
    devices_involved: list[str],
    validated_entities: dict[str, str]
) -> list[str]:
    """
    Consolidate devices_involved array by removing redundant device names that map to the same entity.
    
    Optimized for single-home local solutions:
    - Removes duplicate device names that map to the same entity_id
    - Keeps the most specific/descriptive device name for each unique entity
    - Preserves order while deduplicating
    
    Args:
        devices_involved: Original list of device friendly names
        validated_entities: Dictionary mapping device_name -> entity_id
        
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
                    f"-> '{best_name}' for entity_id '{entity_id}'"
                )
            else:
                consolidated.append(device_name)
            entity_ids_seen.add(entity_id)
        elif entity_id not in validated_entities:
            # Keep unmapped devices (they might be groups or areas)
            consolidated.append(device_name)

    if len(consolidated) < len(devices_involved):
        logger.info(
            f"🔄 Consolidated devices_involved: {len(devices_involved)} -> {len(consolidated)} "
            f"({len(devices_involved) - len(consolidated)} redundant entries removed)"
        )

    return consolidated


def _is_entity_id(mention: str) -> bool:
    """
    Check if a string is an entity ID format (domain.entity_name).
    
    Args:
        mention: String to check
        
    Returns:
        True if the string looks like an entity ID
    """
    if not mention or not isinstance(mention, str):
        return False
    # Entity IDs follow pattern: domain.entity_name
    # Must contain a dot and have at least domain and entity parts
    parts = mention.split('.')
    return len(parts) == 2 and len(parts[0]) > 0 and len(parts[1]) > 0


def extract_device_mentions_from_text(
    text: str,
    validated_entities: dict[str, str],
    enriched_data: dict[str, dict[str, Any]] | None = None
) -> dict[str, str]:
    """
    Extract device mentions from text and map them to entity IDs.
    
    Filters out entity IDs from being used as mention keys to prevent
    entity IDs from appearing as friendly names in the UI.
    
    Args:
        text: Text to scan (description, trigger_summary, action_summary)
        validated_entities: Dictionary mapping friendly_name -> entity_id
        enriched_data: Optional enriched entity data for fuzzy matching
        
    Returns:
        Dictionary mapping mention -> entity_id (no entity IDs as keys)
    """
    if not text:
        return {}

    mentions = {}
    text_lower = text.lower()

    # Extract mentions from validated_entities
    for friendly_name, entity_id in validated_entities.items():
        # Skip if friendly_name is actually an entity ID (prevents entity IDs as keys)
        if _is_entity_id(friendly_name):
            logger.debug(f"⏭️ Skipping entity ID '{friendly_name}' from validated_entities (not a friendly name)")
            continue

        friendly_name_lower = friendly_name.lower()
        # Check if friendly name appears in text (word boundary matching)
        import re
        pattern = r'\b' + re.escape(friendly_name_lower) + r'\b'
        if re.search(pattern, text_lower):
            mentions[friendly_name] = entity_id
            logger.debug(f"🔍 Found mention '{friendly_name}' in text -> {entity_id}")

        # Also check for partial matches (e.g., "wled" matches "WLED" or "wled strip")
        if friendly_name_lower in text_lower or text_lower in friendly_name_lower:
            if friendly_name not in mentions:
                mentions[friendly_name] = entity_id
                logger.debug(f"🔍 Found partial mention '{friendly_name}' in text -> {entity_id}")

    # If enriched_data available, also check entity names and domains
    if enriched_data:
        for entity_id, enriched in enriched_data.items():
            friendly_name = enriched.get('friendly_name', '')
            if not friendly_name:
                continue
            friendly_name = friendly_name.lower()
            domain = entity_id.split('.')[0].lower() if '.' in entity_id else ''
            entity_name = entity_id.split('.')[-1].lower() if '.' in entity_id else ''

            # Check domain matches (e.g., "wled" text matches light entities with "wled" in the name)
            # Skip if domain looks like an entity ID (shouldn't happen, but defensive)
            if domain and domain in text_lower and len(domain) >= 3:
                if domain not in [m.lower() for m in mentions] and not _is_entity_id(domain):
                    mentions[domain] = entity_id
                    logger.debug(f"🔍 Found domain mention '{domain}' in text -> {entity_id}")

            # Check entity name matches
            # Skip if entity_name looks like an entity ID (defensive check)
            if entity_name and entity_name in text_lower:
                if entity_name not in [m.lower() for m in mentions] and not _is_entity_id(entity_name):
                    mentions[entity_name] = entity_id
                    logger.debug(f"🔍 Found entity name mention '{entity_name}' in text -> {entity_id}")

    return mentions


async def enhance_suggestion_with_entity_ids(
    suggestion: dict[str, Any],
    validated_entities: dict[str, str],
    enriched_data: dict[str, dict[str, Any]] | None = None,
    ha_client: HomeAssistantClient | None = None
) -> dict[str, Any]:
    """
    Enhance suggestion by adding entity IDs directly.
    
    Adds:
    - entity_ids_used: List of actual entity IDs
    - entity_id_annotations: Detailed mapping with context
    - device_mentions: Maps description terms -> entity IDs
    
    Args:
        suggestion: Suggestion dictionary
        validated_entities: Mapping friendly_name -> entity_id
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
        # Get actual friendly name from enriched_data if available (from Entity Registry)
        actual_friendly_name = friendly_name  # Default to user's query term
        if enriched_data and entity_id in enriched_data:
            enriched = enriched_data[entity_id]
            # Use the actual friendly name from Home Assistant's entity registry
            ha_friendly_name = enriched.get('friendly_name', '')
            if ha_friendly_name and ha_friendly_name != entity_id:
                actual_friendly_name = ha_friendly_name

        entity_id_annotations[friendly_name] = {
            'entity_id': entity_id,
            'domain': entity_id.split('.')[0] if '.' in entity_id else '',
            'friendly_name': actual_friendly_name,  # Include actual friendly name from HA
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
    # Ensure validated_entities is preserved (required for approval)
    enhanced['validated_entities'] = validated_entities

    logger.info(f"✅ Enhanced suggestion with {len(entity_ids_used)} entity IDs and {len(device_mentions)} device mentions")

    return enhanced


def deduplicate_entity_mapping(entity_mapping: dict[str, str]) -> dict[str, str]:
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
                f"⚠️ Duplicate entity mapping: '{device_name}' -> {entity_id} "
                f"(already mapped as '{seen_entities[entity_id]}')"
            )

    if len(deduplicated) < len(entity_mapping):
        logger.info(
            f"✅ Deduplicated entities: {len(deduplicated)} unique from {len(entity_mapping)} total "
            f"({len(entity_mapping) - len(deduplicated)} duplicates removed)"
        )

    return deduplicated


# YAML generation functions moved to services/automation/yaml_generation_service.py
# Functions: generate_automation_yaml, pre_validate_suggestion_for_yaml, build_suggestion_specific_entity_mapping


async def simplify_query_for_test(suggestion: dict[str, Any], openai_client) -> str:
    """
    Simplify automation description to test core behavior using AI.
    
    Uses OpenAI to intelligently extract just the core action without conditions.
    
    Examples:
    - "Flash office lights every 30 seconds only after 5pm"
      -> "Flash the office lights"
    
    - "Turn on bedroom lights when door opens after sunset"
      -> "Turn on the bedroom lights when door opens"
    
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
    logger.info(" About to build prompt")

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
        logger.info(" About to call OpenAI API")
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
            max_completion_tokens=60,     # Short output - just the command (use max_completion_tokens for newer models)
            top_p=0.9         # Nucleus sampling for slight creativity while staying focused
        )
        logger.info(" Got OpenAI response")

        simplified = response.choices[0].message.content.strip()
        logger.info(f"Simplified '{description}' -> '{simplified}'")
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


async def extract_entities_with_ha(query: str) -> list[dict[str, Any]]:
    """
    Extract entities from query using multi-model approach.
    
    Strategy:
    1. Multi-Model Extractor (NER -> OpenAI -> Pattern) - 90% of queries
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
            logger.info("🔍 Using multi-model entity extraction (NER -> OpenAI -> Pattern)")
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


async def resolve_entities_to_specific_devices(
    entities: list[dict[str, Any]],
    ha_client: HomeAssistantClient | None = None
) -> list[dict[str, Any]]:
    """
    Resolve generic device entities to specific device names by querying Home Assistant.
    
    This function expands generic device types (e.g., "hue lights") to specific devices
    (e.g., "Office Front Left", "Office Front Right") by:
    1. Extracting area/location from entities
    2. Extracting device domain/type from entities
    3. Querying HA for all devices in that area matching the domain
    4. Adding specific device names to entities list
    
    This is called BEFORE ambiguity detection so users can see specific devices in clarification prompts.
    
    Args:
        entities: List of extracted entities (may include generic device types)
        ha_client: Optional Home Assistant client for querying devices
        
    Returns:
        Updated entities list with specific device information added
    """
    if not ha_client or not entities:
        return entities

    # Extract location and device type from entities
    mentioned_locations = []
    mentioned_domains = set()
    device_entities = []

    for entity in entities:
        entity_type = entity.get('type', '')
        entity_name = entity.get('name', '').lower()

        if entity_type == 'area':
            mentioned_locations.append(entity.get('name', ''))
        elif entity_type == 'device':
            device_entities.append(entity)
            # Extract domain hints from device name
            if 'light' in entity_name or 'lamp' in entity_name or 'bulb' in entity_name:
                mentioned_domains.add('light')
            elif 'sensor' in entity_name:
                mentioned_domains.add('binary_sensor')
            elif 'switch' in entity_name:
                mentioned_domains.add('switch')
            elif 'hue' in entity_name:
                mentioned_domains.add('light')  # Hue lights are light domain

            # Check if entity has domain already
            domain = entity.get('domain', '').lower()
            if domain and domain != 'unknown':
                mentioned_domains.add(domain)

    # If no location or domains found, return original entities
    if not mentioned_locations or not mentioned_domains:
        logger.info(f"ℹ️ Early device resolution: No location ({len(mentioned_locations)}) or domains ({len(mentioned_domains)}) found, skipping")
        return entities

    logger.info(f"🔍 Early device resolution: Found locations {mentioned_locations}, domains {mentioned_domains}")

    # Query HA for specific devices in each location
    resolved_devices = []
    for location in mentioned_locations:
        for domain in mentioned_domains:
            try:
                # Normalize location name (try both formats)
                location_variants = [
                    location,
                    location.replace(' ', '_'),
                    location.replace('_', ' '),
                    location.lower(),
                    location.lower().replace(' ', '_'),
                    location.lower().replace('_', ' ')
                ]

                area_entities = None
                for loc_variant in location_variants:
                    try:
                        area_entities = await ha_client.get_entities_by_area_and_domain(
                            area_id=loc_variant,
                            domain=domain
                        )
                        if area_entities:
                            logger.info(f"✅ Found {len(area_entities)} {domain} entities in area '{loc_variant}'")
                            break
                    except Exception as e:
                        logger.debug(f"Location variant '{loc_variant}' failed: {e}")
                        continue

                if area_entities:
                    # Add specific devices to resolved_devices
                    for area_entity in area_entities:
                        entity_id = area_entity.get('entity_id')
                        friendly_name = area_entity.get('friendly_name') or entity_id.split('.')[-1] if entity_id else 'unknown'

                        # Check if this device is already in entities (avoid duplicates)
                        already_exists = any(
                            e.get('type') == 'device' and
                            (e.get('name', '').lower() == friendly_name.lower() or
                             e.get('entity_id') == entity_id)
                            for e in entities
                        )

                        if not already_exists:
                            resolved_devices.append({
                                'name': friendly_name,
                                'friendly_name': friendly_name,
                                'entity_id': entity_id,
                                'type': 'device',
                                'domain': domain,
                                'area_id': area_entity.get('area_id'),
                                'area_name': location,
                                'confidence': 0.9,
                                'extraction_method': 'early_device_resolution',
                                'resolved_from': device_entities[0].get('name') if device_entities else 'generic'
                            })

            except Exception as e:
                logger.warning(f"⚠️ Error resolving devices for location '{location}', domain '{domain}': {e}")
                continue

    # Merge resolved devices with original entities
    # Replace generic device entities with specific ones, or add if new
    if resolved_devices:
        logger.info(f"✅ Early device resolution: Resolved {len(resolved_devices)} specific devices")

        # Create updated entities list
        updated_entities = []
        generic_device_names = {e.get('name', '').lower() for e in device_entities}

        for entity in entities:
            # If this is a generic device entity that was resolved, skip it (we'll add specific ones)
            if entity.get('type') == 'device':
                entity_name_lower = entity.get('name', '').lower()
                # Check if this generic device name was resolved
                was_resolved = any(
                    entity_name_lower in resolved_dev.get('resolved_from', '').lower() or
                    resolved_dev.get('resolved_from', '').lower() in entity_name_lower
                    for resolved_dev in resolved_devices
                )
                if was_resolved:
                    # Skip generic, will add specific below
                    continue

            updated_entities.append(entity)

        # Add all resolved specific devices
        updated_entities.extend(resolved_devices)

        return updated_entities

    return entities


async def build_device_selection_debug_data(
    devices_involved: list[str],
    validated_entities: dict[str, str],
    enriched_data: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
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
    suggestion: dict[str, Any],
    validated_entities: dict[str, str],
    enriched_data: dict[str, dict[str, Any]],
    query: str
) -> dict[str, Any]:
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


async def _score_entities_by_relevance(
    enriched_entities: list[dict[str, Any]],
    enriched_data: dict[str, dict[str, Any]],
    query: str,
    clarification_context: dict[str, Any] | None = None,
    mentioned_locations: list[str] | None = None,
    mentioned_domains: list[str] | None = None
) -> dict[str, float]:
    """
    Score entities by relevance to query + clarification answers.
    Uses keyword matching and basic relevance signals.
    
    Args:
        enriched_entities: List of enriched entity dicts
        enriched_data: Dictionary mapping entity_id to enriched entity data
        query: User query (may already be enriched)
        clarification_context: Optional clarification Q&A context
        mentioned_locations: Optional list of mentioned locations
        mentioned_domains: Optional list of mentioned domains
    
    Returns:
        Dictionary mapping entity_id to relevance score (0.0-1.0)
    """
    scores: dict[str, float] = {}
    
    # Build enriched query from original + clarification answers
    enriched_query = query.lower()
    clarification_entities = set()
    clarification_keywords = set()
    
    if clarification_context and clarification_context.get('questions_and_answers'):
        qa_list = clarification_context['questions_and_answers']
        for qa in qa_list:
            answer = qa.get('answer', '').lower()
            clarification_keywords.update(answer.split())
            
            # Extract entities from selected_entities
            if qa.get('selected_entities'):
                clarification_entities.update(qa['selected_entities'])
    
    # Build keyword set from query + clarifications
    query_keywords = set(enriched_query.split())
    all_keywords = query_keywords | clarification_keywords
    
    # Score each entity
    for entity in enriched_entities:
        entity_id = entity.get('entity_id', '')
        if not entity_id or entity_id not in enriched_data:
            scores[entity_id] = 0.0
            continue
        
        enriched = enriched_data[entity_id]
        score = 0.0
        
        # Signal 1: Entity mentioned in clarification answers (HIGHEST PRIORITY - 0.5 points)
        if entity_id in clarification_entities:
            score += 0.5
        elif any(entity_id.lower() in kw or kw in entity_id.lower() for kw in clarification_keywords):
            score += 0.3
        
        # Signal 2: Location match (0.3 points)
        if mentioned_locations:
            entity_area_id = (enriched.get('area_id') or '').lower()
            entity_area_name = (enriched.get('area_name') or '').lower()
            for location in mentioned_locations:
                location_lower = location.lower().replace('_', ' ')
                if (location_lower in entity_area_id or
                    entity_area_id in location_lower or
                    location_lower in entity_area_name or
                    entity_area_name in location_lower):
                    score += 0.3
                    break
        
        # Signal 3: Domain match (0.2 points)
        if mentioned_domains:
            entity_domain = (enriched.get('domain') or '').lower()
            if entity_domain in mentioned_domains:
                score += 0.2
        
        # Signal 4: Name/Keyword match (0.2 points)
        friendly_name = (enriched.get('friendly_name') or '').lower()
        entity_id_lower = entity_id.lower()
        
        # Check if any query keyword appears in entity name/ID
        for keyword in all_keywords:
            if len(keyword) > 3:  # Only meaningful keywords (length > 3)
                if (keyword in friendly_name or
                    keyword in entity_id_lower or
                    friendly_name in keyword):
                    score += 0.1
                    break
        
        # Cap score at 1.0
        scores[entity_id] = min(score, 1.0)
    
    # Log top scored entities for debugging
    top_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]
    logger.debug(f"📊 Top 5 scored entities: {top_scores}")
    
    return scores


async def generate_suggestions_from_query(
    query: str,
    entities: list[dict[str, Any]],
    user_id: str,
    db_session: AsyncSession | None = None,
    clarification_context: dict[str, Any] | None = None,  # NEW: Clarification Q&A
    query_id: str | None = None,  # NEW: Query ID for metrics tracking
    area_filter: str | None = None  # NEW: Area filter from query (e.g., "office" or "office,kitchen")
) -> list[dict[str, Any]]:
    """Generate automation suggestions based on query and entities"""
    if not openai_client:
        raise ValueError("OpenAI client not available - cannot generate suggestions")

    # Track skipped suggestions for better error reporting
    skipped_suggestions_count = 0
    skipped_reasons = []

    try:
        # Use unified prompt builder for consistent prompt generation
        from ..prompt_building.unified_prompt_builder import UnifiedPromptBuilder

        unified_builder = UnifiedPromptBuilder(device_intelligence_client=_device_intelligence_client)

        # NEW: Resolve and enrich entities with full attribute data (like YAML generation does)
        entity_context_json = ""
        resolved_entity_ids = []
        enriched_data = {}  # Initialize at function level for use in suggestion building
        enriched_entities: list[dict[str, Any]] = []
        query_location: str | None = None  # Initialize at function level for context-aware entity mapping

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
                from ..clients.data_api_client import DataAPIClient
                from ..services.entity_validator import EntityValidator

                data_api_client = DataAPIClient()
                entity_validator = EntityValidator(data_api_client, db_session=None, ha_client=ha_client)

                # Extract location and ALL domains from query to get ALL matching entities
                # Use area_filter if provided (from extract_area_from_request), otherwise extract from query
                if area_filter:
                    # area_filter can be comma-separated (e.g., "office,kitchen"), use first one for query_location
                    query_location = area_filter.split(',')[0].strip()
                    logger.info(f"📍 Using area_filter for location: '{query_location}' (from area_filter: '{area_filter}')")
                else:
                    query_location = entity_validator._extract_location_from_query(query)
                    if query_location:
                        logger.info(f"📍 Extracted location from query: '{query_location}'")
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
                                # Use EntityAttributeService to get proper friendly name from Entity Registry
                                try:
                                    attribute_service = EntityAttributeService(ha_client)
                                    enriched = await attribute_service.enrich_entity_with_attributes(entity_id)
                                    if enriched:
                                        friendly_name = enriched.get('friendly_name', entity_id.split('.')[-1].replace('_', ' ').title())
                                        area_id = enriched.get('area_id') or attributes.get('area_id')
                                    else:
                                        friendly_name = attributes.get('friendly_name', entity_id.split('.')[-1].replace('_', ' ').title())
                                        area_id = attributes.get('area_id')
                                except Exception as e:
                                    logger.warning(f"⚠️ Failed to enrich entity {entity_id} with EntityAttributeService: {e}, using fallback")
                                    friendly_name = attributes.get('friendly_name', entity_id.split('.')[-1].replace('_', ' ').title())
                                    area_id = attributes.get('area_id')

                                entity_dict = {
                                    'entity_id': entity_id,
                                    'friendly_name': friendly_name,
                                    'area_id': area_id,
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
                    logger.info("⚠️ No entities found for specific domains, trying location-only fetch...")
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
                        logger.info("🔍 No entities found by location/domain, trying device name mapping...")
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
                                should_include_air_quality,
                                should_include_carbon,
                                should_include_energy,
                                should_include_weather,
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

                    # Check cache first (Phase 4: Entity Context Caching)
                    from ..services.entity_context_cache import get_entity_cache

                    entity_cache = get_entity_cache(
                        ttl_seconds=getattr(settings, 'entity_cache_ttl_seconds', 300)
                    )

                    cached_data = entity_cache.get(set(resolved_entity_ids))

                    if cached_data:
                        logger.info(f"✅ Cache hit: Using cached entity data for {len(resolved_entity_ids)} entities")
                        enriched_data = cached_data
                    else:
                        # Use comprehensive enrichment service that combines ALL data sources
                        from ..services.comprehensive_entity_enrichment import (
                            enrich_entities_comprehensively,
                        )
                        enriched_data = await enrich_entities_comprehensively(
                            entity_ids=set(resolved_entity_ids),
                            ha_client=ha_client,
                            device_intelligence_client=_device_intelligence_client,
                            data_api_client=None,  # Could add DataAPIClient if historical patterns needed
                            include_historical=False,  # Set to True to include usage patterns
                            enrichment_context=enrichment_context  # NEW: Add enrichment context
                        )

                        # Cache the enriched data
                        entity_cache.set(set(resolved_entity_ids), enriched_data)
                        logger.info(f"✅ Cached entity data for {len(resolved_entity_ids)} entities")

                    # ========================================================================
                    # LOCATION-AWARE ENTITY EXPANSION (NEW)
                    # ========================================================================
                    # Extract locations mentioned in query and clarification context
                    mentioned_locations = set()
                    query_lower = query.lower()

                    # PRIORITY: Use area_filter if provided (most reliable source)
                    if area_filter:
                        from ..utils.area_detection import get_area_list
                        area_list = get_area_list(area_filter)
                        for area in area_list:
                            # Add normalized (office) and with spaces (office)
                            mentioned_locations.add(area)
                            mentioned_locations.add(area.replace('_', ' '))
                            logger.info(f"📍 Added area_filter to mentioned_locations: '{area}' (from area_filter: '{area_filter}')")

                    # Common location keywords (fallback if area_filter not provided)
                    location_keywords = [
                        'office', 'living room', 'bedroom', 'kitchen', 'bathroom', 'dining room',
                        'garage', 'basement', 'attic', 'hallway', 'entryway', 'patio', 'deck',
                        'outdoor', 'outdoors', 'garden', 'yard', 'backyard', 'front yard'
                    ]

                    # Extract locations from query (only if not already in mentioned_locations from area_filter)
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

                    # Extract device domain/type from query and entities using fuzzy matching
                    mentioned_domains = set()
                    
                    # Device types that map to light domain
                    light_device_types = {'wled', 'hue', 'lifx', 'tp-link', 'ikea', 'nanoleaf'}
                    
                    # Use fuzzy matching to detect device types in query
                    detected_device_types = detect_device_types_fuzzy(query, threshold=0.7)
                    for device_type, confidence in detected_device_types:
                        if device_type in light_device_types:
                            mentioned_domains.add('light')
                            logger.info(f"🔍 Detected light device type '{device_type}' in query (confidence: {confidence:.2f}), adding 'light' domain")
                            break  # Only need to find one light device type
                    
                    if entities:
                        for entity in entities:
                            domain = entity.get('domain', '').lower()
                            if domain and domain != 'unknown':
                                mentioned_domains.add(domain)
                            # Also check name for domain hints using fuzzy matching
                            name = entity.get('name', '')
                            name_lower = name.lower()
                            
                            if 'light' in name_lower or 'lamp' in name_lower or 'bulb' in name_lower:
                                mentioned_domains.add('light')
                            # Check for specific device types using fuzzy matching
                            else:
                                detected_device_types = detect_device_types_fuzzy(name, threshold=0.7)
                                for device_type, confidence in detected_device_types:
                                    if device_type in light_device_types:
                                        mentioned_domains.add('light')
                                        logger.info(f"🔍 Detected light device type '{device_type}' in entity name '{name}' (confidence: {confidence:.2f}), adding 'light' domain")
                                        break
                            
                            # Check for other domain hints
                            if 'sensor' in name_lower:
                                mentioned_domains.add('binary_sensor')
                            if 'switch' in name_lower:
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
                            # BUT: Skip this if query mentions specific device types (e.g., "wled", "led")
                            # This prevents over-selection when user wants a specific device type
                            # Use fuzzy matching instead of hardcoded keywords
                            if not mentioned_domains:
                                # Use fuzzy matching to detect any specific device types in query
                                detected_device_types = detect_device_types_fuzzy(query, threshold=0.7)
                                specific_device_types_in_query = len(detected_device_types) > 0
                                
                                if specific_device_types_in_query:
                                    device_type_names = [dt[0] for dt in detected_device_types]
                                    logger.info(f"🔍 Detected specific device types in query using fuzzy matching: {device_type_names}")
                                    logger.info(f"🔍 Query mentions specific device types, skipping expansion to all entities in '{location}' to avoid over-selection")
                                    # Still try to get light entities since device types like "wled", "led" are lights
                                    try:
                                        area_entities = await ha_client.get_entities_by_area_and_domain(
                                            area_id=location,
                                            domain='light'  # Filter to light domain only
                                        )
                                        if area_entities:
                                            area_entity_ids = [e.get('entity_id') for e in area_entities if e.get('entity_id')]
                                            location_expanded_entity_ids.update(area_entity_ids)
                                            logger.info(f"✅ Expanded by location '{location}' + domain 'light' (device type detected): Added {len(area_entity_ids)} entities")
                                            
                                            # Enrich new entities
                                            for area_entity in area_entities:
                                                entity_id = area_entity.get('entity_id')
                                                if entity_id and entity_id not in enriched_data:
                                                    enriched_data[entity_id] = {
                                                        'entity_id': entity_id,
                                                        'friendly_name': area_entity.get('friendly_name', entity_id),
                                                        'area_id': area_entity.get('area_id'),
                                                        'area_name': area_entity.get('area_id'),
                                                        'domain': 'light',
                                                        'state': area_entity.get('state'),
                                                        'attributes': area_entity.get('attributes', {})
                                                    }
                                    except Exception as e:
                                        logger.warning(f"⚠️ Error expanding light entities for location '{location}': {e}")
                                else:
                                    # No specific device types mentioned, safe to get all entities
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
                                from ..services.comprehensive_entity_enrichment import (
                                    enrich_entities_comprehensively,
                                )
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
                    # RELEVANCE-BASED FILTERING (NEW - Option 3)
                    # ========================================================================
                    # OPTIMIZATION: Score entities by relevance BEFORE filtering
                    # Priority: Relevance scoring > Location matching > Device name matching
                    # This ensures most relevant entities are kept even if they don't match location/name filters
                    # Token savings: 4,000-6,000 tokens by keeping only top N most relevant entities
                    
                    # NEW: Score all entities by relevance first
                    relevance_scores = await _score_entities_by_relevance(
                        enriched_entities=[{'entity_id': eid} for eid in resolved_entity_ids],
                        enriched_data=enriched_data,
                        query=query,  # Use function parameter (enriched_query is not in this scope)
                        clarification_context=clarification_context,
                        mentioned_locations=mentioned_locations,
                        mentioned_domains=mentioned_domains
                    )
                    
                    # Keep top N most relevant entities (reduced to 15 to avoid token overflow)
                    top_n_relevant = 15
                    sorted_entity_ids = sorted(
                        resolved_entity_ids,
                        key=lambda eid: relevance_scores.get(eid, 0.0),
                        reverse=True
                    )[:top_n_relevant]
                    
                    logger.info(
                        f"📊 Relevance-scored: {len(sorted_entity_ids)}/{len(resolved_entity_ids)} "
                        f"entities selected (top {top_n_relevant} by relevance)"
                    )
                    
                    # Now apply location/name filtering on top of relevance filtering
                    # LOCATION-PRIORITY FILTERING (EXISTING)
                    # ========================================================================
                    # OPTIMIZATION: Filter entity context to reduce token usage
                    # Priority: Location matching > Device name matching
                    # Only include entities that match location OR extracted device names
                    # BUT: Don't filter if extracted names are generic domain terms (e.g., "lights", "sensor", "led")
                    # This reduces prompt size while still giving AI enough context
                    filtered_entity_ids_for_prompt = set(sorted_entity_ids)  # Start with relevance-filtered set

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
                    # NOTE: Filters from relevance-filtered set (sorted_entity_ids), not full set
                    if mentioned_locations:
                        location_filtered_entity_ids = set()
                        for entity_id in filtered_entity_ids_for_prompt:  # Filter from relevance-filtered set
                            enriched = enriched_data.get(entity_id, {})
                            # Handle None values: get() returns None if key exists but value is None
                            entity_area_id_raw = enriched.get('area_id') or ''
                            entity_area_name_raw = enriched.get('area_name') or ''
                            entity_area_id = entity_area_id_raw.lower() if isinstance(entity_area_id_raw, str) else ''
                            entity_area_name = entity_area_name_raw.lower() if isinstance(entity_area_name_raw, str) else ''

                            # Check if entity is in any mentioned location
                            entity_matches_location = False
                            # CRITICAL: Only match if entity has an area_id or area_name (empty strings match everything with 'in' operator)
                            if entity_area_id or entity_area_name:
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
                                    friendly_name = enriched.get('friendly_name', '')
                                    if not friendly_name:
                                        continue
                                    friendly_name = friendly_name.lower()
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
                                    friendly_name = enriched.get('friendly_name', '')
                                    if not friendly_name:
                                        continue
                                    friendly_name = friendly_name.lower()
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

                    # Compress entity context to reduce token usage (Phase 3)
                    if getattr(settings, 'enable_token_counting', True):
                        from ..utils.entity_context_compressor import compress_entity_context

                        max_entity_tokens = getattr(settings, 'max_entity_context_tokens', 7_000)  # Updated default from 10_000 to 7_000 (Option 1)
                        suggestion_model = getattr(settings, 'suggestion_generation_model', 'gpt-5.1')

                        filtered_enriched_data_for_prompt = compress_entity_context(
                            filtered_enriched_data_for_prompt,
                            max_tokens=max_entity_tokens,
                            model=suggestion_model,
                            relevance_scores=relevance_scores  # NEW: Pass relevance scores for prioritized compression
                        )

                        logger.info(
                            f"✅ Compressed entity context to {len(filtered_enriched_data_for_prompt)} entities "
                            f"(max {max_entity_tokens} tokens)"
                        )

                    context_builder = EntityContextBuilder()
                    entity_context_json = await context_builder.build_entity_context_json(
                        entities=enriched_entities,
                        enriched_data=filtered_enriched_data_for_prompt,
                        db_session=db_session
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

        # Enforce token budget before API call (Phase 2)
        if getattr(settings, 'enable_token_counting', True):
            from ..utils.token_budget import check_token_budget, enforce_token_budget

            # Build budget from settings
            token_budget = {
                'max_entity_context_tokens': getattr(settings, 'max_entity_context_tokens', 10_000),
                'max_enrichment_context_tokens': getattr(settings, 'max_enrichment_context_tokens', 2_000),
                'max_conversation_history_tokens': getattr(settings, 'max_conversation_history_tokens', 1_000),
                'max_total_tokens': 30_000  # OpenAI rate limit (will be 500K after tier verification)
            }

            # Enforce budget on prompt components
            prompt_dict = enforce_token_budget(
                prompt_dict,
                token_budget,
                model=getattr(settings, 'suggestion_generation_model', 'gpt-5.1')
            )

            # Check total token budget and log warning if approaching limit
            # Build messages to check
            check_messages = [
                {"role": "system", "content": prompt_dict.get("system_prompt", "")},
                {"role": "user", "content": prompt_dict.get("user_prompt", "")}
            ]

            budget_status = check_token_budget(
                check_messages,
                token_budget,
                model=getattr(settings, 'suggestion_generation_model', 'gpt-5.1')
            )

            if budget_status['usage_percent'] > 80:
                logger.warning(
                    f"⚠️ Token usage at {budget_status['usage_percent']:.1f}% of budget "
                    f"({budget_status['total_tokens']}/{budget_status['max_tokens']} tokens)"
                )

            if budget_status['total_tokens'] > getattr(settings, 'warn_on_token_threshold', 20_000):
                logger.warning(
                    f"⚠️ Token count ({budget_status['total_tokens']}) exceeds warning threshold "
                    f"({getattr(settings, 'warn_on_token_threshold', 20_000)})"
                )

        if getattr(settings, "enable_langchain_prompt_builder", False):
            try:
                from ..langchain_integration.ask_ai_chain import build_prompt_with_langchain

                prompt_dict = build_prompt_with_langchain(
                    query=query,
                    entities=enriched_entities or entities,
                    base_prompt=prompt_dict,
                    entity_context_json=entity_context_json,
                    clarification_context=clarification_context,
                )
                logger.debug("🧱 LangChain prompt builder applied for Ask AI query.")
            except Exception as langchain_exc:  # pragma: no cover - defensive logging
                logger.warning(
                    "⚠️ LangChain prompt builder failed (%s), falling back to unified prompt.",
                    langchain_exc,
                    exc_info=True,
                )

        # Generate suggestions with unified prompt
        logger.info(f"Generating suggestions for query: {query}")
        logger.info(f"OpenAI client available: {openai_client is not None}")

        # Capture OpenAI prompts for debug panel
        openai_debug_data = {
            'system_prompt': prompt_dict.get('system_prompt', ''),
            'user_prompt': prompt_dict.get('user_prompt', ''),
            'openai_response': None,
            'token_usage': None,
            'clarification_context': clarification_context  # NEW: Include clarification in debug
        }

        try:
            # Check if parallel testing enabled
            from ..database.crud import get_system_settings
            system_settings = await get_system_settings(db_session) if db_session else None
            enable_parallel = system_settings and getattr(system_settings, 'enable_parallel_model_testing', False) if system_settings else False

            if enable_parallel:
                # Parallel model testing mode
                from ..services.parallel_model_tester import ParallelModelTester
                tester = ParallelModelTester(openai_client.api_key)

                # Get models from settings
                parallel_models = getattr(system_settings, 'parallel_testing_models', {}) if system_settings else {}
                models = parallel_models.get('suggestion', ['gpt-5.1'])

                logger.info(f"OpenAI model (parallel testing): {models[0]} vs {models[1]} - using {models[0]}")

                result = await tester.generate_suggestions_parallel(
                    prompt_dict=prompt_dict,
                    models=models,
                    endpoint="ask_ai_suggestions",
                    db_session=db_session,
                    query_id=query_id,  # Use query_id from function parameter
                    temperature=settings.creative_temperature,
                    max_tokens=8000  # Increased to 8000 for GPT-5.1 reasoning models - allows reasoning tokens + full JSON completion
                )

                suggestions_data = result['primary_result']  # Use first model's result
                comparison_metrics = result['comparison']  # Store for metrics

                # Update debug data with primary model usage
                if comparison_metrics and comparison_metrics.get('model_results'):
                    primary_result = comparison_metrics['model_results'][0]
                    openai_debug_data['token_usage'] = {
                        'prompt_tokens': primary_result.get('tokens_input', 0),
                        'completion_tokens': primary_result.get('tokens_output', 0),
                        'total_tokens': primary_result.get('tokens_input', 0) + primary_result.get('tokens_output', 0),
                        'cost_usd': primary_result.get('cost_usd', 0.0),
                        'model': primary_result.get('model', models[0]),
                        'endpoint': 'ask_ai_suggestions'
                    }
                    openai_debug_data['model_used'] = primary_result.get('model', models[0])
                    openai_debug_data['parallel_testing'] = True
                    openai_debug_data['comparison_metrics'] = comparison_metrics

                logger.info(f"Parallel testing: {models[0]} vs {models[1]} - using {models[0]} result")
            else:
                # Single model mode (existing behavior)
                suggestion_model = getattr(settings, 'suggestion_generation_model', 'gpt-5.1')

                logger.info(f"OpenAI model (single mode): {suggestion_model}")

                # Create temporary client with suggestion model if different
                if suggestion_model != openai_client.model:
                    suggestion_client = OpenAIClient(
                        api_key=openai_client.api_key,
                        model=suggestion_model,
                        enable_token_counting=getattr(settings, 'enable_token_counting', True)
                    )
                else:
                    suggestion_client = openai_client

                suggestions_data = await suggestion_client.generate_with_unified_prompt(
                    endpoint="ask_ai_suggestions",  # Phase 5: Track endpoint
                    prompt_dict=prompt_dict,
                    temperature=settings.creative_temperature,
                    max_tokens=8000,  # Increased to 8000 for GPT-5.1 reasoning models - allows reasoning tokens + full JSON completion
                    output_format="json"
                )

                # Update debug data with actual model used
                if suggestion_client.last_usage:
                    openai_debug_data['token_usage'] = suggestion_client.last_usage
                    openai_debug_data['model_used'] = suggestion_model
                    openai_debug_data['parallel_testing'] = False

            # Store OpenAI response (parsed JSON)
            openai_debug_data['openai_response'] = suggestions_data

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
                # 2025 ENHANCEMENT: Context-aware - preserves terms mentioned in clarifications
                # This handles cases where OpenAI includes generic terms like "light", "wled", domain names, etc.
                if devices_involved:
                    devices_involved = _pre_consolidate_device_names(
                        devices_involved, 
                        enriched_data,
                        clarification_context=clarification_context  # Pass context for context-aware filtering
                    )
                    if len(devices_involved) < original_devices_count:
                        logger.info(
                            f"🔄 Pre-consolidated devices for suggestion {i+1}: "
                            f"{original_devices_count} -> {len(devices_involved)} "
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
                            f"{len(devices_involved)} -> {len(deduplicated)} "
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
                    # 2025 ENHANCEMENT: Pass clarification context and location for context-aware mapping
                    # query_location is initialized at function level (line 3491), so it's always accessible here
                    # If not already extracted, try to extract from query as fallback
                    if not query_location and ha_client_for_mapping:
                        try:
                            from ..clients.data_api_client import DataAPIClient
                            from ..services.entity_validator import EntityValidator
                            data_api_client = DataAPIClient()
                            entity_validator = EntityValidator(data_api_client, db_session=None, ha_client=ha_client_for_mapping)
                            query_location = entity_validator._extract_location_from_query(query)
                            logger.debug(f"🔍 Extracted query_location='{query_location}' as fallback for entity mapping")
                        except Exception as e:
                            logger.debug(f"Could not extract location from query: {e}, using None (context-aware matching will use clarification context)")
                    
                    # 2025 ENHANCEMENT: Expand location names to entity friendly names before mapping
                    # This handles cases where OpenAI returns location names (e.g., "office") instead of device names
                    # Follows existing pattern for entity ID expansion (lines 4473-4522)
                    # FIX: Don't expand location names if specific device types are mentioned (e.g., "wled", "led")
                    expanded_devices_involved = []
                    location_names_expanded = []
                    
                    # Check if there are specific device types mentioned using fuzzy matching
                    # Check both devices_involved AND the original query (OpenAI might not include device type in devices_involved)
                    has_specific_device_type_in_query = False
                    has_specific_device_type_in_devices = False
                    
                    # Check query using fuzzy matching
                    if query:
                        detected_in_query = detect_device_types_fuzzy(query, threshold=0.7)
                        if detected_in_query:
                            has_specific_device_type_in_query = True
                            device_type_names = [dt[0] for dt in detected_in_query]
                            logger.debug(f"🔍 Detected device types in query using fuzzy matching: {device_type_names}")
                    
                    # Check devices_involved using fuzzy matching
                    for device_name in devices_involved:
                        detected_in_device = detect_device_types_fuzzy(device_name, threshold=0.7)
                        if detected_in_device:
                            has_specific_device_type_in_devices = True
                            device_type_names = [dt[0] for dt in detected_in_device]
                            logger.debug(f"🔍 Detected device types in devices_involved '{device_name}' using fuzzy matching: {device_type_names}")
                            break
                    
                    has_specific_device_type = has_specific_device_type_in_query or has_specific_device_type_in_devices
                    
                    # Also check if there are multiple non-location device names (indicates specific selection)
                    non_location_device_names = []
                    for device_name in devices_involved:
                        device_name_normalized = device_name.lower().strip().replace(' ', '_')
                        query_location_normalized = query_location.lower().strip().replace(' ', '_') if query_location else None
                        is_location = (
                            query_location_normalized and
                            (device_name_normalized == query_location_normalized or
                             device_name_normalized in query_location_normalized or
                             query_location_normalized in device_name_normalized)
                        )
                        if not is_location:
                            non_location_device_names.append(device_name)
                    
                    # Only expand location names if:
                    # 1. No specific device types are mentioned (e.g., "wled", "led")
                    # 2. No other specific device names exist (only location name in list)
                    should_expand_locations = not has_specific_device_type and len(non_location_device_names) == 0
                    
                    if has_specific_device_type:
                        logger.info(f"🔍 Specific device type detected in devices_involved, skipping location expansion to avoid over-selection")
                    elif len(non_location_device_names) > 0:
                        logger.info(f"🔍 Specific device names found ({non_location_device_names}), skipping location expansion")
                    
                    for device_name in devices_involved:
                        # Normalize location name for comparison (handle spaces, underscores)
                        device_name_normalized = device_name.lower().strip().replace(' ', '_')
                        query_location_normalized = query_location.lower().strip().replace(' ', '_') if query_location else None
                        
                        # Check if device_name is a location name that matches query_location
                        # This follows the same pattern as entity ID detection (line 4475)
                        is_location_name = (
                            query_location_normalized and
                            (device_name_normalized == query_location_normalized or
                             device_name_normalized in query_location_normalized or
                             query_location_normalized in device_name_normalized)
                        )
                        
                        if is_location_name and should_expand_locations and resolved_entity_ids and enriched_data:
                            # Expand location to entities (similar to entity ID expansion at lines 4490-4522)
                            logger.info(f"📍 Expanding location '{device_name}' to {len(resolved_entity_ids)} entities from resolved_entity_ids")
                            location_entities_added = 0
                            
                            # Map entity IDs to friendly names from enriched_data (existing pattern)
                            for entity_id in resolved_entity_ids:
                                enriched = enriched_data.get(entity_id, {})
                                if enriched:
                                    # Use same priority order as lines 4377-4383
                                    friendly_name = (
                                        enriched.get('device_name') or
                                        enriched.get('friendly_name') or
                                        enriched.get('name_by_user') or
                                        enriched.get('name') or
                                        enriched.get('original_name') or
                                        entity_id.split('.')[-1].replace('_', ' ').title()  # Fallback
                                    )
                                    if friendly_name and friendly_name not in expanded_devices_involved:
                                        expanded_devices_involved.append(friendly_name)
                                        location_entities_added += 1
                            
                            if location_entities_added > 0:
                                location_names_expanded.append(device_name)
                                logger.info(f"✅ Expanded location '{device_name}' to {location_entities_added} entity friendly names")
                            else:
                                # Fallback: keep original if expansion failed
                                logger.warning(f"⚠️ Failed to expand location '{device_name}', keeping original")
                                expanded_devices_involved.append(device_name)
                        else:
                            # Not a location name, or expansion skipped due to specific device types, use as-is
                            expanded_devices_involved.append(device_name)
                            if is_location_name and not should_expand_locations:
                                logger.info(f"🔍 Skipped expanding location '{device_name}' because specific device types/names are mentioned")
                    
                    # Use expanded list for mapping (replace devices_involved with expanded_devices_involved)
                    if location_names_expanded:
                        logger.info(f"📍 Location expansion: {len(location_names_expanded)} locations expanded, {len(devices_involved)} -> {len(expanded_devices_involved)} devices")
                        devices_involved = expanded_devices_involved
                    
                    validated_entities = await map_devices_to_entities(
                        devices_involved,  # Now contains friendly names instead of location names
                        enriched_data,
                        ha_client=ha_client_for_mapping,
                        fuzzy_match=True,
                        clarification_context=clarification_context,  # Pass context for better matching
                        query_location=query_location  # Pass location hint from query (always in scope)
                    )
                    if validated_entities:
                        logger.info(f"✅ Mapped {len(validated_entities)}/{len(devices_involved)} devices to VERIFIED entities for suggestion {i+1}")

                        # Replace device names in devices_involved with actual device names from enriched_data
                        # This ensures UI displays "Office Back Left" instead of "Hue Color Downlight 1"
                        updated_devices_involved = []
                        for device_name in devices_involved:
                            # Check if device_name is already an entity_id
                            entity_id = None
                            if _is_entity_id(device_name):
                                # device_name is already an entity_id (e.g., "light.hue_color_downlight_1_4")
                                entity_id = device_name
                            else:
                                # device_name is a friendly name, look it up in validated_entities
                                entity_id = validated_entities.get(device_name)

                            # Try to get enriched data for this entity_id
                            if entity_id and entity_id in enriched_data:
                                enriched = enriched_data[entity_id]
                                # Priority order for device name:
                                # 1. device_name from device intelligence (has name_by_user from database)
                                # 2. friendly_name from Entity Registry (has name_by_user from HA)
                                # 3. name_by_user directly from enriched data
                                # 4. name or original_name as fallback
                                actual_device_name = (
                                    enriched.get('device_name') or
                                    enriched.get('friendly_name') or
                                    enriched.get('name_by_user') or
                                    enriched.get('name') or
                                    enriched.get('original_name')
                                )
                                if actual_device_name:
                                    updated_devices_involved.append(actual_device_name)
                                    logger.info(f"🔄 Replaced '{device_name}' -> '{actual_device_name}' in devices_involved")
                                else:
                                    # No name available, keep original but log warning
                                    updated_devices_involved.append(device_name)
                                    logger.warning(f"⚠️ No device name found for {entity_id} in enriched_data (all name fields NULL)")
                            else:
                                # Entity not in enriched_data, keep original
                                updated_devices_involved.append(device_name)
                                if entity_id:
                                    logger.debug(f"⚠️ Entity {entity_id} not found in enriched_data, keeping original name")

                        if updated_devices_involved != devices_involved:
                            logger.info(f"🔄 Updated devices_involved with actual device names: {devices_involved} -> {updated_devices_involved}")
                            devices_involved = updated_devices_involved

                        # NEW: Validate location context for matched devices
                        location_mismatch_detected = False
                        query_location = None
                        try:
                            logger.info(f"🔍 [LOCATION VALIDATION] Starting location validation for suggestion {i+1}")
                            # Extract location from query
                            from ..clients.data_api_client import DataAPIClient
                            from ..services.entity_validator import EntityValidator
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
                                    # CRITICAL: Only match if entity_area is NOT empty (empty string matches everything with 'in' operator)
                                    if not entity_area or not normalized_entity:
                                        # Entity has no area_id - cannot validate, so don't match
                                        area_matches = False
                                    else:
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
                                logger.info("🔍 [LOCATION VALIDATION] No location extracted from query, skipping validation")
                        except Exception as e:
                            logger.error(f"❌ Error validating location context: {e}", exc_info=True)

                    else:
                        logger.warning(f"⚠️ No verified entities found for suggestion {i+1} (devices: {devices_involved})")
                        # If devices_involved contains entity IDs (e.g., "light.hue_office_1"), use them directly
                        # This handles cases where map_devices_to_entities failed but we have valid entity IDs
                        entity_id_pattern = r'^(light|switch|binary_sensor|sensor|cover|climate|fan|lock|media_player|vacuum|camera|alarm_control_panel|automation|script|scene|input_boolean|input_number|input_select|input_text|input_datetime|timer|counter|zone|person|device_tracker|sun|weather)\.'
                        import re
                        entity_ids_found = {}
                        for device in devices_involved:
                            if re.match(entity_id_pattern, device):
                                # This is already an entity ID, use it directly
                                # Use the entity_id itself as both key and value for backwards compatibility
                                # Or extract a friendly name if available
                                friendly_name = device.split('.')[-1].replace('_', ' ').title()
                                entity_ids_found[friendly_name] = device

                        if entity_ids_found:
                            logger.info(f"✅ Found {len(entity_ids_found)} entity IDs in devices_involved, using them directly: {list(entity_ids_found.values())}")
                            validated_entities = entity_ids_found

                            # CRITICAL: Also replace entity IDs with friendly names even when validated_entities was empty
                            # This handles the case where OpenAI returns entity IDs directly
                            updated_devices_involved = []
                            for device_name in devices_involved:
                                # Check if device_name is already an entity_id
                                entity_id = None
                                if _is_entity_id(device_name):
                                    entity_id = device_name
                                else:
                                    entity_id = validated_entities.get(device_name)

                                # Try to get enriched data for this entity_id
                                if entity_id and entity_id in enriched_data:
                                    enriched = enriched_data[entity_id]
                                    actual_device_name = (
                                        enriched.get('device_name') or
                                        enriched.get('friendly_name') or
                                        enriched.get('name_by_user') or
                                        enriched.get('name') or
                                        enriched.get('original_name')
                                    )
                                    if actual_device_name:
                                        updated_devices_involved.append(actual_device_name)
                                        logger.info(f"🔄 Replaced entity ID '{device_name}' -> '{actual_device_name}' in devices_involved")
                                    else:
                                        updated_devices_involved.append(device_name)
                                        logger.warning(f"⚠️ No device name found for {entity_id} in enriched_data (all name fields NULL)")
                                else:
                                    updated_devices_involved.append(device_name)

                            if updated_devices_involved != devices_involved:
                                logger.info(f"🔄 Updated devices_involved with actual device names: {devices_involved} -> {updated_devices_involved}")
                                devices_involved = updated_devices_involved
                        else:
                            # CRITICAL ERROR: Entity mapping completely failed - no entity IDs found
                            # This is a REAL error that should be logged clearly, not hidden by fallback
                            logger.error(f"❌ CRITICAL: Entity mapping failed for suggestion {i+1}")
                            logger.error(f"❌ devices_involved: {devices_involved}")
                            logger.error(f"❌ No entity IDs found in devices_involved")
                            logger.error(f"❌ enriched_data available: {bool(enriched_data)}")
                            logger.error(f"❌ enriched_data entity count: {len(enriched_data) if enriched_data else 0}")
                            # Log what we tried to map (for debugging)
                            if enriched_data:
                                sample_entities = list(enriched_data.keys())[:5]
                                logger.error(f"❌ Sample entities in enriched_data: {sample_entities}")
                            # We cannot proceed without validated_entities, so we'll skip this suggestion
                            # This is an ERROR condition, not an expected fallback
                            skipped_suggestions_count += 1
                            skipped_reasons.append(f"Suggestion {i+1}: Entity mapping failed (no validated entities)")
                            logger.error(f"❌ Skipping suggestion {i+1} - entity mapping failed (no validated entities)")
                            continue  # Skip this suggestion entirely

                # CRITICAL CHECK: Ensure validated_entities is not empty before saving
                if not validated_entities or len(validated_entities) == 0:
                    # CRITICAL ERROR: This should never happen if mapping succeeded above
                    # If we reach here, something went wrong in the entity ID extraction logic
                    skipped_suggestions_count += 1
                    skipped_reasons.append(f"Suggestion {i+1}: validated_entities is empty (validation failed)")
                    logger.error(f"❌ CRITICAL: validated_entities is empty for suggestion {i+1} - entity mapping validation failed")
                    logger.error(f"❌ devices_involved: {devices_involved}")
                    logger.error(f"❌ This indicates a bug in entity mapping logic - mapping should have populated validated_entities")
                    logger.error(f"❌ Skipping suggestion {i+1} - no validated entities (validation failed)")
                    continue  # Skip this suggestion entirely

                # Ensure devices are consolidated before user display (even if enrichment skipped)
                if devices_involved and validated_entities:
                    before_consolidation_count = len(devices_involved)
                    consolidated_devices = consolidate_devices_involved(devices_involved, validated_entities)
                    if len(consolidated_devices) < before_consolidation_count:
                        logger.info(
                            f"🔄 Optimized devices_involved for suggestion {i+1}: "
                            f"{before_consolidation_count} -> {len(consolidated_devices)} entries "
                            f"({before_consolidation_count - len(consolidated_devices)} redundant entries removed)"
                        )
                    devices_involved = consolidated_devices

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

                # CRITICAL: Ensure validated_entities is not empty before saving
                # This should never happen if the code above is working correctly
                if not validated_entities or len(validated_entities) == 0:
                    skipped_suggestions_count += 1
                    skipped_reasons.append(f"Suggestion {i+1}: validated_entities is empty before saving")
                    logger.error(f"❌ CRITICAL: Cannot save suggestion {i+1} - validated_entities is empty")
                    logger.error(f"❌ devices_involved: {devices_involved}")
                    logger.error("❌ This indicates a bug in entity mapping - skipping this suggestion")
                    continue  # Skip this suggestion entirely - don't save it

                logger.info(f"✅ Suggestion {i+1} has {len(validated_entities)} validated entities - safe to save")

                base_suggestion = {
                    'suggestion_id': f'ask-ai-{uuid.uuid4().hex[:8]}',
                    'description': suggestion['description'],
                    'trigger_summary': suggestion['trigger_summary'],
                    'action_summary': suggestion['action_summary'],
                    'devices_involved': devices_involved,  # Consolidated (deduplicated) - FINAL
                    'validated_entities': validated_entities,  # Save mapping for fast test execution - MUST NOT BE EMPTY
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
                                enriched_data=filtered_enriched_data,
                                db_session=db_session
                            )

                            # Build filtered user prompt (replace entity context JSON with filtered version)
                            original_user_prompt = openai_debug_data.get('user_prompt', '')
                            if filtered_entity_context_json:
                                # Try to find and replace the entity context JSON section
                                # The entity context JSON appears in the "ENRICHED ENTITY CONTEXT" section
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

        adapter = get_soft_prompt()
        if adapter:
            suggestions = adapter.enhance_suggestions(
                query=query,
                suggestions=suggestions,
                context=entity_context_json,
                threshold=getattr(settings, "soft_prompt_confidence_threshold", 0.85)
            )

        guardrail_checker = get_guardrail_checker_instance()
        if guardrail_checker:
            guardrail_results = guardrail_checker.evaluate_batch(
                [suggestion.get('description', '') for suggestion in suggestions]
            )

            flagged_count = 0
            for suggestion, result in zip(suggestions, guardrail_results):
                suggestion.setdefault('metadata', {})['guardrail'] = result.to_dict()
                if result.flagged:
                    suggestion['status'] = 'needs_review'
                    flagged_count += 1

            if guardrail_results:
                logger.info(
                    "Guardrail check complete: %s/%s suggestions flagged",
                    flagged_count,
                    len(guardrail_results)
                )

        logger.info(f"Generated {len(suggestions)} suggestions for query: {query}")
        
        # Log skipped suggestions if any
        if skipped_suggestions_count > 0:
            logger.warning(f"⚠️ Skipped {skipped_suggestions_count} suggestion(s) due to entity mapping failures:")
            for reason in skipped_reasons:
                logger.warning(f"  - {reason}")
        
        # If all suggestions were skipped, provide helpful error
        if len(suggestions) == 0 and skipped_suggestions_count > 0:
            error_msg = f"All {skipped_suggestions_count} suggestion(s) were skipped due to entity mapping failures. "
            error_msg += "This usually means the device names in the query don't match available entities. "
            error_msg += f"Reasons: {', '.join(skipped_reasons[:3])}"  # Show first 3 reasons
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
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

    # Extract area/location from query if specified (for area-based filtering)
    from ..utils.area_detection import extract_area_from_request
    area_filter = extract_area_from_request(request.query)
    if area_filter:
        logger.info(f"📍 Detected area filter in clarification phase: '{area_filter}'")

    try:
        # Step 1: Extract entities using Home Assistant
        entities = await extract_entities_with_ha(request.query)

        # Step 1.5: Resolve generic device entities to specific devices BEFORE ambiguity detection
        # This ensures the ambiguity prompt shows specific device names (e.g., "Office Front Left")
        # instead of generic types (e.g., "hue lights")
        try:
            ha_client_for_resolution = get_ha_client()
            if ha_client_for_resolution:
                entities = await resolve_entities_to_specific_devices(entities, ha_client_for_resolution)
                logger.info(f"✅ Early device resolution completed: {len(entities)} entities (including specific devices)")
        except (HTTPException, Exception) as e:
            # HA client not available or resolution failed - continue with generic entities
            logger.debug(f"ℹ️ Early device resolution skipped (HA client unavailable or failed): {e}")

        # Step 1.6: Check for clarification needs (NEW)
        clarification_detector, question_generator, _, confidence_calculator = await get_clarification_services(db)

        # Build automation context for clarification detection (with area filtering)
        automation_context = {}
        try:
            import pandas as pd

            from ..clients.data_api_client import DataAPIClient
            data_api_client = DataAPIClient()

            # Apply area filter if detected
            if area_filter:
                logger.info(f"🔍 Fetching entities for area(s): {area_filter}")
                # Handle multiple areas (comma-separated)
                if ',' in area_filter:
                    areas = area_filter.split(',')
                    all_devices = []
                    all_entities = []
                    for area in areas:
                        area_devices = await data_api_client.fetch_devices(limit=100, area_id=area.strip())
                        area_entities = await data_api_client.fetch_entities(limit=200, area_id=area.strip())
                        if not (isinstance(area_devices, pd.DataFrame) and area_devices.empty):
                            all_devices.append(area_devices)
                        if not (isinstance(area_entities, pd.DataFrame) and area_entities.empty):
                            all_entities.append(area_entities)
                    # Combine results
                    devices_result = pd.concat(all_devices, ignore_index=True) if all_devices else pd.DataFrame()
                    entities_result = pd.concat(all_entities, ignore_index=True) if all_entities else pd.DataFrame()
                    # Remove duplicates
                    if not devices_result.empty and 'device_id' in devices_result.columns:
                        devices_result = devices_result.drop_duplicates(subset=['device_id'], keep='first')
                    if not entities_result.empty and 'entity_id' in entities_result.columns:
                        entities_result = entities_result.drop_duplicates(subset=['entity_id'], keep='first')
                else:
                    # Single area
                    devices_result = await data_api_client.fetch_devices(limit=100, area_id=area_filter)
                    entities_result = await data_api_client.fetch_entities(limit=200, area_id=area_filter)
            else:
                # No area filter - fetch all entities
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
                            'name': entity.get('name', ''),
                            'name_by_user': entity.get('name_by_user', ''),
                            'device_id': entity.get('device_id', ''),  # Include device_id for device name lookup
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

                # Get RAG client for historical success checking
                rag_client_for_confidence = await _get_rag_client(db)

                confidence = await confidence_calculator.calculate_confidence(
                    query=request.query,
                    extracted_entities=entities,
                    ambiguities=ambiguities,
                    base_confidence=base_confidence,
                    rag_client=rag_client_for_confidence
                )

                # Calculate adaptive threshold (Phase 1.2)
                user_preferences = None
                if getattr(settings, "adaptive_threshold_enabled", True):
                    try:
                        from ..database.crud import get_system_settings
                        system_settings = await get_system_settings(db)
                        if system_settings:
                            user_preferences = {
                                'risk_tolerance': getattr(system_settings, 'risk_tolerance', 'medium')
                            }
                    except Exception as e:
                        logger.debug(f"Failed to get user preferences: {e}")
                        # Use default from config
                        user_preferences = {
                            'risk_tolerance': getattr(settings, "default_risk_tolerance", "medium")
                        }

                # Calculate adaptive threshold (now async with RAG support)
                adaptive_threshold = await confidence_calculator.calculate_adaptive_threshold(
                    query=request.query,
                    extracted_entities=entities,
                    ambiguities=ambiguities,
                    user_preferences=user_preferences,
                    rag_client=rag_client_for_confidence
                ) if getattr(settings, "adaptive_threshold_enabled", True) else 0.85

                # NEW: Try auto-resolution before asking questions (2025 best practice)
                auto_resolved_answers = {}
                remaining_ambiguities = ambiguities
                
                if ambiguities and getattr(settings, "auto_resolution_enabled", True):
                    try:
                        from ..services.clarification import AutoResolver, ABTestingService
                        from ..services.clarification.uncertainty_quantification import UncertaintyQuantifier
                        
                        # Initialize A/B testing service
                        ab_testing = ABTestingService(
                            enabled=getattr(settings, "ab_testing_enabled", False),
                            rollout_percentage=getattr(settings, "ab_testing_rollout_percentage", 1.0)
                        )
                        
                        # Check if auto-resolution should be used for this session
                        auto_resolution_config = ab_testing.get_auto_resolution_config(
                            user_id=request.user_id,
                            session_id=None  # Will be set when session is created
                        )
                        
                        if auto_resolution_config.get('enabled', True):
                            # Initialize auto resolver
                            uncertainty_quantifier = UncertaintyQuantifier(method="bootstrap")
                            auto_resolver = AutoResolver(
                                detector=clarification_detector,
                                rag_client=rag_client_for_confidence,
                                uncertainty_quantifier=uncertainty_quantifier
                            )
                            
                            # Get user preferences for auto-resolution
                            user_prefs_for_resolution = None
                            try:
                                from ..database.crud import get_user_preferences
                                user_prefs_for_resolution = await get_user_preferences(
                                    db=db,
                                    user_id=request.user_id
                                )
                            except Exception as e:
                                logger.debug(f"Failed to get user preferences for auto-resolution: {e}")
                            
                            # Attempt auto-resolution
                            remaining_ambiguities, auto_resolved_answers = await auto_resolver.resolve_ambiguities(
                                ambiguities=ambiguities,
                                query=request.query,
                                extracted_entities=entities,
                                available_devices=automation_context,
                                user_preferences=user_prefs_for_resolution,
                                min_confidence=auto_resolution_config.get('min_confidence', 0.85)
                            )
                            
                            if auto_resolved_answers:
                                logger.info(
                                    f"✅ Auto-resolved {len(auto_resolved_answers)} ambiguities, "
                                    f"{len(remaining_ambiguities)} remaining"
                                )
                                
                                # Track auto-resolution metrics (for observability)
                                try:
                                    from ..database.models import AutoResolutionMetric
                                    
                                    # Store metrics for each auto-resolved ambiguity
                                    for amb_id, resolution in auto_resolved_answers.items():
                                        metric = AutoResolutionMetric(
                                            session_id=None,  # Will be set when session is created
                                            ambiguity_id=amb_id,
                                            query=request.query,
                                            resolution=resolution.get('entities', []),
                                            confidence=resolution.get('confidence', 0.0),
                                            method=resolution.get('method', 'unknown'),
                                            latency_ms=resolution.get('latency_ms', 0.0),
                                            created_at=datetime.utcnow()
                                        )
                                        db.add(metric)
                                    
                                    await db.commit()
                                except Exception as e:
                                    logger.warning(f"Failed to track auto-resolution metrics: {e}")
                                    await db.rollback()
                        else:
                            logger.debug(f"Auto-resolution disabled for this session (A/B test variant: {auto_resolution_config.get('variant')})")
                    
                    except Exception as e:
                        logger.warning(f"⚠️ Auto-resolution failed, falling back to questions: {e}", exc_info=True)
                        # Fall back to all ambiguities if auto-resolution fails
                        remaining_ambiguities = ambiguities
                        auto_resolved_answers = {}
                
                # Update ambiguities to remaining ones (after auto-resolution)
                ambiguities = remaining_ambiguities

                # Check if clarification is needed (using remaining ambiguities)
                if confidence_calculator.should_ask_clarification(confidence, ambiguities, threshold=adaptive_threshold):
                    # Generate questions
                    if question_generator:
                        questions = await question_generator.generate_questions(
                            ambiguities=ambiguities,
                            query=request.query,
                            context=automation_context
                        )

                    # NEW: Apply user preferences (skip questions with high consistency, pre-fill answers)
                    pre_filled_answers = {}
                    if questions:
                        try:
                            from ...services.learning.user_preference_learner import UserPreferenceLearner
                            from ...database.models import SystemSettings
                            
                            # Check if learning is enabled
                            settings_result = await db.execute(select(SystemSettings).limit(1))
                            settings_obj = settings_result.scalar_one_or_none()
                            if settings_obj and getattr(settings_obj, 'enable_qa_learning', True):
                                preference_learner = UserPreferenceLearner()
                                filtered_questions, pre_filled = await preference_learner.apply_user_preferences(
                                    db=db,
                                    user_id=request.user_id,
                                    questions=questions
                                )
                                questions = filtered_questions
                                pre_filled_answers = pre_filled
                                
                                if pre_filled_answers:
                                    logger.info(f"✅ Applied user preferences: {len(pre_filled_answers)} answers pre-filled, {len(questions)} questions remaining")
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to apply user preferences: {e}")
                            # Non-critical: continue with all questions

                    # NEW: Check for cached answers from past sessions
                    cached_answers = {}
                    if questions:
                        try:
                            from ..database.crud import find_similar_past_answers
                            
                            # Get RAG client if available for semantic matching
                            rag_client = None
                            if db:
                                try:
                                    from ..services.rag.rag_client import RAGClient
                                    openvino_url = os.getenv("OPENVINO_SERVICE_URL", "http://openvino-service:8019")
                                    rag_client = RAGClient(
                                        openvino_service_url=openvino_url,
                                        db_session=db
                                    )
                                except Exception as e:
                                    logger.debug(f"RAG client not available for answer caching: {e}")
                            
                            # Convert questions to dict format for matching
                            questions_dict = [
                                {
                                    'id': q.id,
                                    'question_text': q.question_text,
                                    'question_id': q.id  # Alias for compatibility
                                }
                                for q in questions
                            ]
                            
                            # Find similar past answers
                            cached_answers = await find_similar_past_answers(
                                db=db,
                                user_id=request.user_id,
                                current_questions=questions_dict,
                                rag_client=rag_client,
                                similarity_threshold=0.75,  # 75% similarity threshold
                                ha_client=None  # Entity validation can be added later
                            )
                            
                            if cached_answers:
                                logger.info(f"✅ Found {len(cached_answers)} cached answers from past sessions")
                                
                                # Pre-fill answers in questions (add cached_answer field)
                                # Merge with preference-based pre-filled answers
                                for question in questions:
                                    # Check preference-based pre-fill first (higher priority)
                                    if question.id in pre_filled_answers:
                                        if not hasattr(question, 'cached_answer'):
                                            question.cached_answer = pre_filled_answers[question.id]
                                        logger.debug(f"Pre-filled answer from preference for question {question.id}")
                                    elif question.id in cached_answers:
                                        cached_data = cached_answers[question.id]
                                        # Store cached answer as metadata on question object
                                        if not hasattr(question, 'cached_answer'):
                                            question.cached_answer = cached_data['answer_text']
                                        if not hasattr(question, 'cached_entities'):
                                            question.cached_entities = cached_data.get('selected_entities')
                                        logger.debug(f"Pre-filled answer from cache for question {question.id}")
                                        if not hasattr(question, 'cached_similarity'):
                                            question.cached_similarity = cached_data.get('similarity', 0.0)
                                        logger.debug(
                                            f"Pre-filled answer for question '{question.question_text[:50]}...': "
                                            f"'{cached_data['answer_text'][:50]}...' (similarity={cached_data.get('similarity', 0.0):.2f})"
                                        )
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to retrieve cached answers: {e}", exc_info=True)
                            # Continue without cached answers - not critical

                    # Create clarification session
                    if questions or auto_resolved_answers:
                        clarification_session_id = f"clarify-{uuid.uuid4().hex[:8]}"

                        # Create in-memory session (for real-time access)
                        session = ClarificationSession(
                            session_id=clarification_session_id,
                            original_query=request.query,
                            questions=questions,
                            current_confidence=confidence,
                            confidence_threshold=adaptive_threshold,  # Use adaptive threshold
                            ambiguities=ambiguities,
                            query_id=query_id
                        )
                        
                        # Store auto-resolved answers in session context (for later use)
                        if auto_resolved_answers:
                            if not hasattr(session, 'auto_resolved_answers'):
                                session.auto_resolved_answers = auto_resolved_answers
                            logger.info(f"✅ Stored {len(auto_resolved_answers)} auto-resolved answers in session")
                        _clarification_sessions[clarification_session_id] = session

                        # Persist to database
                        try:
                            # First, create a minimal query record so the foreign key exists
                            # We'll update it with full data later
                            minimal_query = AskAIQueryModel(
                                query_id=query_id,
                                original_query=request.query,
                                user_id=request.user_id,
                                parsed_intent='pending',  # Will be updated later
                                extracted_entities=entities,
                                suggestions=[],
                                confidence=confidence,
                                processing_time_ms=0  # Will be updated later
                            )
                            db.add(minimal_query)
                            await db.flush()  # Flush to make query_id available for foreign key

                            # Convert dataclass questions to dicts for JSON storage
                            questions_json = [
                                {
                                    'id': q.id,
                                    'category': q.category,
                                    'question_text': q.question_text,
                                    'question_type': q.question_type.value if hasattr(q.question_type, 'value') else str(q.question_type),
                                    'options': q.options,
                                    'context': q.context,
                                    'priority': q.priority,
                                    'related_entities': q.related_entities,
                                    'ambiguity_id': q.ambiguity_id,
                                    # Include cached answer if available
                                    'cached_answer': getattr(q, 'cached_answer', None),
                                    'cached_entities': getattr(q, 'cached_entities', None),
                                    'cached_similarity': getattr(q, 'cached_similarity', None)
                                } for q in questions
                            ]

                            # Convert ambiguities to dicts
                            ambiguities_json = [
                                {
                                    'id': a.id,
                                    'type': a.type.value if hasattr(a.type, 'value') else str(a.type),
                                    'severity': a.severity.value if hasattr(a.severity, 'value') else str(a.severity),
                                    'description': a.description,
                                    'context': a.context,
                                    'related_entities': a.related_entities,
                                    'detected_text': a.detected_text
                                } for a in ambiguities
                            ] if ambiguities else []

                            db_session = ClarificationSessionDB(
                                confidence_threshold=adaptive_threshold,  # Use adaptive threshold
                                session_id=clarification_session_id,
                                original_query_id=query_id,
                                original_query=request.query,
                                user_id=request.user_id,
                                questions=questions_json,
                                ambiguities=ambiguities_json,
                                current_confidence=confidence,
                                status='in_progress'
                            )
                            db.add(db_session)
                            await db.flush()  # Flush instead of commit - will commit with query update later
                            logger.info(f"✅ Clarification session {clarification_session_id} saved to database (original_query_id={query_id})")
                        except Exception as e:
                            logger.error(f"Failed to save clarification session to database: {e}", exc_info=True)
                            # Don't fail the request, continue with in-memory session
                            # Rollback the minimal query if clarification session failed
                            try:
                                await db.rollback()
                            except Exception as e:
                                logger.debug(f"Rollback failed (non-fatal): {e}")

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
                request.user_id,
                db_session=db,
                clarification_context=None,
                query_id=query_id,  # Pass query_id for metrics tracking
                area_filter=area_filter  # Pass area_filter for location filtering
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
                                from ..clients.data_api_client import DataAPIClient
                                from ..services.entity_validator import EntityValidator
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
                        from ..services.clarification.models import (
                            Ambiguity,
                            AmbiguitySeverity,
                            AmbiguityType,
                        )
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

        # Step 5: Save query to database (or update if already exists from clarification session)
        existing_query = await db.get(AskAIQueryModel, query_id)
        if existing_query:
            # Update existing query record (created earlier for clarification session)
            existing_query.parsed_intent = parsed_intent
            existing_query.extracted_entities = entities
            existing_query.suggestions = suggestions
            existing_query.confidence = confidence
            existing_query.processing_time_ms = int(processing_time)
            query_record = existing_query
        else:
            # Create new query record
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
                    'related_entities': q.related_entities,
                    # Include cached answer if available
                    'cached_answer': getattr(q, 'cached_answer', None),
                    'cached_entities': getattr(q, 'cached_entities', None),
                    'cached_similarity': getattr(q, 'cached_similarity', None)
                }
                for q in questions
            ]

        message = None
        if questions:
            # Build a detailed message explaining what was found and what's ambiguous
            # Use specific device names from resolved entities (early device resolution)
            device_names = []
            for e in entities:
                if e.get('type') == 'device':
                    # Prefer friendly_name if available, fallback to name
                    device_name = e.get('friendly_name') or e.get('name', '')
                    if device_name and device_name not in device_names:
                        device_names.append(device_name)

            area_names = [e.get('name', '') for e in entities if e.get('type') == 'area']

            # If we have specific devices from early resolution, show them
            if device_names:
                device_info = f" I detected these devices: {', '.join(device_names)}."
            else:
                # Fallback to generic device types if early resolution didn't work
                generic_device_names = [e.get('name', '') for e in entities if e.get('type') == 'device']
                device_info = f" I detected these devices: {', '.join(generic_device_names) if generic_device_names else 'none'}." if generic_device_names else ""

            area_info = f" I detected these locations: {', '.join(area_names)}." if area_names else ""

            # Include auto-resolved information in message if available
            auto_resolved_info = ""
            if auto_resolved_answers:
                auto_resolved_info = f" I've automatically resolved {len(auto_resolved_answers)} ambiguity(ies) based on context."
            
            message = f"I found some ambiguities in your request.{device_info}{area_info}{auto_resolved_info} Please answer {len(questions)} question(s) to help me create the automation accurately."
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
        ) from e


def _rebuild_user_query_from_qa(
    original_query: str,
    clarification_context: dict[str, Any]
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


def _generate_user_friendly_prompt(
    original_query: str,
    clarification_context: dict[str, Any]
) -> str:
    """
    Generate a user-friendly prompt that summarizes the original request
    with all clarification answers incorporated.
    
    This is what the AI will use to generate the automation, formatted
    in a way that's easy for users to understand.
    
    Args:
        original_query: Original user query
        clarification_context: Dictionary with questions_and_answers
        
    Returns:
        User-friendly prompt string
    """
    parts = [f"Original request: {original_query}"]

    qa_list = clarification_context.get('questions_and_answers', [])
    if qa_list:
        parts.append("\nClarifications provided:")
        for qa in qa_list:
            answer_text = qa.get('answer', '')
            if qa.get('selected_entities'):
                entities_str = ', '.join(qa['selected_entities'])
                answer_text += f" (Selected: {entities_str})"
            parts.append(f"  • {answer_text}")

    return "\n".join(parts)


async def _re_enrich_entities_from_qa(
    entities: list[dict[str, Any]],
    clarification_context: dict[str, Any],
    ha_client: HomeAssistantClient | None = None
) -> list[dict[str, Any]]:
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
            # Create new entity entry with proper friendly name from Home Assistant
            friendly_name = entity_id.split('.')[-1].replace('_', ' ').title() if '.' in entity_id else entity_id  # Fallback
            area_id = None

            # Try to get proper friendly name from Home Assistant using EntityAttributeService
            if ha_client:
                try:
                    from ..services.entity_attribute_service import EntityAttributeService
                    attribute_service = EntityAttributeService(ha_client)
                    enriched = await attribute_service.enrich_entity_with_attributes(entity_id)
                    if enriched:
                        friendly_name = enriched.get('friendly_name', friendly_name)
                        area_id = enriched.get('area_id')
                        logger.info(f"✅ Enriched entity {entity_id} with friendly_name: {friendly_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to enrich entity {entity_id} with EntityAttributeService: {e}, using fallback")

            new_entity = {
                'entity_id': entity_id,
                'name': friendly_name,  # Use friendly_name as name too
                'friendly_name': friendly_name,
                'type': 'device',
                'domain': entity_id.split('.')[0] if '.' in entity_id else 'unknown',
                'area_id': area_id,
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
    db: AsyncSession = Depends(get_db),
    ha_client: HomeAssistantClient = Depends(get_ha_client)
) -> ClarificationResponse:
    """
    Provide clarification answers to questions.
    
    Processes user answers and either:
    - Generates more questions if needed
    - Generates suggestions if confidence threshold is met
    """
    logger.info(f"🔍 Processing clarification for session {request.session_id}")

    try:
        # Validation: Check request data
        if not request.session_id:
            logger.error("❌ Missing session_id in request")
            raise HTTPException(
                status_code=400,
                detail="session_id is required"
            )

        if not request.answers or len(request.answers) == 0:
            logger.error("❌ No answers provided in request")
            raise HTTPException(
                status_code=400,
                detail="At least one answer is required"
            )

        # Get session
        session = _clarification_sessions.get(request.session_id)
        if not session:
            logger.error(f"❌ Clarification session {request.session_id} not found in memory")
            raise HTTPException(
                status_code=404,
                detail=f"Clarification session {request.session_id} not found"
            )

        # Validation: Check session data
        if not session.original_query:
            logger.error(f"❌ Session {request.session_id} has no original_query")
            raise HTTPException(
                status_code=500,
                detail="Session is missing original query"
            )

        if not session.questions:
            logger.warning(f"⚠️ Session {request.session_id} has no questions")

        logger.info(f"✅ Session validation passed: query='{session.original_query[:100]}...', questions={len(session.questions)}, answers={len(session.answers)}")

        # Get clarification services
        logger.info("🔧 Initializing clarification services")
        _, _, answer_validator, confidence_calculator = await get_clarification_services(db)
        if not answer_validator or not confidence_calculator:
            logger.error("❌ Failed to initialize clarification services")
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize clarification services"
            )
        logger.info("✅ Clarification services initialized")

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

        # Add answers to session - but deduplicate first to prevent duplicate Q&A pairs
        # If user resubmits, only keep the most recent answer for each question
        # Optimized: Use index map for O(1) lookups instead of O(n²) nested loop
        answer_index = {a.question_id: i for i, a in enumerate(session.answers)}
        new_answers_to_add = []

        for validated_answer in validated_answers:
            if validated_answer.question_id in answer_index:
                # Update existing answer - O(1) lookup
                session.answers[answer_index[validated_answer.question_id]] = validated_answer
                logger.info(f"🔄 Updated answer for question {validated_answer.question_id}")
            else:
                # New question answer
                new_answers_to_add.append(validated_answer)
                logger.info(f"➕ Added new answer for question {validated_answer.question_id}")

        # Add new answers
        session.answers.extend(new_answers_to_add)
        session.rounds_completed += 1

        logger.info(f"📊 Session now has {len(session.answers)} unique answers across {session.rounds_completed} rounds")
        logger.info(f"📋 Current session answers breakdown: {[f'{a.question_id}: {a.answer_text[:50]}...' for a in session.answers]}")

        # NEW: Learn user preferences from answers
        try:
            from ...services.learning.user_preference_learner import UserPreferenceLearner
            from ...database.models import SystemSettings
            
            # Check if learning is enabled
            settings_result = await db.execute(select(SystemSettings).limit(1))
            settings_obj = settings_result.scalar_one_or_none()
            if settings_obj and getattr(settings_obj, 'enable_qa_learning', True):
                preference_learner = UserPreferenceLearner()
                
                # Learn from each new answer
                for validated_answer in validated_answers:
                    question = next((q for q in session.questions if q.id == validated_answer.question_id), None)
                    if question:
                        await preference_learner.learn_user_preference(
                            db=db,
                            user_id=request.user_id or "anonymous",
                            question_category=getattr(question, 'category', 'unknown'),
                            question_pattern=question.question_text.lower().strip(),
                            answer_pattern=validated_answer.answer_text.lower().strip()
                        )
                
                logger.debug(f"✅ Learned preferences from {len(validated_answers)} answers")
        except Exception as e:
            logger.warning(f"⚠️ Failed to learn user preferences: {e}")
            # Non-critical: continue even if preference learning fails

        # NEW: Track previous confidence before recalculating
        previous_confidence = session.current_confidence

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
            if _get_ambiguity_id(amb) not in resolved_ambiguity_ids
        ]

        # OPTION 2: Check RAG with enriched query after answers received
        # Build enriched query from original + all previous answers (including new ones)
        all_answers = session.answers  # Includes all previous answers + new ones
        enriched_query_from_answers = None
        rag_confidence_boost = 0.0

        if all_answers:
            # Build enriched query from all answers
            all_qa_context = {
                'original_query': session.original_query,
                'questions_and_answers': [
                    {
                        'question': next((q.question_text for q in session.questions if q.id == a.question_id), 'Unknown question'),
                        'answer': a.answer_text,
                        'selected_entities': a.selected_entities,
                        'category': next((q.category for q in session.questions if q.id == a.question_id), 'unknown')
                    }
                    for a in all_answers
                    if a.validated  # Only include validated answers
                ]
            }

            enriched_query_from_answers = _rebuild_user_query_from_qa(
                original_query=session.original_query,
                clarification_context=all_qa_context
            )

            # Check RAG for similar enriched queries with lower threshold (0.80) for enriched queries
            try:
                rag_client = await _get_rag_client(db)
                if rag_client and enriched_query_from_answers:
                    # Use hybrid retrieval (2025 best practice: dense + sparse + reranking)
                    similar_queries = await rag_client.retrieve_hybrid(
                        query=enriched_query_from_answers,
                        knowledge_type='query',
                        top_k=1,
                        min_similarity=0.80,  # Lower threshold for enriched queries (they're more specific)
                        use_query_expansion=True,
                        use_reranking=True
                    )

                    # Hybrid retrieval returns 'final_score' or 'hybrid_score', fallback to 'similarity'
                    top_result = similar_queries[0] if similar_queries else None
                    if top_result:
                        similarity = top_result.get('final_score') or top_result.get('hybrid_score') or top_result.get('similarity', 0.0)
                        if similarity > 0.80:
                            success_score = top_result.get('success_score', 0.5)

                            # Boost confidence based on similarity and historical success
                            # Higher similarity and success_score = bigger boost
                            rag_confidence_boost = min(0.15, similarity * success_score * 0.2)

                            logger.info(
                                f"📈 Found similar enriched query in RAG (similarity={similarity:.2f}, "
                                f"success_score={success_score:.2f}) - boosting confidence by +{rag_confidence_boost:.2f}"
                            )
            except Exception as e:
                # Non-critical: continue even if RAG check fails
                logger.debug(f"⚠️ RAG check with enriched query failed: {e}")

        # Calculate base confidence with RAG boost from Option 2
        base_confidence_with_rag = 0.5 + rag_confidence_boost

        # Get RAG client for historical success checking (Option 3)
        rag_client_for_confidence = await _get_rag_client(db)

        session.current_confidence = await confidence_calculator.calculate_confidence(
            query=session.original_query,
            extracted_entities=[],  # TODO: Get from session
            ambiguities=remaining_ambiguities_for_confidence,  # Only count unresolved ambiguities
            clarification_answers=all_answers,  # Use ALL answers, not just new ones
            base_confidence=base_confidence_with_rag,  # Include RAG boost from Option 2
            rag_client=rag_client_for_confidence  # Option 3: Historical success checking
        )

        # Calculate confidence delta
        confidence_delta = session.current_confidence - previous_confidence if previous_confidence > 0 else None

        # Generate smart summary of what improved
        confidence_summary = _generate_confidence_summary(
            previous_confidence=previous_confidence,
            current_confidence=session.current_confidence,
            confidence_delta=confidence_delta,
            validated_answers=validated_answers,
            session=session,
            resolved_ambiguity_ids=resolved_ambiguity_ids
        )

        # Format confidence delta for logging
        delta_str = f"{confidence_delta:+.2f}" if confidence_delta is not None else "N/A"
        logger.info(f"📊 Confidence recalculated: {session.current_confidence:.2f} (previous: {previous_confidence:.2f}, delta: {delta_str}, threshold: {session.confidence_threshold:.2f}, answers: {len(all_answers)}, resolved ambiguities: {len(resolved_ambiguity_ids)}, remaining: {len(remaining_ambiguities_for_confidence)})")

        # Check if we should proceed or ask more questions
        if (session.current_confidence >= session.confidence_threshold or
            session.rounds_completed >= session.max_rounds):
            # Track outcome: user proceeded (Phase 2.1)
            try:
                outcome_tracker = ClarificationOutcomeTracker()
                await outcome_tracker.track_outcome(
                    db=db,
                    session_id=session.session_id,
                    final_confidence=session.current_confidence,
                    proceeded=True,
                    suggestion_approved=None,  # Will be updated when suggestion is approved/rejected
                    rounds=session.rounds_completed
                )

                # Track calibration feedback (Phase 1.1)
                if confidence_calculator.calibrator:
                    try:
                        from ..database.crud import store_clarification_confidence_feedback

                        # Count ambiguities for calibration
                        critical_count = sum(
                            1 for amb in session.ambiguities
                            if amb.severity == AmbiguitySeverity.CRITICAL
                        )

                        # Get raw confidence before calibration (we need to recalculate or store it)
                        # For now, use current confidence as approximation
                        raw_confidence = session.current_confidence

                        await store_clarification_confidence_feedback(
                            db=db,
                            session_id=session.session_id,
                            raw_confidence=raw_confidence,
                            proceeded=True,
                            suggestion_approved=None,  # Will be updated later
                            ambiguity_count=len(session.ambiguities),
                            critical_ambiguity_count=critical_count,
                            rounds=session.rounds_completed,
                            answer_count=len(all_answers)
                        )

                        # Add feedback to calibrator
                        confidence_calculator.calibrator.add_feedback(
                            raw_confidence=raw_confidence,
                            actually_proceeded=True,
                            suggestion_approved=None,
                            ambiguity_count=len(session.ambiguities),
                            critical_ambiguity_count=critical_count,
                            rounds=session.rounds_completed,
                            answer_count=len(all_answers)
                        )
                    except Exception as e:
                        logger.warning(f"Failed to track calibration feedback: {e}")
                        # Non-blocking: continue even if tracking fails
            except Exception as e:
                logger.warning(f"Failed to track clarification outcome: {e}")
                # Non-blocking: continue even if tracking fails

            # Generate suggestions
            session.status = "complete"

            # Build clarification context for prompt
            # Include ALL answers from all rounds, not just validated_answers
            all_qa_list = [
                {
                    'question': next((q.question_text for q in session.questions if q.id == answer.question_id), 'Unknown question'),
                    'answer': answer.answer_text,
                    'selected_entities': answer.selected_entities,
                    'category': next((q.category for q in session.questions if q.id == answer.question_id), 'unknown')
                }
                for answer in all_answers  # Use all_answers to include all rounds
            ]

            clarification_context = {
                'original_query': session.original_query,
                'questions_and_answers': all_qa_list
            }
            logger.info(f"📝 Built clarification context with {len(clarification_context['questions_and_answers'])} Q&A pairs for prompt")
            for i, qa in enumerate(clarification_context['questions_and_answers'], 1):
                logger.info(f"  Q&A {i}: Q: {qa['question']} | A: {qa['answer']} | Entities: {qa.get('selected_entities', [])}")

            # NEW: Rebuild enriched user query from original question + Q&A answers
            logger.info(f"🔧 Step 1: Rebuilding enriched query from {len(clarification_context.get('questions_and_answers', []))} Q&A pairs")
            try:
                enriched_query = _rebuild_user_query_from_qa(
                    original_query=session.original_query,
                    clarification_context=clarification_context
                )
                # Validation: Ensure enriched_query is not None or empty
                if not enriched_query or not enriched_query.strip():
                    logger.error("❌ Enriched query is empty or None after rebuilding")
                    raise ValueError("Enriched query cannot be empty")
                logger.info(f"📝 Step 1 complete: Rebuilt enriched query (length: {len(enriched_query)} chars): '{enriched_query[:200]}...'")
            except Exception as e:
                logger.error(f"❌ Failed to rebuild enriched query: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to rebuild enriched query: {str(e)}"
                ) from e

            # NEW: Re-extract entities from enriched query (original + Q&A)
            logger.info("🔧 Step 2: Extracting entities from enriched query (timeout: 30s)")
            try:
                entities = await asyncio.wait_for(
                    extract_entities_with_ha(enriched_query),
                    timeout=30.0
                )
                logger.info(f"🔍 Step 2 complete: Re-extracted {len(entities)} entities from enriched query")
                if not entities:
                    logger.warning("⚠️ No entities extracted from enriched query - continuing with empty list")
            except asyncio.TimeoutError as e:
                logger.error("❌ Entity extraction timed out after 30 seconds")
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "timeout",
                        "message": "Entity extraction is taking longer than expected. Please try again.",
                        "retry_after": 30
                    }
                ) from e
            except Exception as e:
                logger.error(f"❌ Failed to extract entities from enriched query: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to extract entities: {str(e)}"
                ) from e

            # NEW: Re-enrich devices based on selected entities from Q&A answers
            logger.info("🔧 Step 3: Re-enriching entities with Q&A information (timeout: 45s)")
            try:
                entities = await asyncio.wait_for(
                    _re_enrich_entities_from_qa(
                        entities=entities,
                        clarification_context=clarification_context,
                        ha_client=ha_client
                    ),
                    timeout=45.0
                )
                logger.info(f"✅ Step 3 complete: Re-enriched entities with Q&A information: {len(entities)} entities")
            except asyncio.TimeoutError as e:
                logger.error("❌ Entity re-enrichment timed out after 45 seconds")
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "timeout",
                        "message": "Entity enrichment is taking longer than expected. Please try again.",
                        "retry_after": 30
                    }
                ) from e
            except Exception as e:
                logger.error(f"❌ Failed to re-enrich entities: {e}", exc_info=True)
                # Don't fail the request - continue with un-enriched entities
                logger.warning("⚠️ Continuing with un-enriched entities due to re-enrichment failure")

            # Generate suggestions WITH enriched query and clarification context
            logger.info(f"🔧 Step 4: Generating suggestions from enriched query (timeout: {CLARIFICATION_SUGGESTION_TIMEOUT_SECONDS}s)")

            # Extract area_filter from original query (for location filtering)
            from ..utils.area_detection import extract_area_from_request
            area_filter = extract_area_from_request(session.original_query)
            if area_filter:
                logger.info(f"📍 Extracted area_filter from original query: '{area_filter}'")

            # Retry logic for OpenAI failures
            max_retries = CLARIFICATION_RETRY_MAX_ATTEMPTS
            retry_delay = CLARIFICATION_RETRY_DELAY_SECONDS
            suggestions = None

            for attempt in range(max_retries):
                try:
                    suggestions = await asyncio.wait_for(
                        generate_suggestions_from_query(
                            enriched_query,  # NEW: Use enriched query instead of original
                            entities,  # NEW: Re-extracted and re-enriched entities
                            "anonymous",  # TODO: Get from session
                            db_session=db,
                            clarification_context=clarification_context,  # Pass structured clarification
                            query_id=getattr(session, 'query_id', None),  # Pass query_id for metrics tracking
                            area_filter=area_filter  # Pass area_filter for location filtering
                        ),
                        timeout=CLARIFICATION_SUGGESTION_TIMEOUT_SECONDS
                    )
                    logger.info(f"✅ Step 4 complete: Generated {len(suggestions)} suggestions")
                    break  # Success, exit retry loop

                except asyncio.TimeoutError as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ Attempt {attempt + 1}/{max_retries} timed out, retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"❌ All {max_retries} attempts timed out")
                        raise HTTPException(
                            status_code=504,
                            detail={
                                "error": "timeout",
                                "message": "AI suggestion generation is taking longer than expected. This may be due to a complex request. Please try simplifying your query or try again later.",
                                "retry_after": 60
                            }
                        ) from e

                except ValueError as e:
                    error_str = str(e)
                    # Catch all variations of empty content/response errors
                    if ("Empty content from OpenAI" in error_str or
                        "Empty response from OpenAI" in error_str):
                        logger.error(f"❌ OpenAI returned empty content on attempt {attempt + 1}/{max_retries} (likely rate limit or token overflow): {error_str}")
                        if attempt < max_retries - 1:
                            logger.warning(f"⚠️ Retrying in {retry_delay}s...")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            raise HTTPException(
                                status_code=503,
                                detail={
                                    "error": "api_error",
                                    "message": "AI service temporarily unavailable. This may be due to high demand or a complex request. Please try again in a moment.",
                                    "retry_after": 30
                                }
                            ) from e
                    elif "entity mapping failures" in error_str.lower() or "skipped" in error_str.lower():
                        # Entity mapping failure - don't retry, provide helpful error
                        logger.error(f"❌ Entity mapping failed during suggestion generation: {e}", exc_info=True)
                        raise HTTPException(
                            status_code=500,
                            detail={
                                "error": "suggestion_generation_failed",
                                "message": f"Failed to generate suggestions: {str(e)}. This usually means the device names don't match available entities. Please check your device names and try again.",
                                "session_id": request.session_id
                            }
                        ) from e
                    else:
                        # Other ValueError - don't retry
                        logger.error(f"❌ ValueError during suggestion generation: {e}", exc_info=True)
                        # Sanitize error message in production
                        if os.getenv("ENVIRONMENT") == "production":
                            error_message = "An internal error occurred during suggestion generation. Please try again."
                        else:
                            error_message = f"Failed to generate suggestions: {str(e)}"
                        raise HTTPException(
                            status_code=500,
                            detail={
                                "error": "internal_error",
                                "message": error_message
                            }
                        ) from e

                except Exception as e:
                    logger.error(f"❌ Unexpected error on attempt {attempt + 1}/{max_retries}: {e}", exc_info=True)
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ Retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        # Sanitize error message in production
                        if os.getenv("ENVIRONMENT") == "production":
                            error_message = f"Failed to generate suggestions after {max_retries} attempts. Please try again."
                        else:
                            error_message = f"Failed to generate suggestions after {max_retries} attempts: {str(e)}"
                        raise HTTPException(
                            status_code=500,
                            detail={
                                "error": "internal_error",
                                "message": error_message
                            }
                        ) from e

            # Validate suggestions were generated
            if suggestions is None:
                logger.error("❌ Suggestions is None after generation loop")
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "internal_error",
                        "message": "Failed to generate suggestions (no data returned)"
                    }
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

            # Create database query record so suggestions can be approved
            # Use session_id as query_id so approval endpoint can find it
            try:
                query_record = AskAIQueryModel(
                    query_id=request.session_id,  # Use session_id as query_id
                    original_query=session.original_query,
                    user_id="anonymous",  # TODO: Get from session
                    parsed_intent=None,  # Not parsed in clarification flow
                    extracted_entities=entities,  # Re-extracted entities
                    suggestions=suggestions,
                    confidence=session.current_confidence,
                    processing_time_ms=0  # Not tracked in clarification flow
                )
                db.add(query_record)
                await db.commit()
                await db.refresh(query_record)
                logger.info(f"✅ Created query record {request.session_id} with {len(suggestions)} suggestions")

                # Update clarification session in database to link the generated query
                try:
                    stmt = update(ClarificationSessionDB).where(
                        ClarificationSessionDB.session_id == request.session_id
                    ).values(
                        clarification_query_id=request.session_id,
                        status='complete',
                        completed_at=datetime.utcnow(),
                        answers=[
                            {
                                'question_id': a.question_id,
                                'answer_text': a.answer_text,
                                'selected_entities': a.selected_entities,
                                'confidence': a.confidence,
                                'validated': a.validated
                            } for a in session.answers
                        ],
                        current_confidence=session.current_confidence,
                        rounds_completed=session.rounds_completed
                    )
                    await db.execute(stmt)
                    await db.commit()
                    logger.info(f"✅ Updated clarification session {request.session_id} with clarification_query_id={request.session_id}")
                    
                    # NEW: Store clarification questions in semantic_knowledge for future answer caching
                    try:
                        rag_client = await _get_rag_client(db)
                        if rag_client:
                            for question in session.questions:
                                # Find matching answer
                                answer = next(
                                    (a for a in session.answers if a.question_id == question.id),
                                    None
                                )
                                
                                if answer:
                                    await rag_client.store(
                                        text=question.question_text,
                                        knowledge_type='clarification_question',  # NEW type for answer caching
                                        metadata={
                                            'question_id': question.id,
                                            'answer_text': answer.answer_text,
                                            'selected_entities': answer.selected_entities,
                                            'session_id': request.session_id,
                                            'user_id': session.original_query_id,  # Use original query context
                                            'category': question.category,
                                            'created_at': datetime.utcnow().isoformat()
                                        },
                                        success_score=1.0  # Start high, can decrease if user modifies
                                    )
                            logger.debug(f"✅ Stored {len(session.questions)} clarification questions in semantic_knowledge")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to store clarification questions in semantic_knowledge: {e}")
                        # Non-critical, continue
                        
                except Exception as e:
                    logger.error(f"Failed to update clarification session in database: {e}", exc_info=True)
                    # Don't fail the request

                # OPTION 1: Auto-store enriched query in RAG knowledge base for future learning
                # This enables the system to learn from successful clarification sessions
                try:
                    rag_client = await _get_rag_client(db)
                    if rag_client:
                        # Store enriched query (original + Q&A answers) for semantic similarity matching
                        # Using enriched_query that was built earlier (line 4619-4623)
                        await rag_client.store(
                            text=enriched_query,  # Enriched query with original + all Q&A answers
                            knowledge_type='query',
                            metadata={
                                'query_id': request.session_id,
                                'original_query': session.original_query,
                                'confidence': session.current_confidence,
                                'clarification_answers': len(all_answers),
                                'resolved_entities': len(entities),
                                'questions_count': len(session.questions),
                                'rounds_completed': session.rounds_completed,
                                'user_id': "anonymous"  # TODO: Get from session when available
                            },
                            success_score=session.current_confidence  # Use final confidence as success indicator
                        )
                        logger.info(f"✅ Stored enriched query in RAG knowledge base for future learning (confidence: {session.current_confidence:.2f})")
                    else:
                        logger.debug("ℹ️ RAG client not available - skipping enriched query storage")
                except Exception as e:
                    # Non-critical: continue even if RAG storage fails
                    logger.warning(f"⚠️ Failed to store enriched query in RAG knowledge base: {e}")

                # Track Q&A outcome for learning
                try:
                    from ...services.learning.qa_outcome_tracker import QAOutcomeTracker
                    from ...services.learning.question_quality_tracker import QuestionQualityTracker
                    from ...database.models import SystemSettings
                    
                    # Check if learning is enabled
                    settings_result = await db.execute(select(SystemSettings).limit(1))
                    settings = settings_result.scalar_one_or_none()
                    if settings and getattr(settings, 'enable_qa_learning', True):
                        outcome_tracker = QAOutcomeTracker()
                        await outcome_tracker.track_qa_outcome(
                            db=db,
                            session_id=request.session_id,
                            questions_count=len(session.questions),
                            confidence_achieved=session.current_confidence,
                            outcome_type='automation_created' if suggestions else 'abandoned',
                            automation_id=None  # Will be updated when automation is deployed
                        )
                        logger.debug(f"✅ Tracked Q&A outcome for session {request.session_id}")
                        
                        # Track question quality (initial tracking - will be updated when automation deployed)
                        if suggestions:
                            quality_tracker = QuestionQualityTracker()
                            previous_confidence = getattr(session, 'previous_confidence', 0.0)
                            confidence_impact = session.current_confidence - previous_confidence
                            
                            for question in session.questions:
                                await quality_tracker.track_question_quality(
                                    db=db,
                                    question_id=question.id,
                                    question_text=question.question_text,
                                    question_category=getattr(question, 'category', None),
                                    outcome='success' if suggestions else None,
                                    confidence_impact=confidence_impact if confidence_impact > 0 else None
                                )
                            logger.debug(f"✅ Tracked question quality for {len(session.questions)} questions")
                            
                            # Feed outcome to RL calibrator for confidence prediction improvement
                            try:
                                from ...services.clarification.rl_calibrator import RLConfidenceCalibrator
                                rl_calibrator = RLConfidenceCalibrator()
                                
                                # Get predicted confidence (from before clarification)
                                predicted_confidence = previous_confidence if previous_confidence > 0 else session.current_confidence
                                
                                # Actual outcome: True if suggestions were generated (proceeded)
                                actual_outcome = bool(suggestions)
                                
                                # Add feedback to RL calibrator
                                rl_calibrator.add_feedback(
                                    predicted_confidence=predicted_confidence,
                                    actual_outcome=actual_outcome,
                                    ambiguity_count=len(session.ambiguities) if hasattr(session, 'ambiguities') else 0,
                                    critical_ambiguity_count=len([a for a in (session.ambiguities or []) if getattr(a, 'severity', None) == 'critical']),
                                    rounds=session.rounds_completed,
                                    answer_count=len(session.answers),
                                    auto_train=True
                                )
                                logger.debug(f"✅ Fed outcome to RL calibrator: predicted={predicted_confidence:.2f}, actual={actual_outcome}")
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to feed outcome to RL calibrator: {e}")
                                # Non-critical: continue
                except Exception as e:
                    logger.warning(f"⚠️ Failed to track Q&A outcome: {e}")
                    # Non-critical: continue even if tracking fails

            except Exception as e:
                logger.error(f"⚠️ Failed to create query record for clarification session {request.session_id}: {e}", exc_info=True)
                # Continue anyway - suggestions are still returned, but approval might fail
                # Rollback to avoid partial state
                await db.rollback()

            # Generate user-friendly enriched prompt
            enriched_prompt = _generate_user_friendly_prompt(
                original_query=session.original_query,
                clarification_context=clarification_context
            )
            logger.info("📝 Generated enriched prompt for user display")

            # Debug: Log all Q&A pairs being returned
            qa_count = len(clarification_context['questions_and_answers'])
            logger.info(f"🔍 Returning {qa_count} Q&A pairs in response:")
            for i, qa in enumerate(clarification_context['questions_and_answers'], 1):
                logger.info(f"  Q&A {i}/{qa_count}: Q: {qa['question'][:100]}... | A: {qa['answer'][:100]}...")

            return ClarificationResponse(
                session_id=request.session_id,
                confidence=session.current_confidence,
                confidence_threshold=session.confidence_threshold,
                clarification_complete=True,
                message=f"Great! Based on your answers, I'll create the automation. Confidence: {int(session.current_confidence * 100)}%",
                suggestions=suggestions,
                previous_confidence=previous_confidence if previous_confidence > 0 else None,
                confidence_delta=confidence_delta,
                confidence_summary=confidence_summary,
                enriched_prompt=enriched_prompt,
                questions_and_answers=clarification_context['questions_and_answers']
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
            logger.info("🔧 Rebuilding enriched query for re-detection (timeout: 5s)")
            try:
                enriched_query = _rebuild_user_query_from_qa(
                    original_query=session.original_query,
                    clarification_context=all_qa_context
                )
                # Validation: Ensure enriched_query is not None or empty
                if not enriched_query or not enriched_query.strip():
                    logger.error("❌ Enriched query is empty or None after rebuilding (re-detection path)")
                    raise ValueError("Enriched query cannot be empty")
                logger.info(f"📝 Rebuilt enriched query for re-detection (length: {len(enriched_query)} chars)")
            except Exception as e:
                logger.error(f"❌ Failed to rebuild enriched query (re-detection path): {e}", exc_info=True)
                # Don't fail - use original query as fallback
                enriched_query = session.original_query
                logger.warning(f"⚠️ Using original query as fallback: '{enriched_query}'")

            # NEW: Re-detect ambiguities based on enriched query (original + all previous answers)
            # This ensures we find new ambiguities that may have emerged from the answers
            clarification_detector, question_generator, _, _ = await get_clarification_services(db)

            # PERFORMANCE FIX: Skip entity re-extraction during clarification
            # Entity extraction takes 30+ seconds and times out frequently
            # We already have entities from the initial query - no need to re-extract
            logger.info("⚡ Skipping entity re-extraction during clarification (performance optimization)")
            entities = []  # Use empty entities for re-detection - ambiguity detection works without them

            # Get automation context for re-detection
            automation_context = {}
            try:
                import pandas as pd

                from ..clients.data_api_client import DataAPIClient
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
                        amb_type = _get_ambiguity_type(amb)
                        amb_id = _get_ambiguity_id(amb)
                        amb_context = _get_ambiguity_context(amb)

                        if amb_type == 'device' and amb_id not in answered_ambiguity_ids:
                            # Check if this ambiguity is about the same devices
                            amb_entities = amb_context.get('matches', [])
                            if amb_entities:
                                amb_entity_ids = [e.get('entity_id') for e in amb_entities if isinstance(e, dict)]
                                if any(eid in answer.selected_entities for eid in amb_entity_ids):
                                    answered_ambiguity_ids.add(amb_id)
                                    logger.info(f"✅ Marked ambiguity {amb_id} as resolved by device selection")

            # Combine original and new ambiguities, excluding answered ones
            all_ambiguities = session.ambiguities + new_ambiguities
            remaining_ambiguities = [
                amb for amb in all_ambiguities
                if _get_ambiguity_id(amb) not in answered_ambiguity_ids
            ]

            # Remove duplicates by ambiguity ID
            seen_ambiguity_ids = set()
            unique_remaining = []
            for amb in remaining_ambiguities:
                amb_id = _get_ambiguity_id(amb)
                if amb_id not in seen_ambiguity_ids:
                    seen_ambiguity_ids.add(amb_id)
                    unique_remaining.append(amb)
            remaining_ambiguities = unique_remaining

            logger.info(f"📋 Remaining ambiguities: {len(remaining_ambiguities)} (answered: {len(answered_ambiguity_ids)}, total: {len(all_ambiguities)})")

            # CLARIFICATION LOOP PREVENTION: If we've done multiple rounds without reaching threshold, proceed anyway
            if session.rounds_completed >= session.max_rounds:
                logger.warning(f"⚠️ Max clarification rounds ({session.max_rounds}) reached - proceeding with suggestion generation")
                remaining_ambiguities = []  # Force proceed

            # If no remaining ambiguities, generate suggestions even if confidence is below threshold
            # All ambiguities have been resolved, so we should proceed
            if len(remaining_ambiguities) == 0:
                logger.info("✅ All ambiguities resolved - generating suggestions despite low confidence")
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
                        for answer in session.answers  # Use all answers from session
                    ]
                }
                logger.info(f"📝 Built clarification context with {len(clarification_context['questions_and_answers'])} Q&A pairs for prompt")

                # Rebuild enriched user query from original question + Q&A answers
                logger.info("🔧 Step 1 (all-ambiguities-resolved): Rebuilding enriched query")
                try:
                    enriched_query = _rebuild_user_query_from_qa(
                        original_query=session.original_query,
                        clarification_context=clarification_context
                    )
                    # Validation: Ensure enriched_query is not None or empty
                    if not enriched_query or not enriched_query.strip():
                        logger.error("❌ Enriched query is empty or None after rebuilding (all-ambiguities-resolved path)")
                        raise ValueError("Enriched query cannot be empty")
                    logger.info(f"📝 Step 1 complete: Rebuilt enriched query (length: {len(enriched_query)} chars): '{enriched_query[:200]}...'")
                except Exception as e:
                    logger.error(f"❌ Failed to rebuild enriched query (all-ambiguities-resolved path): {e}", exc_info=True)
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to rebuild enriched query: {str(e)}"
                    ) from e

                # Re-extract entities from enriched query
                logger.info("🔧 Step 2 (all-ambiguities-resolved): Extracting entities (timeout: 60s - allows for OpenAI calls)")
                try:
                    entities = await asyncio.wait_for(
                        extract_entities_with_ha(enriched_query),
                        timeout=60.0  # Increased to 60s to handle OpenAI API calls which can take longer
                    )
                    logger.info(f"🔍 Step 2 complete: Re-extracted {len(entities)} entities from enriched query")
                    if not entities:
                        logger.warning("⚠️ No entities extracted from enriched query - continuing with empty list")
                except asyncio.TimeoutError as e:
                    logger.error("❌ Entity extraction timed out after 60 seconds (all-ambiguities-resolved path)")
                    raise HTTPException(
                        status_code=504,
                        detail={
                            "error": "timeout",
                            "message": "Entity extraction is taking longer than expected. Please try again.",
                            "retry_after": 30
                        }
                    ) from e
                except Exception as e:
                    logger.error(f"❌ Failed to extract entities (all-ambiguities-resolved path): {e}", exc_info=True)
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to extract entities: {str(e)}"
                    ) from e

                # Re-enrich devices based on selected entities from Q&A answers
                logger.info("🔧 Step 3 (all-ambiguities-resolved): Re-enriching entities (timeout: 45s)")
                try:
                    entities = await asyncio.wait_for(
                        _re_enrich_entities_from_qa(
                            entities=entities,
                            clarification_context=clarification_context,
                            ha_client=ha_client
                        ),
                        timeout=45.0
                    )
                    logger.info(f"✅ Step 3 complete: Re-enriched entities with Q&A information: {len(entities)} entities")
                except asyncio.TimeoutError as e:
                    logger.error("❌ Entity re-enrichment timed out after 45 seconds (all-ambiguities-resolved path)")
                    raise HTTPException(
                        status_code=504,
                        detail={
                            "error": "timeout",
                            "message": "Entity enrichment is taking longer than expected. Please try again.",
                            "retry_after": 30
                        }
                    ) from e
                except Exception as e:
                    logger.error(f"❌ Failed to re-enrich entities (all-ambiguities-resolved path): {e}", exc_info=True)
                    # Don't fail the request - continue with un-enriched entities
                    logger.warning("⚠️ Continuing with un-enriched entities due to re-enrichment failure")

                # Generate suggestions WITH enriched query and clarification context
                logger.info("🔧 Step 4 (all-ambiguities-resolved): Generating suggestions (timeout: 60s)")
                
                # Extract area_filter from original query (for location filtering)
                from ..utils.area_detection import extract_area_from_request
                area_filter = extract_area_from_request(session.original_query)
                if area_filter:
                    logger.info(f"📍 Extracted area_filter from original query: '{area_filter}'")
                
                try:
                    suggestions = await asyncio.wait_for(
                        generate_suggestions_from_query(
                            enriched_query,
                            entities,
                            "anonymous",  # TODO: Get from session
                            db_session=db,
                            clarification_context=clarification_context,
                            query_id=getattr(session, 'query_id', None),  # Pass query_id for metrics tracking
                            area_filter=area_filter  # Pass area_filter for location filtering
                        ),
                        timeout=60.0
                    )
                    logger.info(f"✅ Step 4 complete: Generated {len(suggestions)} suggestions (all-ambiguities-resolved path)")
                    
                    # Validate suggestions were actually generated
                    if not suggestions or len(suggestions) == 0:
                        logger.error("❌ No suggestions generated after ambiguity resolution - suggestions array is empty")
                        # Check if this was due to entity mapping failures (ValueError from generate_suggestions_from_query)
                        error_detail = {
                            "error": "suggestion_generation_failed",
                            "message": "Failed to generate automation suggestions after clarification. This may be due to a complex query or AI service issue. Please try rephrasing your request or try again later.",
                            "session_id": request.session_id
                        }
                        raise HTTPException(
                            status_code=500,
                            detail=error_detail
                        )
                except asyncio.TimeoutError as e:
                    logger.error("❌ Suggestion generation timed out after 60 seconds (all-ambiguities-resolved path)")
                    raise HTTPException(
                        status_code=504,
                        detail={
                            "error": "timeout",
                            "message": "The request is taking longer than expected. This may be due to a complex query or high system load. Please try again with a simpler request or wait a moment.",
                            "retry_after": 30
                        }
                    ) from e
                except ValueError as e:
                    error_str = str(e)
                    # Catch all variations of empty content/response errors
                    if ("Empty content from OpenAI" in error_str or
                        "Empty response from OpenAI" in error_str):
                        logger.error(f"❌ OpenAI returned empty content (all-ambiguities-resolved path): {error_str}")
                        raise HTTPException(
                            status_code=503,
                            detail={
                                "error": "api_error",
                                "message": "AI service temporarily unavailable. This may be due to high demand or a complex request. Please try again in a moment.",
                                "retry_after": 30
                            }
                        ) from e
                    elif "entity mapping failures" in error_str.lower() or "skipped" in error_str.lower():
                        # Entity mapping failure - provide more helpful error message
                        logger.error(f"❌ Entity mapping failed during suggestion generation (all-ambiguities-resolved path): {e}", exc_info=True)
                        raise HTTPException(
                            status_code=500,
                            detail={
                                "error": "suggestion_generation_failed",
                                "message": f"Failed to generate suggestions: {str(e)}. This usually means the device names don't match available entities. Please check your device names and try again.",
                                "session_id": request.session_id
                            }
                        ) from e
                    else:
                        logger.error(f"❌ ValueError during suggestion generation (all-ambiguities-resolved path): {e}", exc_info=True)
                        raise HTTPException(
                            status_code=500,
                            detail={
                                "error": "internal_error",
                                "message": f"Failed to generate suggestions: {str(e)}"
                            }
                        ) from e
                except Exception as e:
                    logger.error(f"❌ Failed to generate suggestions (all-ambiguities-resolved path): {e}", exc_info=True)
                    raise HTTPException(
                        status_code=500,
                        detail={
                            "error": "internal_error",
                            "message": f"Failed to generate suggestions: {str(e)}"
                        }
                    ) from e

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
                            for a in session.answers
                        ]
                    }

                # Create database query record so suggestions can be approved
                # Use session_id as query_id so approval endpoint can find it
                try:
                    query_record = AskAIQueryModel(
                        query_id=request.session_id,  # Use session_id as query_id
                        original_query=session.original_query,
                        user_id="anonymous",  # TODO: Get from session
                        parsed_intent=None,  # Not parsed in clarification flow
                        extracted_entities=entities,  # Re-extracted entities
                        suggestions=suggestions,
                        confidence=session.current_confidence,
                        processing_time_ms=0  # Not tracked in clarification flow
                    )
                    db.add(query_record)
                    await db.commit()
                    await db.refresh(query_record)
                    logger.info(f"✅ Created query record {request.session_id} with {len(suggestions)} suggestions (all ambiguities resolved)")

                    # OPTION 1: Auto-store enriched query in RAG knowledge base for future learning
                    # This enables the system to learn from successful clarification sessions
                    rag_client = None
                    try:
                        rag_client = await _get_rag_client(db)
                        if rag_client:
                            # Store enriched query (original + Q&A answers) for semantic similarity matching
                            await rag_client.store(
                                text=enriched_query,  # Enriched query with original + all Q&A answers
                                knowledge_type='query',
                                metadata={
                                    'query_id': request.session_id,
                                    'original_query': session.original_query,
                                    'confidence': session.current_confidence,
                                    'clarification_answers': len(session.answers),
                                    'resolved_entities': len(entities),
                                    'questions_count': len(session.questions),
                                    'rounds_completed': session.rounds_completed,
                                    'all_ambiguities_resolved': True,
                                    'user_id': "anonymous"  # TODO: Get from session when available
                                },
                                success_score=session.current_confidence  # Use final confidence as success indicator
                            )
                            logger.info(f"✅ Stored enriched query in RAG knowledge base for future learning (all ambiguities resolved, confidence: {session.current_confidence:.2f})")
                        else:
                            logger.debug("ℹ️ RAG client not available - skipping enriched query storage")
                    except Exception as e:
                        # Non-critical: continue even if RAG storage fails
                        logger.warning(f"⚠️ Failed to store enriched query in RAG knowledge base: {e}")
                    finally:
                        # Ensure RAG client HTTP connection is properly closed
                        if rag_client:
                            try:
                                await rag_client.close()
                            except Exception as e:
                                logger.debug(f"⚠️ Error closing RAG client: {e}")

                except Exception as e:
                    logger.error(f"⚠️ Failed to create query record for clarification session {request.session_id}: {e}", exc_info=True)
                    # Continue anyway - suggestions are still returned, but approval might fail
                    # Rollback to avoid partial state
                    await db.rollback()

                # Generate user-friendly enriched prompt
                enriched_prompt = _generate_user_friendly_prompt(
                    original_query=session.original_query,
                    clarification_context=clarification_context
                )
                logger.info("📝 Generated enriched prompt for user display (all ambiguities resolved)")

                return ClarificationResponse(
                    session_id=request.session_id,
                    confidence=session.current_confidence,
                    confidence_threshold=session.confidence_threshold,
                    clarification_complete=True,
                    message=f"Great! All ambiguities resolved. Based on your answers, I'll create the automation. Confidence: {int(session.current_confidence * 100)}%",
                    suggestions=suggestions,
                    previous_confidence=previous_confidence if previous_confidence > 0 else None,
                    confidence_delta=confidence_delta,
                    confidence_summary=confidence_summary,
                    enriched_prompt=enriched_prompt,
                    questions_and_answers=clarification_context['questions_and_answers']
                )

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

            message = "Thanks for your answers! " if validated_answers else ""
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
                questions=questions_dict,
                previous_confidence=previous_confidence if previous_confidence > 0 else None,
                confidence_delta=confidence_delta,
                confidence_summary=confidence_summary
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to process clarification: {e}", exc_info=True)
        # Check if it's an empty content error that wasn't caught earlier
        error_str = str(e)
        if ("Empty content from OpenAI" in error_str or
            "Empty response from OpenAI" in error_str):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "api_error",
                    "message": "AI service temporarily unavailable. This may be due to high demand or a complex request. Please try again in a moment.",
                    "retry_after": 30
                }
            ) from e
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"Failed to process clarification: {str(e)}"
            }
        ) from e


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
    include_clarifications: bool = Query(default=True, description="Include suggestions from clarification sessions"),
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get all suggestions for a specific query.
    
    This endpoint handles both:
    1. Direct query IDs (queries without clarification)
    2. Original query IDs (finds clarification session and returns those suggestions)
    
    Args:
        query_id: Either original query_id or clarification_query_id
        include_clarifications: If True, will search for clarification sessions linked to this query
        
    Returns:
        Dictionary with query_id, suggestions array, and total_count
    """
    try:
        # Try to get the query directly
        stmt = select(AskAIQueryModel).where(AskAIQueryModel.query_id == query_id)
        result = await db.execute(stmt)
        query = result.scalar_one_or_none()

        if query:
            # Found query directly
            suggestions = query.suggestions or []
            return {
                "query_id": query_id,
                "suggestions": suggestions,
                "total_count": len(suggestions),
                "source": "direct"
            }

        # If not found and include_clarifications is True, check for clarification sessions
        if include_clarifications:
            stmt = select(ClarificationSessionDB).where(
                ClarificationSessionDB.original_query_id == query_id
            ).order_by(ClarificationSessionDB.created_at.desc())
            result = await db.execute(stmt)
            clarification_session = result.scalar_one_or_none()

            if clarification_session and clarification_session.clarification_query_id:
                # Found clarification session, get the suggestions from the clarification query
                stmt = select(AskAIQueryModel).where(
                    AskAIQueryModel.query_id == clarification_session.clarification_query_id
                )
                result = await db.execute(stmt)
                clarification_query = result.scalar_one_or_none()

                if clarification_query:
                    suggestions = clarification_query.suggestions or []
                    return {
                        "query_id": query_id,
                        "original_query_id": query_id,
                        "clarification_session_id": clarification_session.session_id,
                        "clarification_query_id": clarification_session.clarification_query_id,
                        "suggestions": suggestions,
                        "total_count": len(suggestions),
                        "source": "clarification"
                    }

        # Query not found
        raise HTTPException(
            status_code=404,
            detail=f"Query {query_id} not found"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve suggestions for query {query_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve suggestions: {str(e)}"
        ) from e


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

    # Check if timing is expected based on query
    timing_expected = _detects_timing_requirement(original_query)

    try:
        yaml_data = yaml.safe_load(automation_yaml)
    except Exception:
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
    entity_ids: list[str],
    timeout: float = 5.0
) -> dict[str, dict[str, Any]]:
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
    before_states: dict[str, dict[str, Any]],
    entity_ids: list[str],
    wait_timeout: float = 5.0,
    check_interval: float = 0.5
) -> dict[str, Any]:
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
                            logger.info(f"✅ State change detected for {entity_id}: {before_state} -> {after_state_value}")
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
        state_validation: dict[str, Any],
        execution_logs: str | None = None
    ) -> dict[str, Any]:
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
                max_completion_tokens=800,  # Increased from 400 to 800 for multiple ambiguities + JSON (2025 best practice)
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
) -> dict[str, Any]:
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
            raise HTTPException(status_code=500, detail=f"Database error: {e}") from e

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
                logger.debug("Found matching suggestion!")
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
            logger.info("⚠️ Re-resolving entities (validated_entities not saved) - SLOW PATH")
            # Use devices_involved from the suggestion (these are the actual device names to map)
            devices_involved = suggestion.get('devices_involved', [])
            logger.debug(f" devices_involved from suggestion: {devices_involved}")

            # Map devices to entity_ids using the same logic as in generate_automation_yaml
            logger.debug(" Mapping devices to entity_ids...")
            from ..clients.data_api_client import DataAPIClient
            from ..services.entity_validator import EntityValidator
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
            test_suggestion['description'] = f"TEST_MODE_SEQUENCES - {suggestion.get('description', '')} - Execute with shortened delays (10x faster)"
            test_suggestion['trigger_summary'] = "Manual trigger (test mode)"
            test_suggestion['action_summary'] = suggestion.get('action_summary', '')
            test_suggestion['test_mode'] = 'sequence'  # Mark for sequence-aware YAML generation
        else:
            # Simple test mode: strip timing components
            test_suggestion['description'] = f"TEST_MODE - {suggestion.get('description', '')} - Execute core action only"
            test_suggestion['trigger_summary'] = "Manual trigger (test mode)"
            test_suggestion['action_summary'] = suggestion.get('action_summary', '').split('every')[0].split('Every')[0].strip()
            test_suggestion['test_mode'] = 'simple'

        test_suggestion['validated_entities'] = entity_mapping
        logger.debug(f" Added validated_entities: {entity_mapping}")
        logger.debug(f" test_suggestion validated_entities key exists: {'validated_entities' in test_suggestion}")
        logger.debug(f" test_suggestion['validated_entities'] content: {test_suggestion.get('validated_entities')}")

        automation_yaml = await generate_automation_yaml(test_suggestion, query.original_query, openai_client, entities, db_session=db, ha_client=ha_client)
        yaml_gen_time = (time.time() - yaml_gen_start) * 1000
        logger.debug(f"After generate_automation_yaml - validated_entities still exists: {'validated_entities' in test_suggestion}")
        logger.info("Generated test automation YAML")
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
                        from ..services.comprehensive_entity_enrichment import (
                            enrich_entities_comprehensively,
                        )
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
                    from ..services.reverse_engineering_metrics import (
                        store_reverse_engineering_metrics,
                    )
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

        # STEP 3: Execute test using AutomationTestExecutor (uses ActionExecutor internally)
        logger.info("Executing test via AutomationTestExecutor (no automation creation)...")

        try:
            # Get AutomationTestExecutor from ServiceContainer
            service_container = ServiceContainer()
            test_executor = service_container.test_executor

            # Prepare test context
            test_context = {
                'query_id': query_id,
                'suggestion_id': suggestion_id,
                'original_query': query.original_query,
                'automation_yaml': automation_yaml,
                'entity_mapping': entity_mapping
            }

            # Execute test using AutomationTestExecutor (handles state capture, execution, and validation)
            test_result = await test_executor.execute_test(
                automation_yaml=automation_yaml,
                expected_changes=None,
                context=test_context
            )

            # Extract results from test execution
            state_validation = {
                'results': test_result.get('state_changes', {}),
                'summary': test_result.get('state_validation', {})
            }

            execution_summary = test_result.get('execution_summary', {})
            action_execution_time = test_result.get('execution_time_ms', 0)

            logger.info(f"Test execution complete: {execution_summary.get('successful', 0)}/{execution_summary.get('total_actions', 0)} actions successful")

            # Check if execution was successful
            if execution_summary.get('failed', 0) > 0:
                logger.warning(f"Some actions failed: {execution_summary.get('failed', 0)}")
                errors = test_result.get('errors', [])
                if errors:
                    logger.debug(f"Failed action errors: {errors}")

            # Set automation_id to None since we didn't create one
            automation_id = None

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
            execution_logs = f"Actions executed via AutomationTestExecutor: {execution_summary.get('successful', 0)}/{execution_summary.get('total_actions', 0)} successful"
            test_analysis = await analyzer.analyze_test_execution(
                test_yaml=automation_yaml,
                state_validation=state_validation,
                execution_logs=execution_logs
            )

            # TASK 1.5: Format stripped components for preview
            stripped_components_preview = component_detector.format_components_for_preview(stripped_components)

            # Calculate total time
            total_time = (time.time() - start_time) * 1000

            # Calculate performance metrics
            performance_metrics = {
                "entity_resolution_ms": round(entity_resolution_time, 2),
                "yaml_generation_ms": round(yaml_gen_time, 2),
                "action_execution_ms": round(action_execution_time, 2),
                "state_validation_ms": round(state_validation.get('summary', {}).get('validation_time_ms', 0), 2),
                "total_ms": round(total_time, 2),
                "action_executor_used": True,
                "actions_executed": execution_summary.get('total_actions', 0),
                "actions_successful": execution_summary.get('successful', 0),
                "actions_failed": execution_summary.get('failed', 0)
            }

            # Log slow operations
            if total_time > 5000:
                logger.warning(f"Slow operation detected: total time {total_time:.2f}ms")
            if action_execution_time > 5000:
                logger.warning(f"Slow action execution: {action_execution_time:.2f}ms")

            response_data = {
                "suggestion_id": suggestion_id,
                "query_id": query_id,
                "executed": True,
                "automation_yaml": automation_yaml,
                "automation_id": automation_id,  # None - no automation created
                "deleted": False,  # No automation to delete
                "message": "Test completed successfully - actions executed via AutomationTestExecutor (no automation created)",
                "execution_result": {
                    "total_actions": execution_summary.get('total_actions', 0),
                    "successful_actions": execution_summary.get('successful', 0),
                    "failed_actions": execution_summary.get('failed', 0),
                    "execution_time_ms": execution_summary.get('execution_time_ms', 0)
                },
                "execution_summary": test_result.get('execution_summary', {}),
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

        except Exception as action_error:
            logger.error(f"❌ ERROR in AutomationTestExecutor execution: {action_error}", exc_info=True)
            # Fallback: Try old method if AutomationTestExecutor fails
            logger.warning("⚠️ Falling back to old create/delete automation method...")
            try:
                # Extract entity IDs for fallback
                fallback_entity_ids = list(entity_mapping.values()) if entity_mapping else []

                # Capture states before fallback execution
                fallback_before_states = await capture_entity_states(ha_client, fallback_entity_ids)

                # Fallback to old method
                ha_create_start = time.time()
                creation_result = await ha_client.create_automation(automation_yaml)
                ha_create_time = (time.time() - ha_create_start) * 1000
                automation_id = creation_result.get('automation_id')

                if automation_id:
                    await ha_client.trigger_automation(automation_id)
                    state_validation = await validate_state_changes(
                        ha_client, fallback_before_states, fallback_entity_ids, wait_timeout=5.0
                    )
                    await ha_client.delete_automation(automation_id)

                    total_time = (time.time() - start_time) * 1000
                    return {
                        "suggestion_id": suggestion_id,
                        "query_id": query_id,
                        "executed": True,
                        "automation_yaml": automation_yaml,
                        "automation_id": automation_id,
                        "deleted": True,
                        "message": "Test completed (fallback method - AutomationTestExecutor failed)",
                        "state_validation": state_validation,
                        "performance_metrics": {
                            "entity_resolution_ms": round(entity_resolution_time, 2),
                            "yaml_generation_ms": round(yaml_gen_time, 2),
                            "ha_creation_ms": round(ha_create_time, 2),
                            "total_ms": round(total_time, 2),
                            "action_executor_used": False,
                            "fallback_reason": str(action_error)
                        }
                    }
            except Exception as fallback_error:
                logger.error(f"❌ Fallback method also failed: {fallback_error}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Both AutomationTestExecutor and fallback method failed. AutomationTestExecutor error: {action_error}, Fallback error: {fallback_error}"
                ) from fallback_error
            raise

    except HTTPException as e:
        logger.error(f"HTTPException in test endpoint: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Error testing suggestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Task 1.4: Component Restoration Function
# ============================================================================

async def restore_stripped_components(
    original_suggestion: dict[str, Any],
    test_result: dict[str, Any] | None,
    original_query: str,
    openai_client: OpenAIClient
) -> dict[str, Any]:
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
            temperature=0.1,  # Very low temperature for deterministic, consistent restoration
            max_completion_tokens=1500,  # Increased from 500 to 1500 for nested component descriptions (2025 best practice)
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
    selected_entity_ids: list[str] | None = Field(default=None, description="List of entity IDs selected by user to include in automation")
    custom_entity_mapping: dict[str, str] | None = Field(
        default=None,
        description="Custom mapping of friendly_name -> entity_id overrides. Allows users to change which entity_id maps to a device name."
    )

@router.post("/query/{query_id}/suggestions/{suggestion_id}/approve")
async def approve_suggestion_from_query(
    query_id: str,
    suggestion_id: str,
    request: ApproveSuggestionRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
    ha_client: HomeAssistantClient = Depends(get_ha_client),
    openai_client: OpenAIClient = Depends(get_openai_client)
) -> dict[str, Any]:
    """
    Approve a suggestion and create the automation in Home Assistant.
    """
    # Phase 1: Add comprehensive logging for debugging
    logger.info(f"🚀 [APPROVAL START] query_id={query_id}, suggestion_id={suggestion_id}")
    logger.info(f"📝 [APPROVAL] Request body: {request}")

    try:
        # Get the query from database
        logger.info(f"🔍 [APPROVAL] Fetching query record: {query_id}")
        query = await db.get(AskAIQueryModel, query_id)
        if not query:
            logger.error(f"❌ [APPROVAL] Query {query_id} not found in database")
            raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
        logger.info(f"✅ [APPROVAL] Found query with {len(query.suggestions)} suggestions")

        # Find the specific suggestion
        logger.info(f"🔍 [APPROVAL] Searching for suggestion_id={suggestion_id}")
        suggestion = None
        for s in query.suggestions:
            if s.get('suggestion_id') == suggestion_id:
                suggestion = s
                break

        if not suggestion:
            logger.error(f"❌ [APPROVAL] Suggestion {suggestion_id} not found in query suggestions")
            raise HTTPException(status_code=404, detail=f"Suggestion {suggestion_id} not found")

        logger.info(f"✅ [APPROVAL] Found suggestion: {suggestion.get('title', 'Untitled')[:50]}")

        # Get validated_entities from suggestion (MUST be set during suggestion creation)
        validated_entities = suggestion.get('validated_entities')
        if not validated_entities or not isinstance(validated_entities, dict) or len(validated_entities) == 0:
            # This should NEVER happen if suggestion creation is working correctly
            # Log critical error and fail fast - this indicates a bug in suggestion creation
            logger.error(f"❌ CRITICAL BUG: Suggestion {suggestion_id} missing validated_entities")
            logger.error("❌ This should never happen - validated_entities must be set during suggestion creation")
            logger.error(f"❌ Suggestion data: {suggestion.keys()}")
            logger.error(f"❌ devices_involved: {suggestion.get('devices_involved', [])}")

            raise HTTPException(
                status_code=500,
                detail=f"Internal error: Suggestion {suggestion_id} is missing validated entities. This indicates a bug in suggestion creation. Please regenerate the suggestion."
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
                            logger.info(f"✅ Applied custom mapping: '{friendly_name}' -> {new_entity_id}")
                        else:
                            logger.warning(f"⚠️ Custom entity_id {new_entity_id} for '{friendly_name}' does not exist in HA - skipped")
                else:
                    # No HA client - apply without verification
                    logger.warning("⚠️ No HA client - applying custom mappings without verification")
                    final_suggestion['validated_entities'].update(request.custom_entity_mapping)

        # Generate YAML for the suggestion (validated_entities already in final_suggestion)
        logger.info(f"🔧 [YAML_GEN] Starting YAML generation for suggestion {suggestion_id}")
        logger.info(f"📋 [YAML_GEN] Validated entities: {final_suggestion.get('validated_entities')}")
        logger.info(f"📝 [YAML_GEN] Suggestion title: {final_suggestion.get('title', 'Untitled')}")

        # Track which model generated the suggestion for metrics update
        suggestion_model_used = None
        if suggestion.get('debug') and suggestion['debug'].get('model_used'):
            suggestion_model_used = suggestion['debug']['model_used']
        elif suggestion.get('debug') and suggestion['debug'].get('token_usage'):
            suggestion_model_used = suggestion['debug']['token_usage'].get('model')

        try:
            automation_yaml = await generate_automation_yaml(final_suggestion, query.original_query, openai_client, [], db_session=db, ha_client=ha_client)

            # Phase 4: Post-YAML entity ID correction - catch and fix entity ID mismatches
            import re
            parsed_yaml = yaml_lib.safe_load(automation_yaml)
            if parsed_yaml:
                from ..services.entity_id_validator import EntityIDValidator
                entity_id_extractor = EntityIDValidator()
                entity_id_tuples = entity_id_extractor._extract_all_entity_ids(parsed_yaml)
                yaml_entity_ids = [eid for eid, _ in entity_id_tuples] if entity_id_tuples else []
                
                # Find entity IDs in YAML that don't match validated_entities
                validated_entity_ids = set(final_suggestion['validated_entities'].values())
                mismatched_entities = [eid for eid in yaml_entity_ids if eid not in validated_entity_ids and not eid.startswith('scene.')]
                
                if mismatched_entities:
                    logger.warning(f"⚠️ Found {len(mismatched_entities)} entity IDs in YAML that don't match validated_entities: {', '.join(mismatched_entities)}")
                    entity_replacements = {}
                    
                    for invalid_entity_id in mismatched_entities:
                        # Find best match from validated_entities using similarity
                        best_match = None
                        best_score = 0.0
                        
                        for validated_entity_id in validated_entity_ids:
                            # Calculate similarity (domain match + name similarity)
                            invalid_domain = invalid_entity_id.split('.')[0] if '.' in invalid_entity_id else ''
                            validated_domain = validated_entity_id.split('.')[0] if '.' in validated_entity_id else ''
                            
                            if invalid_domain != validated_domain:
                                continue  # Must match domain
                            
                            # Use rapidfuzz for name similarity
                            invalid_name = invalid_entity_id.split('.')[-1] if '.' in invalid_entity_id else invalid_entity_id
                            validated_name = validated_entity_id.split('.')[-1] if '.' in validated_entity_id else validated_entity_id
                            
                            from rapidfuzz import fuzz
                            similarity = fuzz.ratio(invalid_name.lower(), validated_name.lower())
                            
                            if similarity > best_score and similarity >= 50.0:  # Minimum 50% similarity
                                best_score = similarity
                                best_match = validated_entity_id
                        
                        if best_match:
                            entity_replacements[invalid_entity_id] = best_match
                            logger.info(f"🔧 Auto-correcting entity ID: '{invalid_entity_id}' -> '{best_match}' (similarity: {best_score:.1f}%)")
                    
                    # Apply replacements to YAML
                    if entity_replacements:
                        for old_id, new_id in entity_replacements.items():
                            pattern = r'\b' + re.escape(old_id) + r'\b'
                            automation_yaml = re.sub(pattern, new_id, automation_yaml)
                        logger.info(f"✅ Auto-corrected {len(entity_replacements)} entity IDs in YAML")
                        # Re-parse after correction
                        parsed_yaml = yaml_lib.safe_load(automation_yaml)

            # Update metrics: Mark suggestion as approved
            if suggestion_model_used:
                await _update_model_comparison_metrics_on_approval(
                    db=db,
                    suggestion_id=suggestion_id,
                    query_id=query_id,
                    model_used=suggestion_model_used,
                    task_type='suggestion'
                )

            logger.info(f"✅ [YAML_GEN] YAML generated successfully ({len(automation_yaml)} chars)")
            logger.info(f"📄 [YAML_GEN] First 200 chars: {automation_yaml[:200]}")
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
                    # Deduplicate entity IDs before validation (YAML may have same entity in multiple actions)
                    unique_entity_ids = list(set(all_entity_ids_in_yaml))
                    
                    # Extract scenes created dynamically by scene.create service calls (2025 Home Assistant pattern)
                    created_scenes = entity_id_extractor.extract_scenes_created(parsed_yaml)
                    
                    # Also check for scene entities in the YAML that might be created
                    scene_entities_in_yaml = [eid for eid in unique_entity_ids if eid.startswith('scene.')]
                    
                    # Filter out dynamically created scenes from validation (they don't exist until runtime)
                    entities_to_validate = [
                        eid for eid in unique_entity_ids 
                        if eid not in created_scenes
                    ]
                    
                    if created_scenes:
                        logger.info(f"🔍 Excluding {len(created_scenes)} dynamically created scenes from validation: {', '.join(sorted(created_scenes))}")
                        logger.info(f"🔍 Validating {len(entities_to_validate)} static entities")
                    
                    if scene_entities_in_yaml:
                        logger.info(f"🔍 Found {len(scene_entities_in_yaml)} scene entities in YAML: {', '.join(sorted(scene_entities_in_yaml))}")
                        
                        # Check for scene ID consistency (Phase 5)
                        referenced_scenes = set(scene_entities_in_yaml)
                        if created_scenes:
                            missing_scenes = referenced_scenes - created_scenes
                            if missing_scenes:
                                # Fail early: scenes referenced but not created via scene.create
                                error_msg = (
                                    f"Scene entities referenced but not created via scene.create: {', '.join(sorted(missing_scenes))}. "
                                    f"All scene entities must be created using the scene.create service before they can be used. "
                                    f"Example: Use 'service: scene.create' with 'data.scene_id' before referencing the scene entity."
                                )
                                logger.error(f"❌ {error_msg}")
                                raise ValueError(error_msg)
                            unused_scenes = created_scenes - referenced_scenes
                            if unused_scenes:
                                logger.info(f"ℹ️ Scenes created but not referenced: {', '.join(sorted(unused_scenes))}")
                        else:
                            # No scenes created, but scene entities are referenced - this is an error
                            if referenced_scenes:
                                error_msg = (
                                    f"Scene entities referenced but no scene.create service calls found: {', '.join(sorted(referenced_scenes))}. "
                                    f"All scene entities must be created using the scene.create service before they can be used. "
                                    f"Example: Use 'service: scene.create' with 'data.scene_id' before referencing the scene entity."
                                )
                                logger.error(f"❌ {error_msg}")
                                raise ValueError(error_msg)
                        
                        # Check if any scene entities are not in created_scenes - these need to exist in HA
                        scenes_not_created = [eid for eid in scene_entities_in_yaml if eid not in created_scenes]
                        if scenes_not_created:
                            logger.info(f"🔍 {len(scenes_not_created)} static scene entities will be validated against HA: {', '.join(sorted(scenes_not_created))}")
                    
                    if created_scenes:
                        logger.info(f"🔍 Final validation: Checking {len(entities_to_validate)} unique entity IDs exist in HA (found {len(all_entity_ids_in_yaml)} total in YAML, excluding {len(created_scenes)} dynamically created scenes)...")
                    else:
                        logger.info(f"🔍 Final validation: Checking {len(entities_to_validate)} unique entity IDs exist in HA (found {len(all_entity_ids_in_yaml)} total in YAML)...")

                    # Validate each unique entity ID exists in HA (excluding dynamically created scenes)
                    invalid_entities = []
                    connection_error = None
                    for entity_id in entities_to_validate:
                        try:
                            entity_state = await ha_client.get_entity_state(entity_id)
                            if not entity_state:
                                invalid_entities.append(entity_id)
                        except ConnectionError as e:
                            # Connection error - stop validation and return early with clear error
                            connection_error = str(e)
                            logger.error(f"❌ Connection error during entity validation: {connection_error}")
                            break
                        except Exception as e:
                            # Other errors - treat as entity not found
                            logger.warning(f"⚠️ Error validating entity {entity_id}: {e}")
                            invalid_entities.append(entity_id)

                    # If we had a connection error, return early with clear message
                    if connection_error:
                        return {
                            "suggestion_id": suggestion_id,
                            "query_id": query_id,
                            "status": "error",
                            "safe": False,
                            "message": "Cannot connect to Home Assistant to validate entities",
                            "error_details": {
                                "type": "connection_error",
                                "message": f"Unable to connect to Home Assistant at {ha_client.ha_url}. Please check your Home Assistant configuration and ensure the service is running.",
                                "connection_error": connection_error,
                                "ha_url": ha_client.ha_url
                            }
                        }

                    if invalid_entities:
                        # Try to fix invalid entity IDs by matching them to validated entities
                        logger.warning(f"⚠️ Found {len(invalid_entities)} invalid entity IDs, attempting to fix...")
                        entity_replacements = {}

                        for invalid_entity_id in invalid_entities:
                            # Try to find a matching validated entity ID
                            best_match = None
                            best_score = 0.0

                            # Extract domain and name parts from invalid entity ID
                            if '.' in invalid_entity_id:
                                invalid_domain, invalid_name = invalid_entity_id.split('.', 1)
                                invalid_name_lower = invalid_name.lower()

                                # Search through validated entities for best match
                                for device_name, validated_entity_id in final_suggestion['validated_entities'].items():
                                    if '.' in validated_entity_id:
                                        validated_domain, validated_name = validated_entity_id.split('.', 1)

                                        # Domain must match
                                        if validated_domain != invalid_domain:
                                            continue

                                        # Calculate similarity score
                                        score = 0.0
                                        validated_name_lower = validated_name.lower()
                                        device_name_lower = device_name.lower()

                                        # Exact name match (highest priority)
                                        if validated_name_lower == invalid_name_lower:
                                            score = 100.0
                                        # Partial name match
                                        elif invalid_name_lower in validated_name_lower or validated_name_lower in invalid_name_lower:
                                            score = 50.0 + min(len(invalid_name_lower), len(validated_name_lower)) / max(len(invalid_name_lower), len(validated_name_lower)) * 30.0
                                        # Device name match
                                        elif invalid_name_lower in device_name_lower or device_name_lower in invalid_name_lower:
                                            score = 40.0 + min(len(invalid_name_lower), len(device_name_lower)) / max(len(invalid_name_lower), len(device_name_lower)) * 20.0
                                        # Word overlap
                                        else:
                                            invalid_words = set(invalid_name_lower.replace('_', ' ').split())
                                            validated_words = set(validated_name_lower.replace('_', ' ').split())
                                            device_words = set(device_name_lower.replace('_', ' ').split())
                                            overlap = len(invalid_words & validated_words) + len(invalid_words & device_words)
                                            if overlap > 0:
                                                score = overlap * 10.0

                                        if score > best_score:
                                            best_score = score
                                            best_match = validated_entity_id

                            if best_match and best_score >= 30.0:  # Minimum threshold for replacement
                                entity_replacements[invalid_entity_id] = best_match
                                logger.info(f"🔧 Mapping invalid entity '{invalid_entity_id}' -> '{best_match}' (score: {best_score:.1f})")
                            else:
                                logger.warning(f"⚠️ Could not find match for invalid entity '{invalid_entity_id}'")

                        # Apply replacements to YAML if we found any matches
                        if entity_replacements:
                            sanitized_yaml = automation_yaml
                            for old_id, new_id in entity_replacements.items():
                                # Replace with word boundaries to avoid partial matches
                                pattern = r'\b' + re.escape(old_id) + r'\b'
                                sanitized_yaml = re.sub(pattern, new_id, sanitized_yaml)

                            logger.info(f"✅ Fixed {len(entity_replacements)} entity IDs in YAML, re-validating...")
                            automation_yaml = sanitized_yaml

                                # Re-parse and re-validate
                            parsed_yaml = yaml_lib.safe_load(automation_yaml)
                            if parsed_yaml:
                                entity_id_tuples = entity_id_extractor._extract_all_entity_ids(parsed_yaml)
                                all_entity_ids_in_yaml = [eid for eid, _ in entity_id_tuples] if entity_id_tuples else []
                                # Deduplicate again after fix
                                unique_entity_ids_after_fix = list(set(all_entity_ids_in_yaml))
                                
                                # Re-extract dynamically created scenes (in case they changed)
                                created_scenes_after_fix = entity_id_extractor.extract_scenes_created(parsed_yaml)
                                
                                # Filter out dynamically created scenes from re-validation
                                entities_to_validate_after_fix = [eid for eid in unique_entity_ids_after_fix if eid not in created_scenes_after_fix]
                                
                                if created_scenes_after_fix:
                                    logger.info(f"🔍 Re-validation: Checking {len(entities_to_validate_after_fix)} unique entity IDs (excluding {len(created_scenes_after_fix)} dynamically created scenes)...")

                                # Re-validate unique entities only (excluding dynamically created scenes)
                                remaining_invalid = []
                                connection_error_after_fix = None
                                for entity_id in entities_to_validate_after_fix:
                                    try:
                                        entity_state = await ha_client.get_entity_state(entity_id)
                                        if not entity_state:
                                            remaining_invalid.append(entity_id)
                                    except ConnectionError as e:
                                        # Connection error - stop validation
                                        connection_error_after_fix = str(e)
                                        logger.error(f"❌ Connection error during re-validation: {connection_error_after_fix}")
                                        break
                                    except Exception as e:
                                        # Other errors - treat as entity not found
                                        logger.warning(f"⚠️ Error re-validating entity {entity_id}: {e}")
                                        remaining_invalid.append(entity_id)

                                # If we had a connection error during re-validation, return early
                                if connection_error_after_fix:
                                    return {
                                        "suggestion_id": suggestion_id,
                                        "query_id": query_id,
                                        "status": "error",
                                        "safe": False,
                                        "message": "Cannot connect to Home Assistant to validate entities",
                                        "error_details": {
                                            "type": "connection_error",
                                            "message": f"Unable to connect to Home Assistant at {ha_client.ha_url}. Please check your Home Assistant configuration and ensure the service is running.",
                                            "connection_error": connection_error_after_fix,
                                            "ha_url": ha_client.ha_url
                                        }
                                    }

                                if remaining_invalid:
                                    error_msg = f"Invalid entity IDs in YAML (after auto-fix attempt): {', '.join(remaining_invalid)}"
                                    logger.error(f"❌ {error_msg}")
                                    return {
                                        "suggestion_id": suggestion_id,
                                        "query_id": query_id,
                                        "status": "error",
                                        "safe": False,
                                        "message": "Automation contains invalid entity IDs that could not be auto-fixed",
                                        "error_details": {
                                            "type": "invalid_entities",
                                            "message": error_msg,
                                            "invalid_entities": remaining_invalid,
                                            "auto_fixed": list(entity_replacements.keys())
                                        }
                                    }
                                else:
                                    logger.info("✅ All entity IDs fixed and validated successfully")
                        else:
                            # No replacements found, return error
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
                        if created_scenes:
                            logger.info(f"✅ Final validation passed: All {len(entities_to_validate)} unique entity IDs exist in HA (excluded {len(created_scenes)} dynamically created scenes)")
                        else:
                            logger.info(f"✅ Final validation passed: All {len(unique_entity_ids)} unique entity IDs exist in HA")

                        # Update metrics: Mark YAML as valid
                        # Get model used from YAML generation (stored in suggestion debug data)
                        yaml_model_used = None
                        if final_suggestion.get('debug') and final_suggestion['debug'].get('yaml_model_used'):
                            yaml_model_used = final_suggestion['debug']['yaml_model_used']
                        elif final_suggestion.get('debug') and final_suggestion['debug'].get('token_usage'):
                            yaml_model_used = final_suggestion['debug']['token_usage'].get('model')

                        if yaml_model_used:
                            await _update_model_comparison_metrics_on_yaml_validation(
                                db=db,
                                suggestion_id=suggestion_id,
                                model_used=yaml_model_used,
                                yaml_valid=True
                            )
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
            logger.warning("⚠️ Safety validation found issues, but continuing (user can review)")

        # Create automation in Home Assistant
        if not ha_client:
            logger.error("❌ [DEPLOY] Home Assistant client not initialized")
            raise HTTPException(status_code=500, detail="Home Assistant client not initialized")

        logger.info("🚀 [DEPLOY] Starting deployment to Home Assistant")
        logger.info(f"🔗 [DEPLOY] HA URL: {ha_client.base_url if hasattr(ha_client, 'base_url') else 'N/A'}")

        try:
            creation_result = await ha_client.create_automation(automation_yaml)

            if creation_result.get('success'):
                automation_id = creation_result.get('automation_id')
                logger.info(f"✅ [DEPLOY] Successfully created automation: {automation_id}")
                logger.info("🎉 [DEPLOY] Automation is now active in Home Assistant")
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
                logger.error(f"❌ [DEPLOY] Failed to create automation: {error_message}")
                logger.error(f"❌ [DEPLOY] Full error details: {creation_result}")
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
            logger.error(f"❌ [DEPLOY] Exception during HA deployment: {type(e).__name__}: {error_message}")
            logger.error("❌ [DEPLOY] Stack trace:", exc_info=True)
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
        logger.error(f"❌ [APPROVAL] Unexpected exception: {type(e).__name__}: {str(e)}")
        logger.error("❌ [APPROVAL] Full stack trace:", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}") from e


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
        raise HTTPException(status_code=500, detail=str(e)) from e


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
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/aliases", response_model=dict[str, list[str]])
async def list_aliases(
    user_id: str = "anonymous",
    db: AsyncSession = Depends(get_db)
):
    """
    Get all aliases for a user, grouped by entity_id.
    
    Returns a dictionary mapping entity_id -> list of aliases.
    
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
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/model-comparison/metrics")
async def get_model_comparison_metrics(
    task_type: str | None = Query(None, description="Filter by task type: 'suggestion' or 'yaml'"),
    days: int = Query(7, ge=1, le=30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get model comparison metrics for parallel testing.
    
    Returns aggregated metrics comparing model performance, cost, and quality.
    """
    try:
        from datetime import datetime, timedelta

        from sqlalchemy import select

        from ..database.models import ModelComparisonMetrics

        # Build query
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = select(ModelComparisonMetrics).where(
            ModelComparisonMetrics.created_at >= cutoff_date
        )

        if task_type:
            query = query.where(ModelComparisonMetrics.task_type == task_type)

        result = await db.execute(query)
        metrics = result.scalars().all()

        if not metrics:
            return {
                "total_comparisons": 0,
                "task_type": task_type or "all",
                "days": days,
                "summary": {},
                "model_stats": {}
            }

        # Aggregate statistics
        total_comparisons = len(metrics)
        model1_total_cost = sum(m.model1_cost_usd for m in metrics)
        model2_total_cost = sum(m.model2_cost_usd for m in metrics)
        model1_avg_latency = sum(m.model1_latency_ms for m in metrics) / total_comparisons
        model2_avg_latency = sum(m.model2_latency_ms for m in metrics) / total_comparisons

        # Quality metrics (only for metrics with approval/validation data)
        model1_approved = sum(1 for m in metrics if m.model1_approved is True)
        model2_approved = sum(1 for m in metrics if m.model2_approved is True)
        model1_yaml_valid = sum(1 for m in metrics if m.model1_yaml_valid is True)
        model2_yaml_valid = sum(1 for m in metrics if m.model2_yaml_valid is True)

        approved_total = sum(1 for m in metrics if m.model1_approved is not None or m.model2_approved is not None)
        yaml_valid_total = sum(1 for m in metrics if m.model1_yaml_valid is not None or m.model2_yaml_valid is not None)

        return {
            "total_comparisons": total_comparisons,
            "task_type": task_type or "all",
            "days": days,
            "summary": {
                "cost_difference_usd": abs(model1_total_cost - model2_total_cost),
                "cost_savings_percentage": ((model2_total_cost - model1_total_cost) / model1_total_cost * 100) if model1_total_cost > 0 else 0,
                "latency_difference_ms": abs(model1_avg_latency - model2_avg_latency),
                "model1_total_cost": round(model1_total_cost, 4),
                "model2_total_cost": round(model2_total_cost, 4),
                "model1_avg_latency_ms": round(model1_avg_latency, 2),
                "model2_avg_latency_ms": round(model2_avg_latency, 2)
            },
            "model_stats": {
                "model1": {
                    "name": metrics[0].model1_name if metrics else "unknown",
                    "total_cost_usd": round(model1_total_cost, 4),
                    "avg_cost_per_comparison": round(model1_total_cost / total_comparisons, 4),
                    "avg_latency_ms": round(model1_avg_latency, 2),
                    "approval_rate": round(model1_approved / approved_total * 100, 2) if approved_total > 0 else None,
                    "yaml_validation_rate": round(model1_yaml_valid / yaml_valid_total * 100, 2) if yaml_valid_total > 0 else None
                },
                "model2": {
                    "name": metrics[0].model2_name if metrics else "unknown",
                    "total_cost_usd": round(model2_total_cost, 4),
                    "avg_cost_per_comparison": round(model2_total_cost / total_comparisons, 4),
                    "avg_latency_ms": round(model2_avg_latency, 2),
                    "approval_rate": round(model2_approved / approved_total * 100, 2) if approved_total > 0 else None,
                    "yaml_validation_rate": round(model2_yaml_valid / yaml_valid_total * 100, 2) if yaml_valid_total > 0 else None
                }
            }
        }
    except Exception as e:
        logger.error(f"Error fetching model comparison metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/model-comparison/summary")
async def get_model_comparison_summary(
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get summary of model comparison results with recommendations.
    
    Returns high-level summary and recommendations for which model performs better.
    """
    try:
        from datetime import datetime, timedelta

        from sqlalchemy import select

        from ..database.models import ModelComparisonMetrics

        # Get metrics from last 7 days
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        result = await db.execute(
            select(ModelComparisonMetrics).where(
                ModelComparisonMetrics.created_at >= cutoff_date
            )
        )
        metrics = result.scalars().all()

        if not metrics:
            return {
                "total_comparisons": 0,
                "recommendations": {
                    "suggestion": "Insufficient data",
                    "yaml": "Insufficient data"
                }
            }

        # Group by task type
        suggestion_metrics = [m for m in metrics if m.task_type == 'suggestion']
        yaml_metrics = [m for m in metrics if m.task_type == 'yaml']

        def analyze_task_type(task_metrics, task_name):
            if not task_metrics:
                return {"recommendation": "Insufficient data", "reason": "No comparisons yet"}

            model1_cost = sum(m.model1_cost_usd for m in task_metrics)
            model2_cost = sum(m.model2_cost_usd for m in task_metrics)
            model1_avg_latency = sum(m.model1_latency_ms for m in task_metrics) / len(task_metrics)
            model2_avg_latency = sum(m.model2_latency_ms for m in task_metrics) / len(task_metrics)

            model1_approved = sum(1 for m in task_metrics if m.model1_approved is True)
            model2_approved = sum(1 for m in task_metrics if m.model2_approved is True)
            approved_total = sum(1 for m in task_metrics if m.model1_approved is not None)

            model1_name = task_metrics[0].model1_name
            model2_name = task_metrics[0].model2_name

            # Determine recommendation
            cost_savings = ((model2_cost - model1_cost) / model1_cost * 100) if model1_cost > 0 else 0
            quality_diff = ((model2_approved - model1_approved) / approved_total * 100) if approved_total > 0 else 0

            if cost_savings > 50 and quality_diff < 5:
                recommendation = model2_name
                reason = f"{model2_name} is {abs(cost_savings):.1f}% cheaper with similar quality"
            elif quality_diff > 10:
                recommendation = model1_name
                reason = f"{model1_name} has {abs(quality_diff):.1f}% higher approval rate"
            else:
                recommendation = model1_name
                reason = f"{model1_name} provides better quality-cost balance"

            return {
                "recommendation": recommendation,
                "reason": reason,
                "total_comparisons": len(task_metrics),
                "cost_savings_percentage": round(cost_savings, 2),
                "quality_difference_percentage": round(quality_diff, 2)
            }

        return {
            "total_comparisons": len(metrics),
            "recommendations": {
                "suggestion": analyze_task_type(suggestion_metrics, "suggestion"),
                "yaml": analyze_task_type(yaml_metrics, "yaml")
            }
        }
    except Exception as e:
        logger.error(f"Error fetching model comparison summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/reverse-engineer-yaml", response_model=dict[str, Any])
async def reverse_engineer_yaml(request: dict[str, Any]):
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
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Reverse engineering failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
