"""Unit tests for hygiene_endpoints.py — Device Hygiene API

Tests the hygiene router endpoints with mocked httpx calls
to the device-intelligence service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.hygiene_endpoints import (
    ApplyIssueActionRequest,
    HygieneIssueListResponse,
    HygieneIssueResponse,
    UpdateIssueStatusRequest,
    _request_device_intelligence,
    router,
)


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

def _sample_issue(**overrides) -> dict:
    """Return a sample hygiene issue dict."""
    data = {
        "issue_key": "hygiene-001",
        "issue_type": "naming",
        "severity": "warning",
        "status": "open",
        "device_id": "dev-123",
        "entity_id": "light.living_room",
        "name": "Living Room Light",
        "summary": "Entity has non-standard naming",
        "suggested_action": "rename",
        "suggested_value": "light.living_room_main",
        "metadata": {"source": "convention_check"},
        "detected_at": "2026-03-18T08:00:00Z",
        "updated_at": "2026-03-18T08:00:00Z",
        "resolved_at": None,
    }
    data.update(overrides)
    return data


def _sample_issue_list(count=2):
    """Return a sample issue list payload from device-intelligence."""
    issues = [_sample_issue(issue_key=f"hygiene-{i:03d}") for i in range(count)]
    return {"issues": issues, "count": count, "total": count}


def _mock_httpx_response(status_code=200, json_data=None, text=""):
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = text
    return resp


# ---------------------------------------------------------------------------
# Pydantic model tests
# ---------------------------------------------------------------------------

class TestPydanticModels:

    @pytest.mark.unit
    def test_hygiene_issue_response_valid(self):
        issue = HygieneIssueResponse(**_sample_issue())
        assert issue.issue_key == "hygiene-001"
        assert issue.severity == "warning"
        assert issue.device_id == "dev-123"

    @pytest.mark.unit
    def test_hygiene_issue_response_minimal(self):
        issue = HygieneIssueResponse(
            issue_key="k", issue_type="t", severity="low", status="open"
        )
        assert issue.device_id is None
        assert issue.metadata == {}

    @pytest.mark.unit
    def test_hygiene_issue_list_response(self):
        items = [HygieneIssueResponse(**_sample_issue())]
        resp = HygieneIssueListResponse(issues=items, count=1, total=1)
        assert resp.count == 1
        assert len(resp.issues) == 1

    @pytest.mark.unit
    def test_update_issue_status_valid_values(self):
        for val in ("open", "ignored", "resolved"):
            req = UpdateIssueStatusRequest(status=val)
            assert req.status == val

    @pytest.mark.unit
    def test_update_issue_status_invalid(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UpdateIssueStatusRequest(status="invalid_status")

    @pytest.mark.unit
    def test_apply_issue_action_request(self):
        req = ApplyIssueActionRequest(action="rename", value="new_name")
        assert req.action == "rename"
        assert req.value == "new_name"

    @pytest.mark.unit
    def test_apply_issue_action_no_value(self):
        req = ApplyIssueActionRequest(action="dismiss")
        assert req.value is None


# ---------------------------------------------------------------------------
# _request_device_intelligence helper
# ---------------------------------------------------------------------------

class TestRequestDeviceIntelligence:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_success(self):
        mock_resp = _mock_httpx_response(200, json_data={"ok": True})

        with patch("src.hygiene_endpoints.httpx.AsyncClient") as mock_cls:
            client_ctx = AsyncMock()
            client_ctx.__aenter__ = AsyncMock(return_value=client_ctx)
            client_ctx.__aexit__ = AsyncMock(return_value=False)
            client_ctx.request = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = client_ctx

            result = await _request_device_intelligence("GET", "/api/hygiene/issues")

        assert result == {"ok": True}
        client_ctx.request.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_with_params(self):
        mock_resp = _mock_httpx_response(200, json_data={"issues": []})

        with patch("src.hygiene_endpoints.httpx.AsyncClient") as mock_cls:
            client_ctx = AsyncMock()
            client_ctx.__aenter__ = AsyncMock(return_value=client_ctx)
            client_ctx.__aexit__ = AsyncMock(return_value=False)
            client_ctx.request = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = client_ctx

            result = await _request_device_intelligence(
                "GET", "/api/hygiene/issues", params={"status": "open"}
            )

        call_kwargs = client_ctx.request.call_args
        assert call_kwargs.kwargs.get("params") == {"status": "open"}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_post_with_payload(self):
        mock_resp = _mock_httpx_response(200, json_data=_sample_issue())

        with patch("src.hygiene_endpoints.httpx.AsyncClient") as mock_cls:
            client_ctx = AsyncMock()
            client_ctx.__aenter__ = AsyncMock(return_value=client_ctx)
            client_ctx.__aexit__ = AsyncMock(return_value=False)
            client_ctx.request = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = client_ctx

            result = await _request_device_intelligence(
                "POST", "/api/hygiene/issues/k/status",
                payload={"status": "resolved"},
            )

        call_kwargs = client_ctx.request.call_args
        assert call_kwargs.kwargs.get("json") == {"status": "resolved"}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_404_raises_http_exception(self):
        mock_resp = _mock_httpx_response(
            404, json_data={"detail": "Issue not found"}
        )

        with patch("src.hygiene_endpoints.httpx.AsyncClient") as mock_cls:
            client_ctx = AsyncMock()
            client_ctx.__aenter__ = AsyncMock(return_value=client_ctx)
            client_ctx.__aexit__ = AsyncMock(return_value=False)
            client_ctx.request = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = client_ctx

            with pytest.raises(HTTPException) as exc_info:
                await _request_device_intelligence("GET", "/api/hygiene/issues/missing")

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Issue not found"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_500_raises_http_exception(self):
        mock_resp = _mock_httpx_response(
            500, json_data={"detail": "Internal error"}
        )

        with patch("src.hygiene_endpoints.httpx.AsyncClient") as mock_cls:
            client_ctx = AsyncMock()
            client_ctx.__aenter__ = AsyncMock(return_value=client_ctx)
            client_ctx.__aexit__ = AsyncMock(return_value=False)
            client_ctx.request = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = client_ctx

            with pytest.raises(HTTPException) as exc_info:
                await _request_device_intelligence("GET", "/any")

        assert exc_info.value.status_code == 500

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_error_response_json_parse_failure(self):
        """When error response body isn't valid JSON, fall back to text."""
        mock_resp = MagicMock()
        mock_resp.status_code = 502
        mock_resp.json.side_effect = ValueError("bad json")
        mock_resp.text = "Bad Gateway"

        with patch("src.hygiene_endpoints.httpx.AsyncClient") as mock_cls:
            client_ctx = AsyncMock()
            client_ctx.__aenter__ = AsyncMock(return_value=client_ctx)
            client_ctx.__aexit__ = AsyncMock(return_value=False)
            client_ctx.request = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = client_ctx

            with pytest.raises(HTTPException) as exc_info:
                await _request_device_intelligence("GET", "/any")

        assert exc_info.value.status_code == 502
        assert exc_info.value.detail == "Bad Gateway"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_uses_configured_base_url(self):
        mock_resp = _mock_httpx_response(200, json_data={})

        with patch("src.hygiene_endpoints.httpx.AsyncClient") as mock_cls, \
             patch("src.hygiene_endpoints.DEVICE_INTELLIGENCE_URL", "http://custom:9999"):
            client_ctx = AsyncMock()
            client_ctx.__aenter__ = AsyncMock(return_value=client_ctx)
            client_ctx.__aexit__ = AsyncMock(return_value=False)
            client_ctx.request = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = client_ctx

            await _request_device_intelligence("GET", "/test")

        call_args = client_ctx.request.call_args
        assert call_args.args[1] == "http://custom:9999/test"


# ---------------------------------------------------------------------------
# GET /api/v1/hygiene/issues
# ---------------------------------------------------------------------------

class TestListHygieneIssues:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_issues_no_filter(self):
        from src.hygiene_endpoints import list_hygiene_issues

        payload = _sample_issue_list(2)
        with patch("src.hygiene_endpoints._request_device_intelligence", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = payload

            result = await list_hygiene_issues(
                status_filter=None, severity=None, issue_type=None,
                device_id=None, limit=100,
            )

        assert result.count == 2
        assert result.total == 2
        assert len(result.issues) == 2
        mock_req.assert_called_once_with(
            "GET", "/api/hygiene/issues", params={"limit": 100}
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_issues_with_status_filter(self):
        from src.hygiene_endpoints import list_hygiene_issues

        payload = _sample_issue_list(1)
        with patch("src.hygiene_endpoints._request_device_intelligence", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = payload

            result = await list_hygiene_issues(
                status_filter="open", severity=None, issue_type=None,
                device_id=None, limit=100,
            )

        call_params = mock_req.call_args.kwargs.get("params") or mock_req.call_args[0][2]
        assert call_params["status"] == "open"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_issues_with_severity_filter(self):
        from src.hygiene_endpoints import list_hygiene_issues

        payload = _sample_issue_list(1)
        with patch("src.hygiene_endpoints._request_device_intelligence", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = payload

            result = await list_hygiene_issues(
                status_filter=None, severity="critical", issue_type=None,
                device_id=None, limit=100,
            )

        call_params = mock_req.call_args.kwargs.get("params") or mock_req.call_args[0][2]
        assert call_params["severity"] == "critical"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_issues_with_device_id_filter(self):
        from src.hygiene_endpoints import list_hygiene_issues

        payload = _sample_issue_list(1)
        with patch("src.hygiene_endpoints._request_device_intelligence", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = payload

            result = await list_hygiene_issues(
                status_filter=None, severity=None, issue_type=None,
                device_id="dev-xyz", limit=100,
            )

        call_params = mock_req.call_args.kwargs.get("params") or mock_req.call_args[0][2]
        assert call_params["device_id"] == "dev-xyz"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_issues_with_issue_type_filter(self):
        from src.hygiene_endpoints import list_hygiene_issues

        payload = _sample_issue_list(1)
        with patch("src.hygiene_endpoints._request_device_intelligence", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = payload

            result = await list_hygiene_issues(
                status_filter=None, severity=None, issue_type="naming",
                device_id=None, limit=100,
            )

        call_params = mock_req.call_args.kwargs.get("params") or mock_req.call_args[0][2]
        assert call_params["issue_type"] == "naming"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_issues_all_filters(self):
        from src.hygiene_endpoints import list_hygiene_issues

        payload = _sample_issue_list(1)
        with patch("src.hygiene_endpoints._request_device_intelligence", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = payload

            result = await list_hygiene_issues(
                status_filter="open", severity="warning",
                issue_type="naming", device_id="dev-1", limit=50,
            )

        call_params = mock_req.call_args.kwargs.get("params") or mock_req.call_args[0][2]
        assert call_params == {
            "limit": 50,
            "status": "open",
            "severity": "warning",
            "issue_type": "naming",
            "device_id": "dev-1",
        }

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_issues_empty_result(self):
        from src.hygiene_endpoints import list_hygiene_issues

        payload = {"issues": [], "count": 0, "total": 0}
        with patch("src.hygiene_endpoints._request_device_intelligence", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = payload

            result = await list_hygiene_issues(
                status_filter=None, severity=None, issue_type=None,
                device_id=None, limit=100,
            )

        assert result.count == 0
        assert result.issues == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_issues_service_down(self):
        from src.hygiene_endpoints import list_hygiene_issues

        with patch("src.hygiene_endpoints._request_device_intelligence", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = HTTPException(status_code=503, detail="Service unavailable")

            with pytest.raises(HTTPException) as exc_info:
                await list_hygiene_issues(
                    status_filter=None, severity=None, issue_type=None,
                    device_id=None, limit=100,
                )

        assert exc_info.value.status_code == 503


# ---------------------------------------------------------------------------
# POST /api/v1/hygiene/issues/{key}/status
# ---------------------------------------------------------------------------

class TestUpdateIssueStatus:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_status_resolved(self):
        from src.hygiene_endpoints import update_issue_status

        result_data = _sample_issue(status="resolved", resolved_at="2026-03-18T12:00:00Z")
        with patch("src.hygiene_endpoints._request_device_intelligence", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = result_data
            payload = UpdateIssueStatusRequest(status="resolved")

            result = await update_issue_status("hygiene-001", payload)

        assert result.status == "resolved"
        mock_req.assert_called_once_with(
            "POST",
            "/api/hygiene/issues/hygiene-001/status",
            payload={"status": "resolved"},
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_status_ignored(self):
        from src.hygiene_endpoints import update_issue_status

        result_data = _sample_issue(status="ignored")
        with patch("src.hygiene_endpoints._request_device_intelligence", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = result_data
            payload = UpdateIssueStatusRequest(status="ignored")

            result = await update_issue_status("hygiene-002", payload)

        assert result.status == "ignored"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_status_not_found(self):
        from src.hygiene_endpoints import update_issue_status

        with patch("src.hygiene_endpoints._request_device_intelligence", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = HTTPException(status_code=404, detail="Not found")
            payload = UpdateIssueStatusRequest(status="resolved")

            with pytest.raises(HTTPException) as exc_info:
                await update_issue_status("nonexistent", payload)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/hygiene/issues/{key}/actions/apply
# ---------------------------------------------------------------------------

class TestApplyIssueAction:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_apply_rename_action(self):
        from src.hygiene_endpoints import apply_issue_action

        result_data = _sample_issue(status="resolved")
        with patch("src.hygiene_endpoints._request_device_intelligence", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = result_data
            payload = ApplyIssueActionRequest(action="rename", value="light.kitchen_main")

            result = await apply_issue_action("hygiene-001", payload)

        assert result.issue_key == "hygiene-001"
        mock_req.assert_called_once_with(
            "POST",
            "/api/hygiene/issues/hygiene-001/actions/apply",
            payload={"action": "rename", "value": "light.kitchen_main"},
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_apply_action_no_value(self):
        from src.hygiene_endpoints import apply_issue_action

        result_data = _sample_issue(status="resolved")
        with patch("src.hygiene_endpoints._request_device_intelligence", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = result_data
            payload = ApplyIssueActionRequest(action="dismiss")

            result = await apply_issue_action("hygiene-005", payload)

        call_payload = mock_req.call_args.kwargs.get("payload") or mock_req.call_args[0][2]
        # model_dump includes value=None
        assert call_payload["action"] == "dismiss"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_apply_action_service_error(self):
        from src.hygiene_endpoints import apply_issue_action

        with patch("src.hygiene_endpoints._request_device_intelligence", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = HTTPException(status_code=500, detail="Internal error")
            payload = ApplyIssueActionRequest(action="rename", value="x")

            with pytest.raises(HTTPException) as exc_info:
                await apply_issue_action("hygiene-001", payload)

        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# Router structure
# ---------------------------------------------------------------------------

class TestRouterStructure:

    @pytest.mark.unit
    def test_router_prefix(self):
        assert router.prefix == "/api/v1/hygiene"

    @pytest.mark.unit
    def test_router_tags(self):
        assert "Device Hygiene" in router.tags

    @pytest.mark.unit
    def test_router_has_expected_routes(self):
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        # Routes include the router prefix
        assert "/api/v1/hygiene/issues" in paths
        assert "/api/v1/hygiene/issues/{issue_key}/status" in paths
        assert "/api/v1/hygiene/issues/{issue_key}/actions/apply" in paths
