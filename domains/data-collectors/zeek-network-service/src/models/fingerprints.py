"""SQLAlchemy model for network_device_fingerprints table.

Stores device identity data from DHCP, TLS (JA3/JA4), SSH (HASSH),
and software detection — keyed by MAC address.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class NetworkDeviceFingerprint(Base):
    """A network device identified by its MAC address."""

    __tablename__ = "network_device_fingerprints"
    __table_args__ = (
        Index("idx_fingerprints_ip", "ip_address"),
        Index("idx_fingerprints_ja3", "ja3_hash"),
        Index("idx_fingerprints_ja4", "ja4_hash"),
        Index("idx_fingerprints_vendor", "vendor"),
        {"schema": "devices"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mac_address: Mapped[str] = mapped_column(String(17), nullable=False, unique=True)
    ip_address: Mapped[str] = mapped_column(INET, nullable=False)
    hostname: Mapped[str | None] = mapped_column(String(255))
    vendor: Mapped[str | None] = mapped_column(String(255))

    # DHCP fingerprint
    dhcp_fingerprint: Mapped[str | None] = mapped_column(String(512))
    dhcp_vendor_class: Mapped[str | None] = mapped_column(String(255))

    # TLS fingerprints
    ja3_hash: Mapped[str | None] = mapped_column(String(32))
    ja3s_hash: Mapped[str | None] = mapped_column(String(32))
    ja4_hash: Mapped[str | None] = mapped_column(String(64))

    # SSH fingerprint
    hassh_hash: Mapped[str | None] = mapped_column(String(32))
    hassh_server: Mapped[str | None] = mapped_column(String(32))

    # Software detection
    user_agent: Mapped[str | None] = mapped_column(Text)
    server_software: Mapped[str | None] = mapped_column(Text)
    os_guess: Mapped[str | None] = mapped_column(String(100))

    # Metadata
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    times_seen: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
