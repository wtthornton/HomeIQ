# Session handoff
**Updated:** 2026-08-01T21:47:24Z
**Git:** 4f1a0fca
**Linear P0:** TAP-5428

## Done
- **Phase 1 live-audited and fixed** — BackupScheduleRecipe and FirstBackupRecipe against HA 2026.7.4 (HAOS 18.2, Pi hardware)
- **Five defects in phase 1 found and fixed:**
  1. `backup/generate` sent no `agent_ids` — backup had no destination
  2. `verify` re-read immediately after `generate` — async job → 0 backups → failure on still-writing instance
  3. `capture` read ids mid-job — in-flight backup invisible to `diff`, survived `restore`
  4. Schedule recipe never set destination — `automatic_backups_configured` stayed false after "successful" apply
  5. `capture` didn't track `create_backup.agent_ids` — introduced by fixing #4, would have survived restore
- **New module** `libs/homeiq-ha/src/homeiq_ha/agent/backup.py` — async backup polling, `wait_for_backup()`, `wait_until_idle()`, timeout logic
- **Test simulator overhauled** — now models real async contract; `backup/generate` returns a job handle (not immediate backup), lands via `_advance_backup()` state machine over 2+ polls
- **Regression tests added** — 12 new tests (99 total, up from 87); all pass; 8 files score 100, 0 security issues
- **Live cycle proved**: apply 4 changes → monitor `state=idle` → second apply 0 changes (idempotent) → diff 4 differences → restore 2 actions → post-restore diff 0, independent read confirms exact baseline

## Open
- Phase 1 fixes not yet committed (awaiting approval per TAP-5428)
- Phases 2, 4, 5 never exercised live
- BackupScheduleRecipe remains `BLOCKED_ON_HUMAN` (encryption key cannot be set via API)
- Shared HA client (TAP-5424) still wired into nothing
- 11 dashboard path families under-covered

## Next (P0)
- **TAP-5428:** Commit phase 1 defect fixes (8 modified + 2 new files) — all validation green. These are the async backup polling, destination-tracking, and 12 regression tests that proved live idempotency and restore completeness.

## Blockers
- none

## Changed files
- `libs/homeiq-ha/src/homeiq_ha/agent/backup.py` (new, 159 lines)
- `libs/homeiq-ha/src/homeiq_ha/agent/recipes.py` (+125)
- `libs/homeiq-ha/src/homeiq_ha/agent/snapshot.py` (+33)
- `libs/homeiq-ha/src/homeiq_ha/agent/readonly.py` (+1)
- `libs/homeiq-ha/src/homeiq_ha/agent/__init__.py` (+2)
- `libs/homeiq-ha/tests/conftest.py` (new, 16 lines)
- `libs/homeiq-ha/tests/test_agent_recipes.py` (+168)
- `libs/homeiq-ha/tests/test_agent_snapshot.py` (+67)
- `.gitignore` (+4)

## Verify
- `.venv/bin/python -m pytest libs/homeiq-ha -q` — expect 99 passed, 0 skipped
- `python -m homeiq_ha.agent audit` against live HA — expect 0 writes, 15 reads

## Context worth carrying
- **Test fixture models live contract.** Simulator now accurately reflects Home Assistant's async backup creation and state machine. A test that passes here works on real HA.
- **Backup destinations are a platform-wide gap.** BackupScheduleRecipe fills `agent_ids` from available agents; other recipes should adopt this pattern.
- **Phase 1 is the gate for all later phases** per design. An instance without automatic backups cannot proceed. The encryption-key human gate is real — backups without it are unrecoverable.

## Success criterion
Phase 1 applies to live Home Assistant idempotently, restores cleanly to pre-run state, and leaves the instance exactly as found.
