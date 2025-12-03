"""
HA AI Agent Service - Tier 1 Context Injection
Epic AI-19: Foundation for conversational AI agent with context injection

Responsibilities:
- Tier 1 context injection (entity summaries, areas, services, capabilities, sun info)
- Context caching and management
- OpenAI GPT-5.1 integration preparation
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .api.chat_endpoints import router as chat_router
from .api.conversation_endpoints import router as conversation_router
from .api.dependencies import set_services
from .clients.data_api_client import DataAPIClient
from .clients.ha_client import HomeAssistantClient
from .config import Settings
from .database import init_database
from .services.context_builder import ContextBuilder
from .services.conversation_service import ConversationService
from .services.openai_client import OpenAIClient
from .services.prompt_assembly_service import PromptAssemblyService
from .services.tool_service import ToolService
from .tools.tool_schemas import get_tool_schemas

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances populated during startup
context_builder: ContextBuilder | None = None
tool_service: ToolService | None = None
conversation_service: ConversationService | None = None
prompt_assembly_service: PromptAssemblyService | None = None
openai_client: OpenAIClient | None = None
settings: Settings | None = None


def _parse_allowed_origins() -> list[str]:
    """Parse comma-delimited allowed origins from environment."""
    raw_origins = os.getenv("HA_AI_AGENT_ALLOWED_ORIGINS")
    if raw_origins:
        parsed = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        if parsed:
            return parsed
    return ["http://localhost:3000", "http://localhost:3001"]


ALLOWED_ORIGINS = _parse_allowed_origins()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize services on startup, cleanup on shutdown"""
    global context_builder, tool_service, conversation_service, prompt_assembly_service, openai_client, settings

    logger.info("🚀 Starting HA AI Agent Service...")
    try:
        # Load settings
        settings = Settings()
        logger.info(f"✅ Settings loaded (HA URL: {settings.ha_url})")

        # Initialize database
        await init_database(settings.database_url)
        logger.info("✅ Database initialized")

        # Initialize context builder
        context_builder = ContextBuilder(settings)
        await context_builder.initialize()
        logger.info("✅ Context builder initialized")

        # Initialize tool service
        ha_client = HomeAssistantClient(
            ha_url=settings.ha_url,
            access_token=settings.ha_token,
            timeout=settings.ha_timeout
        )
        data_api_client = DataAPIClient(base_url=settings.data_api_url)
        tool_service = ToolService(ha_client, data_api_client)
        logger.info("✅ Tool service initialized")

        # Initialize OpenAI client (Epic AI-20)
        openai_client = OpenAIClient(settings)
        logger.info("✅ OpenAI client initialized")

        # Initialize conversation service (Epic AI-20)
        conversation_service = ConversationService(settings, context_builder)
        logger.info("✅ Conversation service initialized")

        # Initialize prompt assembly service (Epic AI-20)
        prompt_assembly_service = PromptAssemblyService(
            settings, context_builder, conversation_service
        )
        logger.info("✅ Prompt assembly service initialized")

        # Set services for dependency injection (Epic AI-20)
        set_services(
            settings=settings,
            conversation_service=conversation_service,
            prompt_assembly_service=prompt_assembly_service,
            openai_client=openai_client,
            tool_service=tool_service,
        )
        logger.info("✅ Dependency injection configured")

        logger.info("✅ HA AI Agent Service started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to start HA AI Agent Service: {e}", exc_info=True)
        raise

    yield

    # Cleanup on shutdown
    # Run conversation cleanup before shutdown
    if conversation_service and settings:
        try:
            from .database import get_session
            from .services.conversation_persistence import cleanup_old_conversations
            async for session in get_session():
                deleted = await cleanup_old_conversations(
                    session, settings.conversation_ttl_days
                )
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} old conversations on shutdown")
        except Exception as e:
            logger.warning(f"Error during conversation cleanup: {e}")
    logger.info("🛑 HA AI Agent Service shutting down")
    if context_builder:
        await context_builder.close()
    if tool_service:
        # Close clients used by tool service
        if tool_service.ha_client:
            await tool_service.ha_client.close()
        if tool_service.data_api_client:
            await tool_service.data_api_client.close()
    context_builder = None
    tool_service = None
    conversation_service = None
    prompt_assembly_service = None
    openai_client = None
    settings = None


# Create FastAPI app
app = FastAPI(
    title="HA AI Agent Service",
    description="Tier 1 Context Injection for Home Assistant AI Agent",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# Register chat router (Epic AI-20 Story AI20.4)
app.include_router(chat_router)

# Register conversation management router (Epic AI-20 Story AI20.5)
app.include_router(conversation_router)


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not context_builder:
        raise HTTPException(status_code=503, detail="Service not ready")

    return {
        "status": "healthy",
        "service": "ha-ai-agent-service",
        "version": "1.0.0"
    }


@app.get("/api/v1/context")
async def get_context():
    """Get Tier 1 context for OpenAI agent"""
    if not context_builder:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        context = await context_builder.build_context()
        return {
            "context": context,
            "token_count": len(context.split())  # Rough token estimate
        }
    except Exception as e:
        logger.exception("Error building context")
        raise HTTPException(status_code=500, detail=f"Failed to build context: {str(e)}") from e


@app.get("/api/v1/system-prompt")
async def get_system_prompt():
    """Get the system prompt for the OpenAI agent"""
    if not context_builder:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        system_prompt = context_builder.get_system_prompt()
        return {
            "system_prompt": system_prompt,
            "token_count": len(system_prompt.split())  # Rough token estimate
        }
    except Exception as e:
        logger.exception("Error getting system prompt")
        raise HTTPException(status_code=500, detail=f"Failed to get system prompt: {str(e)}") from e


@app.get("/api/v1/complete-prompt")
async def get_complete_prompt():
    """Get complete system prompt with context injection"""
    if not context_builder:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        complete_prompt = await context_builder.build_complete_system_prompt()
        return {
            "system_prompt": complete_prompt,
            "token_count": len(complete_prompt.split())  # Rough token estimate
        }
    except Exception as e:
        logger.exception("Error building complete prompt")
        raise HTTPException(status_code=500, detail=f"Failed to build complete prompt: {str(e)}") from e


@app.get("/api/v1/tools")
async def get_tools():
    """Get available tool schemas for OpenAI function calling"""
    if not tool_service:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        tools = get_tool_schemas()
        return {
            "tools": tools,
            "count": len(tools),
            "tool_names": [tool["function"]["name"] for tool in tools]
        }
    except Exception as e:
        logger.exception("Error getting tools")
        raise HTTPException(status_code=500, detail=f"Failed to get tools: {str(e)}") from e


@app.post("/api/v1/tools/execute")
async def execute_tool(request: dict):
    """
    Execute a tool call.

    Request body:
    {
        "tool_name": "get_entity_state",
        "arguments": {
            "entity_id": "light.kitchen"
        }
    }
    """
    if not tool_service:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        tool_name = request.get("tool_name")
        arguments = request.get("arguments", {})

        if not tool_name:
            raise HTTPException(status_code=400, detail="tool_name is required")

        result = await tool_service.execute_tool(tool_name, arguments)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error executing tool")
        raise HTTPException(status_code=500, detail=f"Failed to execute tool: {str(e)}") from e


@app.post("/api/v1/tools/execute-openai")
async def execute_tool_openai(request: dict):
    """
    Execute a tool call in OpenAI format.

    Request body (OpenAI tool call format):
    {
        "id": "call_...",
        "type": "function",
        "function": {
            "name": "get_entity_state",
            "arguments": "{\"entity_id\": \"light.kitchen\"}"
        }
    }
    """
    if not tool_service:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        result = await tool_service.execute_tool_call(request)
        return result
    except Exception as e:
        logger.exception("Error executing tool call")
        raise HTTPException(status_code=500, detail=f"Failed to execute tool call: {str(e)}") from e


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8030)

