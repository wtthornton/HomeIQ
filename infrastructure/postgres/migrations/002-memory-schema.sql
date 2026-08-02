-- 002-memory-schema.sql — TAP-5437
--
-- Creates the memory schema, its two tables, and their indexes on a live database.
-- init-schemas.sql covers fresh deployments; Postgres only runs entrypoint scripts
-- against an empty data directory, so an existing postgres_data volume needs this.
--
-- PREREQUISITE: the postgres container must already be running the
-- pgvector/pgvector:pg17 image. On stock postgres the CREATE EXTENSION below fails
-- and nothing after it applies. Check first:
--   docker inspect --format '{{.Config.Image}}' homeiq-postgres
--
-- Root cause recap: admin-api mounts the memories router (admin-api/src/routes.py:81)
-- and MemoryClient.initialize() only probes SELECT 1 with create_tables defaulting to
-- False (libs/homeiq-memory/client.py:95,128). So the client reports healthy, then the
-- first real query hits memory.memories, which was never created — a 500, not the 503
-- the unavailable-path would have produced.
--
-- Idempotent: safe to re-run. Apply with:
--   docker exec -i homeiq-postgres psql -U homeiq -d homeiq \
--     < infrastructure/postgres/migrations/002-memory-schema.sql
--
-- AFTER the image swap from postgres:17-alpine, run once — Alpine is musl and the
-- pgvector image is glibc, and text-index collation differs between them:
--   docker exec homeiq-postgres psql -U homeiq -d homeiq -c 'REINDEX DATABASE homeiq;'

CREATE SCHEMA IF NOT EXISTS memory;
CREATE EXTENSION IF NOT EXISTS vector;

DO $$
BEGIN
    EXECUTE format('GRANT ALL ON SCHEMA memory TO %I', current_user);
END
$$;

-- ", public" is required: the vector type and vector_cosine_ops operator class
-- live in public, and SET search_path replaces rather than prepends.
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
    tags TEXT[],
    embedding vector(768),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0,
    superseded_by BIGINT REFERENCES memories(id),
    metadata JSONB,
    CONSTRAINT chk_memory_type CHECK (
        memory_type IN ('fact', 'preference', 'pattern', 'context', 'correction')
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
    tags TEXT[],
    embedding vector(768),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    last_accessed TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0,
    superseded_by BIGINT,
    metadata JSONB,
    archived_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archive_reason VARCHAR(100),
    CONSTRAINT chk_archive_memory_type CHECK (
        memory_type IN ('fact', 'preference', 'pattern', 'context', 'correction')
    )
);

CREATE INDEX IF NOT EXISTS idx_memories_fts ON memories USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_memories_type_conf ON memories (memory_type, confidence DESC);
CREATE INDEX IF NOT EXISTS idx_memories_entities ON memories USING gin(entity_ids);

RESET search_path;

-- Verification: expect both tables, and a vector extension row.
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'memory'
ORDER BY table_name;

SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
