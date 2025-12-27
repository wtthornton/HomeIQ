# Epic 34: Advanced External Data Generation

**Epic ID:** 34  
**Title:** Advanced External Data Generation  
**Status:** Planning  
**Priority:** High  
**Complexity:** Medium  
**Timeline:** 3-4 weeks  
**Story Points:** 28-38  
**Related Design:** `implementation/analysis/SYNTHETIC_EXTERNAL_DATA_GENERATION_DESIGN.md`  
**Depends on:** Epic 33 (Foundation External Data Generation)

---

## Epic Goal

Generate realistic electricity pricing and calendar data that correlates with device usage and presence patterns to support advanced correlation analysis training for the AI automation service.

## Epic Description

### Existing System Context

**Deployment Context:**
- **Single-home NUC deployment** (Intel NUC i3/i5, 8-16GB RAM)
- Resource-constrained environment optimized for local processing
- All services run on one machine via Docker Compose
- Training data generation runs locally (no cloud dependencies)

**Current functionality:**
- Synthetic home generation pipeline with weather and carbon intensity data (Epic 33)
- Foundation external data generators operational
- Ready for advanced external data integration

**Technology stack:**
- Python 3.11, FastAPI
- Location: `services/ai-automation-service/src/training/`
- **2025 Patterns**: Pydantic Settings, async/await, type hints, structured logging
- **Context7 KB**: FastAPI patterns, Python best practices (see `docs/kb/context7-cache/`)

**Integration:** New generators will integrate with existing pipeline and Epic 33 generators

### Enhancement Details

**Two advanced external data generators:**

1. **Electricity Pricing Generator** - Pricing region profiles, time-of-use pricing, market dynamics, energy device correlation
2. **Calendar Generator** - Work schedule generation, routine events, travel events, presence patterns

**Impact:** Enables cost-optimization and presence-aware automation training

**How it integrates:**
- New generator classes in `services/ai-automation-service/src/training/`
- Integrates after Epic 33 generators in pipeline
- Uses home metadata and device list for context
- Correlates with device events and presence patterns
- Adds external data to home JSON structure

**Success criteria:**
- ✅ Electricity pricing data generated with time-of-use patterns
- ✅ Calendar events generated with realistic schedules
- ✅ Pricing correlates with energy device usage
- ✅ Calendar correlates with presence and device usage
- ✅ Multiple pricing regions and work schedules supported
- ✅ Unit tests for all generators

## Business Value

- **Cost-Optimization Automation Training**: Enables AI models to learn time-of-use pricing patterns for EV charging and high-energy device scheduling
- **Presence-Aware Automation Training**: Supports training on calendar-based presence patterns for security and comfort automation
- **Economic and Behavioral Context**: Provides economic (pricing) and behavioral (calendar) context for device behavior
- **Advanced Correlation Analysis**: Enables sophisticated correlation analysis combining pricing, calendar, and device usage

## Success Criteria

- ✅ Electricity pricing data generated with time-of-use patterns
- ✅ Calendar events generated with realistic schedules
- ✅ Pricing correlates with energy device usage
- ✅ Calendar correlates with presence and device usage
- ✅ Multiple pricing regions and work schedules supported
- ✅ Unit tests for all generators
- ✅ Integration tests validate data structure
- ✅ Pipeline integration complete
- ✅ Documentation updated

## Technical Architecture

### Generator Structure

```
SyntheticHomeGenerator
    ↓
SyntheticAreaGenerator
    ↓
SyntheticDeviceGenerator
    ↓
SyntheticEventGenerator
    ↓
SyntheticWeatherGenerator (Epic 33)
    ↓
SyntheticCarbonIntensityGenerator (Epic 33)
    ↓
[NEW] SyntheticElectricityPricingGenerator
    ↓
[NEW] SyntheticCalendarGenerator
    ↓
Home JSON with all external data
```

### File Locations

- **Pricing Generator**: `services/ai-automation-service/src/training/synthetic_electricity_pricing_generator.py`
- **Calendar Generator**: `services/ai-automation-service/src/training/synthetic_calendar_generator.py`
- **Integration Point**: `services/ai-automation-service/src/training/synthetic_home_generator.py`

### Resource Constraints (NUC Deployment)

**Memory Optimization:**
- Generators use in-memory dictionaries for pricing/calendar profiles (not databases)
- Batch processing to minimize memory footprint
- Lazy loading of large datasets
- Target: <100MB memory per generator

**Performance Targets:**
- Pricing generation: <50ms per home
- Calendar generation: <100ms per home (more complex logic)
- Total external data generation: <300ms per home
- Suitable for batch processing 100-120 homes in <40 seconds

**2025 Best Practices:**
- Use Pydantic models for data validation (see `docs/kb/context7-cache/fastapi-pydantic-settings.md`)
- Structured logging with Python logging module
- Type hints throughout (Python 3.11+)
- Async/await for I/O operations
- Context7 KB patterns for FastAPI integration

### Data Structure

External data will be extended in home JSON:
```json
{
  "home": {...},
  "external_data": {
    "weather": [...],
    "carbon_intensity": [...],
    "electricity_pricing": [
      {
        "timestamp": "2025-01-15T08:00:00Z",
        "price_per_kwh": 0.12,
        "pricing_tier": "off-peak",
        "region": "CAISO",
        "forecast": [...]
      }
    ],
    "calendar": [
      {
        "timestamp": "2025-01-15T08:00:00Z",
        "event_type": "work",
        "summary": "Work",
        "location": "Office",
        "presence_state": "away"
      }
    ]
  }
}
```

## Stories

### Story 34.1: Electricity Pricing Generator Foundation
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 hours
- **Description**: Create `SyntheticElectricityPricingGenerator` class with pricing region profiles and basic price generation

### Story 34.2: Time-of-Use Pricing
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 hours
- **Description**: Implement peak/off-peak/mid-peak periods, price multipliers, and weekend pricing patterns

### Story 34.3: Market Dynamics
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 hours
- **Description**: Implement demand-based price variation, random price variation, and forecast generation

### Story 34.4: Pricing-Energy Device Correlation
- **Story Points**: 4
- **Priority**: P0
- **Effort**: 3-4 hours
- **Description**: Correlate pricing with high-energy devices, implement EV charging optimization patterns, and add HVAC scheduling correlation

### Story 34.5: Calendar Generator Foundation
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 hours
- **Description**: Create `SyntheticCalendarGenerator` class with work schedule profiles and basic event generation

### Story 34.6: Work Schedule Generation
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 hours
- **Description**: Implement standard 9-5 schedules, shift work and remote work patterns, and generate commute events

### Story 34.7: Routine & Travel Events
- **Story Points**: 4
- **Priority**: P0
- **Effort**: 3-4 hours
- **Description**: Generate daily routines (morning, evening), weekly routines (grocery, gym), and occasional travel events

### Story 34.8: Presence Pattern Calculation
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 hours
- **Description**: Calculate presence from calendar events, implement home/away/work states, and add presence transitions

### Story 34.9: Calendar-Device Correlation
- **Story Points**: 4
- **Priority**: P0
- **Effort**: 3-4 hours
- **Description**: Correlate presence with device usage, implement away → security on patterns, and add home → comfort settings patterns

### Story 34.10: Pricing & Calendar Testing
- **Story Points**: 4
- **Priority**: P0
- **Effort**: 3-4 hours
- **Description**: Unit tests for pricing generator, unit tests for calendar generator, and integration tests for correlation

### Story 34.11: Pricing & Calendar Pipeline Integration
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 hours
- **Description**: Integrate with synthetic home generation script, update home JSON structure, and validate data output

## Dependencies

### External Dependencies
- None - standalone generators

### Internal Dependencies
- Epic 33 completion (Foundation External Data Generation)
- Existing `SyntheticHomeGenerator` pipeline
- Home metadata (type, location) for context
- Device list for correlation
- Events for correlation validation

### Story Dependencies
- Stories 34.1-34.3: Foundation → TOU → Market (sequential)
- Story 34.4: Depends on 34.1-34.3
- Stories 34.5-34.7: Foundation → Work → Routines (sequential)
- Story 34.8: Depends on 34.5-34.7
- Story 34.9: Depends on 34.8
- Story 34.10: Depends on all previous
- Story 34.11: Depends on all previous

## Risks & Mitigation

### Medium Risk
- **Correlation Complexity**: Mitigation through simple correlation rules initially, iterate based on validation
- **Data Realism**: Mitigation through validation against real-world patterns and comprehensive testing

### Low Risk
- **Performance with Large Datasets**: Mitigation through batch processing and early profiling (NUC-optimized)
- **Breaking Existing Pipeline**: Mitigation through integration tests and backward compatibility
- **Resource Constraints**: Mitigation through lightweight generators, in-memory processing, no external API calls

## Testing Strategy

### Unit Tests
- Pricing region profiles
- Time-of-use pricing logic
- Market dynamics
- Work schedule generation
- Routine event generation
- Presence calculation
- Correlation logic

### Integration Tests
- Full pipeline with all external data
- Verify data structure
- Verify correlations
- Verify realism

### Data Quality Tests
- Pricing follows time-of-use patterns
- Calendar events are consistent
- Presence transitions are logical

## Acceptance Criteria

- [x] Pricing generator creates realistic time-of-use pricing data
- [x] Calendar generator creates realistic schedules and events
- [x] Data correlates with energy device and presence patterns
- [x] Multiple pricing regions and work schedules supported
- [x] All unit tests passing
- [x] Integration tests validate end-to-end pipeline
- [x] Documentation complete

## Definition of Done

- [x] All stories completed and tested
- [x] Pricing and calendar generators integrated with pipeline
- [x] Unit tests passing (>80% coverage) - **95% pricing, 86% calendar**
- [x] Integration tests passing
- [x] Data quality validated
- [x] Documentation updated
- [x] Code review completed
- [x] QA approval received

## QA Results

### Review Date: 2025-01-26

### Reviewed By: Quinn (Test Architect)

### Gate Status

**Gate: PASS** → `docs/qa/gates/34-advanced-external-data-generation-epic.yml`

### Quality Score: 95/100

### Summary

All 11 stories completed with excellent quality. Test coverage exceeds requirements (95% pricing, 86% calendar). All acceptance criteria met, integration verified, and code quality exceeds standards.

### Test Results

- **Total Tests:** 48 tests, all passing
- **Pricing Generator:** 33 tests, 95% coverage
- **Calendar Generator:** 15 tests, 86% coverage
- **Integration:** Verified and working

### Code Quality

- ✅ No linter errors
- ✅ Type hints throughout
- ✅ Pydantic validation
- ✅ Structured logging
- ✅ NUC-optimized

### NFR Validation

- **Security:** PASS - No external dependencies, local generation only
- **Performance:** PASS - Exceeds targets (<50ms pricing, <100ms calendar)
- **Reliability:** PASS - Comprehensive error handling
- **Maintainability:** PASS - Clean code, excellent documentation

### Detailed Review

See full QA summary: `docs/qa/34-advanced-external-data-generation-qa-summary.md`

---

**Created**: November 25, 2025  
**Last Updated**: November 25, 2025  
**Author**: BMAD Master  
**Reviewers**: System Architect, QA Lead  
**Related Assessment**: `implementation/analysis/SYNTHETIC_EXTERNAL_DATA_BMAD_ASSESSMENT.md`  
**Deployment Context**: Single-home NUC (Intel NUC i3/i5, 8-16GB RAM) - see `docs/prd.md` section 1.7  
**Context7 KB References**: 
- FastAPI patterns: `docs/kb/context7-cache/fastapi-pydantic-settings.md`
- Edge ML deployment: `docs/kb/context7-cache/edge-ml-deployment-home-assistant.md`

