"""Wake Word Detection Service -- OpenWakeWord integration.

Story 26.3: ONNX-based wake word detection with configurable model and
threshold. Emits WAKEWORD_DETECTED events on detection.
"""

from __future__ import annotations

import logging

import numpy as np

from .wake_word_null import NullWakeWordService

logger = logging.getLogger(__name__)


class WakeWordService:
    """Wake word detection using OpenWakeWord with ONNX models.

    Falls back to NullWakeWordService if OpenWakeWord is unavailable.
    """

    def __init__(
        self,
        model_name: str = "hey_jarvis",
        threshold: float = 0.5,
    ) -> None:
        self.model_name = model_name
        self.threshold = threshold
        self.model = None
        self.is_loaded = False
        self.name = "openwakeword"
        self._detection_count = 0

    async def startup(self) -> None:
        """Load the OpenWakeWord model."""
        try:
            from openwakeword.model import Model

            self.model = Model(
                wakeword_models=[self.model_name],
                inference_framework="onnx",
            )
            self.is_loaded = True
            logger.info(
                "OpenWakeWord loaded: model=%s threshold=%.2f",
                self.model_name,
                self.threshold,
            )
        except Exception:
            logger.exception("Failed to load OpenWakeWord -- wake word disabled")
            self.is_loaded = False

    async def shutdown(self) -> None:
        """Release model resources."""
        self.model = None
        self.is_loaded = False
        logger.info("Wake word service shut down")

    async def detect(self, audio_chunk: bytes) -> bool:
        """Check audio chunk for wake word.

        Args:
            audio_chunk: Raw 16kHz 16-bit PCM audio chunk (typically 1280 bytes / 80ms).

        Returns:
            True if wake word detected above threshold.
        """
        if not self.is_loaded or self.model is None:
            return False

        try:
            audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
            prediction = self.model.predict(audio_array)

            for model_name, score in prediction.items():
                if score >= self.threshold:
                    self._detection_count += 1
                    logger.info(
                        "Wake word detected: model=%s score=%.3f count=%d",
                        model_name,
                        score,
                        self._detection_count,
                    )
                    return True
            return False
        except Exception:
            logger.exception("Wake word detection failed")
            return False

    def reset(self) -> None:
        """Reset the model state for a new detection cycle."""
        if self.model is not None:
            try:
                self.model.reset()
            except Exception:
                logger.exception("Failed to reset wake word model")

    def health(self) -> dict:
        """Report health status."""
        return {
            "component": "wake_word",
            "status": "loaded" if self.is_loaded else "unavailable",
            "model": self.model_name,
            "threshold": self.threshold,
            "detection_count": self._detection_count,
            "mode": "wake-word",
        }


async def create_wake_word_service(
    model_name: str = "hey_jarvis",
    threshold: float = 0.5,
    enabled: bool = False,
) -> WakeWordService | NullWakeWordService:
    """Factory: create wake word service with fallback.

    Args:
        model_name: OpenWakeWord model name.
        threshold: Detection threshold.
        enabled: Whether to attempt loading wake word detection.

    Returns:
        WakeWordService if model loads successfully, NullWakeWordService otherwise.
    """
    if not enabled:
        svc = NullWakeWordService()
        await svc.startup()
        return svc

    svc = WakeWordService(model_name=model_name, threshold=threshold)
    await svc.startup()
    if not svc.is_loaded:
        logger.warning(
            "AI FALLBACK: OpenWakeWord failed to load -- using push-to-talk mode",
        )
        null_svc = NullWakeWordService()
        await null_svc.startup()
        return null_svc
    return svc
