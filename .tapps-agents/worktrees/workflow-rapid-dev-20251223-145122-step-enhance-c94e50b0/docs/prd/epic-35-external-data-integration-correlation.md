# Epic 35: External Data Integration & Correlation

**Epic ID:** 35  
**Title:** External Data Integration & Correlation  
**Status:** Planning  
**Priority:** High  
**Complexity:** Medium  
**Timeline:** 1-2 weeks  
**Story Points:** 16-22  
**Related Design:** `implementation/analysis/SYNTHETIC_EXTERNAL_DATA_GENERATION_DESIGN.md`  
**Related Analysis:** `implementation/analysis/CORRELATION_ANALYSIS_INTEGRATION_SUMMARY.md`  
**Depends on:** Epic 33 (Foundation) and Epic 34 (Advanced)  
**Feeds into:** Epic 36-38 (Correlation Analysis Implementation)

---

## Epic Goal

Unify all external data generators into a cohesive system with intelligent correlation engine that ensures realistic relationships between external data and device events. This epic provides the foundational external data needed for advanced correlation analysis (Epic 36-38).

## Epic Description

### Existing System Context

**Deployment Context:**
- **Single-home NUC deployment** (Intel NUC i3/i5, 8-16GB RAM)
- Resource-constrained environment optimized for local processing
- All services run on one machine via Docker Compose
- Training data generation runs locally (no cloud dependencies)

**Current functionality:**
- Synthetic home generation pipeline with all external data generators (Epic 33 & 34)
- Weather, carbon intensity, pricing, and calendar generators operational
- Individual generators working independently

**Technology stack:**
- Python 3.11, FastAPI
- Location: `services/ai-automation-service/src/training/`
- **2025 Patterns**: Pydantic Settings, async/await, type hints, structured logging
- **Context7 KB**: FastAPI patterns, Python best practices (see `docs/kb/context7-cache/`)

**Integration:** Unify all generators into single orchestrator with correlation validation

### Enhancement Details

**Two major components:**

1. **Unified External Data Generator** - Orchestrator that coordinates all four generators
2. **Correlation Engine** - Validates and enforces realistic relationships between external data and device events

**Impact:** Production-ready synthetic data generation with intelligent correlation validation

**How it integrates:**
- New orchestrator class in `services/ai-automation-service/src/training/`
- Correlation engine validates all relationships
- Full pipeline integration with existing synthetic home generation
- Comprehensive validation and testing

**Success criteria:**
- ✅ Unified `SyntheticExternalDataGenerator` orchestrator
- ✅ Correlation engine validates all relationships
- ✅ Full pipeline integration with existing synthetic home generation
- ✅ Comprehensive validation and testing
- ✅ Documentation complete
- ✅ Performance meets requirements

## Business Value

- **Single Unified Interface**: One orchestrator for all external data simplifies usage and maintenance
- **Intelligent Correlation**: Correlation engine ensures training data quality and realism
- **End-to-End Validation**: Validates entire synthetic data pipeline
- **Production-Ready**: Complete, tested, and documented solution ready for production use

## Success Criteria

- ✅ Unified `SyntheticExternalDataGenerator` orchestrator
- ✅ Correlation engine validates all relationships
- ✅ Full pipeline integration with existing synthetic home generation
- ✅ Comprehensive validation and testing
- ✅ Documentation complete
- ✅ Performance meets requirements (<500ms per home generation including all external data)

## Technical Architecture

### Unified Generator Structure

```
SyntheticHomeGenerator
    ↓
SyntheticAreaGenerator
    ↓
SyntheticDeviceGenerator
    ↓
SyntheticEventGenerator
    ↓
SyntheticExternalDataGenerator (Orchestrator)
    ├─ SyntheticWeatherGenerator
    ├─ SyntheticCarbonIntensityGenerator
    ├─ SyntheticElectricityPricingGenerator
    └─ SyntheticCalendarGenerator
    ↓
CorrelationEngine
    ├─ Weather → HVAC correlation
    ├─ Carbon/Pricing → Energy device correlation
    └─ Calendar → Presence → Device correlation
    ↓
Home JSON with validated external data
```

### File Locations

- **Orchestrator**: `services/ai-automation-service/src/training/synthetic_external_data_generator.py`
- **Correlation Engine**: `services/ai-automation-service/src/training/synthetic_correlation_engine.py`
- **Integration Point**: `services/ai-automation-service/src/training/synthetic_home_generator.py`

### Resource Constraints (NUC Deployment)

**Memory Optimization:**
- Orchestrator coordinates generators without duplicating data
- Correlation engine uses lightweight rule-based validation (not ML models)
- In-memory processing only (no database writes during generation)
- Target: <150MB memory for orchestrator + correlation engine

**Performance Targets:**
- Orchestrator coordination: <50ms overhead
- Correlation validation: <100ms per home
- Total pipeline (with all external data): <500ms per home
- Suitable for batch processing 100-120 homes in <60 seconds

**2025 Best Practices:**
- Use Pydantic models for data validation (see `docs/kb/context7-cache/fastapi-pydantic-settings.md`)
- Structured logging with Python logging module
- Type hints throughout (Python 3.11+)
- Async/await for I/O operations
- Context7 KB patterns for FastAPI integration
- Rule-based correlation (lightweight, no ML inference overhead)

### Correlation Rules

**Weather → HVAC:**
- High temperature → AC on
- Low temperature → Heat on
- Window open → HVAC off/less active

**Carbon/Pricing → Energy Devices:**
- Low carbon intensity → EV charging
- High pricing → Delay high-energy devices
- Solar peak → Increase renewable usage

**Calendar → Presence → Devices:**
- Away → Security on, lights off
- Home → Comfort settings, lights on
- Work → Reduced device activity

## Stories

### Story 35.1: Unified External Data Generator
- **Story Points**: 4
- **Priority**: P0
- **Effort**: 3-4 hours
- **Description**: Create `SyntheticExternalDataGenerator` orchestrator class, integrate all four generators, and implement unified generation method

### Story 35.2: Correlation Engine Foundation
- **Story Points**: 4
- **Priority**: P0
- **Effort**: 3-4 hours
- **Description**: Create correlation engine class, implement weather → HVAC correlation rules, and implement carbon/pricing → energy device correlation rules

### Story 35.3: Calendar-Presence-Device Correlation
- **Story Points**: 4
- **Priority**: P0
- **Effort**: 3-4 hours
- **Description**: Implement calendar → presence correlation, implement presence → device correlation, and add validation logic

### Story 35.4: Full Pipeline Integration
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 hours
- **Description**: Integrate with `generate_synthetic_homes.py`, update home JSON structure with all external data, and add configuration options

### Story 35.5: End-to-End Validation
- **Story Points**: 4
- **Priority**: P0
- **Effort**: 3-4 hours
- **Description**: Create validation tests for all correlations, validate data realism (temperature ranges, pricing patterns, etc.), and performance testing

### Story 35.6: Documentation & Testing
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 hours
- **Description**: Update design document with implementation details, create usage examples, and add integration documentation

## Dependencies

### External Dependencies
- None - uses existing generators

### Internal Dependencies
- Epic 33 completion (Foundation External Data Generation)
- Epic 34 completion (Advanced External Data Generation)
- Existing `SyntheticHomeGenerator` pipeline
- All four external data generators operational

### Story Dependencies
- Story 35.1: Foundation (no dependencies)
- Story 35.2: Depends on Epic 33 & 34 completion
- Story 35.3: Depends on 35.2
- Story 35.4: Depends on 35.1-35.3
- Story 35.5: Depends on 35.4
- Story 35.6: Depends on all previous

## Risks & Mitigation

### Medium Risk
- **Correlation Complexity**: Mitigation through simple correlation rules initially, iterate based on validation (rule-based, not ML)
- **Performance with Large Datasets**: Mitigation through profiling early, optimize batch processing (NUC-optimized)

### Low Risk
- **Data Realism**: Mitigation through validation against real-world patterns, add comprehensive tests
- **Breaking Existing Pipeline**: Mitigation through integration tests, backward compatibility
- **Resource Constraints**: Mitigation through lightweight orchestrator, rule-based correlation (no ML inference), in-memory processing

## Testing Strategy

### Unit Tests
- Orchestrator coordination
- Correlation rule validation
- Weather → HVAC correlation
- Carbon/Pricing → Energy device correlation
- Calendar → Presence → Device correlation

### Integration Tests
- Full pipeline with all external data
- Verify all correlations
- Verify data realism
- Performance benchmarks

### Data Quality Tests
- All correlations are realistic
- Temperature ranges are valid
- Pricing patterns are logical
- Calendar events are consistent
- Presence transitions are logical

## Acceptance Criteria

- [ ] Unified orchestrator coordinates all generators
- [ ] Correlation engine validates all relationships
- [ ] Full pipeline integration complete
- [ ] All validation tests passing
- [ ] Performance meets requirements
- [ ] Documentation complete

## Definition of Done

- [ ] All stories completed and tested
- [ ] Unified orchestrator operational
- [ ] Correlation engine validates all relationships
- [ ] Full pipeline integration complete
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] Code review completed
- [ ] QA approval received

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

