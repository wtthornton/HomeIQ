"""Null TTS fallback -- returns empty audio when Kokoro is unavailable.

Implements the same interface as TTSService so the pipeline can swap
transparently without restart.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class NullTTSService:
    """No-op TTS that returns empty audio bytes.

    Used when Kokoro is unavailable or TTS is disabled at runtime.
    """

    def __init__(self) -> None:
        self.is_loaded = False
        self.name = "null-tts"

    async def startup(self) -> None:
        """No-op startup."""
        logger.info("NullTTSService active -- TTS synthesis disabled")

    async def shutdown(self) -> None:
        """No-op shutdown."""

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float = 1.0,
    ) -> bytes:
        """Return empty WAV audio.

        Args:
            text: Text to synthesize (ignored).
            voice: Voice name (ignored).
            speed: Speech speed (ignored).

        Returns:
            Empty bytes.
        """
        return b""

    def health(self) -> dict:
        """Report health status."""
        return {
            "component": "tts",
            "status": "disabled",
            "voice": None,
            "device": None,
        }
