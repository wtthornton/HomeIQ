"""JSON-RPC client for the HomeIQ MCP server (TAP-5308).

The server (``domains/core-platform/homeiq-mcp``) speaks streamable-HTTP at
``POST <base>/mcp`` with ``json_response=True`` and ``stateless=True``: replies
are plain JSON rather than SSE frames, and no ``Mcp-Session-Id`` is minted, so
the ``initialize`` / ``notifications/initialized`` handshake is performed once
per client rather than per call. Authentication is a bearer token from
``HOMEIQ_MCP_READ_TOKENS``.

This module deliberately imports nothing from Home Assistant so the transport
and the response-budget rule can be exercised without a running instance.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from aiohttp import ClientError, ClientTimeout

if TYPE_CHECKING:
    from aiohttp import ClientSession

PROTOCOL_VERSION = "2025-06-18"
CLIENT_NAME = "homeiq-home-assistant"
CLIENT_VERSION = "0.1.0"

_HEADERS = {
    "Content-Type": "application/json",
    # The streamable-HTTP session manager rejects a request that does not accept
    # both encodings, even when it answers with plain JSON.
    "Accept": "application/json, text/event-stream",
}


class McpError(Exception):
    """A HomeIQ MCP call failed.

    ``code`` carries the server's machine-readable error code when it supplied
    one (``invalid_input``, ``not_found``, ``backing_unavailable``,
    ``contract_violation``), or a transport-level code otherwise.
    """

    def __init__(self, code: str, message: str) -> None:
        """Initialise the error."""
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class McpUnauthorizedError(McpError):
    """The MCP server rejected the bearer token."""


def payload_size(payload: dict[str, Any]) -> int:
    """Return the byte length of the payload as it is serialised to the agent."""
    return len(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def _largest_list_key(payload: dict[str, Any]) -> str | None:
    lists = {key: value for key, value in payload.items() if isinstance(value, list) and value}
    if not lists:
        return None
    return max(lists, key=lambda key: len(lists[key]))


def enforce_budget(payload: dict[str, Any], max_bytes: int, hint: str | None) -> dict[str, Any]:
    """Shrink ``payload`` to ``max_bytes``, mirroring the server's budget rule.

    The server applies the same rule before answering, so on a healthy path this
    is a no-op. It runs client-side as well because the payload is handed
    straight to a model: an oversized response is a context-window problem for
    Home Assistant regardless of which side produced it.
    """
    if payload_size(payload) <= max_bytes:
        return payload
    while payload_size(payload) > max_bytes:
        key = _largest_list_key(payload)
        if key is None:
            break
        rows = payload[key]
        # Halve, then step by one so large lists converge quickly and small ones exactly.
        drop = max(1, len(rows) // 2) if payload_size(payload) > 2 * max_bytes else 1
        del rows[len(rows) - drop :]
        payload["truncated"] = True
        if hint is not None:
            payload["hint"] = hint
        if isinstance(payload.get("count"), int):
            payload["count"] = len(rows)
    return payload


class HomeIQMcpClient:
    """Calls tools on the HomeIQ MCP server over JSON-RPC."""

    def __init__(self, session: ClientSession, base_url: str, token: str, timeout: float) -> None:
        """Initialise the client."""
        self._session = session
        self._endpoint = f"{base_url.rstrip('/')}/mcp"
        self._headers = {**_HEADERS, "Authorization": f"Bearer {token}"}
        self._timeout = ClientTimeout(total=timeout)
        self._request_id = 0
        self._handshake_lock = asyncio.Lock()
        self._initialized = False

    async def _send(self, body: dict[str, Any]) -> str:
        """Send one JSON-RPC message and return the raw response body."""
        try:
            response = await self._session.post(
                self._endpoint, json=body, headers=self._headers, timeout=self._timeout
            )
            async with response:
                if response.status in (401, 403):
                    raise McpUnauthorizedError(
                        "unauthorized", "the HomeIQ MCP server rejected the bearer token"
                    )
                if response.status >= 400:
                    raise McpError(
                        "http_error", f"HomeIQ MCP server returned HTTP {response.status}"
                    )
                return await response.text()
        except (TimeoutError, ClientError, OSError) as err:
            raise McpError("unreachable", f"cannot reach the HomeIQ MCP server: {err}") from err

    async def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request and return its ``result`` object."""
        raw = await self._send(
            {"jsonrpc": "2.0", "id": self._next_id(), "method": method, "params": params}
        )
        try:
            envelope: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as err:
            raise McpError("contract_violation", f"{method} returned a non-JSON body") from err

        if error := envelope.get("error"):
            raise McpError(str(error.get("code", "jsonrpc_error")), str(error.get("message", "")))
        result = envelope.get("result")
        if not isinstance(result, dict):
            raise McpError("contract_violation", f"{method} returned no result")
        return result

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _ensure_initialized(self) -> None:
        """Run the MCP handshake once per client."""
        async with self._handshake_lock:
            if self._initialized:
                return
            await self._request(
                "initialize",
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": CLIENT_NAME, "version": CLIENT_VERSION},
                },
            )
            await self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            self._initialized = True

    async def async_list_tools(self) -> list[dict[str, Any]]:
        """Return the tools the server currently advertises."""
        await self._ensure_initialized()
        result = await self._request("tools/list", {})
        return list(result.get("tools", []))

    async def async_call_tool(
        self, name: str, arguments: dict[str, Any], max_response_bytes: int
    ) -> dict[str, Any]:
        """Call a tool and return its payload, shrunk to the tool's byte budget."""
        await self._ensure_initialized()
        result = await self._request("tools/call", {"name": name, "arguments": arguments})
        payload = _extract_payload(name, result)
        if result.get("isError"):
            error = payload.get("error", {})
            raise McpError(
                str(error.get("code", "tool_error")), str(error.get("message", "tool failed"))
            )
        return enforce_budget(payload, max_response_bytes, "limit")


def _extract_payload(name: str, result: dict[str, Any]) -> dict[str, Any]:
    """Read a tool payload from a CallToolResult.

    The server sends the payload twice — as ``structuredContent`` and as compact
    JSON in the first text block. The structured form is preferred; the text
    block is the fallback for a server that omits it.
    """
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured

    for block in result.get("content", []):
        if block.get("type") == "text":
            try:
                decoded = json.loads(block["text"])
            except json.JSONDecodeError as err:
                raise McpError(
                    "contract_violation", f"{name} returned a non-JSON text block"
                ) from err
            if isinstance(decoded, dict):
                return decoded

    raise McpError("contract_violation", f"{name} returned no readable payload")
