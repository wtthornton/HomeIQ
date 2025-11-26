# Story 35.2: Correlation Engine Foundation

**Story ID:** 35.2  
**Epic:** 35 - External Data Integration & Correlation  
**Status:** Draft  
**Priority:** P0  
**Story Points:** 4  
**Estimated Effort:** 3-4 hours  
**Depends on:** Story 35.1, Epic 33 & 34

---

## Story Description

Create correlation engine class, implement weather → HVAC correlation rules, and implement carbon/pricing → energy device correlation rules.

## Acceptance Criteria

- [ ] `SyntheticCorrelationEngine` class created
- [ ] Weather → HVAC correlation rules implemented
- [ ] Carbon/Pricing → Energy device correlation rules implemented
- [ ] Rule-based validation (lightweight, no ML)
- [ ] NUC-optimized (<100ms per home)

## Technical Requirements

```python
class SyntheticCorrelationEngine:
    """
    Rule-based correlation engine (lightweight, NUC-optimized).
    
    Validates relationships between external data and device events.
    """
    
    def validate_weather_hvac_correlation(
        self,
        weather_data: list[dict],
        hvac_events: list[dict]
    ) -> bool:
        """Validate weather-HVAC correlations"""
        # Rule-based validation
        pass
    
    def validate_energy_correlation(
        self,
        carbon_data: list[dict],
        pricing_data: list[dict],
        energy_events: list[dict]
    ) -> bool:
        """Validate carbon/pricing-energy device correlations"""
        # Rule-based validation
        pass
```

## Implementation Tasks

- [ ] Create correlation engine class
- [ ] Implement weather-HVAC rules
- [ ] Implement energy device rules
- [ ] Add validation logic
- [ ] Create unit tests

## Definition of Done

- [ ] Correlation engine created
- [ ] Weather-HVAC rules implemented
- [ ] Energy device rules implemented
- [ ] All tests passing

---

**Created**: November 25, 2025

