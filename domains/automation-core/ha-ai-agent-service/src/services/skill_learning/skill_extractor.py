"""
Skill Extractor (Epic 70, Story 70.1).

Analyzes successful multi-turn conversations and extracts reusable
procedures into skills. Runs as fire-and-forget after conversation ends.

Trigger heuristics (from Hermes skill_manager_tool.py):
- Complex task succeeds after 5+ tool-calling iterations
- Error handling overcomes obstacles during conversation
- User corrections lead to successful outcome
- User explicitly says "remember this" or "save this pattern"
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Trigger heuristics
MIN_ITERATIONS_FOR_SKILL = 5
SAVE_KEYWORDS = frozenset({
    "remember this", "save this", "save this pattern",
    "remember how", "keep this", "store this",
})


def should_extract_skill(
    iterations: int,
    tool_calls: list[Any],
    assistant_content: str,
    user_messages: list[str],
) -> bool:
    """Determine if a conversation warrants skill extraction.

    Args:
        iterations: Number of OpenAI loop iterations.
        tool_calls: List of tool calls made during the conversation.
        assistant_content: Final assistant response.
        user_messages: All user messages in the conversation.

    Returns:
        True if this conversation should produce a skill.
    """
    # Explicit user request
    for msg in user_messages:
        if any(kw in msg.lower() for kw in SAVE_KEYWORDS):
            return True

    # Complex task with many iterations
    if iterations >= MIN_ITERATIONS_FOR_SKILL and len(tool_calls) >= 2:
        return True

    return False


def extract_skill_metadata(
    user_messages: list[str],
    tool_calls: list[dict[str, Any]],
    assistant_content: str,
) -> dict[str, Any]:
    """Extract skill metadata from a conversation.

    Returns a dict suitable for SkillStore.create().
    """
    # Derive category from tool calls
    tool_names = {tc.get("name", "") for tc in tool_calls}
    category = _categorize_from_tools(tool_names)

    # Extract area from messages
    area_pattern = _extract_area_pattern(user_messages)

    # Build trigger types
    trigger_types = _extract_trigger_types(tool_names)

    # Build name and description from first user message
    first_msg = user_messages[0] if user_messages else "Unnamed skill"
    name = first_msg[:100].strip()
    description = f"Procedure extracted from conversation: {first_msg[:200]}"

    # Build body (step-by-step from tool calls)
    body = _build_skill_body(user_messages, tool_calls, assistant_content)

    return {
        "name": name,
        "description": description,
        "category": category,
        "area_pattern": area_pattern,
        "trigger_types": trigger_types,
        "body": body,
    }


def _categorize_from_tools(tool_names: set[str]) -> str:
    """Map tool names to skill category."""
    if "create_automation_from_prompt" in tool_names or "preview_automation_from_prompt" in tool_names:
        return "automation"
    if any("light" in t for t in tool_names):
        return "lighting"
    if any("climate" in t or "temperature" in t for t in tool_names):
        return "climate"
    if any("switch" in t for t in tool_names):
        return "device_control"
    if any("scene" in t or "script" in t for t in tool_names):
        return "scene"
    return "general"


def _extract_area_pattern(user_messages: list[str]) -> str | None:
    """Try to extract an area/room name from user messages."""
    common_areas = [
        "kitchen", "living room", "bedroom", "bathroom", "office",
        "garage", "basement", "attic", "garden", "patio",
        "hallway", "dining room", "laundry", "nursery",
    ]
    all_text = " ".join(user_messages).lower()
    for area in common_areas:
        if area in all_text:
            return area
    return None


def _extract_trigger_types(tool_names: set[str]) -> list[str]:
    """Map tool names to automation trigger types."""
    triggers = []
    if "create_automation_from_prompt" in tool_names:
        triggers.append("automation_creation")
    if any("control" in t for t in tool_names):
        triggers.append("device_control")
    if any("scene" in t for t in tool_names):
        triggers.append("scene_activation")
    return triggers or ["general"]


def _build_skill_body(
    user_messages: list[str],
    tool_calls: list[dict[str, Any]],
    assistant_content: str,
) -> str:
    """Build markdown body for the skill."""
    lines = ["## Procedure\n"]

    # Steps from tool calls
    for i, tc in enumerate(tool_calls, 1):
        name = tc.get("name", "unknown")
        args = tc.get("arguments", "{}")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except (json.JSONDecodeError, TypeError):
                pass
        lines.append(f"{i}. Call `{name}`")
        if isinstance(args, dict):
            for k, v in args.items():
                val = str(v)[:100]
                lines.append(f"   - {k}: {val}")
        lines.append("")

    # Final outcome
    lines.append("## Expected Outcome\n")
    lines.append(assistant_content[:500] if assistant_content else "Task completed successfully.")
    lines.append("")

    # Context
    if user_messages:
        lines.append("## Original Request\n")
        lines.append(user_messages[0][:300])

    return "\n".join(lines)
