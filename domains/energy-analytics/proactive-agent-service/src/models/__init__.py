"""Database models for Proactive Agent Service.

Lazy imports: submodules use ``from ..database import Base`` which only
resolves inside the container where the full package tree exists.
Guard so integration tests importing sibling models don't break.
"""

try:
    from .scheduled_task import ScheduledTask, TaskExecution
    from .suggestion import (
        InvalidReportReason,
        InvalidSuggestionReport,
        Suggestion,
        SuggestionEngagement,
        SuggestionEngagementEvent,
    )
except ImportError:
    pass

__all__ = [
    "InvalidReportReason",
    "InvalidSuggestionReport",
    "ScheduledTask",
    "Suggestion",
    "SuggestionEngagement",
    "SuggestionEngagementEvent",
    "TaskExecution",
]
