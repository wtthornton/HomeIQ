"""
HA Setup Service - Main FastAPI Application

Context7 Best Practices Applied:
- Lifespan context manager for initialization/cleanup
- Async dependency injection
- Response model validation
- Proper exception handling
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import os

from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .database import get_db, init_db
from .health_service import HealthMonitoringService
from .http_client import close_http_session
from .integration_checker import IntegrationHealthChecker
from .monitoring_service import ContinuousHealthMonitor
from .optimization_engine import PerformanceAnalysisEngine, RecommendationEngine
from .schemas import (
    EnvironmentHealthResponse,
    HealthCheckResponse,
    IntegrationStatus,
)
from .setup_wizard import MQTTSetupWizard, Zigbee2MQTTSetupWizard
from .validation_service import ValidationService
from .zigbee_bridge_manager import ZigbeeBridgeManager
from .zigbee_setup_wizard import SetupWizardRequest
from .zigbee_setup_wizard import Zigbee2MQTTSetupWizard as ZigbeeSetupWizard

settings = get_settings()
logger = logging.getLogger(__name__)

# API key authentication for destructive endpoints
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)
_api_key = os.getenv("HA_SETUP_API_KEY", "")


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Verify API key for destructive endpoints"""
    if not _api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key not configured on server"
        )
    if api_key != _api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    return api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for service initialization and cleanup

    Context7 Pattern: Modern FastAPI lifespan management
    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown")
    """
    # Startup: Initialize services
    logger.info("HA Setup Service Starting")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Initialize health monitoring service
    app.state.monitor = HealthMonitoringService()
    logger.info("Health monitoring service initialized")

    # Initialize integration health checker
    app.state.integration_checker = IntegrationHealthChecker()
    logger.info("Integration health checker initialized")

    # Initialize continuous monitoring
    continuous_monitor = ContinuousHealthMonitor(
        app.state.monitor,
        app.state.integration_checker
    )
    app.state.continuous_monitor = continuous_monitor

    # Start background monitoring
    await continuous_monitor.start()
    logger.info("Continuous health monitoring started")

    # Initialize setup wizards
    app.state.zigbee2mqtt_wizard = Zigbee2MQTTSetupWizard()
    app.state.mqtt_wizard = MQTTSetupWizard()
    logger.info("Setup wizards initialized")

    # Initialize optimization engine
    app.state.performance_analyzer = PerformanceAnalysisEngine()
    app.state.recommendation_engine = RecommendationEngine()
    logger.info("Optimization engine initialized")

    # Initialize bridge manager
    app.state.bridge_manager = ZigbeeBridgeManager()
    logger.info("Zigbee2MQTT bridge manager initialized")

    # Initialize enhanced setup wizard
    app.state.zigbee_setup_wizard = ZigbeeSetupWizard()
    logger.info("Enhanced Zigbee2MQTT setup wizard initialized")

    # Initialize validation service
    app.state.validation_service = ValidationService()
    logger.info("Validation service initialized")

    logger.info(f"HA Setup Service Ready - Listening on port {settings.service_port}")

    yield  # Application runs here

    # Shutdown: Stop monitoring before cleanup
    logger.info("Stopping continuous monitoring...")
    await continuous_monitor.stop()

    # Shutdown: Close shared HTTP session
    await close_http_session()

    # Shutdown: Clean up resources
    logger.info("HA Setup Service Shutting Down")


# Create FastAPI app with lifespan
app = FastAPI(
    title="HA Setup & Recommendation Service",
    description="Automated setup, health monitoring, and optimization for Home Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health Check Endpoints

@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["health"],
    summary="Simple health check"
)
async def health_check():
    """Simple health check endpoint for container orchestration"""
    return HealthCheckResponse(
        status="healthy",
        service=settings.service_name,
        timestamp=datetime.now(timezone.utc),
        version="1.0.0"
    )


@app.get(
    "/api/health/environment",
    response_model=EnvironmentHealthResponse,
    tags=["health"],
    summary="Get comprehensive environment health status"
)
async def get_environment_health(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> EnvironmentHealthResponse:
    """
    Get comprehensive environment health status
    
    Returns:
        Complete health status including:
        - Overall health score (0-100)
        - Home Assistant core status
        - Integration statuses
        - Performance metrics
        - Detected issues
    """
    try:
        health_service = getattr(request.app.state, "monitor", None)
        if not health_service:
            logger.error(
                "Environment health requested before monitor initialized",
                extra={"event": "environment_health", "status": "uninitialized"}
            )
            # Return minimal response instead of 503 to prevent frontend showing 0/100
            from .schemas import HealthStatus, PerformanceMetrics
            return EnvironmentHealthResponse(
                health_score=0,
                ha_status=HealthStatus.UNKNOWN,
                ha_version=None,
                integrations=[],
                performance=PerformanceMetrics(response_time_ms=0.0),
                issues_detected=["Health monitoring service not initialized. Service may still be starting up."],
                timestamp=datetime.now(timezone.utc)
            )

        response = await health_service.check_environment_health(db)

        logger.info(
            "Environment health retrieved",
            extra={
                "event": "environment_health",
                "health_score": response.health_score,
                "ha_status": str(response.ha_status),
                "integration_count": len(response.integrations),
                "issues_detected": len(response.issues_detected),
            }
        )

        return response

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.exception(
            "Environment health endpoint failed",
            extra={"event": "environment_health", "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


@app.get(
    "/api/health/trends",
    tags=["health"],
    summary="Get health trends over time"
)
async def get_health_trends(
    request: Request,
    hours: int = 24,
    db: AsyncSession = Depends(get_db)
):
    """
    Get health trends over specified time period
    
    Args:
        hours: Number of hours to analyze (default: 24)
        
    Returns:
        Trend analysis including average score, min/max, and trend direction
    """
    try:
        continuous_monitor = getattr(request.app.state, "continuous_monitor", None)
        if not continuous_monitor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Continuous monitoring not initialized"
            )

        trends = await continuous_monitor.get_health_trends(db, hours)
        return trends

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting health trends")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


@app.get(
    "/api/health/integrations",
    tags=["health"],
    summary="Get detailed integration health status"
)
async def get_integrations_health(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed health status for all integrations
    
    Checks:
    - Home Assistant authentication
    - MQTT broker connectivity
    - Zigbee2MQTT status
    - Device discovery
    - HA Ingestor services (Data API, Admin API)
    
    Returns:
        List of integration health results with detailed diagnostics
    """
    try:
        integration_checker = getattr(request.app.state, "integration_checker", None)
        if not integration_checker:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Integration health checker not initialized"
            )

        # Run all integration checks
        check_results = await integration_checker.check_all_integrations()

        # Store results in database
        await _store_integration_health_results(db, check_results)

        # Return results
        return {
            "timestamp": datetime.now(timezone.utc),
            "total_integrations": len(check_results),
            "healthy_count": sum(1 for r in check_results if r.status == IntegrationStatus.HEALTHY),
            "warning_count": sum(1 for r in check_results if r.status == IntegrationStatus.WARNING),
            "error_count": sum(1 for r in check_results if r.status == IntegrationStatus.ERROR),
            "not_configured_count": sum(1 for r in check_results if r.status == IntegrationStatus.NOT_CONFIGURED),
            "integrations": [r.model_dump() for r in check_results]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error checking integrations")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


async def _store_integration_health_results(
    db: AsyncSession,
    check_results: list
):
    """Store integration health check results in database"""
    try:
        from .models import IntegrationHealth

        for result in check_results:
            integration_health = IntegrationHealth(
                integration_name=result.integration_name,
                integration_type=result.integration_type,
                status=result.status.value,
                is_configured=result.is_configured,
                is_connected=result.is_connected,
                error_message=result.error_message,
                last_check=result.last_check,
                check_details=result.check_details
            )

            db.add(integration_health)

        await db.commit()

    except Exception as e:
        await db.rollback()
        # Log error but don't fail the health check
        logger.error("Error storing integration health results", exc_info=e)


# Root endpoint

# Setup Wizard Endpoints

@app.post(
    "/api/setup/wizard/{integration_type}/start",
    tags=["setup"],
    summary="Start setup wizard for integration"
)
async def start_setup_wizard(request: Request, integration_type: str):
    """
    Start a setup wizard for specified integration type
    
    Supported types:
    - zigbee2mqtt
    - mqtt
    """
    try:
        if integration_type == "zigbee2mqtt":
            wizard = getattr(request.app.state, "zigbee2mqtt_wizard", None)
            if not wizard:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Setup wizard not initialized")
            session_id = await wizard.start_zigbee2mqtt_setup()
        elif integration_type == "mqtt":
            wizard = getattr(request.app.state, "mqtt_wizard", None)
            if not wizard:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Setup wizard not initialized")
            session_id = await wizard.start_mqtt_setup()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported integration type: {integration_type}"
            )

        return {
            "session_id": session_id,
            "integration_type": integration_type,
            "status": "started",
            "timestamp": datetime.now(timezone.utc)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error starting setup wizard")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


@app.post(
    "/api/setup/wizard/{session_id}/step/{step_number}",
    tags=["setup"],
    summary="Execute setup wizard step"
)
async def execute_wizard_step(
    request: Request,
    session_id: str,
    step_number: int,
    step_data: dict = None
):
    """Execute a specific step in the setup wizard"""
    try:
        # Get wizard from session
        zigbee_wizard = getattr(request.app.state, "zigbee2mqtt_wizard", None)
        mqtt_wizard = getattr(request.app.state, "mqtt_wizard", None)

        # Check which wizard owns this session
        session = zigbee_wizard.get_session_status(session_id) or mqtt_wizard.get_session_status(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        # Get appropriate wizard
        wizard = zigbee_wizard if session["integration_type"] == "zigbee2mqtt" else mqtt_wizard

        result = await wizard.execute_step(session_id, step_number, step_data)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error executing wizard step")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


# Performance Optimization Endpoints

@app.get(
    "/api/optimization/analyze",
    tags=["optimization"],
    summary="Analyze system performance"
)
async def analyze_performance(request: Request):
    """
    Run comprehensive performance analysis
    
    Returns:
        Performance analysis with bottlenecks identified
    """
    try:
        analyzer = getattr(request.app.state, "performance_analyzer", None)
        if not analyzer:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Performance analyzer not initialized"
            )

        analysis = await analyzer.analyze_performance()
        return analysis

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error analyzing performance")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


@app.get(
    "/api/optimization/recommendations",
    tags=["optimization"],
    summary="Get optimization recommendations"
)
async def get_optimization_recommendations(request: Request):
    """
    Generate optimization recommendations based on performance analysis
    
    Returns:
        Prioritized list of optimization recommendations
    """
    try:
        analyzer = getattr(request.app.state, "performance_analyzer", None)
        rec_engine = getattr(request.app.state, "recommendation_engine", None)

        if not analyzer or not rec_engine:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Optimization engine not initialized"
            )

        # Run performance analysis
        analysis = await analyzer.analyze_performance()

        # Generate recommendations
        recommendations = await rec_engine.generate_recommendations(analysis)

        return {
            "timestamp": datetime.now(timezone.utc),
            "total_recommendations": len(recommendations),
            "recommendations": [r.model_dump() for r in recommendations]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error generating recommendations")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


# Zigbee2MQTT Bridge Management Endpoints

@app.get("/api/zigbee2mqtt/bridge/status", tags=["Zigbee2MQTT Bridge"])
async def get_bridge_status(request: Request):
    """Get comprehensive Zigbee2MQTT bridge health status"""
    try:
        bridge_manager = getattr(request.app.state, "bridge_manager", None)
        if not bridge_manager:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bridge manager not initialized")
        health_status = await bridge_manager.get_bridge_health_status()

        return {
            "bridge_state": health_status.bridge_state.value,
            "is_connected": health_status.is_connected,
            "health_score": health_status.health_score,
            "device_count": health_status.metrics.device_count,
            "response_time_ms": health_status.metrics.response_time_ms,
            "signal_strength_avg": health_status.metrics.signal_strength_avg,
            "network_health_score": health_status.metrics.network_health_score,
            "consecutive_failures": health_status.consecutive_failures,
            "recommendations": health_status.recommendations,
            "last_check": health_status.last_check,
            "recovery_attempts": [
                {
                    "timestamp": attempt.timestamp,
                    "action": attempt.action.value,
                    "success": attempt.success,
                    "error_message": attempt.error_message,
                    "duration_seconds": attempt.duration_seconds
                } for attempt in health_status.recovery_attempts
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get bridge status")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.post("/api/zigbee2mqtt/bridge/recovery", tags=["Zigbee2MQTT Bridge"], dependencies=[Depends(verify_api_key)])
async def attempt_bridge_recovery(request: Request, force: bool = False):
    """Attempt to recover Zigbee2MQTT bridge connectivity"""
    try:
        bridge_manager = getattr(request.app.state, "bridge_manager", None)
        if not bridge_manager:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bridge manager not initialized")
        success, message = await bridge_manager.attempt_bridge_recovery(force=force)

        return {
            "success": success,
            "message": message,
            "timestamp": datetime.now(timezone.utc)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Recovery failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.post("/api/zigbee2mqtt/bridge/restart", tags=["Zigbee2MQTT Bridge"], dependencies=[Depends(verify_api_key)])
async def restart_bridge(request: Request):
    """Restart Zigbee2MQTT bridge (alias for recovery)"""
    try:
        bridge_manager = getattr(request.app.state, "bridge_manager", None)
        if not bridge_manager:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bridge manager not initialized")
        success, message = await bridge_manager.attempt_bridge_recovery(force=True)

        return {
            "success": success,
            "message": message,
            "timestamp": datetime.now(timezone.utc)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Bridge restart failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/api/zigbee2mqtt/bridge/health", tags=["Zigbee2MQTT Bridge"])
async def get_bridge_health(request: Request):
    """Simple health check endpoint for bridge status"""
    try:
        bridge_manager = getattr(request.app.state, "bridge_manager", None)
        if not bridge_manager:
            return {
                "healthy": False,
                "state": "uninitialized",
                "health_score": 0,
                "error": "Bridge manager not initialized",
                "last_check": datetime.now(timezone.utc)
            }
        health_status = await bridge_manager.get_bridge_health_status()

        return {
            "healthy": health_status.bridge_state.value == "online",
            "state": health_status.bridge_state.value,
            "health_score": health_status.health_score,
            "device_count": health_status.metrics.device_count,
            "last_check": health_status.last_check
        }

    except Exception as e:
        return {
            "healthy": False,
            "state": "error",
            "health_score": 0,
            "error": str(e),
            "last_check": datetime.now(timezone.utc)
        }


# Zigbee2MQTT Setup Wizard Endpoints

@app.post("/api/zigbee2mqtt/setup/start", tags=["Zigbee2MQTT Setup"])
async def start_zigbee_setup_wizard(req: Request, request: SetupWizardRequest):
    """Start a new Zigbee2MQTT setup wizard"""
    try:
        setup_wizard = getattr(req.app.state, "zigbee_setup_wizard", None)
        if not setup_wizard:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Setup wizard not initialized")
        response = await setup_wizard.start_setup_wizard(request)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to start setup wizard")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.post("/api/zigbee2mqtt/setup/{wizard_id}/continue", tags=["Zigbee2MQTT Setup"])
async def continue_zigbee_setup_wizard(request: Request, wizard_id: str):
    """Continue the setup wizard to the next step"""
    try:
        setup_wizard = getattr(request.app.state, "zigbee_setup_wizard", None)
        if not setup_wizard:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Setup wizard not initialized")
        response = await setup_wizard.continue_wizard(wizard_id)
        return response

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to continue wizard")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/api/zigbee2mqtt/setup/{wizard_id}/status", tags=["Zigbee2MQTT Setup"])
async def get_zigbee_setup_wizard_status(request: Request, wizard_id: str):
    """Get current wizard status"""
    try:
        setup_wizard = getattr(request.app.state, "zigbee_setup_wizard", None)
        if not setup_wizard:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Setup wizard not initialized")
        response = await setup_wizard.get_wizard_status(wizard_id)

        if response is None:
            raise HTTPException(status_code=404, detail="Wizard not found")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get wizard status")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.delete("/api/zigbee2mqtt/setup/{wizard_id}", tags=["Zigbee2MQTT Setup"])
async def cancel_zigbee_setup_wizard(request: Request, wizard_id: str):
    """Cancel an active setup wizard"""
    try:
        setup_wizard = getattr(request.app.state, "zigbee_setup_wizard", None)
        if not setup_wizard:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Setup wizard not initialized")
        success = await setup_wizard.cancel_wizard(wizard_id)

        if success:
            return {"message": "Wizard cancelled successfully", "wizard_id": wizard_id}
        else:
            raise HTTPException(status_code=404, detail="Wizard not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to cancel wizard")
        raise HTTPException(status_code=500, detail="Internal server error") from e


# Validation Endpoints (Epic 32)

@app.get(
    "/api/v1/validation/ha-config",
    tags=["validation"],
    summary="Get Home Assistant configuration validation results"
)
async def get_ha_config_validation(
    request: Request,
    category: str | None = None,
    min_confidence: float = 0.0
):
    """
    Validate Home Assistant configuration and get suggestions
    
    Checks for:
    - Missing area assignments
    - Incorrect area assignments
    
    Args:
        category: Optional filter by issue category (e.g., "missing_area_assignment")
        min_confidence: Minimum confidence score (0-100) for suggestions
        
    Returns:
        Validation results with issues and suggestions
    """
    try:
        validation_service = getattr(request.app.state, "validation_service", None)
        if not validation_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Validation service not initialized"
            )

        result = await validation_service.validate_ha_config(
            category=category,
            min_confidence=min_confidence
        )
        
        return result.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Validation endpoint failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


class ApplyFixRequest(BaseModel):
    """Request to apply area assignment fix"""
    entity_id: str
    area_id: str


class BulkFixRequest(BaseModel):
    """Request to apply multiple area assignment fixes"""
    fixes: list[dict[str, str]]


@app.post(
    "/api/v1/validation/apply-fix",
    tags=["validation"],
    summary="Apply area assignment fix",
    dependencies=[Depends(verify_api_key)]
)
async def apply_validation_fix(
    req: Request,
    request: ApplyFixRequest
):
    """
    Apply area assignment fix to Home Assistant

    Args:
        entity_id: Entity ID to update (e.g., "light.hue_office_back_left")
        area_id: Area ID to assign (e.g., "office")

    Returns:
        Success response with details
    """
    try:
        validation_service = getattr(req.app.state, "validation_service", None)
        if not validation_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Validation service not initialized"
            )
        
        result = await validation_service.apply_fix(request.entity_id, request.area_id)
        
        # Clear cache after applying fix
        validation_service.clear_cache()
        
        logger.info(
            f"Applied area fix: {request.entity_id} -> {request.area_id}",
            extra={"entity_id": request.entity_id, "area_id": request.area_id}
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Apply fix endpoint failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


@app.post(
    "/api/v1/validation/apply-bulk-fixes",
    tags=["validation"],
    summary="Apply multiple area assignment fixes",
    dependencies=[Depends(verify_api_key)]
)
async def apply_bulk_validation_fixes(
    req: Request,
    request: BulkFixRequest
):
    """
    Apply multiple area assignment fixes in batch

    Args:
        fixes: List of dicts with entity_id and area_id

    Returns:
        Summary of applied fixes
    """
    try:
        validation_service = getattr(req.app.state, "validation_service", None)
        if not validation_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Validation service not initialized"
            )
        
        result = await validation_service.apply_bulk_fixes(request.fixes)
        
        # Clear cache after applying fixes
        validation_service.clear_cache()
        
        logger.info(
            f"Applied bulk fixes: {result['applied']} applied, {result['failed']} failed"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Apply bulk fixes endpoint failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


# Root endpoint

@app.get("/", tags=["info"])
async def root():
    """Root endpoint with service information"""
    return {
        "service": "HA Setup & Recommendation Service",
        "version": "1.0.0",
        "status": "running",
        "features": {
            "health_monitoring": "Real-time environment health monitoring",
            "integration_checking": "Comprehensive integration health validation",
            "setup_wizards": "Guided setup for MQTT and Zigbee2MQTT",
            "performance_optimization": "Automated performance analysis and recommendations",
            "continuous_monitoring": "Background health monitoring with alerting"
        },
        "endpoints": {
            "health": "/health",
            "environment_health": "/api/health/environment",
            "health_trends": "/api/health/trends?hours=24",
            "integrations_health": "/api/health/integrations",
            "performance_analysis": "/api/optimization/analyze",
            "recommendations": "/api/optimization/recommendations",
            "start_wizard": "/api/setup/wizard/{integration_type}/start",
            "bridge_status": "/api/zigbee2mqtt/bridge/status",
            "bridge_recovery": "/api/zigbee2mqtt/bridge/recovery",
            "bridge_restart": "/api/zigbee2mqtt/bridge/restart",
            "bridge_health": "/api/zigbee2mqtt/bridge/health",
            "setup_wizard_start": "/api/zigbee2mqtt/setup/start",
            "setup_wizard_continue": "/api/zigbee2mqtt/setup/{wizard_id}/continue",
            "setup_wizard_status": "/api/zigbee2mqtt/setup/{wizard_id}/status",
            "validation": "/api/v1/validation/ha-config",
            "apply_fix": "/api/v1/validation/apply-fix",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=True
    )

