"""
Statistics Metadata Model (Epic 45.1)

Tracks which entities are eligible for statistics aggregation.
Based on Home Assistant's statistics_meta table pattern.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Index, String, Text

from ..database import Base


class StatisticsMeta(Base):
    """Statistics metadata table - tracks entities eligible for statistics aggregation"""

    __tablename__ = "statistics_meta"

    # Primary key (entity_id)
    statistic_id = Column(String, primary_key=True)  # entity_id

    # Source tracking
    source = Column(String, nullable=False, default="state")  # "state" or "sensor"

    # Measurement metadata
    unit_of_measurement = Column(String)  # Unit (e.g., "°C", "W", "kWh")
    state_class = Column(String, index=True)  # "measurement", "total", "total_increasing"

    # Aggregation capabilities
    has_mean = Column(Boolean, default=True)  # Can calculate mean (measurement entities)
    has_sum = Column(Boolean, default=False)  # Can calculate sum (total_increasing entities)

    # Reset tracking (for total_increasing entities)
    last_reset = Column(DateTime)  # Last reset timestamp (if applicable)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<StatisticsMeta(statistic_id='{self.statistic_id}', state_class='{self.state_class}')>"


# Indexes for fast lookups
Index('idx_statistics_meta_state_class', StatisticsMeta.state_class)
Index('idx_statistics_meta_has_mean', StatisticsMeta.has_mean)
Index('idx_statistics_meta_has_sum', StatisticsMeta.has_sum)


