"""Null STT fallback -- returns empty transcription when model unavailable.

Implements the same interface as STTService so the pipeline can swap
transparently without restart.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class NullSTTService:
    """No-op STT that always returns empty text.

    Used when faster-whisper is unavailable or STT is disabled at runtime.
    """

    def __init__(self) -> None:
        self.is_loaded = False
        self.name = "null-stt"

    async def startup(self) -> None:
        """No-op startup."""
        logger.info("NullSTTService active -- STT transcription disabled")

    async def shutdown(self) -> None:
        """No-op shutdown."""

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Return empty transcription.

        Args:
            audio_bytes: Raw PCM audio (ignored).

        Returns:
            Empty string.
        """
        return ""

    def health(self) -> dict:
        """Report health status."""
        return {
            "component": "stt",
            "status": "disabled",
            "model": None,
            "device": None,
        }
