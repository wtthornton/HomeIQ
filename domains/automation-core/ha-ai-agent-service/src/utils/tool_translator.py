"""Tool schema translation between OpenAI and Anthropic formats.

Epic 97: Prompt Caching & Claude Provider
Story 97.4: Bidirectional tool schema translation.

OpenAI Responses API format:
    {"type": "function", "name": "...", "description": "...", "parameters": {...}}

Anthropic Messages API format:
    {"name": "...", "description": "...", "input_schema": {...}}
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def openai_tools_to_anthropic(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert OpenAI function calling schemas to Anthropic tool use schemas.

    Args:
        tools: List of OpenAI tool definitions.

    Returns:
        List of Anthropic tool definitions.
    """
    anthropic_tools: list[dict[str, Any]] = []
    for tool in tools:
        # OpenAI Responses API format: top-level name/description/parameters
        name = tool.get("name", "")
        description = tool.get("description", "")
        parameters = tool.get("parameters", {"type": "object", "properties": {}})

        # Fallback: legacy OpenAI format with nested "function" key
        if not name and "function" in tool:
            func = tool["function"]
            name = func.get("name", "")
            description = func.get("description", "")
            parameters = func.get("parameters", {"type": "object", "properties": {}})

        anthropic_tools.append({
            "name": name,
            "description": description,
            "input_schema": parameters,
        })

    return anthropic_tools


def anthropic_tool_use_to_openai(tool_use_block: Any) -> dict[str, Any]:
    """Convert an Anthropic tool_use response block to OpenAI tool_calls format.

    Args:
        tool_use_block: Anthropic ToolUseBlock (has .id, .name, .input).

    Returns:
        OpenAI-compatible tool_call dict.
    """
    tool_input = getattr(tool_use_block, "input", {})
    return {
        "id": getattr(tool_use_block, "id", ""),
        "type": "function",
        "function": {
            "name": getattr(tool_use_block, "name", ""),
            "arguments": json.dumps(tool_input) if isinstance(tool_input, dict) else str(tool_input),
        },
    }


def build_anthropic_tool_result(tool_use_id: str, result: str) -> dict[str, Any]:
    """Build an Anthropic tool_result message block.

    Args:
        tool_use_id: The tool_use block ID from the assistant response.
        result: The tool execution result as a string.

    Returns:
        Anthropic-compatible tool_result content block.
    """
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": result,
    }


def openai_messages_to_anthropic(
    messages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    """Convert OpenAI message list to Anthropic format.

    Separates the system message (first message) from conversation messages
    and converts assistant tool_calls / tool results to Anthropic format.

    Args:
        messages: OpenAI-format messages (system first, then user/assistant/tool).

    Returns:
        Tuple of (anthropic_messages, system_prompt_text).
    """
    if not messages:
        return [], ""

    # Extract system prompt
    system_text = ""
    start_idx = 0
    if messages[0].get("role") == "system":
        system_text = messages[0].get("content", "")
        start_idx = 1

    anthropic_messages: list[dict[str, Any]] = []

    for msg in messages[start_idx:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "user":
            anthropic_messages.append({"role": "user", "content": content})

        elif role == "assistant":
            # Build content blocks
            blocks: list[dict[str, Any]] = []
            if content:
                blocks.append({"type": "text", "text": content})

            tool_calls = msg.get("tool_calls")
            if tool_calls:
                for tc in tool_calls:
                    func = tc.get("function", tc)
                    args_str = func.get("arguments", "{}")
                    try:
                        args = json.loads(args_str) if isinstance(args_str, str) else args_str
                    except json.JSONDecodeError:
                        args = {}
                    blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": func.get("name", ""),
                        "input": args,
                    })

            anthropic_messages.append({
                "role": "assistant",
                "content": blocks if blocks else content,
            })

        elif role == "tool":
            # Tool result → user message with tool_result content block
            anthropic_messages.append({
                "role": "user",
                "content": [
                    build_anthropic_tool_result(
                        tool_use_id=msg.get("tool_call_id", ""),
                        result=content if isinstance(content, str) else json.dumps(content),
                    )
                ],
            })

    return anthropic_messages, system_text
