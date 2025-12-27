# Story 34.1: Electricity Pricing Generator Foundation

**Story ID:** 34.1  
**Epic:** 34 - Advanced External Data Generation  
**Status:** Draft  
**Priority:** P0  
**Story Points:** 3  
**Estimated Effort:** 2-3 hours  
**Complexity:** Low  
**Depends on:** Epic 33 completion

---

## Story Description

Create the foundational `SyntheticElectricityPricingGenerator` class with pricing region profiles and basic price generation.

## User Story

**As a** training data engineer  
**I want** an electricity pricing generator with pricing region profiles  
**So that** I can generate realistic electricity pricing data for synthetic homes

## Acceptance Criteria

- [ ] `SyntheticElectricityPricingGenerator` class created
- [ ] Pricing region profiles defined (Germany Awattar, California TOU, Fixed Rate)
- [ ] Basic price generation implemented
- [ ] Prices in realistic ranges (0.10-0.50 currency/kWh)
- [ ] NUC-optimized (in-memory, <50MB)

## Technical Requirements

```python
class PricingDataPoint(BaseModel):
    timestamp: str
    price_per_kwh: float
    pricing_tier: str  # peak, off-peak, mid-peak
    region: str
    forecast: list[float] | None = None

class SyntheticElectricityPricingGenerator:
    PRICING_REGIONS = {
        'germany_awattar': {'baseline': 0.30, 'currency': 'EUR'},
        'california_tou': {'baseline': 0.25, 'currency': 'USD'},
        'fixed_rate': {'baseline': 0.15, 'currency': 'USD'}
    }
```

## Implementation Tasks

- [ ] Create class structure with Pydantic models
- [ ] Define pricing region profiles
- [ ] Implement basic price generation
- [ ] Create unit tests

## Definition of Done

- [ ] Class created
- [ ] Pricing regions defined
- [ ] Basic generation working
- [ ] All tests passing

---

**Created**: November 25, 2025

