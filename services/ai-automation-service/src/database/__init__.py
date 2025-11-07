"""Database package"""

from .models import Base, Pattern, Suggestion, UserFeedback, SystemSettings, TrainingRun, init_db, get_db
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
    get_latest_analysis_run,
    get_system_settings,
    update_system_settings,
    get_active_training_run,
    create_training_run,
    update_training_run,
    list_training_runs,
)

__all__ = [
    'Base', 'Pattern', 'Suggestion', 'UserFeedback', 'SystemSettings', 'TrainingRun', 'init_db', 'get_db',
    'store_patterns', 'get_patterns', 'delete_old_patterns', 'get_pattern_stats',
    'store_suggestion', 'get_suggestions', 'store_feedback',
    'can_trigger_manual_refresh', 'record_manual_refresh',
    'record_analysis_run', 'get_latest_analysis_run',
    'get_system_settings', 'update_system_settings',
    'get_active_training_run', 'create_training_run', 'update_training_run', 'list_training_runs'
]

