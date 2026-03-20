"""Tests for tool schema translation (Story 97.4).

Round-trip tests: OpenAI format → Anthropic format → call → response → OpenAI format.
"""

from __future__ import annotations

import json

import pytest

from src.utils.tool_translator import (
    build_anthropic_tool_result,
    openai_messages_to_anthropic,
    openai_tools_to_anthropic,
)


# ---------------------------------------------------------------------------
# Fixtures — sample tool schemas from tool_schemas.py
# ---------------------------------------------------------------------------

SAMPLE_OPENAI_TOOLS = [
    {
        "type": "function",
        "name": "preview_automation_from_prompt",
        "description": "Generate a detailed preview of a Home Assistant automation.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_prompt": {"type": "string", "description": "User request"},
                "automation_yaml": {"type": "string", "description": "YAML config"},
                "alias": {"type": "string", "description": "Automation name"},
            },
            "required": ["user_prompt", "automation_yaml", "alias"],
        },
    },
    {
        "type": "function",
        "name": "create_automation_from_prompt",
        "description": "Create a Home Assistant automation.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_prompt": {"type": "string"},
                "automation_yaml": {"type": "string"},
                "alias": {"type": "string"},
            },
            "required": ["user_prompt", "automation_yaml", "alias"],
        },
    },
    {
        "type": "function",
        "name": "suggest_automation_enhancements",
        "description": "Generate 5 enhancement suggestions.",
        "parameters": {
            "type": "object",
            "properties": {
                "automation_yaml": {"type": "string"},
                "original_prompt": {"type": "string"},
                "conversation_id": {"type": "string"},
            },
            "required": ["original_prompt", "conversation_id"],
        },
    },
]


class TestOpenAIToolsToAnthropic:
    """Test OpenAI → Anthropic tool schema conversion."""

    def test_converts_all_three_ha_tools(self):
        result = openai_tools_to_anthropic(SAMPLE_OPENAI_TOOLS)
        assert len(result) == 3

    def test_tool_name_preserved(self):
        result = openai_tools_to_anthropic(SAMPLE_OPENAI_TOOLS)
        names = [t["name"] for t in result]
        assert "preview_automation_from_prompt" in names
        assert "create_automation_from_prompt" in names
        assert "suggest_automation_enhancements" in names

    def test_description_preserved(self):
        result = openai_tools_to_anthropic(SAMPLE_OPENAI_TOOLS)
        assert result[0]["description"] == SAMPLE_OPENAI_TOOLS[0]["description"]

    def test_parameters_mapped_to_input_schema(self):
        result = openai_tools_to_anthropic(SAMPLE_OPENAI_TOOLS)
        for i, tool in enumerate(result):
            assert "input_schema" in tool
            assert tool["input_schema"] == SAMPLE_OPENAI_TOOLS[i]["parameters"]
            # Anthropic format should NOT have "parameters" key
            assert "parameters" not in tool

    def test_no_type_field_in_anthropic(self):
        result = openai_tools_to_anthropic(SAMPLE_OPENAI_TOOLS)
        for tool in result:
            assert "type" not in tool

    def test_empty_tools_list(self):
        assert openai_tools_to_anthropic([]) == []

    def test_legacy_openai_format_with_function_wrapper(self):
        legacy = [{
            "type": "function",
            "function": {
                "name": "my_tool",
                "description": "A tool",
                "parameters": {"type": "object", "properties": {}},
            },
        }]
        result = openai_tools_to_anthropic(legacy)
        assert result[0]["name"] == "my_tool"
        assert result[0]["description"] == "A tool"


class TestOpenAIMessagesToAnthropic:
    """Test OpenAI → Anthropic message format conversion."""

    def test_extracts_system_prompt(self):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
        ]
        anthropic_msgs, system_text = openai_messages_to_anthropic(messages)
        assert system_text == "You are a helpful assistant."
        assert len(anthropic_msgs) == 1
        assert anthropic_msgs[0]["role"] == "user"

    def test_user_message_preserved(self):
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "Turn on the lights"},
        ]
        anthropic_msgs, _ = openai_messages_to_anthropic(messages)
        assert anthropic_msgs[0]["content"] == "Turn on the lights"

    def test_assistant_with_tool_calls(self):
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "Create automation"},
            {
                "role": "assistant",
                "content": "I'll create that for you.",
                "tool_calls": [{
                    "id": "call_123",
                    "function": {
                        "name": "preview_automation_from_prompt",
                        "arguments": json.dumps({
                            "user_prompt": "lights on at sunset",
                            "automation_yaml": "alias: test",
                            "alias": "test",
                        }),
                    },
                }],
            },
        ]
        anthropic_msgs, _ = openai_messages_to_anthropic(messages)
        assistant_msg = anthropic_msgs[1]
        assert assistant_msg["role"] == "assistant"
        # Should have text + tool_use blocks
        blocks = assistant_msg["content"]
        assert any(b["type"] == "text" for b in blocks)
        assert any(b["type"] == "tool_use" for b in blocks)

    def test_tool_result_message(self):
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "tool", "content": '{"status": "ok"}', "tool_call_id": "call_123"},
        ]
        anthropic_msgs, _ = openai_messages_to_anthropic(messages)
        assert anthropic_msgs[0]["role"] == "user"
        block = anthropic_msgs[0]["content"][0]
        assert block["type"] == "tool_result"
        assert block["tool_use_id"] == "call_123"

    def test_empty_messages(self):
        msgs, sys = openai_messages_to_anthropic([])
        assert msgs == []
        assert sys == ""

    def test_no_system_message(self):
        messages = [{"role": "user", "content": "Hello"}]
        anthropic_msgs, system_text = openai_messages_to_anthropic(messages)
        assert system_text == ""
        assert len(anthropic_msgs) == 1


class TestBuildAnthropicToolResult:
    """Test tool result block construction."""

    def test_builds_correct_structure(self):
        result = build_anthropic_tool_result("call_abc", '{"yaml": "valid"}')
        assert result["type"] == "tool_result"
        assert result["tool_use_id"] == "call_abc"
        assert result["content"] == '{"yaml": "valid"}'


class TestRoundTrip:
    """End-to-end round-trip translation tests."""

    def test_tool_schema_round_trip_preserves_required_fields(self):
        """OpenAI → Anthropic preserves all required fields."""
        anthropic = openai_tools_to_anthropic(SAMPLE_OPENAI_TOOLS)
        for i, tool in enumerate(anthropic):
            original = SAMPLE_OPENAI_TOOLS[i]
            assert tool["name"] == original["name"]
            assert tool["description"] == original["description"]
            required = tool["input_schema"].get("required", [])
            assert required == original["parameters"].get("required", [])

    def test_multi_turn_conversation_translation(self):
        """Full conversation with tool calls translates correctly."""
        messages = [
            {"role": "system", "content": "You are HomeIQ AI agent."},
            {"role": "user", "content": "Turn on lights at sunset"},
            {
                "role": "assistant",
                "content": "Let me preview that.",
                "tool_calls": [{
                    "id": "call_1",
                    "function": {
                        "name": "preview_automation_from_prompt",
                        "arguments": '{"user_prompt": "lights at sunset", "automation_yaml": "alias: test", "alias": "test"}',
                    },
                }],
            },
            {
                "role": "tool",
                "content": '{"status": "preview_ready", "yaml": "alias: Sunset Lights"}',
                "tool_call_id": "call_1",
            },
            {"role": "user", "content": "Looks good, create it!"},
        ]

        anthropic_msgs, system = openai_messages_to_anthropic(messages)
        assert system == "You are HomeIQ AI agent."
        assert len(anthropic_msgs) == 4  # user, assistant, tool_result(user), user
