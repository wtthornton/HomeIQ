"""
Agent Evaluation Framework — Alert Engine

Manages lifecycle-based alerts for threshold violations.  Alerts are
created when evaluation scores drop below configured thresholds and
auto-resolved when scores recover.

Usage::

    engine = AlertEngine()
    alerts = engine.check_report(batch_report, config)
    engine.acknowledge(alert_id, by="operator", note="Investigating")
    active = engine.get_active_alerts()
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from .config import AgentEvalConfig
from .models import BatchReport, EvalAlert, EvalLevel

logger = logging.getLogger(__name__)


class AlertEngine:
    """
    Lifecycle-managed alert system for evaluation threshold violations.

    Alerts follow the lifecycle: active → acknowledged → resolved.
    Deduplication prevents repeated alerts for the same ongoing violation.
    Auto-resolve clears alerts when scores recover above thresholds.
    """

    def __init__(self) -> None:
        # Active alerts keyed by dedup key (agent:metric)
        self._alerts: dict[str, EvalAlert] = {}

    @property
    def alert_count(self) -> int:
        """Total number of tracked alerts (all statuses)."""
        return len(self._alerts)

    def check_report(
        self,
        report: BatchReport,
        config: AgentEvalConfig,
    ) -> list[EvalAlert]:
        """
        Check a batch report against thresholds and return new/updated alerts.

        - Creates new alerts for violations not already tracked
        - Updates existing alerts with latest scores
        - Auto-resolves alerts where scores have recovered
        """
        new_alerts: list[EvalAlert] = []
        violated_keys: set[str] = set()

        for metric, threshold in config.thresholds.items():
            actual = report.aggregate_scores.get(metric)
            if actual is None:
                continue

            key = f"{config.agent_name}:{metric}"

            if actual < threshold:
                violated_keys.add(key)
                alert = self._get_or_create_alert(
                    key=key,
                    agent_name=config.agent_name,
                    metric=metric,
                    threshold=threshold,
                    actual=actual,
                    report=report,
                )
                new_alerts.append(alert)
            # Score recovered — resolve if alert exists
            elif key in self._alerts and self._alerts[key].status != "resolved":
                self._resolve_alert(key, actual)

        return new_alerts

    def acknowledge(
        self,
        alert_id: str,
        by: str,
        note: str = "",
    ) -> EvalAlert | None:
        """
        Acknowledge an alert by ID.

        Returns the updated alert, or None if not found.
        """
        for alert in self._alerts.values():
            if alert.alert_id == alert_id:
                if alert.status == "resolved":
                    logger.warning(
                        "Cannot acknowledge resolved alert %s", alert_id
                    )
                    return alert
                alert.status = "acknowledged"
                alert.acknowledged_by = by
                alert.note = note
                alert.updated_at = datetime.now(UTC)
                logger.info(
                    "Alert %s acknowledged by %s", alert_id, by
                )
                return alert

        logger.warning("Alert %s not found", alert_id)
        return None

    def resolve(self, alert_id: str) -> EvalAlert | None:
        """Manually resolve an alert by ID."""
        for alert in self._alerts.values():
            if alert.alert_id == alert_id:
                alert.status = "resolved"
                alert.updated_at = datetime.now(UTC)
                return alert
        return None

    def get_active_alerts(
        self, agent_name: str | None = None
    ) -> list[EvalAlert]:
        """Get all active (non-resolved) alerts, optionally filtered by agent."""
        alerts = [
            a for a in self._alerts.values()
            if a.status in ("active", "acknowledged")
        ]
        if agent_name:
            alerts = [a for a in alerts if a.agent_name == agent_name]
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)

    def get_all_alerts(
        self, agent_name: str | None = None
    ) -> list[EvalAlert]:
        """Get all alerts including resolved, optionally filtered by agent."""
        alerts = list(self._alerts.values())
        if agent_name:
            alerts = [a for a in alerts if a.agent_name == agent_name]
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)

    def clear_resolved(self) -> int:
        """Remove all resolved alerts from tracking. Returns count removed."""
        resolved_keys = [
            k for k, a in self._alerts.items() if a.status == "resolved"
        ]
        for k in resolved_keys:
            del self._alerts[k]
        return len(resolved_keys)

    # -- internals ---------------------------------------------------------

    def _get_or_create_alert(
        self,
        key: str,
        agent_name: str,
        metric: str,
        threshold: float,
        actual: float,
        report: BatchReport,
    ) -> EvalAlert:
        """Get existing alert or create new one. Deduplicates by key."""
        existing = self._alerts.get(key)

        if existing is not None and existing.status != "resolved":
            # Update existing alert with latest score
            existing.actual_score = actual
            existing.updated_at = datetime.now(UTC)
            return existing

        # Determine level from report results
        level = self._find_level(metric, report)
        priority = "critical" if actual < threshold * 0.5 else "warning"

        alert = EvalAlert(
            agent_name=agent_name,
            evaluator_name=metric,
            level=level,
            metric=metric,
            threshold=threshold,
            actual_score=actual,
            priority=priority,
            status="active",
        )
        self._alerts[key] = alert

        logger.info(
            "New %s alert: %s:%s = %.4f < %.2f",
            priority,
            agent_name,
            metric,
            actual,
            threshold,
        )
        return alert

    def _resolve_alert(self, key: str, recovered_score: float) -> None:
        """Auto-resolve an alert when score recovers."""
        alert = self._alerts[key]
        alert.status = "resolved"
        alert.actual_score = recovered_score
        alert.updated_at = datetime.now(UTC)
        alert.note = f"Auto-resolved: score recovered to {recovered_score:.4f}"
        logger.info(
            "Alert auto-resolved: %s (score: %.4f)",
            key,
            recovered_score,
        )

    @staticmethod
    def _find_level(metric: str, report: BatchReport) -> EvalLevel:
        """Find the EvalLevel for a metric from report results."""
        for session_report in report.reports:
            for result in session_report.results:
                if result.evaluator_name == metric:
                    return result.level
        return EvalLevel.QUALITY  # Default fallback
