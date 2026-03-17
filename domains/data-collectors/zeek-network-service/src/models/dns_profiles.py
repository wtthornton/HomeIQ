"""SQLAlchemy model for network_device_dns_profiles table.

Stores per-device DNS query frequency with domain category classification.
Rolling 7-day query counts, updated from dns.log parsing.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class NetworkDeviceDnsProfile(Base):
    """Per-device DNS query profile with domain categorization."""

    __tablename__ = "network_device_dns_profiles"
    __table_args__ = (
        Index("idx_dns_profiles_device_ip", "device_ip"),
        Index("idx_dns_profiles_domain", "domain_suffix"),
        Index("idx_dns_profiles_category", "category"),
        {"schema": "devices"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    domain_suffix: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")

    # Rolling 7-day counts
    query_count_7d: Mapped[int] = mapped_column(Integer, default=0)
    last_query_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Metadata
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
