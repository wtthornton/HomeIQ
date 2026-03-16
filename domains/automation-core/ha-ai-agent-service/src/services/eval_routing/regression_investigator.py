"""
Automated Regression Investigation (Epic 69, Story 69.5).

When an eval alert fires, collects investigation context:
- 5 lowest-scoring traces from the alert window
- Common patterns in failing traces
- Model/routing changes in the alert window
Packages as an investigation report.
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class InvestigationReport:
    """Packaged investigation report for an eval alert."""

    alert_id: str
    generated_at: float
    agent_name: str
    dimension: str
    lowest_traces: list[dict[str, Any]] = field(default_factory=list)
    common_patterns: list[dict[str, Any]] = field(default_factory=list)
    routing_changes: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "generated_at": self.generated_at,
            "agent_name": self.agent_name,
            "dimension": self.dimension,
            "lowest_traces": self.lowest_traces,
            "common_patterns": self.common_patterns,
            "routing_changes": self.routing_changes,
            "summary": self.summary,
        }


@dataclass
class TraceRecord:
    """A simplified trace record for investigation."""

    trace_id: str
    timestamp: float
    score: float
    model: str
    complexity_level: str
    entity_domains: list[str] = field(default_factory=list)
    intent_category: str = ""
    error_type: str = ""


class RegressionInvestigator:
    """Investigates eval degradation by analyzing trace patterns."""

    def __init__(self):
        self._traces: list[TraceRecord] = []
        self._reports: dict[str, InvestigationReport] = {}
        self._max_traces = 5000

    def record_trace(self, trace: TraceRecord) -> None:
        """Record a trace for future investigation."""
        self._traces.append(trace)
        if len(self._traces) > self._max_traces:
            self._traces = self._traces[-self._max_traces:]

    def investigate(
        self,
        alert_id: str,
        agent_name: str,
        dimension: str,
        window_hours: int = 24,
        routing_decisions: list[dict[str, Any]] | None = None,
    ) -> InvestigationReport:
        """Generate an investigation report for an eval alert.

        Args:
            alert_id: The alert that triggered this investigation.
            agent_name: Agent being investigated.
            dimension: Eval dimension that degraded.
            window_hours: Time window to analyze.
            routing_decisions: Recent routing decisions for correlation.

        Returns:
            InvestigationReport with findings.
        """
        cutoff = time.time() - window_hours * 3600
        window_traces = [
            t for t in self._traces
            if t.timestamp > cutoff
        ]

        # 1. Find 5 lowest-scoring traces
        sorted_traces = sorted(window_traces, key=lambda t: t.score)
        lowest = sorted_traces[:5]
        lowest_dicts = [
            {
                "trace_id": t.trace_id,
                "score": round(t.score, 1),
                "model": t.model,
                "complexity": t.complexity_level,
                "entity_domains": t.entity_domains,
                "intent": t.intent_category,
                "error_type": t.error_type,
            }
            for t in lowest
        ]

        # 2. Find common patterns in failing traces (score < 70)
        failing = [t for t in window_traces if t.score < 70]
        patterns = self._find_patterns(failing)

        # 3. Routing changes in the window
        routing_changes = []
        if routing_decisions:
            for rd in routing_decisions:
                ts = rd.get("timestamp", 0)
                if ts > cutoff and rd.get("overridden"):
                    routing_changes.append({
                        "timestamp": ts,
                        "model": rd.get("chosen_model"),
                        "reason": rd.get("override_reason"),
                    })

        # Generate summary
        summary_parts = []
        if lowest:
            summary_parts.append(
                f"Lowest score in window: {lowest[0].score:.1f} (trace {lowest[0].trace_id})"
            )
        if patterns:
            top_pattern = patterns[0]
            summary_parts.append(
                f"Most common pattern: {top_pattern['pattern']} ({top_pattern['count']} occurrences)"
            )
        if routing_changes:
            summary_parts.append(
                f"{len(routing_changes)} routing overrides in alert window"
            )
        if failing:
            summary_parts.append(
                f"{len(failing)} of {len(window_traces)} traces scored below 70"
            )

        report = InvestigationReport(
            alert_id=alert_id,
            generated_at=time.time(),
            agent_name=agent_name,
            dimension=dimension,
            lowest_traces=lowest_dicts,
            common_patterns=patterns,
            routing_changes=routing_changes,
            summary=". ".join(summary_parts) if summary_parts else "No significant patterns found.",
        )

        self._reports[alert_id] = report
        return report

    def get_report(self, alert_id: str) -> dict[str, Any] | None:
        """Retrieve a previously generated investigation report."""
        report = self._reports.get(alert_id)
        return report.to_dict() if report else None

    def _find_patterns(self, traces: list[TraceRecord]) -> list[dict[str, Any]]:
        """Find common patterns across failing traces."""
        if not traces:
            return []

        patterns: list[dict[str, Any]] = []

        # Pattern 1: Common entity domains
        domain_counter: Counter[str] = Counter()
        for t in traces:
            for domain in t.entity_domains:
                domain_counter[domain] += 1

        for domain, count in domain_counter.most_common(3):
            if count >= 2:
                patterns.append({
                    "pattern": f"entity_domain:{domain}",
                    "count": count,
                    "description": f"Failures involving {domain} entities",
                })

        # Pattern 2: Common intent categories
        intent_counter: Counter[str] = Counter()
        for t in traces:
            if t.intent_category:
                intent_counter[t.intent_category] += 1

        for intent, count in intent_counter.most_common(3):
            if count >= 2:
                patterns.append({
                    "pattern": f"intent:{intent}",
                    "count": count,
                    "description": f"Failures with {intent} intent",
                })

        # Pattern 3: Common error types
        error_counter: Counter[str] = Counter()
        for t in traces:
            if t.error_type:
                error_counter[t.error_type] += 1

        for error, count in error_counter.most_common(3):
            if count >= 2:
                patterns.append({
                    "pattern": f"error:{error}",
                    "count": count,
                    "description": f"Error type: {error}",
                })

        # Pattern 4: Model distribution
        model_counter: Counter[str] = Counter()
        for t in traces:
            model_counter[t.model] += 1

        for model, count in model_counter.most_common(2):
            pct = count / len(traces) * 100
            if pct >= 60:
                patterns.append({
                    "pattern": f"model:{model}",
                    "count": count,
                    "description": f"{pct:.0f}% of failures on {model}",
                })

        return sorted(patterns, key=lambda p: p["count"], reverse=True)
