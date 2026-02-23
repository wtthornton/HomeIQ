"""
Agent Evaluation Framework — Data Models

SessionTrace and EvaluationResult models that form the foundation
for the entire evaluation pipeline.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EvalLevel(str, Enum):
    """Five-level evaluation pyramid."""

    OUTCOME = "L1_OUTCOME"
    PATH = "L2_PATH"
    DETAILS = "L3_DETAILS"
    QUALITY = "L4_QUALITY"
    SAFETY = "L5_SAFETY"


class EvalScope(str, Enum):
    """Scope at which an evaluator operates."""

    SESSION = "session"
    TOOL_CALL = "tool_call"
    RESPONSE = "response"


# ---------------------------------------------------------------------------
# SessionTrace sub-models
# ---------------------------------------------------------------------------


class UserMessage(BaseModel):
    """A single user message within a session."""

    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    turn_index: int = 0


class ToolCall(BaseModel):
    """A single tool invocation captured during a session."""

    tool_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    sequence_index: int = 0
    turn_index: int = 0
    latency_ms: float | None = None


class AgentResponse(BaseModel):
    """A single agent response within a session."""

    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    turn_index: int = 0
    tool_calls_in_turn: list[ToolCall] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# SessionTrace (top-level)
# ---------------------------------------------------------------------------


class SessionTrace(BaseModel):
    """
    Complete trace of an agent session.

    Captures user messages, agent responses, tool calls, and metadata
    in a standardized format consumed by all evaluators.
    """

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model: str = ""
    temperature: float | None = None

    user_messages: list[UserMessage] = Field(default_factory=list)
    agent_responses: list[AgentResponse] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionTrace:
        """Deserialize from a plain dict."""
        return cls.model_validate(data)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (JSON-safe)."""
        return self.model_dump(mode="json")


# ---------------------------------------------------------------------------
# EvaluationResult
# ---------------------------------------------------------------------------


class EvaluationResult(BaseModel):
    """Result produced by a single evaluator for a single session."""

    evaluator_name: str
    level: EvalLevel
    score: float = Field(ge=0.0, le=1.0)
    label: str = ""
    explanation: str = ""
    passed: bool = True


# ---------------------------------------------------------------------------
# Scoring / Summary models
# ---------------------------------------------------------------------------


class MetricResult(BaseModel):
    """Aggregated result for a single metric across evaluations."""

    score: float = Field(ge=0.0, le=1.0)
    label: str = ""
    evaluations_count: int = 0
    passed: bool = True


class LevelSummary(BaseModel):
    """Summary for a single evaluation level."""

    metrics: dict[str, MetricResult] = Field(default_factory=dict)


class SummaryMatrix(BaseModel):
    """5-level summary matrix matching the Tango format."""

    levels: dict[EvalLevel, LevelSummary] = Field(default_factory=dict)


class Alert(BaseModel):
    """Threshold violation alert."""

    level: EvalLevel
    metric: str
    threshold: float
    actual: float
    priority: str = "warning"


class EvalAlert(BaseModel):
    """
    Lifecycle-managed threshold violation alert.

    Extends the basic Alert model with identity, status tracking,
    and acknowledgement support for the AlertEngine.
    """

    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = ""
    evaluator_name: str = ""
    level: EvalLevel = EvalLevel.QUALITY
    metric: str = ""
    threshold: float = 0.0
    actual_score: float = 0.0
    priority: str = "warning"  # "critical" | "warning"
    status: str = "active"  # "active" | "acknowledged" | "resolved"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_by: str | None = None
    note: str | None = None


class EvaluationReport(BaseModel):
    """Full evaluation report for a single session."""

    session_id: str = ""
    agent_name: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    results: list[EvaluationResult] = Field(default_factory=list)
    summary_matrix: SummaryMatrix = Field(default_factory=SummaryMatrix)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_markdown(self) -> str:
        """Render as a markdown Summary Matrix."""
        lines = [f"# Evaluation Report — {self.agent_name}", ""]
        lines.append(f"**Session:** {self.session_id}")
        lines.append(f"**Timestamp:** {self.timestamp.isoformat()}")
        lines.append("")

        lines.append("| Level | Metric | Score | Label | Passed |")
        lines.append("|-------|--------|-------|-------|--------|")

        for level in EvalLevel:
            level_summary = self.summary_matrix.levels.get(level)
            if not level_summary:
                continue
            for metric_name, metric in level_summary.metrics.items():
                passed_icon = "PASS" if metric.passed else "FAIL"
                lines.append(
                    f"| {level.value} | {metric_name} | {metric.score:.2f} | "
                    f"{metric.label} | {passed_icon} |"
                )

        return "\n".join(lines)


class BatchReport(BaseModel):
    """Evaluation report for a batch of sessions."""

    agent_name: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sessions_evaluated: int = 0
    total_evaluations: int = 0
    reports: list[EvaluationReport] = Field(default_factory=list)
    aggregate_scores: dict[str, float] = Field(default_factory=dict)
    alerts: list[Alert] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_markdown(self) -> str:
        lines = [f"# Batch Evaluation Report — {self.agent_name}", ""]
        lines.append(f"**Sessions:** {self.sessions_evaluated}")
        lines.append(f"**Total Evaluations:** {self.total_evaluations}")
        lines.append("")

        if self.aggregate_scores:
            lines.append("## Aggregate Scores")
            lines.append("| Metric | Score |")
            lines.append("|--------|-------|")
            for metric, score in sorted(self.aggregate_scores.items()):
                lines.append(f"| {metric} | {score:.2f} |")
            lines.append("")

        if self.alerts:
            lines.append("## Alerts")
            for alert in self.alerts:
                lines.append(
                    f"- **{alert.priority.upper()}** [{alert.level.value}] "
                    f"{alert.metric}: {alert.actual:.2f} < {alert.threshold:.2f}"
                )

        return "\n".join(lines)
