"""Assemble the `homeiq` MCP server: low-level Server + Starlette app / stdio.

The low-level `Server` is used deliberately: `list_tools` returns the
catalogue's JSON schemas verbatim, which is what TAP-5297's contract tests pin.
"""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING, Any

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route

from .auth import STATE_KEY, STDIO_SCOPES, BearerScopeMiddleware
from .backends import Backings, build_backings
from .catalogue import load_catalogue
from .errors import ToolError
from .health import make_health_endpoint
from .registry import ToolRegistry

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from .config import Settings

logger = logging.getLogger("homeiq_mcp.server")

SERVER_NAME = "homeiq"
SERVER_VERSION = "0.1.0"
MCP_PATH = "/mcp"


def _scopes_from(ctx: Any) -> frozenset[str]:
    request = getattr(ctx, "request", None)
    if isinstance(request, Request):
        return request.state.__dict__.get("_state", {}).get(STATE_KEY) or request.scope.get(
            "state", {}
        ).get(STATE_KEY, frozenset())
    return STDIO_SCOPES


def _error_result(error: ToolError) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"{error.code}: {error.message}")],
        structured_content={"error": error.to_payload()},
        is_error=True,
    )


class HomeIQMCP:
    """Everything needed to serve the catalogue over HTTP or stdio."""

    def __init__(
        self,
        settings: Settings,
        *,
        registry: ToolRegistry | None = None,
        backings: Backings | None = None,
    ) -> None:
        self.settings = settings
        self.catalogue = registry.catalogue if registry else load_catalogue(settings.catalogue_path)
        self.registry = registry or ToolRegistry(
            self.catalogue, allowed_write_tools=settings.allowed_write_tools
        )
        self.backings = backings or build_backings(settings)
        self.server: Server[Any] = Server(
            SERVER_NAME,
            version=SERVER_VERSION,
            instructions=(
                "Read-only typed tools over HomeIQ's observed Home Assistant data. "
                "Responses are size-budgeted; when 'truncated' is true, narrow the parameter named in 'hint'."
            ),
            on_list_tools=self._on_list_tools,
            on_call_tool=self._on_call_tool,
        )

    async def _on_list_tools(self, _ctx: Any, _params: Any) -> types.ListToolsResult:
        return types.ListToolsResult(tools=self.registry.list_tools())

    async def _on_call_tool(
        self, ctx: Any, params: types.CallToolRequestParams
    ) -> types.CallToolResult:
        try:
            payload = await self.registry.call(
                params.name, params.arguments, scopes=_scopes_from(ctx)
            )
        except ToolError as error:
            return _error_result(error)
        except Exception:
            logger.exception("unhandled failure in tool %s", params.name)
            return _error_result(
                ToolError(
                    "backing_unavailable", "internal failure; see server log", tool=params.name
                )
            )
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=_compact_json(payload))],
            structured_content=payload,
        )

    def build_http_app(self) -> Starlette:
        settings = self.settings
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=settings.allowed_host_patterns,
            allowed_origins=[f"http://{h}" for h in settings.allowed_host_patterns],
        )
        session_manager = StreamableHTTPSessionManager(
            app=self.server, json_response=True, stateless=True, security_settings=security
        )

        @contextlib.asynccontextmanager
        async def lifespan(_: Starlette) -> AsyncIterator[None]:
            async with session_manager.run():
                yield
            await self.backings.aclose()

        mcp_app = BearerScopeMiddleware(
            session_manager.handle_request,
            protected_prefix=MCP_PATH,
            read_tokens=settings.read_token_list,
            write_tokens=settings.write_token_list,
        )
        return Starlette(
            routes=[
                Route(
                    "/health",
                    make_health_endpoint(self.registry, self.backings, version=SERVER_VERSION),
                    methods=["GET"],
                ),
                Mount(MCP_PATH, app=mcp_app),
            ],
            lifespan=lifespan,
        )

    async def run_stdio(self) -> None:
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, write_stream, self.server.create_initialization_options()
            )


def _compact_json(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
