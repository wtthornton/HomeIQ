"""STT Service -- Speech-to-Text using Faster Whisper.

Story 26.1: Accepts 16kHz 16-bit PCM audio and returns transcription text.
GPU auto-detection with CPU fallback cascade.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from .stt_null import NullSTTService

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


def _detect_device() -> tuple[str, str]:
    """Detect best available compute device.

    Returns:
        Tuple of (device, compute_type).
    """
    try:
        import torch  # noqa: F401 -- probe only

        if torch.cuda.is_available():
            logger.info("CUDA detected -- using GPU for STT")
            return "cuda", "float16"
    except ImportError:
        pass

    logger.info("No GPU available -- using CPU for STT")
    return "cpu", "int8"


class STTService:
    """Speech-to-Text using faster-whisper with GPU auto-detection.

    Falls back to NullSTTService if model loading fails.
    """

    def __init__(
        self,
        model_size: str = "base",
        language: str = "en",
        compute_type: str | None = None,
    ) -> None:
        self.model_size = model_size
        self.language = language
        self._compute_type_override = compute_type
        self.model: WhisperModel | None = None
        self.device: str = "cpu"
        self.compute_type: str = "int8"
        self.is_loaded = False
        self.name = "faster-whisper"

    async def startup(self) -> None:
        """Load the Whisper model with GPU auto-detection."""
        try:
            from faster_whisper import WhisperModel

            self.device, self.compute_type = _detect_device()
            if self._compute_type_override:
                self.compute_type = self._compute_type_override

            logger.info(
                "Loading Whisper model=%s device=%s compute=%s",
                self.model_size,
                self.device,
                self.compute_type,
            )
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            self.is_loaded = True
            logger.info("Whisper model loaded successfully")
        except Exception:
            logger.exception("Failed to load Whisper model -- STT disabled")
            self.is_loaded = False

    async def shutdown(self) -> None:
        """Release model resources."""
        self.model = None
        self.is_loaded = False
        logger.info("STT service shut down")

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe 16kHz 16-bit PCM audio to text.

        Args:
            audio_bytes: Raw PCM audio bytes (16kHz, 16-bit, mono).

        Returns:
            Transcribed text string, or empty string on failure.
        """
        if not self.is_loaded or self.model is None:
            logger.warning("STT model not loaded -- returning empty transcription")
            return ""

        try:
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

            segments, _info = self.model.transcribe(
                audio_array,
                language=self.language,
                beam_size=5,
                vad_filter=True,
            )
            text = " ".join(segment.text.strip() for segment in segments)
            logger.debug("Transcribed: %s", text[:100])
            return text
        except Exception:
            logger.exception("Transcription failed")
            return ""

    def health(self) -> dict:
        """Report health status."""
        return {
            "component": "stt",
            "status": "loaded" if self.is_loaded else "unavailable",
            "model": self.model_size,
            "device": self.device,
            "compute_type": self.compute_type,
        }


async def create_stt_service(
    model_size: str = "base",
    language: str = "en",
    compute_type: str | None = None,
    enabled: bool = True,
) -> STTService | NullSTTService:
    """Factory: create STT service with fallback.

    Args:
        model_size: Whisper model size.
        language: Transcription language.
        compute_type: Override compute type.
        enabled: Whether to attempt loading the real STT.

    Returns:
        STTService if model loads successfully, NullSTTService otherwise.
    """
    if not enabled:
        svc = NullSTTService()
        await svc.startup()
        return svc

    svc = STTService(model_size=model_size, language=language, compute_type=compute_type)
    await svc.startup()
    if not svc.is_loaded:
        logger.warning("AI FALLBACK: STT model failed to load -- using NullSTTService")
        null_svc = NullSTTService()
        await null_svc.startup()
        return null_svc
    return svc
