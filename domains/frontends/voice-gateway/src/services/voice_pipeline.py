"""Voice Pipeline Orchestrator.

Story 26.4: Wires components together:
wake word -> record -> STT -> agent -> TTS -> play.

Uses httpx.AsyncClient to call ha-ai-agent-service:8030/api/chat.
Processing lock prevents concurrent voice queries.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx
import numpy as np
from homeiq_resilience import CircuitBreaker

from ..config import settings
from .stt_null import NullSTTService
from .stt_service import STTService
from .tts_null import NullTTSService
from .tts_service import TTSService
from .wake_word_null import NullWakeWordService
from .wake_word_service import WakeWordService

logger = logging.getLogger(__name__)


class PipelineState(str, Enum):
    """Voice pipeline states for UI sync."""

    IDLE = "idle"
    LISTENING = "listening"
    RECORDING = "recording"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class PipelineEvent:
    """Event emitted by the voice pipeline for UI state sync."""

    event_type: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class VoicePipeline:
    """Orchestrates wake word -> STT -> agent -> TTS flow.

    Thread-safe via processing lock. Emits events for UI state sync.
    """

    def __init__(
        self,
        stt: STTService | NullSTTService,
        tts: TTSService | NullTTSService,
        wake_word: WakeWordService | NullWakeWordService,
    ) -> None:
        self.stt = stt
        self.tts = tts
        self.wake_word = wake_word
        self._lock = asyncio.Lock()
        self._state = PipelineState.IDLE
        self._event_listeners: list[asyncio.Queue[PipelineEvent]] = []
        self._http_client: httpx.AsyncClient | None = None
        self._agent_cb = CircuitBreaker(
            failure_threshold=settings.cb_failure_threshold,
            recovery_timeout=settings.cb_recovery_timeout,
        )

        # Metrics
        self.total_queries = 0
        self.successful_queries = 0
        self.failed_queries = 0

    @property
    def state(self) -> PipelineState:
        """Current pipeline state."""
        return self._state

    async def startup(self) -> None:
        """Initialize HTTP client for agent service calls."""
        self._http_client = httpx.AsyncClient(
            base_url=settings.agent_service_url,
            timeout=httpx.Timeout(settings.agent_service_timeout),
        )
        logger.info("Voice pipeline initialized")

    async def shutdown(self) -> None:
        """Close HTTP client and clean up."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        logger.info("Voice pipeline shut down")

    def subscribe(self) -> asyncio.Queue[PipelineEvent]:
        """Subscribe to pipeline events.

        Returns:
            Queue that receives PipelineEvent objects.
        """
        queue: asyncio.Queue[PipelineEvent] = asyncio.Queue(maxsize=100)
        self._event_listeners.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[PipelineEvent]) -> None:
        """Remove an event subscription."""
        if queue in self._event_listeners:
            self._event_listeners.remove(queue)

    async def _emit(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Emit event to all subscribers."""
        event = PipelineEvent(event_type=event_type, data=data or {})
        for queue in self._event_listeners:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Event queue full -- dropping event %s", event_type)

    async def _set_state(self, state: PipelineState) -> None:
        """Update state and emit event."""
        self._state = state
        await self._emit("STATE_CHANGED", {"state": state.value})

    async def process_audio(self, audio_bytes: bytes) -> dict[str, Any]:
        """Process recorded audio through the full pipeline.

        Steps: STT -> Agent -> TTS

        Args:
            audio_bytes: Raw 16kHz 16-bit PCM audio.

        Returns:
            Dict with transcription, response text, and audio bytes.
        """
        if self._lock.locked():
            logger.warning("Pipeline busy -- rejecting concurrent request")
            return {"error": "Pipeline is busy processing another request"}

        async with self._lock:
            self.total_queries += 1
            await self._set_state(PipelineState.PROCESSING)

            try:
                # Step 1: STT
                transcription = await self.stt.transcribe(audio_bytes)
                if not transcription.strip():
                    await self._set_state(PipelineState.IDLE)
                    return {"transcription": "", "response": "", "audio": b""}

                await self._emit("TRANSCRIPTION", {"text": transcription})
                logger.info("Transcribed: %s", transcription[:100])

                # Step 2: Query agent service
                response_text = await self._query_agent(transcription)
                await self._emit("AGENT_RESPONSE", {"text": response_text})

                # Step 3: TTS
                await self._set_state(PipelineState.SPEAKING)
                audio_response = await self.tts.synthesize(response_text)

                self.successful_queries += 1
                await self._set_state(PipelineState.IDLE)

                return {
                    "transcription": transcription,
                    "response": response_text,
                    "audio": audio_response,
                }
            except Exception:
                self.failed_queries += 1
                logger.exception("Voice pipeline processing failed")
                await self._set_state(PipelineState.ERROR)
                await asyncio.sleep(1)
                await self._set_state(PipelineState.IDLE)
                return {"error": "Processing failed"}

    async def _query_agent(self, text: str) -> str:
        """Send text to ha-ai-agent-service and get response.

        Args:
            text: User's transcribed query.

        Returns:
            Agent response text.
        """
        if self._http_client is None:
            logger.error("HTTP client not initialized")
            return "Voice service is not fully initialized."

        if not self._agent_cb.allow_request():
            logger.warning("AI FALLBACK: Agent circuit breaker open")
            return "I'm having trouble connecting to the assistant. Please try again later."

        try:
            response = await self._http_client.post(
                "/api/chat",
                json={"message": text, "source": "voice"},
            )
            response.raise_for_status()
            data = response.json()
            self._agent_cb.record_success()
            return data.get("response", data.get("message", ""))
        except Exception:
            self._agent_cb.record_failure()
            logger.exception("Agent service call failed")
            return "I couldn't process your request. Please try again."

    async def check_wake_word(self, audio_chunk: bytes) -> bool:
        """Check audio chunk for wake word.

        Args:
            audio_chunk: Small audio chunk for wake word detection.

        Returns:
            True if wake word detected.
        """
        detected = await self.wake_word.detect(audio_chunk)
        if detected:
            await self._emit("WAKEWORD_DETECTED", {})
            self.wake_word.reset()
        return detected

    def detect_silence(self, audio_bytes: bytes) -> bool:
        """Check if audio chunk is silence.

        Args:
            audio_bytes: Raw 16-bit PCM audio.

        Returns:
            True if RMS is below silence threshold.
        """
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(audio_array**2)) / 32768.0
        return float(rms) < settings.silence_threshold

    def health(self) -> dict[str, Any]:
        """Report pipeline health."""
        return {
            "state": self._state.value,
            "components": {
                "stt": self.stt.health(),
                "tts": self.tts.health(),
                "wake_word": self.wake_word.health(),
            },
            "metrics": {
                "total_queries": self.total_queries,
                "successful_queries": self.successful_queries,
                "failed_queries": self.failed_queries,
            },
            "agent_circuit_breaker": {
                "state": (
                    "open" if not self._agent_cb.allow_request() else "closed"
                ),
            },
        }
