"""
API Request/Response Models
Epic AI-20 Story AI20.4: Chat API Endpoints

Pydantic 2.9+ models for request validation and response formatting.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""

    message: str = Field(..., description="User message to send to the agent")
    conversation_id: str | None = Field(
        None, description="Optional conversation ID (creates new if not provided)"
    )
    refresh_context: bool = Field(
        False, description="Force context refresh (default: False, uses cache)"
    )
    # Epic AI-20.9: Conversation metadata for new conversations
    title: str | None = Field(
        None, max_length=200, description="Optional title for new conversation (max 200 chars)"
    )
    source: str | None = Field(
        None, description="Conversation source: user, proactive, or pattern (default: user)"
    )
    # Proactive Suggestions Enhancement: Hidden context for LLM
    hidden_context: dict[str, Any] | None = Field(
        None, 
        description="Structured context to inject into system prompt (not shown to user). "
                    "Useful for passing automation hints like game_time, team_colors, trigger_type."
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Turn on the kitchen lights",
                "conversation_id": "conv-123",
                "refresh_context": False,
                "title": "Kitchen lighting request",
                "source": "user",
                "hidden_context": {
                    "game_time": "7:00 PM",
                    "team_colors": ["#B4975A", "#333F48"],
                    "trigger_type": "state_change",
                    "trigger_entity": "sensor.vgk_team_tracker"
                }
            }
        }
    )


class ToolCall(BaseModel):
    """Tool call information"""

    id: str = Field(..., description="Tool call ID")
    name: str = Field(..., description="Tool name")
    arguments: dict[str, Any] = Field(..., description="Tool arguments")


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""

    message: str = Field(..., description="Assistant response message")
    conversation_id: str = Field(..., description="Conversation ID")
    tool_calls: list[ToolCall] = Field(
        default_factory=list, description="Tool calls made by the agent"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (token counts, model, etc.)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "I've turned on the kitchen lights.",
                "conversation_id": "conv-123",
                "tool_calls": [
                    {
                        "id": "call_abc123",
                        "name": "call_service",
                        "arguments": {"domain": "light", "service": "turn_on", "entity_id": "light.kitchen"},
                    }
                ],
                "metadata": {
                    "model": "gpt-4o-mini",
                    "tokens_used": 150,
                    "response_time_ms": 1200,
                },
            }
        }
    )

