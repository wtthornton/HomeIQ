"""Home Assistant WebSocket client.

Home Assistant's entity, device, area, floor, label and category registries are
**WebSocket-only**. There is no REST equivalent, so the several HomeIQ services
that reach for ``GET /api/config/entity_registry`` have always received a 404
and degraded silently. This client is the shared replacement.

It also exposes :meth:`HAWebSocketClient.supervisor_api`, the unrestricted
Supervisor passthrough. The REST path ``/api/hassio/*`` is a deny-by-default
allowlist that answers 401 even for an admin+owner token; the WebSocket
``supervisor/api`` command is how the Home Assistant frontend itself drives the
Supervisor panel, and it is the only route to add-on management from outside
the host.
"""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
from types import TracebackType
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

from .errors import HAAuthError, HAClientClosed, HACommandError
from .redaction import redact

logger = logging.getLogger(__name__)

# Installing an add-on routinely takes minutes; the default command timeout is
# far too short for the Supervisor endpoints that do real work.
DEFAULT_COMMAND_TIMEOUT = 30.0
SUPERVISOR_INSTALL_TIMEOUT = 900.0


class HAWebSocketClient:
    """An authenticated Home Assistant WebSocket connection.

    Commands are correlated by the ``id`` field Home Assistant echoes back, so a
    single connection can serve concurrent callers. Use as an async context
    manager, or call :meth:`connect` and :meth:`close` explicitly.
    """

    def __init__(
        self,
        url: str,
        token: str,
        *,
        ssl_context: ssl.SSLContext | None = None,
        command_timeout: float = DEFAULT_COMMAND_TIMEOUT,
    ) -> None:
        self._url = url
        self._token = token
        self._ssl_context = ssl_context
        self._command_timeout = command_timeout
        self._ws: ClientConnection | None = None
        self._next_id = 1
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._reader: asyncio.Task[None] | None = None
        self._send_lock = asyncio.Lock()

    # -- lifecycle ---------------------------------------------------------

    async def __aenter__(self) -> HAWebSocketClient:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def connect(self) -> None:
        """Open the connection and complete the auth handshake."""
        ssl_context = self._ssl_context if self._url.startswith("wss://") else None
        self._ws = await websockets.asyncio.client.connect(
            self._url,
            ssl=ssl_context,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10,
            max_size=None,  # entity registry listings exceed the 1 MiB default
        )

        greeting = json.loads(await self._ws.recv())
        if greeting.get("type") != "auth_required":
            await self._ws.close()
            raise HAAuthError(f"Unexpected handshake message: {greeting.get('type')!r}")

        await self._ws.send(json.dumps({"type": "auth", "access_token": self._token}))
        result = json.loads(await self._ws.recv())
        if result.get("type") != "auth_ok":
            await self._ws.close()
            self._ws = None
            # `result` may echo the token back; never log it unredacted.
            raise HAAuthError(f"Authentication rejected: {redact(result)}")

        self._reader = asyncio.create_task(self._read_loop())
        logger.info("Connected to Home Assistant WebSocket API (%s)", result.get("ha_version"))

    async def close(self) -> None:
        """Close the connection and fail any in-flight commands."""
        if self._reader is not None:
            self._reader.cancel()
            try:
                await self._reader
            except asyncio.CancelledError:
                pass
            self._reader = None

        for future in self._pending.values():
            if not future.done():
                future.set_exception(HAClientClosed("Connection closed"))
        self._pending.clear()

        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    async def _read_loop(self) -> None:
        """Dispatch incoming frames to whichever command is waiting on them."""
        assert self._ws is not None
        try:
            async for raw in self._ws:
                message = json.loads(raw)
                future = self._pending.pop(message.get("id", -1), None)
                if future is not None and not future.done():
                    future.set_result(message)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # connection dropped mid-flight
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(exc)
            self._pending.clear()

    # -- command plumbing --------------------------------------------------

    async def send_command(
        self,
        command_type: str,
        *,
        timeout: float | None = None,
        fields: dict[str, Any] | None = None,
        **payload: Any,
    ) -> Any:
        """Send one command and return its ``result``.

        Args:
            fields: Command fields supplied as a dict rather than keywords. Use
                this for commands whose own field names collide with this
                method's parameters — ``supervisor/api`` takes a ``timeout``
                field of its own.

        Raises:
            HACommandError: Home Assistant answered ``success: false``.
        """
        payload = {**payload, **(fields or {})}
        if self._ws is None:
            raise HAClientClosed("Not connected — call connect() first")

        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()

        async with self._send_lock:
            message_id = self._next_id
            self._next_id += 1
            self._pending[message_id] = future
            message = {"id": message_id, "type": command_type, **payload}
            logger.debug("HA ws -> %s", redact(message))
            await self._ws.send(json.dumps(message))

        try:
            response = await asyncio.wait_for(
                future, timeout if timeout is not None else self._command_timeout
            )
        except (asyncio.TimeoutError, TimeoutError):
            self._pending.pop(message_id, None)
            raise

        if not response.get("success", False):
            error = response.get("error") or {}
            raise HACommandError(
                command_type,
                str(error.get("code", "unknown")),
                str(error.get("message", "")),
            )
        return response.get("result")

    # -- registries --------------------------------------------------------
    #
    # Every registry follows the same list/create/update/delete command shape,
    # so the generic helpers below are what the named methods are built from.

    async def _registry_list(self, registry: str) -> list[dict[str, Any]]:
        result = await self.send_command(f"config/{registry}/list")
        return list(result or [])

    async def list_entities(self) -> list[dict[str, Any]]:
        return await self._registry_list("entity_registry")

    async def get_entity(self, entity_id: str) -> dict[str, Any]:
        return await self.send_command("config/entity_registry/get", entity_id=entity_id)

    async def update_entity(self, entity_id: str, **changes: Any) -> dict[str, Any]:
        """Update one entity registry entry.

        Accepts Home Assistant's own field names: ``name``, ``icon``,
        ``area_id``, ``labels``, ``new_entity_id``, ``hidden_by``,
        ``disabled_by``, ``aliases``.
        """
        return await self.send_command(
            "config/entity_registry/update", entity_id=entity_id, **changes
        )

    async def remove_entity(self, entity_id: str) -> None:
        await self.send_command("config/entity_registry/remove", entity_id=entity_id)

    async def list_devices(self) -> list[dict[str, Any]]:
        return await self._registry_list("device_registry")

    async def update_device(self, device_id: str, **changes: Any) -> dict[str, Any]:
        """Update a device. Renaming a device with ``has_entity_name`` cascades
        to its entity_ids and friendly names — 19 device renames rather than
        164 entity renames."""
        return await self.send_command(
            "config/device_registry/update", device_id=device_id, **changes
        )

    async def list_areas(self) -> list[dict[str, Any]]:
        return await self._registry_list("area_registry")

    async def create_area(self, name: str, **fields: Any) -> dict[str, Any]:
        return await self.send_command("config/area_registry/create", name=name, **fields)

    async def update_area(self, area_id: str, **changes: Any) -> dict[str, Any]:
        return await self.send_command("config/area_registry/update", area_id=area_id, **changes)

    async def delete_area(self, area_id: str) -> None:
        await self.send_command("config/area_registry/delete", area_id=area_id)

    async def list_floors(self) -> list[dict[str, Any]]:
        return await self._registry_list("floor_registry")

    async def create_floor(self, name: str, **fields: Any) -> dict[str, Any]:
        return await self.send_command("config/floor_registry/create", name=name, **fields)

    async def update_floor(self, floor_id: str, **changes: Any) -> dict[str, Any]:
        return await self.send_command(
            "config/floor_registry/update", floor_id=floor_id, **changes
        )

    async def delete_floor(self, floor_id: str) -> None:
        await self.send_command("config/floor_registry/delete", floor_id=floor_id)

    async def list_labels(self) -> list[dict[str, Any]]:
        return await self._registry_list("label_registry")

    async def create_label(self, name: str, **fields: Any) -> dict[str, Any]:
        return await self.send_command("config/label_registry/create", name=name, **fields)

    async def update_label(self, label_id: str, **changes: Any) -> dict[str, Any]:
        return await self.send_command(
            "config/label_registry/update", label_id=label_id, **changes
        )

    async def delete_label(self, label_id: str) -> None:
        await self.send_command("config/label_registry/delete", label_id=label_id)

    async def list_categories(self, scope: str) -> list[dict[str, Any]]:
        """Categories are per-scope (``automation``, ``script``, ``helpers``)."""
        result = await self.send_command("config/category_registry/list", scope=scope)
        return list(result or [])

    async def create_category(self, scope: str, name: str, **fields: Any) -> dict[str, Any]:
        return await self.send_command(
            "config/category_registry/create", scope=scope, name=name, **fields
        )

    async def update_category(
        self, scope: str, category_id: str, **changes: Any
    ) -> dict[str, Any]:
        return await self.send_command(
            "config/category_registry/update",
            scope=scope,
            category_id=category_id,
            **changes,
        )

    async def delete_category(self, scope: str, category_id: str) -> None:
        await self.send_command(
            "config/category_registry/delete", scope=scope, category_id=category_id
        )

    # -- supervisor --------------------------------------------------------

    async def supervisor_api(
        self,
        endpoint: str,
        *,
        method: str = "get",
        payload: dict[str, Any] | None = None,
        timeout: float = SUPERVISOR_INSTALL_TIMEOUT,
    ) -> Any:
        """Call a Supervisor endpoint through the WebSocket passthrough.

        Args:
            endpoint: Supervisor path, e.g. ``/store/addons/core_ssh/install``.
            method: HTTP verb the Supervisor should use.
            payload: JSON body for write methods.
            timeout: Defaults to 15 minutes — add-on installs are slow, and a
                short timeout aborts the client while the install continues
                server-side, which is worse than waiting.
        """
        command: dict[str, Any] = {
            "endpoint": endpoint,
            "method": method.lower(),
            # Supervisor's own field, distinct from this client's wait timeout.
            "timeout": int(timeout),
        }
        if payload is not None:
            command["data"] = payload
        # Wait slightly longer than the Supervisor does, so its own timeout
        # surfaces as a Supervisor error rather than a client-side abort.
        return await self.send_command(
            "supervisor/api", timeout=timeout + 30.0, fields=command
        )
