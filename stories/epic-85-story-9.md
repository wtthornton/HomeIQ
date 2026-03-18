# Story 85.9 -- Background Jobs Unit Tests

<!-- docsmcp:start:user-story -->

> **As a** platform engineer, **I want** unit tests covering the job scheduler and memory consolidation job, **so that** background task lifecycle and error recovery are validated

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that jobs/scheduler.py and jobs/memory_consolidation.py have unit tests verifying scheduler start/stop, job registration, execution triggers, and consolidation job logic — both currently at zero test coverage.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

**jobs/scheduler.py** — APScheduler wrapper that manages background jobs for data-api. Functions include `start()`, `stop()`, `add_job()`. Configured with cron-like intervals.

**jobs/memory_consolidation.py** — Implements the memory consolidation background job. Called periodically by the scheduler to consolidate data.

Background jobs run silently — failures are invisible without tests. A broken scheduler or consolidation job can cause data staleness across the platform.

See [Epic 85](epic-85-data-api-line-coverage.md) for project context.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/core-platform/data-api/src/jobs/scheduler.py`
- `domains/core-platform/data-api/src/jobs/memory_consolidation.py`
- `domains/core-platform/data-api/tests/test_job_scheduler_unit.py` (new)
- `domains/core-platform/data-api/tests/test_memory_consolidation_unit.py` (new)

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Read jobs/scheduler.py and map scheduler lifecycle methods
- [ ] Write tests for `start()` — scheduler initialized and running
- [ ] Write tests for `stop()` — scheduler stopped, jobs cleared
- [ ] Write tests for `add_job()` — job registered with correct interval
- [ ] Write tests for duplicate job prevention (if applicable)
- [ ] Write tests for scheduler start when already running (idempotent)
- [ ] Read jobs/memory_consolidation.py and map consolidation logic
- [ ] Write tests for `consolidate_memory()` — happy path execution
- [ ] Write tests for consolidation with empty data (no-op)
- [ ] Write tests for consolidation failure — error logged, no crash
- [ ] Write tests for consolidation with database unavailable
- [ ] Verify all tests pass: `pytest tests/test_job_scheduler_unit.py tests/test_memory_consolidation_unit.py -v`

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] scheduler.py has 5+ tests covering start/stop/add_job lifecycle
- [ ] memory_consolidation.py has 5+ tests covering execution and error paths
- [ ] APScheduler mocked — no real scheduler threads
- [ ] Error recovery verified — consolidation failures don't crash scheduler

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 85](epic-85-data-api-line-coverage.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_scheduler_start` -- Scheduler starts successfully
2. `test_scheduler_stop` -- Scheduler stops and clears jobs
3. `test_scheduler_add_job` -- Job added with correct interval and function
4. `test_scheduler_start_idempotent` -- Multiple start calls don't create duplicate schedulers
5. `test_scheduler_stop_when_not_running` -- Stop on inactive scheduler doesn't error
6. `test_consolidation_happy_path` -- Consolidation executes and completes
7. `test_consolidation_empty_data` -- No data to consolidate is a no-op
8. `test_consolidation_db_failure` -- Database error logged, no crash
9. `test_consolidation_partial_failure` -- Partial failure doesn't corrupt successful work
10. `test_consolidation_async_execution` -- Async consolidation runs correctly

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Mock APScheduler's `AsyncIOScheduler` or `BackgroundScheduler` — don't start real threads
- memory_consolidation.py is likely async — use `pytest-asyncio` fixtures
- Consolidation may interact with InfluxDB and/or PostgreSQL — mock both

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- None

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Standalone job modules
- [x] **N**egotiable -- Error scenarios adjustable
- [x] **V**aluable -- Background jobs run silently — failures invisible without tests
- [x] **E**stimable -- Clear scope: 2 files, ~200 LOC
- [x] **S**mall -- 3 points, half-session
- [x] **T**estable -- Mock scheduler and DB, verify calls and error handling

<!-- docsmcp:end:invest -->
