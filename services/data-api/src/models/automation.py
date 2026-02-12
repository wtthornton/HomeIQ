"""
SQLAlchemy models for automation trace data.

Tables:
- automations: Registry of HA automations with rolling stats
- automation_executions: Individual execution records for fast queries
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from ..database import Base


class Automation(Base):
    """Automation registry — synced from HA entity registry."""

    __tablename__ = "automations"

    automation_id = Column(String, primary_key=True)  # "automation.office_motion_dimming"
    alias = Column(String, index=True)
    description = Column(Text)
    mode = Column(String)  # single, parallel, queued, restart
    enabled = Column(Boolean, default=True)

    # Rolling stats (updated on each execution upsert)
    total_executions = Column(Integer, default=0)
    total_errors = Column(Integer, default=0)
    avg_duration_seconds = Column(Float, default=0.0)
    success_rate = Column(Float, default=100.0)  # 0-100
    last_triggered = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    executions = relationship(
        "AutomationExecution", back_populates="automation", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Automation(id='{self.automation_id}', alias='{self.alias}')>"


class AutomationExecution(Base):
    """Individual automation execution record."""

    __tablename__ = "automation_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    automation_id = Column(
        String, ForeignKey("automations.automation_id", ondelete="CASCADE"), index=True
    )
    run_id = Column(String, unique=True, index=True)
    started_at = Column(DateTime, nullable=False, index=True)
    finished_at = Column(DateTime)
    duration_seconds = Column(Float)
    execution_result = Column(String, index=True)  # finished_successfully, error, aborted
    trigger_type = Column(String)  # state, time, event, etc.
    trigger_entity = Column(String)
    error_message = Column(Text)
    step_count = Column(Integer)
    last_step = Column(String)
    context_id = Column(String, index=True)

    # Relationship
    automation = relationship("Automation", back_populates="executions")

    def __repr__(self):
        return f"<AutomationExecution(run_id='{self.run_id}', result='{self.execution_result}')>"


# Composite indexes for common queries
Index("idx_execution_automation_started", AutomationExecution.automation_id, AutomationExecution.started_at.desc())
Index("idx_execution_result", AutomationExecution.execution_result)
