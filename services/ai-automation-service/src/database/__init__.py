"""Database package"""

from .models import Base, Pattern, Suggestion, UserFeedback, init_db, get_db
from .crud import (
    store_patterns,
    get_patterns,
    delete_old_patterns,
    get_pattern_stats,
    store_suggestion,
    get_suggestions,
    store_feedback,
    can_trigger_manual_refresh,
    record_manual_refresh,
    record_analysis_run,
    get_latest_analysis_run
)

__all__ = [
    'Base', 'Pattern', 'Suggestion', 'UserFeedback', 'init_db', 'get_db',
    'store_patterns', 'get_patterns', 'delete_old_patterns', 'get_pattern_stats',
    'store_suggestion', 'get_suggestions', 'store_feedback',
    'can_trigger_manual_refresh', 'record_manual_refresh',
    'record_analysis_run', 'get_latest_analysis_run'
]

