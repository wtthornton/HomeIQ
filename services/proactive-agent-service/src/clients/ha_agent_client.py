"""
HA AI Agent Client for Proactive Agent Service

HTTP client for communicating with the HA AI Agent Service (agent-to-agent communication).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class HAAgentClient:
    """Client for communicating with HA AI Agent Service"""

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
        self.client = httpx.AsyncClient(
            timeout=float(timeout),
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        logger.info(f"HA AI Agent client initialized with base_url={self.base_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=False  # Don't reraise - return None for graceful degradation
    )
    async def send_message(
        self,
        message: str,
        conversation_id: str | None = None,
        refresh_context: bool = False,
        title: str | None = None,
        source: str = "proactive",  # Default to proactive for this client
        hidden_context: dict[str, Any] | None = None,  # NEW: Structured context for LLM
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
                payload["hidden_context"] = hidden_context  # NEW: Pass structured context

            logger.debug(f"Sending message to HA AI Agent: {message[:100]}...")
            response = await self.client.post(
                f"{self.base_url}/api/v1/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            # Validate response structure
            if not self._validate_response(data):
                logger.warning("Invalid response structure from HA AI Agent")
                return None

            logger.info(
                f"Received response from HA AI Agent: conversation={data.get('conversation_id')}, "
                f"tool_calls={len(data.get('tool_calls', []))}"
            )
            return data

        except httpx.HTTPStatusError as e:
            error_msg = f"HA AI Agent returned {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"HTTP error communicating with HA AI Agent: {error_msg}")
            return None  # Graceful degradation
        except httpx.ConnectError as e:
            error_msg = f"Could not connect to HA AI Agent at {self.base_url}"
            logger.warning(f"Connection error: {error_msg}")
            return None  # Graceful degradation
        except httpx.TimeoutException as e:
            error_msg = f"HA AI Agent request timed out after {self.timeout} seconds"
            logger.warning(f"Timeout error: {error_msg}")
            return None  # Graceful degradation
        except Exception as e:
            logger.error(f"Unexpected error communicating with HA AI Agent: {str(e)}", exc_info=True)
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
        """Close HTTP client connection pool"""
        await self.client.aclose()
        logger.debug("HA AI Agent client closed")

