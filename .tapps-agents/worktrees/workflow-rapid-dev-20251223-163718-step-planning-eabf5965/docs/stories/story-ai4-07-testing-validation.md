# Story AI4.7: Testing & Validation

**Epic:** AI-4 - N-Level Synergy Detection  
**Story Points:** 8  
**Priority:** High  
**Dependencies:** Stories AI4.1-AI4.6

---

## Story Description

AS A development team  
I WANT TO comprehensively test n-level synergy detection  
SO THAT we ensure 80-85% accuracy and production readiness

---

## Acceptance Criteria

### Must Have

1. **✅ Test Dataset Creation**
   - Create labeled test dataset (50 sample homes)
   - Label expected synergies manually
   - Include edge cases (1 device, 100+ devices, no compatible devices)
   - Diversity: apartments, houses, multi-floor homes

2. **✅ Accuracy Testing**
   - Precision: % of suggested synergies that are useful
   - Recall: % of possible synergies detected
   - F1 Score: Harmonic mean of precision and recall
   - Target: 80-85% precision, 70-75% recall

3. **✅ Component Testing**
   - Unit tests: Descriptor builder, embedding generation, path scoring
   - Integration tests: End-to-end pipeline
   - Model tests: Verify INT8 quantization quality
   - Database tests: Embedding storage/retrieval

4. **✅ Performance Testing**
   - Load tests: 10, 20, 50, 100 devices
   - Stress tests: Maximum depth (5 hops)
   - Memory leak tests: 1000 consecutive runs
   - Concurrency tests: Multiple simultaneous requests

5. **✅ User Acceptance Testing**
   - Manual review of top 20 suggestions
   - User feedback collection
   - Comparison vs existing 2-level synergies
   - Usability testing

### Should Have

6. **📋 Regression Testing**
   - Golden dataset (unchanging test set)
   - Automated regression suite
   - Performance regression tracking
   - Model version comparison

7. **📋 Error Handling Tests**
   - Model loading failures
   - Database connection errors
   - Invalid input handling
   - Memory exhaustion scenarios

---

## Test Dataset Structure

```json
{
  "home_id": "test-home-001",
  "description": "2BR apartment, kitchen + living room + 2 bedrooms",
  "devices": [
    {
      "entity_id": "binary_sensor.kitchen_motion",
      "device_class": "motion",
      "area_id": "kitchen"
    },
    {
      "entity_id": "light.kitchen_ceiling",
      "area_id": "kitchen"
    },
    {
      "entity_id": "climate.home",
      "area_id": "whole_home"
    }
  ],
  "expected_synergies": [
    {
      "chain": [
        "binary_sensor.kitchen_motion",
        "light.kitchen_ceiling"
      ],
      "category": "convenience",
      "rationale": "Motion-activated kitchen lighting"
    },
    {
      "chain": [
        "binary_sensor.kitchen_motion",
        "light.kitchen_ceiling",
        "climate.home"
      ],
      "category": "comfort",
      "rationale": "Presence-based comfort automation"
    }
  ]
}
```

---

## Test Scenarios

### Scenario 1: Small Apartment (10 devices)
- **Devices:** Motion sensors (2), lights (4), thermostat (1), switches (3)
- **Expected:** 5-8 2-hop synergies, 2-4 3-hop synergies
- **Edge Case:** Limited device types

### Scenario 2: Medium House (20 devices)
- **Devices:** Motion (4), doors (3), lights (8), climate (2), switches (3)
- **Expected:** 10-15 2-hop, 5-8 3-hop
- **Edge Case:** Multiple areas

### Scenario 3: Large Home (50 devices)
- **Devices:** Complete smart home setup
- **Expected:** 20-30 total synergies
- **Edge Case:** Performance at scale

### Scenario 4: Single Device
- **Devices:** 1 light
- **Expected:** 0 synergies
- **Edge Case:** No compatible pairs

### Scenario 5: No Compatible Devices
- **Devices:** All same type (10 lights)
- **Expected:** 0 synergies
- **Edge Case:** Homogeneous device set

---

## Automated Test Suite

```python
# tests/test_nlevel_synergy_accuracy.py

import pytest
import json
from nlevel_synergy.detector import NLevelSynergyDetector

class TestNLevelSynergyAccuracy:
    """
    Story AI4.7: Accuracy testing with labeled dataset
    """
    
    @pytest.fixture
    def test_dataset(self):
        """Load labeled test dataset."""
        with open('tests/fixtures/nlevel_test_dataset.json') as f:
            return json.load(f)
    
    @pytest.mark.asyncio
    async def test_precision_recall(self, test_dataset, detector):
        """Test precision and recall on labeled dataset."""
        results = {
            'true_positives': 0,
            'false_positives': 0,
            'false_negatives': 0
        }
        
        for home in test_dataset['homes']:
            # Run detection
            detected = await detector.detect_nlevel_synergies(
                home['devices'],
                max_depth=3
            )
            
            # Compare with expected
            expected = home['expected_synergies']
            
            for synergy in detected:
                if self._is_correct_synergy(synergy, expected):
                    results['true_positives'] += 1
                else:
                    results['false_positives'] += 1
            
            # Count missed synergies
            for expected_synergy in expected:
                if not self._was_detected(expected_synergy, detected):
                    results['false_negatives'] += 1
        
        # Calculate metrics
        precision = results['true_positives'] / (results['true_positives'] + results['false_positives'])
        recall = results['true_positives'] / (results['true_positives'] + results['false_negatives'])
        f1 = 2 * (precision * recall) / (precision + recall)
        
        print(f"\n📊 Accuracy Metrics:")
        print(f"   Precision: {precision:.1%}")
        print(f"   Recall: {recall:.1%}")
        print(f"   F1 Score: {f1:.1%}")
        
        # Assert targets
        assert precision >= 0.80, f"Precision {precision:.1%} below target 80%"
        assert recall >= 0.70, f"Recall {recall:.1%} below target 70%"
    
    def _is_correct_synergy(self, detected, expected_list):
        """Check if detected synergy matches expected."""
        for expected in expected_list:
            if self._chains_match(detected['chain'], expected['chain']):
                return True
        return False
    
    def _chains_match(self, chain1, chain2):
        """Check if two chains are equivalent."""
        return chain1 == chain2 or chain1 == list(reversed(chain2))

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_single_device(self, detector):
        """Test with single device (expect 0 synergies)."""
        devices = [{"entity_id": "light.living_room"}]
        synergies = await detector.detect_nlevel_synergies(devices)
        assert len(synergies) == 0
    
    @pytest.mark.asyncio
    async def test_no_compatible_devices(self, detector):
        """Test with no compatible device pairs."""
        devices = [{"entity_id": f"light.room_{i}"} for i in range(10)]
        synergies = await detector.detect_nlevel_synergies(devices)
        assert len(synergies) == 0
    
    @pytest.mark.asyncio
    async def test_large_home(self, detector):
        """Test with 100+ devices (performance check)."""
        devices = self._generate_large_home(100)
        
        import time
        start = time.time()
        synergies = await detector.detect_nlevel_synergies(devices, max_depth=3)
        elapsed = time.time() - start
        
        assert elapsed < 30, f"Large home detection took {elapsed:.1f}s (target <30s)"
        assert len(synergies) > 0, "Should find some synergies in large home"
```

---

## Manual Review Checklist

### Review Criteria
- [ ] Chain makes logical sense
- [ ] Devices are in compatible areas
- [ ] Category classification is correct
- [ ] Complexity assessment is accurate
- [ ] Rationale is clear and helpful
- [ ] Automation would be useful to users

### Sample Manual Review

| Chain | Logical? | Category Correct? | Would Use? | Notes |
|-------|----------|-------------------|------------|-------|
| Motion → Light | ✅ Yes | ✅ Convenience | ✅ Yes | Classic automation |
| Motion → Light → Climate | ✅ Yes | ✅ Comfort | ✅ Yes | Good for presence-based comfort |
| Door → Lock → Light | ⚠️ Maybe | ❌ Should be security | 🤷 Unsure | Light seems out of place |

---

## Success Metrics

| Metric | Target | Measured | Status |
|--------|--------|----------|--------|
| **Precision** | ≥80% | ___% | ___ |
| **Recall** | ≥70% | ___% | ___ |
| **F1 Score** | ≥75% | ___% | ___ |
| **Manual Approval** | ≥75% | ___% | ___ |
| **Performance (20 dev)** | <5s | ___s | ___ |
| **Memory (20 dev)** | <500MB | ___MB | ___ |

---

## Deployment Checklist

- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Performance benchmarks meet targets
- [ ] Accuracy metrics meet targets
- [ ] Manual review completed
- [ ] Documentation updated
- [ ] API endpoint tested
- [ ] Health dashboard integration tested
- [ ] Production environment configured
- [ ] Monitoring and alerts configured

---

**Created:** October 19, 2025  
**Status:** Proposed

