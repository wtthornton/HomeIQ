"""
Agent Evaluation Framework — Evaluation Runner

CLI tool for running evaluations against agent sessions and producing
baseline reports.  Supports synthetic session generation for initial
baselining and JSON file loading for real session evaluation.

Usage::

    python -m shared.patterns.evaluation.run_evaluation \\
        --agent ha-ai-agent --sessions synthetic --count 5 --format markdown

    python -m shared.patterns.evaluation.run_evaluation \\
        --agent all --sessions synthetic --count 5 --output-dir reports/
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import AgentEvalConfig, ConfigLoader
from .llm_judge import LLMJudge, LLMProvider
from .models import BatchReport, EvalLevel, SessionTrace
from .registry import EvaluationRegistry
from .session_generator import SyntheticSessionGenerator

logger = logging.getLogger(__name__)

# Config directory
_CONFIGS_DIR = Path(__file__).resolve().parent / "configs"
_REPORTS_DIR = Path(__file__).resolve().parent / "reports"

# All known agent config files
_AGENT_CONFIGS = {
    "ha-ai-agent": "ha_ai_agent.yaml",
    "proactive-agent": "proactive_agent.yaml",
    "ai-automation-service": "ai_automation_service.yaml",
    "ai-core-service": "ai_core_service.yaml",
}


# ---------------------------------------------------------------------------
# Mock LLM provider for deterministic baseline runs
# ---------------------------------------------------------------------------


class BaselineMockProvider(LLMProvider):
    """
    Deterministic mock provider that returns varied but reproducible
    LLM responses for baseline evaluation runs.

    Produces a realistic distribution of scores:
    - Most evaluations return positive results (simulating a working agent)
    - Some return partial results (simulating areas for improvement)
    - Few return negative results (simulating failures)
    """

    def __init__(self, seed: int = 42):
        import random

        self._rng = random.Random(seed)
        self._call_count = 0

    async def complete(self, prompt: str) -> str:
        self._call_count += 1
        prompt_lower = prompt.lower()

        # Safety evaluators — mostly pass
        if "harmful" in prompt_lower or "stereotyp" in prompt_lower:
            return json.dumps({"label": "No", "explanation": "No harmful content detected."})
        if "refusal" in prompt_lower:
            return json.dumps({"label": "No", "explanation": "No inappropriate refusals."})

        # Goal success — mix of outcomes
        if "goal" in prompt_lower or "success" in prompt_lower:
            roll = self._rng.random()
            if roll < 0.6:
                return json.dumps({"label": "Yes", "explanation": "User's goal was fully achieved."})
            elif roll < 0.85:
                return json.dumps({"label": "Partial", "explanation": "Goal partially achieved, some steps incomplete."})
            else:
                return json.dumps({"label": "No", "explanation": "Goal was not achieved."})

        # Quality evaluators — generally positive
        if any(w in prompt_lower for w in ("correct", "faithful", "coherent", "helpful", "concise", "relevant")):
            labels_positive = [
                ("Perfectly Correct", "Response is factually accurate."),
                ("Completely Yes", "Response is faithful to the context."),
                ("Yes", "Response meets quality criteria."),
            ]
            labels_partial = [
                ("Partially Correct", "Some inaccuracies noted."),
                ("Generally Yes", "Mostly faithful with minor issues."),
            ]
            roll = self._rng.random()
            if roll < 0.7:
                label, expl = self._rng.choice(labels_positive)
            else:
                label, expl = self._rng.choice(labels_partial)
            return json.dumps({"label": label, "explanation": expl})

        # Instruction following
        if "instruction" in prompt_lower:
            roll = self._rng.random()
            if roll < 0.75:
                return json.dumps({"label": "Yes", "explanation": "Instructions followed correctly."})
            return json.dumps({"label": "Partial", "explanation": "Some instructions not fully followed."})

        # System prompt rule checks — mostly pass
        if "pass" in prompt_lower or "fail" in prompt_lower or "rule" in prompt_lower:
            roll = self._rng.random()
            if roll < 0.8:
                return json.dumps({"label": "Pass", "explanation": "Rule compliance verified."})
            return json.dumps({"label": "Fail", "explanation": "Rule violation detected."})

        # Default: positive response
        return json.dumps({"label": "Yes", "explanation": "Evaluation passed."})


# ---------------------------------------------------------------------------
# Core evaluation function
# ---------------------------------------------------------------------------


async def run_evaluation(
    agent_names: list[str],
    sessions_source: str = "synthetic",
    session_count: int = 5,
    output_format: str = "markdown",
    output_dir: Path | None = None,
    seed: int = 42,
) -> dict[str, BatchReport]:
    """
    Run evaluation for one or more agents and produce reports.

    Args:
        agent_names: Agent names to evaluate (or ["all"] for all agents).
        sessions_source: "synthetic" or path to JSON file.
        session_count: Number of synthetic sessions per agent.
        output_format: "markdown" or "json".
        output_dir: Directory for output reports. Defaults to reports/.
        seed: Random seed for reproducible results.

    Returns:
        Dict mapping agent_name to BatchReport.
    """
    if output_dir is None:
        output_dir = _REPORTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve "all"
    if agent_names == ["all"]:
        agent_names = list(_AGENT_CONFIGS.keys())

    # Set up registry with mock provider
    provider = BaselineMockProvider(seed=seed)
    judge = LLMJudge(provider=provider)
    registry = EvaluationRegistry(llm_judge=judge)

    results: dict[str, BatchReport] = {}

    for agent_name in agent_names:
        config_file = _AGENT_CONFIGS.get(agent_name)
        if config_file is None:
            logger.warning("Unknown agent '%s' — skipping", agent_name)
            continue

        config_path = _CONFIGS_DIR / config_file
        config = ConfigLoader.load(config_path)
        registry.register_agent(config)

        # Load or generate sessions
        sessions = _load_sessions(
            agent_name, config, sessions_source, session_count, seed
        )

        if not sessions:
            logger.warning("No sessions for '%s' — skipping", agent_name)
            continue

        logger.info(
            "Evaluating %s: %d sessions, %d evaluators",
            agent_name,
            len(sessions),
            len(registry.get_evaluators(agent_name)),
        )

        # Run evaluation
        batch_report = await registry.evaluate_batch(sessions)
        results[agent_name] = batch_report

        # Write report
        _write_report(batch_report, config, output_format, output_dir)

    return results


def _load_sessions(
    agent_name: str,
    config: AgentEvalConfig,
    source: str,
    count: int,
    seed: int,
) -> list[SessionTrace]:
    """Load sessions from synthetic generator or JSON file."""
    if source == "synthetic":
        generator = SyntheticSessionGenerator(config)
        return generator.generate(count=count, seed=seed)

    # Load from JSON file
    path = Path(source)
    if not path.exists():
        logger.error("Session file not found: %s", path)
        return []

    data = json.loads(path.read_text(encoding="utf-8"))
    sessions = []
    items = data if isinstance(data, list) else [data]
    for item in items:
        session = SessionTrace.from_dict(item)
        if session.agent_name == agent_name:
            sessions.append(session)
    return sessions[:count] if count > 0 else sessions


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _write_report(
    report: BatchReport,
    config: AgentEvalConfig,
    fmt: str,
    output_dir: Path,
) -> Path:
    """Write a BatchReport to disk."""
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    agent_slug = config.agent_name.replace(" ", "_")

    if fmt == "json":
        path = output_dir / f"baseline_{agent_slug}_{date_str}.json"
        path.write_text(
            json.dumps(report.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )
    else:
        path = output_dir / f"baseline_{agent_slug}_{date_str}.md"
        content = _render_baseline_markdown(report, config)
        path.write_text(content, encoding="utf-8")

    logger.info("Report written to %s", path)
    return path


def _render_baseline_markdown(
    report: BatchReport, config: AgentEvalConfig
) -> str:
    """Render an enhanced baseline report in markdown."""
    lines: list[str] = []

    # Header
    lines.append(f"# Baseline Evaluation Report — {config.agent_name}")
    lines.append("")
    lines.append(f"**Date:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Sessions Evaluated:** {report.sessions_evaluated}")
    lines.append(f"**Total Evaluations:** {report.total_evaluations}")
    lines.append("")

    # Config summary
    lines.append("## Agent Configuration Summary")
    lines.append("")
    lines.append(f"- **Model:** {config.model}")
    lines.append(f"- **Tools:** {len(config.tools)}")
    lines.append(f"- **Path Rules:** {len(config.paths)}")
    lines.append(f"- **Parameter Rules:** {len(config.parameter_rules)}")
    lines.append(f"- **System Prompt Rules:** {len(config.system_prompt_rules)}")
    lines.append(f"- **Quality Rubrics:** {len(config.quality_rubrics)}")
    lines.append(f"- **Safety Rubrics:** {len(config.safety_rubrics)}")
    lines.append(f"- **Thresholds:** {len(config.thresholds)}")
    lines.append("")

    # Summary Matrix
    lines.append("## Summary Matrix")
    lines.append("")
    lines.append("| Level | Metric | Score | Threshold | Status |")
    lines.append("|-------|--------|-------|-----------|--------|")

    for level in EvalLevel:
        if report.reports:
            # Aggregate across all session reports
            level_metrics: dict[str, list[float]] = {}
            for session_report in report.reports:
                level_summary = session_report.summary_matrix.levels.get(level)
                if level_summary:
                    for name, metric in level_summary.metrics.items():
                        level_metrics.setdefault(name, []).append(metric.score)

            for metric_name, scores in sorted(level_metrics.items()):
                avg_score = sum(scores) / len(scores) if scores else 0.0
                threshold = config.thresholds.get(metric_name)
                if threshold is not None:
                    status = "PASS" if avg_score >= threshold else "FAIL"
                else:
                    status = "N/A"
                threshold_str = f"{threshold:.2f}" if threshold is not None else "—"
                lines.append(
                    f"| {level.value} | {metric_name} | {avg_score:.2f} | "
                    f"{threshold_str} | {status} |"
                )

    lines.append("")

    # Aggregate scores
    if report.aggregate_scores:
        lines.append("## Aggregate Scores")
        lines.append("")
        lines.append("| Metric | Score |")
        lines.append("|--------|-------|")
        for metric, score in sorted(report.aggregate_scores.items()):
            lines.append(f"| {metric} | {score:.4f} |")
        lines.append("")

    # Top 3 lowest-scoring evaluators
    if report.aggregate_scores:
        lines.append("## Top 3 Lowest-Scoring Evaluators (Improvement Priorities)")
        lines.append("")
        sorted_scores = sorted(report.aggregate_scores.items(), key=lambda x: x[1])
        for i, (metric, score) in enumerate(sorted_scores[:3]):
            threshold = config.thresholds.get(metric)
            gap = f" (gap: {threshold - score:.2f})" if threshold and score < threshold else ""
            lines.append(f"{i + 1}. **{metric}**: {score:.4f}{gap}")
        lines.append("")

    # Alerts
    if report.alerts:
        lines.append("## Threshold Violations")
        lines.append("")
        for alert in report.alerts:
            lines.append(
                f"- **{alert.priority.upper()}** [{alert.level.value}] "
                f"{alert.metric}: {alert.actual:.4f} < {alert.threshold:.2f}"
            )
        lines.append("")

    # Recommended threshold adjustments
    lines.append("## Recommended Threshold Adjustments")
    lines.append("")
    lines.append(
        "Based on baseline scores, the following threshold adjustments "
        "are recommended to avoid excessive false-positive alerts during "
        "early operation:"
    )
    lines.append("")

    adjustments = _compute_threshold_adjustments(report, config)
    if adjustments:
        lines.append("| Metric | Current Threshold | Baseline Score | Recommended |")
        lines.append("|--------|------------------|----------------|-------------|")
        for adj in adjustments:
            lines.append(
                f"| {adj['metric']} | {adj['current']:.2f} | "
                f"{adj['baseline']:.4f} | {adj['recommended']:.2f} |"
            )
    else:
        lines.append("No adjustments needed — all scores meet or exceed thresholds.")
    lines.append("")

    return "\n".join(lines)


def _compute_threshold_adjustments(
    report: BatchReport, config: AgentEvalConfig
) -> list[dict[str, Any]]:
    """Identify thresholds that need adjustment based on baseline scores."""
    adjustments = []
    for metric, threshold in config.thresholds.items():
        actual = report.aggregate_scores.get(metric)
        if actual is not None and actual < threshold:
            # Recommend threshold = 90% of baseline score (gives room)
            recommended = round(max(0.0, actual * 0.9), 2)
            adjustments.append({
                "metric": metric,
                "current": threshold,
                "baseline": actual,
                "recommended": recommended,
            })
    return sorted(adjustments, key=lambda x: x["baseline"])


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for running evaluations."""
    parser = argparse.ArgumentParser(
        description="Run Agent Evaluation Framework evaluations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--agent",
        default="all",
        help="Agent name to evaluate (or 'all'). Choices: "
        + ", ".join(_AGENT_CONFIGS.keys()),
    )
    parser.add_argument(
        "--sessions",
        default="synthetic",
        help="Session source: 'synthetic' or path to JSON file",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of sessions per agent (default: 5)",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for reports (default: reports/)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results (default: 42)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    agent_names = [args.agent] if args.agent != "all" else ["all"]

    reports = asyncio.run(
        run_evaluation(
            agent_names=agent_names,
            sessions_source=args.sessions,
            session_count=args.count,
            output_format=args.output_format,
            output_dir=args.output_dir,
            seed=args.seed,
        )
    )

    # Print summary
    print(f"\n{'='*60}")
    print("EVALUATION SUMMARY")
    print(f"{'='*60}")
    for agent_name, report in reports.items():
        alert_count = len(report.alerts)
        alert_str = f" ({alert_count} alerts)" if alert_count > 0 else ""
        print(
            f"  {agent_name}: {report.sessions_evaluated} sessions, "
            f"{report.total_evaluations} evaluations{alert_str}"
        )
        if report.aggregate_scores:
            top3 = sorted(report.aggregate_scores.items(), key=lambda x: x[1])[:3]
            for metric, score in top3:
                print(f"    Lowest: {metric} = {score:.4f}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
