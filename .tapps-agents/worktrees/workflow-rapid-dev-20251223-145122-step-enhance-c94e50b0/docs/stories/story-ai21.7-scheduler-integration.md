# Story AI21.7: Scheduler Integration

**Epic:** AI-21 - Proactive Conversational Agent Service  
**Status:** 🚧 In Progress  
**Points:** 3  
**Effort:** 6-8 hours  
**Created:** December 2025

---

## User Story

**As a** developer,  
**I want** scheduler integration,  
**so that** suggestions are generated automatically on a schedule.

---

## Business Value

- Enables automated daily suggestion generation
- Runs at optimal time (3 AM) to avoid user disruption
- Configurable schedule for flexibility
- Foundation for proactive automation

---

## Acceptance Criteria

1. ✅ APScheduler 3.10+ integration
2. ✅ Daily batch job at 3 AM
3. ✅ Scheduler lifecycle management (start/stop)
4. ✅ Error handling and logging
5. ✅ Configurable schedule (via settings)
6. ✅ Manual trigger endpoint (optional)

---

## Tasks

1. Add APScheduler dependency
2. Create scheduler service
3. Integrate with SuggestionPipelineService
4. Add scheduler to main.py lifespan
5. Add configuration for schedule time
6. Write unit tests

---

## Technical Notes

- Schedule: Daily at 3:00 AM (configurable via `SCHEDULER_BATCH_TIME`)
- Uses APScheduler AsyncIOScheduler
- Job ID: "daily_suggestion_generation"
- Error handling: Log errors, continue scheduler

