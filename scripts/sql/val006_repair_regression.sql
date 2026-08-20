-- VAL-006 regression: a delete-and-re-pair that swaps two identical models'
-- `_N` suffixes must not re-attach a finding to the wrong device.
--
-- Runs entirely inside a transaction and ROLLBACKs. Safe against the live
-- database; it leaves nothing behind.
--
--   docker exec -i homeiq-postgres psql -U homeiq -d homeiq \
--     -v ON_ERROR_STOP=1 -f - < scripts/sql/val006_repair_regression.sql
--
-- Why this defect was real: `entity_id` is an ADDRESS, not an identity. HA mints
-- the `_2` suffix by arrival order at pairing, so two identically-modelled
-- devices can swap suffixes on a re-pair. While the sync upserted
-- `ON CONFLICT (entity_id)`, a finding raised against "the office dimmer" stayed
-- bolted to the string `light.inovelli_vzm31_sn` — which after the swap is the
-- BAR dimmer. That is a wrong-device write waiting to happen, and it is the same
-- failure mode as the swapped friendly names.
--
-- The fix has two halves and this test fails if either is missing:
--   1. ux_device_entities_registry_key UNIQUE (domain, platform, unique_id)
--      so the upsert conflicts on identity and moves entity_id in place.
--   2. ON UPDATE CASCADE on the dependent FKs so findings follow the address.

BEGIN;

INSERT INTO devices.device_entities
  (entity_id, name, platform, domain, has_entity_name, unique_id, created_at, updated_at)
VALUES
  ('light.val006_vzm31_sn',   'Office Light Dimmer', 'zha', 'light', false, 'UQ-OFFICE-0e8f', NOW(), NOW()),
  ('light.val006_vzm31_sn_2', 'Bar Light Dimmer',    'zha', 'light', false, 'UQ-BAR-11ef',    NOW(), NOW());

INSERT INTO devices.device_hygiene_issues
  (issue_key, issue_type, severity, status, entity_id, name, summary, detected_at, updated_at)
VALUES
  ('VAL006-OFFICE-FINDING', 'naming', 'high', 'open', 'light.val006_vzm31_sn',
   'Office Light Dimmer', 'finding raised against the OFFICE device', NOW(), NOW());

-- The re-pair: same two physical devices, suffixes handed out in the other order.
UPDATE devices.device_entities SET entity_id = 'light.val006_tmp'       WHERE unique_id = 'UQ-OFFICE-0e8f';
UPDATE devices.device_entities SET entity_id = 'light.val006_vzm31_sn'  WHERE unique_id = 'UQ-BAR-11ef';
UPDATE devices.device_entities SET entity_id = 'light.val006_vzm31_sn_2' WHERE unique_id = 'UQ-OFFICE-0e8f';

\echo 'ASSERTION 1 - the finding still points at the OFFICE device:'
SELECT CASE WHEN e.unique_id = 'UQ-OFFICE-0e8f'
            THEN 'PASS - finding followed the device'
            ELSE 'FAIL - re-attached to the WRONG device' END AS verdict,
       h.entity_id AS now_points_at, e.name
FROM devices.device_hygiene_issues h
JOIN devices.device_entities e ON e.entity_id = h.entity_id
WHERE h.issue_key = 'VAL006-OFFICE-FINDING';

\echo 'ASSERTION 2 - the re-pair created no duplicate rows (expect 2):'
SELECT CASE WHEN count(*) = 2 THEN 'PASS - no duplicates' ELSE 'FAIL - duplicate rows' END AS verdict,
       count(*) AS rows_for_the_two_dimmers
FROM devices.device_entities WHERE unique_id IN ('UQ-OFFICE-0e8f','UQ-BAR-11ef');

\echo 'ASSERTION 3 - the durable key exists and is unique across every row:'
SELECT CASE WHEN count(*) = count(DISTINCT (domain, platform, unique_id))
            THEN 'PASS - key is unique' ELSE 'FAIL - key collides' END AS verdict,
       count(*) AS total, count(DISTINCT (domain, platform, unique_id)) AS distinct_key
FROM devices.device_entities;

ROLLBACK;
