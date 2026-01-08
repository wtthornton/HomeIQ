"""
Synergy Router - API endpoints for synergy opportunities

Epic 39: Pattern Service API endpoints
Priority 2.3: Create Missing API Routers (from improvement plan)

Provides REST API for querying synergy opportunities from the database.
Enables frontend integration and user feedback collection for RL optimization.
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.data_api_client import DataAPIClient
from ..crud.synergies import get_synergy_opportunities
from ..database import get_db
from ..services.device_activity import DeviceActivityService
from ..services.automation_generator import AutomationGenerator
from ..services.automation_tracker import AutomationTracker
from ..config import settings

# Blueprint Opportunity Engine imports (Phase 2)
try:
    from ..blueprint_opportunity.opportunity_engine import BlueprintOpportunityEngine
    from ..blueprint_opportunity.schemas import BlueprintOpportunity, DeviceSignature
    BLUEPRINT_ENGINE_AVAILABLE = True
except (ImportError, Exception) as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Blueprint Opportunity Engine not available: {e}")
    BLUEPRINT_ENGINE_AVAILABLE = False

# 2025 Enhancement: XAI for explanations
try:
    from ..synergy_detection.explainable_synergy import ExplainableSynergyGenerator
    XAI_AVAILABLE = True
except ImportError:
    XAI_AVAILABLE = False

logger = logging.getLogger(__name__)

# Create a separate router for specific routes that must be matched before parameterized routes
# This ensures /stats and /list are matched before /{synergy_id}
# FastAPI matches routes in the order they're registered via include_router
specific_router = APIRouter(prefix="/api/v1/synergies", tags=["synergies"])

# Main router for parameterized routes (must be registered AFTER specific_router)
router = APIRouter(prefix="/api/v1/synergies", tags=["synergies"])


class SynergyFeedback(BaseModel):
    """Feedback model for synergy opportunities."""
    accepted: bool
    feedback_text: str | None = None
    rating: int | None = None  # 1-5 rating


class AutomationExecutionResult(BaseModel):
    """Execution result model for automation tracking."""
    success: bool
    error: str | None = None
    execution_time_ms: int = 0
    triggered_count: int = 0


# CRITICAL: Define /statistics route on router FIRST (before parameterized routes)
# Using /statistics instead of /stats to avoid conflict with parameterized /{synergy_id} route
# FastAPI matches routes in the order they're defined within a router
# This route MUST be defined before /{synergy_id} to ensure correct matching
@router.get("/statistics")
async def get_synergy_stats(
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get synergy statistics.
    
    Returns summary statistics about detected synergy opportunities.
    
    IMPORTANT: This route must be defined BEFORE the parameterized /{synergy_id} route
    on the same router to ensure FastAPI matches /stats correctly.
    
    Args:
        db: Database session dependency
        
    Returns:
        dict: Synergy statistics including counts by type, average scores, etc.
        
    Raises:
        HTTPException: If database query fails (500 status)
    """
    logger.info("✅ /statistics route handler called")
    try:
        # Get all synergies for stats
        synergies = await get_synergy_opportunities(db, limit=10000)
        
        total_synergies = len(synergies)
        by_type = {}
        by_complexity = {}
        total_confidence = 0.0
        total_impact = 0.0
        areas = set()
        
        for s in synergies:
            # Handle both dict and SynergyOpportunity object
            if isinstance(s, dict):
                synergy_type = s.get("synergy_type", "unknown")
                complexity = s.get("complexity", "medium")
                confidence = s.get("confidence", 0.0)
                impact = s.get("impact_score", 0.0)
                area = s.get("area")
            else:
                synergy_type = s.synergy_type
                complexity = s.complexity or "medium"
                confidence = float(s.confidence) if s.confidence is not None else 0.0
                impact = float(s.impact_score) if s.impact_score is not None else 0.0
                area = s.area
            
            # Count by type
            by_type[synergy_type] = by_type.get(synergy_type, 0) + 1
            
            # Count by complexity (low, medium, high)
            by_complexity[complexity] = by_complexity.get(complexity, 0) + 1
            
            total_confidence += confidence
            total_impact += impact
            if area:
                areas.add(area)
        
        avg_confidence = total_confidence / total_synergies if total_synergies > 0 else 0.0
        avg_impact = total_impact / total_synergies if total_synergies > 0 else 0.0
        
        return {
            "success": True,
            "data": {
                "total_synergies": total_synergies,
                "by_type": by_type,
                "by_complexity": by_complexity,
                "avg_impact_score": round(avg_impact, 3),
                "avg_confidence": round(avg_confidence, 3),
                "unique_areas": len(areas)
            },
            "message": "Synergy statistics retrieved successfully"
        }
    
    except Exception as e:
        logger.error(f"Failed to get synergy stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get synergy stats: {str(e)}"
        ) from e


@specific_router.get("/list")
async def list_synergies(
    synergy_type: str | None = Query(default=None, description="Filter by synergy type (e.g., 'device_pair', 'device_chain')"),
    min_confidence: float = Query(default=0.5, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    synergy_depth: int | None = Query(default=None, ge=2, le=4, description="Filter by synergy depth (2=pair, 3=chain, 4=4-chain)"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum synergies to return"),
    order_by_priority: bool = Query(default=True, description="Order by priority score (impact + confidence)"),
    include_inactive: bool = Query(default=False, description="Include synergies for inactive devices"),
    activity_window_days: int = Query(default=30, ge=1, le=365, description="Activity window in days"),
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    List synergy opportunities with optional filters.
    
    Returns synergies with safely parsed metadata and opportunity details.
    Optionally filters by device activity (default: only active devices).
    
    Args:
        synergy_type: Optional filter by synergy type
        min_confidence: Minimum confidence threshold (0.0-1.0)
        synergy_depth: Optional filter by synergy depth (2, 3, or 4)
        limit: Maximum number of synergies to return
        order_by_priority: If True, order by priority score (impact + confidence)
        include_inactive: If True, include synergies for inactive devices
        activity_window_days: Activity window in days (default: 30)
        db: Database session dependency
        
    Returns:
        dict: Response with synergies list and count
        
    Raises:
        HTTPException: If database query fails (500 status)
    """
    try:
        synergies = await get_synergy_opportunities(
            db,
            synergy_type=synergy_type,
            min_confidence=min_confidence,
            synergy_depth=synergy_depth,
            limit=limit,
            order_by_priority=order_by_priority
        )
        
        # Filter by device activity if requested
        if not include_inactive:
            try:
                async with DataAPIClient(base_url=settings.data_api_url) as data_client:
                    activity_service = DeviceActivityService(data_api_client=data_client)
                    active_devices = await activity_service.get_active_devices(
                        window_days=activity_window_days,
                        data_api_client=data_client
                    )
                    
                    if active_devices:
                        # Convert synergies to dict format for filtering (before JSON parsing)
                        synergies_dict = []
                        for s in synergies:
                            if isinstance(s, dict):
                                synergies_dict.append(s)
                            else:
                                synergies_dict.append({
                                    "id": s.id,
                                    "synergy_id": s.synergy_id,
                                    "synergy_type": s.synergy_type,
                                    "device_ids": s.device_ids if hasattr(s, 'device_ids') else None,
                                    "entities": getattr(s, 'entities', None),
                                })
                        
                        # Filter synergies by activity
                        filtered_synergies = activity_service.filter_synergies_by_activity(
                            synergies_dict,
                            active_devices
                        )
                        
                        # Convert back to original format (keep original objects if possible)
                        active_synergy_ids = {s.get("id") if isinstance(s, dict) else s.id for s in filtered_synergies}
                        synergies = [s for s in synergies if (s.id if hasattr(s, 'id') else s.get("id")) in active_synergy_ids]
                        
                        logger.info(
                            f"Filtered synergies by activity: {len(synergies_dict)} → {len(filtered_synergies)} "
                            f"(window: {activity_window_days} days)"
                        )
                    else:
                        logger.warning("No active devices found, returning all synergies")
            except Exception as e:
                logger.warning(f"Failed to filter synergies by activity: {e}, returning all synergies")
                # Continue with all synergies if filtering fails

        # Convert to dictionaries with safe JSON parsing
        synergies_list = []
        for s in synergies:
            # Handle both SynergyOpportunity objects and dicts (from raw SQL)
            if isinstance(s, dict):
                synergy_dict = s.copy()
                metadata = synergy_dict.get("opportunity_metadata")
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse opportunity_metadata for synergy {synergy_dict.get('id')}: {e}")
                        metadata = {}
                elif metadata is None:
                    metadata = {}
                
                device_ids = synergy_dict.get("device_ids")
                if isinstance(device_ids, str):
                    try:
                        device_ids = json.loads(device_ids)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse device_ids for synergy {synergy_dict.get('id')}: {e}")
                        device_ids = []
                elif device_ids is None:
                    device_ids = []
                
                chain_devices = synergy_dict.get("chain_devices")
                if isinstance(chain_devices, str):
                    try:
                        chain_devices = json.loads(chain_devices)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse chain_devices for synergy {synergy_dict.get('id')}: {e}")
                        chain_devices = None
                elif chain_devices is None:
                    chain_devices = None
                
                # Extract explanation and context_breakdown from metadata (2025 Enhancement)
                explanation = metadata.get('explanation')
                context_breakdown = metadata.get('context_breakdown')
                context_metadata = metadata.get('context_metadata')
                
                # Generate explanation on-the-fly if not stored and XAI available
                if not explanation and XAI_AVAILABLE:
                    try:
                        explainer = ExplainableSynergyGenerator()
                        synergy_for_explanation = {
                            'synergy_id': synergy_dict.get("synergy_id"),
                            'relationship_type': metadata.get('relationship', ''),
                            'trigger_entity': metadata.get('trigger_entity'),
                            'trigger_name': metadata.get('trigger_name'),
                            'action_entity': metadata.get('action_entity'),
                            'action_name': metadata.get('action_name'),
                            'area': synergy_dict.get("area"),
                            'impact_score': synergy_dict.get("impact_score", 0.0),
                            'confidence': synergy_dict.get("confidence", 0.0),
                            'complexity': synergy_dict.get("complexity", "medium"),
                            'opportunity_metadata': metadata
                        }
                        explanation = explainer.generate_explanation(synergy_for_explanation, context_metadata)
                    except Exception as e:
                        logger.warning(f"Failed to generate explanation for synergy {synergy_dict.get('synergy_id')}: {e}")
                
                # Phase 4: Extract blueprint metadata from opportunity_metadata
                blueprint_info = metadata.get('blueprint', {}) if metadata else {}
                
                synergies_list.append({
                    "id": synergy_dict.get("id"),
                    "synergy_id": synergy_dict.get("synergy_id"),
                    "synergy_type": synergy_dict.get("synergy_type"),
                    "devices": device_ids,
                    "chain_devices": chain_devices,
                    "metadata": metadata,
                    "impact_score": synergy_dict.get("impact_score", 0.0),
                    "confidence": synergy_dict.get("confidence", 0.0),
                    "complexity": synergy_dict.get("complexity", "medium"),
                    "area": synergy_dict.get("area"),
                    "synergy_depth": synergy_dict.get("synergy_depth", 2),
                    "explanation": explanation,  # 2025 Enhancement: XAI explanation
                    "context_breakdown": context_breakdown,  # 2025 Enhancement: Multi-modal context
                    # Phase 4: Blueprint metadata
                    "blueprint_id": synergy_dict.get("blueprint_id") or blueprint_info.get('id'),
                    "blueprint_name": synergy_dict.get("blueprint_name") or blueprint_info.get('name'),
                    "blueprint_fit_score": synergy_dict.get("blueprint_fit_score") or blueprint_info.get('fit_score'),
                    "has_blueprint_match": bool(synergy_dict.get("blueprint_id") or blueprint_info.get('id')),
                    "created_at": synergy_dict.get("created_at"),
                    "updated_at": synergy_dict.get("updated_at")
                })
            else:
                # SynergyOpportunity object, access attributes
                metadata = s.opportunity_metadata
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse opportunity_metadata for synergy {s.id}: {e}")
                        metadata = {}
                elif not isinstance(metadata, dict) and metadata is not None:
                    logger.warning(f"Unexpected opportunity_metadata type for synergy {s.id}: {type(metadata)}")
                    metadata = {}
                elif metadata is None:
                    metadata = {}
                
                device_ids = s.device_ids
                if isinstance(device_ids, str):
                    try:
                        device_ids = json.loads(device_ids)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse device_ids for synergy {s.id}: {e}")
                        device_ids = []
                elif device_ids is None:
                    device_ids = []
                
                chain_devices = getattr(s, 'chain_devices', None)
                if isinstance(chain_devices, str):
                    try:
                        chain_devices = json.loads(chain_devices)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse chain_devices for synergy {s.id}: {e}")
                        chain_devices = None
                elif chain_devices is None:
                    chain_devices = None
                
                # Extract explanation and context_breakdown from metadata (2025 Enhancement)
                explanation = metadata.get('explanation')
                context_breakdown = metadata.get('context_breakdown')
                context_metadata = metadata.get('context_metadata')
                
                # Generate explanation on-the-fly if not stored and XAI available
                if not explanation and XAI_AVAILABLE:
                    try:
                        explainer = ExplainableSynergyGenerator()
                        synergy_for_explanation = {
                            'synergy_id': s.synergy_id,
                            'relationship_type': metadata.get('relationship', ''),
                            'trigger_entity': metadata.get('trigger_entity'),
                            'trigger_name': metadata.get('trigger_name'),
                            'action_entity': metadata.get('action_entity'),
                            'action_name': metadata.get('action_name'),
                            'area': s.area,
                            'impact_score': float(s.impact_score) if s.impact_score is not None else 0.0,
                            'confidence': float(s.confidence) if s.confidence is not None else 0.0,
                            'complexity': s.complexity or "medium",
                            'opportunity_metadata': metadata
                        }
                        explanation = explainer.generate_explanation(synergy_for_explanation, context_metadata)
                    except Exception as e:
                        logger.warning(f"Failed to generate explanation for synergy {s.synergy_id}: {e}")
                
                # Phase 4: Extract blueprint metadata from opportunity_metadata
                blueprint_info = metadata.get('blueprint', {}) if metadata else {}
                
                synergies_list.append({
                    "id": s.id,
                    "synergy_id": s.synergy_id,
                    "synergy_type": s.synergy_type,
                    "devices": device_ids,
                    "chain_devices": chain_devices,
                    "metadata": metadata,
                    "impact_score": float(s.impact_score) if s.impact_score is not None else 0.0,
                    "confidence": float(s.confidence) if s.confidence is not None else 0.0,
                    "complexity": s.complexity or "medium",
                    "area": s.area,
                    "synergy_depth": getattr(s, 'synergy_depth', 2),
                    "explanation": explanation,  # 2025 Enhancement: XAI explanation
                    "context_breakdown": context_breakdown,  # 2025 Enhancement: Multi-modal context
                    # Phase 4: Blueprint metadata
                    "blueprint_id": getattr(s, 'blueprint_id', None) or blueprint_info.get('id'),
                    "blueprint_name": getattr(s, 'blueprint_name', None) or blueprint_info.get('name'),
                    "blueprint_fit_score": getattr(s, 'blueprint_fit_score', None) or blueprint_info.get('fit_score'),
                    "has_blueprint_match": bool(getattr(s, 'blueprint_id', None) or blueprint_info.get('id')),
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "updated_at": s.updated_at.isoformat() if hasattr(s, 'updated_at') and s.updated_at else None
                })

        return {
            "success": True,
            "data": {
                "synergies": synergies_list,
                "count": len(synergies_list)
            },
            "message": f"Retrieved {len(synergies_list)} synergy opportunities"
        }

    except Exception as e:
        logger.error(f"Failed to list synergies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list synergies: {str(e)}"
        ) from e


@router.get("/{synergy_id}")
async def get_synergy(
    synergy_id: str,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get detailed synergy opportunity by synergy_id.
    
    Args:
        synergy_id: Unique synergy identifier
        db: Database session dependency
        
    Returns:
        dict: Synergy opportunity details
        
    Raises:
        HTTPException: If synergy not found (404) or query fails (500)
    
    Note:
        This route should NOT match 'stats' or 'list' as those are handled by
        specific routes. FastAPI should match specific routes first, but we
        add a guard here as a safety measure.
    """
    try:
        # Get all synergies and filter by synergy_id
        synergies = await get_synergy_opportunities(db, limit=10000)
        
        synergy = None
        for s in synergies:
            if isinstance(s, dict):
                if s.get("synergy_id") == synergy_id:
                    synergy = s
                    break
            else:
                if s.synergy_id == synergy_id:
                    synergy = s
                    break
        
        if not synergy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Synergy opportunity not found: {synergy_id}"
            )
        
        # Convert to dict format (same logic as list endpoint)
        if isinstance(synergy, dict):
            synergy_dict = synergy.copy()
            metadata = synergy_dict.get("opportunity_metadata")
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except (json.JSONDecodeError, TypeError):
                    metadata = {}
            elif metadata is None:
                metadata = {}
            
            device_ids = synergy_dict.get("device_ids")
            if isinstance(device_ids, str):
                try:
                    device_ids = json.loads(device_ids)
                except (json.JSONDecodeError, TypeError):
                    device_ids = []
            elif device_ids is None:
                device_ids = []
            
            chain_devices = synergy_dict.get("chain_devices")
            if isinstance(chain_devices, str):
                try:
                    chain_devices = json.loads(chain_devices)
                except (json.JSONDecodeError, TypeError):
                    chain_devices = None
            elif chain_devices is None:
                chain_devices = None
            
            # Extract explanation and context_breakdown (2025 Enhancement)
            # Try to get from database columns first, then from metadata
            explanation = synergy_dict.get("explanation") or metadata.get('explanation')
            context_breakdown = synergy_dict.get("context_breakdown") or metadata.get('context_breakdown')
            
            # Parse JSON strings if needed
            if isinstance(explanation, str):
                try:
                    explanation = json.loads(explanation)
                except (json.JSONDecodeError, TypeError):
                    pass
            if isinstance(context_breakdown, str):
                try:
                    context_breakdown = json.loads(context_breakdown)
                except (json.JSONDecodeError, TypeError):
                    pass
            
            context_metadata = metadata.get('context_metadata')
            
            # Generate explanation on-the-fly if not stored and XAI available
            if not explanation and XAI_AVAILABLE:
                try:
                    explainer = ExplainableSynergyGenerator()
                    synergy_for_explanation = {
                        'synergy_id': synergy_dict.get("synergy_id"),
                        'relationship_type': metadata.get('relationship', ''),
                        'trigger_entity': metadata.get('trigger_entity'),
                        'trigger_name': metadata.get('trigger_name'),
                        'action_entity': metadata.get('action_entity'),
                        'action_name': metadata.get('action_name'),
                        'area': synergy_dict.get("area"),
                        'impact_score': synergy_dict.get("impact_score", 0.0),
                        'confidence': synergy_dict.get("confidence", 0.0),
                        'complexity': synergy_dict.get("complexity", "medium"),
                        'opportunity_metadata': metadata
                    }
                    explanation = explainer.generate_explanation(synergy_for_explanation, context_metadata)
                except Exception as e:
                    logger.warning(f"Failed to generate explanation for synergy {synergy_dict.get('synergy_id')}: {e}")
            
            synergy_data = {
                "id": synergy_dict.get("id"),
                "synergy_id": synergy_dict.get("synergy_id"),
                "synergy_type": synergy_dict.get("synergy_type"),
                "devices": device_ids,
                "chain_devices": chain_devices,
                "metadata": metadata,
                "impact_score": synergy_dict.get("impact_score", 0.0),
                "confidence": synergy_dict.get("confidence", 0.0),
                "complexity": synergy_dict.get("complexity", "medium"),
                "area": synergy_dict.get("area"),
                "synergy_depth": synergy_dict.get("synergy_depth", 2),
                "explanation": explanation,  # 2025 Enhancement: XAI explanation
                "context_breakdown": context_breakdown,  # 2025 Enhancement: Multi-modal context
                "created_at": synergy_dict.get("created_at"),
                "updated_at": synergy_dict.get("updated_at")
            }
        else:
            # SynergyOpportunity object
            metadata = synergy.opportunity_metadata
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except (json.JSONDecodeError, TypeError):
                    metadata = {}
            elif metadata is None:
                metadata = {}
            
            device_ids = synergy.device_ids
            if isinstance(device_ids, str):
                try:
                    device_ids = json.loads(device_ids)
                except (json.JSONDecodeError, TypeError):
                    device_ids = []
            elif device_ids is None:
                device_ids = []
            
            chain_devices = getattr(synergy, 'chain_devices', None)
            if isinstance(chain_devices, str):
                try:
                    chain_devices = json.loads(chain_devices)
                except (json.JSONDecodeError, TypeError):
                    chain_devices = None
            elif chain_devices is None:
                chain_devices = None
            
            # Extract explanation and context_breakdown (2025 Enhancement)
            # Try to get from database columns first, then from metadata
            explanation = getattr(synergy, 'explanation', None) or metadata.get('explanation')
            context_breakdown = getattr(synergy, 'context_breakdown', None) or metadata.get('context_breakdown')
            
            # Parse JSON strings if needed
            if isinstance(explanation, str):
                try:
                    explanation = json.loads(explanation)
                except (json.JSONDecodeError, TypeError):
                    pass
            if isinstance(context_breakdown, str):
                try:
                    context_breakdown = json.loads(context_breakdown)
                except (json.JSONDecodeError, TypeError):
                    pass
            
            context_metadata = metadata.get('context_metadata')
            
            # Generate explanation on-the-fly if not stored and XAI available
            if not explanation and XAI_AVAILABLE:
                try:
                    explainer = ExplainableSynergyGenerator()
                    synergy_for_explanation = {
                        'synergy_id': synergy.synergy_id,
                        'relationship_type': metadata.get('relationship', ''),
                        'trigger_entity': metadata.get('trigger_entity'),
                        'trigger_name': metadata.get('trigger_name'),
                        'action_entity': metadata.get('action_entity'),
                        'action_name': metadata.get('action_name'),
                        'area': synergy.area,
                        'impact_score': float(synergy.impact_score) if synergy.impact_score is not None else 0.0,
                        'confidence': float(synergy.confidence) if synergy.confidence is not None else 0.0,
                        'complexity': synergy.complexity or "medium",
                        'opportunity_metadata': metadata
                    }
                    explanation = explainer.generate_explanation(synergy_for_explanation, context_metadata)
                except Exception as e:
                    logger.warning(f"Failed to generate explanation for synergy {synergy.synergy_id}: {e}")
            
            synergy_data = {
                "id": synergy.id,
                "synergy_id": synergy.synergy_id,
                "synergy_type": synergy.synergy_type,
                "devices": device_ids,
                "chain_devices": chain_devices,
                "metadata": metadata,
                "impact_score": float(synergy.impact_score) if synergy.impact_score is not None else 0.0,
                "confidence": float(synergy.confidence) if synergy.confidence is not None else 0.0,
                "complexity": synergy.complexity or "medium",
                "area": synergy.area,
                "synergy_depth": getattr(synergy, 'synergy_depth', 2),
                "explanation": explanation,  # 2025 Enhancement: XAI explanation
                "context_breakdown": context_breakdown,  # 2025 Enhancement: Multi-modal context
                "created_at": synergy.created_at.isoformat() if synergy.created_at else None,
                "updated_at": synergy.updated_at.isoformat() if hasattr(synergy, 'updated_at') and synergy.updated_at else None
            }
        
        return {
            "success": True,
            "data": synergy_data,
            "message": "Synergy opportunity retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get synergy {synergy_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get synergy: {str(e)}"
        ) from e


@router.post("/{synergy_id}/feedback")
async def submit_synergy_feedback(
    synergy_id: str,
    feedback: SynergyFeedback,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Submit user feedback for a synergy opportunity.
    
    This endpoint enables the Reinforcement Learning feedback loop (Priority 2.4).
    Feedback is stored for future RL optimization of synergy scoring.
    
    Args:
        synergy_id: Unique synergy identifier
        feedback: Feedback data (accepted, feedback_text, rating)
        db: Database session dependency
        
    Returns:
        dict: Confirmation of feedback submission
        
    Raises:
        HTTPException: If synergy not found (404) or storage fails (500)
    
    Note:
        Currently stores feedback in a simple format. Full RL integration
        will be implemented in Priority 2.4 (RL feedback loop).
    """
    try:
        # Verify synergy exists
        synergies = await get_synergy_opportunities(db, limit=10000)
        synergy_found = False
        for s in synergies:
            if isinstance(s, dict):
                if s.get("synergy_id") == synergy_id:
                    synergy_found = True
                    break
            else:
                if s.synergy_id == synergy_id:
                    synergy_found = True
                    break
        
        if not synergy_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Synergy opportunity not found: {synergy_id}"
            )
        
        # Store feedback in database and update RL optimizer (Phase 4.1 - RL feedback loop)
        feedback_data = {
            'accepted': feedback.accepted,
            'rating': feedback.rating,
            'feedback_text': feedback.feedback_text
        }
        
        # Store in database
        try:
            from sqlalchemy import text
            
            # Try to insert feedback (table created via migration script)
            insert_feedback_query = text("""
                INSERT INTO synergy_feedback 
                (synergy_id, feedback_type, feedback_data, created_at)
                VALUES (:synergy_id, :feedback_type, :feedback_data, datetime('now'))
            """)
            
            feedback_type = 'accept' if feedback.accepted else 'reject'
            if feedback.rating:
                feedback_type = 'rate'
            
            await db.execute(
                insert_feedback_query,
                {
                    "synergy_id": synergy_id,
                    "feedback_type": feedback_type,
                    "feedback_data": json.dumps(feedback_data)
                }
            )
            await db.commit()
            
            logger.info(
                f"Synergy feedback stored: synergy_id={synergy_id}, "
                f"type={feedback_type}, rating={feedback.rating}"
            )
        except Exception as e:
            # Table may not exist yet - log and continue
            logger.warning(
                f"Failed to store feedback in database (table may not exist yet): {e}. "
                f"Run migration script: python scripts/add_2025_synergy_fields.py"
            )
        
        # Update RL optimizer if available (2025 Enhancement)
        try:
            from ..synergy_detection.rl_synergy_optimizer import RLSynergyOptimizer
            # Note: In production, RL optimizer should be a singleton or injected dependency
            # For now, create instance (will be initialized per request - can be optimized later)
            rl_optimizer = RLSynergyOptimizer()
            await rl_optimizer.update_from_feedback(synergy_id, feedback_data)
            logger.info(f"RL optimizer updated with feedback for synergy {synergy_id}")
        except ImportError:
            logger.debug("RLSynergyOptimizer not available (numpy may be missing)")
        except Exception as e:
            logger.warning(f"Failed to update RL optimizer: {e}")
        
        return {
            "success": True,
            "data": {
                "synergy_id": synergy_id,
                "feedback_received": True,
                "accepted": feedback.accepted,
                "rating": feedback.rating,
                "rl_updated": True
            },
            "message": "Feedback received and RL optimizer updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit feedback for synergy {synergy_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        ) from e


@router.post("/{synergy_id}/generate-automation")
async def generate_automation_from_synergy(
    synergy_id: str,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Generate and deploy Home Assistant automation from synergy.
    
    This endpoint implements Recommendation 1.1: Complete Automation Generation Pipeline.
    Converts synergy to Home Assistant automation using 2025 best practices.
    
    Args:
        synergy_id: Unique synergy identifier
        db: Database session dependency
        
    Returns:
        {
            'automation_id': str,
            'automation_yaml': str,
            'blueprint_id': str | None,
            'deployment_status': str,
            'estimated_impact': float
        }
        
    Raises:
        HTTPException: If synergy not found (404), HA config missing (400), or deployment fails (500)
    """
    try:
        # Verify synergy exists
        synergies = await get_synergy_opportunities(db, limit=10000)
        synergy_data = None
        for s in synergies:
            if isinstance(s, dict):
                if s.get("synergy_id") == synergy_id:
                    # Extract devices and trigger/action from opportunity_metadata if not at top level
                    synergy_data = s.copy()
                    
                    # Parse opportunity_metadata if it's a string
                    opp_meta = synergy_data.get("opportunity_metadata")
                    if isinstance(opp_meta, str):
                        try:
                            opp_meta = json.loads(opp_meta)
                        except (json.JSONDecodeError, TypeError):
                            opp_meta = {}
                    elif opp_meta is None:
                        opp_meta = {}
                    
                    # Extract devices from device_ids string or opportunity_metadata
                    if "devices" not in synergy_data or not synergy_data["devices"]:
                        device_ids = synergy_data.get("device_ids", "")
                        if isinstance(device_ids, str) and device_ids:
                            synergy_data["devices"] = device_ids.split(",")
                        elif "devices" in opp_meta:
                            synergy_data["devices"] = opp_meta["devices"]
                        else:
                            synergy_data["devices"] = []
                    
                    # Extract trigger_entity and action_entity from opportunity_metadata
                    if "trigger_entity" not in synergy_data or not synergy_data.get("trigger_entity"):
                        synergy_data["trigger_entity"] = opp_meta.get("trigger_entity")
                    if "action_entity" not in synergy_data or not synergy_data.get("action_entity"):
                        synergy_data["action_entity"] = opp_meta.get("action_entity")
                    
                    # Parse context_breakdown if it's a string
                    ctx = synergy_data.get("context_breakdown")
                    if isinstance(ctx, str):
                        try:
                            synergy_data["context_breakdown"] = json.loads(ctx)
                        except (json.JSONDecodeError, TypeError):
                            synergy_data["context_breakdown"] = None
                    
                    break
            else:
                if s.synergy_id == synergy_id:
                    # Convert to dict if needed
                    device_ids = getattr(s, 'device_ids', None)
                    devices = device_ids.split(",") if device_ids and isinstance(device_ids, str) else []
                    
                    context_breakdown = None
                    if hasattr(s, 'context_breakdown') and s.context_breakdown:
                        if isinstance(s.context_breakdown, str):
                            try:
                                context_breakdown = json.loads(s.context_breakdown)
                            except (json.JSONDecodeError, TypeError):
                                context_breakdown = None
                        else:
                            context_breakdown = s.context_breakdown
                    
                    synergy_data = {
                        "synergy_id": s.synergy_id,
                        "synergy_type": s.synergy_type,
                        "devices": devices,
                        "trigger_entity": getattr(s, 'trigger_entity', None),
                        "action_entity": getattr(s, 'action_entity', None),
                        "area": s.area,
                        "impact_score": s.impact_score,
                        "confidence": s.confidence,
                        "rationale": getattr(s, 'rationale', ''),
                        "context_breakdown": context_breakdown
                    }
                    break
        
        if not synergy_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Synergy opportunity not found: {synergy_id}"
            )
        
        # Check Home Assistant configuration
        if not settings.ha_url or not settings.ha_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Home Assistant configuration missing. Set HA_URL and HA_TOKEN environment variables."
            )
        
        # Initialize automation generator
        generator = AutomationGenerator(
            ha_url=settings.ha_url,
            ha_token=settings.ha_token,
            ha_version=settings.ha_version
        )
        
        # Create HTTP client for Home Assistant API
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as ha_client:
            # Generate and deploy automation
            result = await generator.generate_automation_from_synergy(
                synergy=synergy_data,
                ha_client=ha_client,
                db=db
            )
        
        logger.info(
            f"✅ Automation generated from synergy {synergy_id}: "
            f"automation_id={result['automation_id']}"
        )
        
        return {
            "success": True,
            "data": result,
            "message": f"Automation {result['automation_id']} created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate automation from synergy {synergy_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate automation: {str(e)}"
        ) from e


@router.post("/{synergy_id}/track-execution")
async def track_automation_execution(
    synergy_id: str,
    automation_id: str,
    execution_result: AutomationExecutionResult,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Track automation execution and update synergy confidence.
    
    This endpoint implements Recommendation 2.2: Automation Execution Tracking.
    Tracks automation success/failure and updates synergy confidence based on outcomes.
    
    Args:
        synergy_id: Synergy ID that generated this automation
        automation_id: Home Assistant automation entity ID
        execution_result: Execution result with success, error, execution_time_ms, triggered_count
        db: Database session dependency
    
    Returns:
        {
            'success': bool,
            'message': str,
            'confidence_updated': bool,
            'new_confidence': float | None
        }
    
    Raises:
        HTTPException: If synergy not found (404) or tracking fails (500)
    """
    try:
        # Verify synergy exists
        synergies = await get_synergy_opportunities(db, limit=10000)
        synergy_found = False
        for s in synergies:
            if isinstance(s, dict):
                if s.get("synergy_id") == synergy_id:
                    synergy_found = True
                    break
            else:
                if s.synergy_id == synergy_id:
                    synergy_found = True
                    break
        
        if not synergy_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Synergy opportunity not found: {synergy_id}"
            )
        
        # Initialize automation tracker
        tracker = AutomationTracker(db=db)
        
        # Track execution
        await tracker.track_automation_execution(
            automation_id=automation_id,
            synergy_id=synergy_id,
            execution_result={
                'success': execution_result.success,
                'error': execution_result.error,
                'execution_time_ms': execution_result.execution_time_ms,
                'triggered_count': execution_result.triggered_count
            },
            db=db
        )
        
        # Get updated confidence
        from sqlalchemy import text
        result = await db.execute(
            text("""
                SELECT confidence FROM synergy_opportunities
                WHERE synergy_id = :synergy_id
            """),
            {"synergy_id": synergy_id}
        )
        row = result.fetchone()
        new_confidence = float(row[0]) if row and row[0] is not None else None
        
        logger.info(
            f"✅ Tracked automation execution: synergy_id={synergy_id}, "
            f"automation_id={automation_id}, success={execution_result.success}"
        )
        
        return {
            "success": True,
            "message": f"Automation execution tracked for synergy {synergy_id}",
            "confidence_updated": True,
            "new_confidence": new_confidence
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to track automation execution: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track automation execution: {str(e)}"
        ) from e


@router.get("/{synergy_id}/execution-stats")
async def get_automation_execution_stats(
    synergy_id: str,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get automation execution statistics for a synergy.
    
    This endpoint provides execution statistics for automations generated from a synergy.
    Implements Recommendation 2.2: Automation Execution Tracking.
    
    Args:
        synergy_id: Synergy ID to get stats for
        db: Database session dependency
    
    Returns:
        {
            'total_executions': int,
            'successful_executions': int,
            'failed_executions': int,
            'total_triggered': int,
            'avg_execution_time_ms': float,
            'success_rate': float
        }
    """
    try:
        # Initialize automation tracker
        tracker = AutomationTracker(db=db)
        
        # Get execution stats
        stats = await tracker.get_execution_stats(synergy_id, db=db)
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get execution stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution stats: {str(e)}"
        ) from e


# =============================================================================
# BLUEPRINT OPPORTUNITY ENDPOINTS (Phase 2 - Blueprint-First Architecture)
# =============================================================================

# Create a dedicated router for blueprint opportunities
blueprint_router = APIRouter(prefix="/api/v1/blueprint-opportunities", tags=["blueprint-opportunities"])


class BlueprintOpportunityRequest(BaseModel):
    """Request model for discovering blueprint opportunities."""
    device_inventory: list[dict[str, Any]] | None = None
    limit: int = 20
    min_fit_score: float = 0.5
    include_partial_matches: bool = True


class BlueprintDeployRequest(BaseModel):
    """Request model for deploying a blueprint."""
    blueprint_id: str
    input_values: dict[str, Any] | None = None
    automation_name: str | None = None
    description: str | None = None


@blueprint_router.get("/")
async def list_blueprint_opportunities(
    limit: int = Query(default=20, ge=1, le=100, description="Maximum opportunities to return"),
    min_fit_score: float = Query(default=0.5, ge=0.0, le=1.0, description="Minimum fit score threshold"),
    domain: str | None = Query(default=None, description="Filter by domain (e.g., 'light', 'climate')"),
    use_case: str | None = Query(default=None, description="Filter by use case (e.g., 'motion', 'presence')"),
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Discover blueprint opportunities based on device inventory.
    
    This endpoint implements Phase 2 of the Blueprint-First Architecture.
    It analyzes the user's Home Assistant device inventory and recommends
    blueprints that can be deployed with their existing devices.
    
    Args:
        limit: Maximum number of opportunities to return
        min_fit_score: Minimum fit score threshold (0.0-1.0)
        domain: Optional filter by domain
        use_case: Optional filter by use case
        db: Database session dependency
        
    Returns:
        dict: Blueprint opportunities with fit scores and auto-fill suggestions
        
    Raises:
        HTTPException: If blueprint engine unavailable (503) or query fails (500)
    """
    if not BLUEPRINT_ENGINE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blueprint Opportunity Engine not available. Check module installation."
        )
    
    try:
        # Initialize blueprint opportunity engine
        engine = BlueprintOpportunityEngine(
            blueprint_index_url=settings.blueprint_index_url or "http://blueprint-index:8031",
            data_api_url=settings.data_api_url
        )
        
        # Create discovery request
        from ..blueprint_opportunity.schemas import OpportunityDiscoveryRequest
        discovery_request = OpportunityDiscoveryRequest(
            min_fit_score=min_fit_score,
            limit=limit,
            use_cases=[use_case] if use_case else None
        )
        
        # Discover blueprint opportunities (engine handles device fetching internally)
        response = await engine.discover_opportunities(request=discovery_request)
        
        return {
            "success": True,
            "data": {
                "opportunities": [opp.model_dump() for opp in response.opportunities],
                "count": len(response.opportunities),
                "total_found": response.total_found,
                "device_count": response.device_count,
                "area_count": response.area_count,
                "discovery_time_ms": response.discovery_time_ms
            },
            "message": f"Found {response.total_found} blueprint opportunities"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to discover blueprint opportunities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover blueprint opportunities: {str(e)}"
        ) from e


@blueprint_router.post("/discover")
async def discover_blueprint_opportunities(
    request: BlueprintOpportunityRequest,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Discover blueprint opportunities with custom device inventory.
    
    This endpoint allows passing a custom device inventory for opportunity discovery.
    Useful for testing or when the device inventory differs from the live HA instance.
    
    Args:
        request: Request with device_inventory, limit, min_fit_score, include_partial_matches
        db: Database session dependency
        
    Returns:
        dict: Blueprint opportunities with fit scores and auto-fill suggestions
        
    Raises:
        HTTPException: If blueprint engine unavailable (503) or query fails (500)
    """
    if not BLUEPRINT_ENGINE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blueprint Opportunity Engine not available. Check module installation."
        )
    
    try:
        # Initialize blueprint opportunity engine
        engine = BlueprintOpportunityEngine(
            blueprint_index_url=settings.blueprint_index_url or "http://blueprint-index:8031"
        )
        
        # Use provided inventory or fetch from data-api
        device_inventory = request.device_inventory
        if device_inventory is None:
            try:
                async with DataAPIClient(base_url=settings.data_api_url) as data_client:
                    devices_response = await data_client.get("/api/devices")
                    if devices_response and "data" in devices_response:
                        device_inventory = devices_response["data"]
            except Exception as e:
                logger.warning(f"Failed to fetch device inventory: {e}")
                device_inventory = []
        
        # Discover opportunities
        opportunities = await engine.discover_opportunities(
            device_inventory=device_inventory,
            limit=request.limit,
            min_fit_score=request.min_fit_score,
            include_partial_matches=request.include_partial_matches
        )
        
        return {
            "success": True,
            "data": {
                "opportunities": [opp.model_dump() for opp in opportunities],
                "count": len(opportunities),
                "device_count": len(device_inventory) if device_inventory else 0
            },
            "message": f"Discovered {len(opportunities)} blueprint opportunities"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to discover blueprint opportunities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover blueprint opportunities: {str(e)}"
        ) from e


@blueprint_router.get("/{blueprint_id}")
async def get_blueprint_opportunity_details(
    blueprint_id: str,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get detailed information about a specific blueprint opportunity.
    
    This includes the full blueprint definition, input requirements,
    device compatibility analysis, and auto-fill suggestions.
    
    Args:
        blueprint_id: Unique blueprint identifier
        db: Database session dependency
        
    Returns:
        dict: Blueprint details with compatibility analysis
        
    Raises:
        HTTPException: If blueprint not found (404) or query fails (500)
    """
    if not BLUEPRINT_ENGINE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blueprint Opportunity Engine not available."
        )
    
    try:
        engine = BlueprintOpportunityEngine(
            blueprint_index_url=settings.blueprint_index_url or "http://blueprint-index:8031"
        )
        
        # Fetch device inventory
        device_inventory = []
        try:
            async with DataAPIClient(base_url=settings.data_api_url) as data_client:
                devices_response = await data_client.get("/api/devices")
                if devices_response and "data" in devices_response:
                    device_inventory = devices_response["data"]
        except Exception as e:
            logger.warning(f"Failed to fetch device inventory: {e}")
        
        # Get blueprint details with opportunity analysis
        opportunity = await engine.get_blueprint_opportunity(
            blueprint_id=blueprint_id,
            device_inventory=device_inventory
        )
        
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Blueprint not found: {blueprint_id}"
            )
        
        return {
            "success": True,
            "data": opportunity.model_dump(),
            "message": f"Blueprint opportunity details retrieved for {blueprint_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get blueprint opportunity details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get blueprint opportunity details: {str(e)}"
        ) from e


@blueprint_router.post("/{blueprint_id}/preview")
async def preview_blueprint_deployment(
    blueprint_id: str,
    request: BlueprintDeployRequest,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Preview what a blueprint deployment would look like.
    
    This generates a preview of the automation that would be created
    without actually deploying it to Home Assistant.
    
    Args:
        blueprint_id: Blueprint to preview
        request: Deployment configuration with input values
        db: Database session dependency
        
    Returns:
        dict: Preview of the automation YAML and configuration
        
    Raises:
        HTTPException: If blueprint not found (404) or preview fails (500)
    """
    if not BLUEPRINT_ENGINE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blueprint Opportunity Engine not available."
        )
    
    try:
        engine = BlueprintOpportunityEngine(
            blueprint_index_url=settings.blueprint_index_url or "http://blueprint-index:8031"
        )
        
        # Fetch device inventory for auto-fill
        device_inventory = []
        try:
            async with DataAPIClient(base_url=settings.data_api_url) as data_client:
                devices_response = await data_client.get("/api/devices")
                if devices_response and "data" in devices_response:
                    device_inventory = devices_response["data"]
        except Exception as e:
            logger.warning(f"Failed to fetch device inventory: {e}")
        
        # Generate deployment preview
        preview = await engine.preview_deployment(
            blueprint_id=blueprint_id,
            input_values=request.input_values or {},
            automation_name=request.automation_name,
            description=request.description,
            device_inventory=device_inventory
        )
        
        if not preview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Blueprint not found: {blueprint_id}"
            )
        
        return {
            "success": True,
            "data": preview,
            "message": f"Deployment preview generated for blueprint {blueprint_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate deployment preview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate deployment preview: {str(e)}"
        ) from e


@blueprint_router.get("/synergy/{synergy_id}/matches")
async def get_blueprint_matches_for_synergy(
    synergy_id: str,
    limit: int = Query(default=5, ge=1, le=20, description="Maximum blueprints to return"),
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Find blueprints that match a detected synergy pattern.
    
    This endpoint bridges synergy detection with blueprint deployment by
    finding blueprints that can implement detected synergy patterns.
    
    Args:
        synergy_id: Synergy ID to find blueprint matches for
        limit: Maximum number of matching blueprints to return
        db: Database session dependency
        
    Returns:
        dict: Matching blueprints ranked by fit score
        
    Raises:
        HTTPException: If synergy not found (404) or query fails (500)
    """
    if not BLUEPRINT_ENGINE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blueprint Opportunity Engine not available."
        )
    
    try:
        # Fetch synergy details
        synergies = await get_synergy_opportunities(db, limit=10000)
        synergy_data = None
        for s in synergies:
            if isinstance(s, dict):
                if s.get("synergy_id") == synergy_id:
                    synergy_data = s.copy()
                    # Parse opportunity_metadata if string
                    opp_meta = synergy_data.get("opportunity_metadata")
                    if isinstance(opp_meta, str):
                        try:
                            synergy_data["opportunity_metadata"] = json.loads(opp_meta)
                        except (json.JSONDecodeError, TypeError):
                            synergy_data["opportunity_metadata"] = {}
                    break
            else:
                if s.synergy_id == synergy_id:
                    synergy_data = {
                        "synergy_id": s.synergy_id,
                        "synergy_type": s.synergy_type,
                        "device_ids": s.device_ids,
                        "area": s.area,
                        "opportunity_metadata": json.loads(s.opportunity_metadata) if isinstance(s.opportunity_metadata, str) else s.opportunity_metadata or {}
                    }
                    break
        
        if not synergy_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Synergy not found: {synergy_id}"
            )
        
        engine = BlueprintOpportunityEngine(
            blueprint_index_url=settings.blueprint_index_url or "http://blueprint-index:8031"
        )
        
        # Find blueprint matches for the synergy pattern
        matches = await engine.find_blueprints_for_synergy(
            synergy=synergy_data,
            limit=limit
        )
        
        return {
            "success": True,
            "data": {
                "synergy_id": synergy_id,
                "matches": [match.model_dump() for match in matches],
                "count": len(matches)
            },
            "message": f"Found {len(matches)} blueprint matches for synergy {synergy_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to find blueprint matches for synergy: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find blueprint matches: {str(e)}"
        ) from e


# CRITICAL: Include specific_router FIRST in main.py to ensure /stats and /list are matched before /{synergy_id}
# FastAPI matches routes in the order they're registered via include_router
# By including specific_router first, we ensure specific routes are matched before parameterized routes
# This is the recommended approach per FastAPI documentation for handling route order

