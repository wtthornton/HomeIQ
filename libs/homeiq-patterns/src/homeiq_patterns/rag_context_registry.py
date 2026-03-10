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

# Default token budget (in estimated tokens; 1 token ≈ 4 chars)
DEFAULT_TOKEN_BUDGET = 8000


class RAGContextRegistry:
    """
    Manages multiple RAGContextService instances and assembles
    matching contexts for a given prompt.

    Contexts are ranked by relevance score and subject to a token budget.
    """

    def __init__(self, max_token_budget: int = DEFAULT_TOKEN_BUDGET) -> None:
        self._services: list[RAGContextService] = []
        self.max_token_budget = max_token_budget

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

    async def get_scored_context(
        self, prompt: str
    ) -> list[tuple[str, float, str]]:
        """
        Score all services and return matching contexts ranked by relevance.

        Args:
            prompt: User message

        Returns:
            List of (service_name, score, formatted_context) tuples,
            sorted by score descending. Only includes services that matched.
        """
        results: list[tuple[str, float, str]] = []
        for service in self._services:
            try:
                score = service.score_relevance(prompt)
                if score < service.min_score:
                    continue
                corpus = service.load_corpus()
                if not corpus:
                    continue
                context = service.format_context(corpus)
                results.append((service.name, score, context))
                logger.debug(
                    f"RAG scored: {service.name} "
                    f"(score={score:.2f}, {len(context)} chars)"
                )
            except Exception as e:
                logger.warning(f"RAG service {service.name} failed: {e}")

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    async def get_all_context(self, prompt: str) -> list[str]:
        """
        Run all registered services and return matching contexts.

        Contexts are ranked by relevance score and trimmed to fit
        within the token budget (chars/4 estimate).

        Args:
            prompt: User message

        Returns:
            List of formatted context strings from matching services,
            ordered by relevance score (highest first)
        """
        scored = await self.get_scored_context(prompt)

        budget_chars = self.max_token_budget * 4
        used_chars = 0
        contexts: list[str] = []

        for name, score, context in scored:
            context_len = len(context)
            if used_chars + context_len > budget_chars and contexts:
                logger.info(
                    f"RAG budget exceeded: skipping {name} "
                    f"({context_len} chars, {used_chars}/{budget_chars} used)"
                )
                continue
            contexts.append(context)
            used_chars += context_len

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

    async def get_context_for_domains(
        self, domains: list[str]
    ) -> list[str]:
        """
        Load context for specific domains by name, bypassing keyword detection.

        Useful when validation errors or other signals indicate which
        domains are relevant regardless of prompt content.

        Args:
            domains: List of service names to load context for

        Returns:
            List of formatted context strings for the requested domains
        """
        contexts: list[str] = []
        domain_set = set(domains)
        for service in self._services:
            if service.name not in domain_set:
                continue
            try:
                corpus = service.load_corpus()
                if corpus:
                    contexts.append(service.format_context(corpus))
            except Exception as e:
                logger.warning(f"RAG service {service.name} failed: {e}")
        return contexts
