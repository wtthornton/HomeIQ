# Story 39.5 Dependencies and Notes

## Epic 39, Story 39.5: Pattern Service Foundation

This document tracks dependencies and notes for the pattern service extraction.

## Completed

### Service Foundation
- ✅ Service structure created (`services/ai-pattern-service/`)
- ✅ FastAPI app (`src/main.py`)
- ✅ Configuration (`src/config.py`)
- ✅ Database connection pooling (`src/database/__init__.py`)
- ✅ Health router (`src/api/health_router.py`)
- ✅ Dockerfile and requirements.txt
- ✅ Docker Compose configuration

### Pattern Analyzer
- ✅ `time_of_day.py` - Time-of-day pattern detection using KMeans
- ✅ `co_occurrence.py` - Co-occurrence pattern detection
- ✅ `confidence_calibrator.py` - Confidence score calibration
- ✅ `pattern_cross_validator.py` - Pattern cross-validation
- ✅ `pattern_deduplicator.py` - Pattern deduplication

### Synergy Detection
- ✅ `synergy_detector.py` - Main synergy detection logic

## Dependencies to Address in Later Stories

### Story 39.6: Daily Scheduler Migration
- Scheduler code migration
- MQTT client configuration
- Scheduled job verification

### Story 39.7: Pattern Learning & RLHF Migration
- Pattern learning code
- RLHF (Reinforcement Learning from Human Feedback)
- Quality scoring

### Story 39.8: Pattern Service Testing & Validation
- Comprehensive testing
- Integration tests
- Scheduler validation

### Additional Dependencies

#### DataAPIClient
- **Status**: Needs to be created or imported from shared
- **Location**: Used in routers for fetching events/devices/entities
- **Action**: Create `src/clients/data_api_client.py` or import from shared

#### Database Models
- **Status**: Models exist in shared database
- **Location**: `Pattern`, `SynergyOpportunity`, `DiscoveredSynergy`, etc.
- **Action**: Import from shared models or create local models that reference shared tables

#### PatternHistoryValidator
- **Status**: Integration module
- **Location**: `src/integration/pattern_history_validator.py`
- **Action**: Copy from ai-automation-service in Story 39.7

#### AutomationParser
- **Status**: Client module
- **Location**: `src/clients/automation_parser.py`
- **Action**: Copy from ai-automation-service or create shared client

#### SynergyCache
- **Status**: Optional performance enhancement
- **Location**: `src/synergy_detection/synergy_cache.py`
- **Action**: Copy from ai-automation-service in later story

#### DevicePairAnalyzer
- **Status**: Advanced scoring (optional)
- **Location**: `src/synergy_detection/device_pair_analyzer.py`
- **Action**: Copy from ai-automation-service in later story

#### Routers
- **Status**: Need to be created with dependency stubs
- **Files**:
  - `pattern_router.py` - Pattern detection endpoints
  - `synergy_router.py` - Synergy detection endpoints
  - `community_pattern_router.py` - Community pattern endpoints
- **Action**: Create simplified routers in Story 39.6 or 39.7

#### Auth Dependencies
- **Status**: Auth middleware
- **Location**: `src/api/dependencies/auth.py`
- **Action**: Copy from ai-automation-service or create shared auth

## Import Updates Needed

### Pattern Analyzer Files
- ✅ All imports updated to use relative imports (`..config`, etc.)

### Synergy Detector
- ✅ Updated to use `..config` for settings
- ⚠️ Optional imports (SynergyCache, DevicePairAnalyzer) handled gracefully
- ⚠️ AutomationParser import handled with try/except

## Next Steps

1. **Story 39.6**: Migrate scheduler and create router stubs
2. **Story 39.7**: Migrate pattern learning, RLHF, and complete routers
3. **Story 39.8**: Comprehensive testing and validation

