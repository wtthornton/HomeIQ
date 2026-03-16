"""
Cost Tracking & Reporting (Epic 69, Story 69.6).

Tracks OpenAI API costs per model per agent per day. Compares baseline
cost (all requests to expensive model) vs adaptive cost (routed).
Alerts on cost spikes (>50% above 7-day average).
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Approximate costs per 1K tokens (USD)
_MODEL_COSTS = {
    "gpt-5.2-codex": {"input": 0.010, "output": 0.030},
    "gpt-4.1-mini": {"input": 0.001, "output": 0.003},
    # Fallback for unknown models
    "default": {"input": 0.010, "output": 0.030},
}

COST_SPIKE_THRESHOLD_PCT = 50.0  # Alert if daily cost > 150% of 7-day avg


@dataclass
class UsageRecord:
    """A single API usage record."""

    timestamp: float
    model: str
    agent_id: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float


@dataclass
class DailyCostSummary:
    """Cost summary for a single day."""

    date: str  # YYYY-MM-DD
    total_cost: float = 0.0
    by_model: dict[str, float] = field(default_factory=dict)
    by_agent: dict[str, float] = field(default_factory=dict)
    request_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "total_cost_usd": round(self.total_cost, 4),
            "by_model": {k: round(v, 4) for k, v in self.by_model.items()},
            "by_agent": {k: round(v, 4) for k, v in self.by_agent.items()},
            "request_count": self.request_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
        }


class CostTracker:
    """Tracks API costs and computes savings from adaptive routing."""

    def __init__(self):
        self._records: list[UsageRecord] = []
        self._max_records = 10000
        self._daily_summaries: dict[str, DailyCostSummary] = {}

    def record_usage(
        self,
        model: str,
        agent_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Record API usage and return estimated cost.

        Returns estimated cost in USD.
        """
        cost = self._estimate_cost(model, input_tokens, output_tokens)

        record = UsageRecord(
            timestamp=time.time(),
            model=model,
            agent_id=agent_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=cost,
        )
        self._records.append(record)
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

        # Update daily summary
        date_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if date_key not in self._daily_summaries:
            self._daily_summaries[date_key] = DailyCostSummary(date=date_key)

        summary = self._daily_summaries[date_key]
        summary.total_cost += cost
        summary.by_model[model] = summary.by_model.get(model, 0.0) + cost
        summary.by_agent[agent_id] = summary.by_agent.get(agent_id, 0.0) + cost
        summary.request_count += 1
        summary.total_input_tokens += input_tokens
        summary.total_output_tokens += output_tokens

        return cost

    def get_savings_report(self) -> dict[str, Any]:
        """Compare adaptive cost vs baseline (all-primary) cost."""
        if not self._records:
            return {"savings_usd": 0.0, "savings_pct": 0.0, "total_requests": 0}

        actual_cost = sum(r.estimated_cost_usd for r in self._records)

        # Baseline: what it would cost if all requests used primary model
        primary_costs = _MODEL_COSTS.get("gpt-5.2-codex", _MODEL_COSTS["default"])
        baseline_cost = sum(
            (r.input_tokens / 1000 * primary_costs["input"])
            + (r.output_tokens / 1000 * primary_costs["output"])
            for r in self._records
        )

        savings = baseline_cost - actual_cost
        savings_pct = (savings / baseline_cost * 100) if baseline_cost > 0 else 0.0

        return {
            "actual_cost_usd": round(actual_cost, 4),
            "baseline_cost_usd": round(baseline_cost, 4),
            "savings_usd": round(savings, 4),
            "savings_pct": round(savings_pct, 1),
            "total_requests": len(self._records),
        }

    def get_daily_summaries(self, days: int = 7) -> list[dict[str, Any]]:
        """Get daily cost summaries for the last N days."""
        sorted_keys = sorted(self._daily_summaries.keys(), reverse=True)[:days]
        return [self._daily_summaries[k].to_dict() for k in sorted_keys]

    def check_cost_spike(self) -> dict[str, Any] | None:
        """Check if today's cost is spiking above 7-day average.

        Returns spike alert dict or None.
        """
        sorted_keys = sorted(self._daily_summaries.keys(), reverse=True)
        if len(sorted_keys) < 2:
            return None

        today_key = sorted_keys[0]
        today_cost = self._daily_summaries[today_key].total_cost

        # 7-day average (excluding today)
        past_keys = sorted_keys[1:8]
        if not past_keys:
            return None

        past_costs = [self._daily_summaries[k].total_cost for k in past_keys]
        avg_cost = sum(past_costs) / len(past_costs) if past_costs else 0.0

        if avg_cost <= 0:
            return None

        spike_pct = (today_cost - avg_cost) / avg_cost * 100
        if spike_pct > COST_SPIKE_THRESHOLD_PCT:
            return {
                "alert": "cost_spike",
                "today_cost_usd": round(today_cost, 4),
                "avg_7d_cost_usd": round(avg_cost, 4),
                "spike_pct": round(spike_pct, 1),
            }

        return None

    def _estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate cost in USD based on model and token counts."""
        costs = _MODEL_COSTS.get(model, _MODEL_COSTS["default"])
        return (
            (input_tokens / 1000 * costs["input"])
            + (output_tokens / 1000 * costs["output"])
        )
