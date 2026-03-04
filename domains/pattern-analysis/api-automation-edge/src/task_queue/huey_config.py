"""
Huey Configuration

Initialize Huey with in-memory backend for task queue.
"""

import logging

from huey import MemoryHuey

logger = logging.getLogger(__name__)


def get_huey_instance() -> MemoryHuey:
    """
    Get or create Huey instance with in-memory backend.

    Returns:
        MemoryHuey instance configured for automation queue
    """
    logger.info("Initializing Huey with in-memory backend")

    huey = MemoryHuey(
        'automation-queue',
        results=True,
        immediate=False,
    )

    return huey


# Global Huey instance
huey = get_huey_instance()
