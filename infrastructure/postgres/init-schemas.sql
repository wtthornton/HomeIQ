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
