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
import contextlib
import json
import logging
import random
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

# The bare package lazy-loads submodules; connect() needs the submodule
# genuinely imported at runtime.
import websockets.asyncio.client

from .errors import HAAuthError, HAClientClosed, HACommandError
from .redaction import redact

if TYPE_CHECKING:
    import ssl
    from types import TracebackType

    from websockets.asyncio.client import ClientConnection

logger = logging.getLogger(__name__)

# Installing an add-on routinely takes minutes; the default command timeout is
# far too short for the Supervisor endpoints that do real work.
DEFAULT_COMMAND_TIMEOUT = 30.0
SUPERVISOR_INSTALL_TIMEOUT = 900.0

# Auto-reconnect backoff: first retry after DEFAULT_RECONNECT_DELAY seconds
# (plus up to 30% jitter), doubling per attempt, capped at MAX_RECONNECT_DELAY.
DEFAULT_RECONNECT_DELAY = 1.0
MAX_RECONNECT_DELAY = 60.0
DEFAULT_MAX_RECONNECT_ATTEMPTS = 10

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


def _frame_logger() -> logging.Logger:
    """The websockets library's frame logger, pinned above DEBUG.

    Raw frames contain unredacted secrets (the backup encryption key rides
    ``backup/config/info`` responses in plaintext); homeiq's own send-path
    logging goes through :func:`~homeiq_ha.client.redaction.redact` instead.
    """
    frame_logger = logging.getLogger("homeiq_ha.client.ws.frames")
    frame_logger.setLevel(logging.INFO)
    return frame_logger


def _is_log_endpoint(endpoint: str) -> bool:
    """Supervisor endpoints that return plain journald text, not JSON.

    Covers ``/core/logs``, ``/supervisor/logs``, ``/host/logs``,
    ``/addons/<slug>/logs`` and their sub-paths (``/host/logs/boots/0``).
    Two collection endpoints under ``/host/logs`` return JSON, not text —
    ``/host/logs/boots`` and ``/host/logs/identifiers`` (verified live
    2026-08-13, HA 2026.8.1) — so those pass through to the WS passthrough,
    while their entry sub-paths (``.../boots/0``) are text and stay blocked.
    """
    path = endpoint.split("?", 1)[0].rstrip("/")
    if path.endswith(("/logs/boots", "/logs/identifiers")):
        return False
    return path.endswith("/logs") or "/logs/" in path


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
        auto_reconnect: bool = False,
        reconnect_delay: float = DEFAULT_RECONNECT_DELAY,
        max_reconnect_attempts: int = DEFAULT_MAX_RECONNECT_ATTEMPTS,
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
        # Event subscriptions survive reconnects: id -> (event_type, handler).
        self._subscriptions: dict[int, tuple[str | None, EventHandler | None]] = {}
        self._auto_reconnect = auto_reconnect
        self._reconnect_delay = reconnect_delay
        self._max_reconnect_attempts = max_reconnect_attempts
        self._reconnect_task: asyncio.Task[None] | None = None
        self._closing = False
        self._connection_lost = False
        # Connection metrics (shape kept compatible with the client this
        # replaces in api-automation-edge, TAP-5440).
        self._disconnect_count = 0
        self._reconnect_count = 0
        self._last_connect_time: float | None = None
        self._last_disconnect_time: float | None = None
        self._reconnect_latencies: list[float] = []

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
            # The library's own DEBUG frame logging ("< %s") would bypass
            # redact() and print raw frames — backup/config/info carries the
            # encryption key in plaintext. Pin its logger above DEBUG.
            logger=_frame_logger(),
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

        self._closing = False
        self._connection_lost = False
        self._last_connect_time = time.time()
        self._reader = asyncio.create_task(self._read_loop())
        logger.info("Connected to Home Assistant WebSocket API (%s)", result.get("ha_version"))

    async def close(self) -> None:
        """Close the connection and fail any in-flight commands."""
        self._closing = True
        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reconnect_task
            self._reconnect_task = None

        if self._reader is not None:
            self._reader.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader
            self._reader = None

        for future in self._pending.values():
            if not future.done():
                future.set_exception(HAClientClosed("Connection closed"))
        self._pending.clear()

        if self._ws is not None:
            await self._ws.close()
            self._ws = None
            # Count the disconnect only when this close ended a connection the
            # loss path has not already counted — otherwise a drop followed by
            # close() reported two disconnects for one.
            if not self._connection_lost:
                self._last_disconnect_time = time.time()
                self._disconnect_count += 1

    async def _read_loop(self) -> None:
        """Dispatch incoming frames to whichever command is waiting on them."""
        assert self._ws is not None
        try:
            async for raw in self._ws:
                message = json.loads(raw)
                message_type = message.get("type")
                if message_type == "event":
                    await self._dispatch_event(message)
                    continue
                if message_type != "result":
                    # Subscription-style commands (zha/devices/permit) stream
                    # event frames under the same id BEFORE their result;
                    # resolving a command future with one made the permit call
                    # report an empty "unknown" error while actually
                    # succeeding (observed live 2026-08-12).
                    continue
                future = self._pending.pop(message.get("id", -1), None)
                if future is not None and not future.done():
                    future.set_result(message)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # connection dropped mid-flight
            self._handle_connection_loss(exc)
        else:
            # The server closed the socket cleanly (async-for exhausted):
            # still a connection loss from the caller's point of view.
            self._handle_connection_loss(HAClientClosed("Connection closed by server"))

    async def _dispatch_event(self, message: dict[str, Any]) -> None:
        """Run the subscription handler for one event frame.

        Handlers run inline on the read loop, preserving event order. A
        handler must NOT await a command on this same client (the command's
        result frame cannot be read while the handler blocks the loop);
        schedule such work with asyncio.create_task instead.
        """
        subscription = self._subscriptions.get(message.get("id", -1))
        if subscription is None:
            return
        _event_type, handler = subscription
        if handler is None:
            return
        try:
            await handler(message.get("event") or {})
        except Exception:
            logger.exception(
                "Event handler for subscription %s raised; subscription continues",
                message.get("id"),
            )

    def _handle_connection_loss(self, exc: Exception) -> None:
        """Fail in-flight commands and, if configured, start reconnecting."""
        for future in self._pending.values():
            if not future.done():
                future.set_exception(exc)
        self._pending.clear()
        self._connection_lost = True
        self._disconnect_count += 1
        self._last_disconnect_time = time.time()
        reconnect_running = self._reconnect_task is not None and not self._reconnect_task.done()
        if self._auto_reconnect and not self._closing and not reconnect_running:
            logger.warning("Connection lost (%s); reconnecting", exc)
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Reconnect with jittered exponential backoff, then resubscribe."""
        delay = self._reconnect_delay
        for attempt in range(1, self._max_reconnect_attempts + 1):
            await asyncio.sleep(delay + random.uniform(0, delay * 0.3))
            started = time.monotonic()
            try:
                await self._reestablish()
            except Exception:
                logger.warning(
                    "Reconnect attempt %d/%d failed",
                    attempt,
                    self._max_reconnect_attempts,
                    exc_info=True,
                )
                delay = min(delay * 2, MAX_RECONNECT_DELAY)
                continue
            self._reconnect_count += 1
            self._reconnect_latencies.append(time.monotonic() - started)
            logger.info("Reconnected to Home Assistant after %d attempt(s)", attempt)
            return
        logger.error(
            "Gave up reconnecting after %d attempts; call connect() to retry",
            self._max_reconnect_attempts,
        )

    async def _reestablish(self) -> None:
        """One reconnect attempt: fresh socket, then replay subscriptions."""
        old_subscriptions = list(self._subscriptions.values())
        self._subscriptions.clear()
        if self._ws is not None:
            with contextlib.suppress(Exception):
                await self._ws.close()
            self._ws = None
        # The old reader task has already exited via the connection-loss path.
        self._reader = None
        await self.connect()
        for event_type, handler in old_subscriptions:
            await self.subscribe_events(event_type, handler)

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
        _, result = await self._send_and_wait(
            command_type, payload, timeout if timeout is not None else self._command_timeout
        )
        return result

    async def _send_and_wait(
        self,
        command_type: str,
        payload: dict[str, Any],
        timeout: float,
        on_sent: Callable[[int], None] | None = None,
    ) -> tuple[int, Any]:
        """Send one command and return ``(message_id, result)``.

        The message id doubles as the subscription id for subscription-style
        commands, which is why it is surfaced here. ``on_sent`` runs with the
        allocated id immediately after the frame is sent, before the result is
        awaited — the seam subscribe_events needs to register its handler
        before any event frame can race the subscribe result.
        """
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
            if on_sent is not None:
                on_sent(message_id)

        try:
            response = await asyncio.wait_for(future, timeout)
        except TimeoutError:
            self._pending.pop(message_id, None)
            raise

        if not response.get("success", False):
            error = response.get("error") or {}
            raise HACommandError(
                command_type,
                str(error.get("code", "unknown")),
                str(error.get("message", "")),
            )
        return message_id, response.get("result")

    # -- event subscriptions -------------------------------------------------

    async def subscribe_events(
        self,
        event_type: str | None = None,
        handler: EventHandler | None = None,
    ) -> int:
        """Subscribe to Home Assistant events.

        Args:
            event_type: Event type to subscribe to (``None`` for all events).
            handler: Async callback invoked with each event dict. Runs inline
                on the read loop — see :meth:`_dispatch_event` for the rules.

        Returns:
            The subscription id (pass to :meth:`unsubscribe_events`). After an
            auto-reconnect the subscription is replayed under a new id; the
            handler keeps firing either way.
        """
        payload: dict[str, Any] = {}
        if event_type is not None:
            payload["event_type"] = event_type

        # Register at send time: event frames can be queued directly behind
        # the subscribe result, and the read loop does not yield between
        # resolving the future and dispatching them — registering after the
        # await silently dropped those first events.
        sent_id: list[int] = []

        def register(subscription_id: int) -> None:
            sent_id.append(subscription_id)
            self._subscriptions[subscription_id] = (event_type, handler)

        try:
            subscription_id, _ = await self._send_and_wait(
                "subscribe_events", payload, self._command_timeout, on_sent=register
            )
        except BaseException:
            # The optimistic registration must not outlive a failed subscribe.
            if sent_id:
                self._subscriptions.pop(sent_id[0], None)
            raise
        logger.info("Subscribed to events (type=%s, id=%d)", event_type, subscription_id)
        return subscription_id

    async def unsubscribe_events(self, subscription_id: int) -> None:
        """Cancel one event subscription.

        Ids from before an auto-reconnect are forgotten locally without a
        server round-trip, since the server-side subscription died with the
        old connection.
        """
        if self._subscriptions.pop(subscription_id, None) is None:
            return
        try:
            await self.send_command("unsubscribe_events", subscription=subscription_id)
        except (HAClientClosed, HACommandError):
            # A dead connection or a server-rejected id both mean the
            # server-side subscription no longer exists — which is the
            # post-condition this method promises. Idempotent by design.
            logger.debug("unsubscribe_events(%d) was already moot", subscription_id)

    def get_metrics(self) -> dict[str, Any]:
        """Connection metrics, shape-compatible with the retired
        api-automation-edge client (TAP-5440)."""
        average_latency = (
            sum(self._reconnect_latencies) / len(self._reconnect_latencies)
            if self._reconnect_latencies
            else 0.0
        )
        connected = self._ws is not None
        return {
            "connected": connected,
            "authenticated": connected,  # the handshake authenticates or fails
            "disconnect_count": self._disconnect_count,
            "reconnect_count": self._reconnect_count,
            "subscriptions": len(self._subscriptions),
            "last_connect_time": self._last_connect_time,
            "last_disconnect_time": self._last_disconnect_time,
            "avg_reconnect_latency": average_latency,
            "reconnect_latencies": self._reconnect_latencies[-10:],
        }

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
        """Update a device. Accepts ``area_id``, ``disabled_by``, ``labels`` and
        ``name_by_user`` — HA core rejects anything else, and a device's ``name``
        stays integration-owned.

        Renaming a device recomputes the *friendly name* of every entity on it
        with ``has_entity_name`` — 19 device renames rather than 164 entity
        renames. It does **not** touch ``entity_id`` slugs: this command never
        reaches the entity registry, and HA moves a slug only when handed
        ``new_entity_id``. Verified against HA core 2026.8.2
        (``components/config/device_registry.py``).

        Prefer :class:`homeiq_ha.registry_writer.HARegistryWriter` for name and
        area writes — it reads the value back and refuses to report a write that
        did not land."""
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
        return await self.send_command("config/floor_registry/update", floor_id=floor_id, **changes)

    async def delete_floor(self, floor_id: str) -> None:
        await self.send_command("config/floor_registry/delete", floor_id=floor_id)

    async def list_labels(self) -> list[dict[str, Any]]:
        return await self._registry_list("label_registry")

    async def create_label(self, name: str, **fields: Any) -> dict[str, Any]:
        return await self.send_command("config/label_registry/create", name=name, **fields)

    async def update_label(self, label_id: str, **changes: Any) -> dict[str, Any]:
        return await self.send_command("config/label_registry/update", label_id=label_id, **changes)

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

    async def update_category(self, scope: str, category_id: str, **changes: Any) -> dict[str, Any]:
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

        Raises:
            ValueError: for log endpoints, which this passthrough cannot
                transport (TAP-5984). Home Assistant's ``supervisor/api``
                handler JSON-decodes every Supervisor response, and log
                endpoints return plain journald text, so they always fail
                with an opaque ``unknown_error`` (verified live 2026-08-13,
                HA 2026.8.1). Refusing up front points the caller at the
                supported path: :meth:`HARestClient.get_supervisor_logs`.
        """
        if _is_log_endpoint(endpoint):
            raise ValueError(
                f"supervisor/api cannot return text logs ({endpoint!r}): the WS "
                "passthrough JSON-decodes every Supervisor response, so log "
                "endpoints always fail with unknown_error. Use "
                "HARestClient.get_supervisor_logs(), which fetches "
                f"GET /api/hassio{endpoint} as text."
            )
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
        return await self.send_command("supervisor/api", timeout=timeout + 30.0, fields=command)
