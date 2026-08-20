-- HomeIQ PostgreSQL Schema Initialization
-- Run automatically on first boot via /docker-entrypoint-initdb.d/
-- Creates domain-isolated schemas and all tables for the schema-per-domain pattern.
-- All statements are idempotent (IF NOT EXISTS) for safe re-runs.

-- Domain schemas
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS automation;
CREATE SCHEMA IF NOT EXISTS agent;
CREATE SCHEMA IF NOT EXISTS blueprints;
CREATE SCHEMA IF NOT EXISTS energy;
CREATE SCHEMA IF NOT EXISTS devices;
CREATE SCHEMA IF NOT EXISTS memory;
CREATE SCHEMA IF NOT EXISTS patterns;
CREATE SCHEMA IF NOT EXISTS rag;

-- pgvector, required by the memory schema's embedding vector(384) columns and
-- their HNSW indexes. Provided by the pgvector/pgvector:pg17 image pinned in
-- domains/core-platform/compose.yml; this statement fails on stock postgres.
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant full access to the application user
DO $$
BEGIN
    EXECUTE format(
        'GRANT ALL ON SCHEMA core, automation, agent, blueprints, energy, devices, memory, patterns, rag TO %I',
        current_user
    );
END
$$;

-- Set default search_path for the application user.
-- Target the connected database rather than a hardcoded name: CI initializes
-- `homeiq_test`, where `ALTER DATABASE homeiq` errored and left search_path unset.
DO $$
BEGIN
    EXECUTE format(
        'ALTER DATABASE %I SET search_path TO public, core, automation, agent, '
        'blueprints, energy, devices, memory, patterns, rag',
        current_database()
    );
END
$$;

-- =============================================================================
-- Agent schema tables (ha-ai-agent-service)
-- =============================================================================
SET search_path TO agent;

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id VARCHAR(36) PRIMARY KEY,
    state VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    debug_id VARCHAR(36),
    title VARCHAR(200),
    source VARCHAR(20),
    pending_preview JSON
);

CREATE INDEX IF NOT EXISTS ix_conversations_created_at ON conversations (created_at);
CREATE UNIQUE INDEX IF NOT EXISTS ix_conversations_debug_id ON conversations (debug_id);
CREATE INDEX IF NOT EXISTS ix_conversations_source ON conversations (source);
CREATE INDEX IF NOT EXISTS ix_conversations_state ON conversations (state);
CREATE INDEX IF NOT EXISTS ix_conversations_updated_at ON conversations (updated_at);

CREATE TABLE IF NOT EXISTS messages (
    message_id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    tool_calls JSON,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Migration: add tool_calls column if table already exists without it
ALTER TABLE messages ADD COLUMN IF NOT EXISTS tool_calls JSON;

CREATE INDEX IF NOT EXISTS ix_messages_conversation_id ON messages (conversation_id);
CREATE INDEX IF NOT EXISTS ix_messages_created_at ON messages (created_at);

CREATE TABLE IF NOT EXISTS context_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(100) NOT NULL,
    cache_value TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_context_cache_cache_key ON context_cache (cache_key);
CREATE INDEX IF NOT EXISTS ix_context_cache_expires_at ON context_cache (expires_at);

-- =============================================================================
-- Automation schema tables (ai-automation-service-new, ai-pattern-service)
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

-- ai-pattern-service tables
CREATE TABLE IF NOT EXISTS community_patterns (
    id VARCHAR(36) PRIMARY KEY,
    pattern_type VARCHAR(50) NOT NULL,
    device_id VARCHAR(255),
    pattern_metadata JSON NOT NULL,
    description TEXT NOT NULL,
    tags JSON,
    author VARCHAR(255),
    status VARCHAR(20) NOT NULL,
    rating_avg DOUBLE PRECISION NOT NULL,
    rating_count INTEGER NOT NULL,
    download_count INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_community_patterns_pattern_type ON community_patterns (pattern_type);
CREATE INDEX IF NOT EXISTS ix_community_patterns_status ON community_patterns (status);

CREATE TABLE IF NOT EXISTS pattern_ratings (
    id VARCHAR(36) PRIMARY KEY,
    pattern_id VARCHAR(36) NOT NULL REFERENCES community_patterns(id),
    user_id VARCHAR(255),
    rating INTEGER NOT NULL,
    comment TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_pattern_ratings_pattern_id ON pattern_ratings (pattern_id);

-- ai-pattern-service patterns table (device-level behavior patterns).
-- Used by the scheduler at /api/analysis/status for storing detected patterns.
-- Check-then-insert logic (lines 144-196 of src/crud/patterns.py) implies
-- UNIQUE(pattern_type, device_id) — at most one active pattern per type per device.
CREATE TABLE IF NOT EXISTS patterns (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR NOT NULL,
    device_id VARCHAR NOT NULL,
    pattern_metadata JSON NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    occurrences INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (pattern_type, device_id)
);

CREATE INDEX IF NOT EXISTS ix_patterns_device_id ON patterns (device_id);
CREATE INDEX IF NOT EXISTS ix_patterns_pattern_type ON patterns (pattern_type);

CREATE TABLE IF NOT EXISTS synergy_opportunities (
    id SERIAL PRIMARY KEY,
    synergy_id VARCHAR(36) NOT NULL,
    synergy_type VARCHAR(50) NOT NULL,
    device_ids TEXT NOT NULL,
    opportunity_metadata JSON,
    impact_score DOUBLE PRECISION NOT NULL,
    complexity VARCHAR(20) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    area VARCHAR(100),
    -- TIMESTAMPTZ: the CRUD writes aware datetimes; a naive column made
    -- asyncpg refuse every raw-SQL store (TAP-6171 batch).
    created_at TIMESTAMPTZ NOT NULL,
    pattern_support_score DOUBLE PRECISION NOT NULL,
    validated_by_patterns BOOLEAN NOT NULL,
    supporting_pattern_ids TEXT,
    synergy_depth INTEGER NOT NULL DEFAULT 2,
    chain_devices TEXT,
    embedding_similarity DOUBLE PRECISION,
    rerank_score DOUBLE PRECISION,
    final_score DOUBLE PRECISION,
    explanation JSON,
    context_breakdown JSON,
    quality_score DOUBLE PRECISION,
    quality_tier VARCHAR(20),
    last_validated_at TIMESTAMPTZ,
    filter_reason VARCHAR(200)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_synergy_opportunities_synergy_id ON synergy_opportunities (synergy_id);
CREATE INDEX IF NOT EXISTS ix_synergy_opportunities_synergy_type ON synergy_opportunities (synergy_type);

CREATE TABLE IF NOT EXISTS synergy_feedback (
    id SERIAL PRIMARY KEY,
    synergy_id VARCHAR(36) NOT NULL REFERENCES synergy_opportunities(synergy_id),
    feedback_type VARCHAR(20) NOT NULL,
    feedback_data JSON NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_synergy_feedback_created_at ON synergy_feedback (created_at);
CREATE INDEX IF NOT EXISTS ix_synergy_feedback_feedback_type ON synergy_feedback (feedback_type);
CREATE INDEX IF NOT EXISTS ix_synergy_feedback_synergy_id ON synergy_feedback (synergy_id);

-- ai-pattern-service ML tables (Stories 40.1, 40.7). These were declared in
-- ai-pattern-service/src/database/models.py but never provisioned here, so every
-- read through model_registry or the training-data writer hit an undefined table.
CREATE TABLE IF NOT EXISTS pattern_training_data (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(36) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    device_id VARCHAR(255),
    raw_events_summary JSON NOT NULL,
    detected_pattern JSON NOT NULL,
    user_action VARCHAR(20),
    user_feedback_at TIMESTAMP,
    confidence DOUBLE PRECISION NOT NULL,
    ml_model_version VARCHAR(50),
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_pattern_training_data_run_id ON pattern_training_data (run_id);
CREATE INDEX IF NOT EXISTS ix_pattern_training_data_pattern_type ON pattern_training_data (pattern_type);
CREATE INDEX IF NOT EXISTS ix_pattern_training_data_user_action ON pattern_training_data (user_action);
CREATE INDEX IF NOT EXISTS ix_pattern_training_data_created_at ON pattern_training_data (created_at);

CREATE TABLE IF NOT EXISTS ml_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    metrics JSON,
    metadata JSON,
    trained_at TIMESTAMP NOT NULL,
    is_active BOOLEAN NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_ml_models_model_name ON ml_models (model_name);
CREATE INDEX IF NOT EXISTS ix_ml_models_is_active ON ml_models (is_active);

-- =============================================================================
-- Blueprints schema tables (blueprint-index, blueprint-suggestion, automation-miner)
-- =============================================================================
SET search_path TO blueprints;

CREATE TABLE IF NOT EXISTS indexed_blueprints (
    id VARCHAR(255) PRIMARY KEY,
    source_url VARCHAR(1024) NOT NULL UNIQUE,
    source_type VARCHAR(50) NOT NULL,
    source_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    domain VARCHAR(50),
    -- JSONB, not JSON: search filters use containment (@>), which plain
    -- json lacks -- .contains() compiled to `json ~~ text` and every
    -- domain/device-class search failed at runtime (TAP-6170 batch).
    required_domains JSONB,
    required_device_classes JSONB,
    optional_domains JSONB,
    optional_device_classes JSONB,
    inputs JSONB,
    trigger_platforms JSONB,
    action_services JSONB,
    use_case VARCHAR(50),
    tags JSONB,
    stars INTEGER,
    downloads INTEGER,
    installs INTEGER,
    community_rating DOUBLE PRECISION,
    vote_count INTEGER,
    quality_score DOUBLE PRECISION,
    complexity VARCHAR(20),
    has_description BOOLEAN,
    has_inputs BOOLEAN,
    author VARCHAR(255),
    ha_min_version VARCHAR(20),
    ha_max_version VARCHAR(20),
    blueprint_version VARCHAR(20),
    -- TIMESTAMPTZ: the writers send aware datetimes; naive columns made
    -- asyncpg refuse every insert (TAP-6170).
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    indexed_at TIMESTAMPTZ,
    last_checked_at TIMESTAMPTZ,
    yaml_content TEXT
);

CREATE INDEX IF NOT EXISTS ix_blueprints_domain ON indexed_blueprints (domain);
CREATE INDEX IF NOT EXISTS ix_blueprints_quality_score ON indexed_blueprints (quality_score);
CREATE INDEX IF NOT EXISTS ix_blueprints_source_type ON indexed_blueprints (source_type);
CREATE INDEX IF NOT EXISTS ix_blueprints_use_case ON indexed_blueprints (use_case);

CREATE TABLE IF NOT EXISTS blueprint_inputs (
    id VARCHAR(255) PRIMARY KEY,
    blueprint_id VARCHAR(255) NOT NULL REFERENCES indexed_blueprints(id) ON DELETE CASCADE,
    input_name VARCHAR(255) NOT NULL,
    input_type VARCHAR(50),
    description TEXT,
    domain VARCHAR(50),
    device_class VARCHAR(50),
    selector_type VARCHAR(50),
    selector_config JSON,
    default_value TEXT,
    is_required BOOLEAN
);

CREATE INDEX IF NOT EXISTS ix_inputs_blueprint_id ON blueprint_inputs (blueprint_id);
CREATE INDEX IF NOT EXISTS ix_inputs_domain ON blueprint_inputs (domain);

CREATE TABLE IF NOT EXISTS blueprint_suggestions (
    id VARCHAR PRIMARY KEY,
    blueprint_id VARCHAR NOT NULL,
    blueprint_name VARCHAR,
    blueprint_description TEXT,
    suggestion_score DOUBLE PRECISION NOT NULL,
    matched_devices JSON NOT NULL,
    use_case VARCHAR,
    status VARCHAR,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    accepted_at TIMESTAMP,
    declined_at TIMESTAMP,
    conversation_id VARCHAR
);

CREATE INDEX IF NOT EXISTS ix_blueprint_suggestions_blueprint_id ON blueprint_suggestions (blueprint_id);
CREATE INDEX IF NOT EXISTS ix_blueprint_suggestions_status ON blueprint_suggestions (status);

CREATE TABLE IF NOT EXISTS community_automations (
    id SERIAL PRIMARY KEY,
    source VARCHAR(20) NOT NULL,
    source_id VARCHAR(200) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    devices JSON NOT NULL,
    integrations JSON NOT NULL,
    triggers JSON NOT NULL,
    conditions JSON,
    actions JSON NOT NULL,
    use_case VARCHAR(20) NOT NULL,
    complexity VARCHAR(10) NOT NULL,
    quality_score DOUBLE PRECISION NOT NULL,
    vote_count INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    last_crawled TIMESTAMP NOT NULL,
    extra_metadata JSON,
    is_blueprint BOOLEAN NOT NULL,
    CONSTRAINT uq_source_source_id UNIQUE (source, source_id)
);

CREATE INDEX IF NOT EXISTS ix_community_automations_source ON community_automations (source);
CREATE INDEX IF NOT EXISTS ix_community_automations_use_case ON community_automations (use_case);
CREATE INDEX IF NOT EXISTS ix_community_automations_quality_score ON community_automations (quality_score);

CREATE TABLE IF NOT EXISTS indexing_jobs (
    id VARCHAR(255) PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20),
    total_items INTEGER,
    processed_items INTEGER,
    indexed_items INTEGER,
    failed_items INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP,
    error_message TEXT,
    error_details JSON,
    config JSON
);

CREATE TABLE IF NOT EXISTS miner_state (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- =============================================================================
-- Core schema tables (data-api, websocket-ingestion)
-- =============================================================================
SET search_path TO core;

CREATE TABLE IF NOT EXISTS automations (
    automation_id VARCHAR PRIMARY KEY,
    alias VARCHAR,
    description TEXT,
    mode VARCHAR,
    enabled BOOLEAN,
    total_executions INTEGER,
    total_errors INTEGER,
    avg_duration_seconds DOUBLE PRECISION,
    success_rate DOUBLE PRECISION,
    last_triggered TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_core_automations_alias ON automations (alias);

CREATE TABLE IF NOT EXISTS automation_executions (
    id SERIAL PRIMARY KEY,
    automation_id VARCHAR REFERENCES automations(automation_id) ON DELETE CASCADE,
    run_id VARCHAR,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    duration_seconds DOUBLE PRECISION,
    execution_result VARCHAR,
    trigger_type VARCHAR,
    trigger_entity VARCHAR,
    error_message TEXT,
    step_count INTEGER,
    last_step VARCHAR,
    context_id VARCHAR
);

CREATE INDEX IF NOT EXISTS idx_execution_automation_started ON automation_executions (automation_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_execution_result ON automation_executions (execution_result);
CREATE UNIQUE INDEX IF NOT EXISTS ix_core_automation_executions_run_id ON automation_executions (run_id);
CREATE INDEX IF NOT EXISTS ix_core_automation_executions_started_at ON automation_executions (started_at);

CREATE TABLE IF NOT EXISTS devices (
    device_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    name_by_user VARCHAR,
    manufacturer VARCHAR,
    model VARCHAR,
    sw_version VARCHAR,
    area_id VARCHAR,
    integration VARCHAR,
    entry_type VARCHAR,
    configuration_url VARCHAR,
    suggested_area VARCHAR,
    labels JSONB,
    serial_number VARCHAR,
    model_id VARCHAR,
    config_entry_id VARCHAR,
    via_device VARCHAR REFERENCES devices(device_id),
    device_type VARCHAR,
    device_category VARCHAR,
    power_consumption_idle_w DOUBLE PRECISION,
    power_consumption_active_w DOUBLE PRECISION,
    power_consumption_max_w DOUBLE PRECISION,
    infrared_codes_json TEXT,
    setup_instructions_url VARCHAR,
    troubleshooting_notes TEXT,
    device_features_json TEXT,
    community_rating DOUBLE PRECISION,
    last_capability_sync TIMESTAMP,
    last_seen TIMESTAMP,
    created_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_core_devices_area_id ON devices (area_id);
CREATE INDEX IF NOT EXISTS ix_core_devices_integration ON devices (integration);
CREATE INDEX IF NOT EXISTS ix_core_devices_device_type ON devices (device_type);
CREATE INDEX IF NOT EXISTS ix_core_devices_device_category ON devices (device_category);
CREATE INDEX IF NOT EXISTS ix_core_devices_config_entry_id ON devices (config_entry_id);
CREATE INDEX IF NOT EXISTS ix_core_devices_via_device ON devices (via_device);

CREATE TABLE IF NOT EXISTS entities (
    entity_id VARCHAR PRIMARY KEY,
    device_id VARCHAR REFERENCES devices(device_id) ON DELETE CASCADE,
    domain VARCHAR NOT NULL,
    platform VARCHAR,
    unique_id VARCHAR,
    area_id VARCHAR,
    disabled BOOLEAN,
    name VARCHAR,
    name_by_user VARCHAR,
    original_name VARCHAR,
    friendly_name VARCHAR,
    supported_features INTEGER,
    capabilities JSONB,
    available_services JSONB,
    icon VARCHAR,
    original_icon VARCHAR,
    device_class VARCHAR,
    unit_of_measurement VARCHAR,
    aliases JSONB,
    labels JSONB,
    options JSONB,
    config_entry_id VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_core_entities_area_id ON entities (area_id);
CREATE INDEX IF NOT EXISTS ix_core_entities_device_id ON entities (device_id);
CREATE INDEX IF NOT EXISTS ix_core_entities_domain ON entities (domain);
CREATE INDEX IF NOT EXISTS ix_core_entities_device_class ON entities (device_class);
CREATE INDEX IF NOT EXISTS ix_core_entities_friendly_name ON entities (friendly_name);

CREATE TABLE IF NOT EXISTS services (
    domain VARCHAR NOT NULL,
    service_name VARCHAR NOT NULL,
    name VARCHAR,
    description VARCHAR,
    fields JSON,
    target JSON,
    last_updated TIMESTAMP,
    PRIMARY KEY (domain, service_name)
);

CREATE INDEX IF NOT EXISTS idx_services_domain ON services (domain);

CREATE TABLE IF NOT EXISTS statistics_meta (
    statistic_id VARCHAR PRIMARY KEY,
    source VARCHAR NOT NULL,
    unit_of_measurement VARCHAR,
    state_class VARCHAR,
    has_mean BOOLEAN,
    has_sum BOOLEAN,
    last_reset TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_core_statistics_meta_state_class ON statistics_meta (state_class);

CREATE TABLE IF NOT EXISTS user_team_preferences (
    user_id VARCHAR(50) PRIMARY KEY,
    nfl_teams JSON NOT NULL,
    nhl_teams JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- Devices schema tables (device-intelligence-service, device-health-monitor,
-- ha-setup-service, device-context-classifier)
-- =============================================================================
SET search_path TO devices;

CREATE TABLE IF NOT EXISTS devices (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    manufacturer VARCHAR,
    model VARCHAR,
    area_id VARCHAR,
    area_name VARCHAR,
    integration VARCHAR NOT NULL,
    sw_version VARCHAR,
    hw_version VARCHAR,
    power_source VARCHAR,
    via_device_id VARCHAR,
    ha_device_id VARCHAR,
    zigbee_device_id VARCHAR,
    last_seen TIMESTAMPTZ,
    health_score INTEGER,
    disabled_by VARCHAR,
    device_class VARCHAR,
    config_entry_id VARCHAR,
    connections_json TEXT,
    identifiers_json TEXT,
    zigbee_ieee VARCHAR,
    is_battery_powered BOOLEAN NOT NULL,
    lqi INTEGER,
    lqi_updated_at TIMESTAMPTZ,
    availability_status VARCHAR,
    availability_updated_at TIMESTAMPTZ,
    battery_level INTEGER,
    battery_low BOOLEAN,
    battery_updated_at TIMESTAMPTZ,
    device_type VARCHAR,
    source VARCHAR,
    name_by_user VARCHAR,
    suggested_area VARCHAR,
    entry_type VARCHAR,
    configuration_url VARCHAR,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_devices_area_id ON devices (area_id);
CREATE INDEX IF NOT EXISTS ix_devices_availability_status ON devices (availability_status);
CREATE INDEX IF NOT EXISTS ix_devices_battery_low ON devices (battery_low);
CREATE INDEX IF NOT EXISTS ix_devices_config_entry_id ON devices (config_entry_id);
CREATE INDEX IF NOT EXISTS ix_devices_device_class ON devices (device_class);
CREATE INDEX IF NOT EXISTS ix_devices_health_score ON devices (health_score);
CREATE INDEX IF NOT EXISTS ix_devices_integration ON devices (integration);
CREATE INDEX IF NOT EXISTS ix_devices_source ON devices (source);
CREATE INDEX IF NOT EXISTS ix_devices_zigbee_ieee ON devices (zigbee_ieee);

CREATE TABLE IF NOT EXISTS device_entities (
    entity_id VARCHAR PRIMARY KEY,
    device_id VARCHAR REFERENCES devices(id) ON DELETE CASCADE,
    name VARCHAR,
    original_name VARCHAR,
    platform VARCHAR NOT NULL,
    domain VARCHAR NOT NULL,
    disabled_by VARCHAR,
    entity_category VARCHAR,
    hidden_by VARCHAR,
    has_entity_name BOOLEAN NOT NULL,
    original_icon VARCHAR,
    unique_id VARCHAR NOT NULL,
    translation_key VARCHAR,
    -- Label ids from the entity registry. HA returns these on every
    -- config/entity_registry/list; the sync dropped them while the naming rubric
    -- scores `labels` at +20, so every entity silently lost a fifth of its score
    -- for data HomeIQ had already fetched.
    labels JSON,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_device_entities_device_id ON device_entities (device_id);
CREATE INDEX IF NOT EXISTS ix_device_entities_domain ON device_entities (domain);

-- The durable key. `entity_id` is the PRIMARY KEY above, but it is an ADDRESS,
-- not an identity: HA mints it from a name at pairing and moves it whenever the
-- entity is renamed or re-paired. Keying the sync on it meant a rename inserted
-- a SECOND row and orphaned every finding hanging off the old address.
--
-- This tuple is HA's own registry key. `EntityRegistryItems` maintains the index
-- (domain, platform, unique_id) -> entity_id, and the entity registry docstring
-- states entities "are uniquely identified by their domain, platform and a
-- unique id provided by that platform". `unique_id` ALONE is not unique and a
-- UNIQUE index on it cannot be created here: on this instance 21 pairs share one
-- (e.g. `core_ssh_state` belongs to both switch.terminal_ssh and
-- binary_sensor.terminal_ssh_running). With `domain` populated correctly the
-- tuple is unique across all 768 rows.
CREATE UNIQUE INDEX IF NOT EXISTS ux_device_entities_registry_key
    ON device_entities (domain, platform, unique_id);

CREATE TABLE IF NOT EXISTS device_capabilities (
    device_id VARCHAR NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    capability_name VARCHAR NOT NULL,
    capability_type VARCHAR NOT NULL,
    properties JSON,
    exposed BOOLEAN NOT NULL,
    configured BOOLEAN NOT NULL,
    source VARCHAR NOT NULL,
    last_updated TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (device_id, capability_name)
);

CREATE INDEX IF NOT EXISTS ix_device_capabilities_capability_type ON device_capabilities (capability_type);

CREATE TABLE IF NOT EXISTS device_health_metrics (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    metric_name VARCHAR NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    metric_unit VARCHAR,
    metadata_json JSON,
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_device_health_metrics_device_id ON device_health_metrics (device_id);
CREATE INDEX IF NOT EXISTS ix_device_health_metrics_metric_name ON device_health_metrics (metric_name);
CREATE INDEX IF NOT EXISTS ix_device_health_metrics_timestamp ON device_health_metrics (timestamp);

CREATE TABLE IF NOT EXISTS device_hygiene_issues (
    id SERIAL PRIMARY KEY,
    issue_key VARCHAR NOT NULL,
    issue_type VARCHAR NOT NULL,
    severity VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    device_id VARCHAR REFERENCES devices(id) ON DELETE SET NULL,
    entity_id VARCHAR REFERENCES device_entities(entity_id) ON UPDATE CASCADE ON DELETE SET NULL,
    name VARCHAR,
    suggested_action VARCHAR,
    suggested_value VARCHAR,
    summary TEXT,
    metadata_json JSON,
    detected_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_device_hygiene_issues_issue_key ON device_hygiene_issues (issue_key);
CREATE INDEX IF NOT EXISTS ix_device_hygiene_issues_device_id ON device_hygiene_issues (device_id);
CREATE INDEX IF NOT EXISTS ix_device_hygiene_issues_issue_type ON device_hygiene_issues (issue_type);
CREATE INDEX IF NOT EXISTS ix_device_hygiene_issues_severity ON device_hygiene_issues (severity);
CREATE INDEX IF NOT EXISTS ix_device_hygiene_issues_status ON device_hygiene_issues (status);

CREATE TABLE IF NOT EXISTS device_relationships (
    id SERIAL PRIMARY KEY,
    source_device_id VARCHAR NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    target_device_id VARCHAR NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    relationship_type VARCHAR NOT NULL,
    strength DOUBLE PRECISION NOT NULL,
    metadata_json JSON,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_device_relationships_source_device_id ON device_relationships (source_device_id);
CREATE INDEX IF NOT EXISTS ix_device_relationships_target_device_id ON device_relationships (target_device_id);

CREATE TABLE IF NOT EXISTS discovery_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR NOT NULL UNIQUE,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status VARCHAR NOT NULL,
    devices_discovered INTEGER NOT NULL,
    capabilities_discovered INTEGER NOT NULL,
    errors JSON,
    metadata_json JSON
);

CREATE TABLE IF NOT EXISTS cache_stats (
    id SERIAL PRIMARY KEY,
    cache_type VARCHAR NOT NULL,
    hit_count INTEGER NOT NULL,
    miss_count INTEGER NOT NULL,
    total_requests INTEGER NOT NULL,
    hit_rate DOUBLE PRECISION NOT NULL,
    memory_usage VARCHAR,
    key_count INTEGER NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_cache_stats_timestamp ON cache_stats (timestamp);

CREATE TABLE IF NOT EXISTS environment_health (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    health_score INTEGER NOT NULL,
    ha_status VARCHAR NOT NULL,
    ha_version VARCHAR,
    integrations_status JSON NOT NULL,
    performance_metrics JSON NOT NULL,
    issues_detected JSON
);

CREATE INDEX IF NOT EXISTS ix_environment_health_timestamp ON environment_health (timestamp);

CREATE TABLE IF NOT EXISTS integration_health (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    integration_name VARCHAR NOT NULL,
    integration_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    is_configured BOOLEAN,
    is_connected BOOLEAN,
    error_message VARCHAR,
    last_check TIMESTAMPTZ,
    check_details JSON
);

CREATE INDEX IF NOT EXISTS ix_integration_health_integration_name ON integration_health (integration_name);
CREATE INDEX IF NOT EXISTS ix_integration_health_timestamp ON integration_health (timestamp);

CREATE TABLE IF NOT EXISTS name_preferences (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR NOT NULL,
    pattern_data TEXT,
    confidence DOUBLE PRECISION NOT NULL,
    learned_from_count INTEGER NOT NULL,
    last_updated TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_name_preferences_pattern_type ON name_preferences (pattern_type);

CREATE TABLE IF NOT EXISTS name_suggestions (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    entity_id VARCHAR REFERENCES device_entities(entity_id) ON UPDATE CASCADE ON DELETE CASCADE,
    original_name VARCHAR NOT NULL,
    suggested_name VARCHAR NOT NULL,
    confidence_score DOUBLE PRECISION,
    suggestion_source VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    reasoning TEXT,
    suggested_at TIMESTAMP NOT NULL,
    reviewed_at TIMESTAMP,
    user_feedback VARCHAR
);

CREATE INDEX IF NOT EXISTS ix_name_suggestions_device_id ON name_suggestions (device_id);
CREATE INDEX IF NOT EXISTS ix_name_suggestions_entity_id ON name_suggestions (entity_id);

CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metric_type VARCHAR NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    component VARCHAR,
    metric_metadata JSON
);

CREATE INDEX IF NOT EXISTS ix_performance_metrics_metric_type ON performance_metrics (metric_type);
CREATE INDEX IF NOT EXISTS ix_performance_metrics_timestamp ON performance_metrics (timestamp);

CREATE TABLE IF NOT EXISTS setup_wizard_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    integration_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    steps_completed INTEGER,
    total_steps INTEGER NOT NULL,
    current_step VARCHAR,
    configuration JSON,
    error_log JSON,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_setup_wizard_sessions_session_id ON setup_wizard_sessions (session_id);

CREATE TABLE IF NOT EXISTS team_tracker_integration (
    id SERIAL PRIMARY KEY,
    is_installed BOOLEAN NOT NULL,
    installation_status VARCHAR NOT NULL,
    version VARCHAR,
    last_checked TIMESTAMPTZ NOT NULL,
    metadata_json JSON,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS team_tracker_teams (
    id SERIAL PRIMARY KEY,
    team_id VARCHAR NOT NULL,
    league_id VARCHAR NOT NULL,
    team_name VARCHAR NOT NULL,
    team_long_name VARCHAR,
    entity_id VARCHAR,
    sensor_name VARCHAR,
    is_active BOOLEAN NOT NULL,
    sport VARCHAR,
    team_abbreviation VARCHAR,
    team_logo VARCHAR,
    league_logo VARCHAR,
    configured_in_ha BOOLEAN NOT NULL,
    last_detected TIMESTAMPTZ,
    user_notes TEXT,
    priority INTEGER NOT NULL,
    metadata_json JSON,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_team_tracker_teams_entity_id ON team_tracker_teams (entity_id);
CREATE INDEX IF NOT EXISTS ix_team_tracker_teams_league_id ON team_tracker_teams (league_id);

CREATE TABLE IF NOT EXISTS zigbee_device_metadata (
    device_id VARCHAR PRIMARY KEY REFERENCES devices(id) ON DELETE CASCADE,
    ieee_address VARCHAR NOT NULL,
    model_id VARCHAR,
    manufacturer_code VARCHAR,
    date_code VARCHAR,
    hardware_version VARCHAR,
    software_build_id VARCHAR,
    network_address INTEGER,
    supported BOOLEAN NOT NULL,
    interview_completed BOOLEAN NOT NULL,
    definition_json JSON,
    settings_json JSON,
    last_seen_zigbee TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_zigbee_device_metadata_ieee_address ON zigbee_device_metadata (ieee_address);

-- -----------------------------------------------------------------------------
-- Device knowledge claims (device-intelligence-service)
-- Provenance-bearing facts about a device MODEL (vendor knowledge) or a device
-- INSTANCE (measurements on this home's hardware). Evidence class is ordered:
--   measured > upstream_source > vendor_doc > community > inferred
-- Precedence and supersession are enforced by the service, not by the client.
-- See docs/architecture/adr-device-knowledge-provenance.md
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS device_knowledge_claims (
    id SERIAL PRIMARY KEY,
    subject_kind VARCHAR(16) NOT NULL,
    subject_key VARCHAR(255) NOT NULL,
    fact_key VARCHAR(255) NOT NULL,
    fact_value TEXT NOT NULL,
    claim_type VARCHAR(16) NOT NULL DEFAULT 'known',
    caveat TEXT,
    evidence_class VARCHAR(24) NOT NULL,
    source_url TEXT,
    source_ref TEXT,
    source_version VARCHAR(255),
    source_quote TEXT,
    method VARCHAR(255),
    confidence DOUBLE PRECISION,
    firmware_min VARCHAR(32),
    firmware_max VARCHAR(32),
    recorded_by VARCHAR(128) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    superseded_by INTEGER REFERENCES device_knowledge_claims(id) ON DELETE SET NULL,
    superseded_reason TEXT,
    CONSTRAINT chk_dk_subject_kind CHECK (subject_kind IN ('model', 'instance')),
    CONSTRAINT chk_dk_evidence_class CHECK (
        evidence_class IN ('measured', 'upstream_source', 'vendor_doc', 'community', 'inferred')
    ),
    CONSTRAINT chk_dk_claim_type CHECK (claim_type IN ('known', 'not_claimed')),
    CONSTRAINT chk_dk_confidence_range CHECK (
        confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)
    )
);

CREATE INDEX IF NOT EXISTS idx_dk_subject ON device_knowledge_claims (subject_kind, subject_key);
CREATE INDEX IF NOT EXISTS idx_dk_subject_fact ON device_knowledge_claims (subject_kind, subject_key, fact_key);
CREATE INDEX IF NOT EXISTS ix_device_knowledge_claims_evidence_class ON device_knowledge_claims (evidence_class);
CREATE INDEX IF NOT EXISTS ix_device_knowledge_claims_superseded_by ON device_knowledge_claims (superseded_by);
CREATE INDEX IF NOT EXISTS ix_device_knowledge_claims_recorded_at ON device_knowledge_claims (recorded_at);

-- =============================================================================
-- Energy schema tables (proactive-agent-service)
-- =============================================================================
SET search_path TO energy;

CREATE TABLE IF NOT EXISTS suggestions (
    id VARCHAR(36) PRIMARY KEY,
    prompt TEXT NOT NULL,
    context_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    quality_score DOUBLE PRECISION NOT NULL,
    context_metadata JSON NOT NULL,
    prompt_metadata JSON NOT NULL,
    agent_response JSON,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_suggestions_context_type ON suggestions (context_type);
CREATE INDEX IF NOT EXISTS ix_suggestions_status ON suggestions (status);
CREATE INDEX IF NOT EXISTS ix_suggestions_created_at ON suggestions (created_at);

CREATE TABLE IF NOT EXISTS invalid_suggestion_reports (
    id VARCHAR(36) PRIMARY KEY,
    suggestion_id VARCHAR(36) NOT NULL REFERENCES suggestions(id) ON DELETE CASCADE,
    reason VARCHAR(50) NOT NULL,
    feedback TEXT,
    reported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_invalid_suggestion_reports_suggestion_id ON invalid_suggestion_reports (suggestion_id);
CREATE INDEX IF NOT EXISTS ix_invalid_suggestion_reports_reason ON invalid_suggestion_reports (reason);

CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    cron_expression VARCHAR(100) NOT NULL,
    prompt TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    notification_preference VARCHAR(20) NOT NULL DEFAULT 'never',
    cooldown_minutes INTEGER NOT NULL DEFAULT 60,
    max_execution_seconds INTEGER NOT NULL DEFAULT 120,
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    run_count INTEGER NOT NULL DEFAULT 0,
    is_template BOOLEAN NOT NULL DEFAULT FALSE,
    template_id VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sched_tasks_enabled ON scheduled_tasks (enabled);
CREATE INDEX IF NOT EXISTS idx_sched_tasks_next_run ON scheduled_tasks (enabled, next_run_at);

CREATE TABLE IF NOT EXISTS task_executions (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES scheduled_tasks(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    prompt TEXT NOT NULL,
    response TEXT,
    tools_used TEXT,
    error TEXT,
    duration_ms INTEGER,
    notification_sent BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_task_exec_task_started ON task_executions (task_id, started_at);
CREATE INDEX IF NOT EXISTS idx_task_exec_status ON task_executions (status);

-- =============================================================================
-- Memory schema tables (admin-api /api/v1/memories, via libs/homeiq-memory)
--
-- Mirrors libs/homeiq-memory/alembic/versions/001_create_memory_schema.py, which
-- nothing in this repo ever runs: homeiq-memory has an alembic.ini but no service
-- invokes it, and MemoryClient.initialize() defaults to create_tables=False. The
-- DDL therefore has to live here, the one provisioning path actually wired up.
-- Keep this section and that migration in step (TAP-5437).
--
-- Note the ", public" below: CREATE EXTENSION put the vector type and the
-- vector_cosine_ops operator class in public, and SET search_path replaces the
-- path rather than prepending to it. Dropping public here makes vector(384) fail
-- to resolve. Every other section can use a bare schema because it only uses
-- built-in types from pg_catalog, which is always implicitly in scope.
-- =============================================================================
SET search_path TO memory, public;

CREATE TABLE IF NOT EXISTS memories (
    id BIGSERIAL PRIMARY KEY,
    content VARCHAR(1024) NOT NULL,
    memory_type VARCHAR(20) NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 0.5,
    source_channel VARCHAR(20) NOT NULL,
    source_service VARCHAR(50),
    entity_ids TEXT[],
    area_ids TEXT[],
    domain VARCHAR(30),
    tags TEXT[],
    embedding vector(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0,
    superseded_by BIGINT REFERENCES memories(id) ON DELETE SET NULL,
    metadata JSONB,
    CONSTRAINT chk_memory_type CHECK (
        memory_type IN ('behavioral', 'preference', 'boundary', 'outcome', 'routine')
    )
);

CREATE TABLE IF NOT EXISTS memory_archive (
    id BIGSERIAL PRIMARY KEY,
    original_id BIGINT NOT NULL,
    content VARCHAR(1024) NOT NULL,
    memory_type VARCHAR(20) NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 0.5,
    source_channel VARCHAR(20) NOT NULL,
    source_service VARCHAR(50),
    entity_ids TEXT[],
    area_ids TEXT[],
    domain VARCHAR(30),
    tags TEXT[],
    embedding vector(384),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    last_accessed TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0,
    superseded_by BIGINT,
    metadata JSONB,
    archived_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archive_reason VARCHAR(100),
    CONSTRAINT chk_archive_memory_type CHECK (
        memory_type IN ('behavioral', 'preference', 'boundary', 'outcome', 'routine')
    )
);

CREATE INDEX IF NOT EXISTS idx_memories_fts ON memories USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_memories_type_conf ON memories (memory_type, confidence DESC);
CREATE INDEX IF NOT EXISTS idx_memories_entities ON memories USING gin(entity_ids);
CREATE INDEX IF NOT EXISTS idx_memories_domain ON memories (domain);

-- =============================================================================
-- Patterns schema tables (api-automation-edge)
-- =============================================================================
SET search_path TO patterns;

CREATE TABLE IF NOT EXISTS spec_versions (
    id SERIAL PRIMARY KEY,
    spec_id VARCHAR NOT NULL,
    version VARCHAR NOT NULL,
    home_id VARCHAR NOT NULL,
    spec_hash VARCHAR NOT NULL,
    spec_content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    deployed_at TIMESTAMP,
    is_active BOOLEAN
);

CREATE INDEX IF NOT EXISTS ix_spec_versions_home_id ON spec_versions (home_id);
CREATE INDEX IF NOT EXISTS ix_spec_versions_spec_id ON spec_versions (spec_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_spec_versions_spec_hash ON spec_versions (spec_hash);

-- =============================================================================
-- RAG schema tables (rag-service)
-- =============================================================================
SET search_path TO rag;

CREATE TABLE IF NOT EXISTS rag_knowledge (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    embedding JSON NOT NULL,
    knowledge_type VARCHAR NOT NULL,
    metadata JSON,
    success_score DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_type ON rag_knowledge (knowledge_type);
CREATE INDEX IF NOT EXISTS idx_success_score ON rag_knowledge (success_score);
CREATE INDEX IF NOT EXISTS idx_created_at ON rag_knowledge (created_at);

RESET search_path;
