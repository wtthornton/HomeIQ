# Capability Parsing Improvement Plan

**Status:** 📋 Ready for Review  
**Date:** January 2025  
**Priority:** Medium  
**Effort:** 8-12 hours  
**Impact:** High (maintainability + future-proofing)

---

## Executive Summary

**Current Problem:** Hardcoded `elif` chains for capability parsing are unmaintainable and only support 5 domains.

**Proposed Solution:** Parse Home Assistant's `supported_features` bitmask using official HA constants (no hardcoding).

**Outcome:** Eliminates 200+ lines of hardcoded logic, supports ALL HA domains automatically.

---

## Current State Analysis

### What We Have Today

**Location:** `services/ai-automation-service/src/clients/data_api_client.py`

**Current Implementation:**
```python
def _parse_capabilities(self, entity_id: str, entity_data: Dict) -> Dict:
    domain = entity_data.get('domain', 'unknown')
    
    # Hardcoded if/elif chain (❌ PROBLEM)
    if domain == 'light':
        return self._parse_light_capabilities(attributes)
    elif domain == 'climate':
        return self._parse_climate_capabilities(attributes)
    elif domain == 'cover':
        return self._parse_cover_capabilities(attributes)
    elif domain == 'fan':
        return self._parse_fan_capabilities(attributes)
    elif domain == 'switch':
        return self._parse_switch_capabilities(attributes)
    else:
        # Generic fallback (limited)
        return {'supported_features': {'on_off': True}}
```

**Issues:**
1. ❌ Only supports 5 domains (light, climate, cover, fan, switch)
2. ❌ Manual attribute checking per domain (100+ lines of elif logic)
3. ❌ Doesn't work for: binary_sensor, sensor, camera, lock, media_player, etc.
4. ❌ Breaks when new HA integrations are added
5. ❌ Requires code changes for every new domain type
6. ❌ Duplicates logic that HA already provides

**Lines of Code:** ~200 lines of hardcoded logic

---

## Proposed Solution: supported_features Bitmask

### High-Level Approach

**Core Concept:** Use HA's built-in `supported_features` bitmask that exists in entity attributes.

**Data Source:** `GET /api/states` or `WebSocket: get_states`

**Key Insight:** Every HA entity already includes a `supported_features` bitmask in its attributes. This is the official, future-proof way to determine capabilities.

### Example: What HA Already Provides

```json
{
  "entity_id": "light.kitchen",
  "state": "on",
  "attributes": {
    "supported_features": 147,  // ← BITMASK (this is the key!)
    "brightness": 128,
    "rgb_color": [255, 0, 0],
    "color_temp": 400
  }
}
```

**Bitmask 147 decodes to:**
- `1` (bit 0): SUPPORT_BRIGHTNESS
- `2` (bit 1): SUPPORT_COLOR_TEMP
- `16` (bit 4): SUPPORT_COLOR
- `128` (bit 7): SUPPORT_TRANSITION
- **Total:** 147 = ALL SUPPORTED FEATURES

### How We Parse It (No Hardcoding!)

**Old Way (Hardcoded):**
```python
# ❌ MANUAL attribute checking
if 'brightness' in attributes:
    features['brightness'] = True
if 'rgb_color' in attributes:
    features['rgb_color'] = True
# ... 50+ more lines
```

**New Way (Bitmask):**
```python
# ✅ USE HA CONSTANTS
from homeassistant.components.light import LightEntityFeature

def parse_supported_features(bitmask: int) -> Dict:
    return {
        'brightness': bool(bitmask & LightEntityFeature.BRIGHTNESS),
        'color_temp': bool(bitmask & LightEntityFeature.COLOR_TEMP),
        'rgb_color': bool(bitmask & LightEntityFeature.RGB_COLOR),
        'flash': bool(bitmask & LightEntityFeature.FLASH),
        'transition': bool(bitmask & LightEntityFeature.TRANSITION),
        # ... all from constants, no hardcoding!
    }
```

---

## Implementation Plan

### Phase 1: Research & Setup (2 hours)

**Tasks:**
1. ✅ Document HA `supported_features` bitmask constants per domain
2. ✅ Research: `homeassistant.components.light.LightEntityFeature`
3. ✅ Research: `homeassistant.components.climate.ClimateEntityFeature`
4. ✅ Research: `homeassistant.components.cover.CoverEntityFeature`
5. ✅ Research: Other domain constants
6. ✅ Create reference mapping table

**Deliverables:**
- `docs/architecture/supported-features-reference.md` (constants mapping)
- Test dataset with real entity responses

**Tools:**
- Context7 KB research
- Home Assistant developer docs
- Live HA instance testing

---

### Phase 2: Core Implementation (4 hours)

**Tasks:**
1. Create `BitmaskCapabilityParser` class
2. Implement bitmask parsing logic per domain
3. Add feature description mapping
4. Add friendly capability text generation
5. Implement fallback for domains without constants

**Key Components:**
```
services/ai-automation-service/src/clients/
└── capability_parsers/
    ├── __init__.py
    ├── bitmask_parser.py         # ✅ NEW: Core parser
    ├── feature_mapper.py         # ✅ NEW: Feature→text mapping
    └── constants.py                # ✅ NEW: HA constants (imported)
```

**Expected Structure:**
```python
class BitmaskCapabilityParser:
    """Parse HA supported_features bitmask into capabilities."""
    
    DOMAIN_CONSTANTS = {
        'light': LightEntityFeature,
        'climate': ClimateEntityFeature,
        'cover': CoverEntityFeature,
        'fan': FanEntityFeature,
        # ... etc
    }
    
    def parse(self, domain: str, supported_features: int) -> Dict:
        """Parse bitmask into structured capabilities."""
        
    def get_friendly_descriptions(self, domain: str, features: Dict) -> List[str]:
        """Generate human-readable capability descriptions."""
```

**Testing:**
- Unit tests per domain
- Mock entity responses
- Edge cases (missing features, unknown domains)

---

### Phase 3: Integration (2 hours)

**Tasks:**
1. Update `DataAPIClient._parse_capabilities()` to use new parser
2. Remove hardcoded `_parse_light_capabilities()` methods
3. Remove hardcoded `_parse_climate_capabilities()` methods
4. Remove hardcoded `_parse_cover_capabilities()` methods
5. Remove hardcoded `_parse_fan_capabilities()` methods
6. Remove hardcoded `_parse_switch_capabilities()` methods
7. Add migration path for existing code

**File Changes:**
```
services/ai-automation-service/src/clients/
└── data_api_client.py  # UPDATE: Remove elif chain, call new parser
```

**Before:**
```python
# 200 lines of hardcoded logic
if domain == 'light':
    return self._parse_light_capabilities(attributes)  # 50 lines
elif domain == 'climate':
    return self._parse_climate_capabilities(attributes)  # 40 lines
# ... etc
```

**After:**
```python
# 5 lines total
parser = BitmaskCapabilityParser()
return parser.parse_capabilities(
    domain=domain,
    supported_features=attributes.get('supported_features', 0),
    attributes=attributes
)
```

---

### Phase 4: Testing & Validation (2 hours)

**Test Scenarios:**

**Unit Tests:**
- ✅ Parse light with full feature set (bitmask 255)
- ✅ Parse light with minimal features (bitmask 1)
- ✅ Parse climate entity
- ✅ Parse cover entity
- ✅ Parse fan entity
- ✅ Parse switch entity
- ✅ Handle unknown domain gracefully
- ✅ Handle missing supported_features attribute
- ✅ Friendly description generation

**Integration Tests:**
- ✅ End-to-end: Query capabilities for real HA entities
- ✅ Compare old vs new parser outputs
- ✅ Verify suggestion generation still works
- ✅ Test with entities from multiple domains
- ✅ Test with custom/integration entities

**Test Data:**
```python
# Real HA entity responses
test_cases = [
    {
        'entity_id': 'light.kitchen',
        'supported_features': 147,
        'expected': ['brightness', 'color_temp', 'rgb_color', 'transition']
    },
    {
        'entity_id': 'climate.thermostat',
        'supported_features': 123,
        'expected': ['temperature', 'hvac_mode', 'fan_mode']
    },
    # ... 10+ test cases
]
```

---

### Phase 5: Documentation & Rollout (2 hours)

**Tasks:**
1. Update architecture documentation
2. Add inline code comments
3. Create migration guide
4. Update API documentation
5. Monitor for issues (1 week)

**Documentation Updates:**
- `docs/architecture/capability-parsing.md` (new)
- Update `ai-automation-suggestion-call-tree.md`
- Update README

**Rollout Strategy:**
- Feature flag: `USE_BITMASK_PARSER=true`
- Run in parallel with old parser for 1 week
- Compare outputs automatically
- Gradual rollout to 100%
- Deprecate old parser after validation

---

## Success Criteria

### Quantitative
- ✅ Remove 200+ lines of hardcoded logic
- ✅ Support ALL HA domains (not just 5)
- ✅ Zero regression in existing functionality
- ✅ 100% test coverage for new parser
- ✅ Response time < 50ms (same or better)

### Qualitative
- ✅ No more domain-specific elif chains
- ✅ Self-documenting code (uses HA constants)
- ✅ Future-proof (new integrations work automatically)
- ✅ Easier to maintain (no hardcoded logic)
- ✅ Better error messages

---

## Risk Analysis

### Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| HA constants not available | High | Low | Fallback to manual parsing |
| Bitmask parsing breaks | Medium | Low | Comprehensive unit tests |
| Performance regression | Low | Very Low | Cache results if needed |
| Integration breaking | High | Low | Feature flag + parallel run |
| Unknown domains fail | Low | Medium | Generic fallback parser |

**Risk Level:** 🟢 LOW

---

## Dependencies

### External
- ✅ Home Assistant API (`/api/states`)
- ✅ WebSocket access to HA
- ✅ HA constants library (comes with integration)

### Internal
- ✅ `DataAPIClient` refactoring
- ✅ Test data from real HA instance
- ✅ Current parser as baseline reference

---

## Timeline

| Phase | Duration | Dependencies | Output |
|-------|----------|--------------|--------|
| 1. Research | 2 hours | None | Reference docs, test data |
| 2. Implementation | 4 hours | Phase 1 | Core parser, tests |
| 3. Integration | 2 hours | Phase 2 | Updated DataAPIClient |
| 4. Testing | 2 hours | Phase 3 | Test suite, validation |
| 5. Rollout | 2 hours | Phase 4 | Documentation, deployment |

**Total:** 12 hours estimated (8-16 hours depending on complexity)

---

## Alternative Approaches Considered

| Approach | Pros | Cons | Score |
|----------|------|------|-------|
| **Option 1: Bitmask (SELECTED)** | • Standard approach<br>• Future-proof<br>• No hardcoding | • Requires HA constants | **30/30** |
| Option 2: Service Schema Caching | • Self-documenting<br>• Complete params | • Requires caching<br>• Less real-time | 27/30 |
| Option 3: Attributes Parsing | • Simple to understand | • Still needs mapping<br>• Less structured | 23/30 |
| Option 4: Registry Metadata | • Domain info included | • Missing attributes<br>• Less detailed | 22/30 |
| Option 5: Hybrid | • Most complete | • More complex | 26/30 |

---

## Key Decisions Needed

1. **Constants Import:** Do we add `homeassistant` as a dependency or reimplement constants?
   - **Recommendation:** Import HA constants (standard approach)

2. **Fallback Strategy:** What do we do for domains without constants?
   - **Recommendation:** Generic attribute parsing with friendly messages

3. **Performance:** Do we need caching?
   - **Recommendation:** No, entity-specific data is lightweight

4. **Migration Path:** Keep old parser for compatibility?
   - **Recommendation:** Feature flag, remove after validation

---

## Open Questions

1. Are we accessing HA constants directly or importing them?
2. Should we support custom domains not in HA core?
3. Do we need backward compatibility with old parser?
4. What's the minimum HA version requirement?

---

## Next Steps

1. **Review this plan** (awaiting approval)
2. **Research HA constants** (gather all domain constants)
3. **Create test cases** (real entity data)
4. **Begin implementation** (Phase 1-2)
5. **Validate & rollout** (Phase 3-5)

---

## References

- Home Assistant Developer Docs: https://developers.home-assistant.io
- Context7 Cache: `docs/kb/context7-cache/libraries/homeassistant/docs.md`
- Current Implementation: `services/ai-automation-service/src/clients/data_api_client.py`
- Architecture: `docs/architecture/ai-automation-suggestion-call-tree.md`

---

**Status:** 📋 Ready for Review  
**Owner:** Development Team  
**Approver:** Pending Review  
**Estimated Completion:** 1-2 weeks

