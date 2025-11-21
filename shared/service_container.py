"""
Shared Service Container Base Class

Provides generic dependency injection container with singleton pattern and lazy loading.
Services can extend this base class to add their own specific services.
"""

import logging
from abc import ABC
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class BaseServiceContainer(ABC):
    """
    Base service container with singleton pattern and lazy loading.

    Provides:
    - Thread-safe singleton pattern
    - Lazy service initialization
    - Service lifecycle management (startup/shutdown hooks)
    - Service registration and retrieval
    """

    _instances: dict[type, "BaseServiceContainer"] = {}
    _initialized: dict[type, bool] = {}

    def __new__(cls):
        """Singleton pattern - one instance per subclass"""
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls)
            cls._initialized[cls] = False
        return cls._instances[cls]

    def __init__(self):
        """Initialize service container (only once per subclass)"""
        if self._initialized.get(self.__class__, False):
            return

        # Service registry: name -> (factory, instance)
        self._services: dict[str, tuple[Callable, Any | None]] = {}

        # Startup/shutdown hooks
        self._startup_hooks: list[Callable] = []
        self._shutdown_hooks: list[Callable] = []

        # Initialization flag
        self._initialized[self.__class__] = True
        logger.info(f"✅ {self.__class__.__name__} initialized")

    def register_service(self, name: str, factory: Callable, lazy: bool = True):
        """
        Register a service factory.

        Args:
            name: Service name
            factory: Factory function that creates the service instance
            lazy: If True, service is created on first access (default: True)
        """
        if lazy:
            self._services[name] = (factory, None)
        else:
            # Eager initialization
            instance = factory()
            self._services[name] = (factory, instance)
            logger.info(f"✅ Service '{name}' registered and initialized")

    def get_service(self, name: str) -> Any:
        """
        Get service instance (lazy initialization if needed).

        Args:
            name: Service name

        Returns:
            Service instance

        Raises:
            KeyError: If service not found
        """
        if name not in self._services:
            msg = f"Service '{name}' not registered"
            raise KeyError(msg)

        factory, instance = self._services[name]

        # Lazy initialization
        if instance is None:
            instance = factory()
            self._services[name] = (factory, instance)
            logger.debug(f"✅ Service '{name}' initialized")

        return instance

    def has_service(self, name: str) -> bool:
        """Check if service is registered"""
        return name in self._services

    def add_startup_hook(self, hook: Callable):
        """
        Add startup hook (called during container startup).

        Args:
            hook: Async or sync callable
        """
        self._startup_hooks.append(hook)

    def add_shutdown_hook(self, hook: Callable):
        """
        Add shutdown hook (called during container shutdown).

        Args:
            hook: Async or sync callable
        """
        self._shutdown_hooks.append(hook)

    async def startup(self):
        """Execute all startup hooks"""
        logger.info(f"Starting {self.__class__.__name__}...")
        for hook in self._startup_hooks:
            try:
                if callable(hook):
                    # Check if it's async
                    import asyncio
                    if asyncio.iscoroutinefunction(hook):
                        await hook()
                    else:
                        hook()
            except Exception as e:
                logger.error(f"Error in startup hook: {e}", exc_info=True)
        logger.info(f"✅ {self.__class__.__name__} started")

    async def shutdown(self):
        """Execute all shutdown hooks"""
        logger.info(f"Shutting down {self.__class__.__name__}...")
        for hook in reversed(self._shutdown_hooks):  # Reverse order for shutdown
            try:
                if callable(hook):
                    import asyncio
                    if asyncio.iscoroutinefunction(hook):
                        await hook()
                    else:
                        hook()
            except Exception as e:
                logger.error(f"Error in shutdown hook: {e}", exc_info=True)
        logger.info(f"✅ {self.__class__.__name__} shut down")

    def reset(self):
        """Reset all services (useful for testing)"""
        # Clear all service instances (force re-initialization)
        for name in self._services:
            factory, _ = self._services[name]
            self._services[name] = (factory, None)
        logger.info(f"✅ {self.__class__.__name__} reset")

    def get_registered_services(self) -> list[str]:
        """Get list of registered service names"""
        return list(self._services.keys())


def get_service_container(container_class: type[BaseServiceContainer]) -> BaseServiceContainer:
    """
    Dependency function for FastAPI routes.

    Args:
        container_class: Service container class

    Returns:
        Service container instance
    """
    return container_class()

