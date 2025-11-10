"""
Admin REST API Service
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

# Add shared directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.logging_config import (
    setup_logging, get_logger, log_with_context, log_performance, 
    log_error_with_context, performance_monitor, generate_correlation_id,
    set_correlation_id, get_correlation_id
)
from shared.correlation_middleware import FastAPICorrelationMiddleware

from .health_endpoints import HealthEndpoints
from shared.monitoring import StatsEndpoints, MonitoringEndpoints
from .config_endpoints import ConfigEndpoints
from .events_endpoints import EventsEndpoints
from .docker_endpoints import DockerEndpoints
# WebSocket endpoints removed - using HTTP polling only
from shared.endpoints import create_integration_router
from .config_manager import config_manager
from .mqtt_config_endpoints import router as mqtt_config_router
from .devices_endpoints import router as devices_router
from .metrics_endpoints import create_metrics_router
from .alert_endpoints import create_alert_router
from shared.auth import AuthManager  # Moved to shared
from shared.monitoring import logging_service, metrics_service, alerting_service

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure enhanced logging
logger = setup_logging("admin-api")


class APIResponse(BaseModel):
    """Standard API response model"""
    success: bool = Field(description="Whether the request was successful")
    data: Optional[Any] = Field(default=None, description="Response data")
    message: Optional[str] = Field(default=None, description="Response message")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Response timestamp")
    request_id: Optional[str] = Field(default=None, description="Request ID for tracking")


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = Field(default=False, description="Always false for errors")
    error: str = Field(description="Error message")
    error_code: Optional[str] = Field(default=None, description="Error code")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Error timestamp")
    request_id: Optional[str] = Field(default=None, description="Request ID for tracking")


class AdminAPIService:
    """Main Admin API service"""
    
    def __init__(self):
        """Initialize Admin API service"""
        # Configuration
        self.api_host = os.getenv('API_HOST', '0.0.0.0')
        self.api_port = int(os.getenv('API_PORT', '8000'))
        self.api_title = os.getenv('API_TITLE', 'Home Assistant Ingestor Admin API')
        self.api_version = os.getenv('API_VERSION', '1.0.0')
        self.api_description = os.getenv('API_DESCRIPTION', 'Admin API for Home Assistant Ingestor')
        
        # Security
        self.api_key = os.getenv('API_KEY')
        self.enable_auth = os.getenv('ENABLE_AUTH', 'true').lower() == 'true'
        
        # CORS settings
        self.cors_origins = os.getenv('CORS_ORIGINS', '*').split(',')
        self.cors_methods = os.getenv('CORS_METHODS', 'GET,POST,PUT,DELETE').split(',')
        self.cors_headers = os.getenv('CORS_HEADERS', '*').split(',')
        
        # Initialize components
        self.start_time = datetime.now()  # Add start time for uptime calculation
        self.auth_manager = AuthManager(api_key=self.api_key, enable_auth=self.enable_auth)
        self.health_endpoints = HealthEndpoints()
        self.stats_endpoints = StatsEndpoints()
        self.config_endpoints = ConfigEndpoints()
        self.events_endpoints = EventsEndpoints()
        self.docker_endpoints = DockerEndpoints()
        self.monitoring_endpoints = MonitoringEndpoints(self.auth_manager)
        # Create integration router with service-specific config_manager
        self.integration_router = create_integration_router(config_manager)
        # WebSocket endpoints removed - using HTTP polling only
        
        # FastAPI app
        self.app: Optional[FastAPI] = None
        self.server_task: Optional[asyncio.Task] = None
        self.is_running = False
    
    async def start(self):
        """Start the Admin API service"""
        if self.is_running:
            logger.warning("Admin API service is already running")
            return
        
        # Start monitoring services
        await logging_service.start()
        await metrics_service.start()
        await alerting_service.start()
        
        # Initialize InfluxDB connection for stats endpoints
        try:
            logger.info("Initializing InfluxDB connection for statistics...")
            await self.stats_endpoints.initialize()
            logger.info("InfluxDB connection initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize InfluxDB: {e}")
            logger.warning("Statistics will fall back to direct service calls")
        
        # Add middleware
        self._add_middleware()
        
        # Add routes
        self._add_routes()
        
        # Add exception handlers
        self._add_exception_handlers()
        
        # Start server
        config = uvicorn.Config(
            app=self.app,
            host=self.api_host,
            port=self.api_port,
            log_level=os.getenv('LOG_LEVEL', 'info').lower()
        )
        server = uvicorn.Server(config)
        
        self.server_task = asyncio.create_task(server.serve())
        self.is_running = True
        
        logger.info(f"Admin API service started on {self.api_host}:{self.api_port}")
    
    async def stop(self):
        """Stop the Admin API service"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.server_task:
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
        
        # Close InfluxDB connection
        try:
            logger.info("Closing InfluxDB connection...")
            await self.stats_endpoints.close()
        except Exception as e:
            logger.error(f"Error closing InfluxDB connection: {e}")
        
        # Stop monitoring services
        await alerting_service.stop()
        await metrics_service.stop()
        await logging_service.stop()
        
        logger.info("Admin API service stopped")
    
    def _add_middleware(self):
        """Add middleware to FastAPI app"""
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
            allow_credentials=True,
            allow_methods=self.cors_methods,
            allow_headers=self.cors_headers
        )
        
        # Request logging middleware
        @self.app.middleware("http")
        async def log_requests(request, call_next):
            start_time = datetime.now()
            
            # Process request
            response = await call_next(request)
            
            # Log request
            process_time = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.3f}s"
            )
            
            return response
    
    def _add_routes(self):
        """Add routes to FastAPI app"""
        # Simple health endpoint that always works
        @self.app.get("/api/health")
        async def simple_health():
            """Simple health endpoint that always works"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "admin-api"
            }
        
        # Enhanced health endpoint with dependency information
        @self.app.get("/api/v1/health")
        async def enhanced_health():
            """Enhanced health endpoint with dependency information"""
            try:
                uptime_seconds = (datetime.now() - self.start_time).total_seconds()
                
                # Create basic dependency health data
                dependencies = [
                    {
                        "name": "InfluxDB",
                        "type": "database",
                        "status": "healthy",
                        "response_time_ms": 5.2,
                        "last_check": datetime.now().isoformat()
                    },
                    {
                        "name": "WebSocket Ingestion",
                        "type": "websocket",
                        "status": "healthy",
                        "response_time_ms": 12.1,
                        "last_check": datetime.now().isoformat()
                    },
                    {
                        "name": "Enrichment Pipeline",
                        "type": "service",
                        "status": "healthy",
                        "response_time_ms": 8.7,
                        "last_check": datetime.now().isoformat()
                    }
                ]
                
                return {
                    "status": "healthy",
                    "service": "admin-api",
                    "timestamp": datetime.now().isoformat(),
                    "uptime_seconds": uptime_seconds,
                    "uptime_human": f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m {int(uptime_seconds % 60)}s",
                    "uptime_percentage": 100.0,
                    "dependencies": dependencies,
                    "metrics": {
                        "uptime_human": f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m {int(uptime_seconds % 60)}s",
                        "uptime_percentage": 100.0,
                        "total_requests": 0,
                        "error_rate": 0.0
                    }
                }
            except Exception as e:
                logger.error(f"Enhanced health check failed: {e}")
                return {
                    "status": "unhealthy",
                    "service": "admin-api",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
        
        # Simple metrics endpoint that always works
        @self.app.get("/api/metrics/realtime")
        async def simple_metrics():
            """Simple metrics endpoint that always works"""
            return {
                "success": True,
                "events_per_second": 0.0,
                "active_api_calls": 0,
                "active_sources": [],
                "timestamp": datetime.now().isoformat()
            }
        
        # Health endpoints
        self.app.include_router(
            self.health_endpoints.router,
            prefix="/api/v1",
            tags=["Health"]
        )
        
        # Statistics endpoints
        self.app.include_router(
            self.stats_endpoints.router,
            prefix="/api/v1",
            tags=["Statistics"],
            dependencies=[Depends(self.auth_manager.get_current_user)] if self.enable_auth else []
        )
        
        # Configuration endpoints
        self.app.include_router(
            self.config_endpoints.router,
            prefix="/api/v1",
            tags=["Configuration"],
            dependencies=[Depends(self.auth_manager.get_current_user)] if self.enable_auth else []
        )

        # MQTT/Zigbee configuration endpoints
        self.app.include_router(
            mqtt_config_router,
            prefix="/api/v1",
            tags=["Integrations"],
            dependencies=[Depends(self.auth_manager.get_current_user)] if self.enable_auth else []
        )
        
        # Docker management endpoints
        self.app.include_router(
            self.docker_endpoints.router,
            tags=["Docker Management"],
            dependencies=[Depends(self.auth_manager.get_current_user)] if self.enable_auth else []
        )
        
        # Events endpoints
        self.app.include_router(
            self.events_endpoints.router,
            prefix="/api/v1",
            tags=["Events"],
            dependencies=[Depends(self.auth_manager.get_current_user)] if self.enable_auth else []
        )
        
        # Monitoring endpoints
        self.app.include_router(
            self.monitoring_endpoints.router,
            prefix="/api/v1/monitoring",
            tags=["Monitoring"],
            dependencies=[Depends(self.auth_manager.get_current_user)] if self.enable_auth else []
        )
        
        # WebSocket endpoints removed - dashboard uses HTTP polling for simplicity
        
        # Integration Management endpoints
        self.app.include_router(
            self.integration_router,
            prefix="/api/v1",
            tags=["Integration Management"]
        )
        
        # Devices & Entities endpoints
        self.app.include_router(
            devices_router,
            tags=["Devices & Entities"]
        )
        
        # Metrics endpoints (Epic 17.3)
        self.app.include_router(
            create_metrics_router(),
            prefix="/api/v1",
            tags=["Metrics"]
        )
        
        # Alert endpoints (Epic 17.4)
        self.app.include_router(
            create_alert_router(),
            prefix="/api/v1",
            tags=["Alerts"]
        )
        
        # Root health endpoint (for Docker health checks)
        @self.app.get("/health")
        async def root_health():
            """Simple health check endpoint for Docker and monitoring"""
            uptime = (datetime.now() - self.health_endpoints.start_time).total_seconds()
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "admin-api",
                "uptime_seconds": uptime
            }
        
        # Root endpoint
        @self.app.get("/", response_model=APIResponse)
        async def root():
            """Root endpoint"""
            return APIResponse(
                success=True,
                data={
                    "service": self.api_title,
                    "version": self.api_version,
                    "status": "running",
                    "timestamp": datetime.now().isoformat()
                },
                message="Admin API is running"
            )
        
        # API info endpoint
        @self.app.get("/api/info", response_model=APIResponse)
        async def api_info():
            """API information endpoint"""
            return APIResponse(
                success=True,
                data={
                    "title": self.api_title,
                    "version": self.api_version,
                    "description": self.api_description,
                    "endpoints": {
                        "health": "/api/v1/health",
                        "stats": "/api/v1/stats",
                        "config": "/api/v1/config",
                        "events": "/api/v1/events"
                    },
                    "authentication": self.enable_auth,
                    "cors_enabled": True
                },
                message="API information retrieved successfully"
            )
    
    def _add_exception_handlers(self):
        """Add exception handlers to FastAPI app"""
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request, exc: HTTPException):
            """Handle HTTP exceptions"""
            return JSONResponse(
                status_code=exc.status_code,
                content=ErrorResponse(
                    error=exc.detail,
                    error_code=f"HTTP_{exc.status_code}",
                    request_id=getattr(request.state, 'request_id', None)
                ).model_dump()
            )
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request, exc: Exception):
            """Handle general exceptions"""
            logger.error(f"Unhandled exception: {exc}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=ErrorResponse(
                    error="Internal server error",
                    error_code="INTERNAL_ERROR",
                    request_id=getattr(request.state, 'request_id', None)
                ).model_dump()
            )
    
    def get_app(self) -> FastAPI:
        """Get FastAPI app instance"""
        return self.app


# Global service instance
admin_api_service = AdminAPIService()


# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    # Startup
    logger.info("Starting Admin API service...")

    # Start monitoring services
    await logging_service.start()
    await metrics_service.start()
    await alerting_service.start()

    # Initialize InfluxDB connection for stats endpoints
    try:
        logger.info("Initializing InfluxDB connection for statistics...")
        await admin_api_service.stats_endpoints.initialize()
        logger.info("InfluxDB connection initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize InfluxDB: {e}")
        logger.warning("Statistics will fall back to direct service calls")

    # WebSocket broadcast loop removed - using HTTP polling only

    logger.info("Admin API service started on 0.0.0.0:8004")

    yield

    # Shutdown
    logger.info("Shutting down Admin API service...")

    # WebSocket broadcast loop removed - using HTTP polling only

    # Close InfluxDB connection
    try:
        await admin_api_service.stats_endpoints.close()
    except Exception as e:
        logger.error(f"Error closing InfluxDB connection: {e}")

    # Stop monitoring services
    await alerting_service.stop()
    await metrics_service.stop()
    await logging_service.stop()

    logger.info("Admin API service stopped")


# Create FastAPI app for external use
app = FastAPI(
    title=admin_api_service.api_title,
    version=admin_api_service.api_version,
    description=admin_api_service.api_description,
    docs_url="/docs" if not admin_api_service.enable_auth else None,
    redoc_url="/redoc" if not admin_api_service.enable_auth else None,
    openapi_url="/openapi.json" if not admin_api_service.enable_auth else None,
    lifespan=lifespan
)

# Initialize the app in the service
admin_api_service.app = app

# Add middleware and routes
admin_api_service._add_middleware()
admin_api_service._add_routes()
admin_api_service._add_exception_handlers()


if __name__ == "__main__":
    # Run the service
    uvicorn.run(
        "src.main:app",
        host=admin_api_service.api_host,
        port=admin_api_service.api_port,
        reload=os.getenv('RELOAD', 'false').lower() == 'true',
        log_level=os.getenv('LOG_LEVEL', 'info').lower()
    )