"""Alembic bootstrap for ha-setup-service.

This service's five tables were defined only as SQLAlchemy models. Nothing
created them: no ``create_all``, nothing in ``init-schemas.sql``, and until
TAP-6492 no migration existed at all — ``alembic/versions`` held a single
``.gitkeep`` while the Dockerfile copied alembic into the image and went
straight to uvicorn. They exist on long-lived instances because someone made
them by hand.

The consequence was invisible rather than loud. ``_persist_blockers`` catches
``Exception`` and ``GET /api/v1/init/blockers`` still answers 200 with a fresh
survey, so a caller saw success while the stored table was never populated —
the same shape as the Zeek fingerprint store that read healthy while empty.

So this module does two things, and the second matters as much as the first:
it runs the migrations at startup, and it reports whether they succeeded so
the service can decline to claim a working store it does not have.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from homeiq_observability.logging_config import setup_logging

logger = setup_logging("ha-setup-migrations")

#: ``src/migrations.py`` -> service root, where ``alembic.ini`` is copied.
_SERVICE_ROOT = Path(__file__).resolve().parent.parent


def _upgrade_to_head(alembic_ini: str) -> None:
    """Run ``alembic upgrade head`` synchronously, off the event loop."""
    from alembic import command
    from alembic.config import Config

    # env.py honours this: without it, alembic's fileConfig() resets the root
    # logger and every log line after startup disappears.
    cfg = Config(alembic_ini, attributes={"configure_logger": False})
    command.upgrade(cfg, "head")


async def run_migrations() -> bool:
    """Bring this service's tables in the ``devices`` schema to head.

    Returns ``True`` when the schema is at head and the tables can be relied
    on. Returns ``False`` on any failure, having logged the cause — the caller
    degrades the affected endpoints rather than persisting into nothing and
    reporting success.
    """
    alembic_ini = _SERVICE_ROOT / "alembic.ini"
    if not alembic_ini.exists():
        logger.error("alembic.ini not found at %s; setup tables unavailable", alembic_ini)
        return False

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _upgrade_to_head, str(alembic_ini))
    except Exception:
        logger.exception("Alembic upgrade failed; setup tables unavailable")
        return False

    logger.info("Alembic migrations at head")
    return True


__all__ = ["run_migrations"]
