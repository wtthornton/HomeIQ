"""
Agent Evaluation Framework — Scoring Engine

Aggregates results from all evaluators into a Summary Matrix with
threshold-based alerting.  Supports single-session and batch scoring.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone

from .base_evaluator import BaseEvaluator
from .models import (
    Alert,
    BatchReport,
    EvalLevel,
    EvaluationReport,
    EvaluationResult,
    LevelSummary,
    MetricResult,
    SessionTrace,
    SummaryMatrix,
)

logger = logging.getLogger(__name__)


class ScoringEngine:
    """
    Runs evaluators against sessions and aggregates into reports.

    Usage::

        engine = ScoringEngine(thresholds={"correctness": 0.8})
        report = await engine.score(session, evaluators)
        print(report.to_markdown())
    """

    def __init__(self, thresholds: dict[str, float] | None = None):
        self.thresholds: dict[str, float] = thresholds or {}

    async def score(
        self,
        session: SessionTrace,
        evaluators: list[BaseEvaluator],
    ) -> EvaluationReport:
        """Run all evaluators on a single session and build a report."""
        results: list[EvaluationResult] = []

        for evaluator in evaluators:
            try:
                result = await evaluator.evaluate(session)
                results.append(result)
            except Exception:
                logger.exception("Evaluator %s failed", evaluator.name)
                results.append(
                    EvaluationResult(
                        evaluator_name=evaluator.name,
                        level=evaluator.level,
                        score=0.0,
                        label="ERROR",
                        explanation="Evaluator raised an exception",
                        passed=False,
                    )
                )

        matrix = self._build_matrix(results)

        return EvaluationReport(
            session_id=session.session_id,
            agent_name=session.agent_name,
            timestamp=datetime.now(timezone.utc),
            results=results,
            summary_matrix=matrix,
        )

    async def score_batch(
        self,
        sessions: list[SessionTrace],
        evaluators: list[BaseEvaluator],
    ) -> BatchReport:
        """Run evaluators on multiple sessions and build an aggregate report."""
        reports: list[EvaluationReport] = []
        for session in sessions:
            report = await self.score(session, evaluators)
            reports.append(report)

        aggregate = self._aggregate_scores(reports)
        alerts = self._check_thresholds(aggregate, reports)

        total_evals = sum(len(r.results) for r in reports)
        agent_name = sessions[0].agent_name if sessions else ""

        return BatchReport(
            agent_name=agent_name,
            timestamp=datetime.now(timezone.utc),
            sessions_evaluated=len(sessions),
            total_evaluations=total_evals,
            reports=reports,
            aggregate_scores=aggregate,
            alerts=alerts,
        )

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _build_matrix(results: list[EvaluationResult]) -> SummaryMatrix:
        """Group results by level and metric into a SummaryMatrix."""
        level_metrics: dict[EvalLevel, dict[str, list[EvaluationResult]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for r in results:
            level_metrics[r.level][r.evaluator_name].append(r)

        levels: dict[EvalLevel, LevelSummary] = {}
        for level, metrics in level_metrics.items():
            metric_results: dict[str, MetricResult] = {}
            for metric_name, evals in metrics.items():
                avg_score = sum(e.score for e in evals) / len(evals)
                all_passed = all(e.passed for e in evals)
                # Use the label from the last eval (most recent)
                label = evals[-1].label if evals else ""
                metric_results[metric_name] = MetricResult(
                    score=round(avg_score, 4),
                    label=label,
                    evaluations_count=len(evals),
                    passed=all_passed,
                )
            levels[level] = LevelSummary(metrics=metric_results)

        return SummaryMatrix(levels=levels)

    @staticmethod
    def _aggregate_scores(
        reports: list[EvaluationReport],
    ) -> dict[str, float]:
        """Compute average scores per metric across all reports."""
        metric_scores: dict[str, list[float]] = defaultdict(list)
        for report in reports:
            for result in report.results:
                metric_scores[result.evaluator_name].append(result.score)

        return {
            name: round(sum(scores) / len(scores), 4)
            for name, scores in metric_scores.items()
        }

    def _check_thresholds(
        self,
        aggregate: dict[str, float],
        reports: list[EvaluationReport],
    ) -> list[Alert]:
        """Check aggregate scores against configured thresholds."""
        alerts: list[Alert] = []
        for metric, threshold in self.thresholds.items():
            actual = aggregate.get(metric)
            if actual is not None and actual < threshold:
                # Find the level from any report result
                level = EvalLevel.QUALITY
                for report in reports:
                    for result in report.results:
                        if result.evaluator_name == metric:
                            level = result.level
                            break

                priority = "critical" if actual < threshold * 0.5 else "warning"
                alerts.append(
                    Alert(
                        level=level,
                        metric=metric,
                        threshold=threshold,
                        actual=actual,
                        priority=priority,
                    )
                )

        return alerts
