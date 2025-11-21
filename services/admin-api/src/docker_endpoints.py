"""
Docker Management Endpoints
REST API endpoints for Docker container management
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel

from shared.auth import AuthManager, User

from .api_key_service import APIKeyService
from .docker_service import DockerService

logger = logging.getLogger(__name__)

class ContainerResponse(BaseModel):
    """Container response model"""
    name: str
    service_name: str
    status: str
    image: str
    created: str
    ports: dict[str, str]
    is_project_container: bool

class ContainerOperationResponse(BaseModel):
    """Container operation response model"""
    success: bool
    message: str
    timestamp: str

class ContainerStatsResponse(BaseModel):
    """Container stats response model"""
    cpu_percent: float | None = None
    memory_usage: int | None = None
    memory_limit: int | None = None
    memory_percent: float | None = None
    timestamp: str

class APIKeyResponse(BaseModel):
    """API key response model"""
    service: str
    key_name: str
    status: str
    masked_key: str
    is_required: bool
    description: str

class APIKeyUpdateRequest(BaseModel):
    """API key update request model"""
    api_key: str

class APIKeyTestResponse(BaseModel):
    """API key test response model"""
    success: bool
    message: str
    timestamp: str

class DockerEndpoints:
    """Docker management endpoints"""

    def __init__(self, auth_manager: AuthManager):
        """Initialize Docker endpoints"""
        self.router = APIRouter(prefix="/api/v1/docker", tags=["docker"])
        self.docker_service = DockerService()
        self.api_key_service = APIKeyService()
        self.auth_manager = auth_manager
        self.allowed_services = set(self.docker_service.container_mapping.keys())
        self._add_routes()

    def _add_routes(self):
        """Add Docker management routes"""

        @self.router.get("/containers", response_model=list[ContainerResponse])
        async def list_containers(
            current_user: User = Depends(self.auth_manager.get_current_user),
        ):
            """List all project containers with their status"""
            try:
                containers = await self.docker_service.list_containers()
                logger.info(
                    "User %s requested container listing (%d containers)",
                    getattr(current_user, "username", "unknown"),
                    len(containers),
                )

                response = []
                for container in containers:
                    response.append(ContainerResponse(
                        name=container.name,
                        service_name=container.service_name,
                        status=container.status.value,
                        image=container.image,
                        created=container.created,
                        ports=container.ports,
                        is_project_container=container.is_project_container
                    ))

                return response

            except Exception as e:
                logger.error(f"Error listing containers: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to list containers: {str(e)}"
                ) from e from e

        @self.router.post("/containers/{service_name}/start", response_model=ContainerOperationResponse)
        async def start_container(
            service_name: str = Path(..., description="Service name to start"),
            current_user: User = Depends(self.auth_manager.get_current_user),
        ):
            """Start a Docker container"""
            try:
                self._ensure_allowed_service(service_name)
                success, message = await self.docker_service.start_container(service_name)
                logger.info(
                    "User %s requested start for %s: %s",
                    getattr(current_user, "username", "unknown"),
                    service_name,
                    message,
                )

                return ContainerOperationResponse(
                    success=success,
                    message=message,
                    timestamp=datetime.now().isoformat()
                )

            except Exception as e:
                logger.error(f"Error starting container {service_name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to start container: {str(e)}"
                ) from e from e

        @self.router.post("/containers/{service_name}/stop", response_model=ContainerOperationResponse)
        async def stop_container(
            service_name: str = Path(..., description="Service name to stop"),
            current_user: User = Depends(self.auth_manager.get_current_user),
        ):
            """Stop a Docker container"""
            try:
                self._ensure_allowed_service(service_name)
                success, message = await self.docker_service.stop_container(service_name)
                logger.warning(
                    "User %s requested stop for %s: %s",
                    getattr(current_user, "username", "unknown"),
                    service_name,
                    message,
                )

                return ContainerOperationResponse(
                    success=success,
                    message=message,
                    timestamp=datetime.now().isoformat()
                )

            except Exception as e:
                logger.error(f"Error stopping container {service_name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to stop container: {str(e)}"
                ) from e

        @self.router.post("/containers/{service_name}/restart", response_model=ContainerOperationResponse)
        async def restart_container(
            service_name: str = Path(..., description="Service name to restart"),
            current_user: User = Depends(self.auth_manager.get_current_user),
        ):
            """Restart a Docker container"""
            try:
                self._ensure_allowed_service(service_name)
                success, message = await self.docker_service.restart_container(service_name)
                logger.warning(
                    "User %s requested restart for %s: %s",
                    getattr(current_user, "username", "unknown"),
                    service_name,
                    message,
                )

                return ContainerOperationResponse(
                    success=success,
                    message=message,
                    timestamp=datetime.now().isoformat()
                )

            except Exception as e:
                logger.error(f"Error restarting container {service_name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to restart container: {str(e)}"
                ) from e

        @self.router.get("/containers/{service_name}/logs")
        async def get_container_logs(
            service_name: str = Path(..., description="Service name"),
            tail: int = Query(100, ge=1, le=500, description="Number of log lines to return"),
            current_user: User = Depends(self.auth_manager.get_current_user),
        ):
            """Get container logs"""
            try:
                self._ensure_allowed_service(service_name)
                logs = await self.docker_service.get_container_logs(service_name, tail)
                logger.info(
                    "User %s accessed logs for %s (tail=%s)",
                    getattr(current_user, "username", "unknown"),
                    service_name,
                    tail,
                )
                return {"logs": logs}

            except Exception as e:
                logger.error(f"Error getting logs for {service_name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get logs: {str(e)}"
                ) from e

        @self.router.get("/containers/{service_name}/stats", response_model=ContainerStatsResponse)
        async def get_container_stats(
            service_name: str = Path(..., description="Service name"),
            current_user: User = Depends(self.auth_manager.get_current_user),
        ):
            """Get container resource usage statistics"""
            try:
                self._ensure_allowed_service(service_name)
                stats = await self.docker_service.get_container_stats(service_name)

                if stats is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Container not found or not running"
                    )

                return ContainerStatsResponse(**stats)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting stats for {service_name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get stats: {str(e)}"
                ) from e

        # API Key Management Endpoints

        @self.router.get("/api-keys", response_model=list[APIKeyResponse])
        async def get_api_keys(
            current_user: User = Depends(self.auth_manager.get_current_user),
        ):
            """Get current API key status for all services"""
            try:
                api_keys = await self.api_key_service.get_api_keys()

                response = []
                for api_key in api_keys:
                    response.append(APIKeyResponse(
                        service=api_key.service,
                        key_name=api_key.key_name,
                        status=api_key.status.value,
                        masked_key=api_key.masked_key,
                        is_required=api_key.is_required,
                        description=api_key.description
                    ))

                return response

            except Exception as e:
                logger.error(f"Error getting API keys: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get API keys: {str(e)}"
                ) from e

        @self.router.put("/api-keys/{service}", response_model=ContainerOperationResponse)
        async def update_api_key(
            service: str = Path(..., description="Service name"),
            request: APIKeyUpdateRequest = None,
            current_user: User = Depends(self.auth_manager.get_current_user),
        ):
            """Update API key for a service"""
            try:
                if not request:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Request body is required"
                    )

                success, message = await self.api_key_service.update_api_key(service, request.api_key)
                logger.warning(
                    "User %s attempted to update API key for %s: %s",
                    getattr(current_user, "username", "unknown"),
                    service,
                    message,
                )

                return ContainerOperationResponse(
                    success=success,
                    message=message,
                    timestamp=datetime.now().isoformat()
                )

            except PermissionError as exc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=str(exc),
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error updating API key for {service}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to update API key: {str(e)}"
                )

        @self.router.post("/api-keys/{service}/test", response_model=APIKeyTestResponse)
        async def test_api_key(
            service: str = Path(..., description="Service name"),
            request: APIKeyUpdateRequest = None,
            current_user: User = Depends(self.auth_manager.get_current_user),
        ):
            """Test an API key without saving it"""
            try:
                if not request:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Request body is required"
                    )

                success, message = await self.api_key_service.test_api_key(service, request.api_key)
                logger.info(
                    "User %s tested API key for %s: %s",
                    getattr(current_user, "username", "unknown"),
                    service,
                    message,
                )

                return APIKeyTestResponse(
                    success=success,
                    message=message,
                    timestamp=datetime.now().isoformat()
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error testing API key for {service}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to test API key: {str(e)}"
                )

        @self.router.get("/api-keys/{service}/status")
        async def get_api_key_status(
            service: str = Path(..., description="Service name"),
            current_user: User = Depends(self.auth_manager.get_current_user),
        ):
            """Get API key status for a specific service"""
            try:
                status = self.api_key_service.get_api_key_status(service)
                return {"service": service, "status": status.value}

            except Exception as e:
                logger.error(f"Error getting API key status for {service}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get API key status: {str(e)}"
                )

    def _ensure_allowed_service(self, service_name: str) -> None:
        """Validate that the requested container belongs to the HomeIQ project."""
        if service_name not in self.allowed_services:
            logger.warning("Blocked Docker action against unknown service '%s'", service_name)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Service '{service_name}' is not managed by admin-api",
            )
