"""
SQLAlchemy database models for AI Automation Service

Epic AI-1: Pattern detection and automation suggestions
Epic AI-2: Device intelligence and capability tracking
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON, Boolean, Index, UniqueConstraint, event, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from datetime import datetime
from typing import Optional
import logging
import uuid

logger = logging.getLogger(__name__)

Base = declarative_base()


from ..config import settings as app_settings


def _default_enabled_categories() -> dict:
    return {
        "energy": True,
        "comfort": True,
        "security": True,
        "convenience": True,
    }


def get_system_settings_defaults() -> dict:
    return {
        "schedule_enabled": True,
        "schedule_time": "03:00",
        "min_confidence": 70,
        "max_suggestions": 10,
        "enabled_categories": _default_enabled_categories(),
        "budget_limit": 10.0,
        "notifications_enabled": False,
        "notification_email": "",
        "soft_prompt_enabled": getattr(app_settings, "soft_prompt_enabled", True),
        "soft_prompt_model_dir": getattr(app_settings, "soft_prompt_model_dir", "data/ask_ai_soft_prompt"),
        "soft_prompt_confidence_threshold": getattr(app_settings, "soft_prompt_confidence_threshold", 0.85),
        "guardrail_enabled": getattr(app_settings, "guardrail_enabled", True),
        "guardrail_model_name": getattr(app_settings, "guardrail_model_name", "unitary/toxic-bert"),
        "guardrail_threshold": getattr(app_settings, "guardrail_threshold", 0.6),
    }


class Pattern(Base):
    """
    Detected automation patterns with history tracking.
    
    Phase 1: Enhanced with history tracking fields for trend analysis.
    """
    __tablename__ = 'patterns'
    
    id = Column(Integer, primary_key=True)
    pattern_type = Column(String, nullable=False)  # 'time_of_day', 'co_occurrence', 'anomaly'
    device_id = Column(String, nullable=False)
    pattern_metadata = Column(JSON)  # Pattern-specific data (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    confidence = Column(Float, nullable=False)
    occurrences = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Phase 1: History tracking fields
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    confidence_history_count = Column(Integer, default=1, nullable=False)
    trend_direction = Column(String(20), nullable=True)  # 'increasing', 'stable', 'decreasing' (cached)
    trend_strength = Column(Float, default=0.0, nullable=False)  # Cached trend strength (0.0-1.0)
    
    # Quality improvement: Confidence calibration fields
    raw_confidence = Column(Float, nullable=True)  # Original confidence before calibration
    calibrated = Column(Boolean, default=False, nullable=False)  # Whether confidence has been calibrated
    
    def __repr__(self):
        return f"<Pattern(id={self.id}, type={self.pattern_type}, device={self.device_id}, confidence={self.confidence}, trend={self.trend_direction})>"


class SystemSettings(Base):
    """Persistent system-wide configuration values."""

    __tablename__ = 'system_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_enabled = Column(Boolean, nullable=False, default=True)
    schedule_time = Column(String, nullable=False, default="03:00")
    min_confidence = Column(Integer, nullable=False, default=70)
    max_suggestions = Column(Integer, nullable=False, default=10)
    enabled_categories = Column(JSON, nullable=False, default=_default_enabled_categories)
    budget_limit = Column(Float, nullable=False, default=10.0)
    notifications_enabled = Column(Boolean, nullable=False, default=False)
    notification_email = Column(String, nullable=False, default="")
    soft_prompt_enabled = Column(Boolean, nullable=False, default=lambda: getattr(app_settings, "soft_prompt_enabled", True))
    soft_prompt_model_dir = Column(String, nullable=False, default=lambda: getattr(app_settings, "soft_prompt_model_dir", "data/ask_ai_soft_prompt"))
    soft_prompt_confidence_threshold = Column(Float, nullable=False, default=lambda: getattr(app_settings, "soft_prompt_confidence_threshold", 0.85))
    guardrail_enabled = Column(Boolean, nullable=False, default=lambda: getattr(app_settings, "guardrail_enabled", True))
    guardrail_model_name = Column(String, nullable=False, default=lambda: getattr(app_settings, "guardrail_model_name", "unitary/toxic-bert"))
    guardrail_threshold = Column(Float, nullable=False, default=lambda: getattr(app_settings, "guardrail_threshold", 0.6))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('id', name='uq_system_settings_singleton'),
    )

    def __repr__(self):
        return f"<SystemSettings(schedule_enabled={self.schedule_enabled}, soft_prompt_enabled={self.soft_prompt_enabled}, guardrail_enabled={self.guardrail_enabled})>"


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
    
    # ===== Expert Mode Fields (NEW - Commit ca86050) =====
    mode = Column(String(20), nullable=True, server_default='auto_draft',
                  comment='Suggestion mode: auto_draft or expert')
    yaml_edited_at = Column(DateTime, nullable=True,
                            comment='Timestamp when YAML was manually edited in expert mode')
    yaml_edit_count = Column(Integer, nullable=True, server_default='0',
                             comment='Number of manual YAML edits made in expert mode')
    yaml_generation_method = Column(String(50), nullable=True,
                                    comment='Method: auto_draft, expert_manual, expert_manual_edited, etc.')
    
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

class PatternHistory(Base):
    """
    Time-series snapshots of pattern confidence and occurrences.
    
    Phase 1: Stores historical data for trend analysis and pattern validation.
    """
    __tablename__ = 'pattern_history'
    
    id = Column(Integer, primary_key=True)
    pattern_id = Column(Integer, ForeignKey('patterns.id', ondelete='CASCADE'), nullable=False)
    confidence = Column(Float, nullable=False)
    occurrences = Column(Integer, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<PatternHistory(id={self.id}, pattern_id={self.pattern_id}, confidence={self.confidence}, recorded_at={self.recorded_at})>"


class SynergyOpportunity(Base):
    """
    Cross-device synergy opportunities for automation suggestions.
    
    Stores detected device pairs that could work together but currently
    have no automation connecting them.
    
    Story AI3.1: Device Synergy Detector Foundation
    Epic AI-3: Cross-Device Synergy & Contextual Opportunities
    Phase 2: Enhanced with pattern validation support
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
    
    # Phase 2: Pattern validation fields
    pattern_support_score = Column(Float, default=0.0, nullable=False)
    validated_by_patterns = Column(Boolean, default=False, nullable=False)
    supporting_pattern_ids = Column(Text, nullable=True)  # JSON array of pattern IDs
    
    # Epic AI-4: N-level synergy fields
    synergy_depth = Column(Integer, default=2, nullable=False, server_default='2')  # Number of devices in chain (2 = pair, 3+ = multi-hop)
    chain_devices = Column(Text, nullable=True)  # JSON array of entity_ids in automation chain
    embedding_similarity = Column(Float, nullable=True)  # Semantic similarity score from embeddings
    rerank_score = Column(Float, nullable=True)  # Cross-encoder re-ranking score
    final_score = Column(Float, nullable=True)  # Combined score (0.5*embedding + 0.5*rerank)
    
    def __repr__(self):
        validated = "✓" if self.validated_by_patterns else "✗"
        depth = getattr(self, 'synergy_depth', 2)
        return f"<SynergyOpportunity(id={self.id}, type={self.synergy_type}, depth={depth}, area={self.area}, impact={self.impact_score}, validated={validated})>"


class DiscoveredSynergy(Base):
    """
    ML-discovered synergies from association rule mining.
    
    Stores synergies found by Apriori algorithm from actual behavior,
    not predefined rule-based relationships.
    
    Quality Improvement: Priority 1.4
    """
    __tablename__ = 'discovered_synergies'
    
    id = Column(Integer, primary_key=True)
    synergy_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    trigger_entity = Column(String, nullable=False, index=True)
    action_entity = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False, default='mined')  # 'mined' for ML-discovered
    
    # Association rule metrics
    support = Column(Float, nullable=False)  # P(X ∪ Y)
    confidence = Column(Float, nullable=False)  # P(Y|X)
    lift = Column(Float, nullable=False)  # P(Y|X) / P(Y)
    
    # Temporal analysis
    frequency = Column(Integer, nullable=False)  # Number of occurrences
    consistency = Column(Float, nullable=False)  # Consistency score (0.0-1.0)
    time_window_seconds = Column(Integer, nullable=False)  # Time window for co-occurrence
    
    # Discovery metadata
    discovered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    validation_count = Column(Integer, default=0, nullable=False)
    validation_passed = Column(Boolean, nullable=True)  # None = not yet validated, True/False = validated
    status = Column(String, nullable=False, default='discovered')  # 'discovered', 'validated', 'rejected'
    rejection_reason = Column(Text, nullable=True)  # Reason if rejected
    last_validated = Column(DateTime, nullable=True)  # Last validation timestamp
    
    # Metadata (JSON) - renamed from 'metadata' to avoid SQLAlchemy reserved name conflict
    synergy_metadata = Column(JSON, nullable=True)  # Additional metadata (analysis_period, total_transactions, etc.)
    
    def __repr__(self):
        status_icon = "✓" if self.validation_passed else "✗" if self.validation_passed is False else "?"
        return f"<DiscoveredSynergy(id={self.id}, {self.trigger_entity} → {self.action_entity}, lift={self.lift:.2f}, status={status_icon})>"


# Indexes for fast lookups (Epic AI-2)
Index('idx_capabilities_manufacturer', DeviceCapability.manufacturer)
Index('idx_capabilities_integration', DeviceCapability.integration_type)
Index('idx_feature_usage_device', DeviceFeatureUsage.device_id)
Index('idx_feature_usage_configured', DeviceFeatureUsage.configured)

# Phase 1: Pattern history indexes
Index('idx_pattern_history_pattern', PatternHistory.pattern_id, PatternHistory.recorded_at)
Index('idx_pattern_history_recorded', PatternHistory.recorded_at.desc())

# Phase 1: Pattern indexes
Index('idx_patterns_device', Pattern.device_id)
Index('idx_patterns_type', Pattern.pattern_type)
Index('idx_patterns_confidence', Pattern.confidence.desc())

# Phase 2: Synergy pattern validation indexes
Index('idx_synergy_validated', SynergyOpportunity.validated_by_patterns)
Index('idx_synergy_pattern_support', SynergyOpportunity.pattern_support_score.desc())


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
    
    # Create tables (including v2 models)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Import v2 models to ensure they're registered
        try:
            from .models_v2 import Conversation, ConversationTurn, ConfidenceFactor, FunctionCall, AutomationSuggestionV2
            # v2 models use the same Base, so they're already included in create_all
            logger.info("✅ v2 conversation models registered")
        except ImportError:
            logger.warning("⚠️ v2 models not available - v2 features may not work")
    
    # Seed default system settings if missing
    async with async_session() as session:
        result = await session.execute(select(SystemSettings).limit(1))
        existing = result.scalar_one_or_none()
        if not existing:
            defaults = get_system_settings_defaults()
            system_settings = SystemSettings(**defaults)
            system_settings.id = 1
            session.add(system_settings)
            await session.commit()
            logger.info("Seeded default system settings")

    logger.info("Database initialized successfully")
    return engine, async_session


async def get_db():
    """Dependency for FastAPI routes to get database session"""
    async with async_session() as session:
        yield session


class ManualRefreshTrigger(Base):
    """Audit log for manual suggestion refresh requests."""
    __tablename__ = 'manual_refresh_triggers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    triggered_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AnalysisRunStatus(Base):
    """Persisted history of analysis runs with summary metrics."""
    __tablename__ = 'analysis_run_status'

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=False, index=True)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    details = Column(JSON, nullable=True)


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


class ClarificationSessionDB(Base):
    """
    Persistent storage for Ask AI clarification sessions.
    
    Tracks clarification conversations where the AI needs to ask follow-up
    questions to understand ambiguous user queries. Links back to the original
    query for suggestion retrieval.
    
    Created: November 2025
    Story: AI1.26 - Clarification Flow Improvements
    """
    __tablename__ = 'clarification_sessions'
    
    # Primary identifier
    session_id = Column(String, primary_key=True, default=lambda: f"clarify-{uuid.uuid4().hex[:8]}")
    
    # Query linkage
    original_query_id = Column(String, ForeignKey('ask_ai_queries.query_id'), nullable=False, index=True)
    original_query = Column(Text, nullable=False)
    
    # User context
    user_id = Column(String, nullable=False, default="anonymous", index=True)
    
    # Clarification state
    questions = Column(JSON, nullable=False, default=list)  # Array of ClarificationQuestion dicts
    answers = Column(JSON, nullable=False, default=list)  # Array of ClarificationAnswer dicts
    ambiguities = Column(JSON, nullable=True)  # Array of detected Ambiguity dicts
    
    # Session tracking
    status = Column(String, nullable=False, default='in_progress', index=True)  # 'in_progress', 'complete', 'abandoned'
    rounds_completed = Column(Integer, nullable=False, default=0)
    max_rounds = Column(Integer, nullable=False, default=3)
    
    # Confidence tracking
    current_confidence = Column(Float, nullable=False, default=0.0)
    confidence_threshold = Column(Float, nullable=False, default=0.85)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Optional linkage to generated query after clarification
    clarification_query_id = Column(String, ForeignKey('ask_ai_queries.query_id'), nullable=True, index=True)
    
    __table_args__ = (
        Index('idx_clarification_user', 'user_id', 'created_at'),
        Index('idx_clarification_status', 'status', 'created_at'),
        Index('idx_clarification_original_query', 'original_query_id'),
    )
    
    def __repr__(self):
        return f"<ClarificationSessionDB(session_id={self.session_id}, original_query_id={self.original_query_id}, status={self.status}, rounds={self.rounds_completed})>"


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


class SemanticKnowledge(Base):
    """
    Generic semantic knowledge storage for RAG (Retrieval-Augmented Generation).
    
    Stores text with embeddings for semantic similarity search.
    Used for:
    - Query clarification (learn from successful queries)
    - Pattern matching enhancement
    - Suggestion generation
    - Device intelligence
    - Automation mining
    """
    __tablename__ = 'semantic_knowledge'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)  # Original text (query, pattern, blueprint, etc.)
    embedding = Column(JSON, nullable=False)  # 384-dim embedding array (stored as JSON)
    knowledge_type = Column(String, nullable=False, index=True)  # 'query', 'pattern', 'blueprint', 'automation', etc.
    knowledge_metadata = Column(JSON, nullable=True)  # Flexible metadata (device_id, area_id, confidence, etc.) - renamed from 'metadata' to avoid SQLAlchemy reserved word conflict
    success_score = Column(Float, default=0.5, nullable=False)  # 0.0-1.0 (learned from user feedback)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_knowledge_type', 'knowledge_type'),  # Fast filtering by type
        Index('idx_success_score', 'success_score'),  # For ranking by success
        Index('idx_created_at', 'created_at'),  # For time-based queries
    )
    
    def __repr__(self):
        return f"<SemanticKnowledge(id={self.id}, type='{self.knowledge_type}', text='{self.text[:50]}...', success={self.success_score})>"


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

    __table_args__ = (
        Index('idx_re_metrics_query_id', 'query_id'),
        Index('idx_re_metrics_suggestion_id', 'suggestion_id'),
        Index('idx_re_metrics_created_at', 'created_at'),
        Index('idx_re_metrics_final_similarity', 'final_similarity'),
        Index('idx_re_metrics_convergence', 'convergence_achieved'),
        Index('idx_re_metrics_automation_created', 'automation_created'),
    )

    def __repr__(self) -> str:
        return (
            f"<ReverseEngineeringMetrics(id={self.id}, query_id={self.query_id}, "
            f"similarity={self.final_similarity:.2%}, iterations={self.iterations_completed}, "
            f"cost={self.estimated_cost_usd!r})>"
        )


class TrainingRun(Base):
    """Record of soft prompt training jobs."""

    __tablename__ = 'training_runs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(20), nullable=False, default='queued')  # queued, running, completed, failed
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    finished_at = Column(DateTime, nullable=True)
    dataset_size = Column(Integer, nullable=True)
    base_model = Column(String, nullable=True)
    output_dir = Column(String, nullable=True)
    run_identifier = Column(String, nullable=True, unique=True)
    final_loss = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_path = Column(String, nullable=True)
    triggered_by = Column(String, nullable=False, default='admin')

    def __repr__(self) -> str:
        return f"<TrainingRun(id={self.id}, status={self.status}, started_at={self.started_at})>"
    
    # ===== Iteration History (JSON) =====
    iteration_history_json = Column(JSON, nullable=True)  # Full iteration history
    
    __table_args__ = (
        Index('idx_training_runs_status', 'status'),
        Index('idx_training_runs_started_at', 'started_at'),
        Index('idx_training_runs_run_identifier', 'run_identifier'),
    )