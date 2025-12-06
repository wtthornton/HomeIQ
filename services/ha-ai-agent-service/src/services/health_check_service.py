"""
Comprehensive Health Check Service

Verifies all dependencies and services in a single call.
"""

import logging
from typing import Any

from ..clients.data_api_client import DataAPIClient
from ..clients.device_intelligence_client import DeviceIntelligenceClient
from ..clients.ha_client import HomeAssistantClient
from ..config import Settings
from ..database import get_session
from ..services.context_builder import ContextBuilder
from sqlalchemy import text

logger = logging.getLogger(__name__)


class HealthCheckService:
    """Service for comprehensive health checks"""

    def __init__(
        self,
        settings: Settings,
        context_builder: ContextBuilder | None = None
    ):
        """
        Initialize health check service.

        Args:
            settings: Application settings
            context_builder: Context builder instance (optional)
        """
        self.settings = settings
        self.context_builder = context_builder
        self.ha_client = HomeAssistantClient(
            ha_url=settings.ha_url,
            access_token=settings.ha_token,
            timeout=5  # Short timeout for health checks
        )
        self.data_api_client = DataAPIClient(base_url=settings.data_api_url)
        self.device_intelligence_client = DeviceIntelligenceClient(settings)

    async def check_database(self) -> dict[str, Any]:
        """Check database connectivity"""
        try:
            async for session in get_session():
                result = await session.execute(text("SELECT 1"))
                result.scalar()
                return {
                    "status": "healthy",
                    "message": "Database connection successful"
                }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}"
            }

    async def check_home_assistant(self) -> dict[str, Any]:
        """Check Home Assistant connection"""
        try:
            # Try to fetch a small number of states (lightweight check)
            states = await self.ha_client.get_states()
            if states is not None:
                return {
                    "status": "healthy",
                    "message": "Home Assistant connection successful",
                    "entities_count": len(states)
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Home Assistant returned empty response"
                }
        except Exception as e:
            logger.error(f"Home Assistant health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Home Assistant connection failed: {str(e)}"
            }

    async def check_data_api(self) -> dict[str, Any]:
        """Check Data API connection"""
        try:
            # Try to fetch a small number of entities (lightweight)
            entities = await self.data_api_client.fetch_entities(limit=1)
            return {
                "status": "healthy",
                "message": "Data API connection successful",
                "entities_available": True
            }
        except Exception as e:
            logger.error(f"Data API health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Data API connection failed: {str(e)}"
            }

    async def check_device_intelligence(self) -> dict[str, Any]:
        """Check Device Intelligence Service connection"""
        try:
            # Try to get device mapping status (lightweight check)
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.device_intelligence_client.base_url}/api/device-mappings/status")
                response.raise_for_status()
                data = response.json()
                return {
                    "status": "healthy",
                    "message": "Device Intelligence Service connection successful",
                    "handler_count": data.get("handler_count", 0)
                }
        except Exception as e:
            logger.error(f"Device Intelligence health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Device Intelligence Service connection failed: {str(e)}"
            }

    async def check_openai(self) -> dict[str, Any]:
        """Check OpenAI configuration (doesn't make API call, just checks config)"""
        if not self.settings.openai_api_key:
            return {
                "status": "warning",
                "message": "OpenAI API key not configured"
            }
        return {
            "status": "healthy",
            "message": "OpenAI API key configured",
            "model": self.settings.openai_model
        }

    async def check_context_builder(self) -> dict[str, Any]:
        """Check context builder services"""
        if not self.context_builder:
            return {
                "status": "unhealthy",
                "message": "Context builder not initialized"
            }

        try:
            # Check if context builder is initialized
            if not self.context_builder._initialized:
                return {
                    "status": "unhealthy",
                    "message": "Context builder not initialized"
                }

            # Try to build a minimal context (this will test all services)
            context = await self.context_builder.build_context()
            
            # Check which components are available
            components = {
                "entity_inventory": "ENTITY INVENTORY:" in context,
                "areas": "AREAS:" in context,
                "services": "AVAILABLE SERVICES:" in context,
                "capability_patterns": "DEVICE CAPABILITY PATTERNS:" in context,
                "helpers_scenes": "HELPERS & SCENES:" in context
            }

            available_count = sum(1 for v in components.values() if v)
            total_count = len(components)

            return {
                "status": "healthy" if available_count > 0 else "degraded",
                "message": f"Context builder operational ({available_count}/{total_count} components available)",
                "components": components
            }
        except Exception as e:
            logger.error(f"Context builder health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Context builder check failed: {str(e)}"
            }

    async def comprehensive_health_check(self) -> dict[str, Any]:
        """
        Perform comprehensive health check of all dependencies.

        Returns:
            Dictionary with overall status and individual component statuses
        """
        checks = {
            "database": await self.check_database(),
            "home_assistant": await self.check_home_assistant(),
            "data_api": await self.check_data_api(),
            "device_intelligence": await self.check_device_intelligence(),
            "openai": await self.check_openai(),
            "context_builder": await self.check_context_builder()
        }

        # Determine overall status
        statuses = [check["status"] for check in checks.values()]
        
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "degraded" in statuses:
            overall_status = "degraded"
        elif "warning" in statuses and all(s in ["healthy", "warning"] for s in statuses):
            overall_status = "healthy"  # Warnings don't make it unhealthy
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "service": "ha-ai-agent-service",
            "version": "1.0.0",
            "checks": checks,
            "summary": {
                "total": len(checks),
                "healthy": sum(1 for c in checks.values() if c["status"] == "healthy"),
                "degraded": sum(1 for c in checks.values() if c["status"] == "degraded"),
                "unhealthy": sum(1 for c in checks.values() if c["status"] == "unhealthy"),
                "warnings": sum(1 for c in checks.values() if c["status"] == "warning")
            }
        }

    async def close(self):
        """Close health check service resources"""
        if self.ha_client:
            await self.ha_client.close()
        if self.data_api_client:
            await self.data_api_client.close()
        # DeviceIntelligenceClient doesn't need explicit close (uses httpx context managers)

