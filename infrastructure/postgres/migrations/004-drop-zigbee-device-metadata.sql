-- 004-drop-zigbee-device-metadata.sql — TAP-6401
--
-- Drops `devices.zigbee_device_metadata`. Apply to any database provisioned
-- before this file existed; fresh databases never create the table, because the
-- CREATE block was removed from init-schemas.sql in the same commit.
--
-- The two mechanisms cannot fight: `IF EXISTS` makes this a no-op wherever
-- init-schemas.sql already stopped creating the table, and the real cleanup
-- everywhere else.
--
-- WHY THIS EXISTS
--
-- The table stored Zigbee2MQTT bridge payloads. Zigbee on this deployment is
-- Home Assistant's built-in ZHA on an SMLIGHT coordinator, and the MQTT/Z2M
-- path was excised on 2026-08-20 — including `_store_zigbee_metadata`, the only
-- thing that ever wrote here. The columns mirror Z2M's bridge JSON and do not
-- map onto ZHA's cluster model, so keeping the table preserved no optionality;
-- it preserved a decoy that reads like a Zigbee feature nobody has finished.
--
-- A previous pass declined the drop citing "drop-migration blast radius". That
-- objection had force only while the row and reference counts were unverified,
-- because blast radius is exactly what those counts measure. Verified at
-- decision time, 2026-08-21:
--
--   rows                          0
--   inbound foreign keys          0   (nothing references this table)
--   outbound foreign keys         1   (device_id -> devices.devices, dropped with the table)
--   views / matviews referencing  0
--   producers in the codebase     0
--   readers in the codebase       0
--   full-text hits repo-wide      3 code sites, all removed in this commit
--
-- NOT `CASCADE`, deliberately. The one FK lives ON this table and goes away with
-- it, so CASCADE buys nothing — and it would silently drop any dependent object
-- an audit had missed, where a plain DROP fails loudly with "cannot drop table
-- because other objects depend on it". Views are the classic miss, since they do
-- not appear in a foreign-key query. Keep the failure loud: if this errors,
-- re-audit rather than adding CASCADE.
--
-- NO DOWN MIGRATION, deliberately. Recreating an empty table would restore shape
-- but not function — the code that wrote Z2M-shaped rows was deleted a day
-- earlier. A down migration you know cannot restore behaviour is a fake safety
-- net that reads as reversible in a migration log while being nothing of the
-- kind. If the shape is ever wanted again it comes from git history, informed by
-- whatever new requirement resurrected it.
--
-- APPLY
--   docker exec -i homeiq-postgres psql -U homeiq -d homeiq -v ON_ERROR_STOP=1 \
--     -f - < infrastructure/postgres/migrations/004-drop-zigbee-device-metadata.sql

-- A 0-row drop is instant, but the table still needs an ACCESS EXCLUSIVE lock.
-- These bound the wait rather than letting it queue behind an unrelated
-- long-running transaction and block everything behind it.
SET lock_timeout = '3s';
SET statement_timeout = '5s';

DROP TABLE IF EXISTS devices.zigbee_device_metadata;

-- Verification, so applying this file proves the end state instead of trusting
-- an exit code.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'devices' AND table_name = 'zigbee_device_metadata'
    ) THEN
        RAISE EXCEPTION 'zigbee_device_metadata still present after DROP';
    END IF;
    RAISE NOTICE 'zigbee_device_metadata is absent from schema devices';
END $$;
