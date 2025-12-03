"""
Suggestion Generation Router

Endpoints for generating automation suggestions from detected patterns using LLM.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.data_api_client import DataAPIClient
from ..clients.data_enrichment_client import DataEnrichmentClient
from ..clients.ha_client import HomeAssistantClient
from ..config import settings
from ..database import (
    can_trigger_manual_refresh,
    get_db,
    get_patterns,
    get_suggestions,
    get_suggestions_with_home_type,
    record_manual_refresh,
    store_suggestion,
)
from ..llm.openai_client import OpenAIClient
from ..prompt_building.unified_prompt_builder import UnifiedPromptBuilder
from ..services.model_comparison_service import ModelComparisonService
from ..services.suggestion_context_enricher import SuggestionContextEnricher
from ..services.learning.user_profile_builder import UserProfileBuilder
from ..synergy_detection.relationship_analyzer import HomeAssistantAutomationChecker
from ..validation.device_validator import DeviceValidator, ValidationResult
from ..automation_templates.device_templates import DeviceTemplateGenerator
from .dependencies.auth import require_authenticated_user

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/suggestions", tags=["Suggestions"])

# Initialize OpenAI client (only if API key is configured)
openai_client: OpenAIClient | None = None
if settings.openai_api_key:
    openai_client = OpenAIClient(api_key=settings.openai_api_key, model=settings.openai_model)
else:
    logger.warning("⚠️ OpenAI API key not configured - suggestion generation will be limited")

# Initialize Unified Prompt Builder
prompt_builder = UnifiedPromptBuilder()

# Initialize Data API client for fetching device metadata
data_api_client = DataAPIClient(base_url="http://data-api:8006")

# Initialize Data Enrichment client for context data
enrichment_client = DataEnrichmentClient()

# Initialize Context Enricher (Phase 2 improvement)
context_enricher = SuggestionContextEnricher(
    data_api_client=data_api_client,
    enrichment_client=enrichment_client
)

# Initialize User Profile Builder (Phase 3 improvement)
user_profile_builder = UserProfileBuilder()

# Initialize Device Validator for validating suggestions
device_validator = DeviceValidator(data_api_client)

# Phase 2.2: Initialize Device Template Generator
device_template_generator = DeviceTemplateGenerator()

# Phase 4.1: Initialize Home Assistant Automation Checker (if HA is configured)
automation_checker: HomeAssistantAutomationChecker | None = None
if settings.ha_url and settings.ha_token:
    try:
        ha_client = HomeAssistantClient(
            ha_url=settings.ha_url,
            access_token=settings.ha_token
        )
        automation_checker = HomeAssistantAutomationChecker(ha_client)
        logger.info("✅ HomeAssistantAutomationChecker initialized")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize HomeAssistantAutomationChecker: {e}")
        automation_checker = None
else:
    logger.debug("Home Assistant not configured - automation duplicate checking disabled")


# Pydantic models for model comparison API
class ModelStats(BaseModel):
    """Statistics for a single model"""
    model_name: str = Field(..., description="Model identifier")
    total_requests: int = Field(..., description="Total number of requests")
    total_input_tokens: int = Field(..., description="Total input tokens used")
    total_output_tokens: int = Field(..., description="Total output tokens used")
    total_tokens: int = Field(..., description="Total tokens (input + output)")
    total_cost_usd: float = Field(..., description="Total cost in USD")
    avg_cost_per_request: float = Field(..., description="Average cost per request")
    avg_input_tokens: float = Field(..., description="Average input tokens per request")
    avg_output_tokens: float = Field(..., description="Average output tokens per request")
    is_local: bool = Field(..., description="Whether model is local (no API cost)")
    sources: list[str] = Field(..., description="Sources that use this model")


class ComparisonSummary(BaseModel):
    """Summary of model comparison"""
    total_models: int = Field(..., description="Total number of models")
    total_requests: int = Field(..., description="Total requests across all models")
    total_cost_usd: float = Field(..., description="Total cost across all models")
    avg_cost_per_request: float = Field(..., description="Average cost per request")


class CostSavingsOpportunity(BaseModel):
    """Cost savings opportunity"""
    current_model: str = Field(..., description="Currently used model")
    recommended_model: str = Field(..., description="Recommended model")
    potential_savings_percent: float = Field(..., description="Potential savings percentage")
    quality_impact: str = Field(..., description="Expected quality impact")
    reasoning: str = Field(..., description="Reasoning for recommendation")


class ModelRecommendations(BaseModel):
    """Model recommendations"""
    best_overall: str | None = Field(None, description="Best overall model")
    best_cost: str | None = Field(None, description="Best cost-optimized model")
    best_quality: str | None = Field(None, description="Best quality model")
    reasoning: dict[str, str] = Field(..., description="Reasoning for each recommendation")
    cost_savings_opportunities: list[CostSavingsOpportunity] = Field(
        default_factory=list,
        description="Cost savings opportunities"
    )


class ModelComparisonResponse(BaseModel):
    """Response for model comparison endpoint"""
    models: list[ModelStats] = Field(..., description="Statistics for each model")
    summary: ComparisonSummary = Field(..., description="Summary statistics")
    recommendations: ModelRecommendations = Field(..., description="Model recommendations")
    timestamp: str = Field(..., description="Timestamp of the comparison")


def get_model_comparison_service() -> ModelComparisonService:
    """
    Get or create ModelComparisonService instance.
    
    Collects instances from various sources to aggregate stats.
    """
    # Get OpenAIClient (already initialized)
    openai_client_instance = openai_client

    # Try to get MultiModelEntityExtractor from ask_ai_router
    multi_model_extractor = None
    try:
        # Import the module to access the global variable
        from ..api import ask_ai_router
        multi_model_extractor = getattr(ask_ai_router, '_multi_model_extractor', None)
    except (ImportError, AttributeError) as e:
        logger.debug(f"Could not access multi_model_extractor: {e}")

    # Try to get DescriptionGenerator and SuggestionRefiner
    # These are typically created on-demand, so we may not have global instances
    description_generator = None
    suggestion_refiner = None

    return ModelComparisonService(
        openai_client=openai_client_instance,
        multi_model_extractor=multi_model_extractor,
        description_generator=description_generator,
        suggestion_refiner=suggestion_refiner
    )


@router.get("/usage/stats")
async def get_usage_stats() -> dict[str, Any]:
    """
    Get OpenAI API usage statistics including token counts and cost estimates.
    
    Returns:
        Dictionary with usage statistics, token counts, cost breakdown, and cache stats
    """
    if not openai_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI client not initialized"
        )

    if not openai_client:
        raise HTTPException(
            status_code=503,
            detail="OpenAI client not configured. Set OPENAI_API_KEY environment variable."
        )
    stats = openai_client.get_usage_stats()

    # Add model-specific cost breakdown
    from ..llm.cost_tracker import CostTracker

    model_breakdown = {
        'gpt-4o': {
            'input_cost_per_1m': CostTracker.GPT4O_INPUT_COST_PER_1M,
            'output_cost_per_1m': CostTracker.GPT4O_OUTPUT_COST_PER_1M,
            'cached_input_cost_per_1m': CostTracker.GPT4O_CACHED_INPUT_COST_PER_1M
        },
        'gpt-4o-mini': {
            'input_cost_per_1m': CostTracker.GPT4O_MINI_INPUT_COST_PER_1M,
            'output_cost_per_1m': CostTracker.GPT4O_MINI_OUTPUT_COST_PER_1M,
            'cached_input_cost_per_1m': CostTracker.GPT4O_MINI_CACHED_INPUT_COST_PER_1M
        }
    }

    # Add cache statistics (Phase 4)
    cache_stats = {}
    try:
        from ..services.entity_context_cache import get_entity_cache
        entity_cache = get_entity_cache()
        cache_stats = entity_cache.get_stats()
    except Exception as e:
        logger.warning(f"Failed to get cache stats: {e}")
        cache_stats = {'error': str(e)}

    # Phase 5: Calculate success metrics
    success_metrics = {}
    try:
        from ..utils.success_metrics import calculate_success_metrics

        # Estimate total requests from endpoint breakdown
        total_requests = sum(
            endpoint_data.get('calls', 0)
            for endpoint_data in stats.get('endpoint_breakdown', {}).values()
        )

        success_metrics = calculate_success_metrics(
            current_stats=stats,
            cache_stats=cache_stats if 'error' not in cache_stats else None,
            total_requests=total_requests if total_requests > 0 else None
        )
    except Exception as e:
        logger.warning(f"Failed to calculate success metrics: {e}")
        success_metrics = {'error': str(e)}

    return {
        **stats,
        'model_pricing': model_breakdown,
        'last_usage': openai_client.last_usage if openai_client else None,
        'cache_stats': cache_stats,
        'success_metrics': success_metrics,  # Phase 5: Add success metrics
        'timestamp': datetime.now(timezone.utc).isoformat()
    }


@router.get("/models/compare", response_model=ModelComparisonResponse)
async def compare_models() -> ModelComparisonResponse:
    """
    Compare all AI models used in the service.
    
    Returns side-by-side comparison of all models including:
    - Usage statistics per model
    - Cost analysis
    - Recommendations (best overall, best cost, best quality)
    - Cost savings opportunities
    
    Returns:
        ModelComparisonResponse with model stats, summary, and recommendations
    """
    try:
        comparison_service = get_model_comparison_service()

        # Get comparison data
        comparison = comparison_service.compare_models()
        recommendations = comparison_service.calculate_recommendations()

        # Convert to Pydantic models
        models = [ModelStats(**model_data) for model_data in comparison.get('models', [])]
        summary_data = comparison.get('summary', {})
        summary = ComparisonSummary(
            total_models=summary_data.get('total_models', 0),
            total_requests=summary_data.get('total_requests', 0),
            total_cost_usd=summary_data.get('total_cost_usd', 0.0),
            avg_cost_per_request=summary_data.get('avg_cost_per_request', 0.0)
        )

        # Convert recommendations
        cost_savings = [
            CostSavingsOpportunity(**opp)
            for opp in recommendations.get('cost_savings_opportunities', [])
        ]
        model_recommendations = ModelRecommendations(
            best_overall=recommendations.get('best_overall'),
            best_cost=recommendations.get('best_cost'),
            best_quality=recommendations.get('best_quality'),
            reasoning=recommendations.get('reasoning', {}),
            cost_savings_opportunities=cost_savings
        )

        return ModelComparisonResponse(
            models=models,
            summary=summary,
            recommendations=model_recommendations,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        logger.error(f"Failed to compare models: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare models: {str(e)}"
        )


@router.get("/refresh/status")
async def refresh_status(
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Return the current manual refresh status and cooldown timer.
    """
    try:
        cooldown_hours = settings.manual_refresh_cooldown_hours
        allowed, last_trigger = await can_trigger_manual_refresh(db, cooldown_hours=cooldown_hours)

        next_allowed_at = None
        if last_trigger and not allowed:
            next_allowed_at = (last_trigger + timedelta(hours=cooldown_hours)).isoformat()

        return {
            "allowed": allowed,
            "last_trigger_at": last_trigger.isoformat() if last_trigger else None,
            "next_allowed_at": next_allowed_at
        }
    except Exception as e:
        logger.error(f"Failed to get refresh status: {e}", exc_info=True)
        error_detail = {
            "error": "Failed to get refresh status",
            "error_code": "REFRESH_STATUS_ERROR",
            "message": str(e),
            "retry_after": None
        }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.post("/refresh", status_code=status.HTTP_202_ACCEPTED)
async def refresh_suggestions(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_authenticated_user)
) -> dict[str, Any]:
    """
    Manually trigger the nightly suggestion pipeline with a 1-per-day guard.
    """
    cooldown_hours = settings.manual_refresh_cooldown_hours
    allowed, last_trigger = await can_trigger_manual_refresh(db, cooldown_hours=cooldown_hours)

    if not allowed:
        next_available = last_trigger + timedelta(hours=cooldown_hours)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Manual refresh already triggered recently.",
                "next_allowed_at": next_available.isoformat()
            }
        )

    # Ensure scheduler is available
    from .analysis_router import _scheduler  # Local import to avoid circular dependency

    if _scheduler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analysis scheduler is not initialized yet."
        )

    await record_manual_refresh(db)
    background_tasks.add_task(_scheduler.trigger_manual_run)

    next_window = datetime.now(timezone.utc) + timedelta(hours=cooldown_hours)
    logger.info("✅ Manual suggestion refresh queued via /api/suggestions/refresh")

    return {
        "success": True,
        "message": "Manual refresh queued successfully.",
        "next_allowed_at": next_window.isoformat()
    }


@router.post("/generate")
async def generate_suggestions(
    pattern_type: str | None = Query(default=None, description="Generate suggestions for specific pattern type"),
    min_confidence: float = Query(default=0.7, ge=0.0, le=1.0, description="Minimum pattern confidence"),
    max_suggestions: int = Query(default=10, ge=1, le=50, description="Maximum suggestions to generate"),
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_authenticated_user)
) -> dict[str, Any]:
    """
    Generate automation suggestions from detected patterns using OpenAI.
    
    This endpoint:
    1. Retrieves patterns from database (filtered by type and confidence)
    2. For each pattern, calls OpenAI to generate automation suggestion
    3. Stores suggestions in database
    4. Returns summary with token usage and costs
    """
    start_time = time.time()

    try:
        logger.info(f"Starting suggestion generation: pattern_type={pattern_type}, min_confidence={min_confidence}")

        # Step 1: Retrieve patterns from database
        patterns = await get_patterns(
            db,
            pattern_type=pattern_type,
            min_confidence=min_confidence,
            limit=max_suggestions
        )

        if not patterns:
            return {
                "success": False,
                "message": f"No patterns found with confidence >= {min_confidence}",
                "data": {
                    "suggestions_generated": 0,
                    "patterns_processed": 0
                }
            }

        logger.info(f"✅ Retrieved {len(patterns)} patterns from database")

        # Step 2: Generate suggestions using OpenAI
        suggestions_generated = 0
        suggestions_stored = []
        errors = []

        # Generate predictive suggestions (NEW - Proactive Opportunities)
        logger.info("→ Generating predictive automation suggestions...")
        try:
            from ..suggestion_generation.predictive_generator import PredictiveAutomationGenerator

            # Fetch recent events for predictive analysis
            predictive_generator = PredictiveAutomationGenerator()
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(days=30)

            try:
                events_df = await data_api_client.fetch_events(
                    start_time=start_dt,
                    end_time=end_dt,
                    limit=50000
                )
                predictive_suggestions = predictive_generator.generate_predictive_suggestions(events_df)
                logger.info(f"   ✅ Generated {len(predictive_suggestions)} predictive suggestions")

                # Store predictive suggestions
                for pred_sugg in predictive_suggestions:
                    try:
                        # Add source_type to metadata for tracking
                        metadata = pred_sugg.get('metadata', {})
                        metadata['source_type'] = 'predictive'
                        metadata['suggestion_type'] = pred_sugg.get('type', 'repetitive_action')
                        
                        suggestion_data = {
                            'pattern_id': None,
                            'title': pred_sugg.get('title', 'Predictive Automation'),
                            'description': pred_sugg.get('description', ''),
                            'automation_yaml': None,
                            'confidence': pred_sugg.get('confidence', 0.8),
                            'category': pred_sugg.get('type', 'convenience'),
                            'priority': pred_sugg.get('priority', 'medium'),
                            'status': pred_sugg.get('status', 'draft'),
                            'device_id': pred_sugg.get('device_id'),
                            'device1': pred_sugg.get('device1'),
                            'device2': pred_sugg.get('device2'),
                            'devices_involved': pred_sugg.get('devices') or pred_sugg.get('device_ids'),
                            'metadata': metadata,
                            'device_info': pred_sugg.get('device_info')
                        }
                        
                        # Phase 2: Enrich with context
                        try:
                            entity_id = pred_sugg.get('device_id') if pred_sugg.get('device_id') and '.' in pred_sugg.get('device_id') else None
                            suggestion_data = await context_enricher.enrich_suggestion(
                                suggestion_data,
                                device_id=pred_sugg.get('device_id') if pred_sugg.get('device_id') and '.' not in pred_sugg.get('device_id') else None,
                                entity_id=entity_id
                            )
                        except Exception as e:
                            logger.warning(f"Context enrichment failed for predictive suggestion: {e}")
                        
                        # Phase 4.1: Device Health Integration - Check health before storing
                        if not await _check_and_filter_by_health(suggestion_data, "predictive"):
                            logger.info("Skipping predictive suggestion due to poor device health")
                            continue
                        
                        # Phase 4.1: Existing Automation Analysis - Check for duplicates
                        if not await _check_and_filter_duplicate_automations(suggestion_data, "predictive"):
                            logger.info("Skipping predictive suggestion - duplicate automation exists")
                            continue
                        
                        stored = await store_suggestion(db, suggestion_data)
                        suggestions_stored.append(stored)
                        suggestions_generated += 1
                    except Exception as e:
                        logger.warning(f"Failed to store predictive suggestion: {e}")
            except Exception as e:
                logger.warning(f"Failed to fetch events for predictive generation: {e}")
        except Exception as e:
            logger.warning(f"Predictive suggestion generation failed: {e}")

        for pattern in patterns:
            try:
                logger.info(f"Processing pattern #{pattern.id}: type={pattern.pattern_type}, device_id={pattern.device_id}")
                logger.info(f"Pattern metadata type: {type(pattern.pattern_metadata)}, value: {pattern.pattern_metadata}")

                # Convert SQLAlchemy model to dict
                # Handle pattern_metadata safely - it might be string, dict, or None
                metadata = pattern.pattern_metadata
                if isinstance(metadata, str):
                    try:
                        import json
                        metadata = json.loads(metadata)
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}
                elif not isinstance(metadata, dict):
                    metadata = {}

                pattern_dict = {
                    'device_id': pattern.device_id,
                    'pattern_type': pattern.pattern_type,
                    'confidence': pattern.confidence,
                    'occurrences': pattern.occurrences,
                    'metadata': metadata
                }

                logger.info(f"Created pattern_dict: {pattern_dict}")

                # Extract hour/minute for time_of_day patterns
                if pattern.pattern_type == 'time_of_day' and metadata:
                    pattern_dict['hour'] = int(metadata.get('avg_time_decimal', 0))
                    pattern_dict['minute'] = int((metadata.get('avg_time_decimal', 0) % 1) * 60)

                # Extract device1/device2 for co_occurrence patterns
                if pattern.pattern_type == 'co_occurrence' and metadata:
                    # Device ID is stored as "device1+device2"
                    if '+' in pattern.device_id:
                        device1, device2 = pattern.device_id.split('+', 1)
                        pattern_dict['device1'] = device1
                        pattern_dict['device2'] = device2

                # ==== NEW: Fetch device metadata for friendly names ====
                device_context = await _build_device_context(pattern_dict)

                # Generate cascade suggestions (NEW - Progressive Enhancement)
                try:
                    from ..suggestion_generation.cascade_generator import CascadeSuggestionGenerator
                    cascade_generator = CascadeSuggestionGenerator()
                    cascade_suggestions = cascade_generator.generate_cascade(
                        base_pattern=pattern_dict,
                        device_context=device_context
                    )
                    logger.info(f"   → Generated {len(cascade_suggestions)} cascade suggestions")

                    # Store cascade suggestions (store first level, others as alternatives)
                    for cascade_sugg in cascade_suggestions[:1]:  # Store first level for now
                        # Add source_type to metadata for tracking
                        cascade_metadata = cascade_sugg.get('metadata', {})
                        cascade_metadata['source_type'] = 'cascade'
                        cascade_metadata['cascade_level'] = cascade_sugg.get('level', 1)
                        cascade_metadata['complexity'] = cascade_sugg.get('complexity', 'simple')
                        
                        cascade_data = {
                            'pattern_id': pattern.id,
                            'title': cascade_sugg.get('title', ''),
                            'description': cascade_sugg.get('description', ''),
                            'automation_yaml': None,
                            'confidence': cascade_sugg.get('confidence', 0.8),
                            'category': 'convenience',
                            'priority': cascade_sugg.get('complexity', 'medium'),
                            'status': cascade_sugg.get('status', 'draft'),
                            'device_id': cascade_sugg.get('device_id', pattern.device_id),
                            'device1': cascade_sugg.get('device1') or pattern_dict.get('device1'),
                            'device2': cascade_sugg.get('device2') or pattern_dict.get('device2'),
                            'devices_involved': cascade_sugg.get('devices_involved'),
                            'metadata': cascade_metadata,
                            'device_capabilities': cascade_sugg.get('device_capabilities'),
                            'device_info': cascade_sugg.get('device_info')
                        }
                        
                        # Phase 2: Enrich with context
                        try:
                            entity_id = cascade_data['device_id'] if cascade_data['device_id'] and '.' in cascade_data['device_id'] else None
                            cascade_data = await context_enricher.enrich_suggestion(
                                cascade_data,
                                device_id=cascade_data['device_id'] if cascade_data['device_id'] and '.' not in cascade_data['device_id'] else None,
                                entity_id=entity_id
                            )
                        except Exception as e:
                            logger.warning(f"Context enrichment failed for cascade suggestion: {e}")
                        
                        # Phase 4.1: Device Health Integration - Check health before storing
                        if not await _check_and_filter_by_health(cascade_data, "cascade"):
                            logger.info("Skipping cascade suggestion due to poor device health")
                            continue
                        
                        # Phase 4.1: Existing Automation Analysis - Check for duplicates
                        if not await _check_and_filter_duplicate_automations(cascade_data, "cascade"):
                            logger.info("Skipping cascade suggestion - duplicate automation exists")
                            continue
                        
                        stored = await store_suggestion(db, cascade_data)
                        suggestions_stored.append(stored)
                        suggestions_generated += 1
                except Exception as e:
                    logger.warning(f"Cascade generation failed for pattern {pattern.id}: {e}")

                logger.info(f"Generating suggestion for pattern #{pattern.id}: {pattern.device_id}")

                # ==== VALIDATION ENABLED: Validate suggestion feasibility before generating ====
                validation_result = await _validate_pattern_feasibility(pattern_dict, device_context)

                if not validation_result.is_valid:
                    logger.warning(f"Pattern #{pattern.id} validation failed: {validation_result.error_message}")
                    # Skip this pattern or generate alternative suggestion
                    if validation_result.available_alternatives:
                        logger.info(f"Found alternatives for pattern #{pattern.id}: {validation_result.available_alternatives}")
                        # Generate alternative suggestion using available devices
                        description_data = await _generate_alternative_suggestion(
                            pattern_dict,
                            device_context,
                            validation_result
                        )
                    else:
                        logger.info(f"No alternatives found for pattern #{pattern.id}, skipping")
                        continue
                else:
                    # Original pattern is valid, proceed normally
                    # Build prompt using UnifiedPromptBuilder
                    prompt_dict = await prompt_builder.build_pattern_prompt(
                        pattern=pattern_dict,
                        device_context=device_context,
                        output_mode="description"
                    )

                    # Generate with unified method
                    if not openai_client:
                        raise HTTPException(
                            status_code=503,
                            detail="OpenAI client not configured. Set OPENAI_API_KEY environment variable."
                        )
                    result = await openai_client.generate_with_unified_prompt(
                        prompt_dict=prompt_dict,
                        temperature=0.7,
                        max_tokens=300,
                        endpoint="pattern_suggestion_generation",  # Phase 5: Track endpoint
                        output_format="description"
                    )

                    # Parse result to match expected format
                    description_data = {
                        'title': result.get('title', pattern_dict.get('device_id', 'Automation')),
                        'description': result.get('description', ''),
                        'rationale': result.get('rationale', ''),
                        'category': result.get('category', 'convenience'),
                        'priority': result.get('priority', 'medium')
                    }

                # Build device info entries from context
                device_info_entries = []
                if device_context:
                    if isinstance(device_context.get('device_id'), str):
                        entity_id = device_context['device_id']
                        device_info_entries.append({
                            'entity_id': entity_id,
                            'friendly_name': device_context.get('name', entity_id),
                            'domain': device_context.get('domain', entity_id.split('.')[0] if '.' in entity_id else 'device'),
                            'selected': True
                        })
                    device1_ctx = device_context.get('device1')
                    if isinstance(device1_ctx, dict) and isinstance(device1_ctx.get('entity_id'), str):
                        entity_id = device1_ctx['entity_id']
                        device_info_entries.append({
                            'entity_id': entity_id,
                            'friendly_name': device1_ctx.get('name', entity_id),
                            'domain': device1_ctx.get('domain', entity_id.split('.')[0] if '.' in entity_id else 'device'),
                            'selected': True
                        })
                    device2_ctx = device_context.get('device2')
                    if isinstance(device2_ctx, dict) and isinstance(device2_ctx.get('entity_id'), str):
                        entity_id = device2_ctx['entity_id']
                        device_info_entries.append({
                            'entity_id': entity_id,
                            'friendly_name': device2_ctx.get('name', entity_id),
                            'domain': device2_ctx.get('domain', entity_id.split('.')[0] if '.' in entity_id else 'device'),
                            'selected': True
                        })

                device_capabilities = {}
                if device_info_entries:
                    device_capabilities['devices'] = device_info_entries

                # Add source_type to metadata for tracking
                if not isinstance(metadata, dict):
                    metadata = {}
                metadata['source_type'] = 'pattern'
                metadata['pattern_type'] = pattern.pattern_type
                
                # Store in database
                suggestion_data = {
                    'pattern_id': pattern.id,
                    'title': description_data['title'],
                    'description': description_data['description'],
                    'automation_yaml': None,  # Story AI1.24: No YAML until approved
                    'confidence': pattern.confidence,
                    'category': description_data['category'],
                    'priority': description_data['priority'],
                    'status': 'draft',
                    'device_id': pattern.device_id,
                    'device1': pattern_dict.get('device1'),
                    'device2': pattern_dict.get('device2'),
                    'devices_involved': [pattern.device_id] if pattern.device_id else None,
                    'metadata': metadata,
                    'device_capabilities': device_capabilities if device_capabilities else None,
                    'device_info': device_info_entries or None
                }

                # Phase 2: Enrich with context (energy, historical, weather, carbon)
                try:
                    entity_id = pattern.device_id if '.' in pattern.device_id else None
                    suggestion_data = await context_enricher.enrich_suggestion(
                        suggestion_data,
                        device_id=pattern.device_id if '.' not in pattern.device_id else None,
                        entity_id=entity_id
                    )
                    logger.info(f"✅ Enriched suggestion with context data")
                except Exception as e:
                    logger.warning(f"Context enrichment failed (continuing without): {e}")

                # Phase 4.1: Device Health Integration - Check and filter by device health
                if not await _check_and_filter_by_health(suggestion_data, "pattern"):
                    logger.info(f"Skipping suggestion for pattern #{pattern.id} due to poor device health")
                    continue  # Skip this suggestion
                
                # Phase 4.1: Existing Automation Analysis - Check for duplicates
                if not await _check_and_filter_duplicate_automations(suggestion_data, "pattern"):
                    logger.info(f"Skipping suggestion for pattern #{pattern.id} - duplicate automation exists")
                    continue  # Skip this suggestion

                stored_suggestion = await store_suggestion(db, suggestion_data)
                suggestions_stored.append(stored_suggestion)
                suggestions_generated += 1

                logger.info(f"✅ Generated and stored suggestion: {description_data['title']}")

            except Exception as e:
                import traceback
                error_msg = f"Failed to generate suggestion for pattern #{pattern.id}: {str(e)}"
                logger.error(error_msg)
                logger.error(f"Full traceback: {traceback.format_exc()}")
                errors.append(error_msg)
                # Continue with next pattern

        # Phase 2.2: Generate device-specific template suggestions (Enhanced 2025)
        logger.info("→ Generating device-specific automation suggestions (template-first)...")
        try:
            # Get devices with device_type from data-api (returns list directly)
            devices = await data_api_client.fetch_devices(limit=100)
            
            # Get all entities for template-based entity resolution
            all_entities = []
            try:
                all_entities = await data_api_client.fetch_entities(limit=1000)
            except Exception as e:
                logger.debug(f"Failed to fetch all entities: {e}")
            
            device_suggestions_count = 0
            for device in devices:
                device_type = device.get("device_type")
                device_id = device.get("device_id")
                
                if not device_type or not device_id:
                    continue
                
                # Get entities for this device (returns list directly)
                try:
                    entities = await data_api_client.fetch_entities(device_id=device_id)
                except Exception as e:
                    logger.debug(f"Failed to fetch entities for device {device_id}: {e}")
                    entities = []
                
                # Enhanced 2025: Use template-first generation with scoring
                template_suggestions = device_template_generator.suggest_device_automations(
                    device_id=device_id,
                    device_type=device_type,
                    device_entities=entities,
                    all_entities=all_entities,
                    max_suggestions=5  # Top 5 templates per device
                )
                
                # Store each template suggestion
                for template_sugg in template_suggestions:
                    # Check if similar automation already exists
                    if not await _check_and_filter_duplicate_automations(template_sugg, "device_template"):
                        logger.debug(f"Skipping device template - duplicate exists: {template_sugg.get('title')}")
                        continue
                    
                    # Enhanced 2025: Use template score and metadata
                    suggestion_data = {
                        'pattern_id': None,
                        'title': template_sugg.get('title'),
                        'description': template_sugg.get('description'),
                        'automation_yaml': template_sugg.get('automation_yaml'),  # Template-first YAML
                        'confidence': template_sugg.get('template_score', template_sugg.get('confidence', 0.8)),
                        'category': template_sugg.get('category', 'device_specific'),
                        'priority': _map_complexity_to_priority(template_sugg.get('complexity', 'simple')),
                        'status': 'draft',
                        'device_id': device_id,
                        'devices_involved': [device_id],
                        'metadata': {
                            'source_type': 'device_template',
                            'device_type': device_type,
                            'template_score': template_sugg.get('template_score', 0.8),
                            'template_match_quality': template_sugg.get('template_match_quality', 1.0),
                            'complexity': template_sugg.get('complexity', 'simple'),
                            'variants': template_sugg.get('variants', ['simple']),
                            'entity_mapping': template_sugg.get('entity_mapping', {})
                        }
                    }
                    
                    stored = await store_suggestion(db, suggestion_data)
                    suggestions_stored.append(stored)
                    device_suggestions_count += 1
                    suggestions_generated += 1
            
            if device_suggestions_count > 0:
                logger.info(f"   ✅ Generated {device_suggestions_count} device-specific template suggestions")
        except Exception as e:
            logger.warning(f"Device-specific template generation failed: {e}")

        # Step 3: Get usage stats
        usage_stats = openai_client.get_usage_stats()

        # Calculate performance
        duration = time.time() - start_time

        logger.info(f"✅ Suggestion generation completed in {duration:.2f}s")
        logger.info(f"   Tokens used: {usage_stats['total_tokens']}, Cost: ${usage_stats['estimated_cost_usd']:.4f}")

        return {
            "success": True,
            "message": f"Generated {suggestions_generated} automation suggestions",
            "data": {
                "suggestions_generated": suggestions_generated,
                "suggestions_stored": len(suggestions_stored),
                "patterns_processed": len(patterns),
                "errors": errors,
                "openai_usage": usage_stats,
                "performance": {
                    "duration_seconds": round(duration, 2),
                    "avg_time_per_suggestion": round(duration / suggestions_generated, 2) if suggestions_generated > 0 else 0
                },
                "suggestions": [
                    {
                        "id": s.id,
                        "title": s.title,
                        "category": s.category,
                        "priority": s.priority,
                        "confidence": s.confidence
                    }
                    for s in suggestions_stored[:5]  # Preview first 5
                ]
            }
        }

    except Exception as e:
        logger.error(f"❌ Suggestion generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Suggestion generation failed: {str(e)}"
        )


@router.get("/list")
async def list_suggestions(
    status_filter: str | None = Query(default=None, description="Filter by status (pending, approved, deployed, rejected)"),
    label_filter: str | None = Query(default=None, description="Filter by labels (comma-separated, e.g., 'outdoor,security')"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum suggestions to return"),
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    List automation suggestions with optional filters.
    """
    try:
        fetch_limit = max(limit * 10, 500)
        
        # Get home type for suggestion ranking (Home Type Integration)
        home_type = None
        try:
            from ..clients.home_type_client import HomeTypeClient
            from ..config import settings
            home_type_client = HomeTypeClient(
                base_url="http://ai-automation-service:8018",
                api_key=settings.ai_automation_api_key
            )
            home_type_data = await home_type_client.get_home_type(use_cache=True)
            home_type = home_type_data.get('home_type')
            await home_type_client.close()
            if home_type:
                logger.debug(f"Using home type '{home_type}' for suggestion ranking")
        except Exception as e:
            logger.debug(f"Home type unavailable, using default ranking: {e}")
            home_type = None
        
        # Use home type-aware ranking if available
        if home_type:
            raw_suggestions = await get_suggestions_with_home_type(
                db, 
                status=status_filter, 
                limit=fetch_limit,
                home_type=home_type
            )
        else:
            raw_suggestions = await get_suggestions(db, status=status_filter, limit=fetch_limit)

        # Phase 3: Build user profile for personalization
        user_profile = None
        try:
            user_profile = await user_profile_builder.build_user_profile(db, user_id='default')
            logger.debug(f"Built user profile: {len(user_profile.get('preferred_categories', {}))} categories, {len(user_profile.get('preferred_devices', {}))} devices")
        except Exception as e:
            logger.warning(f"Failed to build user profile (continuing without personalization): {e}")

        # Apply label filtering if requested (HA 2025 feature)
        if label_filter:
            try:
                from ..services.automation.label_filtering import filter_entities_by_labels, enhance_suggestions_with_labels
                
                # Parse label filter (comma-separated)
                required_labels = [label.strip() for label in label_filter.split(",")]
                
                # Get entities for label filtering
                from ..clients.data_api_client import DataAPIClient
                data_api_client = DataAPIClient()
                entities_data = await data_api_client.get_all_entities()
                await data_api_client.close()
                
                # Enhance suggestions with label information
                raw_suggestions = enhance_suggestions_with_labels(raw_suggestions, entities_data)
                
                # Filter suggestions by labels
                filtered_suggestions = []
                for suggestion in raw_suggestions:
                    detected_labels = suggestion.get("detected_labels", [])
                    if any(label in detected_labels for label in required_labels):
                        filtered_suggestions.append(suggestion)
                
                raw_suggestions = filtered_suggestions
                logger.info(f"Label filtering: {len(raw_suggestions)} suggestions match labels: {required_labels}")
            except Exception as e:
                logger.warning(f"Label filtering failed, continuing without filter: {e}")
        
        suggestions_list = []
        for s in raw_suggestions:
            device_capabilities = s.device_capabilities or {}
            if not isinstance(device_capabilities, dict):
                device_capabilities = {}

            device_info = []
            if isinstance(device_capabilities, dict):
                devices_from_capabilities = device_capabilities.get('devices')
                if isinstance(devices_from_capabilities, list):
                    for entry in devices_from_capabilities:
                        if isinstance(entry, dict):
                            device_info.append(entry)
                elif isinstance(devices_from_capabilities, dict):
                    device_info.append(devices_from_capabilities)

            if not device_info and (s.status in ('draft', 'refining')) and not s.automation_yaml:
                logger.debug(
                    "Skipping suggestion %s due to missing device information",
                    s.id
                )
                continue

            # Extract source_type and context from metadata for UI display
            source_type = 'pattern'  # Default
            # Handle missing suggestion_metadata column gracefully
            try:
                suggestion_metadata = s.suggestion_metadata if isinstance(s.suggestion_metadata, dict) else {}
                if isinstance(s.suggestion_metadata, dict):
                    source_type = suggestion_metadata.get('source_type', 'pattern')
            except AttributeError:
                # Column doesn't exist in database yet
                suggestion_metadata = {}
                source_type = 'pattern'
            
            # Extract context data (Phase 2 improvement)
            context_data = suggestion_metadata.get('context', {})
            energy_savings = suggestion_metadata.get('energy_savings', {})
            estimated_monthly_savings = suggestion_metadata.get('estimated_monthly_savings', 0)
            
            # Phase 3: Calculate user preference match
            user_preference_match = 0.0
            user_preference_badge = None
            if user_profile and isinstance(user_profile, dict):
                # Extract device_id from metadata or device_capabilities
                device_id = None
                if isinstance(suggestion_metadata, dict):
                    device_id = suggestion_metadata.get('device_id')
                if not device_id and isinstance(s.device_capabilities, dict):
                    devices = s.device_capabilities.get('devices', [])
                    if isinstance(devices, list) and len(devices) > 0:
                        device_id = devices[0].get('entity_id') if isinstance(devices[0], dict) else None
                
                suggestion_dict_for_match = {
                    'category': s.category,
                    'device_id': device_id,
                    'priority': s.priority,
                    'metadata': suggestion_metadata
                }
                try:
                    user_preference_match = user_profile_builder.calculate_preference_match(
                        suggestion_dict_for_match,
                        user_profile
                    )
                    
                    # Add badge if high match (>0.7)
                    if user_preference_match > 0.7:
                        user_preference_badge = {
                            'score': user_preference_match,
                            'label': 'Matches your preferences'
                        }
                except Exception as e:
                    logger.debug(f"Failed to calculate preference match: {e}")
            
            # Extract device_id from metadata or device_capabilities for response
            response_device_id = device_id  # Use device_id extracted above for user preference match
            if not response_device_id and device_info and len(device_info) > 0:
                response_device_id = device_info[0].get('entity_id') if isinstance(device_info[0], dict) else None
            
            suggestion_dict = {
                "id": s.id,
                "pattern_id": s.pattern_id,
                "title": s.title,
                "description": s.description_only,
                "description_only": s.description_only,
                "automation_yaml": s.automation_yaml,
                "status": s.status,
                "confidence": s.confidence,
                "category": s.category,
                "priority": s.priority,
                "device_id": response_device_id,  # Include device_id in response
                "source_type": source_type,  # Phase 1: For UI badges
                "energy_savings": energy_savings,  # Phase 2: Energy savings data
                "estimated_monthly_savings": estimated_monthly_savings,  # Phase 2: Quick access
                "context": context_data,  # Phase 2: Full context
                "user_preference_match": user_preference_match,  # Phase 3: User preference score
                "user_preference_badge": user_preference_badge,  # Phase 3: Badge data
                "conversation_history": s.conversation_history or [],
                "refinement_count": s.refinement_count or 0,
                "device_capabilities": device_capabilities,
                "device_info": device_info,
                "ha_automation_id": s.ha_automation_id,
                "yaml_generated_at": s.yaml_generated_at.isoformat() if s.yaml_generated_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "deployed_at": s.deployed_at.isoformat() if s.deployed_at else None,
                "metadata": suggestion_metadata  # Include full metadata for advanced features
            }
            
            # Phase 3: Adjust weighted score with user preference
            if user_preference_match > 0 and hasattr(s, 'weighted_score'):
                try:
                    # Add user preference boost to weighted score (15% weight)
                    base_score = float(s.weighted_score) if s.weighted_score else float(s.confidence)
                    s.weighted_score = base_score + (user_preference_match * 0.15)
                    suggestion_dict['weighted_score'] = s.weighted_score
                except Exception as e:
                    logger.debug(f"Failed to adjust weighted score: {e}")

            suggestions_list.append(suggestion_dict)
            if len(suggestions_list) >= limit:
                break

        return {
            "success": True,
            "data": {
                "suggestions": suggestions_list,
                "count": len(suggestions_list)
            },
            "message": f"Retrieved {len(suggestions_list)} suggestions"
        }

    except Exception as e:
        logger.error(f"Failed to list suggestions: {e}", exc_info=True)
        # Provide structured error response with error code
        error_detail = {
            "error": "Failed to list suggestions",
            "error_code": "SUGGESTIONS_LIST_ERROR",
            "message": str(e),
            "retry_after": None
        }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.get("/usage-stats")
async def get_usage_stats() -> dict[str, Any]:
    """
    Get OpenAI API usage statistics and cost estimates.
    """
    try:
        if not openai_client:
        raise HTTPException(
            status_code=503,
            detail="OpenAI client not configured. Set OPENAI_API_KEY environment variable."
        )
    stats = openai_client.get_usage_stats()

        # Add budget alert
        from ..llm.cost_tracker import CostTracker
        budget_alert = CostTracker.check_budget_alert(
            total_cost=stats['estimated_cost_usd'],
            budget=10.0  # $10/month default budget
        )

        return {
            "success": True,
            "data": {
                **stats,
                "budget_alert": budget_alert
            },
            "message": "Usage statistics retrieved successfully"
        }

    except Exception as e:
        logger.error(f"Failed to get usage stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage stats: {str(e)}"
        )


@router.post("/usage-stats/reset")
async def reset_usage_stats() -> dict[str, Any]:
    """
    Reset OpenAI API usage statistics (for monthly reset).
    """
    try:
        if openai_client:
            openai_client.reset_usage_stats()

        return {
            "success": True,
            "message": "Usage statistics reset successfully"
        }

    except Exception as e:
        logger.error(f"Failed to reset usage stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset usage stats: {str(e)}"
        )


# ==== Helper Functions ====

def _map_complexity_to_priority(complexity: str) -> str:
    """
    Map template complexity to suggestion priority.
    
    Args:
        complexity: Template complexity (simple, standard, advanced)
        
    Returns:
        Priority string (low, medium, high)
    """
    mapping = {
        "simple": "low",
        "standard": "medium",
        "advanced": "high"
    }
    return mapping.get(complexity, "medium")

async def _check_and_filter_duplicate_automations(suggestion_data: dict[str, Any], suggestion_type: str = "pattern") -> bool:
    """
    Phase 4.1: Existing Automation Analysis
    
    Check if suggestion duplicates an existing automation and filter it out.
    Adds duplicate check metadata to suggestion_data.
    
    Args:
        suggestion_data: Suggestion dictionary to check
        suggestion_type: Type of suggestion ("pattern", "predictive", "cascade")
    
    Returns:
        True if suggestion should be stored, False if it's a duplicate and should be filtered out
    """
    # Skip check if automation checker not available
    if not automation_checker:
        return True
    
    try:
        # Extract entity pairs to check
        entity_pairs_to_check: list[tuple[str, str]] = []
        
        # For co-occurrence patterns, check device1 → device2
        device1 = suggestion_data.get('device1')
        device2 = suggestion_data.get('device2')
        
        if device1 and device2:
            # Check if these are entity IDs (contain '.') or device IDs
            # HomeAssistantAutomationChecker works with entity IDs
            # Try to get entity IDs from device_info if available
            device_info = suggestion_data.get('device_info') or []
            
            entity1 = None
            entity2 = None
            
            # If device_info is available, extract entity IDs
            if isinstance(device_info, list) and len(device_info) >= 2:
                entity1 = device_info[0].get('entity_id') if isinstance(device_info[0], dict) else None
                entity2 = device_info[1].get('entity_id') if isinstance(device_info[1], dict) else None
            elif isinstance(device_info, list) and len(device_info) == 1:
                entity1 = device_info[0].get('entity_id') if isinstance(device_info[0], dict) else None
                # Fall back to device2 if we only have one device_info entry
                entity2 = device2 if '.' in str(device2) else None
            
            # If device IDs look like entity IDs (contain '.'), use them directly
            if not entity1 and device1 and '.' in str(device1):
                entity1 = device1
            if not entity2 and device2 and '.' in str(device2):
                entity2 = device2
            
            # If we have valid entity IDs, check for duplicates
            if entity1 and entity2:
                entity_pairs_to_check.append((entity1, entity2))
        
        # Also check devices_involved list for entity pairs
        devices_involved = suggestion_data.get('devices_involved')
        if isinstance(devices_involved, list) and len(devices_involved) >= 2:
            # Check each pair in the list
            for i in range(len(devices_involved) - 1):
                entity1 = devices_involved[i]
                entity2 = devices_involved[i + 1]
                
                # Only check if both look like entity IDs
                if isinstance(entity1, str) and isinstance(entity2, str) and '.' in entity1 and '.' in entity2:
                    entity_pairs_to_check.append((entity1, entity2))
        
        # Check each entity pair for existing automations
        is_duplicate = False
        duplicate_pairs = []
        
        for entity1, entity2 in entity_pairs_to_check:
            try:
                connected = await automation_checker.is_connected(entity1, entity2)
                if connected:
                    is_duplicate = True
                    duplicate_pairs.append((entity1, entity2))
                    logger.debug(
                        f"Found existing automation connecting {entity1} → {entity2}"
                    )
            except Exception as e:
                logger.warning(f"Failed to check automation for {entity1} → {entity2}: {e}")
                # Continue checking other pairs
        
        # Filter out duplicate suggestions
        if is_duplicate:
            logger.info(
                f"Skipping {suggestion_type} suggestion - "
                f"automation already exists for pairs: {duplicate_pairs}"
            )
            return False  # Filter out this suggestion
        
        # Add duplicate check metadata
        if not isinstance(suggestion_data.get('metadata'), dict):
            suggestion_data['metadata'] = {}
        
        suggestion_data['metadata']['duplicate_check_performed'] = True
        suggestion_data['metadata']['is_duplicate'] = False
        suggestion_data['metadata']['entity_pairs_checked'] = [
            f"{pair[0]} → {pair[1]}" for pair in entity_pairs_to_check
        ]
        
        logger.debug(
            f"Duplicate check for {suggestion_type} suggestion: "
            f"checked {len(entity_pairs_to_check)} pairs, no duplicates found"
        )
        
        return True  # Proceed with suggestion
    
    except Exception as e:
        logger.warning(f"Duplicate automation check failed (continuing without duplicate filter): {e}")
        # Continue with suggestion if check fails - don't block suggestions
        return True

async def _check_and_filter_by_health(suggestion_data: dict[str, Any], suggestion_type: str = "pattern") -> bool:
    """
    Phase 4.1: Device Health Integration
    
    Check device health scores and filter suggestions for devices with poor health.
    Adds health metadata to suggestion_data.
    
    Args:
        suggestion_data: Suggestion dictionary to check
        suggestion_type: Type of suggestion ("pattern", "predictive", "cascade")
    
    Returns:
        True if suggestion should be stored, False if it should be filtered out
    """
    try:
        device_ids_to_check = []
        
        # Collect all device IDs to check
        if suggestion_data.get('device_id'):
            device_ids_to_check.append(suggestion_data['device_id'])
        if suggestion_data.get('device1'):
            device_ids_to_check.append(suggestion_data['device1'])
        if suggestion_data.get('device2'):
            device_ids_to_check.append(suggestion_data['device2'])
        
        # Also check devices_involved list
        devices_involved = suggestion_data.get('devices_involved')
        if isinstance(devices_involved, list):
            device_ids_to_check.extend([d for d in devices_involved if isinstance(d, str)])
        
        if not device_ids_to_check:
            # No device IDs to check, proceed with suggestion
            return True
        
        # Check health for each device and find worst score
        worst_health_score = 100
        worst_device_id = None
        health_scores_found = False
        
        for device_id_to_check in device_ids_to_check:
            # Only check health for actual device IDs (not entity IDs ending with .)
            # Skip entity IDs as they might not have health scores
            if device_id_to_check and '.' not in device_id_to_check:
                health_score_data = await data_api_client.get_device_health_score(device_id_to_check)
                if health_score_data:
                    health_scores_found = True
                    overall_score = health_score_data.get('overall_score', 100)
                    
                    if overall_score < worst_health_score:
                        worst_health_score = overall_score
                        worst_device_id = device_id_to_check
        
        # Filter out suggestions for devices with poor health (score < 50)
        if worst_health_score < 50:
            logger.info(
                f"Skipping {suggestion_type} suggestion - "
                f"device {worst_device_id} has poor health score: {worst_health_score}/100"
            )
            return False  # Filter out this suggestion
        
        # Add health info to metadata if available
        if health_scores_found:
            if not isinstance(suggestion_data.get('metadata'), dict):
                suggestion_data['metadata'] = {}
            
            suggestion_data['metadata']['health_score'] = worst_health_score
            if worst_device_id:
                suggestion_data['metadata']['worst_health_device_id'] = worst_device_id
            
            # Get health status from the worst device
            if worst_device_id:
                worst_health_data = await data_api_client.get_device_health_score(worst_device_id)
                if worst_health_data:
                    health_status = worst_health_data.get('health_status', 'unknown')
                    suggestion_data['metadata']['health_status'] = health_status
                    
                    # Add warning flag if health is fair (50-70) or poor (<50)
                    if worst_health_score < 70:
                        suggestion_data['metadata']['health_warning'] = True
                    
                    logger.debug(
                        f"Device health check for {suggestion_type} suggestion: "
                        f"worst score = {worst_health_score}/100 ({health_status})"
                    )
        
        return True  # Proceed with suggestion
    
    except Exception as e:
        logger.warning(f"Device health check failed (continuing without health filter): {e}")
        # Continue with suggestion if health check fails - don't block suggestions
        return True

async def _get_device_metadata_by_id(device_id: str) -> tuple[dict[str, Any] | None, str, str]:
    """
    Get device metadata by device ID or entity ID.
    
    Handles the logic for determining whether an ID is a device ID (long hex string)
    or an entity ID (domain.entity_name), then fetches appropriate metadata.
    
    Args:
        device_id: Device identifier (either device ID or entity ID)
    
    Returns:
        Tuple of (metadata, friendly_name, domain):
            - metadata: Device/entity metadata dict or None
            - friendly_name: Human-readable device name
            - domain: Entity domain (e.g., 'light', 'device', 'unknown')
    """
    # Check if device_id looks like a device ID (long hex string) or entity ID
    if '.' not in device_id and len(device_id) > 20:
        # This is a device ID, get device metadata directly
        logger.debug(f"Treating {device_id} as device ID")
        try:
            device_metadata = await data_api_client.get_device_metadata(device_id)
            if device_metadata and isinstance(device_metadata, dict):
                metadata = {
                    'friendly_name': device_metadata.get('name', ''),
                    'area_name': device_metadata.get('area_id', '')
                }
                friendly_name = device_metadata.get('name', device_id)
                domain = 'device'
            else:
                friendly_name = device_id
                metadata = None
                domain = 'unknown'
        except Exception as e:
            logger.error(f"Error getting device metadata for {device_id}: {e}")
            friendly_name = device_id
            metadata = None
            domain = 'unknown'
    else:
        # This is an entity ID, try entity metadata first
        metadata = await data_api_client.get_entity_metadata(device_id)
        if not metadata:
            # If entity not found, try to get device metadata using device_id from entity
            try:
                entities = await data_api_client.fetch_entities(limit=1000)
                for entity in entities:
                    if entity.get('entity_id') == device_id:
                        device_metadata = await data_api_client.get_device_metadata(entity.get('device_id'))
                        if device_metadata:
                            metadata = {
                                'friendly_name': device_metadata.get('name', ''),
                                'area_name': device_metadata.get('area_id', '')
                            }
                        break
            except Exception as e:
                logger.warning(f"Failed to fetch device metadata for {device_id}: {e}")

        friendly_name = data_api_client.extract_friendly_name(device_id, metadata)
        domain = device_id.split('.')[0] if '.' in device_id else 'unknown'

    return metadata, friendly_name, domain


async def _build_single_device_context(device_id: str) -> dict[str, Any]:
    """
    Build context for a single device.
    
    Args:
        device_id: Device identifier
    
    Returns:
        Dictionary with device context (device_id, name, domain, and optional metadata)
    """
    metadata, friendly_name, domain = await _get_device_metadata_by_id(device_id)
    
    context = {
        'device_id': device_id,
        'name': friendly_name,
        'domain': domain
    }
    
    # Add extra metadata if available
    if metadata:
        context['device_class'] = metadata.get('device_class')
        context['area'] = metadata.get('area_name')
    
    return context


async def _build_co_occurrence_context(device1: str | None, device2: str | None) -> dict[str, Any]:
    """
    Build context for co-occurrence pattern (two devices).
    
    Args:
        device1: First device identifier
        device2: Second device identifier
    
    Returns:
        Dictionary with device1 and device2 context
    """
    context = {}
    
    if device1:
        metadata1, friendly1, domain1 = await _get_device_metadata_by_id(device1)
        context['device1'] = {
            'entity_id': device1,
            'name': friendly1,
            'domain': domain1
        }
    
    if device2:
        metadata2, friendly2, domain2 = await _get_device_metadata_by_id(device2)
        context['device2'] = {
            'entity_id': device2,
            'name': friendly2,
            'domain': domain2
        }
    
    return context


async def _build_device_context(pattern_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Build device context with friendly names for OpenAI prompts.
    
    Routes to appropriate helper function based on pattern type to build device context
    with friendly names and metadata for use in OpenAI prompt generation.
    
    Args:
        pattern_dict: Pattern dictionary containing:
            - pattern_type: Type of pattern ('time_of_day' or 'co_occurrence')
            - device_id: For time_of_day patterns
            - device1, device2: For co_occurrence patterns
    
    Returns:
        Dictionary with friendly names and device metadata:
            - For time_of_day: {device_id, name, domain, device_class?, area?}
            - For co_occurrence: {device1: {...}, device2: {...}}
            - Empty dict on error
    """
    try:
        logger.info(f"Building device context for pattern: {pattern_dict}")
        pattern_type = pattern_dict.get('pattern_type')

        if pattern_type == 'time_of_day':
            device_id = pattern_dict.get('device_id')
            if device_id:
                logger.info(f"Processing time_of_day pattern with device_id: {device_id}")
                context = await _build_single_device_context(device_id)
            else:
                context = {}
        
        elif pattern_type == 'co_occurrence':
            device1 = pattern_dict.get('device1')
            device2 = pattern_dict.get('device2')
            context = await _build_co_occurrence_context(device1, device2)
        
        else:
            logger.warning(f"Unknown pattern type: {pattern_type}")
            context = {}

        logger.debug(f"Built device context: {context}")
        return context

    except Exception as e:
        logger.warning(f"Failed to build device context: {e}")
        # Return empty context on error - OpenAI will use entity IDs as fallback
        return {}


async def _validate_pattern_feasibility(pattern_dict: dict[str, Any], device_context: dict[str, Any]) -> 'ValidationResult':
    """
    Validate that a pattern can be implemented with available devices.
    
    Args:
        pattern_dict: Pattern data with device IDs and metadata
        device_context: Device metadata with friendly names
    
    Returns:
        ValidationResult indicating if pattern is feasible
    """
    try:
        # Extract entities and trigger conditions from pattern
        suggested_entities = []
        trigger_conditions = []

        pattern_type = pattern_dict.get('pattern_type')

        if pattern_type == 'time_of_day':
            # Time-based patterns don't need sensor validation
            device_id = pattern_dict.get('device_id')
            if device_id:
                suggested_entities.append(device_id)
            return ValidationResult(
                is_valid=True,
                missing_devices=[],
                missing_entities=[],
                missing_sensors=[],
                available_alternatives={}
            )

        elif pattern_type == 'co_occurrence':
            # Co-occurrence patterns need both devices to exist
            device1 = pattern_dict.get('device1')
            device2 = pattern_dict.get('device2')
            if device1:
                suggested_entities.append(device1)
            if device2:
                suggested_entities.append(device2)

        # For now, assume time-based and co-occurrence patterns are valid
        # Future: Add more sophisticated validation for complex trigger conditions
        return ValidationResult(
            is_valid=True,
            missing_devices=[],
            missing_entities=[],
            missing_sensors=[],
            available_alternatives={}
        )

    except Exception as e:
        logger.error(f"Pattern validation failed: {e}")
        return ValidationResult(
            is_valid=False,
            missing_devices=[],
            missing_entities=[],
            missing_sensors=[],
            available_alternatives={},
            error_message=f"Validation error: {str(e)}"
        )


async def _generate_alternative_suggestion(
    pattern_dict: dict[str, Any],
    device_context: dict[str, Any],
    validation_result: 'ValidationResult'
) -> dict[str, Any]:
    """
    Generate an alternative suggestion using available devices.
    
    Args:
        pattern_dict: Original pattern data
        device_context: Device metadata
        validation_result: Validation result with alternatives
    
    Returns:
        Alternative suggestion data
    """
    try:
        # For now, generate a simple fallback suggestion
        # Future: Use alternatives to create more sophisticated suggestions

        pattern_type = pattern_dict.get('pattern_type', 'unknown')
        device_id = pattern_dict.get('device_id', 'unknown')
        device_name = device_context.get('name', device_id) if device_context else device_id

        if pattern_type == 'time_of_day':
            hour = pattern_dict.get('hour', 0)
            minute = pattern_dict.get('minute', 0)

            return {
                'title': f"Alternative: {device_name} at {hour:02d}:{minute:02d}",
                'description': f"Automatically control {device_name} at {hour:02d}:{minute:02d} based on your usage pattern. This uses only devices that are confirmed to exist in your system.",
                'category': 'convenience',
                'priority': 'medium',
                'confidence': pattern_dict.get('confidence', 0.5)
            }

        else:
            # Generic fallback
            return {
                'title': f"Alternative: {device_name} automation",
                'description': f"An automation for {device_name} using only available devices in your system.",
                'category': 'convenience',
                'priority': 'low',
                'confidence': pattern_dict.get('confidence', 0.3)
            }

    except Exception as e:
        logger.error(f"Failed to generate alternative suggestion: {e}")
        # Return minimal fallback
        return {
            'title': "Alternative automation suggestion",
            'description': "An automation using only available devices in your system.",
            'category': 'convenience',
            'priority': 'low',
            'confidence': 0.1
        }

