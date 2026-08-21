-- 006-is-battery-powered-nullable.sql — TAP-6393
--
-- Drops NOT NULL from `devices.devices.is_battery_powered`, so a device whose
-- power source cannot be established inserts as unknown rather than failing.
--
-- WHAT BROKE
--
-- This column is derived: `power_source = 'battery'`. Once DeviceKnowledge
-- gained three-state semantics — value / explicit NULL to clear / key absent
-- meaning "could not evaluate" — the derivation could only run when
-- power_source itself had been established. For the 45 of 93 devices where it
-- had not, the key was absent from the upsert, and PostgreSQL checks NOT NULL
-- while forming the tuple, BEFORE the ON CONFLICT arbiter runs. So the row
-- never reached the DO UPDATE branch that would have left the stored value
-- alone. The statement raised, the transaction aborted, and the entire
-- discovery pass wrote nothing.
--
-- Every row in devices.devices carried updated_at = 2026-08-21 03:38:35 for
-- fourteen hours while discovery reported 93 devices found and logged the
-- NotNullViolationError into an errors array nobody was alerting on.
--
-- WHY NULLABLE IS THE RIGHT ANSWER, NOT A DEFAULT
--
-- `DEFAULT false` would make the constraint pass and assert something untrue:
-- that a device of unknown power source is known not to be battery-powered.
-- That is the same class of defect as the eight rows this branch already fixed,
-- which read power_source='battery' alongside is_battery_powered=false. NULL is
-- the only value that means what is actually the case.
--
-- Idempotent: DROP NOT NULL on an already-nullable column is a no-op.

ALTER TABLE devices.devices ALTER COLUMN is_battery_powered DROP NOT NULL;

-- Retract the assertions the old NOT NULL forced.
--
-- 45 of 93 rows read is_battery_powered = false purely because the column could
-- not hold anything else. Their power_source is NULL — unknown — so "known not
-- to run on batteries" was never established about any of them. The write path
-- cannot retract these itself: it omits the key when power_source is
-- unestablished, which preserves the stored value by design, so the false would
-- stand forever.
--
-- Scoped to rows whose source is NULL, so it can never disagree with an
-- established power_source. Idempotent.

UPDATE devices.devices
   SET is_battery_powered = NULL
 WHERE power_source IS NULL
   AND is_battery_powered IS NOT NULL;
