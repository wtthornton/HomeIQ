# Device Detection Enhancement Plan

## Problem Statement

Current system over-expands device selection when users specify compound device names like "Office WLED device". Instead of matching the specific device, it expands to all devices in the Office area, resulting in 15+ devices being selected instead of 1.

## Solution Overview

Two-stage approach leveraging 2025 Home Assistant API best practices:
1. **Stage 1**: Area/location detection and filtering (reduces search space by ~90%)
   - Uses Entity Registry API for reliable area_id metadata
   - Template API for efficient large-area queries (>50 entities)
2. **Stage 2**: Fuzzy device matching with normalization (handles typos, case variations, abbreviations)
   - Uses Entity Registry `name` field (source of truth, what shows in HA UI)
   - Parallel fuzzy matching for large candidate sets (>50 entities)

## 2025 Home Assistant API Best Practices

This plan leverages 2025 HA API best practices:

### ✅ Real-Time API Queries (Not Cached Database)
- **Entity Registry API**: `GET /api/config/entity_registry/list` - Source of truth for entity names and metadata
- **Area Registry API**: `GET /api/config/area_registry/list` - Canonical area data with aliases
- **States API**: `GET /api/states` - Fallback for area filtering when Entity Registry unavailable
- **Template API**: `POST /api/template` - Most efficient for large area queries (>50 entities)

### ✅ Entity Registry First (Not States API)
- **Priority**: Entity Registry `name` field > `original_name` > `friendly_name`
- **Reason**: Entity Registry contains canonical names as shown in HA UI
- **Metadata**: Includes `area_id`, `platform`, `device_id` (more reliable than States API attributes)

### ✅ Performance Optimizations
- **Template API**: Use for large area queries (better than fetching all states)
- **Parallel Processing**: Use `asyncio.gather()` for fuzzy matching >50 candidates
- **Caching**: Area registry cached with 5-minute TTL (configurable)
- **Early Termination**: Exact matches return immediately (no fuzzy scoring needed)

### ✅ Error Handling (2025 Standards)
- **404 Errors**: Expected for some HA versions (gracefully handled)
- **Connection Errors**: Propagated as `ConnectionError` (don't hide network issues)
- **Auth Errors (401/403)**: Propagated as `PermissionError` (don't hide auth issues)
- **Server Errors (500+)**: Logged with full traceback and propagated

### ✅ Leveraging Existing Methods
- **HA Client Methods**: Uses existing `get_entity_registry()`, `get_entities_by_area_and_domain()`, `get_entities_by_area_template()`
- **No Duplication**: Reuses existing HA client infrastructure
- **Consistency**: Follows existing patterns in codebase

### 🔮 Future Enhancement (Not in Scope)
- **Assist API**: `POST /api/conversation/process` - Consider for entity resolution from natural language
  - HA's built-in entity matching (better than custom implementation)
  - Requires HA 2024.5+ and may not suit all query types

## Implementation Tasks

### Phase 1: Normalization Utilities

**File**: `services/ai-automation-service/src/utils/device_normalization.py` (NEW)

Create new utility module with:
- `normalize_device_query(query: str) -> list[str]`: Normalize and tokenize device query
  - Lowercase conversion
  - Remove stop words ("the", "device", "light", etc.)
  - Tokenize compound names ("Office WLED" -> ["office", "wled"])
  - Handle abbreviations (LED -> WLED substring matching)
  
- `normalize_entity_name(entity: dict) -> list[str]`: Normalize entity names (2025 best practice)
  - **2025 Best Practice**: Priority order for Entity Registry entries:
    1. `name` - Entity Registry name (source of truth, what shows in HA UI)
    2. `original_name` - Entity Registry original name
    3. `name_by_user` - User-customized name (if available)
    4. `friendly_name` - States API friendly_name (fallback only)
  - For States API entities (when Entity Registry unavailable):
    1. `friendly_name` - States API friendly_name
    2. `entity_id` - Use entity_id as last resort
  - Lowercase and tokenize
  - Extract platform/integration for matching (from `platform` field in Entity Registry)

- `normalize_area_name(area: str) -> str`: Normalize area names
  - Lowercase
  - Remove articles ("the office" -> "office")
  - Handle variations ("living room" vs "livingroom" vs "living-room")
  - Remove common words ("room", "area", "space")

### Phase 2: Device Matching Service Module

**File**: `services/ai-automation-service/src/services/device_matching.py` (NEW)

Create new service module to encapsulate device matching logic:

**Class: `DeviceMatchingService`**
- `async def match_devices_to_entities()`: Main entry point (moved from `map_devices_to_entities()`)
  - Implements two-stage matching:
    - Stage 1: Area filtering (if area detected)
    - Stage 2: Enhanced fuzzy matching with ensemble scoring
  - Returns dict mapping device_name -> entity_id

- `async def _detect_and_filter_by_area()`: Stage 1 area detection and filtering (2025 best practice)
  - Get area registry from HA client (cached via `get_area_registry()`)
  - Extract area mentions from query using normalization
  - Normalize and fuzzy match against HA area registry
  - **2025 Best Practice**: Use Entity Registry API for area filtering (not States API)
    - Entity Registry includes `area_id` for each entity (more reliable)
    - Use `get_entity_registry()` and filter by `area_id` field
    - OR use existing `get_entities_by_area_and_domain()` method (uses States API as fallback)
  - Pre-filter entities by area_id if area found
  - **2025 Optimization**: Consider Template API for large area queries (better performance)
    - Use `get_entities_by_area_template()` when entity count > 50
  - Return filtered entity set

- `async def _fuzzy_match_devices()`: Stage 2 fuzzy matching (2025 enhanced)
  - Normalize device queries and entity names
  - **2025 Best Practice**: Use Entity Registry names for matching (not States API friendly_name)
    - Entity Registry `name` field is source of truth (what shows in HA UI)
    - Fallback to `original_name` or `friendly_name` if `name` missing
  - Calculate ensemble scores (40% exact, 30% tokens, 20% fuzzy, 10% context)
  - Early termination on exact matches
  - **2025 Optimization**: Parallel fuzzy matching for large candidate sets (>50 entities)
    - Use `asyncio.gather()` for concurrent scoring
  - Return top matches based on thresholds

- `def _calculate_ensemble_score()`: Scoring formula implementation
  - Exact match (40% weight) - early termination
  - All tokens present (30% weight)
  - Fuzzy similarity WRatio (20% weight)
  - Context bonuses (10% weight: area + platform + domain)
  - Cap at 1.0

- `def _pre_consolidate_device_names()`: Helper moved from router
- `def consolidate_devices_involved()`: Helper moved from router

**Move from router:**
- Move `map_devices_to_entities()` function (line 1180) to this service
- Move `_pre_consolidate_device_names()` helper (line 1655) to this service
- Move `consolidate_devices_involved()` helper (line 1748) to this service

### Phase 3: Area Registry Caching (2025 Best Practice)

**File**: `services/ai-automation-service/src/clients/ha_client.py`

Add area registry caching with 2025 HA API best practices:
- New method: `async def get_area_registry(self) -> dict[str, dict[str, Any]]`
  - Calls `GET /api/config/area_registry/list` (HA REST API - 2025 format)
  - Returns dict mapping area_id -> area data (name, aliases, normalized_name, etc.)
  - Uses Entity Registry API pattern for consistency with existing `get_entity_registry()` method

- Cache implementation (2025 best practices):
  - In-memory LRU cache (class-level)
  - Cache key: `area_registry`
  - TTL: 300 seconds (5 minutes) - configurable via settings
  - Graceful error handling:
    - 404: Expected (some HA versions don't expose this endpoint) - returns empty dict
    - Connection errors: Propagated as ConnectionError (real error)
    - 401/403: Propagated as PermissionError (real error)
    - 500+: Logged and propagated (real error)
  - Cache invalidation: Manual refresh method for testing/forced updates
  - Fallback to data-api only if HA API unavailable (not for 404)

- **2025 Enhancement**: Use Entity Registry metadata for area matching
  - Entity Registry includes `area_id` in each entity entry
  - More reliable than States API `attributes.area_id` (can be missing)
  - Provides canonical area names from Area Registry

### Phase 4: Router Cleanup and Integration

**File**: `services/ai-automation-service/src/api/ask_ai_router.py`

**Remove from router:**
- Remove `map_devices_to_entities()` function (line 1180) - moved to service
- Remove `_pre_consolidate_device_names()` helper (line 1655) - moved to service
- Remove `consolidate_devices_involved()` helper (line 1748) - moved to service

**Update router to use service:**
- Import `DeviceMatchingService` from `..services.device_matching`
- In `generate_suggestions_from_query()` (around line 3924):
  - Replace direct call to `map_devices_to_entities()` with service call
  - Pass area context from area detection to service
- In `process_natural_language_query()` endpoint (around line 4397):
  - Ensure area detection happens before entity expansion
  - Pass detected area to `generate_suggestions_from_query()` as `area_filter`
  - Service will handle area filtering internally

**Update area detection in `generate_suggestions_from_query()`:**
- Before entity expansion (around line 2890-2910):
  1. Get area registry from HA client (cached)
  2. Extract area mentions from query using existing `extract_area_from_request()`
  3. Normalize extracted areas using `normalize_area_name()`
  4. Fuzzy match against HA area registry (threshold 0.80)
  5. Pass detected area to DeviceMatchingService

- Update entity fetching logic (around line 2972-2994) - **2025 Best Practice**:
  - **CRITICAL**: Use HA API directly for real-time entity queries (not cached database)
  - If area detected: Use HA client method (2025 best practice):
    - **Primary**: `ha_client.get_entity_registry()` + filter by `area_id` (most reliable)
    - **Fallback**: `ha_client.get_entities_by_area_and_domain()` (uses States API)
    - **Optimization**: `ha_client.get_entities_by_area_template()` for large queries (>50 entities)
    - **NOT**: `data-api` queries (cached/stale data) - only use as last resort fallback
  - Limit to 100 entities max for fuzzy matching performance
  - **2025 Enhancement**: Use Entity Registry metadata for entity names
    - Entity Registry provides canonical names (`name`, `original_name`)
    - More accurate than States API `friendly_name`
  - Pass filtered entities to DeviceMatchingService with registry metadata

### Phase 5: Entity Validator Updates

**File**: `services/ai-automation-service/src/services/entity_validator.py`

Update `_get_available_entities()` method (if exists):
- Support area_id filtering via data-api
- Return limited results (max 100) for performance
- Used by DeviceMatchingService for area filtering

### Phase 6: Configuration

**File**: `services/ai-automation-service/src/config.py`

Add new configuration settings:
- `device_matching_auto_select_threshold: float = 0.90` - Auto-select if single match above this
- `device_matching_high_confidence_threshold: float = 0.85` - Return top 3 if above this
- `device_matching_minimum_threshold: float = 0.70` - Minimum score to consider
- `device_matching_area_fuzzy_threshold: float = 0.80` - Area name fuzzy matching threshold
- `device_matching_max_candidates: int = 100` - Max entities for fuzzy matching

### Phase 7: Testing

Create test cases:
- Exact matches: "Office WLED" -> "Office WLED"
- Case variations: "office wled" -> "Office WLED"
- Abbreviations: "LED" -> "WLED" (substring match)
- Area + device: "Office WLED" -> matches only Office area devices
- Multiple areas: "Office and Kitchen lights" -> matches both areas
- No area: "WLED" -> matches all WLED devices
- Typos: "offis wled" -> "Office WLED"
- Generic names: "light" -> requires area context

## Performance Targets (2025 Optimized)

- Area detection: <10ms (cached area registry)
- Area filtering (2025 methods):
  - Entity Registry filter: <20ms (HA API call + in-memory filter)
  - States API filter: <30ms (HA API call + client-side filter)
  - Template API filter: <15ms (HA Template API, most efficient for large queries)
- Entity normalization: <5ms (in-memory)
- Fuzzy matching (100 candidates):
  - Sequential: <30ms (rapidfuzz C-optimized)
  - **2025 Parallel** (>50 candidates): <20ms (asyncio.gather concurrent scoring)
- Total (cached, Entity Registry): <55ms (well under 500ms target)
- Total (uncached, Entity Registry): <120ms (still under target)
- Total (Template API for large areas): <80ms (better than States API for >50 entities)

**2025 Performance Notes:**
- Template API recommended for large area queries (>50 entities)
- Entity Registry provides better metadata but slightly slower than States API
- Parallel fuzzy matching improves performance for large candidate sets

## Success Criteria (2025 Enhanced)

1. "Office WLED device" query selects only "Office WLED" entity, not all 15 Office devices
2. Area filtering reduces candidate set by ~90% (200 entities -> 20 entities)
   - **2025**: Uses Entity Registry or Template API for efficient filtering
3. Exact matches return immediately (early termination)
4. Fuzzy matching handles typos, case variations, abbreviations
   - **2025**: Uses Entity Registry `name` field (more accurate than States API)
5. Performance stays under 120ms for cached requests (Entity Registry API)
   - Template API queries: <80ms for large areas
6. **2025 Best Practice**: Graceful error handling with proper error propagation
   - 404s handled gracefully (some HA versions don't expose all endpoints)
   - Connection/auth errors propagated correctly (not hidden)
7. **2025 Enhancement**: Real-time entity queries (not cached database)
   - Queries HA API directly during suggestion generation
   - Falls back to cached data only if HA API unavailable
8. **2025 Accuracy**: Uses Entity Registry metadata for better matching
   - Entity Registry `name` field used (source of truth)
   - Platform/integration data from Entity Registry

## Dependencies

- Existing: `rapidfuzz` (already in use)
- Existing: `fuzzy_match_with_context()` utility from `utils/fuzzy.py`
- Existing: HA client methods (2025 best practices):
  - `get_entity_registry()` - Entity Registry API (source of truth for names)
  - `get_entities_by_area_and_domain()` - States API with area filtering
  - `get_entities_by_area_template()` - Template API for efficient queries
- Existing: `EntityAttributeService` for entity enrichment
- New: `get_area_registry()` method in HA client (REST API)
- **2025 Enhancement**: Entity Registry API for metadata (not States API)
  - More reliable area_id, canonical names, platform information
- **2025 Optimization**: Template API for large area queries (>50 entities)
  - Better performance than fetching all states and filtering

## File Structure Changes

**New Files:**
- `services/ai-automation-service/src/utils/device_normalization.py` - Normalization utilities
- `services/ai-automation-service/src/services/device_matching.py` - Device matching service

**Modified Files:**
- `services/ai-automation-service/src/api/ask_ai_router.py` - Remove matching logic, call service instead, use HA API directly
- `services/ai-automation-service/src/clients/ha_client.py` - Add area registry caching (2025 REST API format)
- `services/ai-automation-service/src/config.py` - Add device matching configuration
- `services/ai-automation-service/src/services/entity_validator.py` - Support area filtering using HA API (not data-api)

**2025 API Enhancements:**
- Leverage existing `get_entity_registry()` for metadata (source of truth for names)
- Leverage existing `get_entities_by_area_and_domain()` for area filtering
- Leverage existing `get_entities_by_area_template()` for large queries
- Use Entity Registry API instead of States API when possible (more reliable metadata)

## Risk Mitigation (2025 Best Practices)

- **HA API Availability**:
  - If area registry API unavailable (404): Log info (expected for some HA versions), use Entity Registry area_id field instead
  - If Entity Registry API unavailable (404): Fallback to States API (`get_entities_by_area_and_domain()`)
  - If HA API unavailable (connection error): Fallback to data-api (cached) with warning log
  - **2025 Best Practice**: Never silently fail - propagate real errors (ConnectionError, PermissionError)

- **Performance**:
  - If area detection fails: Skip to device matching (graceful degradation)
  - If fuzzy matching too slow: Limit candidates to 50 instead of 100
  - **2025 Optimization**: Use Template API for large queries (better than fetching all states)
  - **2025 Enhancement**: Parallel fuzzy matching for >50 candidates using `asyncio.gather()`

- **Accuracy**:
  - If scoring produces false positives: Increase thresholds incrementally
  - **2025 Best Practice**: Use Entity Registry names (not States API friendly_name) for better accuracy
  - **2025 Enhancement**: Weight Entity Registry `name` higher than `friendly_name` in scoring

- **Error Handling** (2025 standards):
  - Connection errors: Propagate as ConnectionError (don't hide network issues)
  - Authentication errors (401/403): Propagate as PermissionError (don't hide auth issues)
  - Server errors (500+): Log with full traceback and propagate
  - Expected 404s: Return empty result gracefully (some HA versions don't expose all endpoints)

## Scoring Formula

```python
score = 0.0

# Exact match (40% weight) - early termination
if normalized_query_tokens == normalized_entity_tokens:
    return 1.0

# All tokens present (30% weight)
if all(token in entity_tokens for token in query_tokens):
    score += 0.9 * 0.30

# Fuzzy similarity (20% weight)
fuzzy_score = rapidfuzz.fuzz.WRatio(normalized_query, normalized_entity) / 100.0
if fuzzy_score > 0.7:
    score += fuzzy_score * 0.20

# Context bonuses (10% weight, additive, capped at 1.0)
if area_match: score += 0.05
if platform_match: score += 0.03
if domain_match: score += 0.02

score = min(score, 1.0)  # Cap at 1.0
```

