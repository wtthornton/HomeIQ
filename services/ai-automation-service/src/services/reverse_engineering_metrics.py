"""
Reverse Engineering Metrics Storage and Analytics

Stores and analyzes metrics for reverse engineering value tracking.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import ReverseEngineeringMetrics
from ..llm.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


async def store_reverse_engineering_metrics(
    db_session: AsyncSession,
    suggestion_id: str,
    query_id: str,
    correction_result: Any,  # SelfCorrectionResponse
    automation_created: bool | None = None,
    automation_id: str | None = None,
    had_validation_errors: bool | None = None,
    errors_fixed_count: int = 0,
) -> ReverseEngineeringMetrics:
    """
    Store reverse engineering metrics in the database.

    Args:
        db_session: Database session
        suggestion_id: Suggestion ID
        query_id: Query ID
        correction_result: SelfCorrectionResponse object with metrics
        automation_created: Whether automation was created successfully
        automation_id: HA automation ID if created
        had_validation_errors: Whether original YAML had validation errors
        errors_fixed_count: Number of errors fixed by reverse engineering

    Returns:
        Stored ReverseEngineeringMetrics object
    """
    try:
        # Calculate estimated cost (assuming all tokens are input/output mixed)
        # For reverse engineering, we estimate 70% input, 30% output
        input_tokens = int(correction_result.total_tokens_used * 0.7)
        output_tokens = int(correction_result.total_tokens_used * 0.3)
        estimated_cost = CostTracker.calculate_cost(input_tokens, output_tokens)

        # Calculate tokens per iteration
        tokens_per_iteration = (
            correction_result.total_tokens_used / correction_result.iterations_completed
            if correction_result.iterations_completed > 0 else 0.0
        )

        # Serialize iteration history to JSON
        iteration_history_json = [
            {
                "iteration": iter_result.iteration,
                "similarity_score": iter_result.similarity_score,
                "correction_feedback": iter_result.correction_feedback,
                "improvement_actions": iter_result.improvement_actions,
            }
            for iter_result in correction_result.iteration_history
        ]

        # Create metrics record
        metrics = ReverseEngineeringMetrics(
            suggestion_id=suggestion_id,
            query_id=query_id,

            # Similarity metrics
            initial_similarity=getattr(correction_result, "initial_similarity", None),
            final_similarity=correction_result.final_similarity,
            similarity_improvement=getattr(correction_result, "similarity_improvement", None),
            improvement_percentage=getattr(correction_result, "improvement_percentage", None),

            # Performance metrics
            iterations_completed=correction_result.iterations_completed,
            max_iterations=correction_result.max_iterations,
            convergence_achieved=correction_result.convergence_achieved,
            total_processing_time_ms=getattr(correction_result, "total_processing_time_ms", None),
            time_per_iteration_ms=getattr(correction_result, "time_per_iteration_ms", None),

            # Cost metrics
            total_tokens_used=correction_result.total_tokens_used,
            estimated_cost_usd=estimated_cost,
            tokens_per_iteration=tokens_per_iteration,

            # Automation success
            automation_created=automation_created,
            automation_id=automation_id,
            had_validation_errors=had_validation_errors,
            errors_fixed_count=errors_fixed_count,

            # YAML comparison
            original_yaml=getattr(correction_result, "original_yaml", None),
            corrected_yaml=correction_result.final_yaml,
            yaml_changed=getattr(correction_result, "yaml_changed", False),

            # Iteration history
            iteration_history_json=iteration_history_json,
        )

        db_session.add(metrics)
        await db_session.commit()
        await db_session.refresh(metrics)

        logger.info(
            f"✅ Stored reverse engineering metrics: "
            f"similarity {metrics.initial_similarity:.2%} → {metrics.final_similarity:.2%}, "
            f"{metrics.iterations_completed} iterations, ${metrics.estimated_cost_usd:.4f}",
        )

        return metrics

    except Exception as e:
        logger.error(f"❌ Failed to store reverse engineering metrics: {e}", exc_info=True)
        await db_session.rollback()
        raise


async def get_reverse_engineering_analytics(
    db_session: AsyncSession,
    days: int = 30,
) -> dict[str, Any]:
    """
    Get aggregated analytics for reverse engineering metrics.

    Args:
        db_session: Database session
        days: Number of days to analyze (default: 30)

    Returns:
        Dictionary with aggregated analytics
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Query all metrics in time range
        query = select(ReverseEngineeringMetrics).where(
            ReverseEngineeringMetrics.created_at >= cutoff_date,
        )

        result = await db_session.execute(query)
        all_metrics = result.scalars().all()

        if not all_metrics:
            return {
                "total_automations": 0,
                "message": f"No metrics found in the last {days} days",
            }

        total = len(all_metrics)

        # Similarity metrics
        similarities_with_initial = [
            m for m in all_metrics if m.initial_similarity is not None and m.final_similarity is not None
        ]

        avg_initial_similarity = (
            sum(m.initial_similarity for m in similarities_with_initial) / len(similarities_with_initial)
            if similarities_with_initial else 0.0
        )
        avg_final_similarity = (
            sum(m.final_similarity for m in all_metrics) / len(all_metrics)
            if all_metrics else 0.0
        )
        avg_improvement = (
            sum(m.similarity_improvement for m in similarities_with_initial if m.similarity_improvement is not None) / len(similarities_with_initial)
            if similarities_with_initial else 0.0
        )
        avg_improvement_pct = (
            sum(m.improvement_percentage for m in similarities_with_initial if m.improvement_percentage is not None) / len(similarities_with_initial)
            if similarities_with_initial else 0.0
        )

        # Performance metrics
        avg_iterations = sum(m.iterations_completed for m in all_metrics) / total if total > 0 else 0.0
        convergence_rate = sum(1 for m in all_metrics if m.convergence_achieved) / total if total > 0 else 0.0
        avg_time_ms = (
            sum(m.total_processing_time_ms for m in all_metrics if m.total_processing_time_ms is not None) /
            len([m for m in all_metrics if m.total_processing_time_ms is not None])
            if any(m.total_processing_time_ms for m in all_metrics) else 0.0
        )

        # Cost metrics
        total_tokens = sum(m.total_tokens_used for m in all_metrics)
        total_cost = sum(m.estimated_cost_usd for m in all_metrics if m.estimated_cost_usd is not None)
        avg_cost = total_cost / total if total > 0 else 0.0
        avg_tokens_per_iteration = (
            sum(m.tokens_per_iteration for m in all_metrics if m.tokens_per_iteration is not None) /
            len([m for m in all_metrics if m.tokens_per_iteration is not None])
            if any(m.tokens_per_iteration for m in all_metrics) else 0.0
        )

        # Automation success metrics
        created_count = sum(1 for m in all_metrics if m.automation_created is True)
        created_rate = created_count / total if total > 0 else 0.0

        # Value metrics
        improved_count = sum(1 for m in similarities_with_initial if m.similarity_improvement and m.similarity_improvement > 0)
        improved_rate = improved_count / len(similarities_with_initial) if similarities_with_initial else 0.0

        significantly_improved = sum(1 for m in similarities_with_initial if m.improvement_percentage and m.improvement_percentage > 10)
        significantly_improved_rate = significantly_improved / len(similarities_with_initial) if similarities_with_initial else 0.0

        # YAML changes
        yaml_changed_count = sum(1 for m in all_metrics if m.yaml_changed is True)
        yaml_changed_rate = yaml_changed_count / total if total > 0 else 0.0

        return {
            "period_days": days,
            "total_automations": total,
            "date_range": {
                "from": cutoff_date.isoformat(),
                "to": datetime.utcnow().isoformat(),
            },

            # Similarity metrics
            "similarity": {
                "avg_initial": round(avg_initial_similarity, 4),
                "avg_final": round(avg_final_similarity, 4),
                "avg_improvement": round(avg_improvement, 4),
                "avg_improvement_percentage": round(avg_improvement_pct, 2),
                "improved_count": improved_count,
                "improved_rate": round(improved_rate, 4),
                "significantly_improved_count": significantly_improved,
                "significantly_improved_rate": round(significantly_improved_rate, 4),
            },

            # Performance metrics
            "performance": {
                "avg_iterations": round(avg_iterations, 2),
                "convergence_rate": round(convergence_rate, 4),
                "avg_processing_time_ms": round(avg_time_ms, 0),
                "avg_processing_time_seconds": round(avg_time_ms / 1000, 2),
            },

            # Cost metrics
            "cost": {
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 4),
                "avg_cost_per_automation": round(avg_cost, 4),
                "avg_tokens_per_iteration": round(avg_tokens_per_iteration, 0),
                "estimated_monthly_cost": round(avg_cost * 30, 2),  # Rough estimate
            },

            # Success metrics
            "automation_success": {
                "created_count": created_count,
                "created_rate": round(created_rate, 4),
                "yaml_changed_count": yaml_changed_count,
                "yaml_changed_rate": round(yaml_changed_rate, 4),
            },

            # Value indicators
            "value_indicators": {
                "avg_similarity_improvement": round(avg_improvement, 4),
                "percent_improved": round(improved_rate * 100, 1),
                "percent_significantly_improved": round(significantly_improved_rate * 100, 1),
                "convergence_rate": round(convergence_rate * 100, 1),
                "cost_per_improvement": round(avg_cost / max(avg_improvement, 0.01), 4) if avg_improvement > 0 else None,
            },

            # KPIs (Key Performance Indicators)
            "kpis": {
                "similarity_improvement_target": "> 10%",
                "similarity_improvement_actual": f"{avg_improvement_pct:.1f}%",
                "meets_similarity_target": avg_improvement_pct > 10,

                "convergence_rate_target": "> 70%",
                "convergence_rate_actual": f"{convergence_rate * 100:.1f}%",
                "meets_convergence_target": convergence_rate > 0.70,

                "cost_target": "< $0.10",
                "cost_actual": f"${avg_cost:.4f}",
                "meets_cost_target": avg_cost < 0.10,

                "improvement_rate_target": "> 60%",
                "improvement_rate_actual": f"{improved_rate * 100:.1f}%",
                "meets_improvement_rate_target": improved_rate > 0.60,
            },
        }

    except Exception as e:
        logger.error(f"❌ Failed to get reverse engineering analytics: {e}", exc_info=True)
        raise

