"""
AI Automation Service - Main FastAPI Application
Phase 1 MVP - Pattern detection and suggestion generation
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import sys
import logging
from pathlib import Path

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Setup logging (use shared logging config)
try:
    from shared.logging_config import setup_logging
    logger = setup_logging("ai-automation-service")
except ImportError:
    # Fallback if shared logging not available
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ai-automation-service")

from .config import settings
from .database.models import init_db
from .api import health_router, data_router, pattern_router, suggestion_router, analysis_router, suggestion_management_router, deployment_router, nl_generation_router, conversational_router, ask_ai_router, devices_router, settings_router, admin_router, set_device_intelligence_client
from .api.v2.conversation_router import router as conversation_router_v2
from .api.v2.automation_router import router as automation_router_v2
from .api.v2.action_router import router as action_router_v2
from .api.v2.streaming_router import router as streaming_router_v2
from .api.validation_router import router as validation_router
from .api.ranking_router import router as ranking_router
from .api.middlewares import AuthenticationMiddleware, IdempotencyMiddleware, RateLimitMiddleware
from .api.community_pattern_router import router as community_pattern_router
from .api.mcp_router import router as mcp_router
from .clients.data_api_client import DataAPIClient
from .clients.device_intelligence_client import DeviceIntelligenceClient
from .api.synergy_router import router as synergy_router  # Epic AI-3, Story AI3.8
from .api.analysis_router import set_scheduler
from .api.health import set_capability_listener
from .scheduler import DailyAnalysisScheduler

# Epic AI-2: Device Intelligence (Story AI2.1)
from .clients.mqtt_client import MQTTNotificationClient
from .device_intelligence import CapabilityParser, MQTTCapabilityListener

# Phase 1: Containerized AI Models
from .models.model_manager import get_model_manager

# Global variables for lifecycle management
mqtt_client = None
capability_parser = None
capability_listener = None

# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize service on startup and cleanup on shutdown"""
    global mqtt_client, capability_parser, capability_listener

    logger.info("=" * 60)
    logger.info("AI Automation Service Starting Up")
    logger.info("=" * 60)
    logger.info(f"Data API: {settings.data_api_url}")
    logger.info(f"Device Intelligence Service: {settings.device_intelligence_url}")
    logger.info(f"Home Assistant: {settings.ha_url}")
    logger.info(f"MQTT Broker: {settings.mqtt_broker}:{settings.mqtt_port}")
    logger.info(f"Analysis Schedule: {settings.analysis_schedule}")
    if settings.analysis_schedule != "0 3 * * *":
        logger.warning(
            "⚠️ Analysis schedule deviates from the default 03:00 run (current: %s). "
            "Confirm capability refresh still precedes the job.",
            settings.analysis_schedule
        )
    else:
        logger.info("✅ Analysis schedule confirmed for 03:00 daily run")
    logger.info("=" * 60)

    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

    # Initialize MQTT client (Epic AI-1 + AI-2)
    try:
        mqtt_client = MQTTNotificationClient(
            broker=settings.mqtt_broker,
            port=settings.mqtt_port,
            username=settings.mqtt_username,
            password=settings.mqtt_password
        )
        # Use improved connection with retry logic
        if mqtt_client.connect(max_retries=3, retry_delay=2.0):
            logger.info("✅ MQTT client connected")
        else:
            logger.warning("⚠️ MQTT client connection failed - continuing without MQTT")
            mqtt_client = None
    except Exception as e:
        logger.error(f"❌ MQTT client initialization failed: {e}")
        mqtt_client = None
        # Continue without MQTT - don't block service startup

    # Initialize Device Intelligence (Epic AI-2 - Story AI2.1)
    if mqtt_client and mqtt_client.is_connected:
        try:
            capability_parser = CapabilityParser()
            capability_listener = MQTTCapabilityListener(
                mqtt_client=mqtt_client,
                db_session=None,  # Story 2.2 will add database session
                parser=capability_parser
            )
            await capability_listener.start()
            set_capability_listener(capability_listener)  # Connect to health endpoint
            logger.info("✅ Device Intelligence capability listener started")
        except Exception as e:
            logger.error(f"❌ Device Intelligence initialization failed: {e}")
            # Continue without Device Intelligence - don't block service startup
    else:
        logger.warning("⚠️ Device Intelligence not started (MQTT unavailable)")

    # Set MQTT client in scheduler
    if mqtt_client:
        scheduler.set_mqtt_client(mqtt_client)

    # Start scheduler (Epic AI-1)
    try:
        scheduler.start()
        logger.info("✅ Daily analysis scheduler started")
    except Exception as e:
        logger.error(f"❌ Scheduler startup failed: {e}")
        # Don't raise - service can still run without scheduler

    # Initialize containerized AI models (Phase 1)
    try:
        model_manager = get_model_manager()
        await model_manager.initialize()
        logger.info("✅ Containerized AI models initialized")
    except Exception as e:
        logger.error(f"❌ AI models initialization failed: {e}")
        # Continue without models - service can still run with fallbacks

    # Set extractor references for stats endpoint
    try:
        from .api.health import set_model_orchestrator, set_multi_model_extractor

        # Try multi-model extractor first (currently active)
        extractor = get_multi_model_extractor()
        if extractor:
            set_multi_model_extractor(extractor)
            logger.info("✅ Multi-model extractor set for stats endpoint")

        # Fallback to orchestrator (if configured)
        orchestrator = get_model_orchestrator()
        if orchestrator:
            set_model_orchestrator(orchestrator)
            logger.info("✅ Model orchestrator set for stats endpoint")

        if not extractor and not orchestrator:
            logger.warning("⚠️ No extractor available for stats endpoint")
    except Exception as e:
        logger.error(f"❌ Failed to set extractor for stats: {e}")

    # Initialize ActionExecutor (start worker tasks)
    try:
        from .services.service_container import ServiceContainer
        service_container = ServiceContainer()
        action_executor = service_container.action_executor
        await action_executor.start()
        logger.info("✅ ActionExecutor started")
    except Exception as e:
        logger.error(f"❌ ActionExecutor startup failed: {e}")
        # Continue without ActionExecutor - will fall back to old method

    logger.info("✅ AI Automation Service ready")

    yield

    # Shutdown
    logger.info("AI Automation Service shutting down")
    
    # Shutdown ActionExecutor
    try:
        from .services.service_container import ServiceContainer
        service_container = ServiceContainer()
        if hasattr(service_container, '_action_executor') and service_container._action_executor:
            await service_container._action_executor.shutdown()
            logger.info("✅ ActionExecutor shutdown complete")
    except Exception as e:
        logger.error(f"❌ ActionExecutor shutdown failed: {e}")

    # Close device intelligence client
    try:
        await device_intelligence_client.close()
        logger.info("✅ Device Intelligence client closed")
    except Exception as e:
        logger.error(f"❌ Device Intelligence client shutdown failed: {e}")

    # Stop scheduler
    try:
        scheduler.stop()
        logger.info("✅ Scheduler stopped")
    except Exception as e:
        logger.error(f"❌ Scheduler shutdown failed: {e}")

    # Disconnect MQTT
    if mqtt_client:
        try:
            mqtt_client.disconnect()
            logger.info("✅ MQTT client disconnected")
        except Exception as e:
            logger.error(f"❌ MQTT disconnect failed: {e}")

    # Cleanup AI models (Phase 1)
    try:
        model_manager = get_model_manager()
        await model_manager.cleanup()
        logger.info("✅ AI models cleaned up")
    except Exception as e:
        logger.error(f"❌ AI models cleanup failed: {e}")

# Create FastAPI application
app = FastAPI(
    title="AI Automation Service",
    description="AI-powered Home Assistant automation suggestion system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware (allow frontend at ports 3000, 3001)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Health dashboard
        "http://127.0.0.1:3000",
        "http://localhost:3001",  # AI Automation standalone UI
        "http://127.0.0.1:3001",
        "http://ai-automation-ui",  # Container network
        "http://ai-automation-ui:80",
        "http://homeiq-dashboard",  # Health dashboard container
        "http://homeiq-dashboard:80"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication middleware (API key with optional admin override)
app.add_middleware(
    AuthenticationMiddleware,
    enabled=settings.enable_authentication
)

# Rate limiting middleware (before idempotency)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.rate_limit_requests_per_minute,
    requests_per_hour=settings.rate_limit_requests_per_hour,
    internal_requests_per_minute=settings.rate_limit_internal_requests_per_minute,
    key_header="X-HomeIQ-API-Key"
)

# Idempotency middleware
app.add_middleware(IdempotencyMiddleware)

# Add error handling middleware
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with detailed logging."""
    logger.error(f"❌ Validation error on {request.method} {request.url.path}: {exc}")
    logger.error(f"❌ Validation details: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "path": str(request.url.path),
            "method": request.method
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with logging."""
    logger.error(f"❌ Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
            "path": str(request.url.path),
            "method": request.method
        }
    )

# Include routers
app.include_router(health_router)
app.include_router(data_router)
# Pattern router - ensure it's registered with all routes
app.include_router(pattern_router)
app.include_router(suggestion_router)
app.include_router(synergy_router)  # Epic AI-3, Story AI3.8
app.include_router(community_pattern_router)  # Community pattern learning
app.include_router(analysis_router)
app.include_router(suggestion_management_router)
app.include_router(deployment_router)
app.include_router(nl_generation_router)  # Story AI1.21: Natural Language
app.include_router(conversational_router)  # Story AI1.23: Conversational Refinement (Phase 1: Stubs)
app.include_router(ask_ai_router)  # Ask AI Tab: Natural Language Query Interface
app.include_router(devices_router)  # Devices endpoint
app.include_router(settings_router)  # System settings management
app.include_router(admin_router)  # Admin dashboard endpoints
app.include_router(validation_router)  # Validation wall endpoint
app.include_router(ranking_router)  # Heuristic ranking endpoint
app.include_router(mcp_router)  # MCP Code Execution Tools

# v2 API routers (Phase 3 - New API Routers)
app.include_router(conversation_router_v2)  # Conversation API v2
app.include_router(automation_router_v2)  # Automation API v2
app.include_router(action_router_v2)  # Immediate Actions API v2
app.include_router(streaming_router_v2)  # Streaming API v2

# Initialize scheduler
scheduler = DailyAnalysisScheduler()
set_scheduler(scheduler)  # Connect scheduler to analysis router

# Epic AI-2: Device Intelligence components (Story AI2.1)
mqtt_client = None
capability_parser = None
capability_listener = None

# Initialize Data API client for devices endpoint
data_api_client = DataAPIClient(base_url=settings.data_api_url)

# Initialize Device Intelligence Service client (Story DI-2.1)
device_intelligence_client = DeviceIntelligenceClient(base_url=settings.device_intelligence_url)

# Make device intelligence client available to routers
from .api.ask_ai_router import set_device_intelligence_client as set_ask_ai_client, get_model_orchestrator, get_multi_model_extractor
set_ask_ai_client(device_intelligence_client)  # For Ask AI router
set_device_intelligence_client(device_intelligence_client)  # For devices router


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8018,
        log_level=settings.log_level.lower()
    )

