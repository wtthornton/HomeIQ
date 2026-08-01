"""Tests for hygiene endpoints proxying device intelligence service."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from src.main import app

from src import hygiene_endpoints


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_list_hygiene_issues(monkeypatch, client):
    async def fake_request(method, path, params=None, payload=None):
        assert method == "GET"
        assert path == "/api/hygiene/issues"
        return {
            "issues": [
                {
                    "issue_key": "duplicate_name:dev-1",
                    "issue_type": "duplicate_name",
                    "severity": "high",
                    "status": "open",
                    "metadata": {},
                    "detected_at": "2025-11-07T17:00:00Z",
                    "updated_at": "2025-11-07T17:05:00Z",
                }
            ],
            "count": 1,
            "total": 1,
        }

    monkeypatch.setattr(hygiene_endpoints, "_request_device_intelligence", fake_request)

    response = await client.get("/api/v1/hygiene/issues")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["issues"][0]["issue_key"] == "duplicate_name:dev-1"


@pytest.mark.asyncio
async def test_update_hygiene_issue_status(monkeypatch, client):
    async def fake_request(method, path, params=None, payload=None):
        assert method == "POST"
        assert path.endswith("/status")
        return {
            "issue_key": "duplicate_name:dev-1",
            "issue_type": "duplicate_name",
            "severity": "high",
            "status": payload["status"],
            "metadata": {},
            "detected_at": "2025-11-07T17:00:00Z",
            "updated_at": "2025-11-07T17:10:00Z",
            "resolved_at": "2025-11-07T17:10:00Z" if payload["status"] == "resolved" else None,
        }

    monkeypatch.setattr(hygiene_endpoints, "_request_device_intelligence", fake_request)

    response = await client.post(
        "/api/v1/hygiene/issues/duplicate_name:dev-1/status",
        json={"status": "resolved"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "resolved"
    assert payload["resolved_at"] is not None


@pytest.mark.asyncio
async def test_apply_issue_action(monkeypatch, client):
    async def fake_request(method, path, params=None, payload=None):
        assert method == "POST"
        assert path.endswith("/actions/apply")
        return {
            "issue_key": "duplicate_name:dev-1",
            "issue_type": "duplicate_name",
            "severity": "high",
            "status": "resolved",
            "metadata": {"applied_value": payload["value"]},
            "detected_at": "2025-11-07T17:00:00Z",
            "updated_at": "2025-11-07T17:15:00Z",
            "resolved_at": "2025-11-07T17:15:00Z",
        }

    monkeypatch.setattr(hygiene_endpoints, "_request_device_intelligence", fake_request)

    response = await client.post(
        "/api/v1/hygiene/issues/duplicate_name:dev-1/actions/apply",
        json={"action": "rename_device", "value": "Kitchen"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "resolved"
    assert payload["metadata"]["applied_value"] == "Kitchen"

