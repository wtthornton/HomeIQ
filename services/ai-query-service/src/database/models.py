"""
Database models for AI Query Service

Note: Query service uses shared database tables from ai-automation-service.
This file contains type hints and model references for query-related tables.
"""

# Note: Actual models are defined in ai-automation-service/src/database/models.py
# This file provides type hints and imports for the query service

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_automation_service.database.models import (
        AskAIQuery,
        ClarificationSessionDB,
        Suggestion,
    )

# Re-export for convenience (will need to import from shared location or ai-automation-service)
# For now, we'll import dynamically to avoid circular dependencies

