"""Alembic bootstrap for zeek-network-service.

The migrations under ``alembic/versions`` create ``devices.network_device_
fingerprints`` and its three siblings. They were copied into the image from the
first release but nothing ever invoked them, so on every deployment the tables
were absent, :meth:`FingerprintService.upsert_dhcp` raised ``UndefinedTable``
into a broad ``except`` in the parser loop, and ``/devices/discovered``
answered ``[]`` while ``/health`` answered ``healthy``.

So this module does two things, and the second matters as much as the first:
it runs the migrations at startup, and it reports whether they succeeded so
the service can decline to claim a working fingerprint store it does not have.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from homeiq_observability.logging_config import setup_logging

logger = setup_logging("zeek-migrations")

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
    """Bring the ``devices`` schema to head.

    Returns ``True`` when the schema is at head and the fingerprint tables can
    be relied on. Returns ``False`` on any failure, having logged the cause —
    the caller degrades the affected endpoints rather than serving an empty
    list that reads like "no devices found".
    """
    alembic_ini = _SERVICE_ROOT / "alembic.ini"
    if not alembic_ini.exists():
        logger.error("alembic.ini not found at %s; fingerprint tables unavailable", alembic_ini)
        return False

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _upgrade_to_head, str(alembic_ini))
    except Exception:
        logger.exception("Alembic upgrade failed; fingerprint tables unavailable")
        return False

    logger.info("Alembic migrations at head")
    return True


__all__ = ["run_migrations"]
