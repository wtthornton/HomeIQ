"""
SQLAlchemy database models for AI Automation Service

Epic AI-1: Pattern detection and automation suggestions
Epic AI-2: Device intelligence and capability tracking
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON, Boolean, Index, UniqueConstraint, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from datetime import datetime
from typing import Optional
import logging
import uuid

logger = logging.getLogger(__name__)

Base = declarative_base()


class Pattern(Base):
    """Detected automation patterns"""
    __tablename__ = 'patterns'
    
    id = Column(Integer, primary_key=True)
    pattern_type = Column(String, nullable=False)  # 'time_of_day', 'co_occurrence', 'anomaly'
    device_id = Column(String, nullable=False)
    pattern_metadata = Column(JSON)  # Pattern-specific data (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    confidence = Column(Float, nullable=False)
    occurrences = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Pattern(id={self.id}, type={self.pattern_type}, device={self.device_id}, confidence={self.confidence})>"


class Suggestion(Base):
    """
    Automation suggestions generated from patterns.
    
    Story AI1.23: Conversational Suggestion Refinement
    
    New conversational flow:
    1. Generate description_only (no YAML yet) -> status='draft'
    2. User refines with natural language -> status='refining', conversation_history updated
    3. User approves -> Generate automation_yaml -> status='yaml_generated'
    4. Deploy to HA -> status='deployed'
    """
    __tablename__ = 'suggestions'
    
    id = Column(Integer, primary_key=True)
    pattern_id = Column(Integer, ForeignKey('patterns.id'), nullable=True)
    
    # ===== NEW: Description-First Fields (Story AI1.23) =====
    description_only = Column(Text, nullable=False)  # Human-readable description
    conversation_history = Column(JSON, default=[])  # Array of edit history
    device_capabilities = Column(JSON, default={})   # Cached device features
    refinement_count = Column(Integer, default=0)    # Number of user edits
    
    # ===== YAML Generation (only after approval) =====
    automation_yaml = Column(Text, nullable=True)    # NULL until approved (changed from NOT NULL)
    yaml_generated_at = Column(DateTime, nullable=True)  # NEW: When YAML was created
    
    # ===== Status Tracking (updated for conversational flow) =====
    status = Column(String, default='draft')  # draft, refining, yaml_generated, deployed, rejected
    
    # ===== Legacy Fields (kept for compatibility) =====
    title = Column(String, nullable=False)
    category = Column(String, nullable=True)  # energy, comfort, security, convenience
    priority = Column(String, nullable=True)  # high, medium, low
    confidence = Column(Float, nullable=False)
    
    # ===== Timestamps =====
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)  # NEW: When user approved
    deployed_at = Column(DateTime, nullable=True)
    ha_automation_id = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<Suggestion(id={self.id}, title={self.title}, status={self.status}, refinements={self.refinement_count})>"
    
    def can_refine(self, max_refinements: int = 10) -> tuple[bool, Optional[str]]:
        """
        Check if suggestion can be refined further.
        
        Args:
            max_refinements: Maximum allowed refinements (default: 10)
        
        Returns:
            Tuple of (allowed: bool, error_message: Optional[str])
        """
        if self.refinement_count >= max_refinements:
            return False, f"Maximum refinements reached ({max_refinements}). Please approve or reject."
        return True, None


class UserFeedback(Base):
    """User feedback on suggestions"""
    __tablename__ = 'user_feedback'
    
    id = Column(Integer, primary_key=True)
    suggestion_id = Column(Integer, ForeignKey('suggestions.id'))
    action = Column(String, nullable=False)  # 'approved', 'rejected', 'modified'
    feedback_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<UserFeedback(id={self.id}, suggestion_id={self.suggestion_id}, action={self.action})>"


class AutomationVersion(Base):
    """
    Simple version history for automations.
    Keeps last 3 versions per automation for rollback.
    
    Story AI1.20: Simple Rollback
    """
    __tablename__ = 'automation_versions'
    
    id = Column(Integer, primary_key=True)
    automation_id = Column(String(100), nullable=False, index=True)
    yaml_content = Column(Text, nullable=False)
    deployed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    safety_score = Column(Integer, nullable=False)
    
    def __repr__(self):
        return f"<AutomationVersion(id={self.id}, automation_id={self.automation_id}, deployed_at={self.deployed_at})>"


# ============================================================================
# Epic AI-2: Device Intelligence Models (Story AI2.2)
# ============================================================================

class DeviceCapability(Base):
    """
    Device capability definitions from Zigbee2MQTT bridge.
    
    Stores universal capability data for device models. One record per
    unique model (e.g., "VZM31-SN", "MCCGQ11LM").
    
    Story AI2.2: Capability Database Schema & Storage
    Epic AI-2: Device Intelligence System
    
    Integration:
        Links to devices table via device.model field (cross-database)
        Devices are in data-api's metadata.db, capabilities in ai_automation.db
    
    Example:
        VZM31-SN -> {led_notifications, smart_bulb_mode, auto_off_timer, ...}
    """
    __tablename__ = 'device_capabilities'
    
    # Primary Key
    device_model = Column(String, primary_key=True)  # e.g., "VZM31-SN"
    
    # Device Identification
    manufacturer = Column(String, nullable=False)  # e.g., "Inovelli"
    integration_type = Column(String, nullable=False, default='zigbee2mqtt')
    description = Column(String, nullable=True)
    
    # Capability Data (JSON columns)
    capabilities = Column(JSON, nullable=False)  # Parsed, structured format
    mqtt_exposes = Column(JSON, nullable=True)   # Raw Zigbee2MQTT exposes (backup)
    
    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String, default='zigbee2mqtt_bridge')
    
    def __repr__(self):
        return f"<DeviceCapability(model='{self.device_model}', manufacturer='{self.manufacturer}', features={len(self.capabilities) if self.capabilities else 0})>"


class DeviceFeatureUsage(Base):
    """
    Track feature usage per device instance.
    
    Records which features are configured vs. available for each physical
    device. Used for utilization analysis and unused feature detection.
    
    Story AI2.2: Capability Database Schema & Storage
    Epic AI-2: Device Intelligence System
    
    Composite Primary Key: (device_id, feature_name)
    
    Integration:
        device_id links to devices.device_id in data-api's metadata.db (logical FK)
    
    Example:
        ("kitchen_switch", "led_notifications", configured=False)
        ("kitchen_switch", "smart_bulb_mode", configured=True)
    """
    __tablename__ = 'device_feature_usage'
    
    # Composite Primary Key
    device_id = Column(String, primary_key=True)       # FK to devices.device_id (cross-DB)
    feature_name = Column(String, primary_key=True)    # e.g., "led_notifications"
    
    # Usage Tracking
    configured = Column(Boolean, default=False, nullable=False)
    discovered_date = Column(DateTime, default=datetime.utcnow)
    last_checked = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<DeviceFeatureUsage(device='{self.device_id}', feature='{self.feature_name}', configured={self.configured})>"


# ============================================================================
# Epic AI-3: Cross-Device Synergy Models (Story AI3.1)
# ============================================================================

class SynergyOpportunity(Base):
    """
    Cross-device synergy opportunities for automation suggestions.
    
    Stores detected device pairs that could work together but currently
    have no automation connecting them.
    
    Story AI3.1: Device Synergy Detector Foundation
    Epic AI-3: Cross-Device Synergy & Contextual Opportunities
    """
    __tablename__ = 'synergy_opportunities'
    
    id = Column(Integer, primary_key=True)
    synergy_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    synergy_type = Column(String(50), nullable=False, index=True)  # 'device_pair', 'weather_context', etc.
    device_ids = Column(Text, nullable=False)  # JSON array of device IDs
    opportunity_metadata = Column(JSON)  # Synergy-specific data (trigger, action, relationship, etc.)
    impact_score = Column(Float, nullable=False)
    complexity = Column(String(20), nullable=False)  # 'low', 'medium', 'high'
    confidence = Column(Float, nullable=False)
    area = Column(String(100))  # Area/room where devices are located
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<SynergyOpportunity(id={self.id}, type={self.synergy_type}, area={self.area}, impact={self.impact_score})>"


# Indexes for fast lookups (Epic AI-2)
Index('idx_capabilities_manufacturer', DeviceCapability.manufacturer)
Index('idx_capabilities_integration', DeviceCapability.integration_type)
Index('idx_feature_usage_device', DeviceFeatureUsage.device_id)
Index('idx_feature_usage_configured', DeviceFeatureUsage.configured)


# Database engine and session
engine = None
async_session = None


async def init_db():
    """Initialize database - create tables if they don't exist"""
    global engine, async_session
    
    # Create async engine
    engine = create_async_engine(
        'sqlite+aiosqlite:///data/ai_automation.db',
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,  # Verify connections before using
        connect_args={
            "timeout": 30.0
        }
    )
    
    # Configure SQLite pragmas for optimal performance
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """
        Set SQLite pragmas on each connection for optimal performance.
        
        Pragmas configured:
        - WAL mode: Better concurrency (multiple readers, one writer)
        - NORMAL sync: Faster writes, still safe (survives OS crash)
        - 64MB cache: Improves query performance
        - Memory temp tables: Faster temporary operations
        - Foreign keys ON: Enforce referential integrity
        - 30s busy timeout: Wait for locks instead of immediate fail
        """
        cursor = dbapi_conn.cursor()
        try:
            # Enable WAL mode for concurrent access
            cursor.execute("PRAGMA journal_mode=WAL")
            
            # Synchronous mode: NORMAL is faster and still safe
            cursor.execute("PRAGMA synchronous=NORMAL")
            
            # Cache size (negative = KB, positive = pages)
            cursor.execute("PRAGMA cache_size=-64000")  # 64MB
            
            # Use memory for temp tables
            cursor.execute("PRAGMA temp_store=MEMORY")
            
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys=ON")
            
            # Busy timeout (milliseconds)
            cursor.execute("PRAGMA busy_timeout=30000")  # 30s
            
            logger.debug("SQLite pragmas configured successfully")
        except Exception as e:
            logger.error(f"Failed to set SQLite pragmas: {e}")
            raise
        finally:
            cursor.close()
    
    # Create session factory
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized successfully")
    return engine, async_session


async def get_db():
    """Dependency for FastAPI routes to get database session"""
    async with async_session() as session:
        yield session


class AskAIQuery(Base):
    """Ask AI natural language queries and their generated suggestions"""
    __tablename__ = 'ask_ai_queries'
    
    query_id = Column(String, primary_key=True, default=lambda: f"query-{uuid.uuid4().hex[:8]}")
    original_query = Column(Text, nullable=False)
    user_id = Column(String, nullable=False, default="anonymous")
    parsed_intent = Column(String, nullable=True)  # 'control', 'monitor', 'automate', etc.
    extracted_entities = Column(JSON, nullable=True)  # Entities from HA Conversation API
    suggestions = Column(JSON, nullable=True)  # Generated suggestions array
    confidence = Column(Float, nullable=True)  # Overall confidence score
    processing_time_ms = Column(Integer, nullable=True)  # Time taken to process
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<AskAIQuery(query_id={self.query_id}, query='{self.original_query[:50]}...', suggestions={len(self.suggestions or [])})>"


class EntityAlias(Base):
    """User-defined aliases for entities (nicknames/personalized names)"""
    __tablename__ = "entity_aliases"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(String, nullable=False, index=True)
    alias = Column(String, nullable=False)
    user_id = Column(String, nullable=False, index=True, default="anonymous")  # For multi-user support
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: one alias per entity per user (user can have multiple aliases for same entity)
    # Index for fast alias lookup
    __table_args__ = (
        UniqueConstraint('alias', 'user_id', name='uq_alias_user'),
        Index('idx_alias_lookup', 'alias', 'user_id'),  # Fast lookup
    )
    
    def __repr__(self):
        return f"<EntityAlias(id={self.id}, entity_id='{self.entity_id}', alias='{self.alias}', user_id='{self.user_id}')>"


def get_db_session():
    """
    Get database session as async context manager.
    
    Usage:
        async with get_db_session() as db:
            result = await db.execute(query)
    """
    return async_session()


# ============================================================================
# Reverse Engineering Metrics Tracking
# ============================================================================

class ReverseEngineeringMetrics(Base):
    """
    Metrics for tracking reverse engineering value and performance.
    
    Tracks similarity improvements, iterations, costs, and automation success
    to measure the value provided by reverse engineering.
    
    Created: November 2025
    """
    __tablename__ = 'reverse_engineering_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Keys
    suggestion_id = Column(String, nullable=False, index=True)  # Links to AskAI suggestion
    query_id = Column(String, nullable=False, index=True)  # Links to AskAI query
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # ===== Similarity Metrics =====
    initial_similarity = Column(Float, nullable=True)  # Similarity before RE (iteration 0)
    final_similarity = Column(Float, nullable=False)  # Similarity after RE
    similarity_improvement = Column(Float, nullable=True)  # final - initial
    improvement_percentage = Column(Float, nullable=True)  # (final/initial - 1) * 100
    
    # ===== Performance Metrics =====
    iterations_completed = Column(Integer, nullable=False)  # Number of iterations
    max_iterations = Column(Integer, nullable=False, default=5)
    convergence_achieved = Column(Boolean, nullable=False, default=False)
    total_processing_time_ms = Column(Integer, nullable=True)  # Total time
    time_per_iteration_ms = Column(Float, nullable=True)  # Average time per iteration
    
    # ===== Cost Metrics =====
    total_tokens_used = Column(Integer, nullable=False, default=0)
    estimated_cost_usd = Column(Float, nullable=True)  # ~$0.05 per 1M input tokens
    tokens_per_iteration = Column(Float, nullable=True)
    
    # ===== Automation Success =====
    automation_created = Column(Boolean, nullable=True)  # Was automation created in HA?
    automation_id = Column(String, nullable=True)  # HA automation ID if created
    had_validation_errors = Column(Boolean, nullable=True)  # Did original YAML have errors?
    errors_fixed_count = Column(Integer, nullable=True, default=0)  # Errors fixed by RE
    automation_approved = Column(Boolean, nullable=True)  # Did user approve/test?
    automation_in_use = Column(Boolean, nullable=True)  # Is automation active in HA?
    
    # ===== YAML Comparison =====
    original_yaml = Column(Text, nullable=True)  # YAML before reverse engineering
    corrected_yaml = Column(Text, nullable=True)  # YAML after reverse engineering
    yaml_changed = Column(Boolean, nullable=True, default=False)  # Did RE change the YAML?
    
    # ===== Iteration History (JSON) =====
    iteration_history_json = Column(JSON, nullable=True)  # Full iteration history
    
    # ===== Indexes =====
    __table_args__ = (
        Index('idx_re_metrics_query_id', 'query_id'),
        Index('idx_re_metrics_suggestion_id', 'suggestion_id'),
        Index('idx_re_metrics_created_at', 'created_at'),
        Index('idx_re_metrics_final_similarity', 'final_similarity'),
        Index('idx_re_metrics_convergence', 'convergence_achieved'),
        Index('idx_re_metrics_automation_created', 'automation_created'),
    )
    
    def __repr__(self):
        return f"<ReverseEngineeringMetrics(id={self.id}, query_id={self.query_id}, " \
               f"similarity={self.final_similarity:.2%}, iterations={self.iterations_completed}, " \
               f"cost=${self.estimated_cost_usd:.4f})>"