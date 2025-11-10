# Tests Triage Follow-Up Plan

## Context
- `tests-triage` TODO remains pending. Many suites are currently skipped because of missing heavy dependencies (transformers, InfluxDB v3, device intelligence backends, etc.).
- A first pass restored imports and added skip guards so the unified `pytest -c pytest-unit.ini` run completes without fatal errors, but coverage is limited to the lightweight suites.

## Objectives
1. Decide which skipped suites must return for CI and what mocks are required.
2. Replace broad test skips with dependency-aware fixtures or local stubs.
3. Re-enable targeted suites and validate they pass in the agent sandbox.

## Proposed Tasks
1. **Inventory skipped suites**
   - List each module-level skip (`pytest.importorskip` and service-level skips) and identify its dependency gap.
   - Prioritize AI automation, automation-miner, data-api, websocket-ingestion, and CLI suites.

2. **Design dependency stubs**
   - For transformer-dependent suites, create lightweight stub modules or fixture-based monkeypatches so tests can exercise business logic without heavyweight model loads.
   - For InfluxDB v3 gaps, stub the client interface (e.g. provide fake `QueryApi` responses).

3. **Incrementally re-enable suites**
   - Remove the skip for a suite once its dependencies are stubbed.
   - Run `python -m pytest -c pytest-unit.ini` focusing on the affected service path.
   - Document any tests that remain intentionally skipped (with reasons and follow-up issues).

4. **Update pytest config**
   - Clean up `pytest-unit.ini` to reflect newly reactivated suites.
   - Ensure `tests/path_setup.py` no longer prunes modules required by the restored suites.

5. **Finalize TODO**
   - When all targeted suites are active and green, mark the `tests-triage` TODO as completed.
   - Capture outcomes in a short verification note (see `implementation/verification/`).

## Notes
- Leave this plan in place until the follow-up work is complete or superseded.
- If additional suites are discovered later, append them to the inventory step before removal of the plan.


