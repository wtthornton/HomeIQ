# Story 46.1: Synthetic Device Data Generator

**Story ID:** 46.1  
**Epic:** 46 (Enhanced ML Training Data and Nightly Training Automation)  
**Status:** 📋 Ready for Development  
**Priority:** P0 (Critical for Alpha)  
**Story Points:** 5  
**Complexity:** Medium  
**Estimated Effort:** 4-5 hours

---

## Story Description

Create a **template-based synthetic device data generator** that produces realistic device metrics with behavior patterns, failure scenarios, and temporal patterns. This generator will enable high-quality initial training of Device Intelligence models **before alpha release** (pre-release training only, not ongoing). Follows the proven template-based pattern from `synthetic_home_generator.py` (no LLM/API calls, zero cost, fast generation).

## User Story

**As a** system administrator preparing for alpha release  
**I want** high-quality synthetic device data for initial model training  
**So that** alpha users receive working models immediately without waiting for real data collection

## Acceptance Criteria

### AC1: Template-Based Synthetic Device Data Generator Implementation
- [ ] Create `synthetic_device_generator.py` module following `synthetic_home_generator.py` pattern
- [ ] **Template-based generation** (no LLM/API calls, zero cost)
- [ ] Generate 1000+ realistic device training samples
- [ ] Support diverse device types (sensors, switches, lights, climate, security, etc.)
- [ ] Include realistic behavior patterns (usage cycles, degradation over time)
- [ ] Generate failure scenarios (high error rates, low battery, connection issues, slow response)
- [ ] Include temporal patterns (daily cycles, weekly patterns, seasonal variations)
- [ ] Device aging simulation (progressive degradation)
- [ ] Configurable generation parameters (device count, time range, failure rate)
- [ ] **NUC-optimized**: Fast generation (<30 seconds for 1000 samples)

### AC2: Realistic Device Behavior Patterns
- [ ] Usage frequency patterns (high-usage vs low-usage devices)
- [ ] Battery degradation over time (for battery-powered devices)
- [ ] Signal strength variations (WiFi/Zigbee devices)
- [ ] Response time patterns (normal vs degraded)
- [ ] Error rate patterns (stable vs problematic devices)
- [ ] Connection stability patterns (stable vs unstable)
- [ ] Temperature/humidity patterns (for climate devices)

### AC3: Failure Scenario Generation
- [ ] Progressive failure (gradual degradation)
- [ ] Sudden failure (immediate issues)
- [ ] Intermittent failures (unstable behavior)
- [ ] Battery depletion scenarios
- [ ] Network connectivity issues
- [ ] High error rate scenarios
- [ ] Slow response time scenarios

### AC4: Data Format Compatibility
- [ ] Output format matches `_collect_training_data()` return format
- [ ] Compatible with existing `train_models()` function
- [ ] Includes all required feature columns:
  - `response_time`, `error_rate`, `battery_level`
  - `signal_strength`, `usage_frequency`, `temperature`
  - `humidity`, `uptime_hours`, `restart_count`
  - `connection_drops`, `data_transfer_rate`
- [ ] Includes device_id and timestamp fields
- [ ] Valid data types and ranges for all fields

### AC5: Integration with Training Pipeline
- [ ] Can be called from `prepare_for_production.py` for **pre-release initial training**
- [ ] Can be used standalone for testing
- [ ] Integrates with `PredictiveAnalyticsEngine.train_models()`
- [ ] Supports same data format as database queries
- [ ] Can generate data for specific time ranges
- [ ] **Not used in production** - only for initial model training before alpha release

### AC6: Configuration and Documentation
- [ ] Command-line interface for standalone generation
- [ ] Configurable parameters (device count, time range, failure rate)
- [ ] Documentation with usage examples
- [ ] Code comments explaining generation logic
- [ ] Examples of generated data patterns

## Technical Requirements

### New File Structure

```
services/device-intelligence-service/
├── src/
│   └── training/
│       └── synthetic_device_generator.py  (NEW)
├── scripts/
│   └── generate_synthetic_devices.py  (NEW - optional CLI wrapper)
└── docs/
    └── SYNTHETIC_DEVICE_DATA_GUIDE.md  (NEW)
```

### Implementation Approach

**Pattern Reference:** Follow `services/ai-automation-service/src/training/synthetic_home_generator.py`:
- Template-based generation (predefined distributions, no API calls)
- Fast, deterministic generation
- Realistic patterns using statistical distributions
- Configurable parameters

**Device Type Templates:**
- Sensor devices (motion, temperature, humidity)
- Switch devices (light switches, outlets)
- Light devices (smart bulbs, dimmers)
- Climate devices (thermostats, HVAC)
- Security devices (door sensors, cameras)
- Battery-powered devices (sensors, locks)

**Realistic Patterns:**
- Daily usage cycles (morning/evening peaks)
- Weekly patterns (weekday vs weekend)
- Seasonal variations (temperature, humidity)
- Device aging (gradual degradation)
- Failure modes (battery depletion, network issues)

**Generation Logic (Template-Based):**
```python
class SyntheticDeviceGenerator:
    """
    Generate synthetic device metrics using template-based approach.
    
    Follows synthetic_home_generator.py pattern:
    - Template-based (no LLM/API calls)
    - Predefined distributions and templates
    - Fast generation (<30 seconds for 1000 samples)
    - Realistic patterns using statistical distributions
    """
    
    # Device type templates (similar to HOME_TYPE_DISTRIBUTION pattern)
    DEVICE_TYPE_DISTRIBUTION = {
        'sensor': 30,
        'switch': 20,
        'light': 15,
        'climate': 10,
        # ... etc
    }
    
    def generate_device_metrics(
        self,
        device_id: str,
        device_type: str,
        days: int = 90,
        failure_scenario: str | None = None
    ) -> list[dict]:
        """Generate realistic device metrics over time (template-based)."""
        # Use predefined templates and distributions
        # Generate base patterns (daily cycles, weekly patterns)
        # Add device-specific variations
        # Include failure scenarios if specified
        # Return list of metric dictionaries
```

### Data Quality Requirements

**Realistic Distributions:**
- Not just random numbers - use realistic patterns
- Correlated features (e.g., low battery → higher error rate)
- Temporal consistency (gradual changes, not random jumps)
- Device-specific characteristics (sensors vs switches)

**Failure Scenarios:**
- Progressive: Gradual degradation over time
- Sudden: Immediate failure after normal operation
- Intermittent: Unstable behavior patterns
- Battery-related: Battery depletion leading to failures

**Sample Count:**
- Minimum: 1000 samples
- Optimal: 2000+ samples
- Device diversity: 20+ unique device types
- Time range: 90-180 days of simulated data

## Testing Requirements

### Unit Tests
- [ ] Generator produces valid data format
- [ ] All required fields present
- [ ] Data types and ranges correct
- [ ] Failure scenarios generate appropriate patterns
- [ ] Temporal patterns are consistent

### Integration Tests
- [ ] Generated data works with `train_models()`
- [ ] Data format compatible with training pipeline
- [ ] Models train successfully on synthetic data
- [ ] Model quality meets thresholds (85% accuracy)

### Manual Testing
- [ ] Generate sample data and inspect patterns
- [ ] Verify realistic behavior patterns
- [ ] Test with different device types
- [ ] Verify failure scenarios

## Dependencies

**Depends on:**
- Existing `PredictiveAnalyticsEngine` training pipeline
- Feature column definitions in `predictive_analytics.py`
- `prepare_for_production.py` script structure

**Enables:**
- High-quality initial model training
- Alpha release with working models
- Story 46.3 (Enhanced Initial Training Pipeline)

## Definition of Done

- [ ] Synthetic device generator implemented
- [ ] Generates 1000+ realistic samples
- [ ] Includes diverse device types and failure scenarios
- [ ] Compatible with existing training pipeline
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Documentation complete
- [ ] Code reviewed and approved

## Related Stories

- **Story 46.3**: Enhanced Initial Training Pipeline (uses this generator)
- **Epic DI-3.3**: Predictive Analytics Engine (training infrastructure)

---

**Last Updated:** December 2025  
**Status:** 📋 Ready for Development

