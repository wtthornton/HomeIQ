"""
Service Model for SQLite Storage
Epic 2025: Stores available services per domain from HA Services API
"""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Index, String

from ..database import Base


class Service(Base):
    """Available services per domain from Home Assistant"""

    __tablename__ = "services"

    # Composite primary key
    domain = Column(String, primary_key=True)  # e.g., "light"
    service_name = Column(String, primary_key=True)  # e.g., "turn_on"

    # Service metadata
    name = Column(String)  # Display name (e.g., "Turn on")
    description = Column(String)  # Service description
    fields = Column(JSON)  # Service fields/parameters
    target = Column(JSON)  # Target entity/area specification

    # Timestamps
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Service(domain='{self.domain}', service_name='{self.service_name}', name='{self.name}')>"


# Indexes for common queries
Index('idx_services_domain', Service.domain)

