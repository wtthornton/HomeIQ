"""
Data API Service
Feature Data Hub for Home Assistant Ingestor

This service provides access to feature data including:
- HA event queries from InfluxDB
- Device and entity browsing
- Integration management
- Sports data and analytics
- Home Assistant automation endpoints
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Add shared directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.logging_config import (
    setup_logging, log_with_context, log_error_with_context,
    performance_monitor, generate_correlation_id
)
from shared.correlation_middleware import FastAPICorrelationMiddleware
from shared.auth import AuthManager
from shared.influxdb_query_client import InfluxDBQueryClient

# Story 22.1: SQLite database
from .database import init_db, check_db_health
import pathlib

# Import endpoint routers (Stories 13.2-13.4)
from .events_endpoints import EventsEndpoints
from .devices_endpoints import router as devices_router
from .alert_endpoints import AlertEndpoints
from .metrics_endpoints import create_metrics_router
from .integration_endpoints import router as integration_router
# WebSocket endpoints removed - using HTTP polling only
from .alerting_service import alerting_service
from .metrics_service import metrics_service

# Story 13.4: Sports & HA Automation (Epic 12 Integration)
from .sports_endpoints import router as sports_router
from .ha_automation_endpoints import router as ha_automation_router, start_webhook_detector, stop_webhook_detector

# Story 21.4: Analytics Endpoints
from .analytics_endpoints import router as analytics_router

# Energy Correlation Endpoints (Phase 4)
from .energy_endpoints import router as energy_router

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logger = setup_logging("data-api")

# Story 24.1: Track service start time for accurate uptime calculation
SERVICE_START_TIME = datetime.utcnow()


class APIResponse(BaseModel):
    """Standard API response model"""
    success: bool = Field(description="Whether the request was successful")
    data: Optional[Any] = Field(default=None, description="Response data")
    message: Optional[str] = Field(default=None, description="Response message")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = Field(default=False)
    error: str = Field(description="Error message")
    error_code: Optional[str] = Field(default=None)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class DataAPIService:
    """Main Data API service"""
    
    def __init__(self):
        """Initialize Data API service"""
        # Configuration
        self.api_host = os.getenv('DATA_API_HOST', '0.0.0.0')
        self.api_port = int(os.getenv('DATA_API_PORT', '8006'))
        self.api_title = 'Data API - Feature Data Hub'
        self.api_version = '1.0.0'
        self.api_description = 'Feature data access for HA Ingestor (events, devices, sports, analytics, HA automation)'
        
        # Security
        self.api_key = os.getenv('API_KEY')
        self.enable_auth = os.getenv('ENABLE_AUTH', 'false').lower() == 'true'  # Auth optional for data-api
        
        # CORS settings
        self.cors_origins = os.getenv('CORS_ORIGINS', '*').split(',')
        
        # Initialize components
        self.auth_manager = AuthManager(api_key=self.api_key, enable_auth=self.enable_auth)
        self.influxdb_client = InfluxDBQueryClient()
        
        # Service state
        self.start_time = datetime.now()
        self.is_running = False
        
        logger.info(f"Data API Service initialized (auth enabled: {self.enable_auth})")
    
    async def startup(self):
        """Start the Data API service"""
        logger.info("Starting Data API service...")
        
        # Start monitoring services (Story 13.3)
        await alerting_service.start()
        await metrics_service.start()
        
        # Start webhook event detector (Story 13.4)
        start_webhook_detector()
        
        # Connect to InfluxDB
        try:
            logger.info("Connecting to InfluxDB...")
            connected = await self.influxdb_client.connect()
            if connected:
                logger.info("InfluxDB connection established successfully")
            else:
                logger.warning("InfluxDB connection failed - service will start but queries may fail")
        except Exception as e:
            logger.error(f"Error connecting to InfluxDB: {e}")
            logger.warning("Service will start without InfluxDB connection")
        
        self.is_running = True
        logger.info(f"Data API service started on {self.api_host}:{self.api_port}")
    
    async def shutdown(self):
        """Stop the Data API service"""
        logger.info("Shutting down Data API service...")
        
        # Stop webhook detector (Story 13.4)
        stop_webhook_detector()
        
        # Stop monitoring services (Story 13.3)
        await alerting_service.stop()
        await metrics_service.stop()
        
        # Close InfluxDB connection
        try:
            await self.influxdb_client.close()
        except Exception as e:
            logger.error(f"Error closing InfluxDB connection: {e}")
        
        self.is_running = False
        logger.info("Data API service stopped")


# Create service instance
data_api_service = DataAPIService()


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle"""
    # Startup
    # Ensure data directory exists
    pathlib.Path("./data").mkdir(exist_ok=True)
    
    # Initialize SQLite database
    try:
        await init_db()
        logger.info("SQLite database initialized")
    except Exception as e:
        logger.error(f"SQLite initialization failed: {e}")
        # Don't crash - service can run without SQLite initially
    
    await data_api_service.startup()
    yield
    # Shutdown
    await data_api_service.shutdown()


# Create FastAPI app
app = FastAPI(
    title=data_api_service.api_title,
    version=data_api_service.api_version,
    description=data_api_service.api_description,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=data_api_service.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add correlation middleware
app.add_middleware(FastAPICorrelationMiddleware)


# Register endpoint routers (Stories 13.2-13.3)
# Story 13.2: Events & Devices
events_endpoints = EventsEndpoints()
app.include_router(
    events_endpoints.router,
    prefix="/api/v1",
    tags=["Events"]
)

app.include_router(
    devices_router,
    tags=["Devices & Entities"]
)

# Story 13.3: Alerts, Metrics, Integrations, WebSockets
alert_endpoints = AlertEndpoints()
app.include_router(
    alert_endpoints.router,
    prefix="/api/v1",
    tags=["Alerts"]
)

app.include_router(
    create_metrics_router(),
    prefix="/api/v1",
    tags=["Metrics"]
)

app.include_router(
    integration_router,
    prefix="/api/v1",
    tags=["Integrations"]
)

# WebSocket endpoints removed - dashboard uses HTTP polling for simplicity

# Story 13.4: Sports Data & HA Automation (Epic 12 + 13 Convergence)
app.include_router(
    sports_router,
    prefix="/api/v1",
    tags=["Sports Data"]
)

app.include_router(
    ha_automation_router,
    prefix="/api/v1",
    tags=["Home Assistant Automation"]
)

# Story 21.4: Analytics Endpoints (Real-time metrics aggregation)
app.include_router(
    analytics_router,
    prefix="/api/v1",
    tags=["Analytics"]
)

# Phase 4: Energy Correlation Endpoints
app.include_router(
    energy_router,
    prefix="/api/v1",
    tags=["Energy"]
)


# Root endpoint
@app.get("/", response_model=APIResponse)
async def root():
    """Root endpoint"""
    return APIResponse(
        success=True,
        data={
            "service": data_api_service.api_title,
            "version": data_api_service.api_version,
            "status": "running",
            "timestamp": datetime.now().isoformat()
        },
        message="Data API is running"
    )


# Health endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Returns service health status including InfluxDB and SQLite connections
    """
    uptime = (datetime.now() - data_api_service.start_time).total_seconds()
    influxdb_status = data_api_service.influxdb_client.get_connection_status()
    sqlite_status = await check_db_health()
    
    return {
        "status": "healthy" if data_api_service.is_running else "unhealthy",
        "service": "data-api",
        "version": data_api_service.api_version,
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": uptime,
        "dependencies": {
            "influxdb": {
                "status": "connected" if influxdb_status["is_connected"] else "disconnected",
                "url": influxdb_status["url"],
                "query_count": influxdb_status["query_count"],
                "avg_query_time_ms": influxdb_status["avg_query_time_ms"],
                "success_rate": influxdb_status["success_rate"]
            },
            "sqlite": sqlite_status
        },
        "authentication": {
            "enabled": data_api_service.enable_auth
        }
    }


# API info endpoint
@app.get("/api/info", response_model=APIResponse)
async def api_info():
    """API information endpoint"""
    return APIResponse(
        success=True,
        data={
            "title": data_api_service.api_title,
            "version": data_api_service.api_version,
            "description": data_api_service.api_description,
            "endpoints": {
                "health": "/health",
                "events": "/api/v1/events (Coming in Story 13.2)",
                "devices": "/api/v1/devices (Coming in Story 13.2)",
                "sports": "/api/v1/sports (Coming in Story 13.4)",
                "ha_automation": "/api/v1/ha (Coming in Story 13.4)"
            },
            "authentication": data_api_service.enable_auth
        },
        message="Data API information retrieved successfully"
    )


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            error_code=f"HTTP_{exc.status_code}"
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            error_code="INTERNAL_ERROR"
        ).model_dump()
    )


if __name__ == "__main__":
    # Run the service
    uvicorn.run(
        "src.main:app",
        host=data_api_service.api_host,
        port=data_api_service.api_port,
        reload=os.getenv('RELOAD', 'false').lower() == 'true',
        log_level=os.getenv('LOG_LEVEL', 'info').lower()
    )

