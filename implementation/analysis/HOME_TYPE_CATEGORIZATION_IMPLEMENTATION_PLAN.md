# Home Type Categorization System - Implementation Plan

**Date:** November 2025  
**Status:** Planning - Ready for Implementation  
**Epic:** Home Type Categorization & Event Category Mapping  
**Last Updated:** November 2025 (Cloud features removed, local training focus)

---

## Executive Summary

### Model Baseline Selection (2025 Research)

**Primary Model: scikit-learn RandomForestClassifier**
- ✅ **Best for tabular data** - Home type classification uses structured features (device counts, ratios, event frequencies)
- ✅ **Already proven** - Successfully used in `device-intelligence-service` for similar tasks
- ✅ **Lightweight** - <5MB model, <10ms inference, <100MB memory (perfect for NUC)
- ✅ **No pre-training** - Trains directly on synthetic data (no HuggingFace model needed)
- ✅ **Docker-ready** - Runs in existing ML service container
- ✅ **Interpretable** - Feature importance, decision trees for debugging

**Why NOT HuggingFace Transformers:**
- ❌ Transformers designed for text/NLP, not tabular data
- ❌ Requires pre-training or fine-tuning on large text datasets
- ❌ Heavier resource requirements (100MB+ models, slower inference)
- ❌ Overkill for structured feature classification

**Optional Enhancement: HuggingFace Embeddings**
- Use `all-MiniLM-L6-v2` (already in OpenVINO service) for feature enrichment
- Convert home profile to text description → get embeddings → add as features
- Provides semantic understanding without heavy transformer training
- **Note:** Optional enhancement, not required for baseline

### Training Strategy

**Local Training (Before Release):**
1. Train model on development machine using 100-120 synthetic homes
2. Save trained model to `models/home_type_classifier.pkl`
3. Include pre-trained model in Docker image
4. **No training in production** - Model loaded at container startup for inference only

**Docker Deployment:**
- Model included in Docker image (pre-trained)
- Loads at service startup (<1 second)
- Runs in existing `ai-automation-service` container
- No cloud dependencies, single deployment only

---

This plan implements a **dynamic home type categorization system** that:
1. Profiles single homes using lightweight, statistical methods (NUC-optimized)
2. Uses **fine-tuned ML models** trained locally on synthetic data (100-120 homes) **before release**
3. Maps events to categories based on home type context
4. Runs as a **local service in Docker container** (single deployment, no cloud)
5. Integrates with existing spatial validation and quality framework

**Key Decision:** Skip rule-based approach, use fine-tuned model only (simpler, better accuracy)

**Training Data:** Generate 100-120 synthetic homes using LLM-based generation

**Model Baseline:** scikit-learn RandomForestClassifier (best for tabular data, already proven in system)
**Optional Enhancement:** HuggingFace embeddings (all-MiniLM-L6-v2) for text-based feature enrichment

---

## 1. Architecture Overview

### 1.1 System Components

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
│   ├── Fine-Tuned Classifier (RandomForest)
│   ├── Model Persistence
│   └── Model Evaluation
├── Production System
│   ├── Home Type Profiler
│   ├── Event Categorizer
│   └── Incremental Updater
└── Integration Points
    ├── Spatial Validation
    ├── Quality Framework
    └── Suggestion Enhancement
```

### 1.2 Data Flow

```
Synthetic Homes (100-120)
    ↓
Training Data Generation
    ↓
Model Training (Fine-Tuned)
    ↓
Production: Single Home Profiling
    ↓
Event Category Mapping
    ↓
Suggestion Enhancement
```

### 1.3 Key Design Principles

1. **Single-Home Focus**: Optimized for single-home NUC deployment
2. **Local Training**: Train model locally before release (not in production)
3. **Docker Deployment**: Runs as local service in Docker container
4. **Lightweight**: Statistical features, optional HuggingFace embeddings for enrichment
5. **Batch Processing**: Daily at 3 AM (non-blocking)
6. **Incremental Learning**: Leverage existing infrastructure
7. **Resource Efficient**: <100MB memory, <5 min processing
8. **No Cloud Dependencies**: Single deployment, all processing local

---

## 2. Synthetic Data Generation

### 2.1 Overview

Generate 100-120 synthetic homes using LLM-based generation following the home-assistant-datasets pattern.

### 2.2 Generation Pipeline

#### Phase 1: Home Descriptions
```python
# services/ai-automation-service/src/training/synthetic_home_generator.py

class SyntheticHomeGenerator:
    """
    Generate synthetic homes using LLM (OpenAI/Gemini).
    
    Follows home-assistant-datasets generation pattern.
    """
    
    async def generate_homes(
        self,
        target_count: int = 100,
        home_types: list[str] = None
    ) -> list[dict]:
        """
        Generate synthetic homes with diversity.
        
        Distribution:
        - Single-family house: 30 homes
        - Apartment: 20 homes
        - Condo: 15 homes
        - Townhouse: 10 homes
        - Cottage: 10 homes
        - Studio: 5 homes
        - Multi-story: 5 homes
        - Ranch house: 5 homes
        """
```

#### Phase 2: Areas & Devices
```python
class SyntheticAreaDeviceGenerator:
    """
    Generate areas and devices for synthetic homes.
    
    Pipeline:
    1. Generate areas (rooms/spaces) from home description
    2. Generate devices for each area
    3. Assign device types based on area context
    """
```

#### Phase 3: Event Generation
```python
class SyntheticEventGenerator:
    """
    Generate synthetic events for training.
    
    Uses device-type-specific frequencies (from production analysis):
    - Lights: 11 events/day
    - Binary sensors: 36 events/day
    - Sensors: 26 events/day
    - etc.
    """
```

### 2.3 Home Distribution Strategy

#### Home Type Distribution (100 homes)
| Home Type | Count | Percentage | Purpose |
|-----------|-------|------------|---------|
| Single-family house | 30 | 30% | Most common type |
| Apartment | 20 | 20% | Urban, space-constrained |
| Condo | 15 | 15% | Medium density |
| Townhouse | 10 | 10% | Suburban |
| Cottage | 10 | 10% | Rural, smaller |
| Studio | 5 | 5% | Minimal space |
| Multi-story | 5 | 5% | Large, complex |
| Ranch house | 5 | 5% | Single-level |

#### Size Distribution
| Size | Device Count | Count | Percentage |
|------|--------------|-------|------------|
| Small | 10-20 devices | 30 | 30% |
| Medium | 20-40 devices | 40 | 40% |
| Large | 40-60 devices | 20 | 20% |
| Extra-large | 60+ devices | 10 | 10% |

#### Device Mix Distribution
| Focus | Security Ratio | Climate Ratio | Count | Percentage |
|-------|----------------|---------------|-------|------------|
| Security-focused | >0.2 | <0.1 | 20 | 20% |
| Climate-controlled | <0.1 | >0.15 | 20 | 20% |
| Balanced | 0.1-0.2 | 0.1-0.15 | 40 | 40% |
| Smart home | >5 integrations | Any | 20 | 20% |

### 2.4 Generation Cost & Time Estimates

**Cost:**
- LLM API: $0.10-0.50 per home
- 100 homes: $10-50
- 120 homes: $12-60

**Time:**
- Home generation: ~1-2 min per home
- Areas/devices: ~30 sec per home
- Total: 2-4 hours for 100 homes (batch)

**Storage:**
- Home descriptions: ~1KB per home
- Complete homes (with devices): ~10KB per home
- 100 homes: ~1MB total

---

## 3. Training Data Pipeline

### 3.1 Home Profile Extraction

```python
# services/ai-automation-service/src/home_type/home_type_profiler.py

class HomeTypeProfiler:
    """
    Extract home profile features from synthetic homes.
    
    Features:
    - Device composition (types, categories, counts, ratios)
    - Event patterns (frequencies, distributions, peak hours)
    - Spatial layout (areas, indoor/outdoor, distribution)
    - Behavior patterns (aggregated statistics)
    """
    
    async def profile_home(
        self,
        home_id: str,
        devices: list[dict],
        events: list[dict],
        patterns: list[dict] = None
    ) -> dict:
        """
        Create comprehensive home profile.
        
        Returns:
            {
                'device_composition': {...},
                'event_patterns': {...},
                'spatial_layout': {...},
                'behavior_patterns': {...}
            }
        """
```

### 3.2 Feature Engineering

```python
class HomeTypeFeatureExtractor:
    """
    Extract ML-ready features from home profile.
    
    Features (15-20 total):
    - Device counts (by type, category)
    - Device ratios (security, climate, lighting)
    - Event frequencies (total, per day, peak hours)
    - Spatial metrics (area count, indoor/outdoor ratio)
    - Behavior metrics (pattern counts, confidence)
    """
    
    def extract(self, profile: dict) -> np.ndarray:
        """Extract feature vector for ML model"""
```

### 3.3 Label Generation

```python
class HomeTypeLabelGenerator:
    """
    Generate home type labels from synthetic home metadata.
    
    Strategy:
    1. Use home metadata (type field) when available
    2. Use heuristics from profile features (fallback)
    3. Map to standard home types:
       - security_focused
       - climate_controlled
       - high_activity
       - smart_home
       - standard_home
       - apartment
       - etc.
    """
    
    def label_home_type(
        self,
        home_metadata: dict,
        profile: dict
    ) -> str:
        """Generate home type label"""
```

### 3.4 Data Augmentation

```python
class TrainingDataAugmenter:
    """
    Create variations of homes for training data augmentation.
    
    Variations (3-5 per home):
    1. Device count variations (±20%)
    2. Event frequency variations (±30%)
    3. Device type distribution variations
    4. Spatial layout variations
    """
    
    def create_variations(
        self,
        base_profile: dict,
        count: int = 3
    ) -> list[dict]:
        """Create augmented training samples"""
```

### 3.5 Training Dataset Structure

```python
# Final training dataset
{
    'features': [
        [device_count, security_ratio, climate_ratio, ...],  # Home 1
        [device_count, security_ratio, climate_ratio, ...],  # Home 2
        ...
    ],
    'labels': [
        'security_focused',  # Home 1
        'standard_home',    # Home 2
        ...
    ],
    'metadata': {
        'total_samples': 400,  # 100 homes × 4 variations
        'home_types': ['security_focused', 'standard_home', ...],
        'generation_date': '2025-11-XX',
        'augmentation_factor': 4
    }
}
```

---

## 4. Model Training

### 4.1 Model Architecture & Baseline Selection

**2025 Best Practice Analysis:**

For tabular data classification (home type from device/event features), **scikit-learn RandomForestClassifier** is the optimal choice:

**Why RandomForest (not HuggingFace transformers):**
- ✅ **Designed for tabular data** - Transformers are for text/NLP, not structured features
- ✅ **Already proven in system** - Used successfully in `device-intelligence-service`
- ✅ **Lightweight** - <5MB model size, <10ms inference, <100MB memory
- ✅ **No pre-training needed** - Trains directly on synthetic data
- ✅ **Interpretable** - Feature importance, decision trees
- ✅ **Docker-ready** - Runs in existing ML service container

**Optional Enhancement: HuggingFace Embeddings**
- Use `all-MiniLM-L6-v2` (already in OpenVINO service) to enrich features
- Convert home profile to text description → get embeddings → add as features
- Provides semantic understanding without heavy transformer training

```python
# services/ai-automation-service/src/home_type/home_type_classifier.py

class FineTunedHomeTypeClassifier:
    """
    Fine-tuned RandomForest classifier for home type classification.
    
    Baseline Model: scikit-learn RandomForestClassifier
    - Best for tabular data classification (2025 best practice)
    - Already proven in device-intelligence-service
    - Lightweight, fast, interpretable
    
    Optional: HuggingFace embeddings for feature enrichment
    - all-MiniLM-L6-v2 (already in OpenVINO service)
    - Convert home profile to text → embeddings → additional features
    
    Model Specs:
    - Algorithm: RandomForestClassifier (scikit-learn)
    - Trees: 100 (lightweight for NUC)
    - Max depth: 15
    - Min samples split: 5
    - Features: 15-20 (tabular) + 0-384 (optional embeddings)
    - Classes: 5-10 home types
    """
    
    def __init__(self, model_path: str | None = None, use_embeddings: bool = False):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1  # Use all CPU cores
        )
        self.scaler = StandardScaler()
        self.feature_extractor = HomeTypeFeatureExtractor()
        self.use_embeddings = use_embeddings
        self.embedding_model = None  # Optional: all-MiniLM-L6-v2
        self.is_trained = False
        
        if use_embeddings:
            # Optional: Load HuggingFace embeddings model
            # Uses existing OpenVINO service or loads locally
            self._load_embedding_model()
```

### 4.2 Training Process (Local, Before Release)

**Training Strategy:**
- **Train locally** on development machine (not in production)
- **Before release**: Model is pre-trained and included in Docker image
- **Training time**: ~5-10 minutes for 400-600 samples
- **Model persistence**: Save to `models/home_type_classifier.pkl` (included in Docker)

```python
async def train_from_synthetic_data(
    self,
    dataset_loader: HomeAssistantDatasetLoader,
    synthetic_homes: list[dict]
):
    """
    Train model on synthetic homes (LOCAL TRAINING, BEFORE RELEASE).
    
    Process:
    1. Load synthetic homes
    2. Generate events for each home (7 days)
    3. Extract home profiles
    4. Extract features (tabular + optional embeddings)
    5. Generate labels
    6. Augment data (3-5 variations)
    7. Train model (scikit-learn RandomForest)
    8. Evaluate (cross-validation)
    9. Save model to models/home_type_classifier.pkl
    
    Note: This runs ONCE before release, model is included in Docker image.
    """
    # Training happens locally, model saved to disk
    # Docker image includes pre-trained model
```

### 4.3 Model Evaluation

```python
def evaluate_model(
    self,
    X_test: np.ndarray,
    y_test: list[str]
) -> dict:
    """
    Evaluate model performance.
    
    Metrics:
    - Accuracy
    - Precision (per class)
    - Recall (per class)
    - F1 Score (per class)
    - Confusion matrix
    """
```

### 4.4 Model Persistence

```python
def save(self, path: str):
    """Save trained model and scaler"""
    joblib.dump({
        'model': self.model,
        'scaler': self.scaler,
        'feature_extractor': self.feature_extractor,
        'is_trained': self.is_trained,
        'model_version': '1.0',
        'training_date': datetime.utcnow().isoformat()
    }, path)

def load(self, path: str):
    """Load pre-trained model"""
```

---

## 5. Production System

### 5.1 Home Type Profiling

```python
class ProductionHomeTypeProfiler:
    """
    Profile single home for production use.
    
    Lightweight, NUC-optimized:
    - Statistical features only (no heavy embeddings)
    - Batch processing (daily at 3 AM)
    - Incremental updates
    """
    
    async def profile_current_home(
        self,
        home_id: str = 'default'
    ) -> dict:
        """
        Profile current home from production data.
        
        Sources:
        - Devices (from SQLite)
        - Events (from InfluxDB, last 30 days)
        - Patterns (from pattern detection)
        """
```

### 5.2 Home Type Classification

```python
class ProductionHomeTypeClassifier:
    """
    Classify home type using pre-trained model.
    
    Loads model at startup, uses for inference.
    """
    
    def __init__(self, model_path: str):
        self.classifier = FineTunedHomeTypeClassifier()
        self.classifier.load(model_path)
    
    async def classify_home(
        self,
        home_profile: dict
    ) -> dict:
        """
        Classify home type.
        
        Returns:
            {
                'home_type': str,
                'confidence': float,
                'method': 'ml_model',
                'features_used': list[str]
            }
        """
```

### 5.3 Event Category Mapping

```python
class EventCategoryMapper:
    """
    Map events to categories based on home type.
    
    Categories:
    - security
    - climate
    - lighting
    - appliance
    - monitoring
    - general
    """
    
    def categorize_events(
        self,
        events: list[dict],
        home_type: str
    ) -> dict[str, str]:
        """
        Categorize events using home type context.
        
        Returns:
            Dict mapping event_id to category
        """
```

### 5.4 Incremental Updates

```python
class IncrementalHomeTypeUpdater:
    """
    Update home type profile incrementally.
    
    Leverages existing incremental learning infrastructure.
    """
    
    async def incremental_update(
        self,
        home_id: str,
        new_devices: list[dict],
        new_events: list[dict],
        new_patterns: list[dict],
        last_update_time: datetime
    ) -> dict:
        """
        Update home profile incrementally (not full reprocessing).
        
        Uses existing incremental learning patterns.
        """
```

---

## 6. Docker Deployment & Local Training

### 6.1 Training Workflow (Before Release)

**Training Process:**
1. **Local Development Machine:**
   - Generate 100-120 synthetic homes
   - Train model on synthetic data
   - Evaluate model performance
   - Save model to `models/home_type_classifier.pkl`

2. **Docker Build:**
   - Include pre-trained model in Docker image
   - Model loaded at container startup
   - No training in production

3. **Production Deployment:**
   - Container starts with pre-trained model
   - Model used for inference only
   - No cloud dependencies

```python
# Dockerfile includes pre-trained model
COPY models/home_type_classifier.pkl /app/models/

# Service loads model at startup
classifier = FineTunedHomeTypeClassifier()
classifier.load('/app/models/home_type_classifier.pkl')
```

### 6.2 Docker Container Integration

**Service:** `ai-automation-service` (existing container)
- Model loaded at startup
- Inference via existing API
- No additional containers needed

**Resource Allocation:**
- Memory: +30MB for model (total <100MB)
- CPU: <10ms per inference
- Storage: +5MB for model file

### 6.3 Model Versioning

**Model Storage:**
- `models/home_type_classifier.pkl` - Trained model
- `models/home_type_classifier_metadata.json` - Model version, training date, metrics

**Version Management:**
- Model version in metadata
- Training date tracked
- Performance metrics stored
- Rollback capability (keep previous model versions)

---

## 7. Integration Points

### 7.1 Spatial Validation Integration

**Integration Point:** Use spatial patterns as home type features

```python
# Extract spatial patterns from spatial validator
spatial_features = await spatial_validator.extract_spatial_patterns(devices)

# Include in home profile
home_profile['spatial_layout'] = spatial_features
```

### 7.2 Quality Framework Integration

**Integration Point:** Use quality scores to weight home type features

```python
# Weight device/event features by quality scores
weighted_features = quality_framework.weight_features(
    features,
    quality_scores
)
```

### 7.3 Suggestion Enhancement

**Integration Point:** Filter suggestions by home type

```python
# Filter suggestions by home type
filtered_suggestions = filter_by_home_type(
    suggestions,
    home_type
)

# Prioritize patterns common to home type
prioritized = prioritize_by_home_type(
    filtered_suggestions,
    home_type
)
```

---

## 8. Implementation Phases

### Phase 1: Synthetic Data Generation (Week 1-2)

**Goal:** Generate 100-120 synthetic homes for training

**Tasks:**
1. ✅ Create `SyntheticHomeGenerator` class
2. ✅ Implement LLM-based home generation (OpenAI/Gemini)
3. ✅ Create area generation pipeline
4. ✅ Create device generation pipeline
5. ✅ Generate 100-120 homes with diversity
6. ✅ Validate home quality and diversity
7. ✅ Save synthetic homes to dataset directory

**Deliverables:**
- `services/ai-automation-service/src/training/synthetic_home_generator.py`
- `services/ai-automation-service/src/training/synthetic_area_generator.py`
- `services/ai-automation-service/src/training/synthetic_device_generator.py`
- 100-120 synthetic homes in `tests/datasets/synthetic_homes/`

**Success Criteria:**
- 100+ homes generated
- All home types represented
- All size categories represented
- Device mix diversity achieved

---

### Phase 2: Training Data Pipeline (Week 2-3)

**Goal:** Create training dataset from synthetic homes

**Tasks:**
1. ✅ Create `HomeTypeProfiler` class
2. ✅ Implement feature extraction
3. ✅ Create `HomeTypeLabelGenerator`
4. ✅ Implement data augmentation
5. ✅ Generate training dataset (400-600 samples)
6. ✅ Validate training data quality
7. ✅ Save training dataset

**Deliverables:**
- `services/ai-automation-service/src/home_type/home_type_profiler.py`
- `services/ai-automation-service/src/home_type/feature_extractor.py`
- `services/ai-automation-service/src/home_type/label_generator.py`
- `services/ai-automation-service/src/home_type/data_augmenter.py`
- Training dataset JSON file

**Success Criteria:**
- 400+ training samples
- 50+ samples per home type
- Feature diversity validated
- Labels accurate

---

### Phase 3: Model Training (Week 3)

**Goal:** Train fine-tuned home type classifier

**Tasks:**
1. ✅ Create `FineTunedHomeTypeClassifier` class
2. ✅ Implement training pipeline
3. ✅ Train model on synthetic data
4. ✅ Evaluate model performance
5. ✅ Save trained model
6. ✅ Create model evaluation report

**Deliverables:**
- `services/ai-automation-service/src/home_type/home_type_classifier.py`
- Trained model: `models/home_type_classifier.pkl`
- Model evaluation report

**Success Criteria:**
- Model accuracy > 85%
- All home types classified correctly
- Model size < 5MB
- Training time < 5 minutes

---

### Phase 4: Production System (Week 4)

**Goal:** Integrate home type classification into production

**Tasks:**
1. ✅ Create `ProductionHomeTypeProfiler`
2. ✅ Create `ProductionHomeTypeClassifier`
3. ✅ Integrate with daily batch job (3 AM)
4. ✅ Add home type to database schema
5. ✅ Create API endpoints
6. ✅ Add monitoring/logging

**Deliverables:**
- `services/ai-automation-service/src/home_type/production_profiler.py`
- Database migration for home type storage
- API endpoints: `GET /api/home-type/profile`, `GET /api/home-type/classify`
- Integration with daily batch scheduler

**Success Criteria:**
- Home type profiled daily
- Classification working in production
- API endpoints functional
- Performance: < 5 min processing time

---

### Phase 5: Event Categorization (Week 5)

**Goal:** Map events to categories based on home type

**Tasks:**
1. ✅ Create `EventCategoryMapper` class
2. ✅ Implement category mapping logic
3. ✅ Integrate with event processing
4. ✅ Add event categories to InfluxDB tags
5. ✅ Create category-based queries

**Deliverables:**
- `services/ai-automation-service/src/home_type/event_categorizer.py`
- InfluxDB schema update (event_category tag)
- Category-based query endpoints

**Success Criteria:**
- Events categorized correctly
- Categories stored in InfluxDB
- Query performance acceptable

---

### Phase 6: Incremental Updates (Week 6)

**Goal:** Implement incremental home type updates

**Tasks:**
1. ✅ Create `IncrementalHomeTypeUpdater`
2. ✅ Leverage existing incremental learning
3. ✅ Integrate with daily batch job
4. ✅ Add update tracking
5. ✅ Test incremental updates

**Deliverables:**
- `services/ai-automation-service/src/home_type/incremental_updater.py`
- Integration with existing incremental learning
- Update tracking in database

**Success Criteria:**
- Incremental updates working
- 90% faster than full reprocessing
- Updates tracked correctly

---

### Phase 7: Docker Integration & Model Deployment (Week 7)

**Goal:** Integrate trained model into Docker container

**Tasks:**
1. ✅ Update Dockerfile to include pre-trained model
2. ✅ Add model loading at service startup
3. ✅ Create model versioning system
4. ✅ Add model health checks
5. ✅ Document Docker deployment process

**Deliverables:**
- Updated Dockerfile with model inclusion
- Model loading in service startup
- Model versioning metadata
- Docker deployment documentation

**Success Criteria:**
- Model loads successfully at container startup
- Model version tracked
- Health checks pass
- No training in production

---

### Phase 8: Suggestion Enhancement (Week 8)

**Goal:** Use home type for better suggestions

**Tasks:**
1. ✅ Filter suggestions by home type
2. ✅ Prioritize patterns by home type
3. ✅ Add home type context to suggestions
4. ✅ Update suggestion ranking
5. ✅ Test suggestion improvements

**Deliverables:**
- Integration with suggestion generation
- Home type-aware suggestion filtering
- Updated suggestion ranking

**Success Criteria:**
- Suggestions filtered by home type
- Acceptance rate improved (+10-15%)
- Suggestion quality improved

---

## 9. Technical Specifications

### 9.1 Resource Requirements

**Memory:**
- Home profiling: ~50MB
- Event categorization: ~20MB
- Model inference: ~30MB
- Total: <100MB

**CPU:**
- Daily batch: 2-5 minutes
- Incremental update: 30 seconds
- Model inference: 5-10ms per home

**Storage:**
- Trained model: 1-5MB
- Home profiles: ~10KB per home
- Training data: ~1MB

### 9.2 Model Specifications

**Algorithm:** RandomForestClassifier

**Parameters:**
- n_estimators: 100
- max_depth: 15
- min_samples_split: 5
- random_state: 42

**Features:** 15-20 features
- Device composition (5-7 features)
- Event patterns (4-5 features)
- Spatial layout (3-4 features)
- Behavior patterns (3-4 features)

**Classes:** 5-10 home types
- security_focused
- climate_controlled
- high_activity
- smart_home
- standard_home
- apartment
- (others as discovered)

### 9.3 Database Schema

**New Tables:**

```sql
-- Home type profiles
CREATE TABLE home_type_profiles (
    home_id TEXT PRIMARY KEY,
    home_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    profile_json TEXT NOT NULL,  -- Full profile as JSON
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Home type classification history
CREATE TABLE home_type_classifications (
    id INTEGER PRIMARY KEY,
    home_id TEXT NOT NULL,
    home_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    method TEXT NOT NULL,  -- 'ml_model'
    created_at TIMESTAMP NOT NULL
);

-- Event categories (stored in InfluxDB as tag)
-- event_category: security, climate, lighting, appliance, monitoring, general
```

### 9.4 API Endpoints

**New Endpoints:**

```python
# Home type profiling
GET /api/home-type/profile
    - Returns current home type profile

# Home type classification
GET /api/home-type/classify
    - Classifies home type using pre-trained model (loaded at startup)
    - Returns: {home_type, confidence, model_version}

# Model info
GET /api/home-type/model-info
    - Returns model metadata (version, training date, performance metrics)

# Event categories
GET /api/events/categories
    - Returns event categories for home type
```

---

## 10. Success Metrics

### 10.1 Model Performance

**Training Metrics:**
- Accuracy: > 85%
- Precision (per class): > 80%
- Recall (per class): > 75%
- F1 Score (per class): > 77%

**Production Metrics:**
- Classification confidence: > 0.7 average
- Processing time: < 5 minutes daily
- Memory usage: < 100MB

### 10.2 Suggestion Quality

**Improvement Targets:**
- Acceptance rate: +10-15% (home-type-aware suggestions)
- Suggestion relevance: +20% (filtered by home type)
- User satisfaction: Improved (better context)

### 10.3 System Performance

**Resource Usage:**
- Memory: < 100MB (target: < 50MB)
- CPU: < 5 minutes daily batch
- Storage: < 10MB (model + profiles)

**Reliability:**
- Uptime: 99.9%
- Error rate: < 1%
- Model load time: < 1 second

---

## 11. Testing Strategy

### 11.1 Unit Tests

**Test Coverage:**
- Feature extraction: 100%
- Label generation: 100%
- Model training: 90%
- Classification: 100%
- Event categorization: 100%

### 11.2 Integration Tests

**Test Scenarios:**
- Full pipeline: Synthetic home → Profile → Classification
- Incremental updates: Profile update → Re-classification
- Event categorization: Events → Categories
- Cloud export: Profile → Anonymized export

### 11.3 Validation Tests

**Validation:**
- Model accuracy on held-out synthetic homes
- Classification consistency
- Feature importance analysis
- Performance benchmarks

---

## 12. Documentation

### 12.1 Technical Documentation

**Documents to Create:**
- `docs/architecture/home-type-categorization.md` - Architecture overview
- `docs/api/home-type-api.md` - API documentation
- `docs/training/synthetic-data-generation.md` - Training data guide
- `docs/models/home-type-classifier.md` - Model documentation

### 12.2 User Documentation

**Documents to Create:**
- `docs/user/home-type-profiles.md` - User guide
- `docs/user/event-categories.md` - Event category guide

---

## 13. Timeline & Milestones

### Week 1-2: Synthetic Data Generation
- **Milestone:** 100-120 synthetic homes generated
- **Deliverable:** Synthetic homes dataset

### Week 2-3: Training Data Pipeline
- **Milestone:** 400-600 training samples ready
- **Deliverable:** Training dataset

### Week 3: Model Training
- **Milestone:** Trained model with >85% accuracy
- **Deliverable:** Trained model file

### Week 4: Production System
- **Milestone:** Home type classification in production
- **Deliverable:** Production system deployed

### Week 5: Event Categorization
- **Milestone:** Events categorized by home type
- **Deliverable:** Event categorization system

### Week 6: Incremental Updates
- **Milestone:** Incremental updates working
- **Deliverable:** Incremental update system

### Week 7: Docker Integration
- **Milestone:** Model integrated into Docker container
- **Deliverable:** Docker image with pre-trained model

### Week 8: Suggestion Enhancement
- **Milestone:** Suggestions improved with home type
- **Deliverable:** Enhanced suggestion system

**Total Timeline:** 8 weeks

---

## 14. Risk Mitigation

### 14.1 Risks & Mitigations

**Risk 1: Insufficient Training Data**
- **Mitigation:** Generate 100-120 homes (400-600 samples with augmentation)
- **Fallback:** Use rule-based as temporary fallback

**Risk 2: Model Overfitting**
- **Mitigation:** Use cross-validation, regularization
- **Fallback:** Simplify model (fewer trees, less depth)

**Risk 3: Synthetic Data Quality**
- **Mitigation:** Validate against real home patterns
- **Fallback:** Manual review of generated homes

**Risk 4: Performance Issues**
- **Mitigation:** Lightweight features, batch processing
- **Fallback:** Optimize model (fewer trees, feature selection)

**Risk 5: Integration Complexity**
- **Mitigation:** Phased integration, thorough testing
- **Fallback:** Isolated deployment, gradual rollout

---

## 15. Future Enhancements

### 15.1 Short-Term (3-6 months)

1. **Real-Time Classification**
   - Classify home type on-demand (not just daily)
   - Cache results for performance

2. **Multi-Type Classification**
   - Support multiple home types per home
   - Confidence scores for each type

3. **Home Type Evolution**
   - Track home type changes over time
   - Detect home type transitions

### 15.2 Long-Term (6-12 months)

1. **Cross-Home Training** (Different Project - Cloud Later)
   - Future: Aggregate anonymous profiles from multiple homes
   - Future: Federated learning for model improvement
   - Future: Cloud-based model updates
   - **Note:** Not in current scope, single deployment only

2. **Advanced Features**
   - Deep learning models (if needed)
   - Embedding-based similarity
   - Graph neural networks (if resources allow)

3. **User Feedback Integration**
   - Learn from user corrections
   - Improve classification accuracy
   - Custom home type definitions

---

## 16. Dependencies

### 16.1 External Dependencies

- **LLM API:** OpenAI or Gemini (for synthetic generation, local training only)
- **scikit-learn:** Model training and inference (already in ML service)
- **joblib:** Model persistence (already in dependencies)
- **numpy/pandas:** Feature engineering (already in dependencies)
- **Optional: HuggingFace transformers/sentence-transformers:** For embedding enrichment (already in OpenVINO service)

### 16.2 Internal Dependencies

- **Dataset Loader:** `HomeAssistantDatasetLoader` (existing)
- **Spatial Validator:** `SpatialProximityValidator` (existing)
- **Quality Framework:** Quality scoring (existing)
- **Incremental Learning:** Existing infrastructure
- **Daily Batch Scheduler:** Existing scheduler

---

## 17. File Structure

```
services/ai-automation-service/src/
├── home_type/
│   ├── __init__.py
│   ├── home_type_profiler.py          # Profile extraction
│   ├── feature_extractor.py            # Feature engineering
│   ├── label_generator.py             # Label generation
│   ├── home_type_classifier.py        # ML model
│   ├── production_profiler.py          # Production profiling
│   ├── event_categorizer.py            # Event categorization
│   ├── incremental_updater.py         # Incremental updates
│   └── cloud_exporter.py              # Cloud export
├── training/
│   ├── __init__.py
│   ├── synthetic_home_generator.py    # Home generation
│   ├── synthetic_area_generator.py    # Area generation
│   ├── synthetic_device_generator.py  # Device generation
│   ├── synthetic_event_generator.py   # Event generation
│   └── data_augmenter.py              # Data augmentation
└── api/
    └── home_type_router.py            # API endpoints

models/
└── home_type_classifier.pkl           # Trained model

tests/
├── test_home_type_profiler.py
├── test_home_type_classifier.py
├── test_event_categorizer.py
└── test_synthetic_generation.py

docs/
├── architecture/
│   └── home-type-categorization.md
├── api/
│   └── home-type-api.md
└── training/
    └── synthetic-data-generation.md
```

---

## 18. Acceptance Criteria

### 18.1 Phase 1: Synthetic Data Generation
- [ ] 100-120 synthetic homes generated
- [ ] All home types represented (8 types)
- [ ] All size categories represented (4 sizes)
- [ ] Device mix diversity achieved
- [ ] Homes validated for quality

### 18.2 Phase 2: Training Data Pipeline
- [ ] 400+ training samples generated
- [ ] 50+ samples per home type
- [ ] Features extracted correctly
- [ ] Labels generated accurately
- [ ] Data augmentation working

### 18.3 Phase 3: Model Training
- [ ] Model trained successfully
- [ ] Accuracy > 85%
- [ ] Model saved and loadable
- [ ] Evaluation report generated

### 18.4 Phase 4: Production System
- [ ] Home type profiled daily
- [ ] Classification working
- [ ] API endpoints functional
- [ ] Performance acceptable (< 5 min)

### 18.5 Phase 5: Event Categorization
- [ ] Events categorized correctly
- [ ] Categories stored in InfluxDB
- [ ] Query performance acceptable

### 18.6 Phase 6: Incremental Updates
- [ ] Incremental updates working
- [ ] 90% faster than full reprocessing
- [ ] Updates tracked correctly

### 18.7 Phase 7: Docker Integration
- [ ] Model included in Docker image
- [ ] Model loads at container startup
- [ ] Model versioning working
- [ ] Health checks pass

### 18.8 Phase 8: Suggestion Enhancement
- [ ] Suggestions filtered by home type
- [ ] Acceptance rate improved (+10-15%)
- [ ] Suggestion quality improved

---

## 19. Next Steps

### Immediate Actions (Week 1)

1. **Review & Approve Plan**
   - Review this plan with team
   - Get approval for approach
   - Confirm resource allocation

2. **Set Up Development Environment**
   - Create feature branch
   - Set up directory structure
   - Install dependencies

3. **Start Phase 1: Synthetic Data Generation**
   - Create `SyntheticHomeGenerator` class
   - Set up LLM API access
   - Generate first 10 homes (proof of concept)

### Preparation

1. **LLM API Setup**
   - Get OpenAI or Gemini API key
   - Set up API client
   - Test generation pipeline

2. **Dataset Directory Setup**
   - Create `tests/datasets/synthetic_homes/`
   - Set up version control
   - Create seed data templates

3. **Model Directory Setup**
   - Create `models/` directory
   - Set up model versioning
   - Create backup strategy

---

## 20. References

### Internal Documents
- `implementation/analysis/QUALITY_FRAMEWORK_ENHANCEMENT_2025.md`
- `implementation/analysis/HOME_ASSISTANT_DATASETS_INTEGRATION_PLAN.md`
- `implementation/analysis/DATASET_TESTING_STRATEGY.md`
- `services/ai-automation-service/src/synergy_detection/spatial_validator.py`

### External References
- [home-assistant-datasets](https://github.com/allenporter/home-assistant-datasets)
- [Synthetic Home Format](https://github.com/allenporter/synthetic-home)
- [scikit-learn RandomForestClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html) - Baseline model
- [HuggingFace all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) - Optional embedding enrichment
- [2025 Edge ML Best Practices](https://huggingface.co/blog/tugrulkaya/running-large-transformer-models-on-mobile) - Edge deployment guidelines
- [Docker ML Model Deployment](https://www.docker.com/blog/how-to-build-run-and-package-ai-models-locally-with-docker-model-runner/) - Container best practices

---

## Status

**Current:** Planning Complete - Ready for Implementation  
**Next:** Phase 1 - Synthetic Data Generation  
**Owner:** AI Automation Service Team  
**Last Updated:** November 2025

