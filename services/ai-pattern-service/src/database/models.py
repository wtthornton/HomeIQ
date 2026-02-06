"""
Database models for Pattern Service

Epic 39, Story 39.5: Pattern Service Foundation
Phase 3.3: Enhanced with 2025 improvement fields

Note: These models reference tables in the shared database.
The models are defined here for type checking and ORM usage,
but the actual tables are managed by ai-automation-service.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase


# Use the same Base as the main service for shared database
class Base(DeclarativeBase):
    pass


class SynergyOpportunity(Base):
    """
    Cross-device synergy opportunities for automation suggestions.
    
    Stores detected device pairs that could work together but currently
    have no automation connecting them.
    
    Story AI3.1: Device Synergy Detector Foundation
    Epic AI-3: Cross-Device Synergy & Contextual Opportunities
    Phase 3.3: Enhanced with 2025 improvements (explanation, context_breakdown)
    """
    __tablename__ = 'synergy_opportunities'

    id = Column(Integer, primary_key=True)
    synergy_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    synergy_type = Column(String(50), nullable=False, index=True)  # 'device_pair', 'device_chain', etc.
    device_ids = Column(Text, nullable=False)  # JSON array of device IDs
    opportunity_metadata = Column(JSON)  # Synergy-specific data (trigger, action, relationship, etc.)
    impact_score = Column(Float, nullable=False)
    complexity = Column(String(20), nullable=False)  # 'low', 'medium', 'high'
    confidence = Column(Float, nullable=False)
    area = Column(String(100))  # Area/room where devices are located
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Phase 2: Pattern validation fields
    pattern_support_score = Column(Float, default=0.0, nullable=False)
    validated_by_patterns = Column(Boolean, default=False, nullable=False)
    supporting_pattern_ids = Column(Text, nullable=True)  # JSON array of pattern IDs
    
    # Epic AI-4: N-level synergy fields
    synergy_depth = Column(Integer, default=2, nullable=False, server_default='2')
    chain_devices = Column(Text, nullable=True)  # JSON array of entity_ids in automation chain
    embedding_similarity = Column(Float, nullable=True)
    rerank_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)
    
    # 2025 Enhancement: XAI and Multi-modal context (Phase 3.3)
    explanation = Column(JSON, nullable=True)  # XAI explanation (summary, detailed, score_breakdown, evidence, benefits, visualization)
    context_breakdown = Column(JSON, nullable=True)  # Multi-modal context breakdown (temporal_boost, weather_boost, energy_boost, behavior_boost)
    
    # 2025 Enhancement: Quality scoring and filtering (Phase 1)
    quality_score = Column(Float, nullable=True)  # Calculated quality score (0.0-1.0)
    quality_tier = Column(String(20), nullable=True)  # 'high', 'medium', 'low', 'poor'
    last_validated_at = Column(DateTime, nullable=True)  # Last quality validation timestamp
    filter_reason = Column(String(200), nullable=True)  # Reason if filtered (for audit)

    def __repr__(self) -> str:
        validated = "✓" if self.validated_by_patterns else "✗"
        depth = getattr(self, 'synergy_depth', 2)
        return f"<SynergyOpportunity(id={self.id}, type={self.synergy_type}, depth={depth}, area={self.area}, impact={self.impact_score}, validated={validated})>"


class SynergyFeedback(Base):
    """
    User feedback for synergy opportunities (RL feedback loop).
    
    Stores user feedback on synergy recommendations to enable
    reinforcement learning optimization.
    
    Phase 3.3: Created for RL feedback loop (Phase 4.1)
    """
    __tablename__ = 'synergy_feedback'

    id = Column(Integer, primary_key=True)
    synergy_id = Column(String(36), ForeignKey('synergy_opportunities.synergy_id'), nullable=False, index=True)
    feedback_type = Column(String(20), nullable=False, index=True)  # 'accept', 'reject', 'deploy', 'rate'
    feedback_data = Column(JSON, nullable=False)  # Feedback details (rating, comment, accepted, deployed, etc.)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<SynergyFeedback(id={self.id}, synergy_id={self.synergy_id}, type={self.feedback_type})>"


