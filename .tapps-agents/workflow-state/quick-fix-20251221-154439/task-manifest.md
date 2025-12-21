# Workflow: Quick Fix

**ID**: `quick-fix`
**Version**: 1.0.0
**Type**: brownfield

## Status: ❌ Failed (Step 1 of 5)

**Progress**: 0/5 steps completed (0%)
**Started**: 2025-12-21 15:44:39
**Error**: 'StepExecution' object has no attribute 'attempts'

### Current Step

- [ ] **debug** (debugger) - analyze_error - **IN PROGRESS**

  - **Creates**: `debug-report.md` ⏳

### Upcoming Steps

- [ ] **fix** (implementer) - write_code - ⏸️ Blocked - Waiting for debug-report.md
- [ ] **review** (reviewer) - review_code - ⏸️ Blocked - Waiting for fixed-code/
- [ ] **testing** (tester) - write_tests - ⏸️ Blocked - Waiting for fixed-code/
- [ ] **complete** (orchestrator) - finalize - ⏳ Waiting

### Artifacts

- ⏳ `tests/` (expected from testing)
- ❌ `debug-report.md` (missing, blocking steps)
- ❌ `fixed-code/` (missing, blocking steps)
