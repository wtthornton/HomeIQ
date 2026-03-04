"""Null Wake Word fallback -- push-to-talk mode.

Implements the same interface as WakeWordService so the pipeline can swap
transparently without restart.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class NullWakeWordService:
    """No-op wake word detector for push-to-talk mode.

    Used when OpenWakeWord is unavailable or wake word is disabled.
    """

    def __init__(self) -> None:
        self.is_loaded = False
        self.name = "null-wake-word"

    async def startup(self) -> None:
        """No-op startup."""
        logger.info("NullWakeWordService active -- using push-to-talk mode")

    async def shutdown(self) -> None:
        """No-op shutdown."""

    async def detect(self, audio_chunk: bytes) -> bool:
        """Always returns False (no detection).

        Args:
            audio_chunk: Raw PCM audio chunk (ignored).

        Returns:
            False always.
        """
        return False

    def reset(self) -> None:
        """No-op reset."""

    def health(self) -> dict:
        """Report health status."""
        return {
            "component": "wake_word",
            "status": "disabled",
            "model": None,
            "mode": "push-to-talk",
        }
