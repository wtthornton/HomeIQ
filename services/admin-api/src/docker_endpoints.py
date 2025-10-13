"""
Docker Management Endpoints
REST API endpoints for Docker container management
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Query, Path
from pydantic import BaseModel

from .docker_service import DockerService, ContainerInfo, ContainerStatus
from .api_key_service import APIKeyService, APIKeyInfo, APIKeyStatus

logger = logging.getLogger(__name__)

class ContainerResponse(BaseModel):
    """Container response model"""
    name: str
    service_name: str
    status: str
    image: str
    created: str
    ports: Dict[str, str]
    is_project_container: bool

class ContainerOperationResponse(BaseModel):
    """Container operation response model"""
    success: bool
    message: str
    timestamp: str

class ContainerStatsResponse(BaseModel):
    """Container stats response model"""
    cpu_percent: Optional[float] = None
    memory_usage: Optional[int] = None
    memory_limit: Optional[int] = None
    memory_percent: Optional[float] = None
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
    
    def __init__(self):
        """Initialize Docker endpoints"""
        self.router = APIRouter(prefix="/api/v1/docker", tags=["docker"])
        self.docker_service = DockerService()
        self.api_key_service = APIKeyService()
        self._add_routes()
    
    def _add_routes(self):
        """Add Docker management routes"""
        
        @self.router.get("/containers", response_model=List[ContainerResponse])
        async def list_containers():
            """List all project containers with their status"""
            try:
                containers = await self.docker_service.list_containers()
                
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
                )
        
        @self.router.post("/containers/{service_name}/start", response_model=ContainerOperationResponse)
        async def start_container(
            service_name: str = Path(..., description="Service name to start")
        ):
            """Start a Docker container"""
            try:
                success, message = await self.docker_service.start_container(service_name)
                
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
                )
        
        @self.router.post("/containers/{service_name}/stop", response_model=ContainerOperationResponse)
        async def stop_container(
            service_name: str = Path(..., description="Service name to stop")
        ):
            """Stop a Docker container"""
            try:
                success, message = await self.docker_service.stop_container(service_name)
                
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
                )
        
        @self.router.post("/containers/{service_name}/restart", response_model=ContainerOperationResponse)
        async def restart_container(
            service_name: str = Path(..., description="Service name to restart")
        ):
            """Restart a Docker container"""
            try:
                success, message = await self.docker_service.restart_container(service_name)
                
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
                )
        
        @self.router.get("/containers/{service_name}/logs")
        async def get_container_logs(
            service_name: str = Path(..., description="Service name"),
            tail: int = Query(100, description="Number of log lines to return")
        ):
            """Get container logs"""
            try:
                logs = await self.docker_service.get_container_logs(service_name, tail)
                return {"logs": logs}
                
            except Exception as e:
                logger.error(f"Error getting logs for {service_name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get logs: {str(e)}"
                )
        
        @self.router.get("/containers/{service_name}/stats", response_model=ContainerStatsResponse)
        async def get_container_stats(
            service_name: str = Path(..., description="Service name")
        ):
            """Get container resource usage statistics"""
            try:
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
                )
        
        # API Key Management Endpoints
        
        @self.router.get("/api-keys", response_model=List[APIKeyResponse])
        async def get_api_keys():
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
                )
        
        @self.router.put("/api-keys/{service}", response_model=ContainerOperationResponse)
        async def update_api_key(
            service: str = Path(..., description="Service name"),
            request: APIKeyUpdateRequest = None
        ):
            """Update API key for a service"""
            try:
                if not request:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Request body is required"
                    )
                
                success, message = await self.api_key_service.update_api_key(service, request.api_key)
                
                return ContainerOperationResponse(
                    success=success,
                    message=message,
                    timestamp=datetime.now().isoformat()
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
            request: APIKeyUpdateRequest = None
        ):
            """Test an API key without saving it"""
            try:
                if not request:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Request body is required"
                    )
                
                success, message = await self.api_key_service.test_api_key(service, request.api_key)
                
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
            service: str = Path(..., description="Service name")
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
