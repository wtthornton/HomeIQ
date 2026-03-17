"""
AlertManager Webhook Endpoint
Epic 79, Story 79.6: Admin API Alert Webhook Handler

Receives AlertManager webhook POSTs, logs alerts to structured logging,
stores active alerts in-memory with TTL, and exposes them via GET endpoint.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["AlertManager Webhooks"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AlertManagerAlert(BaseModel):
    """Single alert from an AlertManager webhook payload."""
    status: str  # "firing" or "resolved"
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: str = ""
    endsAt: str = ""
    generatorURL: str = ""
    fingerprint: str = ""


class AlertManagerWebhookPayload(BaseModel):
    """AlertManager webhook POST body (v4 API format)."""
    version: str = "4"
    groupKey: str = ""
    truncatedAlerts: int = 0
    status: str = ""  # "firing" or "resolved"
    receiver: str = ""
    groupLabels: dict[str, str] = Field(default_factory=dict)
    commonLabels: dict[str, str] = Field(default_factory=dict)
    commonAnnotations: dict[str, str] = Field(default_factory=dict)
    externalURL: str = ""
    alerts: list[AlertManagerAlert] = Field(default_factory=list)


class ActiveAlertResponse(BaseModel):
    """Response model for a single active alert."""
    fingerprint: str
    alertname: str
    status: str
    severity: str
    service: str
    tier: str
    summary: str
    description: str
    starts_at: str
    received_at: str
    labels: dict[str, str]


class WebhookResponse(BaseModel):
    """Response returned after processing a webhook."""
    status: str
    processed: int
    firing: int
    resolved: int
    timestamp: str


# ---------------------------------------------------------------------------
# In-Memory Alert Store
# ---------------------------------------------------------------------------

class AlertStore:
    """Thread-safe in-memory store for active alerts with TTL expiry.

    Alerts are keyed by fingerprint (unique per alert instance in AlertManager).
    Resolved alerts are removed immediately. Firing alerts expire after *ttl_seconds*
    if AlertManager stops sending updates (e.g. Prometheus restart).
    """

    def __init__(self, ttl_seconds: int = 900) -> None:  # 15-minute default TTL
        self._alerts: dict[str, dict[str, Any]] = {}
        self._ttl: int = ttl_seconds

    def upsert(self, fingerprint: str, alert_data: dict[str, Any]) -> None:
        """Insert or update an alert."""
        alert_data["_received_at"] = time.monotonic()
        self._alerts[fingerprint] = alert_data

    def remove(self, fingerprint: str) -> None:
        """Remove a resolved alert."""
        self._alerts.pop(fingerprint, None)

    def get_active(self, *, severity: str | None = None) -> list[dict[str, Any]]:
        """Return active (non-expired) alerts, optionally filtered by severity."""
        self._evict_expired()
        alerts = list(self._alerts.values())
        if severity:
            alerts = [
                a for a in alerts
                if a.get("labels", {}).get("severity", "") == severity
            ]
        return alerts

    def count(self) -> int:
        """Return number of active alerts."""
        self._evict_expired()
        return len(self._alerts)

    def _evict_expired(self) -> None:
        """Remove alerts older than TTL."""
        now = time.monotonic()
        expired = [
            fp for fp, data in self._alerts.items()
            if (now - data.get("_received_at", 0)) > self._ttl
        ]
        for fp in expired:
            del self._alerts[fp]


# Module-level singleton
_alert_store = AlertStore()


def get_alert_store() -> AlertStore:
    """Return the module-level AlertStore singleton."""
    return _alert_store


def get_active_alert_count() -> int:
    """Return the count of currently active alerts (for /health enrichment)."""
    return _alert_store.count()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/webhook", response_model=WebhookResponse)
async def alertmanager_webhook(payload: AlertManagerWebhookPayload) -> WebhookResponse:
    """Receive AlertManager webhook POST.

    Processes each alert in the payload:
    - Firing alerts are stored in-memory with structured logging.
    - Resolved alerts are removed from the active store.
    """
    firing_count = 0
    resolved_count = 0

    for alert in payload.alerts:
        alertname = alert.labels.get("alertname", "unknown")
        severity = alert.labels.get("severity", "unknown")
        service = alert.labels.get("service", "unknown")
        tier = alert.labels.get("tier", "")
        summary = alert.annotations.get("summary", "")

        if alert.status == "firing":
            firing_count += 1
            logger.warning(
                "ALERT FIRING: [%s] %s severity=%s service=%s tier=%s summary=%s",
                alert.fingerprint,
                alertname,
                severity,
                service,
                tier,
                summary,
            )
            _alert_store.upsert(alert.fingerprint, {
                "fingerprint": alert.fingerprint,
                "alertname": alertname,
                "status": "firing",
                "severity": severity,
                "service": service,
                "tier": tier,
                "summary": summary,
                "description": alert.annotations.get("description", ""),
                "starts_at": alert.startsAt,
                "received_at": datetime.now(UTC).isoformat() + "Z",
                "labels": alert.labels,
            })

        elif alert.status == "resolved":
            resolved_count += 1
            logger.info(
                "ALERT RESOLVED: [%s] %s service=%s",
                alert.fingerprint,
                alertname,
                service,
            )
            _alert_store.remove(alert.fingerprint)

    logger.info(
        "Webhook processed: receiver=%s group=%s firing=%d resolved=%d total_active=%d",
        payload.receiver,
        payload.groupKey,
        firing_count,
        resolved_count,
        _alert_store.count(),
    )

    return WebhookResponse(
        status="ok",
        processed=len(payload.alerts),
        firing=firing_count,
        resolved=resolved_count,
        timestamp=datetime.now(UTC).isoformat() + "Z",
    )


@router.get("/active", response_model=list[ActiveAlertResponse])
async def get_active_alerts(
    severity: str | None = Query(None, description="Filter by severity (critical, warning)"),
) -> list[ActiveAlertResponse]:
    """Return all currently active (firing) alerts from AlertManager.

    Used by health-dashboard to display real-time alert status.
    """
    alerts = _alert_store.get_active(severity=severity)
    return [
        ActiveAlertResponse(
            fingerprint=a["fingerprint"],
            alertname=a["alertname"],
            status=a["status"],
            severity=a["severity"],
            service=a["service"],
            tier=a.get("tier", ""),
            summary=a.get("summary", ""),
            description=a.get("description", ""),
            starts_at=a.get("starts_at", ""),
            received_at=a.get("received_at", ""),
            labels=a.get("labels", {}),
        )
        for a in alerts
    ]


@router.get("/active/count")
async def get_active_alert_count_endpoint() -> dict[str, Any]:
    """Return count of active alerts, grouped by severity."""
    alerts = _alert_store.get_active()
    by_severity: dict[str, int] = {}
    for a in alerts:
        sev = a.get("severity", "unknown")
        by_severity[sev] = by_severity.get(sev, 0) + 1

    return {
        "total": len(alerts),
        "by_severity": by_severity,
        "timestamp": datetime.now(UTC).isoformat() + "Z",
    }
