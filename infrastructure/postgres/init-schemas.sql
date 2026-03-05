-- HomeIQ PostgreSQL Schema Initialization
-- Run automatically on first boot via /docker-entrypoint-initdb.d/
-- Creates domain-isolated schemas for the schema-per-domain pattern.

-- Domain schemas
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS automation;
CREATE SCHEMA IF NOT EXISTS agent;
CREATE SCHEMA IF NOT EXISTS blueprints;
CREATE SCHEMA IF NOT EXISTS energy;
CREATE SCHEMA IF NOT EXISTS devices;
CREATE SCHEMA IF NOT EXISTS patterns;
CREATE SCHEMA IF NOT EXISTS rag;

-- Grant full access to the application user
DO $$
BEGIN
    EXECUTE format(
        'GRANT ALL ON SCHEMA core, automation, agent, blueprints, energy, devices, patterns, rag TO %I',
        current_user
    );
END
$$;

-- Set default search_path for the application user
ALTER DATABASE homeiq SET search_path TO public, core, automation, agent, blueprints, energy, devices, patterns, rag;

-- =============================================================================
-- Automation schema tables (ai-automation-service-new)
-- Required for suggestion management, deployment tracking, and hybrid flow
-- =============================================================================
SET search_path TO automation;

CREATE TABLE IF NOT EXISTS suggestions (
    id SERIAL PRIMARY KEY,
    pattern_id INTEGER,
    title VARCHAR NOT NULL,
    description TEXT,
    automation_json JSONB,
    automation_yaml TEXT,
    ha_version VARCHAR,
    json_schema_version VARCHAR,
    status VARCHAR DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    automation_id VARCHAR,
    deployed_at TIMESTAMPTZ,
    confidence_score FLOAT,
    safety_score FLOAT,
    user_feedback VARCHAR,
    feedback_at TIMESTAMPTZ,
    plan_id VARCHAR,
    compiled_id VARCHAR,
    deployment_id VARCHAR
);

CREATE TABLE IF NOT EXISTS automation_versions (
    id SERIAL PRIMARY KEY,
    suggestion_id INTEGER NOT NULL REFERENCES suggestions(id),
    automation_id VARCHAR NOT NULL,
    config_id VARCHAR,
    alias VARCHAR,
    version_number INTEGER NOT NULL,
    automation_json JSONB,
    automation_yaml TEXT NOT NULL,
    ha_version VARCHAR,
    yaml_diff TEXT,
    validation_score FLOAT,
    safety_score FLOAT,
    approval_status VARCHAR,
    approved_by VARCHAR,
    deployed_at TIMESTAMPTZ DEFAULT NOW(),
    deployed_by VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    rollback_reason TEXT,
    snapshot_entities TEXT
);

CREATE TABLE IF NOT EXISTS plans (
    plan_id VARCHAR PRIMARY KEY,
    conversation_id VARCHAR,
    template_id VARCHAR NOT NULL,
    template_version INTEGER NOT NULL,
    parameters JSONB NOT NULL,
    confidence FLOAT NOT NULL,
    clarifications_needed JSONB,
    safety_class VARCHAR NOT NULL,
    explanation TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS compiled_artifacts (
    compiled_id VARCHAR PRIMARY KEY,
    plan_id VARCHAR NOT NULL REFERENCES plans(plan_id),
    template_id VARCHAR,
    area_id VARCHAR,
    yaml TEXT NOT NULL,
    human_summary TEXT NOT NULL,
    diff_summary JSONB,
    risk_notes JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id VARCHAR(255) PRIMARY KEY,
    max_suggestions INTEGER NOT NULL DEFAULT 10,
    creativity_level VARCHAR(50) NOT NULL DEFAULT 'balanced',
    blueprint_preference VARCHAR(50) NOT NULL DEFAULT 'medium',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS deployments (
    deployment_id VARCHAR PRIMARY KEY,
    compiled_id VARCHAR NOT NULL REFERENCES compiled_artifacts(compiled_id),
    ha_automation_id VARCHAR NOT NULL,
    template_id VARCHAR,
    area_id VARCHAR,
    status VARCHAR NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    approved_by VARCHAR,
    ui_source VARCHAR,
    deployed_at TIMESTAMPTZ DEFAULT NOW(),
    audit_data JSONB
);

RESET search_path;
