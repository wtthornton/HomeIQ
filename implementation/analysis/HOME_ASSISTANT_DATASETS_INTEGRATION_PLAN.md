# Home Assistant Datasets Integration Plan
## Testing & Enhancing Patterns & Synergies Effectiveness

**Date:** January 2025  
**Status:** Analysis Complete - Implementation Plan Ready  
**Source:** [home-assistant-datasets](https://github.com/allenporter/home-assistant-datasets)

---

## Executive Summary

The [home-assistant-datasets](https://github.com/allenporter/home-assistant-datasets) repository provides synthetic home datasets and evaluation frameworks that can significantly enhance our Patterns & Synergies system. This document outlines how to leverage these datasets for:

1. **Pattern Detection Validation** - Test accuracy of co-occurrence, time-of-day, and multi-factor detectors
2. **Synergy Detection Benchmarking** - Evaluate predefined and ML-discovered synergies against ground truth
3. **Automation Generation Testing** - Validate automation suggestions against known-good automations
4. **Continuous Improvement** - Create feedback loops for pattern/synergy quality

**Key Opportunities:**
- ✅ Synthetic homes with known device relationships (ground truth)
- ✅ Assist/intent datasets for voice action evaluation
- ✅ Automation evaluation datasets for blueprint/automation testing
- ✅ Standardized evaluation framework (pytest-based)

---

## 1. Repository Overview

### Available Datasets

#### 1.1 Synthetic Home Datasets
**Location:** `datasets/` directory  
**Content:**
- **Home descriptions** - Complete home configurations
- **Area descriptions** - Room/area definitions with device layouts
- **Device descriptions** - Device registry with types, models, capabilities
- **Device states** - Historical state data for pattern detection

**Format:** Synthetic Home format (YAML/JSON)  
**Use Case:** Create test environments with known device relationships

#### 1.2 Assist Datasets
**Location:** `datasets/assist/` and `datasets/assist-mini/`  
**Content:**
- Voice action test cases
- Expected automation behaviors
- Device interaction scenarios

**Use Case:** Test pattern detection on voice-triggered automations

#### 1.3 Intent Datasets
**Location:** `datasets/intents/`  
**Content:**
- Based on Home Assistant intents repository unit tests
- Large home configurations (stress testing)
- NLP model evaluation data

**Use Case:** Test pattern/synergy detection on complex, large-scale homes

#### 1.4 Automation Datasets
**Location:** `datasets/automations/`  
**Content:**
- Zero-shot blueprint/automation creation tasks
- Problem descriptions with expected results
- Test evaluations for generated automations

**Use Case:** Validate automation suggestions generated from patterns/synergies

---

## 2. Integration Strategy

### 2.1 Pattern Detection Testing Framework

#### Objective
Validate pattern detection accuracy using synthetic homes with known device relationships.

#### Implementation Plan

**Step 1: Dataset Import**
```python
# services/ai-automation-service/src/testing/dataset_loader.py
class HomeAssistantDatasetLoader:
    """Load synthetic home datasets for testing"""
    
    async def load_synthetic_home(self, dataset_name: str) -> dict:
        """
        Load synthetic home configuration.
        Returns: {
            'home': {...},
            'areas': [...],
            'devices': [...],
            'expected_patterns': [...],  # Ground truth patterns
            'expected_synergies': [...]   # Ground truth synergies
        }
        """
```

**Step 2: Pattern Ground Truth Extraction**
- Extract known device relationships from dataset metadata
- Map to our pattern types (co-occurrence, time-of-day, multi-factor)
- Create ground truth pattern list with confidence scores

**Step 3: Pattern Detection Test Suite**
```python
# tests/pattern_detection/test_with_datasets.py
@pytest.mark.asyncio
async def test_co_occurrence_patterns_on_synthetic_home():
    """Test co-occurrence detection on assist-mini dataset"""
    loader = HomeAssistantDatasetLoader()
    home_data = await loader.load_synthetic_home("assist-mini")
    
    # Inject events into InfluxDB (simulate)
    await inject_events_from_dataset(home_data['events'])
    
    # Run our pattern detection
    patterns = await detect_patterns(
        pattern_type='co_occurrence',
        min_confidence=0.7
    )
    
    # Compare against ground truth
    ground_truth = home_data['expected_patterns']
    metrics = evaluate_pattern_detection(patterns, ground_truth)
    
    assert metrics['precision'] > 0.8
    assert metrics['recall'] > 0.75
    assert metrics['f1_score'] > 0.77
```

**Step 4: Metrics Collection**
- **Precision**: % of detected patterns that are correct
- **Recall**: % of ground truth patterns detected
- **F1 Score**: Harmonic mean of precision/recall
- **False Positive Rate**: Patterns detected but not in ground truth
- **False Negative Rate**: Ground truth patterns missed

#### Expected Outcomes

**Current State (Baseline):**
- Co-occurrence: ~1,817 patterns (94% of total)
- Time-of-day: ~48 patterns (2.5%)
- Multi-factor: ~65 patterns (3.4%)

**Target Improvements:**
- Reduce false positives (system noise: images, sensors)
- Increase time-of-day pattern detection (target: 5-10%)
- Increase multi-factor patterns (target: 5-10%)
- Improve pattern confidence calibration

---

### 2.2 Synergy Detection Benchmarking

#### Objective
Evaluate synergy detection accuracy against known device relationships.

#### Implementation Plan

**Step 1: Ground Truth Synergy Extraction**
```python
# Extract from dataset device relationships
expected_synergies = [
    {
        'trigger_entity': 'binary_sensor.motion_kitchen',
        'action_entity': 'light.kitchen',
        'relationship_type': 'motion_to_light',
        'confidence': 0.9,  # Known relationship
        'area': 'kitchen'
    },
    # ... more synergies
]
```

**Step 2: Synergy Detection Test**
```python
@pytest.mark.asyncio
async def test_synergy_detection_on_assist_dataset():
    """Test synergy detection on assist dataset"""
    loader = HomeAssistantDatasetLoader()
    home_data = await loader.load_synthetic_home("assist")
    
    # Load devices into system
    await load_devices_from_dataset(home_data['devices'])
    
    # Run our synergy detection
    synergies = await detect_synergies(
        min_confidence=0.7,
        validate_with_patterns=True
    )
    
    # Compare against ground truth
    ground_truth = home_data['expected_synergies']
    metrics = evaluate_synergy_detection(synergies, ground_truth)
    
    # Validate predefined relationships
    predefined_metrics = evaluate_predefined_synergies(
        synergies, 
        ground_truth,
        relationship_types=['motion_to_light', 'door_to_lock']
    )
    
    # Validate ML-discovered synergies
    ml_metrics = evaluate_ml_synergies(
        synergies,
        ground_truth
    )
    
    assert predefined_metrics['precision'] > 0.85
    assert ml_metrics['recall'] > 0.70  # ML should discover additional synergies
```

**Step 3: Relationship Type Coverage**
- Test each of 16 predefined relationship types
- Validate ML-discovered synergies (Apriori algorithm)
- Measure coverage: % of ground truth relationships detected

#### Expected Outcomes

**Current State:**
- 6,394 synergies detected
- 81.7% pattern-validated (5,224/6,394)
- 0 discovered_synergies (ML not storing results - TODO fix)

**Target Improvements:**
- Increase pattern validation rate to 90%+
- Fix ML synergy storage (discovered_synergies table)
- Improve relationship type diversity
- Reduce false positives (non-actionable synergies)

---

### 2.3 Automation Generation Testing

#### Objective
Validate automation suggestions generated from patterns/synergies against known-good automations.

#### Implementation Plan

**Step 1: Automation Dataset Integration**
```python
# Load automation evaluation datasets
automation_tasks = [
    {
        'description': 'Turn on lights when motion detected',
        'expected_automation': {...},  # Ground truth YAML
        'test_scenarios': [...],  # Test cases to validate
        'devices_involved': ['binary_sensor.motion', 'light.kitchen']
    }
]
```

**Step 2: Pattern-to-Automation Test**
```python
@pytest.mark.asyncio
async def test_automation_from_pattern():
    """Test automation generation from detected pattern"""
    # Detect pattern
    pattern = await detect_patterns(pattern_type='co_occurrence')[0]
    
    # Generate automation suggestion
    suggestion = await generate_suggestion_from_pattern(pattern)
    
    # Generate YAML
    yaml = await generate_automation_yaml(suggestion)
    
    # Compare against ground truth
    ground_truth = automation_tasks[0]['expected_automation']
    similarity = compare_automation_yaml(yaml, ground_truth)
    
    # Test execution
    test_results = await test_automation_execution(yaml, automation_tasks[0]['test_scenarios'])
    
    assert similarity['structural_match'] > 0.8
    assert test_results['pass_rate'] > 0.9
```

**Step 3: Synergy-to-Automation Test**
```python
@pytest.mark.asyncio
async def test_automation_from_synergy():
    """Test automation generation from detected synergy"""
    # Detect synergy
    synergy = await detect_synergies()[0]
    
    # Generate automation suggestion
    suggestion = await generate_suggestion_from_synergy(synergy)
    
    # Validate against expected relationship behavior
    expected_behavior = get_expected_behavior_for_relationship(
        synergy['relationship_type']
    )
    
    assert suggestion['trigger_type'] == expected_behavior['trigger_type']
    assert suggestion['action_type'] == expected_behavior['action_type']
```

#### Expected Outcomes

**Current State:**
- Automation generation from patterns: ✅ Working
- Automation generation from synergies: ✅ Working
- YAML quality: 4.6/5.0 (needs improvement)

**Target Improvements:**
- Increase YAML generation accuracy (target: 5.0/5.0)
- Reduce entity resolution errors
- Improve automation test pass rate (target: 95%+)
- Better handling of complex multi-device automations

---

## 3. Enhanced Functionality Opportunities

### 3.1 Pattern Detection Enhancements

#### A. Synthetic Pattern Injection
**Use Case:** Test pattern detectors with controlled scenarios

```python
# Inject synthetic events to test specific patterns
async def test_time_of_day_detection():
    """Test time-of-day pattern with synthetic events"""
    # Create synthetic events at consistent times
    events = generate_synthetic_events(
        entity='light.kitchen',
        times=['18:00', '18:05', '18:10'],  # Consistent 6 PM
        days=7  # 7 days of data
    )
    
    # Inject into InfluxDB
    await inject_events(events)
    
    # Run detection
    patterns = await detect_patterns(pattern_type='time_of_day')
    
    # Should detect 6 PM pattern
    assert any(p['time'] == '18:00' for p in patterns)
```

#### B. Pattern Type Diversity Testing
**Use Case:** Ensure all pattern types are being detected

```python
async def test_pattern_type_coverage():
    """Ensure all pattern types are detected on diverse datasets"""
    datasets = ['assist-mini', 'assist', 'intents']
    pattern_types = [
        'co_occurrence', 'time_of_day', 'multi_factor',
        'sequence', 'contextual', 'room_based'
    ]
    
    coverage = {}
    for dataset in datasets:
        home_data = await load_synthetic_home(dataset)
        patterns = await detect_patterns_on_home(home_data)
        
        for pattern_type in pattern_types:
            count = len([p for p in patterns if p['pattern_type'] == pattern_type])
            coverage[f"{dataset}_{pattern_type}"] = count
    
    # Ensure all types are detected
    assert all(count > 0 for count in coverage.values())
```

### 3.2 Synergy Detection Enhancements

#### A. Relationship Type Expansion
**Use Case:** Discover new relationship types from datasets

```python
async def discover_new_relationship_types():
    """Analyze datasets to find new relationship patterns"""
    datasets = await load_all_datasets()
    
    # Extract all device interactions
    interactions = []
    for dataset in datasets:
        interactions.extend(extract_device_interactions(dataset))
    
    # Find common interaction patterns not in our 16 types
    new_relationships = analyze_interaction_patterns(interactions)
    
    # Example: might discover "presence_to_media" relationship
    # if datasets show users often turn on media when presence detected
```

#### B. Multi-Device Chain Validation
**Use Case:** Test 3-device and 4-device chain detection

```python
async def test_multi_device_chains():
    """Test detection of device chains (A → B → C)"""
    # Load dataset with known chains
    home_data = await load_synthetic_home("assist")
    
    # Known chain: motion → light → media_player
    expected_chain = [
        'binary_sensor.motion',
        'light.kitchen',
        'media_player.kitchen'
    ]
    
    # Detect chains
    chains = await detect_device_chains(min_length=3)
    
    # Should find expected chain
    assert any(
        chain['devices'] == expected_chain 
        for chain in chains
    )
```

### 3.3 Automation Quality Improvements

#### A. Template Validation Against Datasets
**Use Case:** Validate automation templates against known-good automations

```python
async def validate_templates_against_datasets():
    """Test our templates against dataset automations"""
    templates = load_automation_templates()
    dataset_automations = load_automation_datasets()
    
    for template in templates:
        # Find similar automations in dataset
        similar = find_similar_automations(template, dataset_automations)
        
        # Compare structure and behavior
        validation = compare_template_to_ground_truth(template, similar)
        
        # Improve template if needed
        if validation['score'] < 0.8:
            improve_template(template, validation['suggestions'])
```

#### B. Suggestion Ranking Validation
**Use Case:** Ensure high-quality suggestions are ranked first

```python
async def test_suggestion_ranking():
    """Validate suggestion ranking against user preferences"""
    # Load dataset with user preference data
    preferences = load_user_preferences_from_datasets()
    
    # Generate suggestions
    suggestions = await generate_suggestions_from_patterns()
    
    # Rank suggestions
    ranked = rank_suggestions(suggestions, preferences)
    
    # Validate top suggestions match user preferences
    top_5 = ranked[:5]
    match_rate = calculate_preference_match(top_5, preferences)
    
    assert match_rate > 0.7  # 70% of top 5 should match preferences
```

---

## 4. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
**Goal:** Set up dataset loading and basic testing framework

**Tasks:**
1. ✅ Create `HomeAssistantDatasetLoader` class
2. ✅ Implement dataset import from repository
3. ✅ Create test infrastructure (pytest fixtures)
4. ✅ Set up synthetic event injection into InfluxDB
5. ✅ Create ground truth extraction utilities

**Deliverables:**
- Dataset loader module
- Test framework setup
- Basic pattern detection tests

### Phase 2: Pattern Testing (Week 3-4)
**Goal:** Comprehensive pattern detection testing

**Tasks:**
1. ✅ Implement pattern detection test suite
2. ✅ Create metrics collection (precision, recall, F1)
3. ✅ Test all pattern types (co-occurrence, time-of-day, multi-factor)
4. ✅ Validate pattern filtering (remove system noise)
5. ✅ Create pattern detection benchmark report

**Deliverables:**
- Pattern detection test suite
- Benchmark metrics and reports
- Pattern quality improvements

### Phase 3: Synergy Testing (Week 5-6)
**Goal:** Comprehensive synergy detection testing

**Tasks:**
1. ✅ Implement synergy detection test suite
2. ✅ Test all 16 predefined relationship types
3. ✅ Validate ML-discovered synergies
4. ✅ Test multi-device chain detection
5. ✅ Fix discovered_synergies storage (current TODO)

**Deliverables:**
- Synergy detection test suite
- ML synergy storage fix
- Synergy quality improvements

### Phase 4: Automation Testing (Week 7-8)
**Goal:** Automation generation validation

**Tasks:**
1. ✅ Implement automation generation tests
2. ✅ Validate YAML quality against ground truth
3. ✅ Test automation execution (using Synthetic Home)
4. ✅ Create automation quality metrics
5. ✅ Improve suggestion ranking

**Deliverables:**
- Automation generation test suite
- YAML quality improvements
- Suggestion ranking enhancements

### Phase 5: Continuous Improvement (Ongoing)
**Goal:** Integrate testing into CI/CD pipeline

**Tasks:**
1. ✅ Add dataset tests to CI pipeline
2. ✅ Create automated benchmark reports
3. ✅ Set up regression testing
4. ✅ Monitor pattern/synergy quality over time
5. ✅ Create feedback loops for improvement

**Deliverables:**
- CI/CD integration
- Automated benchmarking
- Quality monitoring dashboard

---

## 5. Expected Impact

### Pattern Detection Improvements

**Current Metrics:**
- Co-occurrence: 1,817 patterns (94%)
- Time-of-day: 48 patterns (2.5%)
- Multi-factor: 65 patterns (3.4%)
- System noise: ~211 image patterns, ~168 sensor patterns

**Target Metrics:**
- Co-occurrence: 1,500-1,600 patterns (80-85%) - **Reduced false positives**
- Time-of-day: 150-200 patterns (8-10%) - **3-4x increase**
- Multi-factor: 150-200 patterns (8-10%) - **3x increase**
- System noise: <50 patterns (<3%) - **75% reduction**

**Quality Improvements:**
- Precision: 0.75 → 0.85+ (13% improvement)
- Recall: 0.70 → 0.80+ (14% improvement)
- F1 Score: 0.72 → 0.82+ (14% improvement)

### Synergy Detection Improvements

**Current Metrics:**
- Total synergies: 6,394
- Pattern-validated: 5,224 (81.7%)
- ML-discovered: 0 (storage not working)
- Relationship types: 16 predefined

**Target Metrics:**
- Pattern-validated: 90%+ (8% improvement)
- ML-discovered: 500-1,000 synergies (new capability)
- Relationship types: 20-25 types (discover 4-9 new types)
- False positive rate: <10% (currently unknown)

**Quality Improvements:**
- Precision: Unknown → 0.85+
- Recall: Unknown → 0.80+
- Coverage: Unknown → 90%+ of ground truth relationships

### Automation Generation Improvements

**Current Metrics:**
- YAML quality: 4.6/5.0
- Entity resolution: 4.6/5.0
- Suggestion accuracy: 4.7/5.0

**Target Metrics:**
- YAML quality: 5.0/5.0 (9% improvement)
- Entity resolution: 5.0/5.0 (9% improvement)
- Suggestion accuracy: 5.0/5.0 (6% improvement)
- Automation test pass rate: 95%+ (new metric)

---

## 6. Technical Implementation Details

### 6.1 Dataset Repository Integration

**Option 1: Git Submodule**
```bash
git submodule add https://github.com/allenporter/home-assistant-datasets.git tests/datasets
```

**Option 2: Direct Download**
```python
# Download datasets on-demand
async def download_dataset(dataset_name: str):
    url = f"https://raw.githubusercontent.com/allenporter/home-assistant-datasets/main/datasets/{dataset_name}"
    # Download and cache locally
```

**Option 3: Package Installation**
```bash
# If available as Python package
pip install home-assistant-datasets
```

### 6.2 Synthetic Home Integration

**Using Synthetic Home Library:**
```python
from synthetic_home import SyntheticHome

# Load synthetic home
home = SyntheticHome.from_yaml("datasets/assist-mini/home.yaml")

# Extract devices
devices = home.devices  # List of device entities

# Extract areas
areas = home.areas  # List of area definitions

# Generate events
events = home.generate_events(days=30)  # 30 days of synthetic events
```

### 6.3 Test Data Injection

**InfluxDB Event Injection:**
```python
async def inject_events_from_dataset(events: list[dict]):
    """Inject synthetic events into InfluxDB for testing"""
    from services.data_api.src.influxdb_client import InfluxDBClient
    
    client = InfluxDBClient()
    
    for event in events:
        await client.write_event(
            entity_id=event['entity_id'],
            state=event['state'],
            timestamp=event['timestamp'],
            attributes=event.get('attributes', {})
        )
```

**SQLite Device Injection:**
```python
async def inject_devices_from_dataset(devices: list[dict], db_session):
    """Inject synthetic devices into SQLite for testing"""
    from services.ai-automation-service.src.database.crud import create_device
    
    for device in devices:
        await create_device(db_session, device)
```

### 6.4 Evaluation Metrics

**Pattern Detection Metrics:**
```python
def evaluate_pattern_detection(
    detected: list[dict],
    ground_truth: list[dict]
) -> dict:
    """Calculate precision, recall, F1 for pattern detection"""
    
    # Match detected patterns to ground truth
    true_positives = match_patterns(detected, ground_truth)
    false_positives = len(detected) - len(true_positives)
    false_negatives = len(ground_truth) - len(true_positives)
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'true_positives': len(true_positives),
        'false_positives': false_positives,
        'false_negatives': false_negatives
    }
```

**Synergy Detection Metrics:**
```python
def evaluate_synergy_detection(
    detected: list[dict],
    ground_truth: list[dict]
) -> dict:
    """Calculate metrics for synergy detection"""
    
    # Match by trigger/action entity pair
    matches = match_synergies(detected, ground_truth)
    
    # Calculate relationship type coverage
    detected_types = set(s['relationship_type'] for s in detected)
    ground_truth_types = set(s['relationship_type'] for s in ground_truth)
    type_coverage = len(detected_types & ground_truth_types) / len(ground_truth_types)
    
    return {
        'precision': calculate_precision(detected, ground_truth),
        'recall': calculate_recall(detected, ground_truth),
        'f1_score': calculate_f1(detected, ground_truth),
        'relationship_type_coverage': type_coverage,
        'detected_types': list(detected_types),
        'missing_types': list(ground_truth_types - detected_types)
    }
```

---

## 7. Success Criteria

### Pattern Detection
- ✅ Precision > 0.85 (currently ~0.75)
- ✅ Recall > 0.80 (currently ~0.70)
- ✅ F1 Score > 0.82 (currently ~0.72)
- ✅ Time-of-day patterns: 8-10% of total (currently 2.5%)
- ✅ Multi-factor patterns: 8-10% of total (currently 3.4%)
- ✅ System noise: <3% of patterns (currently ~20%)

### Synergy Detection
- ✅ Pattern validation rate: 90%+ (currently 81.7%)
- ✅ ML-discovered synergies: 500-1,000 stored (currently 0)
- ✅ Relationship type coverage: 90%+ of ground truth
- ✅ Precision > 0.85
- ✅ Recall > 0.80

### Automation Generation
- ✅ YAML quality: 5.0/5.0 (currently 4.6)
- ✅ Entity resolution: 5.0/5.0 (currently 4.6)
- ✅ Automation test pass rate: 95%+
- ✅ Suggestion ranking accuracy: 70%+ top-5 match user preferences

---

## 8. Next Steps

1. **Review & Approval** - Review this plan with team
2. **Dataset Access** - Set up access to home-assistant-datasets repository
3. **Phase 1 Implementation** - Begin foundation work (Week 1)
4. **Iterative Testing** - Run tests as each phase completes
5. **Metrics Dashboard** - Create dashboard for ongoing monitoring

---

## References

- [home-assistant-datasets Repository](https://github.com/allenporter/home-assistant-datasets)
- [Synthetic Home Format](https://github.com/allenporter/synthetic-home)
- [Home Assistant Intents](https://github.com/home-assistant/intents)
- Current Patterns & Synergies Implementation:
  - `services/ai-automation-service/src/synergy_detection/synergy_detector.py`
  - `services/ai-automation-service/src/pattern_detection/`
  - `implementation/PATTERNS_SYNERGIES_IMPROVEMENT_PLAN.md`

---

**Document Status:** Ready for Implementation  
**Last Updated:** January 2025  
**Owner:** AI Automation Service Team

