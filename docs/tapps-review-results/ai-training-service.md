# TAPPS Code Quality Review: ai-training-service

**Date:** 2026-02-22
**Preset:** standard (gate threshold: 70.0)
**Reviewer:** tapps-mcp via Claude

## Summary

| Metric | Value |
|--------|-------|
| Total Python files | 27 (22 substantive + 5 `__init__.py`) |
| Files passing gate | 22/22 |
| Files failing gate | 0/22 |
| Security issues | 1 (informational, acceptable for Docker service) |

## File Results (Post-Fix)

### Core Service Files (`src/`)

| File | Score | Gate | Lint Issues | Notes |
|------|-------|------|-------------|-------|
| `src/config.py` | 100 | PASS | 0 | Fixed: W293 (8 instances) |
| `src/main.py` | 70 | PASS | 6 | ARG001, W293; B104 security (Docker) |
| `src/api/health_router.py` | 100 | PASS | 0 | Fixed: I001, F401 (Response, text), W293 |
| `src/api/training_router.py` | 100 | PASS | 0 | Fixed: B904, W293 (11 instances) |
| `src/crud/training.py` | 100 | PASS | 0 | Fixed: W293 (16 instances) |
| `src/database/models.py` | 95 | PASS | 1 (I001) | Minor import sorting |

### Training Module Files (`src/training/`)

| File | Score | Gate | Lint Issues | Notes |
|------|-------|------|-------------|-------|
| `synthetic_area_generator.py` | 100 | PASS | 0 | Fixed: UP035, UP006, W293 and more |
| `synthetic_calendar_generator.py` | 85 | PASS | 3 | Fixed most; C408 remain |
| `synthetic_carbon_intensity_generator.py` | 100 | PASS | 0 | Fixed: F541, ARG002 (5), UP035, W293 |
| `synthetic_correlation_engine.py` | 100 | PASS | 0 | Fixed: UP035, UP006, W293 |
| `synthetic_device_generator.py` | 85 | PASS | 3 | Fixed most; minor style remain |
| `synthetic_electricity_pricing_generator.py` | 95 | PASS | 1 | Fixed: ARG002 (6), SIM102, UP035, W293 |
| `synthetic_event_generator.py` | 100 | PASS | 0 | Fixed: UP035, W293 |
| `synthetic_external_data_generator.py` | 100 | PASS | 0 | Fixed: UP035, UP006, W293 |
| `synthetic_home_generator.py` | 80 | PASS | 4 | Fixed: B007 (2), UP035, W293 |
| `synthetic_home_ha_loader.py` | 85 | PASS | 3 | Fixed most; minor style remain |
| `synthetic_home_openai_generator.py` | 90 | PASS | 2 | Fixed most; minor remain |
| `synthetic_home_yaml_generator.py` | 100 | PASS | 0 | Fixed: UP035, UP006, W293 |
| `synthetic_weather_generator.py` | 100 | PASS | 0 | Fixed: F541, ARG002, UP035, W293 |

### Training Scripts (`scripts/`)

| File | Score | Gate | Lint Issues | Notes |
|------|-------|------|-------------|-------|
| `train_gnn_synergy.py` | 70 | PASS | 1 | Fixed: UP035, W293 |
| `train_home_type_classifier.py` | 85 | PASS | 3 | Fixed: UP035, UP006, W293 |
| `train_soft_prompt.py` | 95 | PASS | 1 | Fixed: UP035, W293 |

## Fixes Applied

### Common patterns fixed across all files:
1. **W293** - Removed trailing whitespace from blank lines (hundreds of instances)
2. **UP035/UP006** - Replaced deprecated `typing.Dict`/`typing.List`/`typing.Optional` with modern `dict`/`list`/`X | None`
3. **UP045** - Replaced `Optional[X]` with `X | None` syntax
4. **F401** - Removed unused imports (`fastapi.Response`, `sqlalchemy.text`)
5. **I001** - Fixed import block sorting
6. **B904** - Added `from None` to `raise` in except clause (training_router.py)
7. **B007** - Prefixed unused loop variables with underscore (synthetic_home_generator.py)
8. **F541** - Replaced f-strings without placeholders with plain strings
9. **ARG002** - Annotated intentionally unused method arguments with `# noqa: ARG002`
10. **SIM102** - Annotated intentional nested `if` with `# noqa: SIM102`

## Pre-Fix Scores (Selected)

| File | Before | After | Improvement |
|------|--------|-------|-------------|
| `config.py` | 60 | 100 | +40 |
| `health_router.py` | 20 | 100 | +80 |
| `training_router.py` | 40 | 100 | +60 |
| `crud/training.py` | 20 | 100 | +80 |
| `synthetic_carbon_intensity_generator.py` | 0 | 100 | +100 |
| `synthetic_electricity_pricing_generator.py` | 0 | 95 | +95 |
| `synthetic_weather_generator.py` | 0 | 100 | +100 |
| `synthetic_home_generator.py` | 0 | 80 | +80 |
| `synthetic_calendar_generator.py` | 0 | 85 | +85 |

## Quality Assessment

The ai-training-service had the most files (27) and the highest number of initial lint issues (900+) of any reviewed service, primarily due to consistent use of deprecated typing patterns and trailing whitespace across the large training module. After automated ruff fixes and targeted manual corrections, all 22 substantive files now pass the quality gate. The training module files are data science/ML code generators with inherently high complexity but clean lint profiles after the fixes.
