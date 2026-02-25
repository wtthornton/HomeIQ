"""
Database models for AI Query Service

Note: Query service uses shared database tables from ai-automation-service.
This file contains type hints and model references for query-related tables.
"""

from sqlalchemy.orm import DeclarativeBase

# Note: Actual models are defined in ai-automation-service/src/database/models.py
# This file provides type hints and imports for the query service.
# Base is defined here for Alembic migration support.
# Models will be added as needed when full implementation is done in Story 39.10


class Base(DeclarativeBase):
    """Base class for query service database models."""
    pass
