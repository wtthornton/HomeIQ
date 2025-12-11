"""
Database models for AI Automation Service

Epic 39, Story 39.10: Automation Service Foundation
Shared models with other services (Suggestion, AutomationVersion, etc.)
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Suggestion(Base):
    """Suggestion model - shared with other services"""
    __tablename__ = "suggestions"
    
    id = Column(Integer, primary_key=True, index=True)
    pattern_id = Column(Integer, nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    automation_yaml = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, approved, rejected, deployed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    automation_id = Column(String, nullable=True)  # HA automation ID after deployment
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Quality metrics
    confidence_score = Column(Float, nullable=True)
    safety_score = Column(Float, nullable=True)
    
    # User feedback
    user_feedback = Column(String, nullable=True)  # approve, reject, modify
    feedback_at = Column(DateTime(timezone=True), nullable=True)


class AutomationVersion(Base):
    """Version history for automations - enables rollback"""
    __tablename__ = "automation_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    suggestion_id = Column(Integer, ForeignKey("suggestions.id"), nullable=False)
    automation_id = Column(String, nullable=False)  # HA automation ID
    version_number = Column(Integer, nullable=False)
    automation_yaml = Column(Text, nullable=False)
    safety_score = Column(Float, nullable=True)
    deployed_at = Column(DateTime(timezone=True), server_default=func.now())
    deployed_by = Column(String, nullable=True)  # User/API key identifier
    is_active = Column(Boolean, default=True)  # Current active version
    rollback_reason = Column(Text, nullable=True)  # If rolled back, reason

