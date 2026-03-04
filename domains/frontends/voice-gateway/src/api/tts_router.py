"""TTS HTTP endpoint.

Story 26.2: POST /api/tts/synthesize returns WAV audio.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ..services.tts_null import NullTTSService
    from ..services.tts_service import TTSService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tts", tags=["tts"])

# Set by main.py after TTS initialization
_tts: TTSService | NullTTSService | None = None


def set_tts(tts: TTSService | NullTTSService) -> None:
    """Inject TTS reference from main.py."""
    global _tts  # noqa: PLW0603
    _tts = tts


class SynthesizeRequest(BaseModel):
    """Request body for TTS synthesis."""

    text: str = Field(..., min_length=1, max_length=5000, description="Text to synthesize")
    voice: str | None = Field(default=None, description="Override voice name")
    speed: float | None = Field(default=None, ge=0.25, le=4.0, description="Speech speed multiplier")


@router.post("/synthesize")
async def synthesize(request: SynthesizeRequest) -> Response:
    """Synthesize text to WAV audio.

    Returns WAV audio bytes with appropriate content type.
    """
    if _tts is None:
        raise HTTPException(status_code=503, detail="TTS service not initialized")

    audio_bytes = await _tts.synthesize(
        text=request.text,
        voice=request.voice,
        speed=request.speed,
    )

    if not audio_bytes:
        raise HTTPException(status_code=503, detail="TTS synthesis produced no audio")

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={"Content-Disposition": 'inline; filename="speech.wav"'},
    )


@router.get("/voices")
async def list_voices() -> dict:
    """List available TTS voices and current configuration."""
    if _tts is None:
        raise HTTPException(status_code=503, detail="TTS service not initialized")

    return {
        "current_voice": getattr(_tts, "voice", None),
        "current_speed": getattr(_tts, "speed", 1.0),
        "status": _tts.health(),
    }
