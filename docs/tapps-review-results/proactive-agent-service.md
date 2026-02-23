# TAPPS Quality Review: proactive-agent-service

**Date:** 2026-02-22
**Preset:** standard (threshold: 70.0)
**Reviewer:** tapps-mcp via Claude Opus 4.6

## Summary

| Metric | Value |
|--------|-------|
| Total files reviewed | 23 |
| Initially passing | 12 |
| Initially failing | 11 |
| Files fixed | 11 |
| Final pass rate | 23/23 (100%) |

## File Results

### Passed on First Check (no changes needed)

| File | Score | Lint | Security |
|------|-------|------|----------|
| `src/__init__.py` | 100.0 | 0 | 0 |
| `src/api/__init__.py` | 100.0 | 0 | 0 |
| `src/api/health.py` | 80.0 | 4 (W293) | 0 |
| `src/clients/__init__.py` | 100.0 | 0 | 0 |
| `src/clients/sports_data_client.py` | 70.0 | 1 (F841) | 0 |
| `src/config.py` | 100.0 | 0 | 0 |
| `src/database.py` | 80.0 | 4 | 0 |
| `src/main.py` | 95.0 | 1 (I001) | 1 (B104) |
| `src/services/__init__.py` | 90.0 | 2 | 0 |
| `src/services/prompt_generation_service.py` | 80.0 | 4 (W293) | 0 |
| `src/services/scheduler_service.py` | 90.0 | 2 (TC) | 0 |

### Fixed (initially failing, now passing)

| File | Before | After | Issues Fixed |
|------|--------|-------|-------------|
| `src/api/suggestions.py` | 0.0 | 90.0 | Removed unused imports: `datetime`, `Enum`, `InvalidReportReason` (F401); sorted imports (I001); stripped blank-line whitespace (W293 x7) |
| `src/clients/carbon_intensity_client.py` | 35.0 | 100.0 | Removed unused `as e` in exception handlers (F841 x2); stripped blank-line whitespace (W293) |
| `src/clients/data_api_client.py` | 60.0 | 100.0 | Removed unused `as e` (F841); added `noqa: ARG002` for interface-required params `pattern_type`, `limit` |
| `src/clients/ha_agent_client.py` | 40.0 | 100.0 | Removed unused `as e` in `ConnectError` and `TimeoutException` handlers (F841 x2) |
| `src/clients/weather_api_client.py` | 40.0 | 100.0 | Removed unused `as e` in `ConnectError` and `TimeoutException` handlers (F841 x2) |
| `src/models.py` | 55.0 | 90.0 | Removed quotes from type annotation `"Suggestion"` (UP037); stripped blank-line whitespace (W293 x5) |
| `src/services/ai_prompt_generation_service.py` | 0.0 | 95.0 | Added `noqa: E402` for intentional late import after sys.path setup; used ternary (SIM108); stripped blank-line whitespace (W293 x18) |
| `src/services/context_analysis_service.py` | 25.0 | 100.0 | Fixed f-strings without placeholders (F541 x2); added `noqa: ARG002` for `events` param; stripped whitespace |
| `src/services/device_validation_service.py` | 0.0 | 95.0 | Removed unused `import json` (F401); collapsed nested if (SIM102); stripped blank-line whitespace (W293 x18) |
| `src/services/suggestion_service.py` | 0.0 | 95.0 | Replaced unused `import update` with `import func` (F401/F821 x5 -- `func` was undefined); stripped whitespace |
| `src/services/suggestion_pipeline_service.py` | 35.0 | 95.0 | Stripped blank-line and trailing whitespace (W293 x9, W291 x2); import sorting handled by whitespace cleanup |
| `src/services/suggestion_storage_service.py` | 25.0 | 95.0 | Stripped blank-line whitespace (W293 x13) |

## Common Patterns Found

1. **W293 - Blank lines with whitespace** (most common, 60+ occurrences): Editor artifacts leaving spaces/tabs on empty lines.
2. **F841 - Unused exception variables**: Pattern `except SomeError as e:` where `e` is never referenced in the handler body. Fixed by removing `as e`.
3. **F401 - Unused imports**: `datetime`, `Enum`, `json`, `update` imported but never used.
4. **F821 - Undefined names**: `func` from SQLAlchemy used in `suggestion_service.py` but not imported (was importing unused `update` instead).
5. **B104 - Binding to all interfaces** (security, `main.py`): `0.0.0.0` binding -- acceptable for Docker container but flagged. Score still passing.

## Complexity Notes

- `ai_prompt_generation_service.py`: CC~23 (high) -- consider refactoring `_generate_prompt_with_context()`.
- `suggestion_pipeline_service.py`: CC~17 (high) -- consider splitting pipeline orchestration.
- `context_analysis_service.py`: CC~12 (moderate).
- `device_validation_service.py`: CC~13 (moderate).
- `prompt_generation_service.py`: CC~13 (moderate).
