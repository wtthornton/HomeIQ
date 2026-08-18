import httpx
import pytest
import respx
from src.backends import HttpBacking, build_backings
from src.errors import ToolError

BASE = "http://data-api.test:8006"


@pytest.fixture
def backing():
    return HttpBacking("data-api", BASE + "/", bearer_token="secret")


@respx.mock
async def test_get_json_sends_bearer_and_drops_none_params(backing):
    route = respx.get(f"{BASE}/api/v1/things").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    body = await backing.get_json("/api/v1/things", {"a": 1, "b": None}, tool="t")
    assert body == {"ok": True}
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer secret"
    assert request.url.params.get("a") == "1" and "b" not in request.url.params


@respx.mock
@pytest.mark.parametrize(
    ("status", "code", "fragment"),
    [
        (404, "not_found", "no data"),
        (401, "backing_unavailable", "credential"),
        (403, "backing_unavailable", "credential"),
        (500, "backing_unavailable", "HTTP 500"),
        (502, "backing_unavailable", "HTTP 502"),
    ],
)
async def test_http_status_maps_to_catalogue_codes(backing, status, code, fragment):
    respx.get(f"{BASE}/x").mock(return_value=httpx.Response(status))
    with pytest.raises(ToolError) as exc:
        await backing.get_json("/x", tool="t")
    assert exc.value.code == code
    assert fragment in exc.value.message
    assert exc.value.tool == "t"


@respx.mock
@pytest.mark.parametrize(
    ("side_effect", "fragment"),
    [(httpx.ConnectTimeout("t"), "timed out"), (httpx.ConnectError("c"), "unreachable")],
)
async def test_transport_failures_are_backing_unavailable(backing, side_effect, fragment):
    respx.get(f"{BASE}/x").mock(side_effect=side_effect)
    with pytest.raises(ToolError) as exc:
        await backing.get_json("/x", tool="t")
    assert exc.value.code == "backing_unavailable"
    assert fragment in exc.value.message


@respx.mock
async def test_non_json_body_is_contract_violation(backing):
    respx.get(f"{BASE}/x").mock(return_value=httpx.Response(200, text="<html>"))
    with pytest.raises(ToolError) as exc:
        await backing.get_json("/x", tool="t")
    assert exc.value.code == "contract_violation"


async def test_unconfigured_backing_is_backing_unavailable():
    backing = HttpBacking("ai-pattern-service", "")
    with pytest.raises(ToolError) as exc:
        await backing.get_json("/x", tool="t")
    assert exc.value.code == "backing_unavailable"
    status = await backing.probe()
    assert status.ok is False and status.detail == "not configured"


@respx.mock
async def test_probe_reports_latency_and_status(backing):
    respx.get(f"{BASE}/health").mock(return_value=httpx.Response(200))
    status = await backing.probe()
    assert status.ok is True and status.latency_ms is not None and status.detail == "HTTP 200"


def test_build_backings_uses_settings(settings):
    backings = build_backings(settings)
    assert backings.data_api.base_url == "http://data-api.test:8006"
    assert [b.name for b in backings.all()] == [
        "data-api",
        "ai-pattern-service",
        "device-intelligence-service",
    ]
    assert backings.data_api._client.headers["authorization"] == "Bearer data-api-key"
