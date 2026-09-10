"""Collectors Service — one production process for the six pure-HTTP collectors.

Folds weather-api, sports-api, air-quality-service, electricity-pricing-service,
calendar-service, and smart-meter-service into one FastAPI app, per TAP-7274.
Each former service is a `CollectorAdapter` (see `adapters/base.py`) mounted at
its exact former path (no shared prefix) via `app.include_router`. Every route
is wrapped in a per-adapter timeout (`adapters.base.with_adapter_timeout`) so
one adapter's hung upstream cannot stall the other five; each adapter's
startup/shutdown hooks are isolated by `ServiceLifespan`'s own per-hook
try/except, and each runs its own independent asyncio background task exactly
as it did as a standalone service — merging into one process changes where
those tasks run, not how they're isolated from each other.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeiq_observability.logging_config import setup_logging
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from . import __version__
from .adapters.air_quality import adapter as air_quality_adapter
from .adapters.calendar import adapter as calendar_adapter
from .adapters.electricity_pricing import adapter as electricity_pricing_adapter
from .adapters.smart_meter import adapter as smart_meter_adapter
from .adapters.sports import adapter as sports_adapter
from .adapters.weather import adapter as weather_adapter
from .config import settings

if TYPE_CHECKING:
    from .adapters import CollectorAdapter

SERVICE_NAME = settings.service_name
SERVICE_VERSION = __version__

logger = setup_logging(SERVICE_NAME)

# Order matters only for OpenAPI/route-listing readability — every adapter's
# paths are disjoint (see docs/architecture/collapse-map.md section C1), so
# there is no shadowing between them.
ADAPTERS: list[CollectorAdapter] = [
    weather_adapter,
    sports_adapter,
    air_quality_adapter,
    electricity_pricing_adapter,
    calendar_adapter,
    smart_meter_adapter,
]

# ---------------------------------------------------------------------------
# Lifespan — one ServiceLifespan composing all six adapters' startup/shutdown.
# ServiceLifespan already wraps each hook in its own try/except (graceful
# mode), so one adapter failing to start does not prevent the others from
# starting; shutdown hooks run in reverse order, each independently guarded.
# ---------------------------------------------------------------------------

_lifespan = ServiceLifespan(SERVICE_NAME)
for _adapter in ADAPTERS:
    _lifespan.on_startup(_adapter.startup, name=f"{_adapter.name}-startup")
for _adapter in reversed(ADAPTERS):
    _lifespan.on_shutdown(_adapter.shutdown, name=f"{_adapter.name}-shutdown")

# ---------------------------------------------------------------------------
# Health check — one shared StandardHealthCheck; each adapter registers its
# own readiness checks under a name-prefixed key.
# ---------------------------------------------------------------------------

_health = StandardHealthCheck(service_name=SERVICE_NAME, version=SERVICE_VERSION)
for _adapter in ADAPTERS:
    _adapter.register_health(_health)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="Collectors Service",
    version=SERVICE_VERSION,
    description=(
        "One process for the six pure-HTTP collectors: weather, sports, "
        "air-quality, electricity-pricing, calendar, and smart-meter."
    ),
    lifespan=_lifespan.handler,
    health_check=_health,
    cors_origins=settings.get_cors_origins_list(),
)

# create_app() registers a generic GET "/" root endpoint before the ADAPTERS
# loop below includes the sports router, and FastAPI matches routes in
# registration order — so without this, the factory's generic root would win
# and sports-api's own "/" would never be reached. Drop the generic one so
# the sports router's "/" is the only handler for that path (a capability
# gain: sports-api's root is now actually reachable), rather than forking
# the shared app_factory just to make its root endpoint optional.
app.router.routes = [
    route
    for route in app.router.routes
    if not (getattr(route, "path", None) == "/" and "GET" in getattr(route, "methods", ()))
]

for _adapter in ADAPTERS:
    app.include_router(_adapter.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        reload=True,
    )
