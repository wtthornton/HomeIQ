# TappsCodingAgents Experts Review - Huey Task Queue Implementation

**Date:** January 20, 2026  
**Status:** Review Required  
**Related:** Huey SQLite Task Queue Implementation (Commit: d21026b7)

## Summary

This document reviews the Huey SQLite task queue implementation and identifies new or updated experts needed for tapps-agents to effectively work with the new architecture.

## Changes Implemented

### New Technologies & Patterns

1. **Huey Task Queue Library** (`huey>=2.6.0`)
   - SQLite backend for persistent task queue
   - Task prioritization and retry mechanisms
   - Periodic task scheduling with cron expressions
   - Async/sync execution bridging patterns

2. **Asynchronous Execution Architecture**
   - Non-blocking HTTP responses
   - Background task processing
   - Task result storage and retrieval
   - Queue management and monitoring

3. **Task Prioritization Logic**
   - Risk-based priority assignment (high=10, medium=5, low=1)
   - Retry strategies based on automation risk level
   - Persistent retry across service restarts

4. **Cron-Based Scheduling**
   - Cron expression parsing (`parse_cron_to_crontab`)
   - Periodic task registration (`@periodic_task` decorator)
   - Dynamic schedule management (enable/disable)

5. **SQLite as Task Queue Backend**
   - File-based persistence (survives restarts)
   - Thread-based workers
   - Result storage with TTL

## Expert Recommendations

### ✅ Existing Experts That Need Updates

#### 1. **expert-automation-strategy** (UPDATE REQUIRED)
**Current Domain:** Automation Strategy Expert  
**Why Update:** Task queue architecture affects automation execution patterns

**New Knowledge Needed:**
- Asynchronous automation execution patterns
- Task prioritization strategies (risk-based)
- Persistent retry mechanisms for automations
- Delayed and scheduled execution patterns
- Queue-based automation execution vs synchronous execution
- Task cancellation and management patterns

**Knowledge Base Files to Add/Update:**
- `.tapps-agents/knowledge/automation-strategy/task-queue-execution-patterns.md`
- `.tapps-agents/knowledge/automation-strategy/automation-prioritization.md`
- `.tapps-agents/knowledge/automation-strategy/persistent-retry-strategies.md`
- `.tapps-agents/knowledge/automation-strategy/scheduled-automation-patterns.md`

#### 2. **expert-microservices** (UPDATE REQUIRED)
**Current Domain:** Microservices Architecture Expert  
**Why Update:** Task queue is a new microservice pattern for async execution

**New Knowledge Needed:**
- Task queue architecture patterns (Huey with SQLite)
- Async/sync execution bridging patterns
- Background worker patterns
- Queue monitoring and health checks
- Task queue integration with FastAPI
- SQLite backend for task queues (vs Redis/Postgres)

**Knowledge Base Files to Add/Update:**
- `.tapps-agents/knowledge/microservices-architecture/task-queue-patterns.md`
- `.tapps-agents/knowledge/microservices-architecture/huey-sqlite-integration.md`
- `.tapps-agents/knowledge/microservices-architecture/async-execution-patterns.md`
- `.tapps-agents/knowledge/microservices-architecture/background-worker-patterns.md`

#### 3. **expert-iot** (UPDATE REQUIRED)
**Current Domain:** IoT & Home Automation Expert  
**Why Update:** Automation execution is core to IoT/home automation

**New Knowledge Needed:**
- HomeIQ automation execution architecture (async vs sync)
- Task queue for automation execution
- Automation scheduling patterns
- Risk-based automation prioritization

**Knowledge Base Files to Add/Update:**
- `.tapps-agents/knowledge/iot-home-automation/homeiq-automation-execution.md`
- `.tapps-agents/knowledge/iot-home-automation/automation-scheduling.md`

### 🆕 New Expert Recommendation

#### 4. **expert-task-queues** (NEW - OPTIONAL)
**Proposed Domain:** Task Queue & Background Processing Expert  
**Why Create:** Task queues are a significant architectural pattern that spans multiple domains

**Scope:**
- Task queue library patterns (Huey, Celery, RQ, etc.)
- Background job processing
- Async/sync execution bridging
- Task prioritization and retry strategies
- Queue monitoring and observability
- SQLite vs Redis vs Postgres for task queues
- Cron-based scheduling patterns

**Knowledge Base Files to Create:**
- `.tapps-agents/knowledge/task-queues/README.md`
- `.tapps-agents/knowledge/task-queues/huey-patterns.md`
- `.tapps-agents/knowledge/task-queues/sqlite-backend-patterns.md`
- `.tapps-agents/knowledge/task-queues/async-sync-bridging.md`
- `.tapps-agents/knowledge/task-queues/task-prioritization.md`
- `.tapps-agents/knowledge/task-queues/cron-scheduling.md`
- `.tapps-agents/knowledge/task-queues/queue-monitoring.md`

**Alternative:** If not creating a new expert, this knowledge could be added to `expert-microservices` since task queues are a microservices pattern.

## Library Documentation Needs

### Context7 Library Documentation

The following libraries should be added to Context7 cache for better code generation:

1. **Huey** (`huey`)
   - Task queue patterns
   - SQLite backend configuration
   - Periodic task decorators
   - Task scheduling (delay, eta)
   - Task result storage

2. **Cron Expression Parsing** (if using external library)
   - Standard cron format
   - Huey crontab conversion

## Priority Assessment

### High Priority (Immediate Updates Needed)

1. **expert-automation-strategy** - Core to automation execution patterns
2. **expert-microservices** - Task queue is a microservices architecture pattern

### Medium Priority (Recommended Updates)

3. **expert-iot** - Automation execution is IoT domain-specific

### Low Priority (Optional)

4. **expert-task-queues** (NEW) - Only if task queues become a major architectural pattern across multiple services

## Implementation Recommendations

### Option 1: Update Existing Experts (Recommended)

**Pros:**
- No new expert configuration needed
- Knowledge stays within relevant domains
- Easier to maintain

**Cons:**
- Knowledge might be split across experts
- Less focused on task queue patterns

**Action:**
- Update `expert-automation-strategy` with automation execution patterns
- Update `expert-microservices` with task queue architecture patterns
- Update `expert-iot` with HomeIQ-specific execution patterns

### Option 2: Create New Expert (If Task Queues Expand)

**Pros:**
- Centralized knowledge for task queue patterns
- Better for future task queue implementations in other services
- More focused expert for task queue questions

**Cons:**
- Additional expert to maintain
- May be premature if only one service uses task queues

**Action:**
- Create `expert-task-queues` expert
- Add to `.tapps-agents/experts.yaml`
- Create knowledge base directory
- Update domains.md

## Knowledge Base Content Outline

### For expert-automation-strategy

**File: `task-queue-execution-patterns.md`**
- Asynchronous vs synchronous execution
- When to use task queue vs direct execution
- Task queue benefits (non-blocking, persistent retry)
- HomeIQ implementation patterns

**File: `automation-prioritization.md`**
- Risk-based priority assignment
- Priority levels (high=10, medium=5, low=1)
- Priority extraction from automation specs
- Priority impact on execution order

**File: `persistent-retry-strategies.md`**
- Retry configuration by risk level
- Retry strategies (high: 10 retries/60s, medium: 5/30s, low: 3/15s)
- Retry persistence across restarts
- Exponential backoff patterns

**File: `scheduled-automation-patterns.md`**
- Cron-based scheduling
- Cron expression format
- Periodic task registration
- Schedule management (enable/disable)

### For expert-microservices

**File: `task-queue-patterns.md`**
- Task queue architecture overview
- When to use task queues in microservices
- Task queue vs message queues
- HomeIQ task queue implementation

**File: `huey-sqlite-integration.md`**
- Huey library overview
- SQLite backend configuration
- Why SQLite for HomeIQ (no Redis/Postgres dependency)
- SQLite backend limitations and considerations

**File: `async-execution-patterns.md`**
- Async/sync execution bridging
- Event loop management in background workers
- Preserving correlation IDs across async boundaries
- Error handling in async tasks

**File: `background-worker-patterns.md`**
- Worker thread configuration
- Consumer process management
- Graceful shutdown patterns
- Worker health monitoring

## Context7 Library Documentation

### Libraries to Add to Context7 Cache

1. **Huey** (`huey`)
   - Use: `@reviewer *docs huey` or `@implementer *docs huey`
   - Topics: task queue, SQLite backend, periodic tasks, scheduling

2. **Cron Expressions** (if needed)
   - Standard cron format documentation
   - Huey crontab conversion patterns

## Review Checklist

- [ ] Review expert-automation-strategy updates
- [ ] Review expert-microservices updates
- [ ] Review expert-iot updates
- [ ] Decide on expert-task-queues (new expert vs update existing)
- [ ] Create/update knowledge base files
- [ ] Add Huey to Context7 cache
- [ ] Test expert knowledge retrieval
- [ ] Update domains.md if new expert created

## Next Steps

1. **Review this document** - Confirm expert update priorities
2. **Create knowledge base files** - Add documentation for new patterns
3. **Update expert configurations** - If creating new expert
4. **Populate Context7 cache** - Add Huey library documentation
5. **Test expert retrieval** - Verify knowledge is accessible

## Related Documentation

- **Implementation Plan:** `c:\Users\tappt\.cursor\plans\huey_sqlite_task_queue_implementation_ccaec85f.plan.md`
- **Epic 31 Architecture:** `.cursor/rules/epic-31-architecture.mdc`
- **Event Flow Architecture:** `docs/architecture/event-flow-architecture.md`
- **API Automation Edge README:** `services/api-automation-edge/README.md`
- **TappsCodingAgents Experts:** `.tapps-agents/experts.yaml`
- **Domains Configuration:** `.tapps-agents/domains.md`
