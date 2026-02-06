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
from pydantic import BaseModel

from .api.chat_endpoints import router as chat_router
from .api.conversation_endpoints import router as conversation_router
from .api.device_suggestions_endpoints import router as device_suggestions_router
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


def _fix_database_permissions(settings: Settings) -> None:
    """
    Fix database directory permissions before initialization (Docker volume fix).
    
    Args:
        settings: Application settings containing database URL
    """
    if not settings.database_url.startswith("sqlite"):
        return
    
    from pathlib import Path
    import os
    import stat
    
    path_str = settings.database_url.split("///")[-1]
    db_path = Path(path_str)
    data_dir = db_path.parent
    
    # Fix permissions if directory exists (Docker volume might be root-owned)
    if not data_dir.exists():
        return
    
    try:
        current_uid = os.getuid() if hasattr(os, 'getuid') else None
        current_gid = os.getgid() if hasattr(os, 'getgid') else None
        
        # Try to fix directory permissions
        os.chmod(data_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
        if current_uid is not None and current_uid != 0:
            try:
                os.chown(data_dir, current_uid, current_gid)
            except (PermissionError, OSError):
                pass  # Can't change ownership, but chmod should help
        
        # Fix database file if it exists
        if db_path.exists():
            os.chmod(db_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH)
            if current_uid is not None and current_uid != 0:
                try:
                    os.chown(db_path, current_uid, current_gid)
                except (PermissionError, OSError):
                    pass
        
        logger.info(f"✅ Fixed permissions for {data_dir}")
    except Exception as e:
        logger.warning(f"⚠️  Could not fix permissions (non-fatal): {e}")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> None:
    """Initialize services on startup, cleanup on shutdown"""
    global context_builder, tool_service, conversation_service, prompt_assembly_service, openai_client, settings

    logger.info("🚀 Starting HA AI Agent Service...")
    try:
        # Load settings
        settings = Settings()
        logger.info(f"✅ Settings loaded (HA URL: {settings.ha_url})")

        # Fix database directory permissions before initialization (Docker volume fix)
        _fix_database_permissions(settings)
        
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
            access_token=settings.ha_token.get_secret_value(),
            timeout=settings.ha_timeout
        )
        data_api_client = DataAPIClient(base_url=settings.data_api_url)
        
        # Initialize AI Automation Service client for consolidated YAML validation
        from .clients.ai_automation_client import AIAutomationClient
        ai_automation_client = AIAutomationClient(
            base_url=settings.ai_automation_service_url,
            api_key=settings.ai_automation_api_key.get_secret_value() if settings.ai_automation_api_key else None
        )
        logger.info(f"✅ AI Automation Service client initialized ({settings.ai_automation_service_url})")
        
        # Initialize Hybrid Flow Client (Hybrid Flow Implementation)
        from .clients.hybrid_flow_client import HybridFlowClient
        hybrid_flow_client = HybridFlowClient(
            base_url=settings.ai_automation_service_url,
            api_key=settings.ai_automation_api_key.get_secret_value() if settings.ai_automation_api_key else None
        )
        logger.info(f"✅ Hybrid Flow client initialized ({settings.ai_automation_service_url})")
        
        # Initialize YAML Validation Service client (Epic 51, Story 51.5)
        from .clients.yaml_validation_client import YAMLValidationClient
        yaml_validation_client = YAMLValidationClient(
            base_url=settings.yaml_validation_service_url,
            api_key=settings.yaml_validation_api_key.get_secret_value() if settings.yaml_validation_api_key else None
        )
        logger.info(f"✅ YAML Validation Service client initialized ({settings.yaml_validation_service_url})")
        
        # Initialize OpenAI client (Epic AI-20) - needed for tool service enhancements
        openai_client = OpenAIClient(settings)
        logger.info("✅ OpenAI client initialized")
        
        tool_service = ToolService(
            ha_client, 
            data_api_client, 
            ai_automation_client, 
            yaml_validation_client, 
            openai_client.client if openai_client else None
        )
        # Update tool handler with hybrid flow client and settings
        if hasattr(tool_service, 'tool_handler'):
            tool_service.tool_handler.hybrid_flow_client = hybrid_flow_client
            tool_service.tool_handler.use_hybrid_flow = settings.use_hybrid_flow
            logger.info(f"✅ Hybrid Flow enabled: {settings.use_hybrid_flow}")
        logger.info("✅ Tool service initialized")

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
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-HomeIQ-API-Key"],
)


# Register chat router (Epic AI-20 Story AI20.4)
app.include_router(chat_router)

# Register conversation management router (Epic AI-20 Story AI20.5)
app.include_router(conversation_router)

# Register device suggestions router (Phase 2: Device-Based Automation Suggestions)
app.include_router(device_suggestions_router)


# API Endpoints
@app.get("/health")
async def health_check() -> dict:
    """
    Comprehensive health check endpoint.
    
    Verifies all dependencies in a single call:
    - Database connectivity
    - Home Assistant connection
    - Data API connection
    - Device Intelligence Service connection
    - OpenAI configuration
    - Context builder services
    """
    if not context_builder or not settings:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        from .services.health_check_service import HealthCheckService
        
        health_service = HealthCheckService(settings, context_builder)
        health_result = await health_service.comprehensive_health_check()
        await health_service.close()
        
        # Return appropriate status code based on overall health
        status_code = 200
        if health_result["status"] == "unhealthy":
            status_code = 503
        elif health_result["status"] == "degraded":
            status_code = 200  # Still operational, just degraded
        
        return health_result
    except Exception as e:
        logger.exception("Error during health check")
        raise HTTPException(
            status_code=503,
            detail="Health check failed"
        )


@app.get("/api/v1/context")
async def get_context() -> dict:
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
        raise HTTPException(status_code=500, detail="Failed to build context") from e


@app.get("/api/v1/system-prompt")
async def get_system_prompt() -> dict:
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
        raise HTTPException(status_code=500, detail="Failed to get system prompt") from e


@app.get("/api/v1/complete-prompt")
async def get_complete_prompt() -> dict:
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
        raise HTTPException(status_code=500, detail="Failed to build complete prompt") from e


class ValidationRequest(BaseModel):
    """Request model for YAML validation."""
    yaml_content: str
    normalize: bool = True
    validate_entities: bool = True
    validate_services: bool = False


@app.post("/api/v1/validation/validate")
async def validate_yaml(request: ValidationRequest) -> dict:
    """
    Validate automation YAML using validation chain.
    
    This endpoint uses the validation chain which tries multiple validation strategies
    in order (YAML Validation Service, AI Automation Service, Basic Validation) until
    one succeeds or all fail. This provides graceful fallback when validation services
    are unavailable.
    
    Args:
        request: Request body containing:
            - yaml_content: YAML string to validate
            - normalize: Optional, whether to normalize YAML (default: True)
            - validate_entities: Optional, whether to validate entities (default: True)
            - validate_services: Optional, whether to validate services (default: False)
    
    Returns:
        Validation result with:
            - valid: Whether validation passed
            - errors: List of error messages
            - warnings: List of warning messages
            - score: Validation score (0-100)
            - fixed_yaml: Normalized YAML if available
            - fixes_applied: List of fixes applied
            - strategy_used: Name of validation strategy that succeeded
            - services_unavailable: List of services that were unavailable
    """
    if not tool_service:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        # Use validation chain (handles fallback automatically)
        validation_result = await tool_service.tool_handler.validation_chain.validate(request.yaml_content)
        
        # Convert to dict (includes strategy_name and services_unavailable if available)
        return validation_result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error validating YAML")
        raise HTTPException(status_code=500, detail="Failed to validate YAML") from e


@app.get("/api/v1/tools")
async def get_tools() -> dict:
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
        raise HTTPException(status_code=500, detail="Failed to get tools") from e


@app.post("/api/v1/tools/execute")
async def execute_tool(request: dict) -> dict:
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
        raise HTTPException(status_code=500, detail="Failed to execute tool") from e


@app.post("/api/v1/tools/execute-openai")
async def execute_tool_openai(request: dict) -> dict:
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
        raise HTTPException(status_code=500, detail="Failed to execute tool call") from e


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8030)

