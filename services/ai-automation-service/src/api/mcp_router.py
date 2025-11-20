"""
MCP tool endpoints for AI Automation Service.
These endpoints are called by code executed in the ai-code-executor sandbox.
"""

import logging
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp/tools", tags=["mcp"])

# Import pattern detection dependencies
from ..clients.data_api_client import DataAPIClient
from ..config import settings
from ..database import get_db
from ..pattern_analyzer.co_occurrence import CoOccurrencePatternDetector
from ..pattern_analyzer.time_of_day import TimeOfDayPatternDetector

# Initialize clients
data_api_client = DataAPIClient(base_url=settings.data_api_url)


def parse_relative_time(time_str: str, base_time: datetime = None) -> datetime:
    """
    Parse relative time strings like '-7d', '-24h', 'now' to datetime objects.

    Args:
        time_str: Time string (e.g., '-7d', '-24h', '-30m', 'now')
        base_time: Base datetime (defaults to now)

    Returns:
        datetime object
    """
    if base_time is None:
        base_time = datetime.now(timezone.utc)

    if time_str.lower() == 'now':
        return base_time

    # Parse relative time (e.g., '-7d', '-24h', '-30m')
    match = re.match(r'^(-?\d+)([dhm])$', time_str.lower())
    if match:
        value = int(match.group(1))
        unit = match.group(2)

        if unit == 'd':
            return base_time + timedelta(days=value)
        elif unit == 'h':
            return base_time + timedelta(hours=value)
        elif unit == 'm':
            return base_time + timedelta(minutes=value)

    # Try parsing as ISO format
    try:
        return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError(f"Invalid time format: {time_str}. Use '-7d', '-24h', 'now', or ISO format.")


class DetectPatternsRequest(BaseModel):
    """Request for pattern detection"""
    start_time: str
    end_time: str
    pattern_types: list[str] | None = ["time-based", "co-occurrence"]


@router.post("/detect_patterns")
async def detect_patterns(
    request: DetectPatternsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    MCP Tool: Detect automation patterns.

    Called from AI-generated code like:
    ```python
    import automation
    patterns = await automation.detect_patterns(
        start_time="-7d",
        end_time="now",
        pattern_types=["time-based"]
    )
    ```

    Args:
        request: Pattern detection request with time range and pattern types

    Returns:
        Dictionary with detected patterns summary
    """
    try:
        logger.info(
            f"MCP detect_patterns: {request.start_time} to {request.end_time}, "
            f"types={request.pattern_types}"
        )

        # Parse time strings
        end_dt = parse_relative_time(request.end_time)
        start_dt = parse_relative_time(request.start_time, end_dt)

        # Calculate days for context
        days = (end_dt - start_dt).days
        if days < 1:
            days = 1

        logger.info(f"Analyzing {days} days of data: {start_dt} to {end_dt}")

        # Fetch historical events
        events_df = await data_api_client.fetch_events(
            start_time=start_dt,
            end_time=end_dt,
            limit=10000
        )

        if events_df.empty:
            return {
                "success": True,
                "patterns": [],
                "message": "No events found for the specified time range",
                "events_analyzed": 0
            }

        # Ensure required columns
        if 'entity_id' in events_df.columns and 'device_id' not in events_df.columns:
            events_df['device_id'] = events_df['entity_id']

        all_patterns = []

        # Detect time-based patterns
        if "time-based" in request.pattern_types:
            logger.info("Detecting time-based patterns")
            time_detector = TimeOfDayPatternDetector(
                min_occurrences=settings.time_of_day_min_occurrences,
                min_confidence=settings.time_of_day_base_confidence,
                domain_occurrence_overrides=dict(settings.time_of_day_occurrence_overrides),
                domain_confidence_overrides=dict(settings.time_of_day_confidence_overrides)
            )
            time_patterns = time_detector.detect_patterns(events_df)

            # Convert to MCP-friendly format
            for pattern in time_patterns:
                all_patterns.append({
                    "type": "time-based",
                    "device_id": pattern.get("device_id"),
                    "pattern": pattern.get("pattern", ""),
                    "confidence": pattern.get("confidence", 0.0),
                    "occurrences": pattern.get("occurrences", 0),
                    "time_window": pattern.get("time_window", "")
                })

        # Detect co-occurrence patterns
        if "co-occurrence" in request.pattern_types:
            logger.info("Detecting co-occurrence patterns")
            cooccur_detector = CoOccurrencePatternDetector(
                window_minutes=5,
                min_support=settings.co_occurrence_min_support,
                min_confidence=settings.co_occurrence_base_confidence,
                domain_support_overrides=dict(settings.co_occurrence_support_overrides),
                domain_confidence_overrides=dict(settings.co_occurrence_confidence_overrides)
            )
            cooccur_patterns = cooccur_detector.detect_patterns(events_df)

            # Convert to MCP-friendly format
            for pattern in cooccur_patterns:
                all_patterns.append({
                    "type": "co-occurrence",
                    "trigger_device": pattern.get("trigger_device"),
                    "action_device": pattern.get("action_device"),
                    "confidence": pattern.get("confidence", 0.0),
                    "support": pattern.get("support", 0),
                    "pattern": pattern.get("pattern", "")
                })

        logger.info(f"✅ Detected {len(all_patterns)} total patterns")

        return {
            "success": True,
            "patterns": all_patterns,
            "summary": {
                "total_patterns": len(all_patterns),
                "time_based": len([p for p in all_patterns if p["type"] == "time-based"]),
                "co_occurrence": len([p for p in all_patterns if p["type"] == "co-occurrence"]),
                "events_analyzed": len(events_df),
                "unique_devices": int(events_df['device_id'].nunique()),
                "time_range_days": days
            }
        }

    except Exception as e:
        logger.error(f"MCP tool error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
