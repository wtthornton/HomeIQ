# Session handoff
**Updated:** 2026-07-31T02:48:00Z
**Git:** ccae1545 (merged to master)
**Linear P0:** none

## Done
- Bootstrapped HomeIQ as AgentForge Pattern A consumer (PR #66)
- Ran baseline audit sweep over 4 real services: 8 findings, all verified real against source
- Fixed critical TypeError in ai-query-service breaking every query request (PR #67)
- Fixed two high-severity security bugs in data-retention service (pattern_aggregate_retention.py + backup_restore.py)
  - cleanup deletion now actually runs (was commented out)
  - .env secrets excluded from backup archives (was persisted unencrypted)
- All PRs pushed to GitHub

## Next (P0)
All 4 HIGH-severity audit findings are now fixed. #68 merged; #67 and #69 open.

Two operational follow-ups from the #68 merge need infra access, neither started:
1. Exercise the now-live InfluxDB delete in pattern_aggregate_retention.py against a NON-PRODUCTION bucket before it runs on real data. It is enabled on master but has never executed.
2. Rotate any credentials present in pre-existing /backups/*.tar.gz — those archives still contain .env from before the fix.

Merge #67 (ai-query HIGH — every query/refine request 500s until it lands) and #69 (websocket house-status visibility).

Remaining audit findings, all MEDIUM/LOW, none started:
- ai-query-service: unbounded `_rate_limit_locks` growth in api/middlewares.py; redundant `except (httpx.HTTPError, Exception)` swallow in query/entity_extractor.py
- admin-api: MEDIUM in devices_endpoints.py try blocks; LOW in analyze_review.py (audit verdict was still "ship")

## Blockers
- none

## Verify
- Baseline audit sweep findings: reports/af-audit-baseline.json
- data-retention tests: `5 failed, 33 passed` — all 5 failures are PRE-EXISTING, confirmed identical on baseline and fix branch. Causes: test_cleanup_old_backups mock lacks Python 3.13 `follow_symlinks` kwarg; test_backup_config/test_restore_config patch `os.path.exists` while src calls `Path.exists`. Worth a separate fix.
- Repo CI is workflow_dispatch-only (0e8cb770), so PRs merge with ZERO automated checks. Run tests locally before merging anything.
- Test invocation needs `PYTHONPATH=<repo root>` — pytest.ini `pythonpath = . ../..` is one level short of the root `tests/path_setup.py` that conftest imports. Affects data-retention AND websocket-ingestion.
- websocket-ingestion suite: baseline 100 failed / 313 passed / 38 errors; with #69 it is 99 failed / 314 passed / 38 errors (zero regressions). That service has NO green baseline — the ~99 failures deserve their own cleanup epic.
- `tests/unit/test_websocket_handler.py` HANGS indefinitely (SIGTERM at 600s). Excluded from all runs. Needs investigation.
- `test_calculate_delay_max_delay` is FLAKY by construction: `_calculate_delay` adds ±10% jitter via random.random() and the test asserts `delay <= max_delay`, so it fails ~50% of runs. Don't chase it as a regression.

## Success criterion
All 4 services validated by baseline audit; high-severity bugs fixed; ready for release pipeline.