"""
API Dependencies
Epic AI-20 Story AI20.4: Chat API Endpoints
Story 30.1: Memory Extraction

Dependency injection functions for FastAPI endpoints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException

from ..config import Settings
from ..services.conversation_service import ConversationService
from ..services.openai_client import OpenAIClient
from ..services.prompt_assembly_service import PromptAssemblyService
from ..services.tool_service import ToolService

if TYPE_CHECKING:
    from ..services.memory_extractor import MemoryExtractor

# These will be set by main.py during startup
_settings: Settings | None = None
_conversation_service: ConversationService | None = None
_prompt_assembly_service: PromptAssemblyService | None = None
_openai_client: OpenAIClient | None = None
_tool_service: ToolService | None = None
_memory_extractor: MemoryExtractor | None = None


def set_services(
    settings: Settings,
    conversation_service: ConversationService,
    prompt_assembly_service: PromptAssemblyService,
    openai_client: OpenAIClient,
    tool_service: ToolService,
    memory_extractor: MemoryExtractor | None = None,
):
    """Set service instances (called from main.py during startup)"""
    global _settings, _conversation_service, _prompt_assembly_service
    global _openai_client, _tool_service, _memory_extractor
    _settings = settings
    _conversation_service = conversation_service
    _prompt_assembly_service = prompt_assembly_service
    _openai_client = openai_client
    _tool_service = tool_service
    _memory_extractor = memory_extractor


def get_settings() -> Settings:
    """Get settings instance"""
    if not _settings:
        raise HTTPException(status_code=503, detail="Service not ready")
    return _settings


def get_conversation_service() -> ConversationService:
    """Get conversation service instance"""
    if not _conversation_service:
        raise HTTPException(status_code=503, detail="Service not ready")
    return _conversation_service


def get_prompt_assembly_service() -> PromptAssemblyService:
    """Get prompt assembly service instance"""
    if not _prompt_assembly_service:
        raise HTTPException(status_code=503, detail="Service not ready")
    return _prompt_assembly_service


def get_openai_client() -> OpenAIClient:
    """Get OpenAI client instance"""
    if not _openai_client:
        raise HTTPException(status_code=503, detail="Service not ready")
    return _openai_client


def get_tool_service() -> ToolService:
    """Get tool service instance"""
    if not _tool_service:
        raise HTTPException(status_code=503, detail="Service not ready")
    return _tool_service


def get_memory_extractor() -> MemoryExtractor | None:
    """Get memory extractor instance (may be None if disabled)"""
    return _memory_extractor

