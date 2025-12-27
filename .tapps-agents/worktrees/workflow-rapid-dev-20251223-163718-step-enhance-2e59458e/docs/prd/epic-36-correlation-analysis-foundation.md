# Epic 36: Correlation Analysis Foundation

**Epic ID:** 36  
**Title:** Correlation Analysis Foundation (Phase 1 Quick Wins)  
**Status:** Planning  
**Priority:** High  
**Complexity:** Medium  
**Timeline:** 6-10 days  
**Story Points:** 25-35  
**Related Design:** `implementation/analysis/CORRELATION_ANALYSIS_INTEGRATION_SUMMARY.md`  
**Related Analysis:** `implementation/analysis/CORRELATION_ANALYSIS_DATA_MAPPING_DESIGN.md`, `implementation/analysis/2025_ML_TECHNIQUES_CORRELATION_ANALYSIS.md`  
**Depends on:** Epic 33-35 (External Data Generation)

---

## Epic Goal

Implement foundational correlation analysis capabilities using 2025 state-of-the-art ML techniques (TabPFN, Streaming Continual Learning) to achieve 100-1000x performance improvements and enable real-time correlation updates for pattern detection, synergy detection, and automation suggestions.

## Epic Description

### Existing System Context

**Deployment Context:**
- **Single-home NUC deployment** (Intel NUC i3/i5, 8-16GB RAM)
- Resource-constrained environment optimized for local processing
- All services run on one machine via Docker Compose
- Real-time event processing via WebSocket ingestion

**Current functionality:**
- Event data in InfluxDB (home_assistant_events bucket)
- Pattern detection system (SQLite storage)
- Synergy detection system (SQLite storage)
- External data services (weather, carbon, electricity, air quality) - Epic 33-35
- Device and entity metadata in SQLite (Epic 22)
- Blueprint-dataset correlation service (implemented)

**Technology stack:**
- Python 3.11, FastAPI
- Location: `services/ai-automation-service/src/synergy_detection/` and `src/correlation/` (new)
- **2025 Patterns**: Pydantic Settings, async/await, type hints, structured logging
- **Context7 KB**: FastAPI patterns, Python best practices (see `docs/kb/context7-cache/`)

**Current bottleneck:**
- O(n²) correlation matrix computation (single-home: ~50-100 entities = 1,225-4,950 pairs, manageable but still inefficient)
- Batch processing: Updates correlations periodically
- No real-time correlation updates
- Limited external data integration

**Single-Home Optimization:**
- Single-home NUC deployment means smaller entity count (~50-100 devices vs multi-home)
- Correlation analysis focused on single home's device relationships
- Real-time processing for single-home event stream
- Resource-constrained: Memory and CPU optimized for NUC hardware

### Enhancement Details

**Four foundational correlation analysis components:**

1. **TabPFN Correlation Prediction** - Predict likely correlated pairs (100-1000x faster, ROI: 3.0)
2. **Streaming Continual Learning** - Real-time correlation updates (O(1) per event, ROI: 3.0)
3. **External Data Features** - Add weather, carbon, electricity, air quality to correlation vectors
4. **Correlation Caching** - Cache computed correlations (100-1000x speedup, ROI: 4.5)

**Impact:** 100-1000x faster correlation computation, +20-30% precision improvement, real-time correlation updates

**How it integrates:**
- New correlation analysis service in `services/ai-automation-service/src/correlation/`
- Integrates with existing pattern detection and synergy detection
- Uses external data from Epic 33-35
- Enhances automation suggestion generation with correlation insights

**Success criteria:**
- ✅ TabPFN predicts likely correlated pairs (only compute ~1% of pairs)
- ✅ Streaming updates correlations in real-time (O(1) per event)
- ✅ External data features included in correlation vectors
- ✅ Correlation caching reduces redundant computation
- ✅ 100-1000x faster correlation computation
- ✅ +20-30% precision improvement
- ✅ Real-time correlation updates as events arrive

## Business Value

- **Performance Breakthrough**: 100-1000x faster correlation computation enables real-time analysis
- **Quality Improvement**: +20-30% precision improvement in correlation detection
- **Real-time Capabilities**: Always up-to-date correlations, no batch processing delays
- **Context-Aware**: External data (weather, calendar, energy) enhances correlation analysis
- **Foundation for Advanced Features**: Establishes foundation for Phase 2 and Phase 3 enhancements

## Success Criteria

- ✅ TabPFN correlation prediction implemented
- ✅ Streaming continual learning implemented
- ✅ External data features integrated
- ✅ Correlation caching operational
- ✅ 100-1000x faster correlation computation
- ✅ +20-30% precision improvement
- ✅ Real-time correlation updates
- ✅ Unit tests for all components
- ✅ Integration tests validate end-to-end pipeline
- ✅ Performance benchmarks met

## Technical Architecture

### Correlation Analysis Service Structure

```
ai-automation-service/src/correlation/
├── __init__.py
├── tabpfn_predictor.py          # TabPFN correlation prediction
├── streaming_tracker.py          # Streaming continual learning
├── correlation_cache.py          # Correlation caching
├── feature_extractor.py          # Feature extraction (with external data)
└── correlation_service.py        # Unified correlation service
```

### Integration Flow

```
Events + External Data (Epic 33-35)
    ↓
Correlation Analysis Service
    ├─ TabPFN Predictor (predict likely pairs)
    ├─ Streaming Tracker (real-time updates)
    ├─ Feature Extractor (with external data)
    └─ Correlation Cache (cache results)
    ↓
Correlation Insights
    ↓
Pattern Detection (enhanced)
    ↓
Synergy Detection (enhanced)
    ↓
Automation Suggestions (with correlation explanations)
```

### File Locations

- **TabPFN Predictor**: `services/ai-automation-service/src/correlation/tabpfn_predictor.py`
- **Streaming Tracker**: `services/ai-automation-service/src/correlation/streaming_tracker.py`
- **Correlation Cache**: `services/ai-automation-service/src/correlation/correlation_cache.py`
- **Feature Extractor**: `services/ai-automation-service/src/correlation/feature_extractor.py`
- **Correlation Service**: `services/ai-automation-service/src/correlation/correlation_service.py`
- **Integration Points**: 
  - Pattern detection: `services/ai-automation-service/src/pattern_detection/`
  - Synergy detection: `services/ai-automation-service/src/synergy_detection/`

### Resource Constraints (NUC Deployment)

**Memory Optimization (Single-Home NUC):**
- TabPFN: ~30MB memory (CPU-based, no GPU needed, single-home scale)
- Streaming tracker: <5MB memory (in-memory statistics, ~50-100 devices)
- Correlation cache: <20MB memory (SQLite-backed, single-home data)
- Feature extractor: <5MB memory (in-memory feature computation, reduced scale)
- Total: <60MB memory for correlation service (single-home optimized)

**Performance Targets:**
- TabPFN prediction: <10ms per prediction batch
- Streaming update: <1ms per event (O(1))
- Cache hit: <1ms per correlation lookup
- Total correlation computation: 100-1000x faster than O(n²) matrix

**2025 Best Practices:**
- Use Pydantic models for data validation (see `docs/kb/context7-cache/fastapi-pydantic-settings.md`)
- Structured logging with Python logging module
- Type hints throughout (Python 3.11+)
- Async/await for I/O operations
- Context7 KB patterns for FastAPI integration
- Use River library for streaming statistics

## Stories

### Story 36.1: TabPFN Correlation Predictor Foundation
- **Story Points**: 4
- **Priority**: P0
- **Effort**: 2-3 days
- **Description**: Create `TabPFNCorrelationPredictor` class, implement pair feature extraction, and basic correlation prediction

### Story 36.2: TabPFN Training and Integration
- **Story Points**: 4
- **Priority**: P0
- **Effort**: 2-3 days
- **Description**: Implement training on known synergies/patterns, integrate with pattern/synergy detection, and optimize prediction accuracy

### Story 36.3: Streaming Continual Learning Foundation
- **Story Points**: 4
- **Priority**: P0
- **Effort**: 3-5 days
- **Description**: Create `StreamingCorrelationTracker` class using River library, implement O(1) correlation updates, and integrate with WebSocket event stream

### Story 36.4: External Data Feature Extraction
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 1-2 days
- **Description**: Create `CorrelationFeatureExtractor` class, add weather/carbon/electricity/air quality features, and integrate with TabPFN and streaming tracker

### Story 36.5: Correlation Caching System
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 1-2 days
- **Description**: Create `CorrelationCache` class (SQLite or Redis-backed), implement cache hit/miss logic, and optimize cache key generation

### Story 36.6: Unified Correlation Service
- **Story Points**: 4
- **Priority**: P0
- **Effort**: 2-3 days
- **Description**: Create `CorrelationService` orchestrator, integrate TabPFN + Streaming + Cache + Features, and provide unified API

### Story 36.7: Pattern Detection Integration
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 days
- **Description**: Integrate correlation service with pattern detection, enhance patterns with correlation insights, and validate correlation-validated patterns

### Story 36.8: Synergy Detection Integration
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 days
- **Description**: Integrate correlation service with synergy detection, use TabPFN to predict likely synergies, and validate correlations against synergies

### Story 36.9: Performance Testing and Optimization
- **Story Points**: 4
- **Priority**: P0
- **Effort**: 2-3 days
- **Description**: Create performance benchmarks, validate 100-1000x speed improvement, measure precision improvement, and optimize for NUC constraints

### Story 36.10: Documentation and Testing
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 days
- **Description**: Comprehensive unit tests, integration tests, update documentation, and create usage examples

## Dependencies

### External Dependencies
- **TabPFN library**: `pip install tabpfn`
- **River library**: `pip install river` (for streaming statistics)
- **NumPy**: For correlation computation
- **SQLite or Redis**: For correlation cache

### Internal Dependencies
- Epic 33-35 completion (External Data Generation) - for external data features
- Existing pattern detection system
- Existing synergy detection system
- Device/entity metadata (Epic 22)
- Event data in InfluxDB

### Story Dependencies
- Stories 36.1-36.2: TabPFN foundation → Training (sequential)
- Story 36.3: Streaming (independent, can run parallel)
- Story 36.4: External data features (depends on Epic 33-35)
- Story 36.5: Caching (independent)
- Story 36.6: Unified service (depends on 36.1-36.5)
- Stories 36.7-36.8: Integration (depends on 36.6)
- Story 36.9: Performance (depends on 36.6-36.8)
- Story 36.10: Documentation (depends on all previous)

## Risks & Mitigation

### Medium Risk
- **TabPFN Learning Curve**: Mitigation through documentation review, start with simple examples
- **Streaming Complexity**: Mitigation through River library (proven solution), incremental implementation
- **Performance Validation**: Mitigation through benchmarking early, validate against baseline

### Low Risk
- **Memory Constraints**: Mitigation through lightweight implementations, NUC-optimized memory targets
- **Integration Complexity**: Mitigation through incremental integration, comprehensive testing
- **External Data Integration**: Mitigation through Epic 33-35 completion, clear interfaces

## Testing Strategy

### Unit Tests
- TabPFN prediction accuracy
- Streaming correlation updates
- Feature extraction with external data
- Cache hit/miss logic
- Correlation service orchestration

### Integration Tests
- End-to-end correlation computation
- Pattern detection integration
- Synergy detection integration
- Real-time event stream integration
- External data integration

### Performance Tests
- Baseline correlation computation (O(n²) matrix)
- TabPFN prediction speed
- Streaming update speed
- Cache performance
- Overall 100-1000x speed improvement validation

### Data Quality Tests
- Correlation accuracy vs ground truth
- Precision improvement measurement
- Real-time update correctness

## Acceptance Criteria

- [ ] TabPFN predicts likely correlated pairs with 85-90% precision
- [ ] Streaming tracker updates correlations in O(1) time
- [ ] External data features included in correlation vectors
- [ ] Correlation cache reduces redundant computation
- [ ] 100-1000x faster correlation computation achieved
- [ ] +20-30% precision improvement measured
- [ ] Real-time correlation updates working
- [ ] All unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Performance benchmarks met
- [ ] Documentation complete

## Definition of Done

- [ ] All stories completed and tested
- [ ] TabPFN correlation prediction operational
- [ ] Streaming continual learning operational
- [ ] External data features integrated
- [ ] Correlation caching operational
- [ ] Unified correlation service working
- [ ] Pattern and synergy detection integrated
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Performance benchmarks met (100-1000x faster)
- [ ] Documentation updated
- [ ] Code review completed
- [ ] QA approval received

---

**Created**: November 25, 2025  
**Last Updated**: November 25, 2025  
**Author**: BMAD Master  
**Reviewers**: System Architect, QA Lead  
**Related Analysis**: 
- `implementation/analysis/CORRELATION_ANALYSIS_INTEGRATION_SUMMARY.md`
- `implementation/analysis/CORRELATION_ANALYSIS_DATA_MAPPING_DESIGN.md`
- `implementation/analysis/2025_ML_TECHNIQUES_CORRELATION_ANALYSIS.md`
**Deployment Context**: Single-home NUC (Intel NUC i3/i5, 8-16GB RAM) - see `docs/prd.md` section 1.7  
**Context7 KB References**: 
- FastAPI patterns: `docs/kb/context7-cache/fastapi-pydantic-settings.md`
- Edge ML deployment: `docs/kb/context7-cache/edge-ml-deployment-home-assistant.md`

