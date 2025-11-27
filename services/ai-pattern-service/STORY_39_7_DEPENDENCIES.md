# Story 39.7 Dependencies and Notes

## Epic 39, Story 39.7: Pattern Learning & RLHF Migration

This document tracks dependencies and notes for the pattern learning, RLHF, and quality scoring migration.

## Completed

### Learning Modules
- ✅ `pattern_learner.py` - Q&A pattern learning (learns from successful automations)
- ✅ `pattern_rlhf.py` - Reinforcement Learning from Human Feedback
- ✅ `pattern_quality_scorer.py` - Base pattern quality scorer
- ✅ `ensemble_quality_scorer.py` - Multi-model ensemble quality scorer
- ✅ `fbvl_quality_scorer.py` - Feedback-Based Validation Learning scorer

## Dependencies to Address

### RAGClient Dependency
**Location:** `pattern_learner.py`
- **Issue:** PatternLearner uses RAGClient to store/retrieve Q&A patterns
- **Current Status:** Import wrapped in try/except, gracefully degrades if not available
- **Options:**
  1. Create shared RAG service accessible via API
  2. Use direct database access for pattern storage
  3. Make RAGClient available as shared module

### Quality Calibration/Optimization Loops
**Location:** `ensemble_quality_scorer.py`
- **Issue:** EnsembleQualityScorer depends on QualityCalibrationLoop and WeightOptimizationLoop
- **Current Status:** Simplified version that starts with base model only
- **Options:**
  1. Copy calibration/optimization loops from ai-automation-service
  2. Create simplified versions for pattern service
  3. Access via shared service/API

### Database Models
**Location:** Multiple learning modules
- **Issue:** Some modules reference models from shared database (SystemSettings, QAOutcome, ClarificationSessionDB, UserPreference)
- **Current Status:** Import paths use try/except with graceful fallback
- **Note:** Models are in shared database, so imports should work if models are accessible

## Integration Points

### Pattern Service Integration
- Learning modules can be used by:
  - Pattern detection pipeline (quality scoring)
  - Scheduler (RLHF feedback collection)
  - API routers (pattern learning from user feedback)

### Future Enhancements
- Full calibration/optimization loops
- RAG integration for pattern storage
- User preference learning (if needed in pattern service)

## Testing Notes
- Quality scorers can be tested independently
- RLHF requires user feedback data
- Pattern learner requires Q&A session data

