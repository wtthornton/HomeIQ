"""
Area Model for Database Storage
TAP-7584 - Areas as first-class rows, sourced from the HA area registry,
instead of being reconstructed with SELECT DISTINCT over entities.
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String

from ..database import Base


class Area(Base):
    """Area registry model - HA areas/rooms persisted as first-class rows"""

    __tablename__ = "areas"

    # Primary key
    area_id = Column(String, primary_key=True)

    # Area metadata
    name = Column(String, nullable=False)
    floor_id = Column(String, index=True)
    floor_name = Column(String)

    # Provenance: "ha_registry" when sourced from HA's area registry,
    # "inferred" when backfilled from a distinct area_id with no registry entry.
    source = Column(String, nullable=False, default="inferred")

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self):
        return f"<Area(area_id='{self.area_id}', name='{self.name}')>"
