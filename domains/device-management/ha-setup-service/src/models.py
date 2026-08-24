"""SQLAlchemy models for HA Setup Service"""

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from .database import Base


class EnvironmentHealth(Base):
    """Environment health metrics storage"""

    __tablename__ = "environment_health"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    health_score = Column(Integer, nullable=False)  # 0-100
    ha_status = Column(String, nullable=False)  # healthy, warning, critical
    ha_version = Column(String)
    integrations_status = Column(JSON, nullable=False)  # Status of each integration
    performance_metrics = Column(JSON, nullable=False)  # Response time, resource usage
    issues_detected = Column(JSON)  # List of detected issues

    def __repr__(self):
        return (
            f"<EnvironmentHealth(id={self.id}, score={self.health_score}, status={self.ha_status})>"
        )


class IntegrationHealth(Base):
    """Individual integration health status"""

    __tablename__ = "integration_health"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    integration_name = Column(String, nullable=False, index=True)
    integration_type = Column(String, nullable=False)  # zha, hue, wled, etc.
    status = Column(String, nullable=False)  # healthy, warning, error
    is_configured = Column(Boolean, default=False)
    is_connected = Column(Boolean, default=False)
    error_message = Column(String)
    last_check = Column(DateTime(timezone=True))
    check_details = Column(JSON)  # Detailed check results

    def __repr__(self):
        return f"<IntegrationHealth(name={self.integration_name}, status={self.status})>"


class PerformanceMetric(Base):
    """Performance metrics over time"""

    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    metric_type = Column(String, nullable=False, index=True)  # response_time, cpu, memory
    metric_value = Column(Float, nullable=False)
    component = Column(String)  # Which component (ha_core, hacs, etc.)
    metric_metadata = Column(
        JSON
    )  # Additional metric context (renamed from 'metadata' - reserved in SQLAlchemy)

    def __repr__(self):
        return f"<PerformanceMetric(type={self.metric_type}, value={self.metric_value})>"


class SetupWizardSession(Base):
    """Setup wizard session tracking"""

    __tablename__ = "setup_wizard_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, nullable=False, index=True)
    integration_type = Column(String, nullable=False)  # zha, hue, wled, etc.
    status = Column(String, nullable=False)  # pending, in_progress, completed, failed
    steps_completed = Column(Integer, default=0)
    total_steps = Column(Integer, nullable=False)
    current_step = Column(String)
    configuration = Column(JSON)  # Wizard configuration data
    error_log = Column(JSON)  # Errors encountered during setup
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<SetupWizardSession(id={self.session_id}, type={self.integration_type}, status={self.status})>"


class IntegrationBlocker(Base):
    """A reason one integration on THIS instance is not configured automatically.

    Refreshed whenever ``GET /api/v1/init/blockers`` runs. The taxonomy itself
    lives in ``homeiq_ha.agent.blockers.CATALOGUE`` and ships with the code;
    this table records which entries a given install is actually hitting, so a
    dashboard or support conversation can read it without re-probing Home
    Assistant's config flows.

    Keyed on ``domain`` because a config flow is per integration, not per
    device — several observed devices collapse to one row.
    """

    __tablename__ = "integration_blockers"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, nullable=False, unique=True, index=True)
    title = Column(String, nullable=False)
    # Null means nothing is blocking it — the flow is fillable right now.
    blocker_kind = Column(String, index=True)
    evidence = Column(String, nullable=False)  # STRICT | MAC | HOSTNAME
    flow_step = Column(String, nullable=False)  # form | external | progress
    # The config-flow fields the form asks for. Named for what the wizard
    # collects, not for an environment variable — nothing here is set on the
    # host.
    required_fields = Column(JSON, nullable=False, default=list)
    # Retained only to satisfy the live NOT NULL constraint while the column is
    # retired (TAP-6462, expand/contract). Nothing reads it and nothing puts a
    # meaningful value in it any more: both API payloads have dropped it, and
    # inserts get the `[]` default. Dropping it needs a migration, and this
    # service has no migration chain yet — alembic is copied into the image but
    # never invoked, and `integration_blockers` has no reproducible creation
    # path at all. Remove the column together with that fix, never before: the
    # constraint has no server default, and Postgres checks NOT NULL before the
    # ON CONFLICT arbiter, so an omission-upsert would abort the whole pass.
    missing_env_vars = Column(JSON, nullable=False, default=list)
    devices = Column(JSON, nullable=False, default=list)
    first_seen = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<IntegrationBlocker(domain={self.domain}, blocker={self.blocker_kind})>"
