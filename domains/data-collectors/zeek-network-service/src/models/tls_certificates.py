"""SQLAlchemy model for network_tls_certificates table.

Stores TLS certificate metadata from x509.log and ssl.log parsing,
including subject, issuer, validity, key info, and TLS negotiation details.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class NetworkTlsCertificate(Base):
    """A TLS certificate observed on the network."""

    __tablename__ = "network_tls_certificates"
    __table_args__ = (
        Index("idx_tls_certs_fingerprint", "fingerprint", unique=True),
        Index("idx_tls_certs_not_valid_after", "not_valid_after"),
        Index("idx_tls_certs_server_name", "server_name"),
        {"schema": "devices"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # Certificate identity
    subject: Mapped[str | None] = mapped_column(Text)
    issuer: Mapped[str | None] = mapped_column(Text)
    serial: Mapped[str | None] = mapped_column(String(128))

    # Validity
    not_valid_before: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    not_valid_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Key info
    key_type: Mapped[str | None] = mapped_column(String(20))
    key_length: Mapped[int | None] = mapped_column(Integer)

    # TLS negotiation (from ssl.log)
    tls_version: Mapped[str | None] = mapped_column(String(20))
    cipher_suite: Mapped[str | None] = mapped_column(String(100))
    server_name: Mapped[str | None] = mapped_column(String(255))

    # Flags
    self_signed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    times_seen: Mapped[int] = mapped_column(Integer, default=1)
