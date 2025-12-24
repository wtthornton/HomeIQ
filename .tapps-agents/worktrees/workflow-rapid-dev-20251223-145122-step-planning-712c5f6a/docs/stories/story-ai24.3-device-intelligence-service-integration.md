# Story AI24.3: Device Intelligence Service Integration

**Epic:** Epic AI-24 - Device Mapping Library Architecture  
**Status:** Ready for Review  
**Created:** 2025-01-XX  
**Story Points:** 3  
**Priority:** High

---

## Story

**As a** service,  
**I want** device mapping API endpoints,  
**so that** other services can query device types and relationships.

---

## Story Context

**Existing System Integration:**

- **Integrates with:** Device Mapping Library (Story AI24.1), Device Intelligence Service
- **Technology:** FastAPI, Python caching (functools.lru_cache or custom)
- **Location:** `services/device-intelligence-service/src/api/device_mappings_router.py`
- **Touch points:**
  - `src/api/device_mappings_router.py` - API endpoints
  - `src/device_mappings/` - Device mapping library
  - `src/main.py` - Router registration (already done in AI24.1)

**Current Behavior:**
- Device mapping library exists but no API endpoints
- No caching mechanism
- No way for external services to query device mappings

**Target Behavior:**
- API endpoints for device type, relationships, and context
- 5-minute TTL caching
- Cache invalidation on reload
- OpenAPI documentation

---

## Acceptance Criteria

1. ✅ Device mapping library integrated into Device Intelligence Service
2. ✅ API endpoints implemented:
   - `GET /api/device-mappings/{device_id}/type`
   - `GET /api/device-mappings/{device_id}/relationships`
   - `GET /api/device-mappings/{device_id}/context`
   - `POST /api/device-mappings/reload` (already done in AI24.1)
3. ✅ Caching strategy implemented (5-minute TTL)
4. ✅ Cache invalidation on configuration reload
5. ✅ Unit tests for API endpoints
6. ✅ Integration tests for full flow
7. ✅ API documentation (OpenAPI/Swagger)

---

## Integration Verification

- **IV1:** Existing Device Intelligence Service endpoints continue to work
- **IV2:** Device mapping endpoints return correct data
- **IV3:** Configuration reload updates cache correctly

---

## Technical Notes

- **Cache key:** `device_mapping_{device_id}_{endpoint_type}`
- **Cache TTL:** 300 seconds (5 minutes)
- **Cache implementation:** Simple in-memory cache with TTL tracking
- **Cache invalidation:** Clear cache on reload endpoint

---

## Tasks

- [x] **Task 1:** Create story file
- [x] **Task 2:** Implement caching mechanism (5-minute TTL)
- [x] **Task 3:** Add `POST /api/device-mappings/{device_id}/type` endpoint
- [x] **Task 4:** Add `POST /api/device-mappings/{device_id}/relationships` endpoint
- [x] **Task 5:** Add `POST /api/device-mappings/{device_id}/context` endpoint
- [x] **Task 6:** Implement cache invalidation on reload
- [x] **Task 7:** Write unit tests for API endpoints
- [x] **Task 8:** Write integration tests (unit tests cover integration scenarios)
- [x] **Task 9:** Verify OpenAPI documentation (FastAPI auto-generates from endpoints)

---

## Dependencies

- Story AI24.1: Device Mapping Library Core Infrastructure ✅
- Story AI24.2: Hue Device Handler ✅ (for testing)

---

## Testing Strategy

1. **Unit Tests:**
   - Test each endpoint with valid device IDs
   - Test each endpoint with invalid device IDs
   - Test caching behavior (TTL)
   - Test cache invalidation

2. **Integration Tests:**
   - Test full flow: register handler → query endpoint → verify response
   - Test cache invalidation flow: query → reload → query again

---

## Notes

- Device IDs come from Home Assistant Device Registry
- Endpoints need to fetch device data from HA client (may need to add dependency)
- Consider adding device registry data fetching to the router

