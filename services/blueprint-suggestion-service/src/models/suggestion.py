"""SQLAlchemy models for Blueprint Suggestion Service."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Float, String, Text, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class BlueprintSuggestion(Base):
    """Blueprint suggestion model."""
    
    __tablename__ = "blueprint_suggestions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    blueprint_id = Column(String, nullable=False, index=True)
    blueprint_name = Column(String, nullable=True)  # Blueprint name for display
    blueprint_description = Column(Text, nullable=True)  # Blueprint description explaining what it does
    suggestion_score = Column(Float, nullable=False, index=True)
    matched_devices = Column(JSON, nullable=False)  # List of device signatures
    use_case = Column(String, index=True, nullable=True)
    status = Column(String, default="pending", index=True)  # pending, accepted, declined
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
    accepted_at = Column(DateTime, nullable=True)
    declined_at = Column(DateTime, nullable=True)
    conversation_id = Column(String, nullable=True)  # Link to Agent conversation
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "blueprint_id": self.blueprint_id,
            "blueprint_name": self.blueprint_name,
            "blueprint_description": self.blueprint_description,
            "suggestion_score": self.suggestion_score,
            "matched_devices": self.matched_devices,
            "use_case": self.use_case,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "declined_at": self.declined_at.isoformat() if self.declined_at else None,
            "conversation_id": self.conversation_id,
        }
