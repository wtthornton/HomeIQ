"""
Jaeger Query API Client
Client for querying traces from Jaeger
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TraceSpan(BaseModel):
    """Represents a single span in a trace."""

    traceID: str
    spanID: str
    operationName: str
    startTime: int
    duration: int
    tags: List[Dict[str, Any]]
    logs: List[Dict[str, Any]]
    references: List[Dict[str, Any]]
    processID: str
    warnings: Optional[List[str]] = None


class Trace(BaseModel):
    """Represents a complete trace."""

    traceID: str
    spans: List[TraceSpan]
    processes: Dict[str, Dict[str, Any]]


class Service(BaseModel):
    """Represents a service in Jaeger."""

    name: str
    operations: Optional[List[str]] = None


class Dependency(BaseModel):
    """Represents a service dependency."""

    parent: str
    child: str
    callCount: int


class JaegerClient:
    """
    Client for querying Jaeger Query API.

    Provides methods to query traces, services, and dependencies from Jaeger.
    """

    def __init__(self, api_url: Optional[str] = None):
        """
        Initialize Jaeger client.

        Args:
            api_url: Jaeger Query API URL (default: from JAEGER_API_URL env var)
        """
        self.api_url = api_url or os.getenv("JAEGER_API_URL", "http://jaeger:16686/api")
        self.client = httpx.AsyncClient(timeout=30.0)
        self._services_cache: Optional[List[Service]] = None
        self._services_cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)

    async def close(self) -> None:
        """
        Close the HTTP client.
        
        Should be called when client is no longer needed to free resources.
        """
        await self.client.aclose()

    async def get_traces(
        self,
        service: Optional[str] = None,
        operation: Optional[str] = None,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Trace]:
        """
        Get traces from Jaeger.

        Args:
            service: Filter by service name
            operation: Filter by operation name
            limit: Maximum number of traces to return
            start_time: Start time for trace query
            end_time: End time for trace query

        Returns:
            List of traces
        """
        try:
            # Build query parameters
            params: Dict[str, Any] = {"limit": limit}

            if service:
                params["service"] = service
            if operation:
                params["operation"] = operation

            # Convert datetime to microseconds since epoch
            if start_time:
                params["start"] = int(start_time.timestamp() * 1000000)
            if end_time:
                params["end"] = int(end_time.timestamp() * 1000000)

            # Default to last hour if no time range specified
            if not start_time and not end_time:
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=1)
                params["start"] = int(start_time.timestamp() * 1000000)
                params["end"] = int(end_time.timestamp() * 1000000)

            # Query Jaeger API
            response = await self.client.get(
                f"{self.api_url}/traces",
                params=params,
            )
            response.raise_for_status()

            data = response.json()
            traces = []
            for trace_data in data.get("data", []):
                try:
                    trace = Trace(**trace_data)
                    traces.append(trace)
                except Exception as e:
                    logger.warning(f"Failed to parse trace: {e}")
                    continue

            return traces

        except httpx.HTTPError as e:
            logger.error(f"Failed to query traces: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error querying traces: {e}", exc_info=True)
            return []

    async def get_trace(self, trace_id: str) -> Optional[Trace]:
        """
        Get a specific trace by ID.

        Args:
            trace_id: Trace ID

        Returns:
            Trace if found, None otherwise
        """
        try:
            response = await self.client.get(
                f"{self.api_url}/trace/{trace_id}",
            )
            response.raise_for_status()

            data = response.json()
            if data.get("data"):
                return Trace(**data["data"][0])
            return None

        except httpx.HTTPError as e:
            logger.error(f"Failed to query trace {trace_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error querying trace {trace_id}: {e}", exc_info=True)
            return None

    async def get_services(self, force_refresh: bool = False) -> List[Service]:
        """
        Get list of services from Jaeger.

        Args:
            force_refresh: Force refresh of cache

        Returns:
            List of services
        """
        # Check cache
        if (
            not force_refresh
            and self._services_cache is not None
            and self._services_cache_time is not None
            and datetime.utcnow() - self._services_cache_time < self._cache_ttl
        ):
            return self._services_cache

        try:
            response = await self.client.get(f"{self.api_url}/services")
            response.raise_for_status()

            data = response.json()
            services = []
            for service_name in data.get("data", []):
                # Get operations for this service
                operations = await self._get_service_operations(service_name)
                service = Service(name=service_name, operations=operations)
                services.append(service)

            # Update cache
            self._services_cache = services
            self._services_cache_time = datetime.utcnow()

            return services

        except httpx.HTTPError as e:
            logger.error(f"Failed to query services: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error querying services: {e}", exc_info=True)
            return []

    async def _get_service_operations(self, service_name: str) -> List[str]:
        """Get operations for a service."""
        try:
            response = await self.client.get(
                f"{self.api_url}/services/{service_name}/operations",
            )
            response.raise_for_status()

            data = response.json()
            return data.get("data", [])

        except httpx.HTTPError:
            return []
        except Exception as e:
            logger.warning(f"Failed to get operations for {service_name}: {e}")
            return []

    async def get_dependencies(
        self, start_time: datetime, end_time: datetime
    ) -> List[Dependency]:
        """
        Get service dependencies.

        Args:
            start_time: Start time for dependency query
            end_time: End time for dependency query

        Returns:
            List of dependencies
        """
        try:
            params = {
                "start": int(start_time.timestamp() * 1000000),
                "end": int(end_time.timestamp() * 1000000),
            }

            response = await self.client.get(
                f"{self.api_url}/dependencies",
                params=params,
            )
            response.raise_for_status()

            data = response.json()
            dependencies = []
            for dep_data in data.get("data", []):
                try:
                    dependency = Dependency(**dep_data)
                    dependencies.append(dependency)
                except Exception as e:
                    logger.warning(f"Failed to parse dependency: {e}")
                    continue

            return dependencies

        except httpx.HTTPError as e:
            logger.error(f"Failed to query dependencies: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error querying dependencies: {e}", exc_info=True)
            return []

    async def search_traces(self, query_params: Dict[str, Any]) -> List[Trace]:
        """
        Search traces with custom query parameters.

        Args:
            query_params: Custom query parameters

        Returns:
            List of traces
        """
        try:
            response = await self.client.get(
                f"{self.api_url}/traces",
                params=query_params,
            )
            response.raise_for_status()

            data = response.json()
            traces = []
            for trace_data in data.get("data", []):
                try:
                    trace = Trace(**trace_data)
                    traces.append(trace)
                except Exception as e:
                    logger.warning(f"Failed to parse trace: {e}")
                    continue

            return traces

        except httpx.HTTPError as e:
            logger.error(f"Failed to search traces: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error searching traces: {e}", exc_info=True)
            return []
