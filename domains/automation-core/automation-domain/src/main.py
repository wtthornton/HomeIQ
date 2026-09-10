"""automation-domain: one process for the agent, authoring and proactive slices.

TAP-7275. `ha-ai-agent-service`, `ai-automation-service-new` and
`proactive-agent-service` were three containers with three FastAPI apps, three
lifespans and three `/health` endpoints. This module is the single app: it
registers each slice's startup and shutdown hooks on one lifespan, mounts every
surviving router at the path it already had, and answers one `/health` that
reports all three (`api/health.py`).

Route paths are unchanged on purpose -- consumers were repointed at a new
hostname, not at new paths, so a caller that reached
`http://ai-automation-service-new:8025/api/suggestions/list` now reaches
`http://automation-domain:8030/api/suggestions/list`. The only routes that did
not survive verbatim are the three per-service `/health` endpoints, which one
endpoint replaces because only the first registration would ever be reached.

The LLM slice is not here at all any more: every model call is an AgentForge
workflow run (`agentforge_client.py`), so no provider SDK and no provider
credential is in this image.
"""

from __future__ import annotations

import logging

from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from .agent import main as agent_main
from .agent.api.chat_endpoints import router as chat_router
from .agent.api.conversation_endpoints import router as conversation_router
from .agent.api.core_endpoints import router as core_router
from .agent.api.device_suggestions_endpoints import router as device_suggestions_router
from .api.health import router as health_router
from .authoring import main as authoring_main
from .authoring.api import (
    analysis_router,
    automation_compile_router,
    automation_lifecycle_router,
    automation_plan_router,
    automation_validate_router,
    automation_yaml_validate_router,
    blueprint_validate_router,
    pattern_router,
    preference_router,
    scene_validate_router,
    script_validate_router,
    setup_validate_router,
    synergy_router,
)
from .authoring.api.deployment_router import router as deployment_router
from .authoring.api.health_router import metrics_router as authoring_metrics_router
from .authoring.api.middlewares import AuthenticationMiddleware, RateLimitMiddleware
from .authoring.api.suggestion_router import router as suggestion_router
from .authoring.main import (
    OBSERVABILITY_AVAILABLE,
    CorrelationMiddleware,
    instrument_fastapi,
    register_error_handlers,
)
from .proactive import main as proactive_main
from .proactive.api.health import router as proactive_health_router
from .proactive.api.proactive_router import router as proactive_router
from .proactive.api.suggestions import router as suggestions_router
from .proactive.api.task_router import router as task_router
from .proactive.database import close_database as proactive_close_database

logger = logging.getLogger(__name__)

#: Process settings. The agent slice's Settings carries the AgentForge fields
#: the merged /health reports; each slice keeps its own Settings for its own
#: database schema and service URLs.
settings = agent_main.settings

_agentforge_reachable = False


def agentforge_reachable() -> bool:
    """Whether startup actually reached AgentForge.

    Separate from "a key is configured" on purpose: a configured-but-
    unreachable AgentForge is precisely the shape of failure a config-only
    check reports as healthy (TAP-7365).
    """
    return _agentforge_reachable


async def _probe_agentforge() -> None:
    """Record whether AgentForge answers, without failing startup on it."""
    global _agentforge_reachable  # noqa: PLW0603
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.agentforge_url.rstrip('/')}/health")
        _agentforge_reachable = response.status_code == 200
    except Exception as exc:  # noqa: BLE001 - reported through /health, not raised
        logger.warning("AgentForge unreachable at %s: %s", settings.agentforge_url, exc)
        _agentforge_reachable = False
    if _agentforge_reachable:
        logger.info("AgentForge reachable at %s", settings.agentforge_url)


# ---------------------------------------------------------------------------
# Lifespan: one per slice, in dependency order.
# ---------------------------------------------------------------------------
lifespan = ServiceLifespan("automation-domain", graceful=False)
lifespan.on_startup(_probe_agentforge, name="agentforge")
lifespan.on_startup(agent_main._startup_services, name="agent")
lifespan.on_startup(authoring_main._startup, name="authoring")
lifespan.on_startup(proactive_main._startup_dependencies, name="proactive-dependencies")
lifespan.on_startup(proactive_main._startup_db, name="proactive-database")
lifespan.on_startup(proactive_main._startup_memory, name="proactive-memory")
lifespan.on_startup(proactive_main._startup_scheduler, name="proactive-scheduler")
lifespan.on_startup(proactive_main._startup_cron_scheduler, name="proactive-cron")
lifespan.on_startup(proactive_main._startup_agent_loop, name="proactive-agent-loop")

lifespan.on_shutdown(proactive_main._shutdown_agent_loop, name="proactive-agent-loop")
lifespan.on_shutdown(proactive_main._shutdown_cron_scheduler, name="proactive-cron")
lifespan.on_shutdown(proactive_main._shutdown_scheduler, name="proactive-scheduler")
lifespan.on_shutdown(proactive_main._shutdown_memory, name="proactive-memory")
lifespan.on_shutdown(proactive_close_database, name="proactive-database")
lifespan.on_shutdown(authoring_main._shutdown, name="authoring")
lifespan.on_shutdown(agent_main._shutdown_services, name="agent")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = create_app(
    title="HomeIQ automation-domain",
    version="1.0.0",
    description=(
        "Conversational agent, automation authoring, and proactive suggestions. "
        "LLM inference runs on AgentForge."
    ),
    lifespan=lifespan.handler,
    cors_origins=settings.get_cors_origins_list(),
    cors_allow_credentials=True,
)

if register_error_handlers:
    register_error_handlers(app)

# Carried from ai-automation-service-new, which instrumented its own app. The
# merged process is instrumented once, under its own service name.
if OBSERVABILITY_AVAILABLE:
    try:
        instrument_fastapi(app, "automation-domain")
        app.add_middleware(CorrelationMiddleware)
    except Exception:
        logger.warning("Failed to instrument FastAPI", exc_info=True)

# Both middlewares came from the authoring service and enforce only on that
# slice's route prefixes -- see AUTHORING_PATH_PREFIXES in authoring/api/middlewares.py.
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(RateLimitMiddleware)

# The merged /health is registered FIRST so it wins: Starlette serves the first
# matching route, and each slice's own /health is deliberately not mounted.
app.include_router(health_router)

# StandardHealthCheck supplies /ready. Its /health would shadow nothing because
# the merged one above is already registered.
_standard_health = StandardHealthCheck(service_name="automation-domain", version="1.0.0")
app.include_router(_standard_health.router)

# --- agent slice (former ha-ai-agent-service, port 8030) -------------------
app.include_router(core_router)
app.include_router(chat_router)
app.include_router(conversation_router)
app.include_router(device_suggestions_router)
# NOT mounted: agent/api/eval_routing_endpoints.py. ha-ai-agent-service declared
# that router and never included it (its main.py mounted health, core, chat,
# conversation and device_suggestions only, re-read at base sha dbc32495), so
# its ten /api/v1/model-routing, /api/v1/eval-alerts and /api/v1/cost-tracking
# routes answered 404 in production while their unit tests passed against the
# router object. Mounting them here would newly expose surface this lane has no
# way to exercise; the collapse map records all ten as dropped-with-reason
# (never reachable), which is what they already were.

# --- authoring slice (former ai-automation-service-new, port 8025) ---------
# Only GET /health/validation-metrics from the authoring health module. Its own
# GET /health is deliberately not mounted -- the merged endpoint above answers
# that path, and a second registration would be unreachable code plus a
# duplicate OpenAPI operation id.
app.include_router(authoring_metrics_router, tags=["health"])
app.include_router(suggestion_router, tags=["suggestions"])
app.include_router(deployment_router, tags=["deployment"])
app.include_router(pattern_router.router, tags=["patterns"])
app.include_router(synergy_router.router, tags=["synergies"])
app.include_router(analysis_router.router, tags=["analysis"])
app.include_router(preference_router.router, tags=["preferences"])
app.include_router(automation_plan_router.router, tags=["automation"])
app.include_router(automation_validate_router.router, tags=["automation"])
app.include_router(automation_yaml_validate_router.router, tags=["automation"])
app.include_router(automation_compile_router.router, tags=["automation"])
app.include_router(automation_lifecycle_router.router, tags=["automation"])
app.include_router(blueprint_validate_router.router)
app.include_router(setup_validate_router.router)
app.include_router(scene_validate_router.router)
app.include_router(script_validate_router.router)

# --- proactive slice (former proactive-agent-service, port 8031) -----------
# proactive_health_router carries only GET /health, which the merged endpoint
# already answers; it is imported so the scheduler-status setter it exports
# stays reachable, and deliberately NOT mounted.
_ = proactive_health_router
app.include_router(suggestions_router)
app.include_router(task_router)
app.include_router(proactive_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
    )
