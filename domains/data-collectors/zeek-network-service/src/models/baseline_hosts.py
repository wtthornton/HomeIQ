"""SQLAlchemy model for network_baseline_hosts table.

Stores known hosts and services from known_hosts.log and
known_services.log, supporting baseline approval workflow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

if TYPE_CHECKING:
    from datetime import datetime


class Base(DeclarativeBase):
    pass


class NetworkBaselineHost(Base):
    """A host observed on the network with baseline approval status."""

    __tablename__ = "network_baseline_hosts"
    __table_args__ = (
        Index("idx_baseline_ip", "ip_address"),
        Index("idx_baseline_mac", "mac_address"),
        Index("idx_baseline_is_baseline", "is_baseline"),
        {"schema": "devices"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Primary identifiers
    ip_address: Mapped[str] = mapped_column(INET, nullable=False, unique=True)
    mac_address: Mapped[str | None] = mapped_column(String(17))
    hostname: Mapped[str | None] = mapped_column(String(255))

    # Services observed on this host (from known_services.log)
    services: Mapped[dict | None] = mapped_column(JSONB)

    # Baseline approval
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str | None] = mapped_column(String(100))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Metadata
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    times_seen: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str | None] = mapped_column(Text)
