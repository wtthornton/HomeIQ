"""
Synergy Opportunity Router

API endpoints for browsing and querying synergy opportunities.

Epic AI-3: Cross-Device Synergy & Contextual Opportunities
Story AI3.8: Frontend Synergy Tab
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.data_api_client import DataAPIClient
from ..config import settings
from ..database import get_db
from ..database.crud import (
    get_synergy_opportunities,
    get_synergy_stats,
    store_synergy_opportunities,
)
from ..database.models import SynergyOpportunity
from ..integration.pattern_synergy_validator import PatternSynergyValidator
from ..synergy_detection.synergy_detector import DeviceSynergyDetector
from .dependencies.auth import require_admin_user

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/synergies", tags=["Synergies"])


@router.get("", include_in_schema=True)
@router.get("/", include_in_schema=True)
async def list_synergies(
    synergy_type: str | None = Query(default=None, description="Filter by synergy type"),
    min_confidence: float = Query(default=0.7, ge=0.0, le=1.0, description="Minimum confidence"),
    validated_by_patterns: bool | None = Query(default=None, description="Filter by pattern validation (Phase 2)"),
    synergy_depth: int | None = Query(default=None, ge=2, le=5, description="Filter by chain depth (2=pair, 3=3-chain, 4=4-chain)"),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum results"),
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    List synergy opportunities.
    
    Story AI3.8: Frontend Synergy Tab
    
    Returns:
        List of synergy opportunities with metadata
    """
    try:
        logger.info(f"Listing synergies: type={synergy_type!r}, min_confidence={min_confidence}, validated_by_patterns={validated_by_patterns}")
        logger.info(f"Router received parameters - synergy_type type: {type(synergy_type)}, value: {repr(synergy_type)}")

        synergies = await get_synergy_opportunities(
            db,
            synergy_type=synergy_type,
            min_confidence=min_confidence,
            synergy_depth=synergy_depth,
            limit=limit
        )

        # Convert to dict format for JSON response
        synergies_list = []
        for s in synergies:
            # Phase 2: Filter by pattern validation if requested
            # Use getattr with defaults in case Phase 2 columns don't exist
            validated_by_patterns_value = getattr(s, 'validated_by_patterns', False)
            if validated_by_patterns is not None and validated_by_patterns_value != validated_by_patterns:
                continue

            synergy_dict = {
                'id': s.id,
                'synergy_id': s.synergy_id,
                'synergy_type': s.synergy_type,
                'device_ids': s.device_ids,
                'opportunity_metadata': s.opportunity_metadata,
                'impact_score': s.impact_score,
                'complexity': s.complexity,
                'confidence': s.confidence,
                'area': s.area,
                'created_at': s.created_at.isoformat() if s.created_at else None
            }

            # Phase 2: Add pattern validation fields (use getattr with defaults)
            synergy_dict['pattern_support_score'] = getattr(s, 'pattern_support_score', 0.0)
            synergy_dict['validated_by_patterns'] = validated_by_patterns_value
            supporting_pattern_ids_value = getattr(s, 'supporting_pattern_ids', None)
            if supporting_pattern_ids_value:
                import json
                try:
                    synergy_dict['supporting_pattern_ids'] = json.loads(supporting_pattern_ids_value)
                except:
                    synergy_dict['supporting_pattern_ids'] = []
            else:
                synergy_dict['supporting_pattern_ids'] = []

            # Epic AI-4: Add n-level synergy fields
            synergy_dict['synergy_depth'] = getattr(s, 'synergy_depth', 2)
            chain_devices_value = getattr(s, 'chain_devices', None)
            if chain_devices_value:
                import json
                try:
                    synergy_dict['chain_devices'] = json.loads(chain_devices_value)
                except:
                    synergy_dict['chain_devices'] = []
            else:
                synergy_dict['chain_devices'] = synergy_dict.get('device_ids', [])

            synergies_list.append(synergy_dict)

        return {
            'success': True,
            'data': {
                'synergies': synergies_list,
                'count': len(synergies_list)
            }
        }

    except Exception as e:
        logger.error(f"Failed to list synergies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve synergies: {str(e)}")


@router.get("/stats")
async def synergy_statistics(
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get synergy opportunity statistics.
    
    Story AI3.8: Frontend Synergy Tab
    
    Returns:
        Statistics about detected synergies
    """
    try:
        stats = await get_synergy_stats(db)

        return {
            'success': True,
            'data': stats
        }

    except Exception as e:
        logger.error(f"Failed to get synergy stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {str(e)}")


@router.get("/{synergy_id}")
async def get_synergy_detail(
    synergy_id: str,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get single synergy opportunity by ID.
    
    Story AI3.8: Frontend Synergy Tab
    
    Args:
        synergy_id: Synergy UUID
    
    Returns:
        Synergy opportunity details
    """
    try:
        from sqlalchemy import select

        result = await db.execute(
            select(SynergyOpportunity).where(SynergyOpportunity.synergy_id == synergy_id)
        )
        synergy = result.scalar_one_or_none()

        if not synergy:
            raise HTTPException(status_code=404, detail=f"Synergy {synergy_id} not found")

        return {
            'success': True,
            'data': {
                'synergy': {
                    'id': synergy.id,
                    'synergy_id': synergy.synergy_id,
                    'synergy_type': synergy.synergy_type,
                    'device_ids': synergy.device_ids,
                    'opportunity_metadata': synergy.opportunity_metadata,
                    'impact_score': synergy.impact_score,
                    'complexity': synergy.complexity,
                    'confidence': synergy.confidence,
                    'area': synergy.area,
                    'created_at': synergy.created_at.isoformat() if synergy.created_at else None
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get synergy {synergy_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get synergy detail: {str(e)}")


@router.post("/detect")
async def detect_synergies_realtime(
    use_patterns: bool = Query(default=True, description="Enable pattern validation (Phase 3)"),
    min_pattern_confidence: float = Query(default=0.7, ge=0.0, le=1.0, description="Minimum pattern confidence for validation"),
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_user)
) -> dict[str, Any]:
    """
    Real-time synergy detection with optional pattern validation.
    
    Phase 3: On-demand synergy detection with pattern cross-validation.
    
    Args:
        use_patterns: Whether to validate synergies against patterns (default: True)
        min_pattern_confidence: Minimum pattern confidence for validation (default: 0.7)
        
    Returns:
        Detected synergies with pattern validation if enabled
    """
    try:
        import asyncio

        logger.info(f"Starting real-time synergy detection (use_patterns={use_patterns})")

        # Initialize detector
        data_api_client = DataAPIClient(base_url=settings.data_api_url)
        detector = DeviceSynergyDetector(
            data_api_client=data_api_client,
            ha_client=None  # Can be added if needed
        )

        # Detect synergies with timeout protection (max 100 seconds to leave buffer for nginx 120s timeout)
        try:
            synergies = await asyncio.wait_for(
                detector.detect_synergies(),
                timeout=100.0  # 100 seconds max (nginx timeout is 120s)
            )
        except asyncio.TimeoutError:
            logger.error("Synergy detection timed out after 100 seconds")
            raise HTTPException(
                status_code=504,
                detail="Synergy detection timed out. Try reducing the number of devices or running detection in smaller batches."
            )

        logger.info(f"Detected {len(synergies)} synergy opportunities")

        # Store with pattern validation if enabled
        stored_count = await store_synergy_opportunities(
            db,
            synergies,
            validate_with_patterns=use_patterns,
            min_pattern_confidence=min_pattern_confidence
        )

        # Return results with validation data
        synergies_list = []
        for synergy_data in synergies:
            synergy_dict = {
                'synergy_id': synergy_data.get('synergy_id'),
                'synergy_type': synergy_data.get('synergy_type'),
                'device_ids': synergy_data.get('devices', []),
                'impact_score': synergy_data.get('impact_score'),
                'complexity': synergy_data.get('complexity'),
                'confidence': synergy_data.get('confidence'),
                'area': synergy_data.get('area'),
                'opportunity_metadata': synergy_data.get('opportunity_metadata', {})
            }

            # If pattern validation was enabled, get validation results
            # Note: Validation already happened during storage, so we can skip here
            # to avoid using a potentially rolled-back session
            if use_patterns:
                try:
                    # Check if session is healthy before using it
                    from sqlalchemy import select
                    from sqlalchemy.exc import PendingRollbackError
                    try:
                        await db.execute(select(1))
                    except (PendingRollbackError, Exception):
                        # Session is in bad state, skip validation
                        logger.warning("Skipping pattern validation - session in bad state")
                        synergy_dict['pattern_validation'] = {
                            'pattern_support_score': 0.0,
                            'validated_by_patterns': False,
                            'validation_status': 'unknown',
                            'supporting_patterns_count': 0
                        }
                    else:
                        validator = PatternSynergyValidator(db)
                        validation_result = await validator.validate_synergy_with_patterns(
                            synergy_data, min_pattern_confidence
                        )
                        synergy_dict['pattern_validation'] = {
                            'pattern_support_score': validation_result.get('pattern_support_score', 0.0),
                            'validated_by_patterns': validation_result.get('validated_by_patterns', False),
                            'validation_status': validation_result.get('validation_status', 'invalid'),
                            'supporting_patterns_count': len(validation_result.get('supporting_patterns', []))
                        }
                except Exception as e:
                    logger.warning(f"Error getting pattern validation for synergy {synergy_data.get('synergy_id')}: {e}")
                    synergy_dict['pattern_validation'] = {
                        'pattern_support_score': 0.0,
                        'validated_by_patterns': False,
                        'validation_status': 'error',
                        'supporting_patterns_count': 0
                    }

            synergies_list.append(synergy_dict)

        return {
            'success': True,
            'data': {
                'synergies': synergies_list,
                'count': len(synergies_list),
                'stored_count': stored_count,
                'pattern_validation_enabled': use_patterns
            },
            'message': f"Detected {len(synergies_list)} synergies{' with pattern validation' if use_patterns else ''}"
        }

    except Exception as e:
        logger.error(f"Failed to detect synergies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to detect synergies: {str(e)}")

