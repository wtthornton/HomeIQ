"""
Docker Management Service
Handles Docker container operations for the HA Ingestor system
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

try:
    import docker
except ImportError:  # pragma: no cover - optional dependency
    docker = None

if docker:
    DockerNotFoundError = docker.errors.NotFound
else:
    class DockerNotFoundError(Exception):
        """Fallback error used when docker SDK is unavailable."""
        pass

logger = logging.getLogger(__name__)

class ContainerStatus(Enum):
    """Container status enumeration"""
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"
    UNKNOWN = "unknown"

@dataclass
class ContainerInfo:
    """Container information model"""
    name: str
    service_name: str
    status: ContainerStatus
    image: str
    created: str
    ports: dict[str, str]
    labels: dict[str, str]
    is_project_container: bool = True

class DockerService:
    """Docker container management service"""

    def __init__(self):
        """Initialize Docker service"""
        if docker is None:
            self.client = None
            logger.warning("Docker SDK not installed - running in mock mode")
        else:
            try:
                docker_host = os.getenv('DOCKER_HOST', 'unix:///var/run/docker.sock')

                if docker_host.startswith('unix://'):
                    try:
                        self.client = docker.from_env()
                        self.client.ping()
                        logger.info("Docker service initialized successfully with default connection")
                    except Exception as e1:
                        logger.warning(f"Default Docker connection failed: {e1}")
                        try:
                            socket_path = docker_host.replace('unix://', '')
                            self.client = docker.DockerClient(base_url=f'unix://{socket_path}')
                            self.client.ping()
                            logger.info("Docker service initialized successfully with explicit socket path")
                        except Exception as e2:
                            logger.error(f"Explicit socket connection also failed: {e2}")
                            self.client = None
                            logger.warning("Docker client disabled - running in mock mode")
                else:
                    self.client = docker.DockerClient(base_url=docker_host)
                    self.client.ping()
                    logger.info("Docker service initialized successfully with TCP connection")

            except Exception as e:
                logger.error(f"Failed to initialize Docker service: {e}")
                self.client = None
                logger.warning("Docker client disabled - running in mock mode")

        # Container name mapping - maps service names to Docker container names
        self.container_mapping = {
            'websocket-ingestion': 'homeiq-websocket',
            'admin-api': 'homeiq-admin',
            'health-dashboard': 'homeiq-dashboard',
            'influxdb': 'homeiq-influxdb',
            'weather-api': 'homeiq-weather-api',
            'carbon-intensity-service': 'homeiq-carbon-intensity',
            'electricity-pricing-service': 'homeiq-electricity-pricing',
            'air-quality-service': 'homeiq-air-quality',
            'calendar-service': 'homeiq-calendar',
            'smart-meter-service': 'homeiq-smart-meter',
            'data-retention': 'homeiq-data-retention'
        }

        # Project label for filtering containers
        self.project_label = "com.docker.compose.project=homeiq"

    async def list_containers(self) -> list[ContainerInfo]:
        """
        List all project containers with their status
        
        Returns:
            List of ContainerInfo objects
        """
        try:
            if self.client is None:
                # Return mock data when Docker is not available
                return await self._get_mock_containers()

            # Get all containers (including stopped ones)
            containers = await asyncio.to_thread(self.client.containers.list, all=True)

            project_containers = []

            for container in containers:
                # Check if this is a project container
                labels = container.labels or {}
                project_name = labels.get('com.docker.compose.project')

                if project_name == 'homeiq':
                    # Map container name to service name
                    service_name = self._get_service_name_from_container(container.name)

                    # Get container status
                    status = self._get_container_status(container)

                    # Get port mappings
                    ports = {}
                    if container.attrs.get('NetworkSettings', {}).get('Ports'):
                        for container_port, host_bindings in container.attrs['NetworkSettings']['Ports'].items():
                            if host_bindings:
                                ports[container_port] = host_bindings[0]['HostPort']

                    container_info = ContainerInfo(
                        name=container.name,
                        service_name=service_name,
                        status=status,
                        image=container.image.tags[0] if container.image.tags else container.image.short_id,
                        created=container.attrs['Created'],
                        ports=ports,
                        labels=labels,
                        is_project_container=True
                    )

                    project_containers.append(container_info)

            logger.info(f"Found {len(project_containers)} project containers")
            return project_containers

        except Exception as e:
            logger.error(f"Error listing containers: {e}")
            # Return mock data on error
            return await self._get_mock_containers()

    async def start_container(self, service_name: str) -> tuple[bool, str]:
        """
        Start a Docker container
        
        Args:
            service_name: Service name to start
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if self.client is None:
                # Mock response when Docker is not available
                return True, f"Mock: Container {service_name} started successfully (Docker not available)"

            container_name = self._get_container_name(service_name)
            if not container_name:
                return False, f"Unknown service: {service_name}"

            container = await asyncio.to_thread(self.client.containers.get, container_name)

            if container.status == 'running':
                return True, f"Container {container_name} is already running"

            # Start the container
            await asyncio.to_thread(container.start)

            # Wait a moment for startup
            await asyncio.sleep(2)

            # Check if it started successfully
            await asyncio.to_thread(container.reload)
            if container.status == 'running':
                logger.info(f"Successfully started container: {container_name}")
                return True, f"Container {container_name} started successfully"
            else:
                logger.warning(f"Container {container_name} may not have started properly")
                return False, f"Container {container_name} failed to start properly"

        except DockerNotFoundError:
            logger.error(f"Container not found for service: {service_name}")
            return False, f"Container not found for service: {service_name}"
        except Exception as e:
            logger.error(f"Error starting container {service_name}: {e}")
            return False, f"Error starting container: {str(e)}"

    async def stop_container(self, service_name: str) -> tuple[bool, str]:
        """
        Stop a Docker container

        Args:
            service_name: Service name to stop

        Returns:
            Tuple of (success, message)
        """
        try:
            if self.client is None:
                # Mock response when Docker is not available
                return True, f"Mock: Container {service_name} stopped successfully (Docker not available)"

            container_name = self._get_container_name(service_name)
            if not container_name:
                return False, f"Unknown service: {service_name}"

            container = await asyncio.to_thread(self.client.containers.get, container_name)

            if container.status != 'running':
                return True, f"Container {container_name} is not running"

            # Stop the container
            await asyncio.to_thread(container.stop, timeout=10)

            # Wait a moment for shutdown
            await asyncio.sleep(2)

            # Check if it stopped successfully
            await asyncio.to_thread(container.reload)
            if container.status != 'running':
                logger.info(f"Successfully stopped container: {container_name}")
                return True, f"Container {container_name} stopped successfully"
            else:
                logger.warning(f"Container {container_name} may not have stopped properly")
                return False, f"Container {container_name} failed to stop properly"

        except DockerNotFoundError:
            logger.error(f"Container not found for service: {service_name}")
            return False, f"Container not found for service: {service_name}"
        except Exception as e:
            logger.error(f"Error stopping container {service_name}: {e}")
            return False, f"Error stopping container: {str(e)}"

    async def restart_container(self, service_name: str) -> tuple[bool, str]:
        """
        Restart a Docker container

        Args:
            service_name: Service name to restart

        Returns:
            Tuple of (success, message)
        """
        try:
            if self.client is None:
                # Mock response when Docker is not available
                return True, f"Mock: Container {service_name} restarted successfully (Docker not available)"

            container_name = self._get_container_name(service_name)
            if not container_name:
                return False, f"Unknown service: {service_name}"

            container = await asyncio.to_thread(self.client.containers.get, container_name)

            # Restart the container
            await asyncio.to_thread(container.restart, timeout=10)

            # Wait a moment for restart
            await asyncio.sleep(3)

            # Check if it restarted successfully
            await asyncio.to_thread(container.reload)
            if container.status == 'running':
                logger.info(f"Successfully restarted container: {container_name}")
                return True, f"Container {container_name} restarted successfully"
            else:
                logger.warning(f"Container {container_name} may not have restarted properly")
                return False, f"Container {container_name} failed to restart properly"

        except DockerNotFoundError:
            logger.error(f"Container not found for service: {service_name}")
            return False, f"Container not found for service: {service_name}"
        except Exception as e:
            logger.error(f"Error restarting container {service_name}: {e}")
            return False, f"Error restarting container: {str(e)}"

    async def get_container_logs(self, service_name: str, tail: int = 100) -> str:
        """
        Get container logs
        
        Args:
            service_name: Service name
            tail: Number of lines to return
            
        Returns:
            Container logs as string
        """
        try:
            if self.client is None:
                # Mock logs when Docker is not available
                return f"Mock logs for {service_name}:\n" + \
                       f"{datetime.now().isoformat()} INFO: Service {service_name} is running\n" + \
                       f"{datetime.now().isoformat()} INFO: Mock mode - Docker not available\n" + \
                       f"{datetime.now().isoformat()} INFO: Container would be running normally\n"

            container_name = self._get_container_name(service_name)
            if not container_name:
                return f"Unknown service: {service_name}"

            container = await asyncio.to_thread(self.client.containers.get, container_name)
            logs_bytes = await asyncio.to_thread(container.logs, tail=tail, timestamps=True)
            logs = logs_bytes.decode('utf-8')

            return logs

        except DockerNotFoundError:
            return f"Container not found for service: {service_name}"
        except Exception as e:
            logger.error(f"Error getting logs for {service_name}: {e}")
            return f"Error getting logs: {str(e)}"

    def _get_container_name(self, service_name: str) -> str | None:
        """Get Docker container name from service name"""
        return self.container_mapping.get(service_name)

    def _get_service_name_from_container(self, container_name: str) -> str:
        """Get service name from Docker container name"""
        for service, container in self.container_mapping.items():
            if container == container_name:
                return service
        return container_name

    def _get_container_status(self, container) -> ContainerStatus:
        """Get container status as enum"""
        status = container.status.lower()

        if status == 'running':
            return ContainerStatus.RUNNING
        elif status == 'exited':
            return ContainerStatus.STOPPED
        elif status in ['created', 'restarting']:
            return ContainerStatus.STARTING
        else:
            return ContainerStatus.UNKNOWN

    async def get_container_stats(self, service_name: str) -> dict | None:
        """
        Get container resource usage statistics
        
        Args:
            service_name: Service name
            
        Returns:
            Container stats or None if not running
        """
        try:
            if self.client is None:
                # Return mock stats when Docker is not available
                return {
                    'cpu_percent': 15.5,
                    'memory_usage': 256 * 1024 * 1024,  # 256MB
                    'memory_limit': 512 * 1024 * 1024,  # 512MB
                    'memory_percent': 50.0,
                    'timestamp': datetime.now().isoformat()
                }

            container_name = self._get_container_name(service_name)
            if not container_name:
                return None

            container = await asyncio.to_thread(self.client.containers.get, container_name)

            if container.status != 'running':
                return None

            stats = await asyncio.to_thread(container.stats, stream=False)

            # Calculate CPU usage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
            cpu_percent = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0

            # Memory usage
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            memory_percent = (memory_usage / memory_limit) * 100.0

            return {
                'cpu_percent': round(cpu_percent, 2),
                'memory_usage': memory_usage,
                'memory_limit': memory_limit,
                'memory_percent': round(memory_percent, 2),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting stats for {service_name}: {e}")
            return None

    async def _get_mock_containers(self) -> list[ContainerInfo]:
        """
        Get mock container data when Docker is not available
        
        Returns:
            List of mock ContainerInfo objects
        """
        mock_containers = []

        # Create mock data for all known services
        for service_name, container_name in self.container_mapping.items():
            # Mock different statuses for variety
            if service_name in ['influxdb', 'websocket-ingestion']:
                status = ContainerStatus.RUNNING
                ports = {'8086/tcp': '8086'} if service_name == 'influxdb' else {'8001/tcp': '8001'} if service_name == 'websocket-ingestion' else {'8002/tcp': '8002'}
            elif service_name in ['weather-api', 'carbon-intensity-service']:
                status = ContainerStatus.STOPPED
                ports = {}
            else:
                status = ContainerStatus.RUNNING
                ports = {}

            container_info = ContainerInfo(
                name=container_name,
                service_name=service_name,
                status=status,
                image=f"homeiq-{service_name}:latest",
                created="2024-01-01T00:00:00Z",
                ports=ports,
                labels={'com.docker.compose.project': 'homeiq'},
                is_project_container=True
            )

            mock_containers.append(container_info)

        logger.info(f"Returning {len(mock_containers)} mock containers")
        return mock_containers
