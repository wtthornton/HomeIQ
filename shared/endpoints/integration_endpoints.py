"""
Integration Management Endpoints
Shared integration endpoints for admin-api and data-api.
"""

import logging
from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from shared.endpoints.service_controller import service_controller

logger = logging.getLogger(__name__)


# Request/Response Models
class ConfigUpdateRequest(BaseModel):
    """Configuration update request"""
    settings: Dict[str, str]


class ServiceActionResponse(BaseModel):
    """Service action response"""
    success: bool
    service: str
    message: str
    error: str | None = None


class ConfigResponse(BaseModel):
    """Configuration response"""
    service: str
    settings: Dict[str, str]
    template: Dict[str, Dict[str, str]]


class ServiceStatusResponse(BaseModel):
    """Service status response"""
    service: str
    running: bool
    status: str
    timestamp: str | None = None
    error: str | None = None


def create_integration_router(config_manager: Any) -> APIRouter:
    """
    Create integration router with service-specific config_manager.
    
    Args:
        config_manager: Service-specific config manager instance
        
    Returns:
        APIRouter with integration endpoints
    """
    router = APIRouter()

    # Configuration Endpoints

    @router.get("/integrations", tags=["Integrations"])
    def list_integrations():
        """List all available integrations"""
        try:
            services = config_manager.list_services()
            return {
                "services": services,
                "count": len(services)
            }
        except Exception as e:
            logger.error(f"Error listing integrations: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @router.get("/integrations/{service}/config", tags=["Integrations"])
    def get_integration_config(service: str):
        """Get configuration for a service"""
        try:
            config = config_manager.read_config(service)
            template = config_manager.get_config_template(service)
            
            return {
                "service": service,
                "settings": config,
                "template": template
            }
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration not found for service: {service}"
            )
        except Exception as e:
            logger.error(f"Error reading config for {service}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @router.put("/integrations/{service}/config", tags=["Integrations"])
    def update_integration_config(service: str, update: ConfigUpdateRequest):
        """Update configuration for a service"""
        try:
            # Validate configuration
            validation = config_manager.validate_config(service, update.settings)
            
            if not validation["valid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Configuration validation failed",
                        "errors": validation["errors"],
                        "warnings": validation["warnings"]
                    }
                )
            
            # Update configuration
            updated_config = config_manager.write_config(service, update.settings)
            
            return {
                "success": True,
                "service": service,
                "message": "Configuration updated successfully. Restart service to apply changes.",
                "restart_required": True,
                "settings": updated_config,
                "warnings": validation["warnings"]
            }
        
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration not found for service: {service}"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating config for {service}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @router.post("/integrations/{service}/validate", tags=["Integrations"])
    def validate_integration_config(service: str, config: ConfigUpdateRequest):
        """Validate configuration without saving"""
        try:
            validation = config_manager.validate_config(service, config.settings)
            return validation
        except Exception as e:
            logger.error(f"Error validating config for {service}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    # Service Control Endpoints

    @router.get("/services", tags=["Services"])
    def list_services():
        """List all services with their status"""
        try:
            services = service_controller.list_services()
            running_count = sum(1 for s in services if s["running"])
            
            return {
                "services": services,
                "total": len(services),
                "running": running_count,
                "stopped": len(services) - running_count
            }
        except Exception as e:
            logger.error(f"Error listing services: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @router.get("/services/{service}/status", tags=["Services"])
    def get_service_status(service: str):
        """Get status of a specific service"""
        try:
            status_info = service_controller.get_service_status(service)
            return status_info
        except Exception as e:
            logger.error(f"Error getting status for {service}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @router.post("/services/{service}/restart", tags=["Services"])
    def restart_service(service: str):
        """Restart a service"""
        try:
            result = service_controller.restart_service(service)
            
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("error", "Failed to restart service")
                )
            
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error restarting {service}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @router.post("/services/{service}/stop", tags=["Services"])
    def stop_service(service: str):
        """Stop a service"""
        try:
            result = service_controller.stop_service(service)
            
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("error", "Failed to stop service")
                )
            
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error stopping {service}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @router.post("/services/{service}/start", tags=["Services"])
    def start_service(service: str):
        """Start a service"""
        try:
            result = service_controller.start_service(service)
            
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("error", "Failed to start service")
                )
            
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error starting {service}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @router.post("/services/restart-all", tags=["Services"])
    def restart_all_services():
        """Restart all services"""
        try:
            result = service_controller.restart_all_services()
            
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("error", "Failed to restart all services")
                )
            
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error restarting all services: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    return router
