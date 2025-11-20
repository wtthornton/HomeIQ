"""
LangChain prototype for orchestrating pattern detectors.

The scheduler can route selected detectors (time-of-day, co-occurrence) through
this chain to illustrate how LangChain's runnable pipeline coordinates
sequential steps while sharing intermediate context.
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableLambda, RunnablePassthrough


class PatternChainResult(dict[str, Any]):
    """Typed alias to make intent explicit."""


def _build_time_of_day_step(tod_detector):
    async def _step(inputs: dict[str, Any]) -> dict[str, Any]:
        events_df = inputs["events_df"]
        last_update = inputs.get("last_update")
        incremental = inputs.get("incremental", False)

        if incremental and last_update and hasattr(tod_detector, "incremental_update"):
            patterns = tod_detector.incremental_update(events_df, last_update)
        else:
            patterns = tod_detector.detect_patterns(events_df)

        return {
            **inputs,
            "time_of_day_patterns": patterns,
            "last_update": inputs.get("current_run_time"),
        }

    return RunnableLambda(_step)


def _build_co_occurrence_step(co_detector):
    async def _step(inputs: dict[str, Any]) -> dict[str, Any]:
        events_df = inputs["events_df"]
        last_update = inputs.get("last_update")
        incremental = inputs.get("incremental", False)

        if incremental and last_update and hasattr(co_detector, "incremental_update"):
            patterns = co_detector.incremental_update(events_df, last_update)
        else:
            if len(events_df) > 10000 and hasattr(co_detector, "detect_patterns_optimized"):
                patterns = co_detector.detect_patterns_optimized(events_df)
            else:
                patterns = co_detector.detect_patterns(events_df)

        existing = inputs.get("time_of_day_patterns", [])
        return {
            **inputs,
            "time_of_day_patterns": existing,
            "co_occurrence_patterns": patterns,
        }

    return RunnableLambda(_step)


def build_pattern_detection_chain(
    *,
    tod_detector,
    co_detector,
) -> RunnablePassthrough:
    """
    Compose a LangChain runnable that sequentially executes the core detectors.

    The result dictionary includes both detector outputs alongside the original
    inputs so downstream code can continue with additional detectors.
    """

    return (
        RunnablePassthrough()
        | _build_time_of_day_step(tod_detector)
        | _build_co_occurrence_step(co_detector)
    )


