"""
Dependency Injection Framework

Dependency injection framework for simulation framework using FastAPI-style patterns.
Supports mock service factories and service registration.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, TypeVar, cast

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceFactory(ABC, Generic[T]):
    """
    Abstract base class for service factories.
    
    Service factories create and configure mock services for simulation.
    """

    @abstractmethod
    def create(self) -> T:
        """Create and return a service instance."""
        pass

    @abstractmethod
    def cleanup(self, service: T) -> None:
        """Cleanup resources used by service."""
        pass


class DependencyContainer:
    """
    Dependency injection container for simulation framework.
    
    Manages service registration, creation, and lifecycle using FastAPI-style
    dependency injection patterns.
    """

    def __init__(self):
        """Initialize dependency container."""
        self._factories: dict[str, ServiceFactory[Any]] = {}
        self._instances: dict[str, Any] = {}
        self._singletons: set[str] = set()
        logger.debug("DependencyContainer initialized")

    def register_factory(
        self,
        service_name: str,
        factory: ServiceFactory[Any],
        singleton: bool = True
    ) -> None:
        """
        Register a service factory.
        
        Args:
            service_name: Name of the service (e.g., "influxdb_client")
            factory: Service factory instance
            singleton: If True, service is created once and reused
        """
        self._factories[service_name] = factory
        if singleton:
            self._singletons.add(service_name)
        logger.debug(f"Registered factory for {service_name} (singleton={singleton})")

    def register_instance(
        self,
        service_name: str,
        instance: Any
    ) -> None:
        """
        Register a service instance directly.
        
        Args:
            service_name: Name of the service
            instance: Service instance
        """
        self._instances[service_name] = instance
        logger.debug(f"Registered instance for {service_name}")

    def get(self, service_name: str) -> Any:
        """
        Get a service instance.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service is not registered
        """
        # Check if instance already exists (singleton or pre-registered)
        if service_name in self._instances:
            return self._instances[service_name]

        # Check if factory exists
        if service_name not in self._factories:
            raise KeyError(f"Service '{service_name}' not registered")

        # Create instance using factory
        factory = self._factories[service_name]
        instance = factory.create()

        # Store if singleton
        if service_name in self._singletons:
            self._instances[service_name] = instance

        logger.debug(f"Created instance for {service_name}")
        return instance

    def has(self, service_name: str) -> bool:
        """Check if a service is registered."""
        return service_name in self._factories or service_name in self._instances

    def clear(self) -> None:
        """Clear all registered services and instances."""
        # Cleanup all instances
        for service_name, instance in list(self._instances.items()):
            if service_name in self._factories:
                factory = self._factories[service_name]
                try:
                    factory.cleanup(instance)
                except Exception as e:
                    logger.warning(f"Error cleaning up {service_name}: {e}")

        self._factories.clear()
        self._instances.clear()
        self._singletons.clear()
        logger.debug("DependencyContainer cleared")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources."""
        self.clear()

