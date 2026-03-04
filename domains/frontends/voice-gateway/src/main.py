"""Voice Gateway Service -- main entry point.

FastAPI app providing voice interaction for HomeIQ via STT, TTS,
and wake word detection with pipeline orchestration.
"""

from __future__ import annotations

import logging
import sys

from fastapi.responses import JSONResponse
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from . import __version__
from .api import admin_router, tts_router, voice_router
from .config import settings
from .services.stt_service import create_stt_service
from .services.tts_service import create_tts_service
from .services.voice_pipeline import VoicePipeline
from .services.wake_word_service import create_wake_word_service


def _configure_logging() -> None:
    """Configure logging for the service."""
    try:
        from homeiq_observability.logging_config import setup_logging

        setup_logging(settings.service_name)
    except ImportError:
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )


_configure_logging()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global service components
# ---------------------------------------------------------------------------
pipeline: VoicePipeline | None = None


async def _startup() -> None:
    """Initialize all voice components and wire the pipeline."""
    global pipeline  # noqa: PLW0603

    logger.info("Starting %s v%s", settings.service_name, __version__)

    # Create services with null-object fallbacks
    stt = await create_stt_service(
        model_size=settings.stt_model_size,
        language=settings.stt_language,
        compute_type=settings.stt_compute_type,
        enabled=settings.stt_enabled,
    )

    tts = await create_tts_service(
        voice=settings.tts_voice,
        speed=settings.tts_speed,
        sample_rate=settings.tts_sample_rate,
        enabled=settings.tts_enabled,
    )

    wake_word = await create_wake_word_service(
        model_name=settings.wake_word_model,
        threshold=settings.wake_word_threshold,
        enabled=settings.wake_word_enabled,
    )

    # Create and start pipeline
    pipeline = VoicePipeline(stt=stt, tts=tts, wake_word=wake_word)
    await pipeline.startup()

    # Inject pipeline into routers
    voice_router.set_pipeline(pipeline)
    admin_router.set_pipeline(pipeline)
    tts_router.set_tts(pipeline.tts)

    logger.info(
        "Voice pipeline ready: stt=%s tts=%s wake_word=%s",
        stt.name,
        tts.name,
        wake_word.name,
    )


async def _shutdown() -> None:
    """Graceful shutdown of all voice components."""
    logger.info("Shutting down %s", settings.service_name)

    if pipeline:
        await pipeline.stt.shutdown()
        await pipeline.tts.shutdown()
        await pipeline.wake_word.shutdown()
        await pipeline.shutdown()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup, name="voice_components")
lifespan.on_shutdown(_shutdown, name="voice_components")

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

health = StandardHealthCheck(
    service_name=settings.service_name,
    version=__version__,
)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="Voice Gateway Service",
    version=__version__,
    description="Voice interface for HomeIQ -- STT, TTS, wake word, and pipeline orchestration",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)

# Register routers
app.include_router(voice_router.router)
app.include_router(tts_router.router)
app.include_router(admin_router.router)


# ---------------------------------------------------------------------------
# Detailed health endpoint
# ---------------------------------------------------------------------------


@app.get("/health/details")
async def health_details() -> JSONResponse:
    """Detailed health check with component-level status."""
    if not pipeline:
        return JSONResponse(
            content={"status": "unavailable", "detail": "Pipeline not initialized"},
            status_code=503,
        )

    result = pipeline.health()
    result["version"] = __version__
    result["service"] = settings.service_name

    all_ok = all(
        c.get("status") in {"loaded", "disabled"}
        for c in result["components"].values()
    )
    result["status"] = "healthy" if all_ok else "degraded"
    status_code = 200 if all_ok else 503

    return JSONResponse(content=result, status_code=status_code)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        log_level="info",
    )
