# Epic AI-17: Simulation Framework Core

**Epic ID:** AI-17  
**Title:** Simulation Framework Core - End-to-End Workflow Validation  
**Status:** 📋 **PLANNING**  
**Type:** Brownfield Enhancement (Testing & Validation Infrastructure)  
**Priority:** High (Pre-Production Quality Blocker)  
**Effort:** 10 Stories (42 story points, 5-6 weeks estimated)  
**Created:** January 2025  
**Based On:** Training Data Quality Review, Pattern Detection Analysis, YAML Validation Requirements, Epic AI-16 Design  
**Note:** This epic provides comprehensive simulation infrastructure separate from production deployment

---

## Epic Goal

Build a comprehensive, fast, high-volume simulation framework that validates the complete 3 AM batch workflow and Ask AI conversational flow end-to-end using synthetic data, mocked services, and integrated ML model training/validation. This framework enables pre-production validation of both pipelines (model training → event fetching → pattern detection → suggestion generation → YAML creation → validation) at scale and speed, without real API calls or network dependencies.

**⚠️ CRITICAL: Simulation code is deployed separately from production**
- **Location**: `simulation/` directory at project root (NOT in `services/`)
- **Isolation**: Zero dependencies on production services
- **Deployment**: Separate Docker Compose profile, excluded from production builds
- **Purpose**: Development, testing, CI/CD validation only

**Business Value:**
- **+4,000% Validation Speed** (Real-time: hours → Simulation: minutes)
- **-100% API Costs** (No OpenAI calls, no HA API calls)
- **+95% Deployment Confidence** (Validate before production)
- **+100% Test Coverage** (100+ homes, 50+ queries in minutes)
- **+80% YAML Accuracy** (Multi-stage validation catches errors early)

---

## Existing System Context

### Current Testing Infrastructure

**Location:** `services/ai-automation-service/tests/`, `scripts/`

**Current State:**
1. **Unit Tests:**
   - ✅ 18 unit tests for `DailyAnalysisScheduler` (~95% coverage)
   - ✅ Pattern detector unit tests
   - ✅ Suggestion generator unit tests
   - ⚠️ **GAP**: No E2E validation of complete 3 AM workflow
   - ⚠️ **GAP**: No Ask AI flow simulation

2. **Integration Tests:**
   - ✅ Ask AI E2E tests (`tests/integration/test_ask_ai_end_to_end.py`)
   - ✅ YAML generation tests
   - ⚠️ **GAP**: Tests hit real services (HA, OpenAI)
   - ⚠️ **GAP**: Cannot run at scale (100+ homes)

3. **YAML Validation:**
   - ✅ Multi-stage validation pipeline (`_validate_generated_yaml()`)
   - ✅ Entity ID validation (`EntityIDValidator`)
   - ✅ Structure validation (`AutomationYAMLValidator`)
   - ⚠️ **GAP**: No batch validation at scale
   - ⚠️ **GAP**: No prompt validation framework

### Technology Stack

- **Language:** Python 3.12+ (async/await, type hints, Pydantic 2.x)
- **Frameworks:** FastAPI 0.115.x, Pydantic Settings, pytest-asyncio 0.23.x
- **Location:** `simulation/` (project root, separate from production)
- **2025 Patterns:** 
  - Type hints throughout (`typing` module, `collections.abc` for generics)
  - Structured logging (`structlog` 24.x)
  - Async generators for data streaming
  - Dependency injection for mock services
  - Context managers for resource management
  - Pydantic 2.x with `BaseModel` and `Field` validators
- **Context7 KB References:**
  - FastAPI 2025 patterns (async routes, dependency injection)
  - pytest-asyncio 2025 best practices (async fixtures, async tests)
  - Python 3.12+ features (match/case, improved type hints)
  - Pydantic 2.x validation patterns

### Integration Points

- `DailyAnalysisScheduler` - 3 AM workflow orchestrator (from production)
- `UnifiedPromptBuilder` - Prompt generation for both flows (from production)
- `generate_automation_yaml()` - YAML generation service (from production)
- `_validate_generated_yaml()` - Multi-stage validation (from production)
- `scripts/prepare_for_production.py` - Model training pipeline (from production)
- `SyntheticHomeGenerator` - Synthetic data generation (Epic AI-11, from production)

**Note:** Simulation framework imports from production code but runs in isolated environment with mocked dependencies.

---

## Enhancement Details

### What's Being Added

1. **Simulation Engine Core** (NEW - Isolated)
   - `SimulationEngine` class - Main orchestrator
   - Mock service factories (InfluxDB, OpenAI, MQTT, Data API, Device Intelligence, HA)
   - Dependency injection framework
   - Synthetic data loader integration
   - Model loading infrastructure (production-style)
   - **Location**: `simulation/src/engine/`

2. **Mock Service Layer** (NEW - Isolated)
   - `MockInfluxDBClient` - In-memory event storage
   - `MockOpenAIClient` - Deterministic YAML/suggestion generation
   - `MockMQTTClient` - No-op implementation
   - `MockDataAPIClient` - Direct DataFrame returns
   - `MockDeviceIntelligenceClient` - Pre-computed capabilities
   - `MockHAConversationAPI` - Deterministic entity extraction
   - `MockHAClient` - Entity validation simulation
   - `MockSafetyValidator` - Safety check simulation
   - **Location**: `simulation/src/mocks/`

3. **3 AM Workflow Simulation** (NEW - Isolated)
   - Complete `run_daily_analysis()` workflow execution
   - All 6 phases with mocked services
   - Real logic (pattern detection, synergy detection, models)
   - Mocked data (synthetic homes, events)
   - Performance benchmarking
   - **Location**: `simulation/src/workflows/`

4. **Ask AI Flow Simulation** (NEW - Isolated)
   - Complete conversational flow (query → suggestion → approval → YAML)
   - Mock HA Conversation API for entity extraction
   - Mock OpenAI for suggestion and YAML generation
   - User approval simulation
   - Final validation and deployment readiness
   - **Location**: `simulation/src/workflows/`

5. **Prompt & YAML Validation** (NEW - Isolated)
   - Prompt quality validation framework
   - YAML validation framework (multi-stage)
   - Ground truth comparison (with automation datasets)
   - Scoring engines
   - **Location**: `simulation/src/validation/`

6. **Metrics & Reporting** (NEW - Isolated)
   - Pattern detection metrics
   - Suggestion quality metrics
   - YAML generation metrics
   - Performance benchmarks
   - Report generation (JSON, CSV, HTML)
   - **Location**: `simulation/src/metrics/`, `simulation/src/reporting/`

### Folder Structure (Isolated from Production)

```
simulation/
├── src/
│   ├── engine/              # Core simulation engine
│   ├── mocks/               # Mock service implementations
│   ├── workflows/           # Workflow simulators (3 AM, Ask AI)
│   ├── validation/          # Validation frameworks
│   ├── metrics/             # Metrics collection
│   ├── reporting/           # Report generation
│   └── config.py            # Configuration management
├── tests/                   # Simulation framework tests
├── data/                    # Generated/cached synthetic data
├── results/                 # Simulation results and reports
├── cli.py                   # CLI interface
├── requirements.txt         # Simulation-only dependencies
├── docker-compose.yml       # Separate Docker Compose (simulation profile)
└── README.md                # Simulation framework documentation
```

**Production Exclusion:**
- NOT included in `services/` directory
- NOT built in production Docker images
- NOT deployed in production environment
- Uses Docker Compose profile: `simulation` (excluded from default)

### Success Criteria

1. **Functional:**
   - Simulation engine processes 100 homes in < 10 minutes
   - Simulation engine processes 50 Ask AI queries in < 5 minutes
   - All 6 phases of 3 AM workflow execute successfully
   - Complete Ask AI flow executes successfully
   - Model training integration works (pre-trained and during simulation)
   - Prompt validation catches quality issues
   - YAML validation catches errors before deployment
   - Zero real API calls (all mocked)
   - Zero network dependencies

2. **Technical:**
   - All code uses 2025 patterns (Python 3.12+, async/await, type hints, Pydantic 2.x)
   - >90% test coverage for simulation framework
   - Memory usage < 2GB for 100 homes
   - Deterministic results (reproducible)
   - Separated from production codebase (different directory)

3. **Quality:**
   - YAML validation rate: >95% (all stages passed)
   - Entity ID accuracy: >98%
   - Prompt quality score: >90%
   - Deployment readiness: >90% of suggestions ready

---

## Story Creation Requirements

**⚠️ CRITICAL: All stories created from this epic must:**
1. **Assign to Dev Agent**: Stories must be created with `@dev` agent in `.bmad-core` configuration
2. **Reference Context7 KB**: All stories must reference Context7 KB documentation for:
   - FastAPI 2025 patterns and best practices
   - Python 3.12+ async/await patterns
   - Pydantic 2.x validation and settings
   - pytest-asyncio 2025 testing patterns
   - Mock service implementation patterns
   - Dependency injection patterns

**Story Creation Process:**
- Use BMAD story creation workflow with `@dev` agent
- Include Context7 KB references in story acceptance criteria
- Use Context7 KB for technology decisions and patterns

---

## Stories

### Phase 1: Foundation & Core Engine (Weeks 1-2)

#### Story AI17.1: Simulation Engine Core Framework
**Type:** Foundation  
**Points:** 5  
**Effort:** 10-12 hours

Create the core `SimulationEngine` class with dependency injection framework and mock service factories.

**Acceptance Criteria:**
- `SimulationEngine` class with configuration management
- Mock service factory pattern (InfluxDB, OpenAI, MQTT, Data API, Device Intelligence, HA)
- Dependency injection framework
- Synthetic data loader integration
- Model loading infrastructure (production-style)
- Configuration management (pre-trained vs train-during-simulation)
- Unit tests for core framework (>90% coverage)
- All code uses 2025 patterns (type hints, async/await, Pydantic 2.x)

**Files:**
- `simulation/src/engine/simulation_engine.py` (new)
- `simulation/src/engine/config.py` (new)
- `simulation/src/engine/dependency_injection.py` (new)
- `simulation/tests/test_engine.py` (new)

**Context7 KB References:**
- FastAPI dependency injection patterns (Context7 KB mandatory)
- Python 3.12+ async context managers (Context7 KB mandatory)
- Pydantic Settings 2.x configuration (Context7 KB mandatory)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** None

---

#### Story AI17.2: Mock Service Implementations
**Type:** Foundation  
**Points:** 5  
**Effort:** 10-12 hours

Implement all mock services for external dependencies.

**Acceptance Criteria:**
- `MockInfluxDBClient` - In-memory event storage (pandas DataFrames)
- `MockOpenAIClient` - Deterministic YAML/suggestion generation (no API calls)
- `MockMQTTClient` - No-op implementation
- `MockDataAPIClient` - Direct DataFrame returns from synthetic data
- `MockDeviceIntelligenceClient` - Pre-computed capabilities
- `MockHAConversationAPI` - Deterministic entity extraction responses
- `MockHAClient` - Entity validation simulation
- `MockSafetyValidator` - Safety check simulation
- All mocks maintain same interface as real services
- Unit tests for all mock services (>90% coverage)
- Type hints and async/await patterns throughout

**Files:**
- `simulation/src/mocks/influxdb_client.py` (new)
- `simulation/src/mocks/openai_client.py` (new)
- `simulation/src/mocks/mqtt_client.py` (new)
- `simulation/src/mocks/data_api_client.py` (new)
- `simulation/src/mocks/device_intelligence_client.py` (new)
- `simulation/src/mocks/ha_conversation_api.py` (new)
- `simulation/src/mocks/ha_client.py` (new)
- `simulation/src/mocks/safety_validator.py` (new)
- `simulation/tests/test_mocks.py` (new)

**Context7 KB References:**
- pytest-asyncio async fixture patterns (Context7 KB mandatory)
- Python mocking best practices (unittest.mock, pytest-mock) (Context7 KB mandatory)
- Interface matching patterns (Context7 KB mandatory)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Story AI17.1

---

#### Story AI17.3: Model Training Integration
**Type:** Integration  
**Points:** 4  
**Effort:** 8-10 hours

Integrate model training pipeline into simulation framework.

**Acceptance Criteria:**
- Integration with `train_all_models()` from `prepare_for_production.py` (import from production)
- Support pre-trained models (fast mode) - load from `models/` directory
- Support training during simulation (comprehensive mode) - train on simulation dataset
- Model quality validation with thresholds (accuracy, precision, recall)
- Model performance metrics collection (inference latency, memory usage)
- Model loading validation (same as production startup)
- Unit tests for model training integration (>90% coverage)

**Files:**
- `simulation/src/engine/model_training.py` (new)
- `simulation/src/engine/model_loader.py` (new)
- `simulation/tests/test_model_training.py` (new)

**Context7 KB References:**
- Model loading patterns (PyTorch, scikit-learn) (Context7 KB mandatory)
- Performance profiling techniques (Context7 KB mandatory)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Story AI17.1, Epic AI-11 (synthetic homes)

---

### Phase 2: 3 AM Workflow Simulation (Weeks 2-3)

#### Story AI17.4: 3 AM Workflow Integration
**Type:** Integration  
**Points:** 5  
**Effort:** 10-12 hours

Integrate complete 3 AM workflow (`run_daily_analysis()`) with mocked services.

**Acceptance Criteria:**
- Inject mocks into `DailyAnalysisScheduler` (import from production)
- Load models (same as production startup)
- Run complete `run_daily_analysis()` workflow
- All 6 phases execute successfully:
  - Phase 1: Device Capability Update (mocked)
  - Phase 2: Event Fetching (from synthetic data)
  - Phase 3: Pattern Detection (real logic, mocked data)
  - Phase 3c: Synergy Detection (real logic, mocked data)
  - Phase 4: Feature Analysis (real logic, mocked data)
  - Phase 5: Suggestion Generation (mocked OpenAI)
  - Phase 6: Storage & Notifications (mocked)
- Maintain real logic (pattern detection, synergy detection, models)
- Support dependency injection pattern
- Integration tests for complete workflow

**Files:**
- `simulation/src/workflows/daily_analysis_simulator.py` (new)
- `simulation/tests/test_daily_analysis_simulation.py` (new)

**Context7 KB References:**
- Dependency injection in async workflows (Context7 KB mandatory)
- Workflow orchestration patterns (Context7 KB mandatory)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Story AI17.1, Story AI17.2, Story AI17.3

---

#### Story AI17.5: 3 AM Metrics Collection
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

Collect comprehensive metrics for 3 AM workflow simulation.

**Acceptance Criteria:**
- Pattern detection metrics (precision, recall, F1, false positive rate)
- Model performance metrics (accuracy, inference latency)
- Suggestion quality scores (count, relevance)
- Performance benchmarks (execution time per home, memory usage)
- Results aggregation and reporting
- Metrics export (JSON, CSV)
- Unit tests for metrics collection

**Files:**
- `simulation/src/metrics/pattern_metrics.py` (new)
- `simulation/src/metrics/model_metrics.py` (new)
- `simulation/src/metrics/performance_metrics.py` (new)
- `simulation/src/metrics/aggregator.py` (new)
- `simulation/tests/test_metrics.py` (new)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Story AI17.4

---

### Phase 3: Ask AI Flow Simulation (Weeks 3-4)

#### Story AI17.6: Ask AI Flow Integration
**Type:** Integration  
**Points:** 5  
**Effort:** 10-12 hours

Integrate complete Ask AI conversational flow with mocked services.

**Acceptance Criteria:**
- Query simulation (load synthetic queries from test dataset)
- Entity extraction (mock HA Conversation API)
- Entity resolution and enrichment (real logic, mocked data)
- Suggestion generation (mock OpenAI, real prompt building)
- User approval simulation (apply user filters)
- YAML generation (real logic, mocked OpenAI)
- Final validation (mock HA client, mock safety validator)
- Complete flow executes successfully
- Integration tests for complete Ask AI flow
- Support automation dataset integration (DESCRIPTION.md → solution.yaml pairs)

**Files:**
- `simulation/src/workflows/ask_ai_simulator.py` (new)
- `simulation/src/data/synthetic_queries.py` (new)
- `simulation/tests/test_ask_ai_simulation.py` (new)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Story AI17.1, Story AI17.2

---

#### Story AI17.7: Ask AI Metrics Collection
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

Collect comprehensive metrics for Ask AI flow simulation.

**Acceptance Criteria:**
- Query processing time
- Entity extraction accuracy
- Suggestion relevance scores
- User approval simulation results
- YAML generation success rate
- Final validation pass rate
- Ground truth comparison scores (vs solution.yaml)
- Results aggregation and reporting
- Metrics export (JSON, CSV)
- Unit tests for metrics collection

**Files:**
- `simulation/src/metrics/ask_ai_metrics.py` (new)
- `simulation/tests/test_ask_ai_metrics.py` (new)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Story AI17.6

---

### Phase 4: Prompt & YAML Validation (Weeks 4-5)

#### Story AI17.8: Prompt Data Creation & Validation
**Type:** Feature  
**Points:** 4  
**Effort:** 8-10 hours

Implement prompt generation and validation framework.

**Acceptance Criteria:**
- Prompt generation using real `UnifiedPromptBuilder` with mocked data (import from production)
- Prompt quality metrics (token count, entity coverage, capability inclusion)
- Prompt consistency testing (compare prompts across similar patterns/queries)
- Prompt validation (ensure all required components included)
- Prompt performance metrics (building time)
- Integration with 3 AM and Ask AI simulations
- Unit tests for prompt validation (>90% coverage)

**Files:**
- `simulation/src/validation/prompt_validator.py` (new)
- `simulation/src/validation/prompt_quality.py` (new)
- `simulation/tests/test_prompt_validation.py` (new)

**Context7 KB References:**
- Token counting techniques (Context7 KB mandatory)
- Text analysis patterns (Context7 KB mandatory)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Story AI17.4, Story AI17.6

---

#### Story AI17.9: YAML Validation Framework
**Type:** Feature  
**Points:** 5  
**Effort:** 10-12 hours

Implement comprehensive YAML validation framework with ground truth comparison.

**Acceptance Criteria:**
- Multi-stage validation pipeline integration (import from production)
- Entity ID validation against synthetic entity registry
- Auto-fix testing and validation
- Validation metrics collection (validation rate, auto-fix rate, entity accuracy)
- Deployment readiness determination
- Ground truth comparison (compare generated YAML with solution.yaml from automation datasets)
- Semantic similarity scoring
- Integration with 3 AM and Ask AI simulations
- Batch validation support (100+ YAMLs)
- Unit tests for YAML validation (>90% coverage)

**Files:**
- `simulation/src/validation/yaml_validator.py` (new)
- `simulation/src/validation/yaml_metrics.py` (new)
- `simulation/src/validation/ground_truth_comparator.py` (new)
- `simulation/tests/test_yaml_validation.py` (new)

**Context7 KB References:**
- YAML parsing and validation (PyYAML) (Context7 KB mandatory)
- Semantic similarity algorithms (Context7 KB mandatory)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Story AI17.4, Story AI17.6

---

### Phase 5: Batch Processing & Optimization (Weeks 5-6)

#### Story AI17.10: Batch Processing & Parallelization
**Type:** Feature  
**Points:** 4  
**Effort:** 8-10 hours

Implement batch processing and parallelization for high-volume simulation.

**Acceptance Criteria:**
- Process 100+ homes in parallel
- Process 50+ Ask AI queries in parallel
- Progress tracking and reporting
- Results aggregation
- Memory optimization (streaming, batching)
- Performance optimization (async/await, concurrent execution)
- Support quick/standard/stress modes
- Unit tests for batch processing

**Files:**
- `simulation/src/engine/batch/processor.py` (new)
- `simulation/src/engine/batch/parallel_executor.py` (new)
- `simulation/src/engine/batch/progress_tracker.py` (new)
- `simulation/tests/test_batch_processing.py` (new)

**Context7 KB References:**
- Python async/await concurrency patterns (Context7 KB mandatory)
- asyncio.gather, asyncio.create_task patterns (Context7 KB mandatory)
- Memory-efficient data processing (Context7 KB mandatory)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Story AI17.4, Story AI17.6

---

#### Story AI17.11: Results Aggregation & Reporting
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

Implement comprehensive results aggregation and reporting.

**Acceptance Criteria:**
- Aggregate metrics across all simulations
- Generate comprehensive reports (JSON, CSV, HTML)
- Performance summaries (execution time, memory usage)
- Quality summaries (validation rates, accuracy scores)
- Model performance summaries
- Prompt quality summaries
- YAML validation summaries
- Comparison reports (baseline vs improved)
- Unit tests for reporting

**Files:**
- `simulation/src/reporting/aggregator.py` (new)
- `simulation/src/reporting/report_generator.py` (new)
- `simulation/src/reporting/formatters.py` (new)
- `simulation/tests/test_reporting.py` (new)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Story AI17.5, Story AI17.7, Story AI17.8, Story AI17.9

---

#### Story AI17.12: CLI & Integration Scripts
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

Create CLI interface and integration scripts for simulation framework.

**Acceptance Criteria:**
- CLI interface for running simulations
- Configuration file support (YAML/JSON)
- Integration with `prepare_for_production.py` (optional)
- Integration with CI/CD pipeline
- Documentation and usage examples
- Error handling and logging
- Docker Compose profile for simulation environment
- Unit tests for CLI

**Files:**
- `simulation/cli.py` (new)
- `simulation/docker-compose.yml` (new)
- `simulation/README.md` (new)
- `simulation/docs/USAGE.md` (new)
- `simulation/tests/test_cli.py` (new)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Story AI17.10, Story AI17.11

---

## Technical Architecture

### Simulation Engine Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Simulation Framework (simulation/ directory)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ SimulationEngine (Core Orchestrator)                     │  │
│  │  - Configuration Management                              │  │
│  │  - Dependency Injection                                   │  │
│  │  - Workflow Orchestration                                 │  │
│  │  - Results Aggregation                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Mock Service Layer                                        │  │
│  │  - MockInfluxDBClient                                     │  │
│  │  - MockOpenAIClient                                       │  │
│  │  - MockMQTTClient                                         │  │
│  │  - MockDataAPIClient                                      │  │
│  │  - MockDeviceIntelligenceClient                           │  │
│  │  - MockHAConversationAPI                                  │  │
│  │  - MockHAClient                                           │  │
│  │  - MockSafetyValidator                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Workflow Simulators                                        │  │
│  │  - DailyAnalysisSimulator (3 AM workflow)                 │  │
│  │  - AskAISimulator (Ask AI flow)                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Validation Framework                                       │  │
│  │  - PromptValidator                                        │  │
│  │  - YAMLValidator                                          │  │
│  │  - GroundTruthComparator                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Metrics & Reporting                                        │  │
│  │  - PatternMetrics                                         │  │
│  │  - ModelMetrics                                           │  │
│  │  - PromptMetrics                                          │  │
│  │  - YAMLMetrics                                            │  │
│  │  - ReportGenerator                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
        ↓ Imports (read-only)
┌─────────────────────────────────────────────────────────────────┐
│  Production Code (services/ directory)                          │
│  - DailyAnalysisScheduler                                       │
│  - UnifiedPromptBuilder                                         │
│  - generate_automation_yaml()                                   │
│  - _validate_generated_yaml()                                   │
│  - Pattern detectors, synergy detectors, models                 │
└─────────────────────────────────────────────────────────────────┘
```

### Integration Points

1. **Model Training:**
   - `scripts/prepare_for_production.py` → `train_all_models()` (import from production)
   - Model loading from `models/` directory
   - Model quality validation

2. **Synthetic Data:**
   - `SyntheticHomeGenerator` (Epic AI-11, import from production)
   - Synthetic queries dataset
   - Event data from synthetic homes

3. **Real Logic (Not Mocked):**
   - Pattern detection algorithms (import from production)
   - Synergy detection (GNN model, import from production)
   - Feature analysis (import from production)
   - Prompt building (`UnifiedPromptBuilder`, import from production)
   - YAML generation (`generate_automation_yaml()`, import from production)
   - YAML validation (`_validate_generated_yaml()`, import from production)

4. **Mocked Services:**
   - All external API calls (OpenAI, HA, MQTT)
   - All database writes (InfluxDB, SQLite)
   - All network operations

### Production Isolation

**Code Separation:**
- Simulation code in `simulation/` directory (root level)
- Production code in `services/` directory
- No simulation code in production services
- Imports are one-way: simulation → production (read-only)

**Deployment Isolation:**
- Separate Docker Compose profile: `simulation`
- Excluded from default `docker-compose up` (requires `--profile simulation`)
- Separate requirements.txt
- Separate environment configuration

**Runtime Isolation:**
- Separate Python environment
- Separate data directories
- No shared state with production
- Deterministic execution (no side effects on production)

---

## Dependencies

### Prerequisites
- **Epic AI-11**: Realistic Training Data Enhancement (synthetic homes)
- **Existing**: `scripts/prepare_for_production.py` (model training infrastructure)
- **Existing**: Model loading infrastructure (production code)
- **Existing**: `UnifiedPromptBuilder` (prompt building)
- **Existing**: YAML validation pipeline

### Can Run In Parallel
- **Epic AI-18**: Simulation Data Generation & Training Collection (separate focus)
- **Epic AI-12**: Personalized Entity Resolution (different focus area)
- **Epic AI-13**: ML-Based Pattern Quality (different focus area)

---

## Risk Assessment

### Technical Risks
1. **Mock Service Complexity**: Maintaining mock services that match real service behavior
   - **Mitigation**: Use interface contracts, comprehensive tests, version pinning

2. **Model Loading**: Ensuring models load correctly in simulation context
   - **Mitigation**: Use same loading code as production, validate model initialization

3. **Performance**: Simulation may be slower than expected with 100+ homes
   - **Mitigation**: Parallel processing, async/await, memory optimization, profiling

4. **Determinism**: Ensuring reproducible results across runs
   - **Mitigation**: Seed random number generators, deterministic mock responses

5. **Production Code Coupling**: Risk of tight coupling with production code
   - **Mitigation**: Clear interface contracts, dependency injection, isolated execution

### Integration Risks
1. **Real Logic Changes**: Changes to real logic may break simulation
   - **Mitigation**: Integration tests, version pinning, interface contracts

2. **Data Format Changes**: Changes to synthetic data format may break simulation
   - **Mitigation**: Versioned data formats, migration scripts, validation

### Deployment Risks
1. **CI/CD Integration**: Simulation may slow down CI/CD pipeline
   - **Mitigation**: Optional simulation step, quick mode for CI, parallel execution

2. **Production Contamination**: Risk of simulation code affecting production
   - **Mitigation**: Separate directory, separate Docker profile, excluded from production builds

---

## Success Metrics

### Performance Metrics
- **Simulation Speed**: 100 homes in < 10 minutes
- **Memory Usage**: < 2GB for 100 homes
- **CPU Usage**: < 80% on 8-core system

### Quality Metrics
- **YAML Validation Rate**: >95% (all stages passed)
- **Entity ID Accuracy**: >98%
- **Prompt Quality Score**: >90%
- **Deployment Readiness**: >90% of suggestions ready

### Coverage Metrics
- **Test Coverage**: >90% for simulation framework
- **Home Coverage**: 100+ homes simulated
- **Query Coverage**: 50+ Ask AI queries simulated

---

## Future Enhancements

1. **Continuous Learning Integration**: Use simulation results to improve models (Epic AI-18)
2. **A/B Testing Framework**: Compare different suggestion strategies
3. **Adversarial Testing**: Test edge cases and failure scenarios
4. **Real-World Validation**: Compare simulation results with production data
5. **Performance Profiling**: Identify bottlenecks in workflow
6. **Model Comparison**: Compare different model versions in simulation

---

## References

- [Epic AI-11: Realistic Training Data Enhancement](epic-ai11-realistic-training-data-enhancement.md)
- [Epic AI-16: Simulation Framework (Design)](epic-ai16-simulation-framework.md)
- [Epic AI-18: Simulation Data Generation & Training Collection](epic-ai18-simulation-data-generation.md) (companion epic)
- [Epic AI-12: Personalized Entity Resolution](epic-ai12-personalized-entity-resolution.md) (planned)
- [Epic AI-13: ML-Based Pattern Quality](epic-ai13-ml-based-pattern-quality.md) (planned)
- [Home Assistant Best Practices PDF](../../research/Best%20Practices%20for%20Home%20Assistant%20Setup%20and%20Automations.pdf)
- [BMAD Methodology](../../.bmad-core/user-guide.md)
- **Context7 KB**: FastAPI 2025, pytest-asyncio 2025, Python 3.12+, Pydantic 2.x

---

**Last Updated:** January 2025  
**Next Review:** After Story AI17.1 completion

