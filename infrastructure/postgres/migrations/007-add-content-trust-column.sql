-- 007-add-content-trust-column.sql — TAP-7311
--
-- Adds `content_trust` to blueprints.indexed_blueprints for already-populated
-- deployments. init-schemas.sql only fires via CREATE TABLE IF NOT EXISTS, so
-- a deployment that already ran init before this change never sees the new
-- column; this migration is what closes that gap.
--
-- DEFAULT 'untrusted' backfills every existing row before the NOT NULL
-- constraint is applied -- PostgreSQL populates the column for pre-existing
-- rows from the DEFAULT clause in the same ALTER TABLE statement, so this
-- never rejects rows the way a bare NOT NULL with no default would.
--
-- Idempotent: IF NOT EXISTS makes a second run a no-op.

SET search_path TO blueprints;

ALTER TABLE indexed_blueprints
    ADD COLUMN IF NOT EXISTS content_trust VARCHAR(20) NOT NULL DEFAULT 'untrusted';
