"""
Database models for Pattern Service

Epic 39, Story 39.5: Pattern Service Foundation
Note: These models reference tables in the shared database.
The models are defined here for type checking and ORM usage,
but the actual tables are managed by ai-automation-service.
"""

from sqlalchemy.ext.declarative import declarative_base

# Use the same Base as the main service for shared database
Base = declarative_base()

# Note: Pattern and SynergyOpportunity models are defined in
# ai-automation-service/src/database/models.py
# We import them here for use in this service, or we can redefine
# them if needed for type checking.

# For now, we'll import from the main service's models when needed
# This allows us to use the same database schema

