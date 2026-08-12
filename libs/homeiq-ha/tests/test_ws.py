"""Event subscription, auto-reconnect and metrics on HAWebSocketClient (TAP-5440)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import homeiq_ha.client.ws as ws_module
import pytest
from homeiq_ha.client import HAWebSocketClient

pytestmark = pytest.mark.asyncio

HANDSHAKE = [
    {"type": "auth_required", "ha_version": "2026.7.4"},
    {"type": "auth_ok", "ha_version": "2026.7.4"},
]


def ok(message: dict[str, Any], result: Any = None) -> dict[str, Any]:
    return {"id": message["id"], "type": "result", "success": True, "result": result}


class FakeWebSocket:
    """Scripted handshake, responder-driven replies, injectable failure."""

    def __init__(self, responder: Any) -> None:
        self._handshake = [dict(m) for m in HANDSHAKE]
        self._responder = responder
        self._outbox: asyncio.Queue[str] = asyncio.Queue()
        self.sent: list[dict[str, Any]] = []
        self.closed = False
        self._broken: Exception | None = None

    async def recv(self) -> str:
        if self._handshake:
            return json.dumps(self._handshake.pop(0))
        return await self._outbox.get()

    async def send(self, raw: str) -> None:
        message = json.loads(raw)
        self.sent.append(message)
        if message.get("type") == "auth":
            return
        response = self._responder(message)
        if response is not None:
            await self._outbox.put(json.dumps(response))

    async def close(self) -> None:
        self.closed = True

    def push_event(self, sub_id: int, event: dict[str, Any]) -> None:
        self._outbox.put_nowait(
            json.dumps({"id": sub_id, "type": "event", "event": event})
        )

    def break_connection(self, exc: Exception) -> None:
        self._broken = exc
        # Wake the reader: __anext__ raises once the sentinel is queued.
        self._outbox.put_nowait("__BREAK__")

    def __aiter__(self) -> FakeWebSocket:
        return self

    async def __anext__(self) -> str:
        raw = await self._outbox.get()
        if raw == "__BREAK__" and self._broken is not None:
            raise self._broken
        return raw


async def connect_via_fake(
    client: HAWebSocketClient, responder: Any, monkeypatch: pytest.MonkeyPatch
) -> list[FakeWebSocket]:
    """Route client.connect() (and reconnects) onto fresh FakeWebSockets."""
    sockets: list[FakeWebSocket] = []

    async def fake_connect(*_args: Any, **_kwargs: Any) -> FakeWebSocket:
        sockets.append(FakeWebSocket(responder))
        return sockets[-1]

    monkeypatch.setattr(ws_module.websockets.asyncio.client, "connect", fake_connect)
    await client.connect()
    return sockets


def subscribing_responder(message: dict[str, Any]) -> dict[str, Any] | None:
    if message.get("type") in {"subscribe_events", "unsubscribe_events", "ping"}:
        return ok(message)
    return ok(message, [])


async def drain() -> None:
    """Let the read loop process queued frames."""
    for _ in range(10):
        await asyncio.sleep(0)


async def test_subscribe_dispatches_events_to_handler(monkeypatch):
    client = HAWebSocketClient("ws://ha.test/api/websocket", "secret-token")
    sockets = await connect_via_fake(client, subscribing_responder, monkeypatch)

    received: list[dict[str, Any]] = []

    async def handler(event: dict[str, Any]) -> None:
        received.append(event)

    sub_id = await client.subscribe_events("state_changed", handler)
    sent = sockets[0].sent[-1]
    assert sent["type"] == "subscribe_events"
    assert sent["event_type"] == "state_changed"
    assert sent["id"] == sub_id

    sockets[0].push_event(sub_id, {"event_type": "state_changed", "data": {"entity_id": "light.office"}})
    await drain()
    assert received == [{"event_type": "state_changed", "data": {"entity_id": "light.office"}}]
    await client.close()


async def test_handler_exception_does_not_kill_the_read_loop(monkeypatch):
    client = HAWebSocketClient("ws://ha.test/api/websocket", "secret-token")
    sockets = await connect_via_fake(client, subscribing_responder, monkeypatch)

    async def bad_handler(_event: dict[str, Any]) -> None:
        raise RuntimeError("handler bug")

    sub_id = await client.subscribe_events("state_changed", bad_handler)
    sockets[0].push_event(sub_id, {"data": 1})
    await drain()

    # Commands still resolve after the handler blew up.
    assert await client.list_entities() == []
    await client.close()


async def test_unsubscribe_stops_dispatch_and_is_idempotent(monkeypatch):
    client = HAWebSocketClient("ws://ha.test/api/websocket", "secret-token")
    sockets = await connect_via_fake(client, subscribing_responder, monkeypatch)

    received: list[dict[str, Any]] = []

    async def handler(event: dict[str, Any]) -> None:
        received.append(event)

    sub_id = await client.subscribe_events("state_changed", handler)
    await client.unsubscribe_events(sub_id)
    assert sockets[0].sent[-1]["type"] == "unsubscribe_events"
    assert sockets[0].sent[-1]["subscription"] == sub_id

    sockets[0].push_event(sub_id, {"data": 1})
    await drain()
    assert received == []

    # Unknown/stale ids are a no-op, not an error.
    await client.unsubscribe_events(sub_id)
    await client.unsubscribe_events(99999)
    await client.close()


async def test_auto_reconnect_resubscribes_and_keeps_handler(monkeypatch):
    client = HAWebSocketClient(
        "ws://ha.test/api/websocket",
        "secret-token",
        auto_reconnect=True,
        reconnect_delay=0.01,
        max_reconnect_attempts=3,
    )
    sockets = await connect_via_fake(client, subscribing_responder, monkeypatch)

    received: list[dict[str, Any]] = []

    async def handler(event: dict[str, Any]) -> None:
        received.append(event)

    await client.subscribe_events("state_changed", handler)

    sockets[0].break_connection(ConnectionError("socket died"))
    for _ in range(200):
        await asyncio.sleep(0.01)
        if len(sockets) > 1 and any(
            m.get("type") == "subscribe_events" for m in sockets[-1].sent
        ):
            break
    assert len(sockets) == 2, "a second connection should have been made"

    resub = [m for m in sockets[1].sent if m.get("type") == "subscribe_events"]
    assert resub and resub[0]["event_type"] == "state_changed"

    sockets[1].push_event(resub[0]["id"], {"data": "after-reconnect"})
    await drain()
    assert received == [{"data": "after-reconnect"}]

    metrics = client.get_metrics()
    assert metrics["connected"] is True
    assert metrics["disconnect_count"] >= 1
    assert metrics["reconnect_count"] == 1
    assert metrics["subscriptions"] == 1
    await client.close()


async def test_close_suppresses_auto_reconnect(monkeypatch):
    client = HAWebSocketClient(
        "ws://ha.test/api/websocket",
        "secret-token",
        auto_reconnect=True,
        reconnect_delay=0.01,
    )
    sockets = await connect_via_fake(client, subscribing_responder, monkeypatch)
    await client.close()
    await asyncio.sleep(0.1)
    assert len(sockets) == 1, "close() must not trigger a reconnect"
    assert client.get_metrics()["connected"] is False


async def test_event_queued_behind_subscribe_result_is_not_dropped(monkeypatch):
    """An event frame arriving with the subscribe result must reach the handler."""

    def eager_responder(message: dict[str, Any]) -> dict[str, Any] | None:
        return ok(message) if message.get("type") == "subscribe_events" else ok(message, [])

    client = HAWebSocketClient("ws://ha.test/api/websocket", "secret-token")
    sockets = await connect_via_fake(client, eager_responder, monkeypatch)
    ws = sockets[0]

    original_send = ws.send

    async def send_then_event(raw: str) -> None:
        await original_send(raw)
        message = json.loads(raw)
        if message.get("type") == "subscribe_events":
            # Queue an event frame immediately behind the subscribe result,
            # before subscribe_events() gets a chance to run again.
            ws.push_event(message["id"], {"data": "raced"})

    ws.send = send_then_event  # type: ignore[method-assign]

    received: list[dict[str, Any]] = []

    async def handler(event: dict[str, Any]) -> None:
        received.append(event)

    await client.subscribe_events("state_changed", handler)
    await drain()
    assert received == [{"data": "raced"}], "event behind the subscribe result was dropped"
    await client.close()


async def test_clean_server_close_triggers_reconnect(monkeypatch):
    """async-for exhaustion (server closed cleanly) counts as connection loss."""
    client = HAWebSocketClient(
        "ws://ha.test/api/websocket",
        "secret-token",
        auto_reconnect=True,
        reconnect_delay=0.01,
        max_reconnect_attempts=3,
    )
    sockets = await connect_via_fake(client, subscribing_responder, monkeypatch)
    await client.subscribe_events("state_changed", None)

    sockets[0].break_connection(StopAsyncIteration())
    for _ in range(200):
        await asyncio.sleep(0.01)
        if len(sockets) > 1 and any(
            m.get("type") == "subscribe_events" for m in sockets[-1].sent
        ):
            break
    assert len(sockets) == 2, "clean server close must trigger a reconnect"
    metrics = client.get_metrics()
    assert metrics["reconnect_count"] == 1
    assert metrics["disconnect_count"] == 1
    # The reconnect established a genuinely new connection, so close() ending
    # it is a real second disconnect (2 connections, 2 disconnects).
    await client.close()
    assert client.get_metrics()["disconnect_count"] == 2


async def test_loss_without_reconnect_then_close_counts_one_disconnect(monkeypatch):
    """A drop followed by close() is one disconnect, not two (metrics honesty)."""
    client = HAWebSocketClient("ws://ha.test/api/websocket", "secret-token")
    sockets = await connect_via_fake(client, subscribing_responder, monkeypatch)

    sockets[0].break_connection(ConnectionError("socket died"))
    await drain()
    assert client.get_metrics()["disconnect_count"] == 1

    await client.close()
    assert client.get_metrics()["disconnect_count"] == 1
