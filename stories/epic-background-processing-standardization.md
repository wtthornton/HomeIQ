---
epic: background-processing-standardization
priority: medium
status: open
estimated_duration: 1-2 weeks
risk_level: low
source: Architecture review of 50 microservices (2026-03-01)
---

# Epic 14: Background Processing Standardization

**Status:** Open
**Priority:** Medium (P2)
**Duration:** 1-2 weeks
**Risk Level:** Low
**Source:** Duplicated boilerplate analysis across 50 HomeIQ microservices
**Affects:** 11 services with scheduled jobs, 10 services with background tasks

## Context

Services that run recurring jobs or background tasks each implement their own APScheduler setup and asyncio task management. APScheduler initialization (`AsyncIOScheduler()` -> `add_job()` with `CronTrigger` -> `start()`) is duplicated across 11 services with identical boilerplate. Background task creation and cancellation (`asyncio.create_task()` -> store reference -> cancel on shutdown) follows the same pattern in 10 services. Extracting these into shared utilities eliminates ~700 lines of duplicate lifecycle code and ensures consistent error handling, logging, and graceful shutdown.

## Stories

### Story 14.1: BackgroundTaskManager — Managed Async Task Lifecycle

**Priority:** Medium | **Estimate:** 1 day | **Risk:** Low

**Problem:** 10 services use `asyncio.create_task()` to spawn background work during startup, then manually track task references and cancel them on shutdown. Each service independently implements: task creation, reference storage, cancellation with `task.cancel()`, `asyncio.gather(*tasks, return_exceptions=True)` for cleanup, and exception logging. Missing cancellation causes orphaned tasks; inconsistent error handling causes silent failures.

**Files:**
- New: `libs/homeiq-patterns/src/homeiq_patterns/task_manager.py`
- Modify: `libs/homeiq-patterns/src/homeiq_patterns/__init__.py` (add export)
- Migrate:
  - `domains/core-platform/websocket-ingestion/src/main.py` — 3 background tasks (event processor, batch processor, memory manager)
  - `domains/core-platform/data-retention/src/main.py` — retention cleanup task
  - `domains/device-management/device-health-monitor/src/main.py` — monitoring task
  - `domains/automation-core/ai-automation-service-new/src/main.py` — rate limit cleanup task
  - 6 additional services with background task patterns

**Acceptance Criteria:**
- [ ] `BackgroundTaskManager` class in `homeiq-patterns` with: `add_task(coro, name)`, `cancel_all()`, `wait_for_shutdown(timeout)`
- [ ] Automatic task reference tracking — no manual list management per service
- [ ] Graceful shutdown: cancel all tasks, wait with timeout, log any that fail to stop
- [ ] Exception logging built-in — background task exceptions captured and logged (not silently lost)
- [ ] Integration with `LifespanBuilder` (Story 12.4) — auto-cleanup on shutdown
- [ ] 10 services migrated — task management reduced from ~15 lines to 2-3 lines per task
- [ ] Unit tests for task lifecycle, cancellation, timeout, and exception handling

---

### Story 14.2: SchedulerManager — Standardized APScheduler Setup

**Priority:** Medium | **Estimate:** 1 day | **Risk:** Low

**Problem:** 11 services configure APScheduler with identical boilerplate: `AsyncIOScheduler()` instantiation, `add_job()` with `CronTrigger.from_crontab()`, `replace_existing=True`, `max_instances=1`, `start()`, and `shutdown(wait=True)`. Schedule configuration is inconsistent — some hardcode cron expressions, others read from settings. No shared error handling for job failures.

**Files:**
- New: `libs/homeiq-patterns/src/homeiq_patterns/scheduler_manager.py`
- Modify: `libs/homeiq-patterns/src/homeiq_patterns/__init__.py` (add export)
- Migrate:
  - `domains/pattern-analysis/ai-pattern-service/src/scheduler/pattern_analysis.py` — daily pattern analysis (cron from settings)
  - `domains/automation-core/ai-automation-service-new/src/main.py` — daily suggestion generation (hardcoded "0 2 * * *")
  - `domains/blueprints/automation-miner/src/api/main.py` — weekly corpus refresh
  - `domains/ml-engine/device-intelligence-service/src/scheduler/training_scheduler.py` — ML training schedule
  - `domains/energy-analytics/proactive-agent-service/src/main.py` — daily proactive suggestions
  - 6 additional services with APScheduler usage

**Acceptance Criteria:**
- [ ] `SchedulerManager` class in `homeiq-patterns` with: `add_cron_job(func, cron_expr, job_id)`, `start()`, `stop()`, `is_running`
- [ ] Defaults applied: `replace_existing=True`, `max_instances=1` (prevent overlapping runs)
- [ ] Cron expression from settings or explicit parameter (no hardcoding needed)
- [ ] Job exception handling: log errors, continue scheduler operation (never crash scheduler)
- [ ] Integration with `LifespanBuilder` (Story 12.4) — auto-stop on shutdown
- [ ] Health check integration: reports scheduled job status and last run times
- [ ] 11 services migrated — scheduler setup reduced from ~20 lines to 3-5 lines per job
- [ ] Unit tests for job registration, cron parsing, error handling, and shutdown
