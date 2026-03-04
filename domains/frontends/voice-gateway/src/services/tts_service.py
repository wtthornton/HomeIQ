"""TTS Service -- Text-to-Speech using Kokoro.

Story 26.2: Synthesizes text to WAV audio with configurable voice and speed.
GPU auto-detection with CPU fallback.
"""

from __future__ import annotations

import io
import logging
import struct
import wave

import numpy as np

from .tts_null import NullTTSService

logger = logging.getLogger(__name__)


def _write_wav(audio_data: np.ndarray, sample_rate: int) -> bytes:
    """Convert float32 audio array to WAV bytes.

    Args:
        audio_data: Float32 audio samples (-1.0 to 1.0).
        sample_rate: Output sample rate in Hz.

    Returns:
        WAV file bytes.
    """
    pcm = (audio_data * 32767).astype(np.int16)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))
    return buffer.getvalue()


class TTSService:
    """Text-to-Speech using Kokoro TTS.

    Falls back to NullTTSService if Kokoro is unavailable.
    """

    def __init__(
        self,
        voice: str = "af_heart",
        speed: float = 1.0,
        sample_rate: int = 24000,
    ) -> None:
        self.voice = voice
        self.speed = speed
        self.sample_rate = sample_rate
        self.pipeline = None
        self.is_loaded = False
        self.device: str = "cpu"
        self.name = "kokoro"

    async def startup(self) -> None:
        """Load the Kokoro TTS pipeline."""
        try:
            from kokoro import KPipeline

            # Detect GPU
            try:
                import torch

                if torch.cuda.is_available():
                    self.device = "cuda"
                    logger.info("CUDA detected -- using GPU for TTS")
            except ImportError:
                pass

            self.pipeline = KPipeline(lang_code="a", device=self.device)
            self.is_loaded = True
            logger.info(
                "Kokoro TTS loaded: voice=%s speed=%.1f device=%s",
                self.voice,
                self.speed,
                self.device,
            )
        except Exception:
            logger.exception("Failed to load Kokoro TTS -- TTS disabled")
            self.is_loaded = False

    async def shutdown(self) -> None:
        """Release TTS resources."""
        self.pipeline = None
        self.is_loaded = False
        logger.info("TTS service shut down")

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float | None = None,
    ) -> bytes:
        """Synthesize text to WAV audio bytes.

        Args:
            text: Text to synthesize.
            voice: Override default voice.
            speed: Override default speed.

        Returns:
            WAV audio bytes, or empty bytes on failure.
        """
        if not self.is_loaded or self.pipeline is None:
            logger.warning("TTS not loaded -- returning empty audio")
            return b""

        use_voice = voice or self.voice
        use_speed = speed if speed is not None else self.speed

        try:
            generator = self.pipeline(
                text,
                voice=use_voice,
                speed=use_speed,
            )
            all_audio = []
            for _graphemes, _phonemes, audio_chunk in generator:
                if audio_chunk is not None:
                    all_audio.append(audio_chunk)

            if not all_audio:
                logger.warning("TTS produced no audio for text: %s", text[:50])
                return b""

            combined = np.concatenate(all_audio)
            wav_bytes = _write_wav(combined, self.sample_rate)
            logger.debug("Synthesized %d bytes of WAV audio", len(wav_bytes))
            return wav_bytes
        except Exception:
            logger.exception("TTS synthesis failed")
            return b""

    def health(self) -> dict:
        """Report health status."""
        return {
            "component": "tts",
            "status": "loaded" if self.is_loaded else "unavailable",
            "voice": self.voice,
            "device": self.device,
            "sample_rate": self.sample_rate,
        }


async def create_tts_service(
    voice: str = "af_heart",
    speed: float = 1.0,
    sample_rate: int = 24000,
    enabled: bool = True,
) -> TTSService | NullTTSService:
    """Factory: create TTS service with fallback.

    Args:
        voice: Kokoro voice name.
        speed: Speech speed multiplier.
        sample_rate: Output sample rate.
        enabled: Whether to attempt loading the real TTS.

    Returns:
        TTSService if Kokoro loads successfully, NullTTSService otherwise.
    """
    if not enabled:
        svc = NullTTSService()
        await svc.startup()
        return svc

    svc = TTSService(voice=voice, speed=speed, sample_rate=sample_rate)
    await svc.startup()
    if not svc.is_loaded:
        logger.warning("AI FALLBACK: Kokoro TTS failed to load -- using NullTTSService")
        null_svc = NullTTSService()
        await null_svc.startup()
        return null_svc
    return svc
