"""
HA AI Agent Service - Tier 1 Context Injection
Epic AI-19: Foundation for conversational AI agent with context injection

Responsibilities:
- Tier 1 context injection (entity summaries, areas, services, capabilities, sun info)
- Context caching and management
- OpenAI GPT-5.1 integration preparation
"""

import logging
import sys

from homeiq_resilience import ServiceLifespan, create_app

from .api.chat_endpoints import router as chat_router
from .api.conversation_endpoints import router as conversation_router
from .api.core_endpoints import router as core_router
from .api.dependencies import set_services
from .api.device_suggestions_endpoints import router as device_suggestions_router
from .api.health_endpoints import router as health_router
from .clients.data_api_client import DataAPIClient
from .clients.ha_client import HomeAssistantClient
from .config import Settings
from .database import init_database
from .services.context_builder import ContextBuilder
from .services.conversation_service import ConversationService
from .services.openai_client import OpenAIClient
from .services.prompt_assembly_service import PromptAssemblyService
from .services.tool_service import ToolService


def _configure_logging() -> None:
    """Configure logging for the service."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


# ---------------------------------------------------------------------------
# Settings (module-level singleton)
# ---------------------------------------------------------------------------
settings = Settings()
_configure_logging()
logger = logging.getLogger(__name__)

# Global instances populated during startup
context_builder: ContextBuilder | None = None
tool_service: ToolService | None = None
conversation_service: ConversationService | None = None
prompt_assembly_service: PromptAssemblyService | None = None
openai_client: OpenAIClient | None = None
group_health = None  # GroupHealthCheck -- initialized in lifespan


# ---------------------------------------------------------------------------
# Startup / Shutdown helpers
# ---------------------------------------------------------------------------

def _get_secret(field: object) -> str | None:
    """Extract secret value or return None."""
    if field is None:
        return None
    return field.get_secret_value()


async def _init_group_health() -> object:
    """Probe dependencies and build GroupHealthCheck."""
    from homeiq_resilience import GroupHealthCheck, wait_for_dependency

    data_api_ok = await wait_for_dependency(
        url=settings.data_api_url, name="data-api", max_retries=10,
    )
    device_intel_ok = await wait_for_dependency(
        url=settings.device_intelligence_url,
        name="device-intelligence-service",
        max_retries=5,
    )
    if not data_api_ok:
        logger.warning("data-api unavailable -- entity resolution will be degraded")
    if not device_intel_ok:
        logger.warning("device-intelligence unavailable -- device context limited")

    gh = GroupHealthCheck(group_name="automation-intelligence", version="1.0.0")
    gh.register_dependency("data-api", settings.data_api_url)
    gh.register_dependency(
        "device-intelligence-service", settings.device_intelligence_url,
    )
    gh.register_dependency("ai-automation-service", settings.ai_automation_service_url)
    if not data_api_ok:
        gh.add_degraded_feature("entity-resolution (data-api unreachable)")
    if not device_intel_ok:
        gh.add_degraded_feature("device-context (device-intelligence unreachable)")
    return gh


def _build_clients() -> tuple:
    """Create all HTTP clients for external services."""
    from .clients.ai_automation_client import AIAutomationClient
    from .clients.hybrid_flow_client import HybridFlowClient
    from .clients.yaml_validation_client import YAMLValidationClient

    ha_client = HomeAssistantClient(
        ha_url=settings.ha_url,
        access_token=settings.ha_token.get_secret_value(),
        timeout=settings.ha_timeout,
    )
    data_api_client = DataAPIClient(
        base_url=settings.data_api_url,
        api_key=_get_secret(settings.data_api_key),
    )
    automation_key = _get_secret(settings.ai_automation_api_key)
    ai_automation_client = AIAutomationClient(
        base_url=settings.ai_automation_service_url, api_key=automation_key,
    )
    hybrid_flow_client = HybridFlowClient(
        base_url=settings.ai_automation_service_url, api_key=automation_key,
    )
    yaml_validation_client = YAMLValidationClient(
        base_url=settings.yaml_validation_service_url,
        api_key=_get_secret(settings.yaml_validation_api_key),
    )
    return (
        ha_client, data_api_client, ai_automation_client,
        hybrid_flow_client, yaml_validation_client,
    )


# ---------------------------------------------------------------------------
# Startup / Shutdown hooks for ServiceLifespan
# ---------------------------------------------------------------------------

async def _startup_services() -> None:
    """Initialize all service components during startup."""
    global context_builder, tool_service, conversation_service
    global prompt_assembly_service, openai_client, group_health

    # Initialize database
    db_ok = await init_database(settings.database_url)
    if db_ok:
        logger.info("Database initialized")
    else:
        logger.warning("Database unavailable -- starting in degraded mode")

    group_health = await _init_group_health()

    # Initialize context builder
    cb = ContextBuilder(settings)
    await cb.initialize()
    logger.info("Context builder initialized")
    context_builder = cb

    # Initialize clients
    ha_cl, dapi_cl, ai_auto_cl, hybrid_cl, yaml_cl = _build_clients()

    oc = OpenAIClient(settings)
    logger.info("OpenAI client initialized")
    openai_client = oc

    ts = ToolService(
        ha_cl, dapi_cl, ai_auto_cl, yaml_cl,
        oc.client if oc else None,
    )
    if hasattr(ts, "tool_handler"):
        ts.tool_handler.hybrid_flow_client = hybrid_cl
        ts.tool_handler.use_hybrid_flow = settings.use_hybrid_flow
    tool_service = ts

    cs = ConversationService(settings, cb)
    pas = PromptAssemblyService(settings, cb, cs)
    conversation_service = cs
    prompt_assembly_service = pas

    set_services(
        settings=settings, conversation_service=cs,
        prompt_assembly_service=pas, openai_client=oc, tool_service=ts,
    )
    logger.info("HA AI Agent Service started successfully")


async def _shutdown_services() -> None:
    """Run cleanup tasks on shutdown."""
    global context_builder, tool_service, conversation_service
    global prompt_assembly_service, openai_client, group_health

    if conversation_service:
        try:
            from .database import get_session
            from .services.conversation_persistence import cleanup_old_conversations

            async for session in get_session():
                deleted = await cleanup_old_conversations(
                    session, settings.conversation_ttl_days,
                )
                if deleted > 0:
                    logger.info("Cleaned up %d old conversations", deleted)
        except Exception as e:
            logger.warning("Error during conversation cleanup: %s", e)

    if context_builder:
        await context_builder.close()
    if tool_service:
        if tool_service.ha_client:
            await tool_service.ha_client.close()
        if tool_service.data_api_client:
            await tool_service.data_api_client.close()

    context_builder = None
    tool_service = None
    conversation_service = None
    prompt_assembly_service = None
    openai_client = None
    group_health = None


# ---------------------------------------------------------------------------
# Lifespan (ServiceLifespan)
# ---------------------------------------------------------------------------

lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_services, name="services")
lifespan.on_shutdown(_shutdown_services, name="services")


# ---------------------------------------------------------------------------
# App (create_app factory -- CORS, request-id, timing, exception handler)
# ---------------------------------------------------------------------------

app = create_app(
    title="HA AI Agent Service",
    version="1.0.0",
    description="Tier 1 Context Injection for Home Assistant AI Agent",
    lifespan=lifespan.handler,
    cors_origins=settings.get_cors_origins_list(),
)

# Routers
app.include_router(health_router)
app.include_router(core_router)
app.include_router(chat_router)
app.include_router(conversation_router)
app.include_router(device_suggestions_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
    )
