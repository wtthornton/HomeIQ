"""
HA AI Agent Client for Proactive Agent Service

HTTP client for communicating with the HA AI Agent Service (agent-to-agent communication).
Uses CrossGroupClient for resilient cross-group calls with circuit breaker, retry,
and Bearer token authentication (Step 4.7).
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from homeiq_resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient

logger = logging.getLogger(__name__)

# Shared circuit breaker for all calls to automation-core group.
_automation_core_breaker = CircuitBreaker(name="automation-core")


class HAAgentClient:
    """Client for communicating with HA AI Agent Service via CrossGroupClient."""

    def __init__(
        self,
        base_url: str = "http://ha-ai-agent-service:8030",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize HA AI Agent client.

        Args:
            base_url: Base URL for HA AI Agent Service (default: http://ha-ai-agent-service:8030)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum retry attempts (default: 3)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries

        # Resolve auth token from environment (cross-group service auth).
        api_key = (
            os.getenv("HA_AGENT_API_KEY")
            or os.getenv("SERVICE_AUTH_TOKEN")
        )

        self._cross_client = CrossGroupClient(
            base_url=self.base_url,
            group_name="automation-core",
            timeout=float(timeout),
            max_retries=max_retries,
            auth_token=api_key,
            circuit_breaker=_automation_core_breaker,
        )

        logger.info("HA AI Agent client initialized with base_url=%s", self.base_url)

    async def send_message(
        self,
        message: str,
        conversation_id: str | None = None,
        refresh_context: bool = False,
        title: str | None = None,
        source: str = "proactive",  # Default to proactive for this client
        hidden_context: dict[str, Any] | None = None,  # Structured context for LLM
    ) -> dict[str, Any] | None:
        """
        Send a message to the HA AI Agent Service.

        Args:
            message: Message/prompt to send to the agent
            conversation_id: Optional conversation ID (creates new if not provided)
            refresh_context: Force context refresh (default: False)
            title: Optional title for new conversation (Epic AI-20.9)
            source: Conversation source - defaults to 'proactive' for this client (Epic AI-20.9)
            hidden_context: Optional structured context to inject into system prompt (not shown to user).
                           Useful for passing automation hints like game_time, team_colors, trigger_type.

        Returns:
            Dictionary with response:
            {
                "message": str,
                "conversation_id": str,
                "tool_calls": list,
                "metadata": dict
            }
            or None if unavailable/error
        """
        try:
            payload: dict[str, Any] = {
                "message": message,
                "refresh_context": refresh_context,
                "source": source,  # Epic AI-20.9: Mark as proactive
            }
            if conversation_id:
                payload["conversation_id"] = conversation_id
            if title:
                payload["title"] = title
            if hidden_context:
                payload["hidden_context"] = hidden_context

            logger.debug("Sending message to HA AI Agent: %s...", message[:100])
            response = await self._cross_client.call(
                "POST", "/api/v1/chat", json=payload,
            )
            response.raise_for_status()
            data = response.json()

            # Validate response structure
            if not self._validate_response(data):
                logger.warning("Invalid response structure from HA AI Agent")
                return None

            logger.info(
                "Received response from HA AI Agent: conversation=%s, tool_calls=%d",
                data.get('conversation_id'),
                len(data.get('tool_calls', [])),
            )
            return data

        except CircuitOpenError:
            logger.warning(
                "Circuit open for automation-core — HA AI Agent unavailable"
            )
            return None  # Graceful degradation
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error communicating with HA AI Agent: %d %s",
                e.response.status_code,
                e.response.text[:200],
            )
            return None  # Graceful degradation
        except httpx.HTTPError as e:
            logger.warning("Connection/timeout error to HA AI Agent: %s", e)
            return None  # Graceful degradation
        except Exception as e:
            logger.error(
                "Unexpected error communicating with HA AI Agent: %s", e,
                exc_info=True,
            )
            return None  # Graceful degradation

    def _validate_response(self, response: dict[str, Any]) -> bool:
        """
        Validate response structure from HA AI Agent.

        Args:
            response: Response dictionary

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["message", "conversation_id"]
        return all(field in response for field in required_fields)

    async def close(self):
        """No-op -- CrossGroupClient uses per-request clients."""
        logger.debug("HA AI Agent client closed (no-op with CrossGroupClient)")
