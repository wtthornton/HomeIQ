# Epic AI-8: Home Assistant 2025 API Integration

**Status:** 📋 **PLANNING**  
**Type:** Brownfield Enhancement (AI Automation Service)  
**Priority:** High  
**Effort:** 6 Stories (14 story points, 3-4 weeks estimated)  
**Created:** January 2025  
**Last Updated:** January 2025

---

## Epic Goal

Fully integrate Home Assistant 2025 API attributes (aliases, labels, options, icon) throughout the AI Automation Service and ensure they are used in entity resolution, suggestion generation, and filtering.

**Business Value:**
- **+50% entity resolution accuracy** - Aliases improve matching
- **+30% suggestion quality** - Labels and options provide context
- **100% HA 2025 compliance** - Full support for latest API features

---

## Existing System Context

### Current Functionality

**AI Automation Service** (Port 8024) currently:
- Resolves entities from natural language queries
- Generates automation suggestions based on patterns
- Uses entity registry data for entity information
- Has database fields for 2025 attributes but doesn't fully utilize them

**Home Assistant 2025 API Attributes Status:**

**Already Implemented (Phase 1):**
- ✅ Entity `aliases` - Database field exists, used in entity resolution
- ✅ Entity `name_by_user` - Database field exists, retrieved from Entity Registry
- ✅ Entity `icon` - Database field exists, separate from `original_icon`

**Partially Implemented (Phase 2):**
- ⚠️ Entity `labels` - Database field exists, not fully used in filtering
- ⚠️ Entity `options` - Database field exists, not used in suggestions
- ⚠️ Device `labels` - Database field exists, not used in filtering

**Missing Integration:**
- ❌ Labels-based filtering in suggestions
- ❌ Options-based preference detection
- ❌ Enhanced entity context in prompts
- ❌ Dashboard display of new attributes
- ❌ Label-based organization in UI

### Technology Stack

- **Service:** `services/ai-automation-service/` (FastAPI, Python 3.11+)
- **Entity Enrichment:** `services/ai-automation-service/src/services/entity_enrichment.py`
- **Entity Validation:** `services/ai-automation-service/src/services/entity_validator.py`
- **Suggestion Generation:** `services/ai-automation-service/src/services/automation/suggestion_generator.py`
- **Ask AI Router:** `services/ai-automation-service/src/api/ask_ai_router.py`
- **Database:** SQLite (entities, devices, suggestions tables)
- **Data API:** `services/data-api/` (Port 8006) - Entity/device queries

### Integration Points

- Entity resolution pipeline (`entity_validator.py`, `ask_ai_router.py`)
- Suggestion generation (`suggestion_generator.py`)
- Entity enrichment (`entity_enrichment.py`)
- Database queries (`database/crud.py`)
- Data API endpoints (`data-api/src/devices_endpoints.py`)

---

## Enhancement Details

### What's Being Added/Changed

1. **Labels-Based Filtering System** (NEW)
   - Label-based filtering in suggestion queries
   - Filter suggestions by entity labels (e.g., "outdoor", "security")
   - Filter suggestions by device labels
   - Label-based grouping in suggestions

2. **Options-Based Preference Detection** (NEW)
   - Options extracted from entity registry
   - Options used to inform automation suggestions (e.g., default brightness)
   - Suggestions respect user-configured defaults
   - Options included in entity context for YAML generation

3. **Enhanced Entity Context in Prompts** (ENHANCEMENT)
   - Entity context includes aliases, labels, options
   - Aliases used in entity resolution prompts
   - Labels used for organizational context
   - Options used for preference detection

4. **Icon Display Enhancement** (ENHANCEMENT)
   - Current `icon` (not `original_icon`) used in UI
   - Icon changes reflected in suggestions
   - Icon-based filtering works correctly

5. **Entity Resolution with Aliases Enhancement** (ENHANCEMENT)
   - Aliases checked in all entity resolution paths
   - Aliases prioritized in matching (after exact matches)
   - Alias matching works in natural language queries

6. **Name By User Priority** (ENHANCEMENT)
   - `name_by_user` prioritized over `name` in entity resolution
   - Entity Registry `name_by_user` used instead of State API `friendly_name`
   - User-customized names properly recognized

### How It Integrates

- **Non-Breaking Changes:** All enhancements are additive, existing functionality unchanged
- **Incremental Integration:** Each story builds on previous work
- **Performance Optimized:** Filtering and context enhancement add <30ms latency
- **Backward Compatible:** Existing entity resolution continues to work

---

## Success Criteria

1. **Functional:**
   - All 2025 API attributes integrated
   - Labels-based filtering working
   - Options-based preferences detected
   - Entity resolution accuracy improved
   - Enhanced context in prompts

2. **Technical:**
   - Performance requirements met (<30ms additional latency)
   - Unit tests >90% coverage
   - Integration tests cover all paths
   - All attributes properly retrieved and used

3. **Quality:**
   - All existing functionality verified
   - No breaking changes
   - Comprehensive documentation
   - Code reviewed and approved

---

## Stories

### Phase 1: Filtering and Preferences (Weeks 1-2)

#### Story AI8.1: Labels-Based Filtering System
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

Implement label-based filtering in suggestion queries and grouping.

**Acceptance Criteria:**
1. Label-based filtering in suggestion queries
2. Filter suggestions by entity labels (e.g., "outdoor", "security")
3. Filter suggestions by device labels
4. Label-based grouping in suggestions
5. Unit tests verify label filtering
6. Integration tests verify label-based suggestions

**Files to Update:**
- `services/ai-automation-service/src/services/automation/suggestion_generator.py`
- `services/ai-automation-service/src/database/crud.py` - Add label filtering queries
- `services/ai-automation-service/src/api/suggestions_router.py` - Add label filter parameter

---

#### Story AI8.2: Options-Based Preference Detection
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

Extract and use entity options to inform automation suggestions and respect user preferences.

**Acceptance Criteria:**
1. Options extracted from entity registry
2. Options used to inform automation suggestions (e.g., default brightness)
3. Suggestions respect user-configured defaults
4. Options included in entity context for YAML generation
5. Unit tests verify options usage
6. Integration tests verify preference-aware suggestions

**Files to Update:**
- `services/ai-automation-service/src/services/entity_enrichment.py`
- `services/ai-automation-service/src/services/automation/yaml_generation_service.py`
- `services/ai-automation-service/src/llm/description_generator.py`

---

### Phase 2: Context Enhancement (Weeks 2-3)

#### Story AI8.3: Enhanced Entity Context in Prompts
**Type:** Enhancement  
**Points:** 2  
**Effort:** 4-6 hours

Enhance entity context to include all 2025 attributes (aliases, labels, options).

**Acceptance Criteria:**
1. Entity context includes aliases, labels, options
2. Aliases used in entity resolution prompts
3. Labels used for organizational context
4. Options used for preference detection
5. Unit tests verify context completeness

**Files to Update:**
- `services/ai-automation-service/src/services/entity_enrichment.py`
- `services/ai-automation-service/src/services/automation/yaml_generation_service.py`
- `services/ai-automation-service/src/api/ask_ai_router.py`

---

#### Story AI8.4: Icon Display Enhancement
**Type:** Enhancement  
**Points:** 1  
**Effort:** 2-4 hours

Ensure current `icon` (not `original_icon`) is used correctly throughout the service.

**Acceptance Criteria:**
1. Current `icon` (not `original_icon`) used in UI
2. Icon changes reflected in suggestions
3. Icon-based filtering works correctly
4. Unit tests verify icon usage

**Files to Update:**
- `services/ai-automation-service/src/services/entity_enrichment.py`
- `services/data-api/src/devices_endpoints.py` - Ensure `icon` returned in responses

---

### Phase 3: Resolution Enhancement (Weeks 3-4)

#### Story AI8.5: Entity Resolution with Aliases Enhancement
**Type:** Enhancement  
**Points:** 2  
**Effort:** 4-6 hours

Enhance entity resolution to comprehensively use aliases in all resolution paths.

**Acceptance Criteria:**
1. Aliases checked in all entity resolution paths
2. Aliases prioritized in matching (after exact matches)
3. Alias matching works in natural language queries
4. Unit tests verify alias matching
5. Integration tests verify alias-based resolution

**Files to Update:**
- `services/ai-automation-service/src/services/entity_validator.py`
- `services/ai-automation-service/src/api/ask_ai_router.py`

---

#### Story AI8.6: Name By User Priority
**Type:** Enhancement  
**Points:** 1  
**Effort:** 2-4 hours

Prioritize `name_by_user` over `name` in entity resolution to respect user customizations.

**Acceptance Criteria:**
1. `name_by_user` prioritized over `name` in entity resolution
2. Entity Registry `name_by_user` used instead of State API `friendly_name`
3. User-customized names properly recognized
4. Unit tests verify name priority

**Files to Update:**
- `services/ai-automation-service/src/services/entity_enrichment.py`
- `services/device-intelligence-service/src/clients/ha_client.py`

---

## Dependencies

### External Dependencies
- **Home Assistant 2025.10+** - Required for new API attributes
- **Entity Registry API** - Source of aliases, labels, options
- **Device Registry API** - Source of device labels

### Internal Dependencies
- **Data API Service** - Must return all 2025 attributes
- **Device Intelligence Service** - Must retrieve all 2025 attributes
- **AI Automation Service** - Core service being enhanced

---

## Risk Mitigation

### Technical Risks

**API Attribute Availability:**
- **Risk:** Some attributes may not be available for all entities
- **Mitigation:** Graceful fallback, optional fields
- **Testing:** Test with entities missing attributes

**Performance Impact:**
- **Risk:** Additional filtering may slow queries
- **Mitigation:** Optimize queries, add indexes
- **Target:** <30ms additional latency

### Timeline Risks

**Integration Complexity:**
- **Risk:** Multiple services need updates
- **Mitigation:** Incremental integration, clear interfaces
- **Approach:** Phase-by-phase with testing

---

## Related Documentation

- [Missing HA 2025 Database Attributes](../../implementation/analysis/MISSING_HA_2025_DATABASE_ATTRIBUTES.md)
- [HA Best Practices & API 2025 Update Plan](../../implementation/HA_BEST_PRACTICES_AND_API_2025_UPDATE_PLAN.md)
- [AI Automation Service Technical Whitepaper](../../docs/current/AI_AUTOMATION_SERVICE_TECHNICAL_WHITEPAPER.md)

---

**Epic Owner:** Product Manager  
**Technical Lead:** AI Automation Service Team  
**Status:** 📋 Planning  
**Next Steps:** Begin Story AI8.1 - Labels-Based Filtering System

