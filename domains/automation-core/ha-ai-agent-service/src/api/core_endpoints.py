"""Core API endpoints for HA AI Agent Service.

Context injection, system prompts, YAML validation, and tool execution.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..tools.tool_schemas import get_tool_schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["core"])


class ValidationRequest(BaseModel):
    """Request model for YAML validation."""

    yaml_content: str
    normalize: bool = True
    validate_entities: bool = True
    validate_services: bool = False


def _require(obj: object, name: str = "Service") -> None:
    """Raise 503 if the service dependency is not ready."""
    if obj is None:
        raise HTTPException(status_code=503, detail=f"{name} not ready")


@router.get("/context")
async def get_context() -> dict:
    """Get Tier 1 context for OpenAI agent."""
    from ..main import context_builder

    _require(context_builder, "Context builder")
    try:
        context = await context_builder.build_context()
        return {"context": context, "token_count": len(context.split())}
    except Exception as e:
        logger.exception("Error building context")
        raise HTTPException(status_code=500, detail="Failed to build context") from e


@router.get("/system-prompt")
async def get_system_prompt() -> dict:
    """Get the system prompt for the OpenAI agent."""
    from ..main import context_builder

    _require(context_builder, "Context builder")
    try:
        prompt = context_builder.get_system_prompt()
        return {"system_prompt": prompt, "token_count": len(prompt.split())}
    except Exception as e:
        logger.exception("Error getting system prompt")
        raise HTTPException(status_code=500, detail="Failed to get system prompt") from e


@router.get("/complete-prompt")
async def get_complete_prompt() -> dict:
    """Get complete system prompt with context injection."""
    from ..main import context_builder

    _require(context_builder, "Context builder")
    try:
        prompt = await context_builder.build_complete_system_prompt()
        return {"system_prompt": prompt, "token_count": len(prompt.split())}
    except Exception as e:
        logger.exception("Error building complete prompt")
        raise HTTPException(status_code=500, detail="Failed to build complete prompt") from e


@router.post("/validation/validate")
async def validate_yaml(request: ValidationRequest) -> dict:
    """Validate automation YAML using the validation chain."""
    from ..main import tool_service

    _require(tool_service, "Tool service")
    try:
        result = await tool_service.tool_handler.validation_chain.validate(
            request.yaml_content,
        )
        return result.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error validating YAML")
        raise HTTPException(status_code=500, detail="Failed to validate YAML") from e


@router.get("/tools")
async def get_tools() -> dict:
    """Get available tool schemas for OpenAI function calling."""
    from ..main import tool_service

    _require(tool_service, "Tool service")
    try:
        tools = get_tool_schemas()
        return {
            "tools": tools,
            "count": len(tools),
            "tool_names": [t["function"]["name"] for t in tools],
        }
    except Exception as e:
        logger.exception("Error getting tools")
        raise HTTPException(status_code=500, detail="Failed to get tools") from e


@router.post("/tools/execute")
async def execute_tool(request: dict) -> dict:
    """Execute a tool call."""
    from ..main import tool_service

    _require(tool_service, "Tool service")
    try:
        tool_name = request.get("tool_name")
        if not tool_name:
            raise HTTPException(status_code=400, detail="tool_name is required")
        return await tool_service.execute_tool(tool_name, request.get("arguments", {}))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error executing tool")
        raise HTTPException(status_code=500, detail="Failed to execute tool") from e


@router.post("/tools/execute-openai")
async def execute_tool_openai(request: dict) -> dict:
    """Execute a tool call in OpenAI format."""
    from ..main import tool_service

    _require(tool_service, "Tool service")
    try:
        return await tool_service.execute_tool_call(request)
    except Exception as e:
        logger.exception("Error executing tool call")
        raise HTTPException(status_code=500, detail="Failed to execute tool call") from e
