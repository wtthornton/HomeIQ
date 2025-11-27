"""
Database models for AI Training Service

Epic 39, Story 39.1: Training Service Foundation
Extracted from ai-automation-service for shared database access.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    Index,
    JSON,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TrainingRun(Base):
    """Record of training jobs (soft prompt, GNN, etc.)."""

    __tablename__ = 'training_runs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    training_type = Column(String(20), nullable=False, default='soft_prompt')  # soft_prompt, gnn_synergy
    status = Column(String(20), nullable=False, default='queued')  # queued, running, completed, failed
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    finished_at = Column(DateTime, nullable=True)
    dataset_size = Column(Integer, nullable=True)
    base_model = Column(String, nullable=True)
    output_dir = Column(String, nullable=True)
    run_identifier = Column(String, nullable=True, unique=True)
    final_loss = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_path = Column(String, nullable=True)
    triggered_by = Column(String, nullable=False, default='admin')

    # Iteration History (JSON)
    iteration_history_json = Column(JSON, nullable=True)  # Full iteration history

    __table_args__ = (
        Index('idx_training_runs_status', 'status'),
        Index('idx_training_runs_started_at', 'started_at'),
        Index('idx_training_runs_run_identifier', 'run_identifier'),
    )

    def __repr__(self) -> str:
        return f"<TrainingRun(id={self.id}, status={self.status}, started_at={self.started_at})>"

