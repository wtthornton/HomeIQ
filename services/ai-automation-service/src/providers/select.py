"""
Provider Selection Policy
Simple deterministic provider selection based on task type.
"""

import logging

from .base import BaseProvider
from .openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)

# Provider registry
_providers: dict[str, BaseProvider] = {}


def register_provider(provider: BaseProvider):
    """
    Register a provider for use.

    Args:
        provider: Provider instance to register
    """
    _providers[provider.provider_id()] = provider
    logger.info(f"Registered provider: {provider.provider_id()}")


def get_provider(provider_id: str) -> BaseProvider | None:
    """
    Get provider by ID.

    Args:
        provider_id: Provider identifier

    Returns:
        Provider instance or None if not found
    """
    return _providers.get(provider_id)


def select_provider(task: str = "default", provider_id: str | None = None) -> BaseProvider:
    """
    Select provider for a given task.

    Simple policy:
    - If provider_id specified, use that provider
    - Otherwise, use default provider mapping

    Args:
        task: Task type (default, automation, entity_extraction, etc.)
        provider_id: Optional explicit provider ID

    Returns:
        Selected provider instance

    Raises:
        ValueError: If no provider available
    """
    # Explicit provider selection
    if provider_id:
        provider = get_provider(provider_id)
        if provider:
            return provider
        msg = f"Provider '{provider_id}' not registered"
        raise ValueError(msg)

    # Task-based selection (simple policy)
    task_to_provider = {
        "default": "openai",
        "automation": "openai",
        "entity_extraction": "openai",
        "description": "openai",
    }

    selected_id = task_to_provider.get(task, "openai")
    provider = get_provider(selected_id)

    if not provider:
        # Fallback: try to get any provider
        if _providers:
            provider = next(iter(_providers.values()))
            logger.warning(f"No provider for task '{task}', using: {provider.provider_id()}")
        else:
            msg = "No providers registered"
            raise ValueError(msg)

    return provider


def get_default_provider() -> BaseProvider | None:
    """Get default provider (first registered provider)."""
    if _providers:
        return next(iter(_providers.values()))
    return None


def initialize_default_providers(openai_api_key: str, openai_model: str = "gpt-4o"):
    """
    Initialize default providers (OpenAI).

    Args:
        openai_api_key: OpenAI API key
        openai_model: OpenAI model identifier
    """
    openai_provider = OpenAIProvider(api_key=openai_api_key, model=openai_model)
    register_provider(openai_provider)
    logger.info("Default providers initialized")

