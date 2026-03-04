"""Admin endpoints for hot-swap component toggling.

Story 26.5: Runtime enable/disable of STT, TTS, wake word without restart.
Uses null-object swap pattern.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

if TYPE_CHECKING:
    from ..services.voice_pipeline import VoicePipeline

from ..config import settings
from ..services.stt_null import NullSTTService
from ..services.stt_service import STTService, create_stt_service
from ..services.tts_null import NullTTSService
from ..services.tts_service import TTSService, create_tts_service
from ..services.wake_word_null import NullWakeWordService
from ..services.wake_word_service import WakeWordService, create_wake_word_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Set by main.py after pipeline initialization
_pipeline: VoicePipeline | None = None


def set_pipeline(pipeline: VoicePipeline) -> None:
    """Inject pipeline reference from main.py."""
    global _pipeline  # noqa: PLW0603
    _pipeline = pipeline


class ToggleRequest(BaseModel):
    """Request body for component toggle."""

    enabled: bool


@router.get("/status")
async def component_status() -> dict[str, Any]:
    """Report which voice components are active."""
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    return {
        "stt": {
            "enabled": isinstance(_pipeline.stt, STTService) and _pipeline.stt.is_loaded,
            "type": _pipeline.stt.name,
            **_pipeline.stt.health(),
        },
        "tts": {
            "enabled": isinstance(_pipeline.tts, TTSService) and _pipeline.tts.is_loaded,
            "type": _pipeline.tts.name,
            **_pipeline.tts.health(),
        },
        "wake_word": {
            "enabled": isinstance(_pipeline.wake_word, WakeWordService) and _pipeline.wake_word.is_loaded,
            "type": _pipeline.wake_word.name,
            **_pipeline.wake_word.health(),
        },
        "pipeline": {
            "state": _pipeline.state.value,
            "total_queries": _pipeline.total_queries,
            "successful_queries": _pipeline.successful_queries,
            "failed_queries": _pipeline.failed_queries,
        },
    }


@router.post("/stt/toggle")
async def toggle_stt(request: ToggleRequest) -> dict[str, Any]:
    """Enable or disable STT at runtime.

    Uses null-object swap pattern -- no restart required.
    """
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    if request.enabled:
        if isinstance(_pipeline.stt, STTService) and _pipeline.stt.is_loaded:
            return {"status": "already_enabled", "component": "stt"}
        new_stt = await create_stt_service(
            model_size=settings.stt_model_size,
            language=settings.stt_language,
            compute_type=settings.stt_compute_type,
            enabled=True,
        )
        if isinstance(new_stt, NullSTTService):
            raise HTTPException(
                status_code=503,
                detail="STT model failed to load",
            )
        await _pipeline.stt.shutdown()
        _pipeline.stt = new_stt
        logger.info("STT enabled via hot-swap")
        return {"status": "enabled", "component": "stt", **new_stt.health()}
    else:
        await _pipeline.stt.shutdown()
        null_stt = NullSTTService()
        await null_stt.startup()
        _pipeline.stt = null_stt
        logger.info("STT disabled via hot-swap")
        return {"status": "disabled", "component": "stt"}


@router.post("/tts/toggle")
async def toggle_tts(request: ToggleRequest) -> dict[str, Any]:
    """Enable or disable TTS at runtime.

    Uses null-object swap pattern -- no restart required.
    """
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    if request.enabled:
        if isinstance(_pipeline.tts, TTSService) and _pipeline.tts.is_loaded:
            return {"status": "already_enabled", "component": "tts"}
        new_tts = await create_tts_service(
            voice=settings.tts_voice,
            speed=settings.tts_speed,
            sample_rate=settings.tts_sample_rate,
            enabled=True,
        )
        if isinstance(new_tts, NullTTSService):
            raise HTTPException(
                status_code=503,
                detail="TTS engine failed to load",
            )
        await _pipeline.tts.shutdown()
        _pipeline.tts = new_tts
        logger.info("TTS enabled via hot-swap")
        return {"status": "enabled", "component": "tts", **new_tts.health()}
    else:
        await _pipeline.tts.shutdown()
        null_tts = NullTTSService()
        await null_tts.startup()
        _pipeline.tts = null_tts
        logger.info("TTS disabled via hot-swap")
        return {"status": "disabled", "component": "tts"}


@router.post("/wake-word/toggle")
async def toggle_wake_word(request: ToggleRequest) -> dict[str, Any]:
    """Enable or disable wake word detection at runtime.

    Uses null-object swap pattern -- no restart required.
    """
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    if request.enabled:
        if isinstance(_pipeline.wake_word, WakeWordService) and _pipeline.wake_word.is_loaded:
            return {"status": "already_enabled", "component": "wake_word"}
        new_ww = await create_wake_word_service(
            model_name=settings.wake_word_model,
            threshold=settings.wake_word_threshold,
            enabled=True,
        )
        if isinstance(new_ww, NullWakeWordService):
            raise HTTPException(
                status_code=503,
                detail="Wake word model failed to load",
            )
        await _pipeline.wake_word.shutdown()
        _pipeline.wake_word = new_ww
        logger.info("Wake word enabled via hot-swap")
        return {"status": "enabled", "component": "wake_word", **new_ww.health()}
    else:
        await _pipeline.wake_word.shutdown()
        null_ww = NullWakeWordService()
        await null_ww.startup()
        _pipeline.wake_word = null_ww
        logger.info("Wake word disabled via hot-swap")
        return {"status": "disabled", "component": "wake_word"}
