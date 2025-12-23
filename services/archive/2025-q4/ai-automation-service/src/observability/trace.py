"""
Decision Trace - JSON trace for every decision
"""

import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DecisionTrace:
    """
    Decision trace for automation plan decisions.
    
    Captures:
    - Prompt
    - Provider/model IDs
    - Raw LLM JSON
    - Validation results
    - Ranking features/scores
    - Final plan
    - Diff
    - Timings
    """
    trace_id: str
    timestamp: str
    prompt: str | None = None
    provider_id: str | None = None
    model_id: str | None = None
    prompt_pack_id: str | None = None
    raw_llm_json: dict[str, Any] | None = None
    validation_results: dict[str, Any] | None = None
    ranking_features: dict[str, Any] | None = None
    ranking_scores: dict[str, Any] | None = None
    final_plan: dict[str, Any] | None = None
    diff: dict[str, Any] | None = None
    timings: dict[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, default=str)


# Trace storage directory (use relative path for flexibility)
TRACE_DIR = Path("/app/data/traces")


def _ensure_trace_dir():
    """Ensure trace directory exists"""
    try:
        TRACE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"Failed to create trace directory: {e}, using fallback")
        # Fallback to current directory
        return Path("./traces")
    return TRACE_DIR


def generate_trace_id() -> str:
    """Generate unique trace ID"""
    return str(uuid.uuid4())


def write_trace(trace: DecisionTrace) -> str:
    """
    Write decision trace to disk.
    
    Args:
        trace: DecisionTrace instance
        
    Returns:
        Trace ID
    """
    try:
        trace_dir = _ensure_trace_dir()
        # Write to file
        trace_file = trace_dir / f"{trace.trace_id}.json"
        with open(trace_file, 'w') as f:
            f.write(trace.to_json())

        logger.debug(f"Trace written: {trace.trace_id}")
        return trace.trace_id
    except Exception as e:
        logger.error(f"Failed to write trace: {e}")
        return trace.trace_id  # Return trace_id even if write failed


def get_trace(trace_id: str) -> DecisionTrace | None:
    """
    Retrieve trace by ID.
    
    Args:
        trace_id: Trace ID
        
    Returns:
        DecisionTrace or None if not found
    """
    try:
        trace_dir = _ensure_trace_dir()
        trace_file = trace_dir / f"{trace_id}.json"
        if not trace_file.exists():
            return None

        with open(trace_file) as f:
            data = json.load(f)

        return DecisionTrace(**data)
    except Exception as e:
        logger.error(f"Failed to read trace {trace_id}: {e}")
        return None


def create_trace(
    prompt: str | None = None,
    provider_id: str | None = None,
    model_id: str | None = None,
    prompt_pack_id: str | None = None,
    raw_llm_json: dict[str, Any] | None = None,
    validation_results: dict[str, Any] | None = None,
    ranking_features: dict[str, Any] | None = None,
    ranking_scores: dict[str, Any] | None = None,
    final_plan: dict[str, Any] | None = None,
    diff: dict[str, Any] | None = None,
    timings: dict[str, float] | None = None
) -> DecisionTrace:
    """
    Create a new decision trace.
    
    Args:
        prompt: User prompt
        provider_id: LLM provider ID
        model_id: Model ID
        prompt_pack_id: Prompt pack ID
        raw_llm_json: Raw LLM JSON output
        validation_results: Validation results
        ranking_features: Ranking feature breakdown
        ranking_scores: Ranking scores
        final_plan: Final automation plan
        diff: Diff from original
        timings: Timing information
        
    Returns:
        DecisionTrace instance
    """
    return DecisionTrace(
        trace_id=generate_trace_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
        prompt=prompt,
        provider_id=provider_id,
        model_id=model_id,
        prompt_pack_id=prompt_pack_id,
        raw_llm_json=raw_llm_json,
        validation_results=validation_results,
        ranking_features=ranking_features,
        ranking_scores=ranking_scores,
        final_plan=final_plan,
        diff=diff,
        timings=timings
    )

