# Story AI21.8: Suggestion Storage & Management

**Epic:** AI-21 - Proactive Conversational Agent Service  
**Status:** 🚧 In Progress  
**Points:** 3  
**Effort:** 6-8 hours  
**Created:** December 2025

---

## User Story

**As a** developer,  
**I want** suggestion storage and management,  
**so that** suggestions are persisted and trackable.

---

## Business Value

- Enables suggestion tracking and history
- Supports suggestion status management
- Foundation for user notification system
- Allows suggestion analytics and insights

---

## Acceptance Criteria

1. ✅ SQLite database schema (suggestions table)
2. ✅ SQLAlchemy 2.0 async models
3. ✅ Suggestion CRUD operations
4. ✅ Status tracking (pending, sent, approved, rejected)
5. ✅ Metadata storage (context used, prompt, response)
6. ✅ Indexes for performance (status, created_at)
7. ✅ Suggestion cleanup (TTL-based, 90 days default)
8. ✅ Database migrations (Alembic)
9. ✅ Unit tests for storage layer

---

## Tasks

- [x] Create database models
- [x] Create database initialization
- [x] Implement CRUD operations
- [x] Add status tracking
- [x] Add metadata storage
- [x] Add database indexes
- [x] Add cleanup functionality
- [x] Set up Alembic migrations
- [x] Write unit tests

---

## File List

- `services/proactive-agent-service/src/database.py` (NEW)
- `services/proactive-agent-service/src/models.py` (NEW)
- `services/proactive-agent-service/src/services/suggestion_service.py` (NEW)
- `services/proactive-agent-service/alembic.ini` (NEW)
- `services/proactive-agent-service/alembic/env.py` (NEW)
- `services/proactive-agent-service/alembic/versions/` (NEW)
- `services/proactive-agent-service/tests/test_suggestion_service.py` (NEW)

---

## Implementation Notes

- Uses SQLAlchemy 2.0 async patterns
- SQLite for single-home deployment
- Alembic for migrations
- TTL-based cleanup for old suggestions

---

## QA Results

_To be completed after implementation_

