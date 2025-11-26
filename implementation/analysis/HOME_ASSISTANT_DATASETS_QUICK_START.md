# Home Assistant Datasets - Quick Start Guide
## Testing Patterns & Synergies Effectiveness

**Quick Reference:** See [HOME_ASSISTANT_DATASETS_INTEGRATION_PLAN.md](./HOME_ASSISTANT_DATASETS_INTEGRATION_PLAN.md) for full details.

---

## 🎯 Key Opportunities

### 1. Pattern Detection Testing
- **Problem:** 94% co-occurrence patterns, only 2.5% time-of-day, 3.4% multi-factor
- **Solution:** Use synthetic homes with known patterns to test detection accuracy
- **Impact:** Increase pattern diversity, reduce false positives

### 2. Synergy Detection Benchmarking
- **Problem:** 81.7% pattern-validated, 0 ML-discovered synergies stored
- **Solution:** Test against known device relationships in datasets
- **Impact:** Improve validation rate to 90%+, fix ML storage, discover new relationship types

### 3. Automation Generation Validation
- **Problem:** YAML quality 4.6/5.0, entity resolution 4.6/5.0
- **Solution:** Validate generated automations against known-good automations
- **Impact:** Achieve 5.0/5.0 quality, 95%+ test pass rate

---

## 🚀 Quick Start (30 Minutes)

### Step 1: Clone Dataset Repository
```bash
# Option A: Git submodule
git submodule add https://github.com/allenporter/home-assistant-datasets.git tests/datasets

# Option B: Clone separately
git clone https://github.com/allenporter/home-assistant-datasets.git tests/datasets
```

### Step 2: Install Dependencies
```bash
# Install Synthetic Home library (if needed)
pip install synthetic-home

# Or use the dataset format directly
# Datasets are in YAML/JSON format
```

### Step 3: Create Basic Test
```python
# tests/pattern_detection/test_with_datasets.py
import pytest
from pathlib import Path

@pytest.mark.asyncio
async def test_pattern_detection_on_assist_mini():
    """Quick test: Load assist-mini dataset and detect patterns"""
    
    # Load dataset
    dataset_path = Path("tests/datasets/datasets/assist-mini")
    home_config = load_yaml(dataset_path / "home.yaml")
    
    # Extract devices and events
    devices = home_config['devices']
    events = load_events_from_dataset(dataset_path)
    
    # Inject into system (simulate)
    await inject_devices(devices)
    await inject_events(events)
    
    # Run our pattern detection
    from services.ai_automation_service.src.pattern_detection import detect_patterns
    patterns = await detect_patterns(pattern_type='co_occurrence')
    
    # Basic validation
    assert len(patterns) > 0
    print(f"Detected {len(patterns)} patterns")
    
    # Check for known relationships (e.g., motion → light)
    motion_light_patterns = [
        p for p in patterns 
        if 'motion' in p.get('device1', '') and 'light' in p.get('device2', '')
    ]
    assert len(motion_light_patterns) > 0, "Should detect motion-to-light patterns"
```

### Step 4: Run Test
```bash
pytest tests/pattern_detection/test_with_datasets.py -v
```

---

## 📊 Available Datasets

### assist-mini (Recommended for Quick Testing)
- **Size:** Small home, limited entities
- **Use Case:** Fast pattern/synergy testing
- **Location:** `datasets/assist-mini/`

### assist
- **Size:** Medium home, more complex scenarios
- **Use Case:** Comprehensive testing
- **Location:** `datasets/assist/`

### intents
- **Size:** Large home, stress testing
- **Use Case:** Performance and scalability testing
- **Location:** `datasets/intents/`

### automations
- **Size:** Automation evaluation tasks
- **Use Case:** Validate automation generation
- **Location:** `datasets/automations/`

---

## 🔧 Integration Points

### Pattern Detection
```python
# Current: services/ai-automation-service/src/pattern_detection/
# Test: Compare detected patterns vs. ground truth from datasets
```

### Synergy Detection
```python
# Current: services/ai-automation-service/src/synergy_detection/
# Test: Validate 16 relationship types against dataset relationships
```

### Automation Generation
```python
# Current: services/ai-automation-service/src/api/suggestion_router.py
# Test: Compare generated YAML vs. expected automations in datasets
```

---

## 📈 Expected Results

### Pattern Detection
- **Before:** 94% co-occurrence, 2.5% time-of-day
- **After:** 80-85% co-occurrence, 8-10% time-of-day, 8-10% multi-factor
- **Quality:** Precision 0.75 → 0.85+, Recall 0.70 → 0.80+

### Synergy Detection
- **Before:** 81.7% validated, 0 ML-discovered
- **After:** 90%+ validated, 500-1,000 ML-discovered
- **Quality:** Discover 4-9 new relationship types

### Automation Generation
- **Before:** YAML 4.6/5.0, Entity resolution 4.6/5.0
- **After:** YAML 5.0/5.0, Entity resolution 5.0/5.0
- **Quality:** 95%+ automation test pass rate

---

## 🎓 Learning Resources

1. **Repository README:** [home-assistant-datasets](https://github.com/allenporter/home-assistant-datasets)
2. **Synthetic Home Format:** [synthetic-home](https://github.com/allenporter/synthetic-home)
3. **Full Integration Plan:** [HOME_ASSISTANT_DATASETS_INTEGRATION_PLAN.md](./HOME_ASSISTANT_DATASETS_INTEGRATION_PLAN.md)

---

## ⚡ Next Actions

1. **Today:** Clone repository, explore dataset structure
2. **This Week:** Create basic test framework, run first pattern detection test
3. **This Month:** Complete Phase 1-2 (Foundation + Pattern Testing)
4. **Next Month:** Complete Phase 3-4 (Synergy + Automation Testing)

---

**Quick Start Status:** Ready to Begin  
**Estimated Setup Time:** 30 minutes  
**First Test Time:** 1-2 hours

