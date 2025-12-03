# Epic AI-18: Simulation Data Generation & Training Data Collection

**Epic ID:** AI-18  
**Title:** Simulation Data Generation & Training Data Collection  
**Status:** ✅ **COMPLETE**  
**Type:** Brownfield Enhancement (Training Infrastructure)  
**Priority:** High (Pre-Production Quality Blocker)  
**Effort:** 8 Stories (32 story points, 4-5 weeks estimated)  
**Created:** January 2025  
**Based On:** Epic AI-17 Design, Training Data Requirements, Continuous Learning Needs  
**Note:** This epic provides synthetic data generation and training data collection for simulation framework

---

## Epic Goal

Build comprehensive synthetic data generation and training data collection infrastructure for the simulation framework. Enable on-demand generation of multiple synthetic homes with varied characteristics, collect all training data from simulation runs, and automatically retrain models with collected data to continuously improve performance.

**⚠️ CRITICAL: Simulation code is deployed separately from production**
- **Location**: `simulation/` directory at project root (NOT in `services/`)
- **Isolation**: Zero dependencies on production services
- **Deployment**: Separate Docker Compose profile, excluded from production builds
- **Purpose**: Development, testing, CI/CD validation, model training data collection only

**Business Value:**
- **+∞% Training Data Availability** (Unlimited synthetic homes vs limited production data)
- **+100% Data Diversity** (Varied home types, sizes, device configurations)
- **+95% Model Accuracy Improvement** (Continuous learning from simulation data)
- **-100% Production Data Dependency** (Train models without production data)
- **+80% Training Speed** (Automated data collection and retraining)

---

## Existing System Context

### Current Training Data Infrastructure

**Location:** `services/ai-automation-service/src/training/`, `services/ai-automation-service/scripts/`

**Current State:**
1. **Synthetic Home Generation** (Epic AI-11):
   - ✅ Template-based generation (100-120 homes, 90 days events)
   - ✅ 8 home types with realistic distributions
   - ✅ Weather and carbon intensity data correlation
   - ✅ HA 2024 naming conventions
   - ✅ Areas/Floors/Labels organization
   - ⚠️ **GAP**: No integration with simulation framework
   - ⚠️ **GAP**: No on-demand generation for simulation runs

2. **Model Training**:
   - ✅ `scripts/prepare_for_production.py` - Trains all models
   - ✅ GNN Synergy Detector training (`scripts/train_gnn_synergy.py`)
   - ✅ Soft Prompt training (`scripts/train_soft_prompt.py`)
   - ⚠️ **GAP**: No training data collection from simulation
   - ⚠️ **GAP**: No automated retraining pipeline
   - ⚠️ **GAP**: No data quality validation for collected data

3. **Training Data Sources**:
   - Production database (limited availability)
   - Synthetic homes (pre-generated)
   - ⚠️ **GAP**: No simulation-generated training data
   - ⚠️ **GAP**: No training data export/import mechanisms

### Technology Stack

- **Language:** Python 3.12+ (async/await, type hints, Pydantic 2.x)
- **Frameworks:** FastAPI 0.115.x, Pydantic Settings, pytest-asyncio 0.23.x
- **Location:** `simulation/` (project root, separate from production)
- **Data Storage:** JSON, Parquet, SQLite (in-memory or simulation-specific)
- **2025 Patterns:**
  - Type hints throughout (`typing` module, `collections.abc` for generics)
  - Structured logging (`structlog` 24.x)
  - Async generators for data streaming
  - Pydantic 2.x with `BaseModel` and `Field` validators
  - Data validation with Pydantic validators
- **Context7 KB References:**
  - FastAPI 2025 patterns (async routes, data validation)
  - Python 3.12+ features (match/case, improved type hints)
  - Pydantic 2.x validation patterns
  - Data serialization patterns (JSON, Parquet)

### Integration Points

- `SyntheticHomeGenerator` - Home generation (from production, Epic AI-11)
- `SyntheticDeviceGenerator` - Device generation (from production)
- `SyntheticEventGenerator` - Event generation (from production)
- `scripts/train_gnn_synergy.py` - GNN training (from production)
- `scripts/train_soft_prompt.py` - Soft Prompt training (from production)
- Simulation framework (Epic AI-17) - Data collection points

**Note:** Simulation framework imports from production code but runs in isolated environment.

---

## Enhancement Details

### What's Being Added

1. **Data Generation Manager** (NEW - Isolated)
   - Orchestrates multi-home generation
   - Manages generation parameters
   - Tracks generation progress
   - Validates generated data
   - Caching and reusability
   - **Location**: `simulation/src/data_generation/`

2. **Enhanced Home Generator** (NEW - Isolated Wrapper)
   - Wrapper around production `SyntheticHomeGenerator`
   - On-demand generation for simulation
   - Varied home characteristics
   - Ground truth annotation
   - **Location**: `simulation/src/data_generation/`

3. **Ground Truth Generator** (NEW - Isolated)
   - Extract ground truth patterns from events
   - Generate expected synergies
   - Create validation baselines
   - **Location**: `simulation/src/data_generation/`

4. **Training Data Collector** (NEW - Isolated)
   - Collect data from all simulation collection points
   - Validate collected data quality
   - Filter low-quality data
   - Aggregate data per model type
   - Export to training formats
   - Track data lineage
   - **Location**: `simulation/src/training_data/`

5. **Model Retraining Pipeline** (NEW - Isolated)
   - Automatic retraining triggers
   - Data sufficiency checks
   - Model training orchestration
   - Model evaluation and comparison
   - Model deployment (simulation environment)
   - **Location**: `simulation/src/retraining/`

### Folder Structure (Isolated from Production)

```
simulation/
├── src/
│   ├── data_generation/      # Synthetic data generation
│   │   ├── home_generator.py
│   │   ├── ground_truth_generator.py
│   │   └── data_generation_manager.py
│   ├── training_data/        # Training data collection
│   │   ├── collector.py
│   │   ├── validators.py
│   │   ├── exporters.py
│   │   └── lineage_tracker.py
│   ├── retraining/           # Model retraining
│   │   ├── retraining_manager.py
│   │   ├── data_sufficiency.py
│   │   ├── model_evaluator.py
│   │   └── deployment.py
│   └── ... (Epic AI-17 components)
├── data/                     # Generated/cached synthetic data
│   ├── homes/                # Generated home files
│   ├── cache/                # Generation cache
│   └── ground_truth/         # Ground truth annotations
├── training_data/            # Collected training data
│   ├── gnn_synergy/
│   ├── soft_prompt/
│   ├── pattern_detection/
│   └── device_intelligence/
└── ... (Epic AI-17 structure)
```

### Success Criteria

1. **Functional:**
   - Generate 50+ homes in < 5 minutes
   - Homes have varied characteristics (types, sizes, devices)
   - Events include realistic patterns and ground truth
   - Collect training data from all simulation collection points
   - Export training data in required formats
   - Automatically retrain models when sufficient data available
   - Retrained models perform better or equal to previous

2. **Technical:**
   - All code uses 2025 patterns (Python 3.12+, async/await, type hints, Pydantic 2.x)
   - >90% test coverage for data generation and collection
   - Data quality filters applied correctly
   - Data lineage tracked accurately
   - Separated from production codebase (different directory)

3. **Quality:**
   - Data quality: >90% of collected data meets quality thresholds
   - Ground truth accuracy: >95% match with actual patterns
   - Model improvement: >5% improvement after retraining
   - Data sufficiency checks: Accurately identify when retraining possible

---

## Story Creation Requirements

**⚠️ CRITICAL: All stories created from this epic must:**
1. **Assign to Dev Agent**: Stories must be created with `@dev` agent in `.bmad-core` configuration
2. **Reference Context7 KB**: All stories must reference Context7 KB documentation for:
   - Python 3.12+ async/await patterns and generators
   - Pydantic 2.x validation and data models
   - Data serialization patterns (JSON, Parquet, CSV)
   - SQLite integration patterns
   - Model training and evaluation patterns
   - Data lineage tracking patterns

**Story Creation Process:**
- Use BMAD story creation workflow with `@dev` agent
- Include Context7 KB references in story acceptance criteria
- Use Context7 KB for technology decisions and patterns

---

## Stories

### Phase 1: Data Generation Infrastructure (Weeks 1-2)

#### Story AI18.1: Data Generation Manager
**Type:** Foundation  
**Points:** 4  
**Effort:** 8-10 hours

Create data generation manager for orchestrating multi-home generation.

**Acceptance Criteria:**
- `DataGenerationManager` class with configuration management
- Support varied home types, sizes, device configurations
- Parallel generation support
- Progress tracking and reporting
- Caching mechanism (reuse generated homes)
- Cache invalidation (when parameters change)
- Validation of generated data
- Unit tests (>90% coverage)
- All code uses 2025 patterns (type hints, async/await, Pydantic 2.x)

**Files:**
- `simulation/src/data_generation/data_generation_manager.py` (new)
- `simulation/src/data_generation/config.py` (new)
- `simulation/tests/test_data_generation_manager.py` (new)

**Context7 KB References:**
- Async task management patterns (Context7 KB mandatory)
- Caching strategies (memory, disk) (Context7 KB mandatory)
- Progress tracking patterns (Context7 KB mandatory)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Epic AI-11 (SyntheticHomeGenerator)

---

#### Story AI18.2: Enhanced Home Generator Wrapper
**Type:** Enhancement  
**Points:** 3  
**Effort:** 6-8 hours

Create wrapper around production `SyntheticHomeGenerator` for simulation use.

**Acceptance Criteria:**
- Wrapper class for `SyntheticHomeGenerator` (import from production)
- On-demand generation for simulation runs
- Support varied parameters (home types, sizes, event days)
- Integration with data generation manager
- Error handling and validation
- Unit tests (>90% coverage)

**Files:**
- `simulation/src/data_generation/home_generator.py` (new)
- `simulation/tests/test_home_generator.py` (new)

**Context7 KB References:**
- Wrapper pattern implementation (Context7 KB mandatory)
- Async generator patterns (Context7 KB mandatory)
- Error handling patterns (Context7 KB mandatory)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Story AI18.1, Epic AI-11

---

#### Story AI18.3: Ground Truth Generator
**Type:** Feature  
**Points:** 4  
**Effort:** 8-10 hours

Generate ground truth annotations for synthetic homes.

**Acceptance Criteria:**
- Extract ground truth patterns from generated events
- Generate expected synergies from device relationships
- Create validation baselines
- Annotate patterns with metadata (confidence, occurrences)
- Export ground truth in standardized format
- Integration with synthetic home generation
- Unit tests (>90% coverage)

**Files:**
- `simulation/src/data_generation/ground_truth_generator.py` (new)
- `simulation/src/data_generation/pattern_extractor.py` (new)
- `simulation/tests/test_ground_truth_generator.py` (new)

**Context7 KB References:**
- Pattern extraction algorithms (Context7 KB mandatory)
- Data annotation patterns (Context7 KB mandatory)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Story AI18.2

---

### Phase 2: Training Data Collection (Weeks 2-3)

#### Story AI18.4: Training Data Collector Core
**Type:** Foundation  
**Points:** 5  
**Effort:** 10-12 hours

Create training data collector for all simulation collection points.

**Acceptance Criteria:**
- `TrainingDataCollector` class with collection point registration
- Collect pattern detection data (patterns, ground truth, metrics)
- Collect synergy detection data (synergies, relationships, predictions)
- Collect suggestion generation data (suggestions, prompts, responses)
- Collect YAML generation data (YAML pairs, validation results, ground truth)
- Collect Ask AI conversation data (queries, responses, approvals)
- Data quality validation
- Data filtering (remove low-quality data)
- Unit tests (>90% coverage)

**Files:**
- `simulation/src/training_data/collector.py` (new)
- `simulation/src/training_data/validators.py` (new)
- `simulation/tests/test_collector.py` (new)

**Context7 KB References:**
- Data collection patterns (Context7 KB mandatory)
- Data validation patterns (Pydantic validators) (Context7 KB mandatory)
- Data filtering patterns (Context7 KB mandatory)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Epic AI-17 (Simulation Framework)

---

#### Story AI18.5: Training Data Exporters
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

Implement exporters for different model training formats.

**Acceptance Criteria:**
- Export GNN synergy data (JSON, Parquet formats)
- Export Soft Prompt data (JSON, SQLite table format)
- Export pattern detection data (JSON, Parquet formats)
- Export YAML generation data (JSON format)
- Export device intelligence data (JSON, CSV formats)
- Format validation
- Integration with training scripts (import from production)
- Unit tests (>90% coverage)

**Files:**
- `simulation/src/training_data/exporters.py` (new)
- `simulation/src/training_data/formatters.py` (new)
- `simulation/tests/test_exporters.py` (new)

**Context7 KB References:**
- Data serialization patterns (JSON, Parquet, CSV) (Context7 KB mandatory)
- SQLite integration patterns (Context7 KB mandatory)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Story AI18.4

---

#### Story AI18.6: Data Lineage Tracking
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

Implement data lineage tracking for collected training data.

**Acceptance Criteria:**
- Track data source (which cycle, which home, which test)
- Track data transformations (filters, validations)
- Track data relationships (linked patterns, synergies, suggestions)
- Store lineage metadata with collected data
- Query lineage (find all data from cycle X, find all data for model Y)
- Lineage export (for audit and debugging)
- Unit tests (>90% coverage)

**Files:**
- `simulation/src/training_data/lineage_tracker.py` (new)
- `simulation/tests/test_lineage_tracker.py` (new)

**Context7 KB References:**
- Data lineage tracking patterns (Context7 KB mandatory)
- Metadata tracking patterns (Context7 KB mandatory)
- SQLite query patterns (Context7 KB mandatory)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Story AI18.4

---

### Phase 3: Model Retraining Pipeline (Weeks 3-4)

#### Story AI18.7: Retraining Manager
**Type:** Feature  
**Points:** 5  
**Effort:** 10-12 hours

Create model retraining manager with automatic triggers.

**Acceptance Criteria:**
- `RetrainingManager` class with trigger logic
- Data sufficiency checks (per model type)
- Automatic retraining triggers (data threshold, performance degradation)
- Manual retraining triggers (CLI, configuration)
- Retraining orchestration (call production training scripts)
- Model version management
- Retraining history tracking
- Unit tests (>90% coverage)

**Files:**
- `simulation/src/retraining/retraining_manager.py` (new)
- `simulation/src/retraining/data_sufficiency.py` (new)
- `simulation/tests/test_retraining_manager.py` (new)

**Context7 KB References:**
- Task orchestration patterns (Context7 KB mandatory)
- Model version management patterns (Context7 KB mandatory)
- Data sufficiency validation patterns (Context7 KB mandatory)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Story AI18.5, Production training scripts

---

#### Story AI18.8: Model Evaluation & Deployment
**Type:** Feature  
**Points:** 5  
**Effort:** 10-12 hours

Implement model evaluation and deployment for retrained models.

**Acceptance Criteria:**
- Model evaluation on validation set
- Compare with previous model version
- Performance benchmarks
- Regression detection (performance drops)
- Model deployment (simulation environment)
- Model rollback capability
- A/B testing support (compare model versions)
- Unit tests (>90% coverage)

**Files:**
- `simulation/src/retraining/model_evaluator.py` (new)
- `simulation/src/retraining/deployment.py` (new)
- `simulation/tests/test_model_evaluation.py` (new)

**Context7 KB References:**
- Model evaluation metrics (accuracy, precision, recall, F1) (Context7 KB mandatory)
- A/B testing patterns (Context7 KB mandatory)

**Story Creation:**
- Must create story with `@dev` agent in `.bmad-core`
- Story must reference Context7 KB for all technology decisions

**Dependencies:** Story AI18.7

---

## Technical Architecture

### Data Generation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              DATA GENERATION PIPELINE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DataGenerationManager                                          │
│    ↓                                                            │
│  HomeGenerator (wrapper around production)                      │
│    ↓                                                            │
│  SyntheticHomeGenerator (from production)                       │
│    ↓                                                            │
│  GroundTruthGenerator                                           │
│    ↓                                                            │
│  Generated Homes + Ground Truth                                 │
│    ↓                                                            │
│  Cache (reuse for multiple simulation runs)                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Training Data Collection Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              TRAINING DATA COLLECTION PIPELINE                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Simulation Run (Epic AI-17)                                    │
│    ↓                                                            │
│  Collection Points:                                             │
│    - Pattern Detection → Pattern Data                           │
│    - Synergy Detection → Synergy Data                           │
│    - Suggestion Generation → Suggestion Data                    │
│    - YAML Generation → YAML Pair Data                           │
│    - Ask AI Flow → Conversation Data                            │
│    ↓                                                            │
│  TrainingDataCollector                                          │
│    ↓                                                            │
│  Data Validators (quality filters)                              │
│    ↓                                                            │
│  Data Exporters (format conversion)                             │
│    ↓                                                            │
│  Training Data Storage (JSON, Parquet, SQLite)                  │
│    ↓                                                            │
│  Lineage Tracker (metadata tracking)                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Model Retraining Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              MODEL RETRAINING PIPELINE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  RetrainingManager                                              │
│    ↓                                                            │
│  Data Sufficiency Check                                         │
│    ↓ (if sufficient)                                            │
│  Load Training Data                                             │
│    ↓                                                            │
│  Call Production Training Scripts                               │
│    - train_gnn_synergy.py                                       │
│    - train_soft_prompt.py                                       │
│    - train_pattern_quality.py                                   │
│    ↓                                                            │
│  Model Evaluation                                               │
│    ↓                                                            │
│  Compare with Previous Model                                    │
│    ↓                                                            │
│  Deploy if Improved (simulation environment)                    │
│    ↓                                                            │
│  Track Retraining History                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Storage Structure

```
simulation/training_data/
├── cycle_1/
│   ├── gnn_synergy/
│   │   ├── synergies.json
│   │   ├── entities.json
│   │   └── metadata.json
│   ├── soft_prompt/
│   │   ├── queries.json
│   │   └── metadata.json
│   ├── pattern_detection/
│   │   ├── patterns.json
│   │   └── ground_truth.json
│   └── yaml_generation/
│       ├── yaml_pairs.json
│       └── validation_results.json
├── cycle_2/
│   └── ...
└── aggregated/
    └── (combined data across cycles)
```

---

## Dependencies

### Prerequisites
- **Epic AI-17**: Simulation Framework Core (data collection points)
- **Epic AI-11**: Realistic Training Data Enhancement (SyntheticHomeGenerator)
- **Existing**: Production training scripts (`train_gnn_synergy.py`, `train_soft_prompt.py`)

### Can Run In Parallel
- **Epic AI-12**: Personalized Entity Resolution (different focus area)
- **Epic AI-13**: ML-Based Pattern Quality (different focus area)

---

## Risk Assessment

### Technical Risks
1. **Data Quality**: Collected training data may not match production quality
   - **Mitigation**: Quality filters, validation thresholds, manual review process

2. **Model Overfitting**: Models may overfit to simulation data
   - **Mitigation**: Combine with production data, cross-validation, regular evaluation

3. **Generation Performance**: Generating many homes may be slow
   - **Mitigation**: Parallel generation, caching, optimization

4. **Data Storage**: Large volumes of training data may consume disk space
   - **Mitigation**: Data retention policies, compression, archival

### Integration Risks
1. **Training Script Changes**: Changes to production training scripts may break integration
   - **Mitigation**: Interface contracts, version pinning, integration tests

2. **Data Format Changes**: Changes to data formats may break collection
   - **Mitigation**: Versioned formats, migration scripts, validation

---

## Success Metrics

### Data Generation Metrics
- **Generation Speed**: 50+ homes in < 5 minutes
- **Home Diversity**: 8+ home types, varied sizes
- **Ground Truth Accuracy**: >95% match with actual patterns

### Data Collection Metrics
- **Collection Coverage**: 100% of collection points covered
- **Data Quality**: >90% of collected data meets quality thresholds
- **Data Volume**: Sufficient data for model retraining (varies by model)

### Model Retraining Metrics
- **Retraining Frequency**: Automatic retraining when thresholds met
- **Model Improvement**: >5% improvement after retraining
- **Regression Rate**: <5% performance degradation after retraining

---

## Future Enhancements

1. **Active Learning**: Prioritize data collection for model improvement
2. **Data Augmentation**: Enhance collected data with synthetic variations
3. **Federated Learning**: Combine training data from multiple simulation runs
4. **Model Versioning**: Track model versions and performance over time
5. **Data Visualization**: Visualize training data and model performance

---

## References

- [Epic AI-17: Simulation Framework Core](epic-ai17-simulation-framework-core.md) (companion epic)
- [Epic AI-11: Realistic Training Data Enhancement](epic-ai11-realistic-training-data-enhancement.md)
- [Epic AI-16: Simulation Framework (Design)](epic-ai16-simulation-framework.md)
- [BMAD Methodology](../../.bmad-core/user-guide.md)
- **Context7 KB**: FastAPI 2025, Python 3.12+, Pydantic 2.x, Data serialization patterns

---

**Last Updated:** January 2025  
**Next Review:** After Story AI18.1 completion

