"""
Eval Degradation Alerting (Epic 69, Story 69.4).

Automated alerting when agent eval scores degrade:
- Rolling 24h average drops >10% vs 7-day baseline
- Any eval dimension drops below floor (50/100)

Alert payload: agent name, dimension, current vs baseline, sample trace IDs.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Alert thresholds
DROP_PCT_THRESHOLD = 10.0  # Alert if rolling avg drops >10%
FLOOR_THRESHOLD = 50.0  # Alert if any dimension drops below this
COOLDOWN_SECONDS = 3600  # 1 hour between re-alerts for same dimension


@dataclass
class EvalAlert:
    """An eval degradation alert."""

    alert_id: str
    timestamp: float
    agent_name: str
    dimension: str
    current_score: float
    baseline_score: float
    drop_pct: float
    alert_type: str  # "degradation" or "floor_breach"
    sample_trace_ids: list[str] = field(default_factory=list)
    acknowledged: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp,
            "agent_name": self.agent_name,
            "dimension": self.dimension,
            "current_score": round(self.current_score, 1),
            "baseline_score": round(self.baseline_score, 1),
            "drop_pct": round(self.drop_pct, 1),
            "alert_type": self.alert_type,
            "sample_trace_ids": self.sample_trace_ids,
            "acknowledged": self.acknowledged,
        }


@dataclass
class DimensionTracker:
    """Tracks scores for a single eval dimension over time."""

    dimension: str
    # Rolling 24h scores (timestamp, score)
    recent_scores: list[tuple[float, float]] = field(default_factory=list)
    # 7-day baseline average
    baseline_avg: float = 0.0
    baseline_sample_count: int = 0

    def add_score(self, score: float, trace_id: str = "") -> None:
        """Add a score observation."""
        now = time.time()
        self.recent_scores.append((now, score))
        # Prune scores older than 7 days
        cutoff = now - 7 * 86400
        self.recent_scores = [(t, s) for t, s in self.recent_scores if t > cutoff]

    @property
    def rolling_24h_avg(self) -> float:
        """Average score over last 24 hours."""
        cutoff = time.time() - 86400
        recent = [s for t, s in self.recent_scores if t > cutoff]
        return sum(recent) / len(recent) if recent else 0.0

    @property
    def rolling_7d_avg(self) -> float:
        """Average score over last 7 days."""
        if not self.recent_scores:
            return 0.0
        return sum(s for _, s in self.recent_scores) / len(self.recent_scores)

    @property
    def recent_count(self) -> int:
        cutoff = time.time() - 86400
        return sum(1 for t, _ in self.recent_scores if t > cutoff)


class EvalAlertService:
    """Monitors eval scores and fires alerts on degradation."""

    def __init__(self):
        # dimension_key → DimensionTracker
        self._trackers: dict[str, DimensionTracker] = {}
        self._alerts: list[EvalAlert] = []
        self._alert_counter = 0
        # Cooldown tracking: dimension_key → last alert timestamp
        self._last_alert_time: dict[str, float] = {}

    def record_score(
        self,
        agent_name: str,
        dimension: str,
        score: float,
        trace_id: str = "",
    ) -> EvalAlert | None:
        """Record an eval score and check for alert conditions.

        Returns an alert if degradation is detected, None otherwise.
        """
        key = f"{agent_name}:{dimension}"

        if key not in self._trackers:
            self._trackers[key] = DimensionTracker(dimension=dimension)

        tracker = self._trackers[key]
        tracker.add_score(score, trace_id)

        # Need minimum samples before alerting
        if tracker.recent_count < 5:
            return None

        # Check alert conditions
        alert = self._check_degradation(agent_name, key, tracker, trace_id)
        return alert

    def get_alerts(
        self,
        limit: int = 50,
        unacknowledged_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Get recent alerts."""
        alerts = self._alerts
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]
        return [a.to_dict() for a in alerts[-limit:]]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def get_tracker_status(self) -> dict[str, Any]:
        """Get status of all tracked dimensions."""
        return {
            key: {
                "dimension": t.dimension,
                "rolling_24h_avg": round(t.rolling_24h_avg, 1),
                "rolling_7d_avg": round(t.rolling_7d_avg, 1),
                "recent_count": t.recent_count,
                "total_scores": len(t.recent_scores),
            }
            for key, t in self._trackers.items()
        }

    def _check_degradation(
        self,
        agent_name: str,
        key: str,
        tracker: DimensionTracker,
        trace_id: str,
    ) -> EvalAlert | None:
        """Check if current scores indicate degradation."""
        now = time.time()

        # Cooldown check
        last_alert = self._last_alert_time.get(key, 0)
        if now - last_alert < COOLDOWN_SECONDS:
            return None

        current = tracker.rolling_24h_avg
        baseline = tracker.rolling_7d_avg

        # Check 1: Floor breach
        if current < FLOOR_THRESHOLD and current > 0:
            return self._fire_alert(
                agent_name=agent_name,
                dimension=tracker.dimension,
                current=current,
                baseline=baseline,
                drop_pct=0.0,
                alert_type="floor_breach",
                key=key,
                trace_id=trace_id,
            )

        # Check 2: >10% drop from baseline
        if baseline > 0 and current > 0:
            drop_pct = (baseline - current) / baseline * 100
            if drop_pct > DROP_PCT_THRESHOLD:
                return self._fire_alert(
                    agent_name=agent_name,
                    dimension=tracker.dimension,
                    current=current,
                    baseline=baseline,
                    drop_pct=drop_pct,
                    alert_type="degradation",
                    key=key,
                    trace_id=trace_id,
                )

        return None

    def _fire_alert(
        self,
        agent_name: str,
        dimension: str,
        current: float,
        baseline: float,
        drop_pct: float,
        alert_type: str,
        key: str,
        trace_id: str,
    ) -> EvalAlert:
        """Create and record an alert."""
        self._alert_counter += 1
        alert = EvalAlert(
            alert_id=f"eval-alert-{self._alert_counter}",
            timestamp=time.time(),
            agent_name=agent_name,
            dimension=dimension,
            current_score=current,
            baseline_score=baseline,
            drop_pct=drop_pct,
            alert_type=alert_type,
            sample_trace_ids=[trace_id] if trace_id else [],
        )

        self._alerts.append(alert)
        self._last_alert_time[key] = time.time()

        # Keep alert list bounded
        if len(self._alerts) > 500:
            self._alerts = self._alerts[-500:]

        logger.warning(
            "EVAL ALERT: %s — %s:%s current=%.1f baseline=%.1f drop=%.1f%%",
            alert_type, agent_name, dimension, current, baseline, drop_pct,
        )

        return alert
