# Session handoff
**Updated:** 2026-08-19T21:40:00Z
**Git:** ed48df8f (branch tap-6230-ha-write-gateway)
**Linear P0:** TAP-6230

## Done
- `HARegistryWriter` (`libs/homeiq-ha/src/homeiq_ha/registry_writer.py`) is the single verified path for device/entity **name and area** writes. Takes anything with `send_command`, so it composes with `HAClient.ws`, the read-only proxy, the sim, and device-intelligence's own client. Every write reads the value back and raises `WriteNotVerified` on disagreement; refuses an unknown `area_id` (HA stores those verbatim and they would verify cleanly into a phantom area). Never sends `new_entity_id`, so entity_id slugs cannot move through it. 8 tests.
- Fixed three defects the read-back exposed, all previously invisible behind a 200 or a stub:
  1. `sync_name_to_ha` posted to the `homeassistant.update_entity` **service** with a `name` field — a state-refresh service with no `name`, and a device id used as an entity id. Logged "Synced name", renamed nothing. Result was also discarded (`success=True` hardcoded); `AcceptNameResponse` now carries `synced_to_ha`.
  2. `remediation_service._rename_device` sent `name=` to `config/device_registry/update`. HA accepts only area_id/disabled_by/labels/name_by_user and is PREVENT_EXTRA, so that action answered `success: false` every run — the rename_device hygiene action has never worked.
  3. `ws.py:501` claimed device renames cascade into entity_ids. **They do not** — verified in HA core 2026.8.2. Only computed friendly names change. That comment was the stated reason 88 hygiene findings went unactioned.
- Test stubs in `test_hygiene_router` / `test_remediation_service` echoed back any field handed to them, which is what let `name=` look like it worked. They now reject what real HA rejects.
- Suites: homeiq-ha 315 passed (was 307), homeiq 3.14 113 passed, device-intelligence +9 runnable tests.

## Open
- **Two callers still not routed through the gateway** (blocks the epic's success criterion): `admin-api` `entity_management_endpoints._sync_to_ha` (hand-rolled aiohttp WS, new connection + auth handshake *per write*, no read-back) and `ha-setup-service` `validation_service.apply_fix` (shared lib, no read-back). The agent recipes verify via their own contract and are fine.
- 88 hygiene findings still unread — but the entity_id-cascade fear that froze them was unfounded, so device renames are now safe to act on.
- TAP-6230 children still untouched: shared rules module (rubric implemented 5x incl. a TypeScript copy in `useEntityAudit.ts`), the brand-token contradiction, `AUTO_GENERATE_NAME_SUGGESTIONS` (still `False`, pipeline dark), TAP-6227, TAP-6228.
- AF agent `homeiq-ha-automation-tester` committed but unpublished — needs a homeiq-scoped `afp_*` key; the one in `AgentForge/.env` returns 403.

## Blockers
- `device-intelligence-service` tests that need Postgres error on any machine without it: their fixtures hardcode `localhost:5432`, which per prior finding belongs to **another project** (HomeIQ is on 15432). 4 tests in `test_remediation_service.py` and 2 in `test_hygiene_router.py` error identically on HEAD — pre-existing, not from this work. Deliberately not "fixed", since pointing them at a live 5432 would authenticate against a stranger's database. Needs a real decision: point at 15432, or containerise the fixture.

## Verify
- `.venv/bin/python -m pytest libs/homeiq-ha/tests/ -q` — expect 315 passed
- `.venv-ha/bin/python -m pytest -c pytest-homeiq.ini -q` — expect 113 passed
- `.venv/bin/python -m pytest -c pytest-unit.ini -q domains/ml-engine/device-intelligence-service/tests/test_remediation_service.py` — expect 3 passed, 4 errors (DB, pre-existing)
- `curl -s localhost:8024/api/v1/init/audit` — expect 24 satisfied, 1 blocked_on_human

## Next (P0)
- Route `admin-api` `_sync_to_ha` and `ha-setup-service` `apply_fix` through `HARegistryWriter`, deleting the hand-rolled aiohttp WS client in admin-api. That closes "exactly one component writes a name or area, every other caller routes through it".

## Success criterion
- Exactly one component writes a device or entity name or area to Home Assistant, and every other caller routes through it.
