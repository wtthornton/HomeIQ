"""
Main FastAPI Application Entry Point
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.execution_router import router as execution_router
from .api.health_router import router as health_router
from .api.observability_router import router as observability_router
from .api.spec_router import router as spec_router
from .capability.capability_graph import CapabilityGraph
from .clients.ha_rest_client import HARestClient
from .clients.ha_websocket_client import HAWebSocketClient
from .config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="HomeIQ API Automation Edge Service",
    description="API-driven automation engine for HomeIQ",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(spec_router)
app.include_router(execution_router)
app.include_router(observability_router)

# Global components
rest_client: HARestClient = None
websocket_client: HAWebSocketClient = None
capability_graph: CapabilityGraph = None


@app.on_event("startup")
async def startup():
    """Initialize services on startup"""
    global rest_client, websocket_client, capability_graph
    
    logger.info("Starting API Automation Edge Service")
    
    # Initialize REST client
    rest_client = HARestClient()
    
    # Initialize WebSocket client
    websocket_client = HAWebSocketClient()
    await websocket_client.connect()
    
    # Initialize capability graph
    capability_graph = CapabilityGraph(rest_client, websocket_client)
    await capability_graph.initialize()
    await capability_graph.start(websocket_client)
    
    logger.info("API Automation Edge Service started")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    global websocket_client, capability_graph
    
    logger.info("Shutting down API Automation Edge Service")
    
    if capability_graph:
        await capability_graph.stop()
    
    if websocket_client:
        await websocket_client.disconnect()
    
    logger.info("API Automation Edge Service stopped")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)
