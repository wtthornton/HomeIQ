"""Validation and optimization route handlers."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .auth import verify_api_key

logger = logging.getLogger(__name__)

validation_router = APIRouter(tags=["validation"])
optimization_router = APIRouter(tags=["optimization"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class ApplyFixRequest(BaseModel):
    """Request to apply area assignment fix."""
    entity_id: str
    area_id: str


class BulkFixRequest(BaseModel):
    """Request to apply multiple area assignment fixes."""
    fixes: list[dict[str, str]]


# ---------------------------------------------------------------------------
# Optimization endpoints
# ---------------------------------------------------------------------------


@optimization_router.get("/api/optimization/analyze")
async def analyze_performance(request: Request) -> dict[str, Any]:
    """Run comprehensive performance analysis."""
    try:
        analyzer = getattr(request.app.state, "performance_analyzer", None)
        if not analyzer:
            raise HTTPException(status_code=503, detail="Performance analyzer not initialized")
        return await analyzer.analyze_performance()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error analyzing performance")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@optimization_router.get("/api/optimization/recommendations")
async def get_optimization_recommendations(request: Request) -> dict[str, Any]:
    """Generate optimization recommendations based on performance analysis."""
    try:
        analyzer = getattr(request.app.state, "performance_analyzer", None)
        rec_engine = getattr(request.app.state, "recommendation_engine", None)
        if not analyzer or not rec_engine:
            raise HTTPException(status_code=503, detail="Optimization engine not initialized")
        analysis = await analyzer.analyze_performance()
        recommendations = await rec_engine.generate_recommendations(analysis)
        return {
            "timestamp": datetime.now(UTC),
            "total_recommendations": len(recommendations),
            "recommendations": [r.model_dump() for r in recommendations],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error generating recommendations")
        raise HTTPException(status_code=500, detail="Internal server error") from e


# ---------------------------------------------------------------------------
# Validation endpoints
# ---------------------------------------------------------------------------


@validation_router.get("/api/v1/validation/ha-config")
async def get_ha_config_validation(
    request: Request, category: str | None = None, min_confidence: float = 0.0,
) -> dict[str, Any]:
    """Validate Home Assistant configuration and return suggestions."""
    try:
        validation_service = getattr(request.app.state, "validation_service", None)
        if not validation_service:
            raise HTTPException(status_code=503, detail="Validation service not initialized")
        result = await validation_service.validate_ha_config(category=category, min_confidence=min_confidence)
        return result.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Validation endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@validation_router.post("/api/v1/validation/apply-fix", dependencies=[Depends(verify_api_key)])
async def apply_validation_fix(req: Request, request: ApplyFixRequest) -> dict[str, Any]:
    """Apply a single area assignment fix to Home Assistant."""
    try:
        validation_service = getattr(req.app.state, "validation_service", None)
        if not validation_service:
            raise HTTPException(status_code=503, detail="Validation service not initialized")
        result = await validation_service.apply_fix(request.entity_id, request.area_id)
        validation_service.clear_cache()
        logger.info("Applied area fix: %s -> %s", request.entity_id, request.area_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Apply fix endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@validation_router.post("/api/v1/validation/apply-bulk-fixes", dependencies=[Depends(verify_api_key)])
async def apply_bulk_validation_fixes(req: Request, request: BulkFixRequest) -> dict[str, Any]:
    """Apply multiple area assignment fixes in batch."""
    try:
        validation_service = getattr(req.app.state, "validation_service", None)
        if not validation_service:
            raise HTTPException(status_code=503, detail="Validation service not initialized")
        result = await validation_service.apply_bulk_fixes(request.fixes)
        validation_service.clear_cache()
        logger.info("Applied bulk fixes: %s applied, %s failed", result["applied"], result["failed"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Apply bulk fixes endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e
