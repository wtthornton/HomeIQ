# Home Type Categorization System

**Last Updated:** November 25, 2025  
**Status:** ✅ Production Ready  
**Epic:** Home Type Categorization & Event Category Mapping

---

## Overview

The Home Type Categorization System uses **machine learning classification** to categorize homes based on device composition, event patterns, spatial layout, and behavior patterns. This enables context-aware automation suggestions and improved pattern detection.

## Architecture

### System Components

```
Home Type Categorization System
├── Synthetic Data Generation
│   ├── Home Generator (LLM-based)
│   ├── Area Generator
│   ├── Device Generator
│   └── Event Generator
├── Training Data Pipeline
│   ├── Home Profile Extractor
│   ├── Feature Engineering
│   ├── Label Generator
│   └── Data Augmentation
├── Model Training
│   ├── RandomForest Classifier
│   ├── Model Persistence
│   └── Model Evaluation
├── Production System
│   ├── Home Type Profiler
│   ├── Production Classifier
│   └── Incremental Updater
└── Integration Points
    ├── Suggestion Ranking
    ├── Pattern Detection
    └── Event Categorization
```

## Implementation

### Model Architecture

- **Default Algorithm:** scikit-learn RandomForestClassifier
- **Alternative Options** (2025 improvements):
  - **LightGBM**: 2-5x faster training, similar accuracy
  - **TabPFN v2.5**: Instant training (<1s), 90-98% accuracy
- **Configuration:** Via `ML_FAILURE_MODEL` environment variable
- **Trees:** 100 (RandomForest)
- **Max Depth:** 15 (RandomForest)
- **Features:** 15-20 tabular features
- **Classes:** 5-10 home type categories

**Home Types:**
- `smart_home_enthusiast` - High device count, extensive automation
- `basic_automation` - Standard automation with common devices
- `security_focused` - Security devices and monitoring emphasis
- `energy_efficient` - Climate and energy monitoring focus
- `minimal` - Few devices, basic functionality

### Training Process

1. **Synthetic Data Generation** (100-120 homes)
   - LLM-based home generation
   - Realistic device composition
   - Event pattern simulation

2. **Feature Extraction**
   - Device composition metrics
   - Event pattern analysis
   - Spatial layout characteristics
   - Behavior pattern indicators

3. **Model Training**
   - Trained locally before deployment
   - Model persisted as `.pkl` file
   - Included in Docker image

### Production System

**Profiling:**
- Extracts current home characteristics
- Device composition analysis
- Event pattern detection
- Spatial layout mapping
- Behavior pattern identification

**Classification:**
- Uses pre-trained RandomForest model
- Returns home type with confidence score
- Category distribution per home type
- Model metadata available via API

## API Endpoints

**Base URL:** `http://localhost:8018/api/home-type`

### GET /api/home-type/profile
Get current home type profile with comprehensive characteristics.

**Query Parameters:**
- `home_id` (optional, default: "default")

**Returns:**
- Device composition breakdown
- Event patterns (frequency, peak hours)
- Spatial layout (areas, rooms)
- Behavior patterns (automation count, interventions)

### GET /api/home-type/classify
Classify home type using pre-trained model.

**Query Parameters:**
- `home_id` (optional, default: "default")

**Returns:**
- `home_type`: Classified category
- `confidence`: Confidence score (0-1)
- `method`: Classification method
- `model_version`: Model version used
- `categories`: Category distribution

### GET /api/home-type/model-info
Get model metadata and training information.

**Returns:**
- Model loading status
- Training date and version
- Available home type classes
- Feature names used
- Training sample count

## Integration

### Suggestion Ranking Enhancement

**Implementation:**
- Home type boost applied to suggestions (10% weight)
- Category preferences influence ranking
- Home type context passed to suggestion router

**Files:**
- `services/ai-automation-service/src/home_type/integration_helpers.py`
- `services/ai-automation-service/src/database/crud.py`
- `services/ai-automation-service/src/api/suggestion_router.py`

### Pattern Detection Enhancement

**Implementation:**
- Threshold adjustment based on home type
- Pattern confidence scoring with home type context
- Category-aware pattern filtering

### Event Categorization

**Categories:**
- `security` - Security-related events
- `climate` - Climate control events
- `lighting` - Lighting events
- `appliance` - Appliance events
- `monitoring` - Monitoring events
- `general` - Other events

**Mapping:**
- Events automatically categorized based on home type preferences
- Category distribution influences suggestion relevance

## Performance Characteristics

- **Classification Latency:** <100ms (with caching)
- **Cache TTL:** 24 hours
- **Model Load Time:** <1 second at startup
- **Memory Footprint:** ~5MB (model + cache)
- **Expected Impact:** +15-20% suggestion acceptance rate

## Caching Strategy

**HomeTypeClient:**
- In-memory caching with 24-hour TTL
- Single-home optimization (always 'default')
- Graceful fallback to default home type
- Connection pooling (httpx)
- Retry logic with exponential backoff

## Error Handling

- **Model Not Loaded:** Returns default home type
- **Profiling Failure:** Falls back to cached result
- **API Errors:** Graceful degradation with default values
- **Classification Errors:** Returns 'basic_automation' as fallback

## Files and Locations

**Core Components:**
- `services/ai-automation-service/src/home_type/production_profiler.py`
- `services/ai-automation-service/src/home_type/production_classifier.py`
- `services/ai-automation-service/src/home_type/event_categorizer.py`
- `services/ai-automation-service/src/api/home_type_router.py`
- `services/ai-automation-service/src/clients/home_type_client.py`

**Training Components:**
- `services/ai-automation-service/src/training/synthetic_home_generator.py`
- `services/ai-automation-service/src/home_type/home_type_profiler.py`
- `services/ai-automation-service/src/home_type/feature_extractor.py`
- `services/ai-automation-service/scripts/train_home_type_classifier.py`

**Integration:**
- `services/ai-automation-service/src/home_type/integration_helpers.py`
- `services/ai-automation-service/src/home_type/suggestion_filter.py`

**Model Storage:**
- `services/ai-automation-service/models/home_type_classifier.pkl`

## Future Enhancements

- Incremental profile updates
- Multi-home support (if needed)
- Real-time category adjustments
- Enhanced feature engineering
- Model retraining pipeline

---

**Reference:** See [Home Type Categorization Implementation Complete](../implementation/HOME_TYPE_CATEGORIZATION_IMPLEMENTATION_COMPLETE.md) for detailed implementation notes.

