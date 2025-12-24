# Story AI21.9: API Endpoints

**Epic:** AI-21 - Proactive Conversational Agent Service  
**Status:** 🚧 In Progress  
**Points:** 5  
**Effort:** 8-10 hours  
**Created:** December 2025

---

## User Story

**As a** developer,  
**I want** REST API endpoints,  
**so that** I can manage suggestions programmatically.

---

## Business Value

- Enables external access to suggestions
- Supports dashboard integration
- Allows manual suggestion management
- Foundation for user notification system

---

## Acceptance Criteria

1. ✅ GET /api/v1/suggestions - List suggestions
2. ✅ GET /api/v1/suggestions/{id} - Get suggestion by ID
3. ✅ PATCH /api/v1/suggestions/{id} - Update suggestion status
4. ✅ DELETE /api/v1/suggestions/{id} - Delete suggestion
5. ✅ GET /api/v1/suggestions/stats - Get statistics
6. ✅ POST /api/v1/suggestions/trigger - Manual trigger (optional)
7. ✅ Request/response validation (Pydantic models)
8. ✅ Error handling (HTTP status codes)
9. ✅ OpenAPI documentation

---

## Tasks

1. Create suggestions router
2. Implement list endpoint (with filters)
3. Implement get by ID endpoint
4. Implement update status endpoint
5. Implement delete endpoint
6. Implement stats endpoint
7. Implement manual trigger endpoint
8. Add Pydantic request/response models
9. Register router in main.py
10. Write unit tests

---

## Technical Notes

- API prefix: `/api/v1/suggestions`
- Status values: pending, sent, approved, rejected
- Filtering: status, context_type, limit, offset
- Response format: JSON with consistent structure

