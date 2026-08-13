"""Tests for the shared Home Assistant client.

These run against a fake transport, never a live instance.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from homeiq_ha.client import HAClient
from homeiq_ha.client.errors import (
    HAAuthError,
    HACommandError,
    HAFlowError,
    HAHumanGateRequired,
)
from homeiq_ha.client.redaction import REDACTED, redact, redact_text
from homeiq_ha.client.rest import HARestClient
from homeiq_ha.client.ws import HAWebSocketClient


class FakeWebSocket:
    """Minimal stand-in for a websockets ClientConnection.

    Replays a scripted handshake, then answers each command via ``responder``.
    """

    def __init__(self, handshake: list[dict[str, Any]], responder: Any) -> None:
        self._handshake = list(handshake)
        self._responder = responder
        self._outbox: asyncio.Queue[str] = asyncio.Queue()
        self.sent: list[dict[str, Any]] = []
        self.closed = False

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

    def __aiter__(self) -> FakeWebSocket:
        return self

    async def __anext__(self) -> str:
        return await self._outbox.get()


def make_client(responder: Any, *, auth_ok: bool = True) -> HAWebSocketClient:
    client = HAWebSocketClient("ws://ha.test/api/websocket", "secret-token")
    handshake = [
        {"type": "auth_required", "ha_version": "2026.7.4"},
        {"type": "auth_ok", "ha_version": "2026.7.4"}
        if auth_ok
        else {"type": "auth_invalid", "message": "bad token"},
    ]
    client._ws = FakeWebSocket(handshake, responder)  # noqa: SLF001 - test seam
    return client


async def connect_fake(client: HAWebSocketClient) -> FakeWebSocket:
    """Run the handshake and reader loop against the already-injected socket."""
    ws = client._ws  # noqa: SLF001 - test seam
    assert isinstance(ws, FakeWebSocket)
    greeting = json.loads(await ws.recv())
    assert greeting["type"] == "auth_required"
    await ws.send(json.dumps({"type": "auth", "access_token": "secret-token"}))
    result = json.loads(await ws.recv())
    if result.get("type") != "auth_ok":
        raise HAAuthError(str(result))
    client._reader = asyncio.create_task(client._read_loop())  # noqa: SLF001
    return ws


def ok(message: dict[str, Any], result: Any) -> dict[str, Any]:
    return {"id": message["id"], "type": "result", "success": True, "result": result}


# --- redaction ------------------------------------------------------------


def test_redact_masks_secret_keys_at_any_depth():
    payload = {
        "outer": {"access_token": "abc123", "keep": "visible"},
        "list": [{"password": "hunter2"}],
    }
    assert redact(payload) == {
        "outer": {"access_token": REDACTED, "keep": "visible"},
        "list": [{"password": REDACTED}],
    }


def test_redact_masks_the_backup_encryption_key():
    # backup/config/info returns this in plaintext; it must never be logged.
    assert redact({"encryption_key": "AAAA-BBBB-CCCC"})["encryption_key"] == REDACTED


def test_redact_text_masks_bearer_tokens():
    assert "eyJhbGciOi" not in redact_text("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9")


def test_redact_leaves_ordinary_values_alone():
    assert redact({"name": "Kitchen", "count": 3}) == {"name": "Kitchen", "count": 3}


# --- websocket plumbing ---------------------------------------------------


@pytest.mark.asyncio
async def test_auth_failure_raises():
    client = make_client(lambda _m: None, auth_ok=False)
    with pytest.raises(HAAuthError):
        await connect_fake(client)


@pytest.mark.asyncio
async def test_send_command_correlates_by_id():
    client = make_client(lambda m: ok(m, {"echo": m["type"]}))
    await connect_fake(client)
    try:
        assert await client.send_command("ping") == {"echo": "ping"}
        assert await client.send_command("pong") == {"echo": "pong"}
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_command_failure_raises_with_code():
    def responder(message):
        return {
            "id": message["id"],
            "type": "result",
            "success": False,
            "error": {"code": "not_found", "message": "nope"},
        }

    client = make_client(responder)
    await connect_fake(client)
    try:
        with pytest.raises(HACommandError) as excinfo:
            await client.send_command("config/area_registry/delete", area_id="x")
        assert excinfo.value.code == "not_found"
        assert excinfo.value.command == "config/area_registry/delete"
    finally:
        await client.close()


# --- registries -----------------------------------------------------------


@pytest.mark.parametrize(
    ("call", "expected_type"),
    [
        ("list_entities", "config/entity_registry/list"),
        ("list_devices", "config/device_registry/list"),
        ("list_areas", "config/area_registry/list"),
        ("list_floors", "config/floor_registry/list"),
        ("list_labels", "config/label_registry/list"),
    ],
)
@pytest.mark.asyncio
async def test_registry_list_uses_the_websocket_command_names(call, expected_type):
    """Registries are WebSocket-only; these names are what HA actually accepts."""
    client = make_client(lambda m: ok(m, []))
    ws = await connect_fake(client)
    try:
        assert await getattr(client, call)() == []
        assert ws.sent[-1]["type"] == expected_type
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_update_device_sends_device_id_and_changes():
    client = make_client(lambda m: ok(m, {"id": "dev1", "name_by_user": "Bar Light"}))
    ws = await connect_fake(client)
    try:
        await client.update_device("dev1", name_by_user="Bar Light", area_id="kitchen")
        sent = ws.sent[-1]
        assert sent["type"] == "config/device_registry/update"
        assert sent["device_id"] == "dev1"
        assert sent["name_by_user"] == "Bar Light"
        assert sent["area_id"] == "kitchen"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_categories_are_scoped():
    client = make_client(lambda m: ok(m, []))
    ws = await connect_fake(client)
    try:
        await client.list_categories("automation")
        assert ws.sent[-1]["scope"] == "automation"
    finally:
        await client.close()


# --- supervisor -----------------------------------------------------------


@pytest.mark.asyncio
async def test_supervisor_api_passes_its_own_timeout_field():
    """The Supervisor takes a `timeout` field that must not collide with the
    client's own wait timeout — a real bug this test pins down."""
    client = make_client(lambda m: ok(m, {"addons": []}))
    ws = await connect_fake(client)
    try:
        await client.supervisor_api("/store/addons/core_ssh/install", method="post", timeout=900)
        sent = ws.sent[-1]
        assert sent["type"] == "supervisor/api"
        assert sent["endpoint"] == "/store/addons/core_ssh/install"
        assert sent["method"] == "post"
        assert sent["timeout"] == 900
    finally:
        await client.close()


# --- supervisor logs (TAP-5984) --------------------------------------------


@pytest.mark.asyncio
async def test_supervisor_api_refuses_log_endpoints_with_guidance():
    """Home Assistant's supervisor/api handler JSON-decodes every Supervisor
    response, so text log endpoints always die as an opaque unknown_error
    (reproduced live 2026-08-13 on HA 2026.8.1). The client refuses them up
    front and names the working path instead."""
    client = make_client(lambda m: ok(m))
    await connect_fake(client)
    try:
        for endpoint in (
            "/core/logs",
            "/supervisor/logs",
            "/addons/core_ssh/logs",
            "/host/logs/boots/0",
        ):
            with pytest.raises(ValueError, match="get_supervisor_logs"):
                await client.supervisor_api(endpoint)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_supervisor_api_still_forwards_non_log_endpoints():
    client = make_client(lambda m: ok(m, {"result": "ok"}))
    ws = await connect_fake(client)
    try:
        await client.supervisor_api("/addons")
        assert ws.sent[-1]["endpoint"] == "/addons"
    finally:
        await client.close()


# --- config flows ---------------------------------------------------------


class FakeRest(HARestClient):
    """HARestClient with `request` replaced by a scripted step sequence."""

    def __init__(self, steps: list[dict[str, Any]]) -> None:
        super().__init__("http://ha.test", "secret-token")
        self._steps = list(steps)
        self.calls: list[tuple[str, str]] = []

    async def request(self, method: str, path: str, **_kwargs: Any) -> Any:
        self.calls.append((method, path))
        return self._steps.pop(0)


@pytest.mark.asyncio
async def test_config_flow_completes():
    rest = FakeRest(
        [
            {"type": "form", "flow_id": "f1", "step_id": "user"},
            {"type": "create_entry", "title": "NWS", "result": "entry-1"},
        ]
    )
    step = await rest.run_config_flow("nws", [{"api_key": "x"}])
    assert step["type"] == "create_entry"


@pytest.mark.asyncio
async def test_external_step_surfaces_as_a_human_gate():
    """OAuth flows return type=external and core refuses client advancement.
    Gating on `type` is what makes this surface instead of failing obscurely."""
    rest = FakeRest([{"type": "external", "flow_id": "f1", "url": "https://accounts.google.com/x"}])
    with pytest.raises(HAHumanGateRequired) as excinfo:
        await rest.run_config_flow("google_drive", [])
    assert excinfo.value.external_url == "https://accounts.google.com/x"
    assert excinfo.value.flow_id == "f1"


@pytest.mark.asyncio
async def test_progress_step_exposes_device_code_placeholders():
    """HACS puts its GitHub device code in description_placeholders."""
    rest = FakeRest(
        [
            {
                "type": "progress",
                "flow_id": "f2",
                "description_placeholders": {
                    "url": "https://github.com/login/device",
                    "code": "ABCD-1234",
                },
            }
        ]
    )
    with pytest.raises(HAHumanGateRequired) as excinfo:
        await rest.run_config_flow("hacs", [])
    assert excinfo.value.placeholders["code"] == "ABCD-1234"


@pytest.mark.asyncio
async def test_abort_raises_flow_error():
    rest = FakeRest([{"type": "abort", "reason": "already_configured"}])
    with pytest.raises(HAFlowError, match="already_configured"):
        await rest.run_config_flow("nws", [])


@pytest.mark.asyncio
async def test_running_out_of_input_is_an_error_not_a_silent_stop():
    rest = FakeRest([{"type": "form", "flow_id": "f1", "step_id": "user"}])
    with pytest.raises(HAFlowError, match="none was supplied"):
        await rest.run_config_flow("nws", [])


def test_classify_flow_step_defaults_to_form():
    assert HARestClient.classify_flow_step({}) == "form"
    assert HARestClient.classify_flow_step({"type": "external"}) == "external"


# --- facade ---------------------------------------------------------------


def test_ha_client_derives_the_websocket_url():
    client = HAClient("http://192.168.1.80:8123", "t")
    assert client.ws._url == "ws://192.168.1.80:8123/api/websocket"  # noqa: SLF001
    secure = HAClient("https://example.ui.nabu.casa", "t")
    assert secure.ws._url == "wss://example.ui.nabu.casa/api/websocket"  # noqa: SLF001


def test_ha_client_from_env_requires_credentials(monkeypatch):
    for name in ("HOME_ASSISTANT_URL", "HOME_ASSISTANT_TOKEN", "HA_URL", "HA_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(Exception, match="HOME_ASSISTANT_URL"):
        HAClient.from_env()


@pytest.mark.asyncio
async def test_event_frames_before_the_result_do_not_resolve_the_command():
    """Subscription-style commands (zha/devices/permit) stream event frames
    under the same id before their result. Observed live 2026-08-12: the
    permit call reported an empty "unknown" error while succeeding, because
    the first event frame resolved the future."""

    def responder(message: dict[str, Any]) -> dict[str, Any] | None:
        if message.get("type") == "zha/devices/permit":
            # Queue two event frames, then the real result, all same id.
            ws = client._ws  # noqa: SLF001 - test seam
            for _ in range(2):
                ws._outbox.put_nowait(  # noqa: SLF001
                    json.dumps(
                        {
                            "id": message["id"],
                            "type": "event",
                            "event": {"type": "log_output"},
                        }
                    )
                )
            return ok(message, None)
        return ok(message, None)

    client = make_client(responder)
    await connect_fake(client)

    result = await client.send_command("zha/devices/permit", duration=60)

    assert result is None  # success: the result frame, not an event, resolved it
    await client.close()


# --- supervisor logs via REST (TAP-5984) ------------------------------------


@pytest.mark.asyncio
async def test_get_supervisor_logs_uses_the_rest_proxy_and_returns_text():
    """The core's /api/hassio proxy forwards journald text untouched — the
    supported log path, since the WS passthrough can only carry JSON."""
    rest = FakeRest(["2026-08-13 00:00:00 INFO booting\n2026-08-13 00:00:01 INFO ready"])
    text = await rest.get_supervisor_logs()
    assert rest.calls == [("GET", "/api/hassio/core/logs")]
    assert "INFO ready" in text.splitlines()[-1]


@pytest.mark.asyncio
async def test_get_supervisor_logs_targets_the_requested_endpoint():
    rest = FakeRest(["addon log line"])
    text = await rest.get_supervisor_logs("/addons/core_ssh/logs")
    assert rest.calls == [("GET", "/api/hassio/addons/core_ssh/logs")]
    assert text == "addon log line"
