-- 003-memory-schema-align-alembic.sql — TAP-5437 follow-up
--
-- Brings an already-provisioned `memory` schema into line with the application
-- ORM. Apply after 002-memory-schema.sql on any database that was provisioned
-- before this file existed.
--
-- WHY THIS EXISTS
--
-- The schema source of truth is libs/homeiq-memory/alembic/versions/, a four-
-- revision chain. Both hand-maintained provisioning paths — init-schemas.sql and
-- 002-memory-schema.sql — were transcribed from revision 001 alone and never
-- picked up 002, 003, or 004. A database created from either therefore had a
-- `memory.memories` the ORM could not query: the first real request died with
-- `column memories.domain does not exist`, surfacing as a 500 rather than a 503.
--
-- The three omitted revisions, and what each one corrects here:
--
--   002_fix_memory_type_enum        The CHECK constraint listed
--                                   fact/preference/pattern/context/correction.
--                                   The MemoryType enum
--                                   (libs/homeiq-memory/src/homeiq_memory/models.py:34-41)
--                                   is behavioral/preference/boundary/outcome/routine —
--                                   only `preference` overlapped, so every write of any
--                                   other type would have violated the constraint.
--
--   003_add_domain_and_fix_fk       `domain VARCHAR(30)` was missing from both tables
--                                   (models.py:106-110, 209-212). This is the column
--                                   whose absence produced the 500. Also gives
--                                   superseded_by the ON DELETE SET NULL the model
--                                   declares (models.py:138-142), so deleting a
--                                   superseding memory no longer orphans the reference.
--
--   004_fix_embedding_dimension_384 embedding was vector(768). The default embedding
--                                   model all-MiniLM-L6-v2 emits 384 dimensions
--                                   (embeddings.py:50,54), so every insert carrying a
--                                   default-generated embedding would have failed on a
--                                   dimension mismatch.
--
-- Idempotent: every step is guarded, so a re-run and a run against an
-- already-correct database are both no-ops. Apply with:
--   docker exec -i homeiq-postgres psql -U homeiq -d homeiq \
--     < infrastructure/postgres/migrations/003-memory-schema-align-alembic.sql
--
-- When a fifth alembic revision lands, mirror it into 002-memory-schema.sql and
-- init-schemas.sql for fresh deployments, and add a corrective step here for
-- existing ones.

-- --- 003_add_domain_and_fix_fk: the domain column ---------------------------

ALTER TABLE memory.memories ADD COLUMN IF NOT EXISTS domain VARCHAR(30);
ALTER TABLE memory.memory_archive ADD COLUMN IF NOT EXISTS domain VARCHAR(30);

CREATE INDEX IF NOT EXISTS idx_memories_domain ON memory.memories (domain);

-- --- 003_add_domain_and_fix_fk: ON DELETE SET NULL on superseded_by ---------
-- Recreated only when the existing constraint lacks the SET NULL action, so a
-- correct database is untouched. confdeltype 'n' is SET NULL; 'a' is NO ACTION.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'memories_superseded_by_fkey'
          AND conrelid = 'memory.memories'::regclass
          AND confdeltype <> 'n'
    ) THEN
        ALTER TABLE memory.memories
            DROP CONSTRAINT memories_superseded_by_fkey;
        ALTER TABLE memory.memories
            ADD CONSTRAINT memories_superseded_by_fkey
            FOREIGN KEY (superseded_by) REFERENCES memory.memories(id)
            ON DELETE SET NULL;
    END IF;
END
$$;

-- --- 002_fix_memory_type_enum: CHECK values ---------------------------------
-- The remap mirrors the alembic revision exactly. It is a no-op on a database
-- that never accepted the old values, which is every database that reached this
-- file, since the old constraint made those writes impossible in the first place.

UPDATE memory.memories SET memory_type = CASE
    WHEN memory_type = 'fact' THEN 'behavioral'
    WHEN memory_type = 'pattern' THEN 'routine'
    WHEN memory_type = 'context' THEN 'outcome'
    WHEN memory_type = 'correction' THEN 'boundary'
    ELSE memory_type
END
WHERE memory_type IN ('fact', 'pattern', 'context', 'correction');

UPDATE memory.memory_archive SET memory_type = CASE
    WHEN memory_type = 'fact' THEN 'behavioral'
    WHEN memory_type = 'pattern' THEN 'routine'
    WHEN memory_type = 'context' THEN 'outcome'
    WHEN memory_type = 'correction' THEN 'boundary'
    ELSE memory_type
END
WHERE memory_type IN ('fact', 'pattern', 'context', 'correction');

ALTER TABLE memory.memories DROP CONSTRAINT IF EXISTS chk_memory_type;
ALTER TABLE memory.memories ADD CONSTRAINT chk_memory_type
    CHECK (memory_type IN ('behavioral', 'preference', 'boundary', 'outcome', 'routine'));

ALTER TABLE memory.memory_archive DROP CONSTRAINT IF EXISTS chk_archive_memory_type;
ALTER TABLE memory.memory_archive ADD CONSTRAINT chk_archive_memory_type
    CHECK (memory_type IN ('behavioral', 'preference', 'boundary', 'outcome', 'routine'));

-- --- 004_fix_embedding_dimension_384: vector width --------------------------
-- Guarded on the current width so a correct database keeps its HNSW index and
-- its embeddings. Where the width is wrong the stored vectors are 768-dim
-- values that no longer match the configured model, so they are cleared for
-- regeneration rather than truncated — the same choice the alembic revision makes.

DO $$
DECLARE
    memories_type TEXT;
    archive_type TEXT;
BEGIN
    SELECT format_type(a.atttypid, a.atttypmod) INTO memories_type
    FROM pg_attribute a
    WHERE a.attrelid = 'memory.memories'::regclass AND a.attname = 'embedding';

    SELECT format_type(a.atttypid, a.atttypmod) INTO archive_type
    FROM pg_attribute a
    WHERE a.attrelid = 'memory.memory_archive'::regclass AND a.attname = 'embedding';

    IF memories_type IS DISTINCT FROM 'vector(384)' THEN
        DROP INDEX IF EXISTS memory.idx_memories_embedding;
        UPDATE memory.memories SET embedding = NULL WHERE embedding IS NOT NULL;
        ALTER TABLE memory.memories ALTER COLUMN embedding TYPE vector(384);
        CREATE INDEX idx_memories_embedding ON memory.memories
            USING hnsw (embedding vector_cosine_ops);
    END IF;

    IF archive_type IS DISTINCT FROM 'vector(384)' THEN
        UPDATE memory.memory_archive SET embedding = NULL WHERE embedding IS NOT NULL;
        ALTER TABLE memory.memory_archive ALTER COLUMN embedding TYPE vector(384);
    END IF;
END
$$;

-- Verification: domain present on both tables, embeddings 384-wide, CHECK
-- constraints carrying the enum values, and the FK set to SET NULL.

SELECT c.relname AS table_name,
       a.attname AS column_name,
       format_type(a.atttypid, a.atttypmod) AS type
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'memory'
  AND c.relname IN ('memories', 'memory_archive')
  AND a.attname IN ('domain', 'embedding')
ORDER BY c.relname, a.attname;

SELECT conname, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE connamespace = 'memory'::regnamespace
  AND conname IN ('chk_memory_type', 'chk_archive_memory_type',
                  'memories_superseded_by_fkey')
ORDER BY conname;
