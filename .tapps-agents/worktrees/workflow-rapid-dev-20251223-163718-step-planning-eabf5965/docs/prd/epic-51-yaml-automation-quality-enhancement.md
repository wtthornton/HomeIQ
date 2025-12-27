# Epic 51: YAML Automation Quality Enhancement & Validation Pipeline

**Epic ID:** 51  
**Title:** YAML Automation Quality Enhancement & Validation Pipeline  
**Status:** Planning  
**Priority:** High  
**Complexity:** High  
**Timeline:** 4-6 weeks  
**Story Points:** 45-65  
**Type:** Brownfield Enhancement  
**Related Analysis:** YAML generation review completed (see conversation history)

---

## Epic Goal

Establish a comprehensive YAML automation validation and normalization pipeline that ensures 100% of generated automations are valid, correctly formatted, and deployable to Home Assistant on first attempt, eliminating format errors, entity validation failures, and deployment rejections.

---

## Epic Description

### Existing System Context

**Current YAML Generation Architecture:**

HomeIQ generates Home Assistant automation YAML through two primary paths:

1. **HA AI Agent Service (Chat Interface)** - `services/ha-ai-agent-service/`
   - LLM generates YAML directly as tool call arguments
   - System prompt instructs model to create valid YAML
   - Basic validation via `_validate_yaml()` method
   - Falls back to basic validation if AI Automation Service unavailable
   - **Issue**: No format normalization, accepts invalid YAML variants

2. **AI Automation Service (Suggestion Deployment)** - `services/ai-automation-service-new/`
   - Minimal prompt: "Use valid Home Assistant automation YAML format"
   - Basic syntax validation (YAML parsing)
   - Entity existence validation via Data API
   - **Issue**: No schema validation, no format enforcement, no auto-correction

**Current Problems Identified:**

1. **Format Inconsistencies:**
   - LLM generates `triggers:`/`actions:` (plural) instead of `trigger:`/`action:` (singular)
   - Action steps use `action:` field instead of `service:` field
   - Trigger items use `trigger:` field instead of `platform:` field
   - Error handling uses `continue_on_error: true` instead of `error: continue`

2. **Validation Gaps:**
   - No schema validation (only syntax checking)
   - No service parameter validation
   - No safety checks for critical devices
   - Entity extraction too permissive (false positives)
   - No validation of state values against known states

3. **Missing Auto-Correction:**
   - Validator can detect errors but doesn't auto-fix
   - Fixed YAML returned but not applied
   - Users see invalid YAML in preview
   - Deployment fails with HTTP 400 errors

4. **Service Integration Issues:**
   - HA Agent Service calls non-existent validation endpoint
   - Hardcoded service URLs (port 8000 vs 8025)
   - No unified validation service
   - Inconsistent validation behavior across services

**Technology Stack:**
- Python 3.12, FastAPI 0.115.x
- OpenAI API (GPT-4o-mini, GPT-5.1)
- Home Assistant REST API
- SQLite database (shared)
- YAML parsing (PyYAML)

**Current Validation Flow:**
```
LLM Generates YAML
    ↓
Basic Syntax Check (yaml.safe_load)
    ↓
Check Required Keys (trigger, action)
    ↓
Entity Validation (optional, via Data API)
    ↓
Deploy to Home Assistant
    ↓
❌ HTTP 400 Error (format rejected)
```

### Enhancement Details

**What's being added/changed:**

1. **Canonical Automation Schema (Internal Representation)**
   - Define structured `AutomationSpec` class with strict typing
   - Support all Home Assistant 2025.10+ features (choose, repeat, parallel, sequence)
   - YAML is rendered FROM schema, not primary source of truth
   - Store both plan (for edits) and rendered YAML (for display)

2. **Structured Plan Generation (LLM Output Change)**
   - LLM generates structured JSON/object matching AutomationSpec
   - Server-side deterministic YAML rendering
   - Eliminates format variations from LLM output
   - Enables future automation editing capabilities

3. **Multi-Stage Validation Pipeline**
   - **Stage 1: Syntax** - YAML parsing validation
   - **Stage 2: Schema** - Required keys, correct node shapes, field types
   - **Stage 3: Referential Integrity** - Entities, areas, devices exist
   - **Stage 4: Service Schema** - Service exists, parameters valid, types/ranges correct
   - **Stage 5: Safety** - Critical device checks (locks, alarms, heating)
   - **Stage 6: Style/Maintainability** - Best practices, target optimization
   - Returns errors, warnings, score, and fixes applied

4. **Auto-Correction & Normalization**
   - Format normalization (plural → singular, field name corrections)
   - Entity ID validation and correction
   - Service parameter validation and correction
   - Target structure optimization (area_id/device_id)
   - **MUST apply fixes** to preview, create, and stored versions

5. **Unified Validation Service**
   - Single validation endpoint used by all services
   - Consistent behavior across HA Agent, Automation Service, UI
   - Service discovery/environment configuration
   - Versioned API contract

6. **Enhanced Entity/Service Extraction**
   - Only extract from known locations (entity_id, target.entity_id, etc.)
   - Distinguish service references (domain.service) from entities
   - Validate state values against known states
   - Prevent false positives

7. **Canonical Format Enforcement**
   - Always use `trigger:`, `action:`, `service:` (not variants)
   - Compatibility parser accepts variants but normalizes
   - Never store unnormalized YAML

8. **Robust State Restoration**
   - Enumerate correct snapshot_entities from inventory
   - Guardrails for large areas (cap, warn, prefer groups)
   - Deterministic scene naming (collision-safe)

9. **ID/Versioning Strategy**
   - Single deterministic ID strategy across all paths
   - Clear mapping: alias → config_id → entity_id
   - Version history with diffs, scores, approval tracking

10. **UX Improvements**
   - Preview shows normalized, validated YAML
   - Disable Create button if validation errors
   - Show validation panel (errors/warnings/fixes)
   - Test mode with dry-run capability

**How it integrates:**

- **New Service**: `yaml-validation-service` (Port 8026)
  - Centralized validation logic
  - Shared by HA Agent Service and Automation Service
  - RESTful API with versioning

- **Enhanced Services:**
  - `ha-ai-agent-service`: Calls validation service, applies fixes
  - `ai-automation-service-new`: Uses validation service, stores normalized YAML
  - `ai-automation-ui`: Shows validation results, normalized YAML

- **New Components:**
  - `AutomationSpec` class (canonical schema)
  - `YAMLNormalizer` class (format correction)
  - `ValidationPipeline` class (multi-stage validation)
  - `AutomationRenderer` class (schema → YAML)

**Success criteria:**

- ✅ 95%+ automations pass validation on first attempt (with structured plan)
- ✅ 0% persisted YAML contains format errors (triggers/actions, wrong field names)
- ✅ 99%+ deploy success rate once user approves
- ✅ All services use unified validation endpoint
- ✅ Auto-correction applied automatically (no manual fixes needed)
- ✅ Validation pipeline returns comprehensive results (errors, warnings, score, fixes)
- ✅ Entity extraction has <1% false positive rate
- ✅ Service parameter validation prevents invalid service calls
- ✅ Safety checks flag critical device automations
- ✅ UX shows validation status clearly

### Technology Research

- **YAML Schema Validation**: Research Pydantic models for Home Assistant automation schema
- **Service Discovery**: Research service mesh patterns for microservice communication
- **MANDATORY**: Use Context7 KB-first commands (*context7-docs, *context7-resolve) when researching external libraries
- **ALWAYS**: Check KB cache first before fetching from Context7 API

---

## Business Value

- **Zero Deployment Failures**: Eliminates HTTP 400 errors from format issues
- **Improved User Experience**: Users see valid automations immediately, no manual fixes
- **Reduced Support Burden**: Fewer "automation doesn't work" issues
- **Faster Development**: Developers can trust generated YAML is correct
- **Better Maintainability**: Canonical schema enables future automation editing
- **Quality Metrics**: Trackable validation scores and error rates
- **Safety Assurance**: Critical device automations flagged and validated
- **Consistency**: All services use same validation logic

---

## Success Criteria

- ✅ 95%+ automations pass validation on first attempt (with structured plan generation)
- ✅ 0% persisted YAML contains format errors (triggers/actions, wrong field names)
- ✅ 99%+ deploy success rate once user approves (non-admin)
- ✅ All services use unified validation endpoint
- ✅ Auto-correction applied automatically (no manual fixes needed)
- ✅ Validation pipeline returns comprehensive results (errors, warnings, score, fixes)
- ✅ Entity extraction has <1% false positive rate
- ✅ Service parameter validation prevents invalid service calls
- ✅ Safety checks flag critical device automations
- ✅ UX shows validation status clearly
- ✅ All existing functionality maintained
- ✅ Performance requirements met (<100ms validation latency)
- ✅ Zero breaking changes to external APIs
- ✅ All tests passing (unit, integration, E2E)
- ✅ Documentation updated

---

## Technical Architecture

### Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│  (HA Agent Chat, Automation UI, Suggestion Deployment)       │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ API Calls
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ HA AI Agent  │  │ Automation  │  │ Automation   │
│ Service      │  │ Service      │  │ UI           │
│ (Port 8018)  │  │ (Port 8025)  │  │ (Port 3001)  │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
                          │ Validation API
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│           YAML Validation Service (Port 8026)               │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         Validation Pipeline (Multi-Stage)            │ │
│  │  1. Syntax Validation (YAML parsing)                 │ │
│  │  2. Schema Validation (Required keys, structure)     │ │
│  │  3. Referential Integrity (Entities, areas, devices) │ │
│  │  4. Service Schema (Service exists, params valid)    │ │
│  │  5. Safety Checks (Critical devices)                 │ │
│  │  6. Style/Maintainability (Best practices)           │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         YAML Normalizer                              │ │
│  │  - Format correction (plural → singular)            │ │
│  │  - Field name fixes (action: → service:)            │ │
│  │  - Target optimization (area_id/device_id)         │ │
│  │  - Error handling placement fixes                   │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         Automation Spec (Canonical Schema)            │ │
│  │  - Structured automation representation              │ │
│  │  - Type-safe validation                              │ │
│  │  - YAML rendering                                    │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Data API     │  │ Home         │  │ Entity       │
│ (Port 8006)  │  │ Assistant    │  │ Registry     │
│              │  │ API          │  │ Service      │
│ - Entities   │  │              │  │              │
│ - Areas      │  │ - Validation │  │ - Capabilities│
│ - Services   │  │ - Deployment │  │ - States     │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Data Flow

**YAML Generation Flow (New):**
```
User Request
    ↓
LLM Generates Structured Plan (JSON/object)
    ↓
AutomationSpec Validation
    ↓
YAML Rendering (Deterministic)
    ↓
Validation Pipeline (6 Stages)
    ↓
Normalization (Auto-Fix)
    ↓
✅ Valid, Normalized YAML
    ↓
Preview/Create/Deploy
```

**YAML Validation Flow (Existing YAML):**
```
Existing YAML Input
    ↓
YAML Parsing (Syntax)
    ↓
Schema Validation
    ↓
Format Normalization
    ↓
Validation Pipeline (6 Stages)
    ↓
Auto-Correction Applied
    ↓
✅ Fixed, Validated YAML
```

### Key Components

**1. AutomationSpec (Canonical Schema)**
```python
class AutomationSpec:
    id: str
    alias: str
    description: str
    initial_state: bool
    mode: AutomationMode
    trigger: list[TriggerSpec]
    condition: list[ConditionSpec] | None
    action: list[ActionSpec]
    max_exceeded: str | None
    tags: list[str] | None
```

**2. ValidationPipeline**
- Multi-stage validation with early exit on critical errors
- Returns ValidationResult with errors, warnings, score, fixed_yaml
- Configurable validation levels (strict, moderate, permissive)

**3. YAMLNormalizer**
- Format corrections (plural → singular)
- Field name fixes (action: → service:)
- Structure optimization (target.area_id)
- Error handling placement

**4. AutomationRenderer**
- Converts AutomationSpec to Home Assistant YAML
- Deterministic formatting
- 2025.10+ format compliance

---

## Stories

1. **Story 51.1**: Create Canonical Automation Schema & YAML Renderer
   - Define AutomationSpec class with Pydantic models
   - Implement AutomationRenderer (schema → YAML)
   - Support all HA 2025.10+ features (choose, repeat, parallel, sequence)
   - Unit tests for schema validation and rendering

2. **Story 51.2**: Implement Multi-Stage Validation Pipeline
   - Create ValidationPipeline class with 6 stages
   - Implement each validation stage (syntax, schema, entities, services, safety, style)
   - Return comprehensive ValidationResult (errors, warnings, score, fixes)
   - Integration tests with real Home Assistant automations

3. **Story 51.3**: Build YAML Normalizer & Auto-Correction
   - Implement YAMLNormalizer for format corrections
   - Auto-fix common format errors (plural keys, wrong field names)
   - Target structure optimization
   - Error handling placement fixes
   - Unit tests for normalization rules

4. **Story 51.4**: Create Unified Validation Service
   - New service: `yaml-validation-service` (Port 8026)
   - RESTful API with versioning
   - Service discovery/environment configuration
   - Health checks and metrics
   - Docker deployment

5. **Story 51.5**: Integrate Validation Service with HA Agent Service
   - Update HA Agent Service to call validation service
   - Apply auto-corrections to preview and create flows
   - Show validation results in UI
   - Fallback to basic validation if service unavailable
   - Integration tests

6. **Story 51.6**: Integrate Validation Service with Automation Service
   - Update Automation Service to use validation service
   - Store normalized YAML in database
   - Apply fixes before deployment
   - Integration tests

7. **Story 51.7**: Enhance Entity/Service Extraction & Validation
   - Improve entity extraction (only known locations)
   - Distinguish service references from entities
   - Validate state values against known states
   - Reduce false positive rate to <1%
   - Unit tests

8. **Story 51.8**: Implement Structured Plan Generation (LLM Output Change)
   - Update LLM prompts to generate structured JSON/object
   - Parse structured plan into AutomationSpec
   - Render to YAML server-side
   - Store both plan and rendered YAML
   - Integration tests

9. **Story 51.9**: Add UX Validation Feedback & Status Display
   - Show validation panel in preview (errors/warnings/fixes)
   - Disable Create button if validation errors
   - Display normalized YAML in preview
   - Test mode with dry-run capability
   - UI component tests

10. **Story 51.10**: Implement Safety Checks & Critical Device Validation
    - Identify critical devices (locks, alarms, heating, doors/windows)
    - Safety scoring algorithm
    - Warning system for risky automations
    - Admin override capability
    - Unit tests

11. **Story 51.11**: Add ID/Versioning Strategy & State Restoration
    - Single deterministic ID strategy across all paths
    - Mapping: alias → config_id → entity_id
    - Version history with diffs, scores, approval tracking
    - Robust state restoration (snapshot_entities enumeration)
    - Integration tests

12. **Story 51.12**: Comprehensive Testing & Quality Metrics
    - E2E tests for full validation pipeline
    - Performance tests (<100ms validation latency)
    - Quality metrics tracking (validation scores, error rates)
    - Documentation updates
    - Acceptance criteria verification

---

## Compatibility Requirements

- [x] Existing APIs remain backward compatible (validation is additive)
- [x] Database schema changes are backward compatible (new fields optional)
- [x] UI changes follow existing patterns (TailwindCSS, React)
- [x] Performance impact is minimal (<100ms validation latency)
- [x] Existing automation creation flow remains functional
- [x] Fallback to basic validation if service unavailable
- [x] No breaking changes to external APIs

---

## Risk Mitigation

**Primary Risks:**

1. **Risk**: LLM structured plan generation may be less reliable than YAML generation
   - **Mitigation**: Start with YAML input, add structured plan as enhancement
   - **Fallback**: Keep YAML generation as primary, structured plan as optional

2. **Risk**: Validation service becomes bottleneck
   - **Mitigation**: Async processing, caching, connection pooling
   - **Fallback**: Local validation library if service unavailable

3. **Risk**: Auto-correction may change user intent
   - **Mitigation**: Show fixes applied, allow user review
   - **Fallback**: Manual approval for major corrections

4. **Risk**: Service integration complexity
   - **Mitigation**: Gradual rollout, feature flags, comprehensive testing
   - **Fallback**: Keep existing validation as fallback

**Rollback Plan:**
- Revert to basic validation if issues occur
- Keep existing YAML generation as fallback
- Feature flags for gradual rollout
- All changes are additive, no breaking changes

---

## Definition of Done

- [ ] All stories completed with acceptance criteria met
- [ ] Canonical AutomationSpec schema implemented and tested
- [ ] Multi-stage validation pipeline functional (6 stages)
- [ ] YAML normalizer auto-corrects common format errors
- [ ] Unified validation service deployed and operational
- [ ] HA Agent Service integrated with validation service
- [ ] Automation Service integrated with validation service
- [ ] Entity extraction has <1% false positive rate
- [ ] 95%+ automations pass validation on first attempt
- [ ] 0% persisted YAML contains format errors
- [ ] 99%+ deploy success rate once user approves
- [ ] UX shows validation status clearly
- [ ] All existing functionality verified through testing
- [ ] No regression in existing features
- [ ] Performance requirements met (<100ms validation latency)
- [ ] Code follows project coding standards
- [ ] Documentation updated (API docs, user guides, architecture)
- [ ] Quality metrics tracking implemented

---

## Related Epics

- **Epic 39**: AI Automation Service Modularization (service architecture)
- **Epic AI-20**: HA AI Agent Completion & Production Readiness (base chat functionality)
- **Epic AI-25**: HA Agent UI Enhancements (UI improvements)
- **Epic 32**: Home Assistant Validation (related validation work)

---

## Dependencies

- **Data API Service** (Port 8006) - Entity/area/service queries
- **Home Assistant API** - Validation and deployment
- **Entity Registry Service** - Entity capabilities and states
- **OpenAI API** - LLM for structured plan generation (optional enhancement)

---

## Timeline

**Week 1-2**: Stories 51.1-51.3 (Schema, Validation Pipeline, Normalizer)
**Week 3**: Stories 51.4-51.6 (Validation Service, Integration)
**Week 4**: Stories 51.7-51.9 (Entity Validation, Structured Plans, UX)
**Week 5**: Stories 51.10-51.11 (Safety Checks, ID/Versioning)
**Week 6**: Story 51.12 (Testing, Metrics, Documentation)

---

## Acceptance Criteria Summary

**Must Have:**
- ✅ 95%+ first-pass validation success rate
- ✅ 0% format errors in persisted YAML
- ✅ 99%+ deploy success rate
- ✅ Unified validation service operational
- ✅ Auto-correction applied automatically

**Should Have:**
- ✅ Structured plan generation (LLM enhancement)
- ✅ Safety checks for critical devices
- ✅ Quality metrics tracking
- ✅ Test mode with dry-run

**Nice to Have:**
- ✅ Automation editing capabilities (future)
- ✅ Advanced safety scoring
- ✅ Performance optimization

---

## Notes

- This epic addresses critical quality issues identified in YAML generation review
- Focus on eliminating deployment failures and format errors
- Gradual rollout recommended with feature flags
- All changes are additive, maintaining backward compatibility
- Validation service can be extended for future automation features

