-- 005-canonicalise-claim-fact-keys.sql — TAP-6394 follow-up
--
-- `fact_key` is a join key, and two genes wrote it with different vocabularies.
-- The researcher declares an enum in its output schema; the curator — which is
-- the actual write path — types the same field as a free string. A vocabulary
-- enforced on the proposer and not on the approver is not enforced, so `wattage`,
-- `standby_power_consumption`, `communication_protocol` and
-- `upstream_zha_quirk_reference` all landed live.
--
-- The cost is silent: a cache probe for `typical_power_watts` returns nothing
-- against a store that already holds the answer under another name, so the
-- lookup is paid for again. Onboarding is cache-first by design, which makes
-- key agreement the difference between a cache that works and one that never
-- hits.
--
-- Going forward this is enforced in DeviceKnowledgeService.record(), which every
-- claim passes through whichever gene proposed it. This file brings the rows
-- written before that existed into line.
--
-- Idempotent: re-running maps already-canonical keys to themselves.
--
-- APPLY
--   docker exec -i homeiq-postgres psql -U homeiq -d homeiq -v ON_ERROR_STOP=1 \
--     -f - < infrastructure/postgres/migrations/005-canonicalise-claim-fact-keys.sql

SET lock_timeout = '3s';
SET statement_timeout = '30s';

UPDATE devices.device_knowledge_claims
SET fact_key = CASE lower(btrim(fact_key))
    WHEN 'wattage'                          THEN 'typical_power_watts'
    WHEN 'power_watts'                      THEN 'typical_power_watts'
    WHEN 'power_consumption'                THEN 'typical_power_watts'
    WHEN 'power_consumption_watts'          THEN 'typical_power_watts'
    WHEN 'typical_power_consumption'        THEN 'typical_power_watts'
    WHEN 'standby_power_consumption'        THEN 'standby_power_watts'
    WHEN 'standby_power'                    THEN 'standby_power_watts'
    WHEN 'idle_power_watts'                 THEN 'standby_power_watts'
    WHEN 'max_power_consumption'            THEN 'max_power_watts'
    WHEN 'maximum_wattage'                  THEN 'max_power_watts'
    WHEN 'max_load_watts'                   THEN 'max_power_watts'
    WHEN 'communication_protocol'           THEN 'radio_protocol'
    WHEN 'protocol'                         THEN 'radio_protocol'
    WHEN 'wireless_protocol'                THEN 'radio_protocol'
    WHEN 'zigbee_model_identifier'          THEN 'zigbee_model_id'
    WHEN 'zigbee_manufacturer_model'        THEN 'zigbee_model_id'
    WHEN 'zigbee_device_type'               THEN 'zigbee_role'
    WHEN 'zigbee_router_capable'            THEN 'zigbee_role'
    WHEN 'zigbee_device_role'               THEN 'zigbee_role'
    WHEN 'upstream_zha_quirk_reference'     THEN 'zha_quirk_required'
    WHEN 'upstream_zha_quirk_class'         THEN 'zha_quirk_required'
    WHEN 'zha_quirk'                        THEN 'zha_quirk_required'
    WHEN 'neutral_wire_required'            THEN 'requires_neutral'
    WHEN 'requires_neutral_wire'            THEN 'requires_neutral'
    WHEN 'power_supply'                     THEN 'power_source'
    WHEN 'power_source_type'                THEN 'power_source'
    WHEN 'supports_ota_updates'             THEN 'firmware_update_path'
    WHEN 'ota_supported'                    THEN 'firmware_update_path'
    WHEN 'home_assistant_update_mechanism'  THEN 'firmware_update_path'
    WHEN 'product_type'                     THEN 'device_type'
    WHEN 'supports_metering'                THEN 'supports_power_metering'
    WHEN 'measured_power_accuracy'          THEN 'supports_power_metering'
    ELSE lower(btrim(fact_key))
END
WHERE fact_key IS DISTINCT FROM CASE lower(btrim(fact_key))
    WHEN 'wattage'                          THEN 'typical_power_watts'
    WHEN 'power_watts'                      THEN 'typical_power_watts'
    WHEN 'power_consumption'                THEN 'typical_power_watts'
    WHEN 'power_consumption_watts'          THEN 'typical_power_watts'
    WHEN 'typical_power_consumption'        THEN 'typical_power_watts'
    WHEN 'standby_power_consumption'        THEN 'standby_power_watts'
    WHEN 'standby_power'                    THEN 'standby_power_watts'
    WHEN 'idle_power_watts'                 THEN 'standby_power_watts'
    WHEN 'max_power_consumption'            THEN 'max_power_watts'
    WHEN 'maximum_wattage'                  THEN 'max_power_watts'
    WHEN 'max_load_watts'                   THEN 'max_power_watts'
    WHEN 'communication_protocol'           THEN 'radio_protocol'
    WHEN 'protocol'                         THEN 'radio_protocol'
    WHEN 'wireless_protocol'                THEN 'radio_protocol'
    WHEN 'zigbee_model_identifier'          THEN 'zigbee_model_id'
    WHEN 'zigbee_manufacturer_model'        THEN 'zigbee_model_id'
    WHEN 'zigbee_device_type'               THEN 'zigbee_role'
    WHEN 'zigbee_router_capable'            THEN 'zigbee_role'
    WHEN 'zigbee_device_role'               THEN 'zigbee_role'
    WHEN 'upstream_zha_quirk_reference'     THEN 'zha_quirk_required'
    WHEN 'upstream_zha_quirk_class'         THEN 'zha_quirk_required'
    WHEN 'zha_quirk'                        THEN 'zha_quirk_required'
    WHEN 'neutral_wire_required'            THEN 'requires_neutral'
    WHEN 'requires_neutral_wire'            THEN 'requires_neutral'
    WHEN 'power_supply'                     THEN 'power_source'
    WHEN 'power_source_type'                THEN 'power_source'
    WHEN 'supports_ota_updates'             THEN 'firmware_update_path'
    WHEN 'ota_supported'                    THEN 'firmware_update_path'
    WHEN 'home_assistant_update_mechanism'  THEN 'firmware_update_path'
    WHEN 'product_type'                     THEN 'device_type'
    WHEN 'supports_metering'                THEN 'supports_power_metering'
    WHEN 'measured_power_accuracy'          THEN 'supports_power_metering'
    ELSE lower(btrim(fact_key))
END;

DO $$
DECLARE
    stragglers int;
BEGIN
    SELECT count(*) INTO stragglers
    FROM devices.device_knowledge_claims
    WHERE fact_key <> lower(btrim(fact_key));
    IF stragglers > 0 THEN
        RAISE EXCEPTION 'canonicalisation left % non-normalised fact_key(s)', stragglers;
    END IF;
    RAISE NOTICE 'fact_key canonicalisation complete';
END $$;
