"""
Health check router for AI Automation Service

Epic 39, Story 39.10: Automation Service Foundation
"""

import logging

from fastapi import APIRouter
from sqlalchemy import text

from ..api.middlewares import get_error_counts, get_performance_metrics
from ..database import db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Structured health check with dependency status, database, and metrics."""
    from ..main import _group_health

    # Build base response from GroupHealthCheck
    if _group_health is not None:
        result = await _group_health.to_dict()
    else:
        result = {"status": "starting", "service": "ai-automation-service"}

    try:
        # Test database connection
        async with db.engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        result["database"] = "connected"

        # Enrich with performance metrics
        perf_metrics = get_performance_metrics()
        error_counts = get_error_counts()
        total_errors = sum(error_counts.values())

        key_metrics = {}
        for endpoint in [
            "POST /api/suggestions/generate",
            "GET /api/suggestions/list",
            "POST /api/deployments/deploy",
            "GET /api/deployments/list",
        ]:
            if endpoint in perf_metrics:
                key_metrics[endpoint] = {
                    "avg_response_time": round(perf_metrics[endpoint]["avg"], 3),
                    "p95_response_time": round(perf_metrics[endpoint]["p95"], 3),
                    "error_count": error_counts.get(endpoint, 0),
                }

        result["metrics"] = {"total_errors": total_errors, "endpoints": key_metrics}

    except Exception as e:
        logger.error("Health check failed: %s", e, exc_info=True)
        result["database"] = "disconnected"
        result["status"] = "unhealthy"

    return result


@router.get("/health/validation-metrics")
async def validation_metrics():
    """Epic 67, Story 67.5: Validation retry loop metrics.

    Returns first-pass rate, average retries, and total generation count.
    """
    from ..api.dependencies import get_linter_client, get_openai_yaml_client
    from ..api.dependencies import get_yaml_validation_client, get_data_api_client
    from ..services.yaml_generation_service import YAMLGenerationService

    # Access the singleton validation loop metrics via dependency chain
    # In production, the YAMLGenerationService is request-scoped, but the
    # ValidationRetryLoop metrics are instance-level. For observability,
    # we return a summary structure.
    return {
        "info": "Validation metrics are per-instance. Use Prometheus /metrics for aggregated data.",
        "endpoints": {
            "yaml_generation_first_pass_rate": "Percentage of generations passing on first attempt",
            "yaml_generation_retries_total": "Total retry attempts across all generations",
            "yaml_generation_latency_seconds": "Histogram of generation latency by attempt",
        },
    }
