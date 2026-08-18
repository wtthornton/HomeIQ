"""Entrypoint: `python -m src.main` (HTTP by default; HOMEIQ_MCP_TRANSPORT=stdio for stdio)."""

from __future__ import annotations

import asyncio
import logging
import sys

from .config import ConfigError, load_settings
from .server import HomeIQMCP
from .tools import register_all


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"homeiq-mcp: {exc}", file=sys.stderr)
        return 2
    logging.basicConfig(
        level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    app = HomeIQMCP(settings)
    register_all(app.registry, app.backings)
    if settings.transport == "stdio":
        asyncio.run(app.run_stdio())
        return 0
    import uvicorn

    uvicorn.run(
        app.build_http_app(),
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
