"""
RAGContextRegistry - Multi-Domain Context Assembly

Epic: Reusable Pattern Framework, Story 2
Registry that manages multiple RAGContextService implementations and
runs all domain detections for a given prompt.

Usage:
    registry = RAGContextRegistry()
    registry.register(AutomationRAGService())
    registry.register(EnergyRAGService())

    contexts = await registry.get_all_context("shift laundry to off-peak")
    # Returns list of matching context strings
"""

import logging
from typing import Sequence

from .rag_context_service import RAGContextService

logger = logging.getLogger(__name__)


class RAGContextRegistry:
    """
    Manages multiple RAGContextService instances and assembles
    matching contexts for a given prompt.

    Context injection order is deterministic (registration order).
    """

    def __init__(self) -> None:
        self._services: list[RAGContextService] = []

    def register(self, service: RAGContextService) -> None:
        """
        Register a RAG context service.

        Args:
            service: RAGContextService instance to register
        """
        self._services.append(service)
        logger.info(f"Registered RAG service: {service.name}")

    def unregister(self, name: str) -> bool:
        """
        Remove a registered service by name.

        Args:
            name: Service name to remove

        Returns:
            True if a service was removed
        """
        before = len(self._services)
        self._services = [s for s in self._services if s.name != name]
        removed = len(self._services) < before
        if removed:
            logger.info(f"Unregistered RAG service: {name}")
        return removed

    @property
    def services(self) -> Sequence[RAGContextService]:
        """Return registered services (read-only)."""
        return tuple(self._services)

    async def get_all_context(self, prompt: str) -> list[str]:
        """
        Run all registered services and return matching contexts.

        Contexts are returned in registration order.

        Args:
            prompt: User message

        Returns:
            List of formatted context strings from matching services
        """
        contexts: list[str] = []
        for service in self._services:
            try:
                context = await service.get_context(prompt)
                if context:
                    contexts.append(context)
                    logger.debug(
                        f"RAG match: {service.name} "
                        f"({len(context)} chars)"
                    )
            except Exception as e:
                logger.warning(
                    f"RAG service {service.name} failed: {e}"
                )
        return contexts

    async def get_merged_context(self, prompt: str) -> str:
        """
        Convenience method: get all matching contexts merged into one string.

        Args:
            prompt: User message

        Returns:
            Concatenated context string, or empty string if no matches
        """
        contexts = await self.get_all_context(prompt)
        return "\n".join(contexts)
