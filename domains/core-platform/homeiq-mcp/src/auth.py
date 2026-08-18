"""Bearer-token auth for the `/mcp` route (LAN-internal, static tokens).

Two token classes map to scopes: read tokens → {"read"}; write tokens →
{"read", "mutate"}. The resolved scope set is placed on the ASGI scope state
so the tool dispatcher can enforce the per-tool write grant. `/health` and
anything outside the protected prefix pass through untouched.
"""

from __future__ import annotations

import hmac
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from starlette.types import ASGIApp, Receive, Scope, Send


READ_SCOPES: frozenset[str] = frozenset({"read"})
WRITE_SCOPES: frozenset[str] = frozenset({"read", "mutate"})
STDIO_SCOPES: frozenset[str] = WRITE_SCOPES
STATE_KEY = "homeiq_scopes"


def _matches(candidate: str, tokens: Iterable[str]) -> bool:
    # Compare against every token so timing does not reveal which one matched.
    matched = False
    for token in tokens:
        if hmac.compare_digest(candidate.encode(), token.encode()):
            matched = True
    return matched


def resolve_scopes(
    candidate: str, read_tokens: list[str], write_tokens: list[str]
) -> frozenset[str] | None:
    if _matches(candidate, write_tokens):
        return WRITE_SCOPES
    if _matches(candidate, read_tokens):
        return READ_SCOPES
    return None


class BearerScopeMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        protected_prefix: str,
        read_tokens: list[str],
        write_tokens: list[str],
    ) -> None:
        self.app = app
        self.protected_prefix = protected_prefix
        self.read_tokens = list(read_tokens)
        self.write_tokens = list(write_tokens)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith(self.protected_prefix):
            await self.app(scope, receive, send)
            return
        header = next((v for k, v in scope["headers"] if k == b"authorization"), b"").decode(
            "latin-1"
        )
        scheme, _, credential = header.partition(" ")
        scopes = None
        if scheme.lower() == "bearer" and credential:
            scopes = resolve_scopes(credential.strip(), self.read_tokens, self.write_tokens)
        if scopes is None:
            await _reject(send)
            return
        scope.setdefault("state", {})[STATE_KEY] = scopes
        await self.app(scope, receive, send)


async def _reject(send: Send) -> None:
    body = json.dumps(
        {"error": "invalid_token", "error_description": "Authentication required"}
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"www-authenticate", b'Bearer error="invalid_token"'),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
