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


class DockerUnavailableError(Exception):
    """The docker socket is unusable.

    Callers must answer 503 — fabricated 200s made mock mode look like a
    working fleet (TAP-5999)."""



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
            logger.warning("Docker SDK not installed - docker routes will answer 503")
        else:
            try:
                docker_host = os.getenv("DOCKER_HOST", "unix:///var/run/docker.sock")

                if docker_host.startswith("unix://"):
                    try:
                        self.client = docker.from_env()
                        self.client.ping()
                        logger.info(
                            "Docker service initialized successfully with default connection"
                        )
                    except Exception as e1:
                        logger.warning(f"Default Docker connection failed: {e1}")
                        try:
                            socket_path = docker_host.replace("unix://", "")
                            self.client = docker.DockerClient(base_url=f"unix://{socket_path}")
                            self.client.ping()
                            logger.info(
                                "Docker service initialized successfully with explicit socket path"
                            )
                        except Exception as e2:
                            logger.error(f"Explicit socket connection also failed: {e2}")
                            self.client = None
                            logger.warning("Docker client disabled - docker routes will answer 503")
                else:
                    self.client = docker.DockerClient(base_url=docker_host)
                    self.client.ping()
                    logger.info("Docker service initialized successfully with TCP connection")

            except Exception as e:
                logger.error(f"Failed to initialize Docker service: {e}")
                self.client = None
                logger.warning("Docker client disabled - docker routes will answer 503")

        # Container name mapping - maps service names to Docker container names
        self.container_mapping = {
            "websocket-ingestion": "homeiq-websocket",
            "admin-api": "homeiq-admin",
            "health-dashboard": "homeiq-dashboard",
            "influxdb": "homeiq-influxdb",
            "weather-api": "homeiq-weather-api",
            "electricity-pricing-service": "homeiq-electricity-pricing",
            "air-quality-service": "homeiq-air-quality",
            "calendar-service": "homeiq-calendar",
            "smart-meter-service": "homeiq-smart-meter",
            "data-retention": "homeiq-data-retention",
            "data-api": "homeiq-data-api",
        }

    async def list_containers(self) -> list[ContainerInfo]:
        """
        List all project containers with their status

        Returns:
            List of ContainerInfo objects
        """
        if self.client is None:
            raise DockerUnavailableError("docker socket unavailable")

        try:

            # Get all containers (including stopped ones)
            containers = await asyncio.to_thread(self.client.containers.list, all=True)

            project_containers = []

            for container in containers:
                # Check if this is a project container
                labels = container.labels or {}
                project_name = labels.get("com.docker.compose.project")

                # Each domain compose sets its own project name
                # (homeiq-core-platform, homeiq-device-management, ...) —
                # an exact "homeiq" match returned zero containers the
                # moment mock mode stopped papering over it (TAP-5999).
                if project_name and project_name.startswith("homeiq"):
                    # Map container name to service name using container_mapping
                    # (which aligns with health API keys). Fall back to the
                    # Compose service label when no mapping entry exists.
                    service_name = self._get_service_name_from_container(
                        container.name,
                        compose_service=labels.get("com.docker.compose.service"),
                    )

                    # Get container status
                    status = self._get_container_status(container)

                    # Get port mappings
                    ports = {}
                    if container.attrs.get("NetworkSettings", {}).get("Ports"):
                        for container_port, host_bindings in container.attrs["NetworkSettings"][
                            "Ports"
                        ].items():
                            if host_bindings:
                                ports[container_port] = host_bindings[0]["HostPort"]

                    container_info = ContainerInfo(
                        name=container.name,
                        service_name=service_name,
                        status=status,
                        # From attrs, not container.image: the lazy image
                        # lookup 404s for a container whose image tag was
                        # rebuilt out from under it, failing the whole
                        # listing (surfaced by TAP-5999).
                        image=(
                            container.attrs.get("Config", {}).get("Image")
                            or container.attrs.get("Image", "")[:19]
                        ),
                        created=container.attrs["Created"],
                        ports=ports,
                        labels=labels,
                        is_project_container=True,
                    )

                    project_containers.append(container_info)

            logger.info(f"Found {len(project_containers)} project containers")
            return project_containers

        except DockerUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Error listing containers: {e}")
            raise

    async def start_container(self, service_name: str) -> tuple[bool, str]:
        """
        Start a Docker container

        Args:
            service_name: Service name to start

        Returns:
            Tuple of (success, message)
        """
        if self.client is None:
            raise DockerUnavailableError("docker socket unavailable")

        try:

            container_name = self._get_container_name(service_name)
            if not container_name:
                return False, f"Unknown service: {service_name}"

            container = await asyncio.to_thread(self.client.containers.get, container_name)

            if container.status == "running":
                return True, f"Container {container_name} is already running"

            # Start the container
            await asyncio.to_thread(container.start)

            # Wait a moment for startup
            await asyncio.sleep(2)

            # Check if it started successfully
            await asyncio.to_thread(container.reload)
            if container.status == "running":
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
        if self.client is None:
            raise DockerUnavailableError("docker socket unavailable")

        try:

            container_name = self._get_container_name(service_name)
            if not container_name:
                return False, f"Unknown service: {service_name}"

            container = await asyncio.to_thread(self.client.containers.get, container_name)

            if container.status != "running":
                return True, f"Container {container_name} is not running"

            # Stop the container
            await asyncio.to_thread(container.stop, timeout=10)

            # Wait a moment for shutdown
            await asyncio.sleep(2)

            # Check if it stopped successfully
            await asyncio.to_thread(container.reload)
            if container.status != "running":
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
        if self.client is None:
            raise DockerUnavailableError("docker socket unavailable")

        try:

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
            if container.status == "running":
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
        if self.client is None:
            raise DockerUnavailableError("docker socket unavailable")

        try:

            container_name = self._get_container_name(service_name)
            if not container_name:
                return f"Unknown service: {service_name}"

            container = await asyncio.to_thread(self.client.containers.get, container_name)
            logs_bytes = await asyncio.to_thread(container.logs, tail=tail, timestamps=True)
            logs = logs_bytes.decode("utf-8")

            return logs

        except DockerNotFoundError:
            return f"Container not found for service: {service_name}"
        except Exception as e:
            logger.error(f"Error getting logs for {service_name}: {e}")
            return f"Error getting logs: {str(e)}"

    def _get_container_name(self, service_name: str) -> str | None:
        """Get Docker container name from service name"""
        return self.container_mapping.get(service_name)

    def _get_service_name_from_container(
        self,
        container_name: str,
        compose_service: str | None = None,
    ) -> str:
        """Get service name from Docker container name.

        Priority:
        1. Reverse lookup in container_mapping (names aligned with health API).
        2. Compose service label (``com.docker.compose.service``).
        3. Raw container name (last resort).
        """
        for service, mapped_name in self.container_mapping.items():
            if mapped_name == container_name:
                return service
        if compose_service:
            return compose_service
        return container_name

    def _get_container_status(self, container) -> ContainerStatus:
        """Get container status as enum"""
        status = container.status.lower()

        if status == "running":
            return ContainerStatus.RUNNING
        elif status == "exited":
            return ContainerStatus.STOPPED
        elif status in ["created", "restarting"]:
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
        if self.client is None:
            raise DockerUnavailableError("docker socket unavailable")

        try:

            container_name = self._get_container_name(service_name)
            if not container_name:
                return None

            container = await asyncio.to_thread(self.client.containers.get, container_name)

            if container.status != "running":
                return None

            stats = await asyncio.to_thread(container.stats, stream=False)

            # Calculate CPU usage
            cpu_delta = (
                stats["cpu_stats"]["cpu_usage"]["total_usage"]
                - stats["precpu_stats"]["cpu_usage"]["total_usage"]
            )
            system_delta = (
                stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
            )
            # cgroup v2 hosts carry online_cpus; percpu_usage is v1-only —
            # indexing it raised KeyError here, which the generic except
            # turned into a bogus "not running" (surfaced by TAP-5999).
            cpu_count = stats["cpu_stats"].get("online_cpus") or len(
                stats["cpu_stats"]["cpu_usage"].get("percpu_usage") or [1]
            )
            cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0

            # Memory usage
            memory_usage = stats["memory_stats"]["usage"]
            memory_limit = stats["memory_stats"]["limit"]
            memory_percent = (memory_usage / memory_limit) * 100.0

            return {
                "cpu_percent": round(cpu_percent, 2),
                "memory_usage": memory_usage,
                "memory_limit": memory_limit,
                "memory_percent": round(memory_percent, 2),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting stats for {service_name}: {e}")
            return None

