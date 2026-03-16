---
epic: ha-naming-convention
priority: P1 High
status: in-progress
estimated_duration: 3-4 weeks across 3 epics
risk_level: medium
source: docs/ha-naming-convention.md — naming convention for AI discovery
type: feature
---

# Epics 62-64: HA Entity Naming Convention for AI Discovery

**Status:** Epic 62 COMPLETE, Epic 63 COMPLETE, Epic 64 Planned
**Priority:** P1 High (Epic 62-63), P2 Medium (Epic 64)
**Duration:** 3-4 weeks across 3 epics
**Risk Level:** Medium — cross-cutting (data-api, admin-api, entity resolution, health-dashboard, device-intelligence)
**Source:** [docs/ha-naming-convention.md](../docs/ha-naming-convention.md) — naming convention specification
**Affects:** `core-platform/data-api`, `core-platform/admin-api`, `core-platform/health-dashboard`, `automation-core/ha-ai-agent-service`, `automation-core/ha-device-control`, `ml-engine/device-intelligence-service`

## Context

HomeIQ's entity resolution uses fuzzy matching and keyword scoring to compensate for inconsistent HA entity naming. The naming convention document defines standards for areas, entity IDs, friendly names, labels, aliases, and device classes — but the codebase doesn't enforce or leverage them yet.

### Current Gaps

| Gap | Impact | Fix |
|---|---|---|
| Hardcoded area list in `entity_resolution_service.py` (8 areas) | Misses any area not in the list | Dynamic area lookup from entity cache |
| Labels stored but never queried or filtered | AI can't filter by `ai:automatable` vs `ai:ignore` | Label-aware entity resolution + query endpoints |
| Aliases stored but only used for scoring bonus | No dedicated alias search endpoint | Full alias resolution in entity resolver |
| No entity management UI in health-dashboard | Users must use HA UI for labels/aliases | Label/alias editor in health-dashboard |
| No naming quality feedback | Users don't know if their names help AI | Convention compliance scoring |
| No bulk entity audit | Cleanup requires entity-by-entity review | Audit page with bulk actions |

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Health Dashboard (port 3000)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ HA Setup     │  │ Label/Alias  │  │ Convention Compliance  │ │
│  │ Wizard (new) │  │ Editor (new) │  │ Dashboard (new)        │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘ │
└─────────┼─────────────────┼──────────────────────┼──────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│ admin-api:8004  │  │ data-api:8006   │  │ device-intelligence │
│                 │  │                 │  │       :8028         │
│ POST /entities/ │  │ GET /entities   │  │                     │
│   {id}/labels   │  │   ?label=X      │  │ GET /naming/audit   │
│ POST /entities/ │  │   ?has_alias=1  │  │ GET /naming/score   │
│   {id}/aliases  │  │ GET /areas      │  │ POST /naming/       │
│ POST /entities/ │  │ GET /labels     │  │   suggest-aliases   │
│   bulk-label    │  │                 │  │                     │
│ PUT /entities/  │  │ Internal:       │  │                     │
│   {id}/name     │  │ GET /internal/  │  │                     │
│                 │  │   areas/list    │  │                     │
└─────────────────┘  └─────────────────┘  └─────────────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              Entity Resolution (ha-ai-agent-service)            │
│  ┌────────────────────┐  ┌───────────────────────────────────┐  │
│  │ Dynamic area       │  │ Label-aware filtering             │  │
│  │ extraction (new)   │  │ ai:ignore → skip                 │  │
│  │ from entity cache  │  │ ai:critical → require confirm    │  │
│  └────────────────────┘  └───────────────────────────────────┘  │
│  ┌────────────────────┐  ┌───────────────────────────────────┐  │
│  │ Alias-first        │  │ Device class boost               │  │
│  │ matching (new)     │  │ in scoring (new)                 │  │
│  └────────────────────┘  └───────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│              Entity Resolver (ha-device-control)                │
│  ┌────────────────────┐  ┌───────────────────────────────────┐  │
│  │ Label-aware        │  │ Alias resolution                 │  │
│  │ resolve() (new)    │  │ tier (new)                       │  │
│  └────────────────────┘  └───────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Epic 62: Entity Convention API Foundation

**Priority:** P1 High | **Duration:** 1-2 weeks | **Stories:** 8
**Enhances:** `data-api`, `admin-api`, `ha-ai-agent-service`, `ha-device-control`

### Problem

The data layer stores labels, aliases, and areas but doesn't expose them as queryable dimensions. Entity resolution uses a hardcoded area list and ignores labels entirely. There are no endpoints for managing labels/aliases — users must go to the HA UI.

---

### Story 62.1: Dynamic Area List Endpoint (data-api) — DONE

**Priority:** High | **Estimate:** 2h | **Risk:** Low | **Status:** DONE

Add an endpoint that returns all distinct areas from the entity cache, replacing the hardcoded area list.

**Endpoints:**
- `GET /api/areas` — Public. Returns distinct `area_id` values with entity counts.
- `GET /internal/areas/list` — Internal. Returns area list for inter-service use (no auth).

**Response Model:**
```python
class AreaResponse(BaseModel):
    area_id: str          # e.g., "kitchen"
    display_name: str     # e.g., "Kitchen" (title-cased)
    entity_count: int     # number of entities in this area
    domains: list[str]    # distinct domains in this area (light, sensor, etc.)
```

**Implementation:**
- Query: `SELECT area_id, COUNT(*) as entity_count FROM entities WHERE area_id IS NOT NULL GROUP BY area_id`
- Derive `display_name` from `area_id`: replace `_` with space, title case
- Add `domains` subquery: distinct domains per area
- Cache result in-memory (60s TTL) — areas change rarely

**Files:**
- `domains/core-platform/data-api/src/devices_endpoints.py` — add `/api/areas` route
- `domains/core-platform/data-api/src/devices_endpoints.py` — add `/internal/areas/list` route

**Acceptance Criteria:**
- [ ] `GET /api/areas` returns all areas with entity counts and domain lists
- [ ] `GET /internal/areas/list` returns same data without auth
- [ ] Empty areas (no entities) are excluded
- [ ] Response cached for 60s

---

### Story 62.2: Label Query Endpoints (data-api) — DONE

**Priority:** High | **Estimate:** 3h | **Risk:** Low | **Status:** DONE

Add label-based entity filtering and a labels inventory endpoint.

**Endpoints:**
- `GET /api/entities?label={label}` — Filter entities by label (existing endpoint, new query param)
- `GET /api/labels` — Returns all distinct labels with entity counts

**Response Model (labels):**
```python
class LabelResponse(BaseModel):
    label: str            # e.g., "ai:automatable"
    entity_count: int     # entities with this label
    prefix: str           # e.g., "ai" (derived from label)
```

**Implementation:**
- Entity label filter: `WHERE entities.labels @> '["ai:automatable"]'::jsonb` (PostgreSQL JSONB containment)
- Labels inventory: query distinct values from JSONB array across all entities
- Add `label` query parameter to existing `/api/entities` endpoint
- Index: `CREATE INDEX idx_entity_labels ON entities USING GIN (labels)` (GIN index for JSONB array)

**Files:**
- `domains/core-platform/data-api/src/devices_endpoints.py` — extend entity list endpoint + add `/api/labels`
- `domains/core-platform/data-api/src/models/entity.py` — add GIN index on `labels`
- Alembic migration for GIN index

**Acceptance Criteria:**
- [ ] `GET /api/entities?label=ai:automatable` returns only entities with that label
- [ ] `GET /api/entities?label=ai:ignore` works for exclusion discovery
- [ ] Multiple labels supported: `?label=ai:automatable&label=sensor:primary`
- [ ] `GET /api/labels` returns all labels with counts, grouped by prefix
- [ ] GIN index on labels column for performance

---

### Story 62.3: Alias Search Endpoint (data-api) — DONE

**Priority:** High | **Estimate:** 2h | **Risk:** Low | **Status:** DONE

Add alias-based entity search — find entities by matching against their aliases array.

**Endpoints:**
- `GET /api/entities?alias={search_term}` — Search entities whose aliases contain the term
- `GET /api/entities?has_aliases=true` — Filter to entities that have aliases set
- `GET /api/entities?has_aliases=false` — Filter to entities missing aliases (for audit)

**Implementation:**
- Alias search: `WHERE EXISTS (SELECT 1 FROM jsonb_array_elements_text(aliases) a WHERE a ILIKE '%kitchen lights%')`
- Has-aliases filter: `WHERE aliases IS NOT NULL AND aliases != '[]'::jsonb`
- Add GIN index on aliases: `CREATE INDEX idx_entity_aliases ON entities USING GIN (aliases)`

**Files:**
- `domains/core-platform/data-api/src/devices_endpoints.py` — extend entity list endpoint
- `domains/core-platform/data-api/src/models/entity.py` — add GIN index on `aliases`
- Alembic migration for GIN index

**Acceptance Criteria:**
- [ ] `GET /api/entities?alias=kitchen lights` finds entities with that alias
- [ ] Alias search is case-insensitive
- [ ] `GET /api/entities?has_aliases=false` returns entities without aliases (audit use)
- [ ] GIN index on aliases column

---

### Story 62.4: Entity Label & Alias Management (admin-api) — DONE

**Priority:** High | **Estimate:** 3h | **Risk:** Medium | **Status:** DONE

Add CRUD endpoints for managing labels and aliases on entities. These write to HomeIQ's database AND sync back to Home Assistant via the HA REST API.

**Endpoints:**
- `PUT /api/v1/entities/{entity_id}/labels` — Set labels for an entity
- `PUT /api/v1/entities/{entity_id}/aliases` — Set aliases for an entity
- `PUT /api/v1/entities/{entity_id}/name` — Set `name_by_user` (friendly name override)
- `POST /api/v1/entities/bulk-label` — Add/remove a label across multiple entities

**Request Models:**
```python
class SetLabelsRequest(BaseModel):
    labels: list[str]  # ["ai:automatable", "sensor:primary"]

class SetAliasesRequest(BaseModel):
    aliases: list[str]  # ["kitchen lights", "the big light"]

class SetNameRequest(BaseModel):
    name_by_user: str  # "Kitchen Ceiling Light"

class BulkLabelRequest(BaseModel):
    entity_ids: list[str]      # ["light.kitchen_1", "light.kitchen_2"]
    add_labels: list[str]      # Labels to add
    remove_labels: list[str]   # Labels to remove
```

**Implementation:**
- Write to HomeIQ's PostgreSQL (`entities` table) via data-api internal endpoint
- Sync to HA via REST API: `POST /api/config/entity_registry/{entity_id}` with `aliases` and `labels`
- HA sync is best-effort — if HA is unreachable, local DB is updated and sync retried later
- Validate label format: must match `{prefix}:{name}` pattern (e.g., `ai:automatable`)

**Files:**
- `domains/core-platform/admin-api/src/entity_management_endpoints.py` (new)
- `domains/core-platform/admin-api/src/routes.py` — register new router
- `domains/core-platform/admin-api/src/ha_sync_client.py` (new) — HA Entity Registry sync

**Acceptance Criteria:**
- [ ] Labels can be set, added, and removed per entity
- [ ] Aliases can be set per entity
- [ ] Friendly name can be overridden via `name_by_user`
- [ ] Bulk label operations work across multiple entities
- [ ] Changes sync to HA Entity Registry (best-effort)
- [ ] Label format validated (`prefix:name` pattern)
- [ ] All endpoints require auth

---

### Story 62.5: Dynamic Area Resolution (ha-ai-agent-service) — DONE

**Priority:** High | **Estimate:** 2h | **Risk:** Low | **Status:** DONE

Replace the hardcoded `area_keywords` list in `_extract_area_from_prompt()` with dynamic area lookup from the entity cache.

**Current Code (entity_resolution_service.py:173-191):**
```python
# Hardcoded - misses any area not in this list
area_keywords = ["office", "kitchen", "bedroom", "living room", ...]
```

**New Approach:**
- On initialization (or with TTL cache), fetch areas from `data-api /internal/areas/list`
- Build area keyword set from actual area names
- Support multi-word areas ("living room" → match "living room" in prompt)
- Sort by length descending to match longest area first (prevents "bed" matching before "bedroom")

**Files:**
- `domains/automation-core/ha-ai-agent-service/src/services/entity_resolution/entity_resolution_service.py`
- `domains/automation-core/ha-ai-agent-service/src/clients/data_api_client.py` — add `fetch_areas()` method

**Acceptance Criteria:**
- [ ] Area list fetched dynamically from data-api
- [ ] Areas cached with 5-minute TTL
- [ ] Multi-word areas matched correctly ("living room", "master bedroom")
- [ ] Longest-match-first ordering prevents false positives
- [ ] Graceful fallback to hardcoded list if data-api unreachable
- [ ] Unit tests cover new area matching logic

---

### Story 62.6: Label-Aware Entity Filtering (ha-ai-agent-service) — DONE

**Priority:** High | **Estimate:** 3h | **Risk:** Medium | **Status:** DONE

Modify entity resolution to respect AI labels during scoring and filtering.

**New Behavior:**
- **Pre-filter:** Exclude entities with `ai:ignore` label before scoring
- **Confidence boost:** Entities with `ai:automatable` get +0.5 score boost
- **Confirmation flag:** Entities with `ai:critical` are returned with `requires_confirmation=True`
- **Sensor roles:** `sensor:primary` gets priority over other sensors in same area/type
- **Trigger/condition hints:** `sensor:trigger` and `sensor:condition` inform automation suggestions

**Implementation:**
- Add label checks to `_score_entities()` method
- Add `requires_confirmation` field to `EntityResolutionResult`
- Filter `ai:ignore` entities in `resolve_entities()` before scoring step

**Files:**
- `domains/automation-core/ha-ai-agent-service/src/services/entity_resolution/entity_resolution_service.py`
- `domains/automation-core/ha-ai-agent-service/src/services/entity_resolution/entity_resolution_result.py`

**Acceptance Criteria:**
- [ ] `ai:ignore` entities are excluded from resolution
- [ ] `ai:automatable` entities get score boost
- [ ] `ai:critical` entities flagged with `requires_confirmation=True`
- [ ] `sensor:primary` prioritized over non-primary sensors
- [ ] Entities without labels are treated normally (no penalty)
- [ ] Unit tests cover all label behaviors

---

### Story 62.7: Alias-First Resolution Tier (ha-device-control) — DONE

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low | **Status:** DONE

Add alias matching as a resolution tier in `EntityResolver.resolve()`, between friendly_name exact match and partial match.

**Current Resolution Tiers:**
1. Exact entity_id match (confidence 1.0)
2. Exact friendly_name match (confidence 1.0)
3. Partial/substring match on friendly_name (confidence 0.8)
4. Entity_id suffix match (confidence 0.7)

**New Resolution Tiers:**
1. Exact entity_id match (confidence 1.0)
2. Exact friendly_name match (confidence 1.0)
3. **Exact alias match (confidence 0.95)** ← NEW
4. Partial/substring match on friendly_name (confidence 0.8)
5. **Partial alias match (confidence 0.75)** ← NEW
6. Entity_id suffix match (confidence 0.7)

**Implementation:**
- `CachedEntity` needs `aliases: list[str]` field (populated from HA states)
- Add `_match_alias()` method similar to `_match_friendly_name()`
- Alias matching is case-insensitive

**Files:**
- `domains/automation-core/ha-device-control/src/services/entity_resolver.py`

**Acceptance Criteria:**
- [ ] Exact alias match returns confidence 0.95
- [ ] Partial alias match returns confidence 0.75
- [ ] "the big light" alias resolves to `light.kitchen_ceiling_main`
- [ ] Multiple aliases per entity supported
- [ ] Alias matching is case-insensitive

---

### Story 62.8: Alias Scoring in Agent Entity Resolution (ha-ai-agent-service) — DONE

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low | **Status:** DONE

Improve alias scoring in `_score_entities()` — currently aliases get a generic scoring boost; they should get full word-matching treatment.

**Current Code (entity_resolution_service.py:331-334):**
```python
aliases = [a.lower() for a in entity.get("aliases", [])]
search_text = f"{entity_id} {friendly_name} {' '.join(aliases)}"
```

**Enhancement:**
- Score whole-alias matches higher than substring matches
- If user prompt exactly matches an alias, boost to +3.0 (same as pattern match)
- If user prompt contains an alias as a substring, boost to +1.5
- Add alias-count bonus: entities with more relevant aliases get slight boost

**Files:**
- `domains/automation-core/ha-ai-agent-service/src/services/entity_resolution/entity_resolution_service.py`

**Acceptance Criteria:**
- [ ] Exact alias match ("kitchen lights") gets +3.0 score boost
- [ ] Partial alias match gets +1.5 score boost
- [ ] Aliases treated as whole phrases, not split into individual words
- [ ] Unit tests cover alias scoring scenarios

---

## Epic 63: HA Setup Wizard & Entity Management UI

**Priority:** P1 High | **Duration:** 1-2 weeks | **Stories:** 7
**Enhances:** `core-platform/health-dashboard`

### Problem

Users have no guidance on how to set up their HA entities for optimal AI discovery. The naming convention document exists but there's no interactive tool to audit entities, manage labels/aliases, or see what the AI "sees."

---

### Story 63.1: HA Setup Wizard — Tab & Navigation

**Priority:** High | **Estimate:** 2h | **Risk:** Low

Add a new "HA Setup" tab to the health-dashboard under the "Devices & Data" navigation group.

**Implementation:**
- New tab: `HASetupTab.tsx` (lazy-loaded)
- Navigation group: "Devices & Data" → add "HA Setup" after "Devices"
- URL hash: `#ha-setup`
- Sub-navigation within the tab: Audit | Labels | Aliases | Exclusions

**Files:**
- `domains/core-platform/health-dashboard/src/components/tabs/HASetupTab.tsx` (new)
- `domains/core-platform/health-dashboard/src/components/Dashboard.tsx` — add tab to NAV_GROUPS

**Acceptance Criteria:**
- [ ] "HA Setup" tab appears in sidebar under "Devices & Data"
- [ ] Tab lazy-loads (React.lazy + Suspense)
- [ ] Sub-navigation: Audit | Labels | Aliases | Exclusions
- [ ] URL hash navigation works (`#ha-setup`)
- [ ] Loading skeleton while data loads

---

### Story 63.2: Entity Audit View

**Priority:** High | **Estimate:** 4h | **Risk:** Medium

The main audit view shows all entities with a convention compliance score and actionable recommendations.

**UI Components:**
```
┌──────────────────────────────────────────────────────────────┐
│ HA Setup — Entity Audit                        [Refresh] 📊 │
├──────────────────────────────────────────────────────────────┤
│ Overall Score: 72% ████████░░  (412/572 entities compliant) │
│                                                              │
│ ⚠ 89 entities missing area assignment                       │
│ ⚠ 234 entities have no labels                               │
│ ⚠ 312 entities have no aliases                              │
│ ✓ 98% of areas follow naming convention                     │
├──────────────────────────────────────────────────────────────┤
│ Filter: [All ▼] [Area ▼] [Domain ▼] [Issues ▼] [Search___] │
├──────────────────────────────────────────────────────────────┤
│ Entity                    │ Area    │ Labels │ Aliases │ ⚠   │
│───────────────────────────┼─────────┼────────┼─────────┼─────│
│ light.kitchen_ceiling     │ Kitchen │ 2      │ 3       │ ✓   │
│ sensor.hue_motion_1       │ —       │ 0      │ 0       │ ⚠⚠  │
│ binary_sensor.door_1      │ Hall    │ 0      │ 0       │ ⚠   │
└──────────────────────────────────────────────────────────────┘
```

**Features:**
- Fetch all entities from `data-api GET /api/entities?limit=10000`
- Score each entity against naming convention rules:
  - Has area? (+20 pts)
  - Has labels? (+20 pts, +10 if includes AI intent label)
  - Has aliases? (+20 pts)
  - Friendly name follows convention? (+20 pts — starts with area, Title Case, no brand)
  - Device class set? (+20 pts for sensors)
- Sort by score ascending (worst first)
- Filters: area, domain, issue type (missing area, missing labels, etc.)
- Click entity row → expand to show details + quick-edit form

**API Calls:**
- `GET /api/entities?limit=10000` (data-api) — all entities
- `GET /api/areas` (data-api) — area list for filter dropdown

**Files:**
- `domains/core-platform/health-dashboard/src/components/ha-setup/EntityAuditView.tsx` (new)
- `domains/core-platform/health-dashboard/src/components/ha-setup/EntityAuditRow.tsx` (new)
- `domains/core-platform/health-dashboard/src/components/ha-setup/AuditSummaryCards.tsx` (new)
- `domains/core-platform/health-dashboard/src/hooks/useEntityAudit.ts` (new)

**Acceptance Criteria:**
- [ ] All entities loaded and scored against naming convention
- [ ] Summary cards show overall compliance and top issues
- [ ] Table sortable by score, area, domain, issue count
- [ ] Filters for area, domain, and issue type
- [ ] Click to expand entity details
- [ ] Loading skeleton while fetching

---

### Story 63.3: Label Editor Panel

**Priority:** High | **Estimate:** 3h | **Risk:** Low

Inline label editing for entities — add/remove labels from the standard taxonomy.

**UI Components:**
```
┌──────────────────────────────────────────────────────────────┐
│ Labels — light.kitchen_ceiling                               │
├──────────────────────────────────────────────────────────────┤
│ Current: [ai:automatable ×] [group:all-lights ×]            │
│                                                              │
│ Add label: [Select label...     ▼]  [+ Custom]              │
│                                                              │
│ Suggested:                                                   │
│   [+ ai:automatable]  (controllable light)                  │
│   [+ group:all-lights] (light domain)                       │
│   [+ group:night-lights] (if bedroom/hallway)               │
├──────────────────────────────────────────────────────────────┤
│ [Apply to this entity]  [Apply to all lights in Kitchen]    │
└──────────────────────────────────────────────────────────────┘
```

**Features:**
- Display current labels as removable badges
- Dropdown with standard label taxonomy (from naming convention)
- Custom label input with `prefix:name` validation
- Smart suggestions based on entity domain, device_class, and area
- Bulk apply: apply same labels to all entities matching a filter
- Save via `PUT /api/v1/entities/{id}/labels` (admin-api)

**Suggestion Rules:**
- `light.*` → suggest `ai:automatable`, `group:all-lights`
- `sensor.* + device_class=temperature` → suggest `sensor:primary`, `ai:monitor-only`
- `binary_sensor.* + device_class=motion` → suggest `sensor:trigger`
- `cover.*` or `lock.*` → suggest `ai:critical`
- `sensor.* + device_class=battery` → suggest `sensor:diagnostic`, `ai:ignore`

**API Calls:**
- `PUT /api/v1/entities/{entity_id}/labels` (admin-api) — set labels
- `POST /api/v1/entities/bulk-label` (admin-api) — bulk label operations
- `GET /api/labels` (data-api) — existing labels for dropdown

**Files:**
- `domains/core-platform/health-dashboard/src/components/ha-setup/LabelEditor.tsx` (new)
- `domains/core-platform/health-dashboard/src/components/ha-setup/LabelBadge.tsx` (new)
- `domains/core-platform/health-dashboard/src/components/ha-setup/LabelSuggestions.tsx` (new)
- `domains/core-platform/health-dashboard/src/hooks/useEntityLabels.ts` (new)

**Acceptance Criteria:**
- [ ] Current labels displayed as removable badges
- [ ] Standard label taxonomy in dropdown
- [ ] Custom label input with format validation
- [ ] Smart label suggestions based on entity attributes
- [ ] Bulk apply to filtered entities
- [ ] Saves via admin-api with HA sync
- [ ] Optimistic UI updates

---

### Story 63.4: Alias Editor Panel

**Priority:** High | **Estimate:** 3h | **Risk:** Low

Inline alias editing with auto-suggestions based on entity name patterns.

**UI Components:**
```
┌──────────────────────────────────────────────────────────────┐
│ Aliases — light.kitchen_ceiling (Kitchen Ceiling Light)      │
├──────────────────────────────────────────────────────────────┤
│ Current aliases:                                             │
│   [kitchen lights ×]  [kitchen light ×]  [the big light ×]  │
│                                                              │
│ Add alias: [___________________________] [+ Add]            │
│                                                              │
│ Suggestions (click to add):                                  │
│   [+ kitchen light]   (singular of friendly name)           │
│   [+ kitchen lights]  (plural of friendly name)             │
│   [+ ceiling light]   (without area prefix)                 │
│   [+ main light]      (qualifier + type)                    │
└──────────────────────────────────────────────────────────────┘
```

**Features:**
- Display current aliases as removable tags
- Free-text input for custom aliases
- Auto-generated suggestions from friendly name:
  - Singular/plural variants
  - Without area prefix (if area is clear from context)
  - Abbreviations (TV, AC, etc.)
  - Qualifier + type combinations
- Duplicate detection (warn if alias matches another entity)
- Save via `PUT /api/v1/entities/{id}/aliases` (admin-api)

**API Calls:**
- `PUT /api/v1/entities/{entity_id}/aliases` (admin-api) — set aliases
- `GET /api/entities?alias={term}` (data-api) — check for alias conflicts

**Files:**
- `domains/core-platform/health-dashboard/src/components/ha-setup/AliasEditor.tsx` (new)
- `domains/core-platform/health-dashboard/src/components/ha-setup/AliasSuggestions.tsx` (new)
- `domains/core-platform/health-dashboard/src/hooks/useEntityAliases.ts` (new)

**Acceptance Criteria:**
- [ ] Current aliases displayed as removable tags
- [ ] Free-text alias input
- [ ] Auto-suggestions from friendly name patterns
- [ ] Duplicate alias detection (warns if another entity has same alias)
- [ ] Saves via admin-api with HA sync
- [ ] Optimistic UI updates

---

### Story 63.5: Friendly Name Editor

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low

Quick inline editing of entity friendly names with convention guidance.

**UI Components:**
```
┌──────────────────────────────────────────────────────────────┐
│ Name — sensor.hue_motion_1                                   │
├──────────────────────────────────────────────────────────────┤
│ Current: Hue motion sensor 1                                 │
│ Suggested: Kitchen Motion Sensor                             │
│                                                              │
│ New name: [Kitchen Motion Sensor          ]                  │
│                                                              │
│ Convention check:                                            │
│   ✓ Starts with area name (Kitchen)                         │
│   ✓ Title Case                                              │
│   ✓ No manufacturer name                                    │
│   ✓ No model number                                         │
│   ⚠ Consider adding position (if multiple motion sensors)   │
│                                                              │
│ [Save]  [Use suggestion]  [Cancel]                          │
└──────────────────────────────────────────────────────────────┘
```

**Features:**
- Show current name and AI-suggested name (from device-intelligence name_generator)
- Live convention check as user types:
  - Starts with area name? (check against areas list)
  - Title Case?
  - Contains manufacturer/model strings?
  - Appropriate length?
- Save sets `name_by_user` which takes priority in friendly_name computation

**API Calls:**
- `PUT /api/v1/entities/{entity_id}/name` (admin-api) — set name_by_user
- `GET /api/areas` (data-api) — validate area prefix
- `GET /api/device-intelligence/naming/suggest?entity_id={id}` (device-intelligence) — name suggestion

**Files:**
- `domains/core-platform/health-dashboard/src/components/ha-setup/NameEditor.tsx` (new)
- `domains/core-platform/health-dashboard/src/components/ha-setup/ConventionChecker.tsx` (new)

**Acceptance Criteria:**
- [ ] Current name displayed with suggested alternative
- [ ] Live convention check while typing
- [ ] "Use suggestion" button applies AI-generated name
- [ ] Save updates `name_by_user` via admin-api
- [ ] Convention violations shown inline

---

### Story 63.6: Exclusion Manager

**Priority:** Medium | **Estimate:** 3h | **Risk:** Low

UI for managing entity blacklist/exclusion patterns — entities the AI should ignore.

**UI Components:**
```
┌──────────────────────────────────────────────────────────────┐
│ Exclusions — Entities hidden from AI                         │
├──────────────────────────────────────────────────────────────┤
│ Glob Patterns:                                               │
│   [sensor.*_battery        ×] (142 entities matched)        │
│   [sensor.*_signal_strength ×] (38 entities matched)        │
│   [update.*                ×] (27 entities matched)         │
│   [___________________________] [+ Add Pattern]             │
│                                                              │
│ Labeled ai:ignore (auto-excluded):                          │
│   sensor.hacs_updates (HACS Updates)                        │
│   button.zigbee_identify (Zigbee Identify)                  │
│   ... 14 more                                               │
│                                                              │
│ Suggested exclusions:                                        │
│   [+ sensor.*_linkquality]  (23 entities — Zigbee diag)    │
│   [+ number.*_calibration*] (8 entities — device config)   │
├──────────────────────────────────────────────────────────────┤
│ Preview: 244 entities excluded / 572 total (43%)            │
│ [Show excluded entities]                                     │
└──────────────────────────────────────────────────────────────┘
```

**Features:**
- Manage glob patterns for entity exclusion (from Epic 25.2 blacklist)
- Show `ai:ignore` labeled entities (auto-excluded by label-aware filtering)
- Pattern preview: show how many entities each pattern matches
- Suggested exclusion patterns based on common diagnostic entity patterns
- Preview total exclusion impact

**API Calls:**
- Blacklist CRUD via admin-api (existing from Epic 25.2)
- `GET /api/entities?label=ai:ignore` (data-api) — show auto-excluded entities
- `GET /api/entities` (data-api) — for pattern preview/match counting

**Files:**
- `domains/core-platform/health-dashboard/src/components/ha-setup/ExclusionManager.tsx` (new)
- `domains/core-platform/health-dashboard/src/components/ha-setup/PatternPreview.tsx` (new)
- `domains/core-platform/health-dashboard/src/hooks/useExclusions.ts` (new)

**Acceptance Criteria:**
- [ ] Glob patterns displayed with match counts
- [ ] Add/remove exclusion patterns
- [ ] `ai:ignore` labeled entities shown separately
- [ ] Pattern preview shows affected entities
- [ ] Suggested exclusion patterns based on common diagnostic patterns
- [ ] Total exclusion impact shown

---

### Story 63.7: Bulk Operations & Quick Actions

**Priority:** Medium | **Estimate:** 3h | **Risk:** Low

Bulk actions for efficiently cleaning up large entity sets.

**Features:**
- Multi-select entities in audit view (checkboxes)
- Bulk actions dropdown:
  - "Add label to selected" → label picker
  - "Remove label from selected" → label picker
  - "Generate aliases for selected" → calls device-intelligence for suggestions, applies
  - "Mark as ai:ignore" → quick exclusion
  - "Mark as ai:automatable" → quick inclusion
- Domain-wide quick actions:
  - "Label all lights as ai:automatable" → one click
  - "Label all battery sensors as ai:ignore" → one click
  - "Generate aliases for all entities missing aliases" → batch job

**API Calls:**
- `POST /api/v1/entities/bulk-label` (admin-api) — bulk label
- `PUT /api/v1/entities/{id}/aliases` (admin-api) — per-entity alias set (batched)

**Files:**
- `domains/core-platform/health-dashboard/src/components/ha-setup/BulkActionsBar.tsx` (new)
- `domains/core-platform/health-dashboard/src/components/ha-setup/QuickActions.tsx` (new)

**Acceptance Criteria:**
- [ ] Multi-select entities with checkboxes
- [ ] Bulk add/remove labels
- [ ] "Mark as ai:ignore" quick action
- [ ] "Mark as ai:automatable" quick action
- [ ] Domain-wide one-click labeling
- [ ] Progress indicator for bulk operations
- [ ] Undo support (bulk remove what was just added)

---

## Epic 64: Convention Compliance & Auto-Enhancement

**Priority:** P2 Medium | **Duration:** 1-2 weeks | **Stories:** 6
**Enhances:** `ml-engine/device-intelligence-service`, `core-platform/health-dashboard`

### Problem

Users need ongoing feedback on how well their HA install follows the naming convention, and the system should proactively suggest improvements.

---

### Story 64.1: Naming Convention Score Engine (device-intelligence)

**Priority:** High | **Estimate:** 3h | **Risk:** Low

Create a scoring engine that evaluates entities against the naming convention and returns per-entity and aggregate scores.

**Endpoint:**
- `GET /api/naming/audit` — Score all entities, return per-entity results + summary
- `GET /api/naming/score/{entity_id}` — Score a single entity

**Scoring Rules (100 points per entity):**
```
+20: Has area_id assigned
+20: Has at least one AI intent label (ai:automatable, ai:monitor-only, ai:ignore, ai:critical)
+20: Has at least one alias
+20: Friendly name follows convention:
     - Starts with area name (+8)
     - Title Case (+4)
     - No manufacturer/model strings (+4)
     - No integration prefix (+4)
+10: device_class set (for sensors/binary_sensors)
+10: Has sensor role label (sensor:primary, sensor:trigger, sensor:condition) — sensors only
```

**Response Model:**
```python
class EntityNamingScore(BaseModel):
    entity_id: str
    score: int                    # 0-100
    issues: list[str]            # ["Missing area", "No labels", ...]
    suggestions: list[str]       # ["Add label ai:automatable", "Set area to Kitchen", ...]

class NamingAuditResponse(BaseModel):
    total_entities: int
    scored_entities: int
    average_score: float
    compliant_count: int          # score >= 70
    compliant_percentage: float
    top_issues: list[dict]        # [{"issue": "Missing labels", "count": 234}, ...]
    entities: list[EntityNamingScore]
```

**Files:**
- `domains/ml-engine/device-intelligence-service/src/services/naming_convention/` (new directory)
- `domains/ml-engine/device-intelligence-service/src/services/naming_convention/score_engine.py` (new)
- `domains/ml-engine/device-intelligence-service/src/services/naming_convention/convention_rules.py` (new)
- `domains/ml-engine/device-intelligence-service/src/naming_endpoints.py` (new)

**Acceptance Criteria:**
- [ ] Per-entity scoring against convention rules
- [ ] Aggregate audit with top issues
- [ ] Actionable suggestions per entity
- [ ] Entities fetched from data-api
- [ ] Scoring is deterministic (same input → same score)

---

### Story 64.2: Auto-Alias Generation (device-intelligence)

**Priority:** Medium | **Estimate:** 3h | **Risk:** Low

Generate alias suggestions from entity friendly names using pattern rules (no AI required).

**Endpoint:**
- `POST /api/naming/suggest-aliases` — Generate alias suggestions for entities

**Request:**
```python
class AliasSuggestionRequest(BaseModel):
    entity_ids: list[str] | None = None  # None = all entities missing aliases
    max_suggestions: int = 5
```

**Generation Rules:**
1. **Singular/plural:** "Kitchen Lights" → ["kitchen light", "kitchen lights"]
2. **Area-less:** "Kitchen Ceiling Light" → ["ceiling light"] (if only one in area)
3. **Abbreviations:** "Television" → "TV", "Air Conditioner" → "AC"
4. **Type shorthand:** "Kitchen Temperature Sensor" → ["kitchen temperature", "kitchen temp"]
5. **Casual:** "Living Room Thermostat" → ["heating", "the thermostat"] (if only one)
6. **Position drop:** "Office Back Left Light" → ["office light"] (if unambiguous)

**Conflict Detection:**
- Before suggesting, check if alias already belongs to another entity
- Skip suggestions that would create ambiguity

**Files:**
- `domains/ml-engine/device-intelligence-service/src/services/naming_convention/alias_generator.py` (new)

**Acceptance Criteria:**
- [ ] Generates 3-5 alias suggestions per entity
- [ ] Singular/plural variants generated
- [ ] Common abbreviations applied (TV, AC, etc.)
- [ ] Area-less aliases generated when unambiguous
- [ ] Conflict detection prevents duplicate aliases
- [ ] No AI required (pattern-based only)

---

### Story 64.3: Compliance Dashboard Widget (health-dashboard)

**Priority:** Medium | **Estimate:** 3h | **Risk:** Low

Add a convention compliance summary card to the health-dashboard Overview tab.

**UI Component:**
```
┌──────────────────────────────────────────────┐
│ 📋 Entity Convention Compliance              │
│                                              │
│ Score: 72% ████████░░                        │
│                                              │
│ ✓ 412 entities compliant                    │
│ ⚠ 89 missing area        [Fix →]           │
│ ⚠ 234 missing labels     [Fix →]           │
│ ⚠ 312 missing aliases    [Fix →]           │
│                                              │
│ [Open HA Setup →]                            │
└──────────────────────────────────────────────┘
```

**Features:**
- Shows aggregate compliance score from device-intelligence naming audit
- Top 3 issues with counts
- "Fix →" links navigate to HA Setup tab with appropriate filter
- "Open HA Setup →" link navigates to full audit view
- Auto-refreshes every 5 minutes

**API Calls:**
- `GET /api/naming/audit` (device-intelligence) — aggregate scores

**Files:**
- `domains/core-platform/health-dashboard/src/components/overview/ConventionComplianceCard.tsx` (new)
- `domains/core-platform/health-dashboard/src/components/tabs/OverviewTab.tsx` — add card

**Acceptance Criteria:**
- [ ] Compliance score shown as progress bar
- [ ] Top issues listed with counts
- [ ] "Fix" links navigate to HA Setup tab with filter
- [ ] Card refreshes every 5 minutes
- [ ] Handles loading/error states

---

### Story 64.4: Name Suggestion Integration (device-intelligence → health-dashboard)

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low

Wire the existing `DeviceNameGenerator` (name_enhancement) into the HA Setup wizard so users get AI-suggested friendly names.

**Flow:**
1. Entity audit view shows entities with poor friendly names (low convention score)
2. Click "Suggest name" → calls device-intelligence
3. Returns 1-3 name suggestions with confidence scores
4. User picks one or edits → saves via admin-api

**Endpoint:**
- `GET /api/naming/suggest-name/{entity_id}` (device-intelligence) — returns name suggestions

**Implementation:**
- Wraps existing `DeviceNameGenerator.generate_suggested_name()` with HTTP endpoint
- Adds convention-aware suggestions: ensures area prefix, Title Case, no brand
- Falls back to AI suggester for low-confidence pattern matches

**Files:**
- `domains/ml-engine/device-intelligence-service/src/naming_endpoints.py` — add suggest-name endpoint
- `domains/core-platform/health-dashboard/src/components/ha-setup/NameEditor.tsx` — wire to API

**Acceptance Criteria:**
- [ ] Name suggestions returned for any entity
- [ ] Suggestions follow naming convention (area prefix, Title Case)
- [ ] Existing `DeviceNameGenerator` patterns reused
- [ ] AI fallback for complex cases
- [ ] Suggestions displayed in Name Editor (Story 63.5)

---

### Story 64.5: Entity Discovery Sync Enhancement

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low

Enhance the entity discovery sync (`standalone-entity-discovery.py` and websocket-ingestion) to pull labels and aliases from HA's Entity Registry API.

**Current Gap:**
- `standalone-entity-discovery.py` fetches `name`, `name_by_user`, `original_name` from Entity Registry
- Does NOT fetch `aliases` or `labels` (HA 2023.8+ / 2024.4+)

**Enhancement:**
- Add `aliases` and `labels` fields to Entity Registry WebSocket query
- Pass through to data-api bulk_upsert
- Ensure bidirectional sync: changes made in HomeIQ UI (Epic 63) sync to HA, and changes made in HA sync back to HomeIQ

**Files:**
- `scripts/standalone-entity-discovery.py` — add aliases + labels to entity registry query
- `domains/core-platform/websocket-ingestion/src/entity_filter.py` — pass labels/aliases through
- `domains/core-platform/data-api/src/devices_endpoints.py` — ensure bulk_upsert handles aliases + labels

**Acceptance Criteria:**
- [ ] Entity discovery fetches aliases from HA Entity Registry
- [ ] Entity discovery fetches labels from HA Entity Registry
- [ ] Aliases and labels passed through bulk_upsert to PostgreSQL
- [ ] Bidirectional sync: HomeIQ changes → HA, HA changes → HomeIQ
- [ ] Existing entities get aliases/labels populated on next sync

---

### Story 64.6: Convention Enforcement in Chat (ha-ai-agent-service)

**Priority:** Low | **Estimate:** 2h | **Risk:** Low

When the AI agent encounters entities with poor naming during chat, surface gentle suggestions to the user.

**Behavior:**
- During entity resolution, if matched entities have low convention scores:
  - Add a hint to the agent's response: "Tip: Adding aliases to your kitchen lights would help me find them faster next time."
- If entity resolution fails (no match found):
  - Suggest the user check HA Setup: "I couldn't find that entity. You can review your entity naming in the HA Setup page."
- If an entity has `ai:critical` label:
  - Add confirmation step: "This controls your front door lock. Are you sure?"

**Implementation:**
- After entity resolution, check score/labels and append hints to response metadata
- Hints are non-blocking — they appear as a subtle note below the main response
- Max 1 hint per conversation turn (avoid spam)

**Files:**
- `domains/automation-core/ha-ai-agent-service/src/services/context_builder.py` — add naming hints
- `domains/automation-core/ha-ai-agent-service/src/chat_endpoints.py` — include hints in response

**Acceptance Criteria:**
- [ ] Naming improvement hints surfaced when entities have low scores
- [ ] Entity-not-found suggests HA Setup page
- [ ] `ai:critical` entities trigger confirmation
- [ ] Max 1 hint per turn
- [ ] Hints are optional metadata (don't disrupt main response)

---

## Dependency Graph

```
Epic 62 (API Foundation)              Epic 63 (UI)
  ├── 62.1 area endpoint               ├── 63.1 tab + nav
  ├── 62.2 label query ─────────────►  ├── 63.2 audit view ← 62.1, 62.2, 62.3
  ├── 62.3 alias search ────────────►  ├── 63.3 label editor ← 62.2, 62.4
  ├── 62.4 label/alias mgmt ────────►  ├── 63.4 alias editor ← 62.3, 62.4
  ├── 62.5 dynamic areas               ├── 63.5 name editor ← 62.4
  ├── 62.6 label-aware filtering        ├── 63.6 exclusion mgr ← 62.6
  ├── 62.7 alias resolution             └── 63.7 bulk operations ← 62.4
  └── 62.8 alias scoring
                                      Epic 64 (Compliance)
                                        ├── 64.1 score engine ← 62.2
                                        ├── 64.2 auto-aliases ← 62.3
                                        ├── 64.3 compliance card ← 64.1
                                        ├── 64.4 name suggestions ← 62.4
                                        ├── 64.5 discovery sync ← 62.4
                                        └── 64.6 chat hints ← 62.6, 64.1

Recommended execution order:
  Week 1: Epic 62 (API foundation) — all stories can parallelize except 62.5/62.6
  Week 2: Epic 63 (UI) — depends on 62.1-62.4 being complete
  Week 3: Epic 64 (compliance) — depends on 62.x + can start alongside 63.x
```

## Risk Assessment

| Risk | Impact | Mitigation |
|---|---|---|
| HA Entity Registry API differences across versions | Labels (2024.4+) and aliases (2023.8+) may not exist on older HA | Feature-detect fields; degrade gracefully to no labels/aliases |
| GIN indexes on JSONB columns | May be slow on large entity sets | Benchmark with 1000+ entities; partial GIN index if needed |
| HA REST API rate limiting for sync | Bulk label/alias updates may hit HA limits | Batch updates, 100ms delay between calls, queue with retry |
| UI complexity in entity audit | 500+ entities may be slow to render | Virtual scrolling (react-window), pagination, lazy scoring |
| Bidirectional sync conflicts | User edits in HA UI vs HomeIQ UI | Last-write-wins with timestamp comparison; show conflict indicator |

## API Call Summary

### data-api (port 8006) — Read Endpoints

| Endpoint | Method | Purpose | Auth |
|---|---|---|---|
| `/api/areas` | GET | List all areas with entity counts | Yes |
| `/api/entities?label={label}` | GET | Filter entities by label | Yes |
| `/api/entities?alias={term}` | GET | Search entities by alias | Yes |
| `/api/entities?has_aliases={bool}` | GET | Filter by alias presence | Yes |
| `/api/labels` | GET | List all distinct labels with counts | Yes |
| `/internal/areas/list` | GET | Area list for inter-service use | No |

### admin-api (port 8004) — Write Endpoints

| Endpoint | Method | Purpose | Auth |
|---|---|---|---|
| `PUT /api/v1/entities/{id}/labels` | PUT | Set entity labels | Yes |
| `PUT /api/v1/entities/{id}/aliases` | PUT | Set entity aliases | Yes |
| `PUT /api/v1/entities/{id}/name` | PUT | Set entity friendly name | Yes |
| `POST /api/v1/entities/bulk-label` | POST | Bulk add/remove labels | Yes |

### device-intelligence (port 8028) — Scoring Endpoints

| Endpoint | Method | Purpose | Auth |
|---|---|---|---|
| `GET /api/naming/audit` | GET | Score all entities against convention | Yes |
| `GET /api/naming/score/{entity_id}` | GET | Score single entity | Yes |
| `POST /api/naming/suggest-aliases` | POST | Generate alias suggestions | Yes |
| `GET /api/naming/suggest-name/{entity_id}` | GET | Generate name suggestions | Yes |

### UI Pages (health-dashboard)

| Page | URL Hash | Components | API Dependencies |
|---|---|---|---|
| HA Setup — Audit | `#ha-setup` | EntityAuditView, AuditSummaryCards | data-api entities + areas, device-intelligence audit |
| HA Setup — Labels | `#ha-setup/labels` | LabelEditor, LabelSuggestions | data-api labels, admin-api label CRUD |
| HA Setup — Aliases | `#ha-setup/aliases` | AliasEditor, AliasSuggestions | data-api alias search, admin-api alias CRUD |
| HA Setup — Exclusions | `#ha-setup/exclusions` | ExclusionManager, PatternPreview | admin-api blacklist, data-api entities |
| Overview — Compliance Card | `#overview` | ConventionComplianceCard | device-intelligence audit |
