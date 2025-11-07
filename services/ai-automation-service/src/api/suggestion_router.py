"""
Suggestion Generation Router

Endpoints for generating automation suggestions from detected patterns using LLM.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
import logging
import time

from ..llm.openai_client import OpenAIClient
from ..database import (
    get_db,
    get_patterns,
    store_suggestion,
    get_suggestions,
    can_trigger_manual_refresh,
    record_manual_refresh,
)
from ..config import settings
from ..clients.data_api_client import DataAPIClient
from ..validation.device_validator import DeviceValidator, ValidationResult
from ..prompt_building.unified_prompt_builder import UnifiedPromptBuilder

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/suggestions", tags=["Suggestions"])

# Initialize OpenAI client
openai_client = OpenAIClient(api_key=settings.openai_api_key, model="gpt-4o-mini")

# Initialize Unified Prompt Builder
prompt_builder = UnifiedPromptBuilder()

# Initialize Data API client for fetching device metadata
data_api_client = DataAPIClient(base_url="http://data-api:8006")

# Initialize Device Validator for validating suggestions
device_validator = DeviceValidator(data_api_client)


@router.get("/refresh/status")
async def refresh_status(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Return the current manual refresh status and cooldown timer.
    """
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


@router.post("/refresh", status_code=status.HTTP_202_ACCEPTED)
async def refresh_suggestions(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
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
    pattern_type: Optional[str] = Query(default=None, description="Generate suggestions for specific pattern type"),
    min_confidence: float = Query(default=0.7, ge=0.0, le=1.0, description="Minimum pattern confidence"),
    max_suggestions: int = Query(default=10, ge=1, le=50, description="Maximum suggestions to generate"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
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
            from ..clients.data_api_client import DataAPIClient
            
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
                        suggestion_data = {
                            'pattern_id': None,  # Predictive suggestions don't have patterns
                            'title': pred_sugg.get('title', 'Predictive Automation'),
                            'description': pred_sugg.get('description', ''),
                            'automation_yaml': None,
                            'confidence': pred_sugg.get('confidence', 0.8),
                            'category': pred_sugg.get('type', 'convenience'),
                            'priority': pred_sugg.get('priority', 'medium')
                        }
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
                        cascade_data = {
                            'pattern_id': pattern.id,
                            'title': cascade_sugg.get('title', ''),
                            'description': cascade_sugg.get('description', ''),
                            'automation_yaml': None,
                            'confidence': cascade_sugg.get('confidence', 0.8),
                            'category': 'convenience',
                            'priority': cascade_sugg.get('complexity', 'medium')
                        }
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
                    result = await openai_client.generate_with_unified_prompt(
                        prompt_dict=prompt_dict,
                        temperature=0.7,
                        max_tokens=300,
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
                
                # Store in database
                suggestion_data = {
                    'pattern_id': pattern.id,
                    'title': description_data['title'],
                    'description': description_data['description'],
                    'automation_yaml': None,  # Story AI1.24: No YAML until approved
                    'confidence': pattern.confidence,
                    'category': description_data['category'],
                    'priority': description_data['priority']
                }
                
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
    status_filter: Optional[str] = Query(default=None, description="Filter by status (pending, approved, deployed, rejected)"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum suggestions to return"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    List automation suggestions with optional filters.
    """
    try:
        suggestions = await get_suggestions(db, status=status_filter, limit=limit)
        
        # Convert to dictionaries
        suggestions_list = [
            {
                "id": s.id,
                "pattern_id": s.pattern_id,
                "title": s.title,
                "description": s.description_only,  # Fixed: use description_only field
                "automation_yaml": s.automation_yaml,
                "status": s.status,
                "confidence": s.confidence,
                "category": s.category,
                "priority": s.priority,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "deployed_at": s.deployed_at.isoformat() if s.deployed_at else None
            }
            for s in suggestions
        ]
        
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list suggestions: {str(e)}"
        )


@router.get("/usage-stats")
async def get_usage_stats() -> Dict[str, Any]:
    """
    Get OpenAI API usage statistics and cost estimates.
    """
    try:
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
async def reset_usage_stats() -> Dict[str, Any]:
    """
    Reset OpenAI API usage statistics (for monthly reset).
    """
    try:
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

async def _build_device_context(pattern_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build device context with friendly names for OpenAI prompts.
    
    Args:
        pattern_dict: Pattern dictionary containing device_id(s)
    
    Returns:
        Dictionary with friendly names and device metadata
    """
    context = {}
    
    try:
        logger.info(f"Building device context for pattern: {pattern_dict}")
        pattern_type = pattern_dict.get('pattern_type')
        
        # For time_of_day patterns: single device
        if pattern_type == 'time_of_day':
            device_id = pattern_dict.get('device_id')
            if device_id:
                logger.info(f"Processing time_of_day pattern with device_id: {device_id}")
                # Check if device_id looks like a device ID (long hex string) or entity ID (domain.entity_name)
                if '.' not in device_id and len(device_id) > 20:
                    # This is a device ID, get device metadata directly
                    logger.info(f"Treating {device_id} as device ID")
                    try:
                        device_metadata = await data_api_client.get_device_metadata(device_id)
                        if device_metadata:
                            logger.info(f"Got device metadata: {device_metadata}")
                            # Safely access device_metadata
                            if isinstance(device_metadata, dict):
                                metadata = {
                                    'friendly_name': device_metadata.get('name', ''),
                                    'area_name': device_metadata.get('area_id', '')
                                }
                                friendly_name = device_metadata.get('name', device_id)
                            else:
                                logger.warning(f"Device metadata is not a dict: {type(device_metadata)}")
                                friendly_name = device_id
                                metadata = None
                            domain = 'device'  # Generic domain for device-level patterns
                        else:
                            friendly_name = device_id
                            metadata = None
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
                
                context = {
                    'device_id': device_id,
                    'name': friendly_name,
                    'domain': domain
                }
                
                # Add extra metadata if available
                if metadata:
                    context['device_class'] = metadata.get('device_class')
                    context['area'] = metadata.get('area_name')
        
        # For co_occurrence patterns: two devices
        elif pattern_type == 'co_occurrence':
            device1 = pattern_dict.get('device1')
            device2 = pattern_dict.get('device2')
            
            if device1:
                # Check if device1 looks like a device ID (long hex string) or entity ID
                if '.' not in device1 and len(device1) > 20:
                    # This is a device ID, get device metadata directly
                    device_metadata1 = await data_api_client.get_device_metadata(device1)
                    if device_metadata1:
                        friendly1 = device_metadata1.get('name', device1)
                        domain1 = 'device'
                    else:
                        friendly1 = device1
                        domain1 = 'unknown'
                else:
                    # This is an entity ID
                    metadata1 = await data_api_client.get_entity_metadata(device1)
                    if not metadata1:
                        # Try to get device metadata using device_id from entity
                        try:
                            entities = await data_api_client.fetch_entities(limit=1000)
                            for entity in entities:
                                if entity.get('entity_id') == device1:
                                    device_metadata = await data_api_client.get_device_metadata(entity.get('device_id'))
                                    if device_metadata:
                                        metadata1 = {
                                            'friendly_name': device_metadata.get('name', ''),
                                            'area_name': device_metadata.get('area_id', '')
                                        }
                                    break
                        except Exception as e:
                            logger.warning(f"Failed to fetch device metadata for {device1}: {e}")
                    
                    friendly1 = data_api_client.extract_friendly_name(device1, metadata1)
                    domain1 = device1.split('.')[0] if '.' in device1 else 'unknown'
                
                context['device1'] = {
                    'entity_id': device1,
                    'name': friendly1,
                    'domain': domain1
                }
            
            if device2:
                # Check if device2 looks like a device ID (long hex string) or entity ID
                if '.' not in device2 and len(device2) > 20:
                    # This is a device ID, get device metadata directly
                    device_metadata2 = await data_api_client.get_device_metadata(device2)
                    if device_metadata2:
                        friendly2 = device_metadata2.get('name', device2)
                        domain2 = 'device'
                    else:
                        friendly2 = device2
                        domain2 = 'unknown'
                else:
                    # This is an entity ID
                    metadata2 = await data_api_client.get_entity_metadata(device2)
                    if not metadata2:
                        # Try to get device metadata using device_id from entity
                        try:
                            entities = await data_api_client.fetch_entities(limit=1000)
                            for entity in entities:
                                if entity.get('entity_id') == device2:
                                    device_metadata = await data_api_client.get_device_metadata(entity.get('device_id'))
                                    if device_metadata:
                                        metadata2 = {
                                            'friendly_name': device_metadata.get('name', ''),
                                            'area_name': device_metadata.get('area_id', '')
                                        }
                                    break
                        except Exception as e:
                            logger.warning(f"Failed to fetch device metadata for {device2}: {e}")
                    
                    friendly2 = data_api_client.extract_friendly_name(device2, metadata2)
                    domain2 = device2.split('.')[0] if '.' in device2 else 'unknown'
                
                context['device2'] = {
                    'entity_id': device2,
                    'name': friendly2,
                    'domain': domain2
                }
        
        logger.debug(f"Built device context: {context}")
        return context
        
    except Exception as e:
        logger.warning(f"Failed to build device context: {e}")
        # Return empty context on error - OpenAI will use entity IDs as fallback
        return {}


async def _validate_pattern_feasibility(pattern_dict: Dict[str, Any], device_context: Dict[str, Any]) -> 'ValidationResult':
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
    pattern_dict: Dict[str, Any], 
    device_context: Dict[str, Any], 
    validation_result: 'ValidationResult'
) -> Dict[str, Any]:
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

