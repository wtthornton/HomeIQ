# Story 85.8 -- Configuration & Config Manager Unit Tests

<!-- docsmcp:start:user-story -->

> **As a** platform engineer, **I want** unit tests covering configuration loading and management, **so that** environment variable parsing, secret handling, and config overrides work correctly

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** S

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that config.py and config_manager.py have unit tests verifying settings construction from environment variables, secret field handling, default values, and configuration storage/retrieval — currently at zero test coverage.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

**config.py** — Defines `Settings` (extends BaseServiceSettings) with all data-api configuration: database URLs, API keys (SecretStr), InfluxDB settings, feature flags. Loaded from environment variables.

**config_manager.py** — Runtime configuration management — stores/retrieves config values, handles overrides.

Configuration bugs are notoriously hard to debug in production. Unit tests here prevent misconfigured deployments.

See [Epic 85](epic-85-data-api-line-coverage.md) for project context.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/core-platform/data-api/src/config.py`
- `domains/core-platform/data-api/src/config_manager.py`
- `domains/core-platform/data-api/tests/test_config_unit.py` (new)

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Read config.py and map all settings fields and their types
- [ ] Write tests for Settings construction with all env vars set
- [ ] Write tests for Settings with missing optional env vars (defaults applied)
- [ ] Write tests for SecretStr fields (api keys) — `.get_secret_value()` works, str() is masked
- [ ] Write tests for invalid env var values (wrong types, out-of-range)
- [ ] Read config_manager.py and map CRUD operations
- [ ] Write tests for config storage and retrieval
- [ ] Write tests for config override precedence
- [ ] Write tests for config with missing/empty values
- [ ] Verify all tests pass: `pytest tests/test_config_unit.py -v`

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] config.py has 4+ tests covering env var parsing and defaults
- [ ] SecretStr masking verified
- [ ] config_manager.py has 4+ tests covering storage/retrieval/overrides
- [ ] All tests use `monkeypatch.setenv` — no real env var pollution

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 85](epic-85-data-api-line-coverage.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_settings_all_env_vars` -- All env vars set produces valid Settings
2. `test_settings_defaults` -- Missing optional vars use defaults
3. `test_settings_secret_str_masked` -- SecretStr fields masked in str()
4. `test_settings_secret_str_value` -- SecretStr `.get_secret_value()` returns real value
5. `test_settings_invalid_type` -- Invalid env var type raises ValidationError
6. `test_config_manager_store_retrieve` -- Store value and retrieve it
7. `test_config_manager_override` -- Override takes precedence over default
8. `test_config_manager_missing_key` -- Missing key returns None or default

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Use `monkeypatch.setenv()` to set env vars in tests — never modify `os.environ` directly
- Pydantic BaseSettings may cache — ensure each test constructs a fresh Settings instance
- SecretStr fields: `DATA_API_KEY`, `INFLUXDB_TOKEN`, `DATABASE_URL`

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- None

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Standalone config modules
- [x] **N**egotiable -- Test cases adjustable based on actual settings fields
- [x] **V**aluable -- Prevents misconfigured deployments
- [x] **E**stimable -- Small scope, well-defined behavior
- [x] **S**mall -- 2 points, quick session
- [x] **T**estable -- Env var injection via monkeypatch

<!-- docsmcp:end:invest -->
