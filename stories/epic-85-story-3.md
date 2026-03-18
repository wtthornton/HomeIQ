# Story 85.3 -- Capability Discovery & Setup Assistant Unit Tests

<!-- docsmcp:start:user-story -->

> **As a** platform engineer, **I want** unit tests covering capability discovery and setup assistant modules, **so that** device onboarding features have verified logic for capability detection and setup guidance

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that capability_discovery.py (~70 LOC) and setup_assistant.py (~115 LOC) have unit tests verifying capability detection from entity attributes and setup guidance generation — both currently at zero test coverage.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

**capability_discovery.py** — Detects device capabilities from entity attributes (e.g., a light with `brightness` attribute has dimming capability). Maps entity domains to capability sets.

**setup_assistant.py** — Generates setup guidance for devices — configuration suggestions, integration recommendations, best practices based on device type and capabilities.

Both are small, pure-logic modules with no external I/O dependencies. High value-per-line for testing.

See [Epic 85](epic-85-data-api-line-coverage.md) for project context.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/core-platform/data-api/src/services/capability_discovery.py`
- `domains/core-platform/data-api/src/services/setup_assistant.py`
- `domains/core-platform/data-api/tests/test_capability_discovery_unit.py` (new)
- `domains/core-platform/data-api/tests/test_setup_assistant_unit.py` (new)

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Read capability_discovery.py and map all capability detection rules
- [ ] Write tests for light entity capability detection (brightness, color_temp, rgb)
- [ ] Write tests for climate entity capability detection (temperature, humidity, hvac_mode)
- [ ] Write tests for sensor entity capability mapping
- [ ] Write tests for entity with no recognizable capabilities
- [ ] Write tests for multi-capability entity
- [ ] Read setup_assistant.py and map guidance generation logic
- [ ] Write tests for setup guidance — light device type
- [ ] Write tests for setup guidance — climate device type
- [ ] Write tests for setup guidance — unknown device type (generic guidance)
- [ ] Write tests for configuration suggestions based on discovered capabilities
- [ ] Verify all tests pass: `pytest tests/test_capability_discovery_unit.py tests/test_setup_assistant_unit.py -v`

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] capability_discovery.py has 5+ unit tests covering all capability detection paths
- [ ] setup_assistant.py has 5+ unit tests covering guidance generation
- [ ] Edge cases tested (empty attributes, unknown domains, null values)
- [ ] All tests pass without external services

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 85](epic-85-data-api-line-coverage.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_discover_light_capabilities` -- Light with brightness has dimming capability
2. `test_discover_climate_capabilities` -- Climate entity has temperature/humidity capabilities
3. `test_discover_sensor_capabilities` -- Sensor mapped to monitoring capability
4. `test_discover_no_capabilities` -- Entity with unrecognized attributes returns empty set
5. `test_discover_multi_capability` -- Entity with multiple attributes returns full capability set
6. `test_setup_guidance_light` -- Light device gets appropriate setup guidance
7. `test_setup_guidance_climate` -- Climate device gets HVAC-specific recommendations
8. `test_setup_guidance_unknown` -- Unknown device type gets generic guidance
9. `test_setup_config_suggestions` -- Suggestions match discovered capabilities
10. `test_setup_guidance_empty_capabilities` -- No capabilities produces minimal guidance

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Both modules are pure functions with no side effects — ideal for parametrized tests
- Consider `@pytest.mark.parametrize` for domain/capability matrix testing

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- None

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Fully standalone
- [x] **N**egotiable -- Test cases adjustable based on actual capability rules
- [x] **V**aluable -- Protects device onboarding features
- [x] **E**stimable -- Small scope: 2 files, ~185 LOC
- [x] **S**mall -- 3 points, half-session
- [x] **T**estable -- Pure functions, easy to verify

<!-- docsmcp:end:invest -->
