"""
Database models for AI Automation Service

Epic 39, Story 39.10: Automation Service Foundation
Shared models with other services (Suggestion, AutomationVersion, etc.)
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Suggestion(Base):
    """Suggestion model - shared with other services"""
    __tablename__ = "suggestions"
    
    id = Column(Integer, primary_key=True, index=True)
    pattern_id = Column(Integer, nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    automation_json = Column(JSON, nullable=True)  # HomeIQ JSON format
    automation_yaml = Column(Text, nullable=True)  # Generated from JSON
    ha_version = Column(String, nullable=True)  # Target Home Assistant version
    json_schema_version = Column(String, nullable=True)  # HomeIQ JSON schema version
    status = Column(String, default="draft")  # draft, refining, yaml_generated, deployed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    automation_id = Column(String, nullable=True)  # HA automation ID after deployment
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Quality metrics
    confidence_score = Column(Float, nullable=True)
    safety_score = Column(Float, nullable=True)
    
    # User feedback
    user_feedback = Column(String, nullable=True)  # approve, reject, modify
    feedback_at = Column(DateTime(timezone=True), nullable=True)
    
    # Hybrid Flow Integration (optional foreign keys)
    plan_id = Column(String, nullable=True, index=True)  # Link to plans table
    compiled_id = Column(String, nullable=True, index=True)  # Link to compiled_artifacts table
    deployment_id = Column(String, nullable=True, index=True)  # Link to deployments table


class AutomationVersion(Base):
    """
    Version history for automations - enables rollback
    
    Epic 51, Story 51.11: Enhanced with diffs, scores, approval tracking, state restoration
    """
    __tablename__ = "automation_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    suggestion_id = Column(Integer, ForeignKey("suggestions.id"), nullable=False)
    automation_id = Column(String, nullable=False)  # HA automation ID (entity_id)
    config_id = Column(String, nullable=True)  # Home Assistant config_id (Epic 51.11)
    alias = Column(String, nullable=True)  # Automation alias for mapping (Epic 51.11)
    version_number = Column(Integer, nullable=False)
    automation_json = Column(JSON, nullable=True)  # HomeIQ JSON format
    automation_yaml = Column(Text, nullable=False)  # Generated from JSON
    ha_version = Column(String, nullable=True)  # HA version when deployed
    yaml_diff = Column(Text, nullable=True)  # Diff from previous version (Epic 51.11)
    validation_score = Column(Float, nullable=True)  # Quality score from validation (Epic 51.11)
    safety_score = Column(Float, nullable=True)
    approval_status = Column(String, nullable=True)  # approved, rejected, pending (Epic 51.11)
    approved_by = Column(String, nullable=True)  # User/API key who approved (Epic 51.11)
    deployed_at = Column(DateTime(timezone=True), server_default=func.now())
    deployed_by = Column(String, nullable=True)  # User/API key identifier
    is_active = Column(Boolean, default=True)  # Current active version
    rollback_reason = Column(Text, nullable=True)  # If rolled back, reason
    snapshot_entities = Column(Text, nullable=True)  # JSON array of entity states for restoration (Epic 51.11)


class Plan(Base):
    """
    Automation plan - structured intent from LLM (template_id + parameters)
    
    Hybrid Flow Implementation: LLM outputs structured plan, not YAML
    """
    __tablename__ = "plans"
    
    plan_id = Column(String, primary_key=True, index=True)
    conversation_id = Column(String, nullable=True, index=True)  # Optional link to conversation
    template_id = Column(String, nullable=False, index=True)
    template_version = Column(Integer, nullable=False)
    parameters = Column(JSON, nullable=False)  # Template parameters
    confidence = Column(Float, nullable=False)  # LLM confidence score (0.0-1.0)
    clarifications_needed = Column(JSON, nullable=True)  # Array of clarification questions
    safety_class = Column(String, nullable=False)  # low, medium, high, critical
    explanation = Column(Text, nullable=True)  # LLM explanation of plan
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class CompiledArtifact(Base):
    """
    Compiled YAML artifact - deterministic compilation from template + plan
    
    Hybrid Flow Implementation: YAML is compiled, not LLM-generated
    """
    __tablename__ = "compiled_artifacts"
    
    compiled_id = Column(String, primary_key=True, index=True)
    plan_id = Column(String, ForeignKey("plans.plan_id"), nullable=False, index=True)
    yaml = Column(Text, nullable=False)  # Generated HA automation YAML
    human_summary = Column(Text, nullable=False)  # Human-readable summary
    diff_summary = Column(JSON, nullable=True)  # Array of change descriptions
    risk_notes = Column(JSON, nullable=True)  # Array of risk warnings
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class Deployment(Base):
    """
    Deployment record - tracks automation deployment to Home Assistant
    
    Hybrid Flow Implementation: Full audit trail for deployments
    """
    __tablename__ = "deployments"
    
    deployment_id = Column(String, primary_key=True, index=True)
    compiled_id = Column(String, ForeignKey("compiled_artifacts.compiled_id"), nullable=False, index=True)
    ha_automation_id = Column(String, nullable=False, index=True)  # HA automation entity ID
    status = Column(String, nullable=False, index=True)  # deployed, failed, rolled_back
    version = Column(Integer, nullable=False, default=1)  # Deployment version
    approved_by = Column(String, nullable=True)  # User/API key who approved
    ui_source = Column(String, nullable=True)  # UI source (ha-agent, automation-ui, etc.)
    deployed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    audit_data = Column(JSON, nullable=True)  # who/when/why/template/version metadata

