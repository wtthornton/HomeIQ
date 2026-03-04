"""Service configuration for voice-gateway.

Uses BaseServiceSettings for common fields (InfluxDB, data-api, logging, CORS).
"""

from __future__ import annotations

from homeiq_data import BaseServiceSettings
from pydantic import Field


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Override base defaults
    service_port: int = 8041
    service_name: str = "voice-gateway"

    # HA AI Agent Service (chat backend)
    agent_service_url: str = Field(
        default="http://ha-ai-agent-service:8030",
        description="URL of the HA AI Agent Service",
    )
    agent_service_timeout: float = Field(
        default=30.0,
        description="Timeout in seconds for agent service calls",
    )

    # STT (Faster Whisper) settings
    stt_enabled: bool = Field(default=True, description="Enable STT on startup")
    stt_model_size: str = Field(
        default="base",
        description="Faster Whisper model size (tiny, base, small, medium, large-v3)",
    )
    stt_language: str = Field(default="en", description="STT language code")
    stt_compute_type: str = Field(
        default="int8",
        description="Compute type for STT (int8, float16, float32)",
    )

    # TTS (Kokoro) settings
    tts_enabled: bool = Field(default=True, description="Enable TTS on startup")
    tts_voice: str = Field(default="af_heart", description="Kokoro voice name")
    tts_speed: float = Field(default=1.0, description="TTS speech speed multiplier")
    tts_sample_rate: int = Field(default=24000, description="TTS output sample rate")

    # Wake word (OpenWakeWord) settings
    wake_word_enabled: bool = Field(default=False, description="Enable wake word on startup")
    wake_word_model: str = Field(
        default="hey_jarvis",
        description="Wake word model name",
    )
    wake_word_threshold: float = Field(
        default=0.5,
        description="Wake word detection threshold (0.0-1.0)",
    )

    # Audio settings
    audio_sample_rate: int = Field(default=16000, description="Audio input sample rate (Hz)")
    audio_channels: int = Field(default=1, description="Audio input channels")
    silence_threshold: float = Field(
        default=0.01,
        description="RMS threshold below which audio is considered silence",
    )
    silence_duration: float = Field(
        default=1.5,
        description="Seconds of silence before stopping recording",
    )

    # Circuit breaker settings
    cb_failure_threshold: int = Field(
        default=3,
        description="Circuit breaker failure threshold",
    )
    cb_recovery_timeout: int = Field(
        default=60,
        description="Circuit breaker recovery timeout in seconds",
    )


settings = Settings()
