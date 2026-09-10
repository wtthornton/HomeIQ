"""
API Dependencies
Epic AI-20 Story AI20.4: Chat API Endpoints
Story 30.1: Memory Extraction

Dependency injection functions for FastAPI endpoints.
"""

from typing import Any

from fastapi import HTTPException

from ..config import Settings
from ..services.conversation_service import ConversationService
from ..services.llm_client import AgentChatClient
from ..services.prompt_assembly_service import PromptAssemblyService
from ..services.tool_service import ToolService

_STARTUP_INCOMPLETE = (
    "Service not ready: chat dependencies were not initialized. "
    "Usually missing AGENTFORGE_API_KEY or a startup error; see automation-domain logs."
)

# These will be set by main.py during startup
_settings: Settings | None = None
_conversation_service: ConversationService | None = None
_prompt_assembly_service: PromptAssemblyService | None = None
_chat_client: AgentChatClient | None = None
_tool_service: ToolService | None = None
_memory_extractor: Any | None = None


def chat_dependencies_ready() -> bool:
    """True after successful startup (set_services). Used by /health for accurate readiness."""
    return _conversation_service is not None


def clear_services() -> None:
    """Reset DI state (shutdown). Keeps /health consistent when the app stops."""
    global _settings, _conversation_service, _prompt_assembly_service
    global _chat_client, _tool_service, _memory_extractor
    _settings = None
    _conversation_service = None
    _prompt_assembly_service = None
    _chat_client = None
    _tool_service = None
    _memory_extractor = None


def set_services(
    settings: Settings,
    conversation_service: ConversationService,
    prompt_assembly_service: PromptAssemblyService,
    chat_client: AgentChatClient,
    tool_service: ToolService,
    memory_extractor: Any | None = None,
):
    """Set service instances (called from main.py during startup)"""
    global _settings, _conversation_service, _prompt_assembly_service
    global _chat_client, _tool_service, _memory_extractor
    _settings = settings
    _conversation_service = conversation_service
    _prompt_assembly_service = prompt_assembly_service
    _chat_client = chat_client
    _tool_service = tool_service
    _memory_extractor = memory_extractor


def get_settings() -> Settings:
    """Get settings instance"""
    if not _settings:
        raise HTTPException(status_code=503, detail=_STARTUP_INCOMPLETE)
    return _settings


def get_conversation_service() -> ConversationService:
    """Get conversation service instance"""
    if not _conversation_service:
        raise HTTPException(status_code=503, detail=_STARTUP_INCOMPLETE)
    return _conversation_service


def get_prompt_assembly_service() -> PromptAssemblyService:
    """Get prompt assembly service instance"""
    if not _prompt_assembly_service:
        raise HTTPException(status_code=503, detail=_STARTUP_INCOMPLETE)
    return _prompt_assembly_service


def get_chat_client() -> AgentChatClient:
    """Get the AgentForge-backed chat client instance"""
    if not _chat_client:
        raise HTTPException(status_code=503, detail=_STARTUP_INCOMPLETE)
    return _chat_client


def get_tool_service() -> ToolService:
    """Get tool service instance"""
    if not _tool_service:
        raise HTTPException(status_code=503, detail=_STARTUP_INCOMPLETE)
    return _tool_service


def get_memory_extractor() -> Any | None:
    """Get memory extractor instance (may be None if disabled)"""
    return _memory_extractor
