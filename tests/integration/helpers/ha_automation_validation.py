"""
HA automation listing and validation helper (Epic 53.3).

Reusable helpers to list automations from the deploy service or Home Assistant
and check if a given automation_id exists. Config via env:
- DEPLOY_SERVICE_URL: e.g. http://localhost:8036 (ai-automation-service-new)
- DEPLOY_AUTH_HEADER: optional, e.g. "Bearer <token>" for deploy service
- HA_URL: e.g. http://192.168.1.86:8123 (direct HA)
- HA_TOKEN: long-lived access token for HA (used as Bearer)
"""

from __future__ import annotations

import os
from typing import Any

import httpx


def _deploy_service_url() -> str | None:
    return os.environ.get("DEPLOY_SERVICE_URL", "http://localhost:8036").strip() or None


def _ha_url() -> str | None:
    return os.environ.get("HA_URL", "").strip() or None


def _ha_token() -> str | None:
    return os.environ.get("HA_TOKEN", "").strip() or None


def _deploy_auth_header() -> dict[str, str]:
    h = os.environ.get("DEPLOY_AUTH_HEADER", "").strip()
    if h.lower().startswith("bearer "):
        return {"Authorization": h}
    if h:
        return {"Authorization": f"Bearer {h}"}
    return {}


def _ha_headers() -> dict[str, str]:
    token = _ha_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


async def list_automations_from_deploy(
    deploy_url: str | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
) -> list[dict[str, Any]]:
    """
    List automations from the deploy service (GET /api/deploy/automations).

    Returns list of automation objects (shape depends on service).
    """
    base = (deploy_url or _deploy_service_url() or "").rstrip("/")
    if not base:
        return []
    url = f"{base}/api/deploy/automations"
    h = dict(_deploy_auth_header())
    if headers:
        h.update(headers)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url, headers=h)
            if r.status_code != 200:
                return []
            data = r.json()
            return data.get("automations", []) if isinstance(data, dict) else []
    except Exception:
        return []


async def list_automations_from_ha(
    ha_url: str | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
) -> list[dict[str, Any]]:
    """
    List automation configs from Home Assistant (GET /api/config/automation/config).

    Returns list of automation config objects (HA format).
    """
    base = (ha_url or _ha_url() or "").rstrip("/")
    if not base:
        return []
    url = f"{base}/api/config/automation/config"
    h = dict(_ha_headers())
    if headers:
        h.update(headers)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url, headers=h)
            if r.status_code != 200:
                return []
            data = r.json()
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _normalize_automation_id(automation_id: str) -> str:
    """Return entity_id form (e.g. automation.xyz)."""
    s = (automation_id or "").strip()
    if s and not s.startswith("automation."):
        return f"automation.{s}" if s.replace("_", "").isalnum() else s
    return s


async def automation_exists(
    automation_id: str,
    *,
    deploy_url: str | None = None,
    ha_url: str | None = None,
    deploy_headers: dict[str, str] | None = None,
    ha_headers_override: dict[str, str] | None = None,
    timeout: float = 15.0,
) -> bool:
    """
    Return True if the given automation_id exists in the deploy service or HA.

    Checks deploy service first (if DEPLOY_SERVICE_URL or deploy_url is set),
    then HA direct (if HA_URL or ha_url is set). automation_id can be
    "automation.test_xyz" or "test_xyz".
    """
    normalized = _normalize_automation_id(automation_id or "")
    if not normalized:
        return False
    automation_id = normalized

    # Try deploy service: list and look for matching id
    deploy_base = deploy_url or _deploy_service_url()
    if deploy_base:
        automations = await list_automations_from_deploy(
            deploy_url=deploy_base, headers=deploy_headers, timeout=timeout
        )
        for a in automations:
            aid = a.get("automation_id") or a.get("entity_id") or a.get("id") or ""
            if automation_id == aid or automation_id in str(aid):
                return True
        # Also try GET /api/deploy/automations/{id}
        base = deploy_base.rstrip("/")
        url = f"{base}/api/deploy/automations/{automation_id}"
        h = dict(_deploy_auth_header())
        if deploy_headers:
            h.update(deploy_headers)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(url, headers=h)
                if r.status_code == 200:
                    return True
        except Exception:
            pass

    # Try HA direct: GET /api/states/{entity_id}
    ha_base = ha_url or _ha_url()
    if ha_base:
        url = f"{ha_base.rstrip('/')}/api/states/{automation_id}"
        h = dict(_ha_headers())
        if ha_headers_override:
            h.update(ha_headers_override)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(url, headers=h)
                if r.status_code == 200:
                    return True
        except Exception:
            pass

    return False
