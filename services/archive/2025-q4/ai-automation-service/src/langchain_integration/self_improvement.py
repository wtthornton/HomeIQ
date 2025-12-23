"""
LangChain-assisted self-improvement pilot.

Generates a weekly report summarising Ask-AI performance metrics and suggested
prompt adjustments. The recommendations are formatted through LangChain prompt
templates rather than executing automatically; humans must review the report
before applying changes.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from sqlalchemy import select

from ..database.models import AskAIQuery


async def _collect_metrics(db_session_factory) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "total_queries": 0,
        "total_suggestions": 0,
        "accepted_suggestions": 0,
        "needs_review": 0,
        "average_confidence": None,
        "sample_queries": [],
    }

    try:
        async with db_session_factory() as session:
            result = await session.execute(
                select(AskAIQuery).order_by(AskAIQuery.created_at.desc()).limit(20)
            )
            queries: list[AskAIQuery] = result.scalars().all()
    except Exception:
        # Database may not be initialised in development environments.
        return metrics

    metrics["total_queries"] = len(queries)
    confidence_values: list[float] = []

    for query in queries:
        suggestions = query.suggestions or []
        metrics["total_suggestions"] += len(suggestions)

        for suggestion in suggestions:
            status = suggestion.get("status", "unknown")
            if status in {"approved", "deployed"}:
                metrics["accepted_suggestions"] += 1
            if status in {"needs_review", "blocked"}:
                metrics["needs_review"] += 1
            confidence = suggestion.get("confidence")
            if isinstance(confidence, (float, int)):
                confidence_values.append(float(confidence))

        if query.original_query and len(metrics["sample_queries"]) < 5:
            metrics["sample_queries"].append(query.original_query)

    if confidence_values:
        metrics["average_confidence"] = round(mean(confidence_values), 3)

    return metrics


def _derive_recommendations(metrics: dict[str, Any]) -> list[str]:
    recs: list[str] = []
    total = metrics.get("total_suggestions", 0) or 1  # Avoid division by zero
    accepted = metrics.get("accepted_suggestions", 0)
    needs_review = metrics.get("needs_review", 0)
    acceptance_rate = accepted / total
    review_rate = needs_review / total
    avg_confidence = metrics.get("average_confidence")

    if acceptance_rate < 0.4:
        recs.append("Decrease creative temperature by 0.1 to favour conservative suggestions.")
    elif acceptance_rate > 0.75:
        recs.append("Experiment with higher creative temperature (increase by 0.05) to diversify ideas.")

    if review_rate > 0.2:
        recs.append("Add stricter guardrail prompts emphasising device validation.")

    if avg_confidence is not None and avg_confidence < 0.7:
        recs.append("Review entity enrichment context; confidence indicates missing device metadata.")

    if not recs:
        recs.append("Maintain current prompt settings; metrics fall within healthy thresholds.")

    return recs


def _build_plan_text(metrics: dict[str, Any], recommendations: list[str]) -> str:
    chat_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(
                "You are documenting a weekly Ask-AI prompt tuning review. Do not apply changes automatically."
            ),
            HumanMessagePromptTemplate.from_template(
                """Metrics Summary:
{metrics_json}

Recommended Actions:
- {recommendations}

Next Steps:
1. Present this report to the HomeIQ maintainer.
2. Apply approved changes manually via configuration or prompt files.
3. Record decision outcome in implementation notes.
"""
            ),
        ]
    )

    formatted = chat_prompt.format_prompt(
        metrics_json=json.dumps(metrics, indent=2),
        recommendations="\n- ".join(recommendations),
    )

    return "\n\n".join(message.content for message in formatted.to_messages())


async def generate_prompt_tuning_report(db_session_factory) -> dict[str, Any]:
    """
    Build the weekly self-improvement report without mutating system state.
    """
    metrics = await _collect_metrics(db_session_factory)
    recommendations = _derive_recommendations(metrics)
    plan_text = _build_plan_text(metrics, recommendations)

    return {
        "metrics": metrics,
        "recommendations": recommendations,
        "plan_text": plan_text,
    }


def write_report_to_markdown(report: dict[str, Any], output_path: Path) -> None:
    """
    Persist report to markdown so humans can review and approve changes.
    """
    lines = [
        "# Ask-AI Prompt Tuning Report",
        "",
        f"Generated: {report.get('generated_at', 'manual run')}",
        "",
        "## Metrics",
        "```json",
        json.dumps(report.get("metrics", {}), indent=2),
        "```",
        "",
        "## Recommendations",
        *(f"- {item}" for item in report.get("recommendations", [])),
        "",
        "## Plan Text",
        report.get("plan_text", ""),
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


