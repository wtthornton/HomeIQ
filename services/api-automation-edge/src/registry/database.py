"""
Database models for spec registry
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from .spec_registry import Base


class SpecVersion(Base):
    """Database model for spec versions"""
    __tablename__ = "spec_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    spec_id = Column(String, index=True, nullable=False)
    version = Column(String, nullable=False)
    home_id = Column(String, index=True, nullable=False)
    spec_hash = Column(String, unique=True, nullable=False, index=True)
    spec_content = Column(Text, nullable=False)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deployed_at = Column(DateTime, nullable=True)
    is_active = Column(String, default="false")  # "true" or "false" for SQLite compatibility
