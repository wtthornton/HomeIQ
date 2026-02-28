"""
Huey Configuration

Initialize Huey with in-memory backend for task queue.
"""

import logging

from huey import Huey

from ..config import settings

logger = logging.getLogger(__name__)


def get_huey_instance() -> Huey:
    """
    Get or create Huey instance with in-memory backend.

    Returns:
        Huey instance configured for automation queue
    """
    logger.info("Initializing Huey with in-memory backend")

    huey = Huey(
        'automation-queue',
        results=True,
        result_ttl=settings.huey_result_ttl,
    )

    return huey


# Global Huey instance
huey = get_huey_instance()
