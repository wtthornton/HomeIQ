"""
LangChain prototype for Ask-AI prompt construction.

The goal is to demonstrate how LangChain's prompt templates can orchestrate
system/user messages while still reusing the existing UnifiedPromptBuilder
payload. The resulting dictionary mirrors the builder's output so downstream
code remains unchanged.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)


def _truncate(text: str, limit: int = 2000) -> str:
    """Trim long context blocks while preserving readability."""
    if len(text) <= limit:
        return text
    ellipsis = "...[truncated]"
    return f"{text[: limit - len(ellipsis)]}{ellipsis}"


def _format_entities_for_prompt(entities: List[Dict[str, Any]], max_items: int = 10) -> str:
    """Create a compact list of key entity details for the LangChain prompt."""
    if not entities:
        return "No entities resolved."

    lines: List[str] = []
    for entity in entities[:max_items]:
        entity_id = entity.get("entity_id", "unknown")
        friendly = entity.get("friendly_name") or entity.get("name") or entity_id
        domain = entity.get("domain") or (entity_id.split(".")[0] if "." in entity_id else "unknown")
        area = entity.get("area_name") or entity.get("area_id") or "unknown area"
        lines.append(f"- {friendly} ({entity_id}, domain={domain}, area={area})")

    if len(entities) > max_items:
        lines.append(f"- ...and {len(entities) - max_items} more")
    return "\n".join(lines)


def _format_clarifications(clarification_context: Optional[Dict[str, Any]]) -> str:
    if not clarification_context or not clarification_context.get("questions_and_answers"):
        return "No clarification answers provided."

    formatted: List[str] = []
    for idx, qa in enumerate(clarification_context["questions_and_answers"], start=1):
        question = qa.get("question", "Unknown question")
        answer = qa.get("answer", "No answer")
        selected = qa.get("selected_entities") or []
        selected_str = f" | Selected entities: {', '.join(selected)}" if selected else ""
        formatted.append(f"{idx}. Q: {question}\n   A: {answer}{selected_str}")
    return "\n".join(formatted)


def build_prompt_with_langchain(
    *,
    query: str,
    entities: List[Dict[str, Any]],
    base_prompt: Dict[str, Any],
    entity_context_json: str = "",
    clarification_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Wrap the unified prompt with LangChain templates for structured assembly.

    Args:
        query: Original user request.
        entities: Enriched entity dictionaries used for context summaries.
        base_prompt: Prompt dictionary returned by UnifiedPromptBuilder.
        entity_context_json: Rich entity context generated earlier in the flow.
        clarification_context: Optional clarification metadata.

    Returns:
        Dictionary conforming to the UnifiedPromptBuilder contract.
    """

    system_prompt = base_prompt.get("system_prompt", "")
    user_prompt = base_prompt.get("user_prompt", "")

    clarifications_block = _format_clarifications(clarification_context)
    entities_block = _format_entities_for_prompt(entities)
    enriched_block = _truncate(entity_context_json) if entity_context_json else "No enriched context."

    chat_template = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(
                """{baseline_system}

You are using LangChain prompt assembly. Maintain all original safety and device
guardrails while incorporating clarifications and enriched context summaries."""
            ),
            HumanMessagePromptTemplate.from_template(
                """User request:
{query}

Detected entities:
{entities_block}

Clarification (if any):
{clarifications_block}

Enriched context (truncated to fit):
{enriched_block}

Base prompt:
{baseline_user}"""
            ),
        ]
    )

    formatted_messages = chat_template.format_prompt(
        baseline_system=system_prompt,
        baseline_user=user_prompt,
        query=query,
        entities_block=entities_block,
        clarifications_block=clarifications_block,
        enriched_block=enriched_block,
    ).to_messages()

    # LangChain returns a list of BaseMessage instances. The first is system, the
    # second is human for our template configuration.
    lc_system = next((msg.content for msg in formatted_messages if msg.type == "system"), system_prompt)
    lc_user = next((msg.content for msg in formatted_messages if msg.type == "human"), user_prompt)

    prompt_dict = dict(base_prompt)
    prompt_dict["system_prompt"] = lc_system
    prompt_dict["user_prompt"] = lc_user
    prompt_dict["metadata"] = {
        **prompt_dict.get("metadata", {}),
        "langchain": {
            "template": "ask_ai_chain_v1",
            "clarification_included": bool(clarification_context and clarification_context.get("questions_and_answers")),
            "entity_sample_count": min(len(entities), 10),
        },
    }
    return prompt_dict


