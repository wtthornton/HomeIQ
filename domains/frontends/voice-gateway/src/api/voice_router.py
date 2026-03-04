"""Voice WebSocket endpoints.

Story 26.4: WebSocket for streaming audio and receiving pipeline events.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from ..services.voice_pipeline import VoicePipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

# Set by main.py after pipeline initialization
_pipeline: VoicePipeline | None = None


def set_pipeline(pipeline: VoicePipeline) -> None:
    """Inject pipeline reference from main.py."""
    global _pipeline  # noqa: PLW0603
    _pipeline = pipeline


@router.websocket("/stream")
async def voice_stream(ws: WebSocket) -> None:
    """WebSocket endpoint for voice interaction.

    Client sends binary audio frames (16kHz, 16-bit PCM).
    Server responds with JSON messages:
      - {"type": "transcription", "text": "..."}
      - {"type": "response", "text": "...", "audio": "<base64 WAV>"}
      - {"type": "state", "state": "idle|listening|processing|speaking"}
      - {"type": "wakeword", "detected": true}
      - {"type": "error", "message": "..."}

    Client can also send JSON commands:
      - {"command": "stop"} -- stop current processing
      - {"command": "process"} -- process accumulated audio
    """
    if _pipeline is None:
        await ws.close(code=1011, reason="Pipeline not initialized")
        return

    await ws.accept()
    logger.info("Voice WebSocket connected")

    event_queue = _pipeline.subscribe()
    audio_buffer = bytearray()

    # Background task to forward pipeline events to WebSocket
    async def _forward_events() -> None:
        try:
            while True:
                event = await event_queue.get()
                msg: dict = {"type": event.event_type.lower()}
                if event.event_type == "STATE_CHANGED":
                    msg = {"type": "state", "state": event.data.get("state", "idle")}
                elif event.event_type == "TRANSCRIPTION":
                    msg = {"type": "transcription", "text": event.data.get("text", "")}
                elif event.event_type == "AGENT_RESPONSE":
                    msg = {"type": "agent_response", "text": event.data.get("text", "")}
                elif event.event_type == "WAKEWORD_DETECTED":
                    msg = {"type": "wakeword", "detected": True}
                await ws.send_json(msg)
        except (WebSocketDisconnect, Exception):
            pass

    forward_task = asyncio.create_task(_forward_events(), name="event-forwarder")

    try:
        while True:
            message = await ws.receive()

            if "bytes" in message and message["bytes"]:
                # Binary audio data
                audio_data = message["bytes"]

                # Check for wake word if enabled
                if _pipeline.wake_word.is_loaded:
                    detected = await _pipeline.check_wake_word(audio_data)
                    if detected:
                        audio_buffer.clear()

                audio_buffer.extend(audio_data)

                # Detect silence to auto-process
                if len(audio_buffer) > 16000 * 2:  # At least 1 second of audio
                    if _pipeline.detect_silence(audio_data):
                        result = await _pipeline.process_audio(bytes(audio_buffer))
                        audio_buffer.clear()
                        await _send_result(ws, result)

            elif "text" in message and message["text"]:
                import json

                try:
                    cmd = json.loads(message["text"])
                except (json.JSONDecodeError, TypeError):
                    continue

                command = cmd.get("command", "")

                if command == "process" and audio_buffer:
                    result = await _pipeline.process_audio(bytes(audio_buffer))
                    audio_buffer.clear()
                    await _send_result(ws, result)
                elif command == "stop":
                    audio_buffer.clear()
                    await ws.send_json({"type": "state", "state": "idle"})

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")
    except Exception:
        logger.exception("Voice WebSocket error")
    finally:
        forward_task.cancel()
        _pipeline.unsubscribe(event_queue)


async def _send_result(ws: WebSocket, result: dict) -> None:
    """Send pipeline result to WebSocket client."""
    if "error" in result:
        await ws.send_json({"type": "error", "message": result["error"]})
        return

    response: dict = {
        "type": "response",
        "transcription": result.get("transcription", ""),
        "text": result.get("response", ""),
    }

    audio = result.get("audio", b"")
    if audio:
        response["audio"] = base64.b64encode(audio).decode("ascii")

    await ws.send_json(response)
