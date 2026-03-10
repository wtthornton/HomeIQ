---
epic: auto-bugfix-robustness-and-tests
priority: high
status: complete
estimated_duration: 1-2 weeks
risk_level: low
source: auto-bugfix pipeline run 2026-03-10 (3 bugs fixed, scan retry observed)
type: quality
---

# Epic 46: Auto-Bugfix Pipeline — Scan Robustness & Test Coverage

**Status:** Complete (Mar 10, 2026)
**Priority:** P1 High
**Duration:** 1-2 weeks
**Risk Level:** Low
**Source:** Auto-bugfix run 2026-03-10 (`-Bugs 3 -Worktree`); scan produced no JSON on first attempt, retry with direct code review succeeded. Three bugs fixed in core-platform; no automated tests added for those fixes.
**Affects:** `scripts/auto-bugfix.ps1`, scan/fix pipeline, `domains/core-platform/admin-api`, `domains/core-platform/data-retention`

## Context

The auto-bugfix pipeline (`scripts/auto-bugfix.ps1`) runs a TappsMCP- and code-review-based scan to find bugs, then applies fixes via Claude Code headless. In the Mar 10 run:

1. **Scan robustness:** The first scan completed (12 turns, ~126s) but "no JSON found in scan output." The pipeline retried with "direct code review only" and then successfully extracted 3 bugs via BUGS markers. Improving the scan step to reliably produce machine-parseable output (or to degrade gracefully without retry) will reduce latency and cost.
2. **Test coverage:** Three bugs were fixed (Flux query injection in `influxdb_client.py`, BackupResponse type mismatch in `backup.py`, missing `self.enabled` guard in `storage_analytics.py`). No new tests were added to lock in the fixes; adding targeted tests will prevent regressions and document expected behavior.

---

## Stories

### Story 46.1: Scan Step — Reliable Structured Output

**Priority:** P1 High | **Estimate:** 6h | **Risk:** Low

**Problem:** The scan phase uses a Claude session to find bugs; the pipeline expects parseable output (e.g. JSON or BUGS markers). When the model returns prose without the expected structure, the script reports "no JSON found in scan output" and retries with "direct code review only," doubling scan time and cost.

**Acceptance Criteria:**
- [x] Document the exact format the pipeline expects from the scan (JSON schema or BUGS marker format) in the script or in `docs/workflows/` / script header.
- [x] Update the scan prompt (or FIND_PROMPT_OVERRIDES.md) to require structured output (e.g. "Respond with a JSON object..." or "Emit BUGS blocks with file, line, description") so the first attempt succeeds more often.
- [x] Add a lightweight validation step after scan (e.g. regex for BUGS blocks or JSON parse); if valid, skip retry.
- [x] Optionally: if first scan fails validation, log the raw response (redacted if needed) to a file under `implementation/` or `reports/` for debugging.
- [ ] Run pipeline with `-Bugs 3` (or 1) and confirm scan completes without retry in normal conditions; document any remaining edge cases.

---

### Story 46.2: Scan Step — Retry and Fallback Behavior

**Priority:** P2 Medium | **Estimate:** 3h | **Risk:** Low

**Problem:** When the first scan fails validation, the pipeline retries with "direct code review only." Retry logic and fallback are not clearly specified (e.g. max retries, backoff, or user-facing message).

**Acceptance Criteria:**
- [x] Define max retries (e.g. 2 total attempts) and document in script or docs.
- [x] Ensure the fallback path (direct code review) is clearly triggered and logged so operators know which path ran.
- [x] If both attempts fail, exit with a clear error message and, if applicable, a path to the saved scan output for manual inspection.
- [x] No change to success-path behavior when scan returns valid output on first try.

---

### Story 46.3: Tests — admin-api Flux Query Injection Guard

**Priority:** P1 High | **Estimate:** 2h | **Risk:** Low

**Problem:** Bug fix in `domains/core-platform/admin-api/src/influxdb_client.py` added an allowlist regex for `service_name` and raises `ValueError` for invalid values. There are no tests to prevent regressions (e.g. someone removing the check or relaxing the regex).

**Acceptance Criteria:**
- [x] Add unit tests for `get_service_metrics()` (or the validation helper): valid `service_name` (alphanumeric, underscore, hyphen, length ≤128) succeeds or is passed through; invalid inputs (e.g. containing `"`, `|>`, newline, or over length) raise `ValueError`.
- [x] Tests live in the admin-api test suite (e.g. `domains/core-platform/admin-api/tests/`) and run with the rest of the service tests.
- [x] No new lint or quality gate failures; `tapps_quick_check` passes on new/modified files.

---

### Story 46.4: Tests — data-retention Backup Response Shape

**Priority:** P1 High | **Estimate:** 2h | **Risk:** Low

**Problem:** Bug fix in `domains/core-platform/data-retention/src/api/routers/backup.py` maps `BackupInfo` to `BackupResponse` (including `status` and ISO `created_at`). Without tests, future changes to the service or model could reintroduce ResponseValidationError (500).

**Acceptance Criteria:**
- [x] Add unit tests for the backup creation endpoint (or the mapping logic): response has required fields (`backup_id`, `backup_type`, `created_at` as string, `size_bytes`, `status`); `status` is "success" or "failed" based on `BackupInfo.success`.
- [x] Tests run in the data-retention test suite; may use a mock or in-memory backup service if needed.
- [x] `tapps_quick_check` passes on new/modified files.

---

### Story 46.5: Tests — data-retention Storage Analytics Enabled Guard

**Priority:** P2 Medium | **Estimate:** 1.5h | **Risk:** Low

**Problem:** Bug fix in `domains/core-platform/data-retention/src/storage_analytics.py` added `if not self.enabled: return` at the start of `log_retention_operation()`. When disabled, the method must no-op and must not access `self.client`.

**Acceptance Criteria:**
- [x] Add unit tests for `log_retention_operation()`: when `enabled` is False (and optionally `self.client` is None), the method returns without calling `self.client.write` or raising.
- [x] When enabled, existing or new tests cover the write path if not already covered.
- [x] Tests live in data-retention test suite; `tapps_quick_check` passes on new/modified files.

---

## Summary

| Story | Focus | Priority | Est. |
|-------|--------|----------|------|
| 46.1 | Scan structured output & validation | P1 | 6h |
| 46.2 | Scan retry & fallback behavior | P2 | 3h |
| 46.3 | admin-api `service_name` validation tests | P1 | 2h |
| 46.4 | data-retention backup response tests | P1 | 2h |
| 46.5 | data-retention storage_analytics enabled guard tests | P2 | 1.5h |
| **Total** | | | **~14.5h** |

## Dependencies

- None. Stories 46.1 and 46.2 can be done in parallel with 46.3–46.5.
- 46.3–46.5 depend only on the current codebase (fixes already merged).
