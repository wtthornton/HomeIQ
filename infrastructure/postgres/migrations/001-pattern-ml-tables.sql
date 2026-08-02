-- 001-pattern-ml-tables.sql — TAP-5438
--
-- First file in this directory. Migrations here are hand-applied, numbered in
-- apply order, and each must be idempotent so a re-run is harmless.
--
-- Adds automation.pattern_training_data and automation.ml_models.
--
-- Why this file exists separately from init-schemas.sql: that script is mounted at
-- /docker-entrypoint-initdb.d/01-schemas.sql (domains/core-platform/compose.yml:64),
-- and Postgres runs entrypoint scripts ONLY when the data directory is empty. Any
-- deployment whose postgres_data volume already exists will never see a change made
-- there. init-schemas.sql is the source of truth for fresh deployments; this file
-- applies the same change to a live one.
--
-- Both tables were declared in
-- domains/pattern-analysis/ai-pattern-service/src/database/models.py:152-186
-- but were never added to provisioning, so every query through them failed on an
-- undefined table.
--
-- Target schema is `automation` — ai-pattern-service/src/config.py:61 sets
-- database_schema = "automation", which is also where its four sibling tables
-- (community_patterns, pattern_ratings, synergy_opportunities, synergy_feedback)
-- already live.
--
-- Idempotent: safe to re-run. Apply with:
--   docker exec -i homeiq-postgres psql -U homeiq -d homeiq \
--     < infrastructure/postgres/migrations/002-pattern-ml-tables.sql

SET search_path TO automation;

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

RESET search_path;

-- Verification: both rows should report a matching table.
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'automation'
  AND table_name IN ('pattern_training_data', 'ml_models')
ORDER BY table_name;
