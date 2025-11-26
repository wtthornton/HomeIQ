"""Database package"""

from .crud import (
    delete_old_training_runs,
    delete_training_run,
    can_trigger_manual_refresh,
    create_training_run,
    delete_old_patterns,
    get_active_training_run,
    get_latest_analysis_run,
    get_pattern_stats,
    get_patterns,
    get_suggestions,
    get_suggestions_with_home_type,
    get_system_settings,
    list_training_runs,
    record_analysis_run,
    record_manual_refresh,
    store_feedback,
    store_patterns,
    store_suggestion,
    update_system_settings,
    update_training_run,
)
from .models import (
    Base,
    Pattern,
    Suggestion,
    SystemSettings,
    TrainingRun,
    UserFeedback,
    get_db,
    init_db,
)

__all__ = [
    'Base', 'Pattern', 'Suggestion', 'UserFeedback', 'SystemSettings', 'TrainingRun', 'init_db', 'get_db',
    'store_patterns', 'get_patterns', 'delete_old_patterns', 'get_pattern_stats',
    'store_suggestion', 'get_suggestions', 'get_suggestions_with_home_type', 'store_feedback',
    'can_trigger_manual_refresh', 'record_manual_refresh',
    'record_analysis_run', 'get_latest_analysis_run',
    'get_system_settings', 'update_system_settings',
    'get_active_training_run', 'create_training_run', 'update_training_run', 'list_training_runs',
    'delete_training_run', 'delete_old_training_runs'
]

