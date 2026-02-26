# Changelog

## [Unreleased] - 2026-02-26

### Added

- **infra fixes, library bumps, and proactive-agent RAG integration** (74ee779) - Bill Thornton
- **implement 5 service stubs across 4 domains** (c0c7919) - Bill Thornton
- **implement 6 stub services and wire persistent eval sinks** (88a4a31) - Bill Thornton
- **operational readiness - Alembic, monitoring, CI, backups, E2E, runbooks** (41c61dd) - Bill Thornton
- **SQLite to PostgreSQL migration + library version standardization** (8508f97) - Bill Thornton
- **Phase 1 dependency updates, Dockerfile modernization, and documentation refresh** (7066ce7) - Bill Thornton
- **complete domain architecture restructuring (Epics 1-4)** (d47f7c0) - Bill Thornton
- **service groups decomposition + cross-group resilience rollout** (6e9cf95) - Bill Thornton
- **upgrade LLM/ML model stack — OpenAI SDK 2.x, gpt-5.2-codex, library alignment** (b62f1a6) - Bill Thornton
- **feat(activity-recognition): Phase 1+2 integration and quality improvements** (78f19c4) - Bill Thornton
- **feat(ai-automation-service-new): separate plan (gpt-4o-mini) and YAML (Codex) models** (1bb834b) - Bill Thornton

### Fixed

- **switch Claude Code hooks from .sh to .ps1 for Windows compatibility** (06dfa52) - Bill Thornton
- **remove 20 files committed with literal ${workspaceFolder} path prefix** (850d47a) - Bill Thornton
- **update pytest-asyncio config for explicit loop scope across all services** (141da0d) - Bill Thornton
- **resolve data-api startup and legacy shared.* imports (Phase 1 complete)** (296ce95) - Bill Thornton
- **resolve pre-existing e2e test failures** (d1d0921) - Bill Thornton
- **OTel mock fallbacks, blueprint-suggestion Docker context, resilience E2E tests** (7d6c3e9) - Bill Thornton
- **resolve 3 deployment bugs in resilience startup and health probes** (e206790) - Bill Thornton
- **fix(ha-ai-agent): inject entity inventory, fix device-intel auth, switch to gpt-4.1** (9d9c397) - Bill Thornton
- **resolve 5 deployment bugs across data-api, ha-ai-agent, ai-pattern, smart-meter** (e4e2c8e) - Bill Thornton
- **platform-wide code quality review — 6,500+ lint fixes across 46 services** (9aae7e5) - Bill Thornton
- **fix(ai-automation-service-new): tests, schema, and OpenAI default model** (4f92f92) - Bill Thornton
- **YAML tests, deployment router, entity extraction, and validator** (34f6f50) - Bill Thornton
- **Fix activity-recognition bugs; ai-automation-service updates** (a8bbcf9) - Bill Thornton
- **fix(activity-recognition): quality gate fixes, tests, and refactors** (be3f154) - Bill Thornton
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (7e4a019) - Bill Thornton


### Added

- **implement 5 service stubs across 4 domains** (c0c7919) - Bill Thornton
- **implement 6 stub services and wire persistent eval sinks** (88a4a31) - Bill Thornton
- **operational readiness - Alembic, monitoring, CI, backups, E2E, runbooks** (41c61dd) - Bill Thornton
- **SQLite to PostgreSQL migration + library version standardization** (8508f97) - Bill Thornton
- **Phase 1 dependency updates, Dockerfile modernization, and documentation refresh** (7066ce7) - Bill Thornton
- **complete domain architecture restructuring (Epics 1-4)** (d47f7c0) - Bill Thornton
- **service groups decomposition + cross-group resilience rollout** (6e9cf95) - Bill Thornton
- **upgrade LLM/ML model stack — OpenAI SDK 2.x, gpt-5.2-codex, library alignment** (b62f1a6) - Bill Thornton
- **feat(activity-recognition): Phase 1+2 integration and quality improvements** (78f19c4) - Bill Thornton
- **feat(ai-automation-service-new): separate plan (gpt-4o-mini) and YAML (Codex) models** (1bb834b) - Bill Thornton

### Fixed

- **switch Claude Code hooks from .sh to .ps1 for Windows compatibility** (06dfa52) - Bill Thornton
- **remove 20 files committed with literal ${workspaceFolder} path prefix** (850d47a) - Bill Thornton
- **update pytest-asyncio config for explicit loop scope across all services** (141da0d) - Bill Thornton
- **resolve data-api startup and legacy shared.* imports (Phase 1 complete)** (296ce95) - Bill Thornton
- **resolve pre-existing e2e test failures** (d1d0921) - Bill Thornton
- **OTel mock fallbacks, blueprint-suggestion Docker context, resilience E2E tests** (7d6c3e9) - Bill Thornton
- **resolve 3 deployment bugs in resilience startup and health probes** (e206790) - Bill Thornton
- **fix(ha-ai-agent): inject entity inventory, fix device-intel auth, switch to gpt-4.1** (9d9c397) - Bill Thornton
- **resolve 5 deployment bugs across data-api, ha-ai-agent, ai-pattern, smart-meter** (e4e2c8e) - Bill Thornton
- **platform-wide code quality review — 6,500+ lint fixes across 46 services** (9aae7e5) - Bill Thornton
- **fix(ai-automation-service-new): tests, schema, and OpenAI default model** (4f92f92) - Bill Thornton
- **YAML tests, deployment router, entity extraction, and validator** (34f6f50) - Bill Thornton
- **Fix activity-recognition bugs; ai-automation-service updates** (a8bbcf9) - Bill Thornton
- **fix(activity-recognition): quality gate fixes, tests, and refactors** (be3f154) - Bill Thornton
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (7e4a019) - Bill Thornton
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (624419d) - Bill Thornton


### Added

- **Phase 1 dependency updates, Dockerfile modernization, and documentation refresh** (7066ce7) - Bill Thornton
- **complete domain architecture restructuring (Epics 1-4)** (d47f7c0) - Bill Thornton
- **service groups decomposition + cross-group resilience rollout** (6e9cf95) - Bill Thornton
- **upgrade LLM/ML model stack — OpenAI SDK 2.x, gpt-5.2-codex, library alignment** (b62f1a6) - Bill Thornton
- **feat(activity-recognition): Phase 1+2 integration and quality improvements** (78f19c4) - Bill Thornton
- **feat(ai-automation-service-new): separate plan (gpt-4o-mini) and YAML (Codex) models** (1bb834b) - Bill Thornton
- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (35dccf6) - wtthornton

### Fixed

- **remove 20 files committed with literal ${workspaceFolder} path prefix** (850d47a) - Bill Thornton
- **update pytest-asyncio config for explicit loop scope across all services** (141da0d) - Bill Thornton
- **resolve data-api startup and legacy shared.* imports (Phase 1 complete)** (296ce95) - Bill Thornton
- **resolve pre-existing e2e test failures** (d1d0921) - Bill Thornton
- **OTel mock fallbacks, blueprint-suggestion Docker context, resilience E2E tests** (7d6c3e9) - Bill Thornton
- **resolve 3 deployment bugs in resilience startup and health probes** (e206790) - Bill Thornton
- **fix(ha-ai-agent): inject entity inventory, fix device-intel auth, switch to gpt-4.1** (9d9c397) - Bill Thornton
- **resolve 5 deployment bugs across data-api, ha-ai-agent, ai-pattern, smart-meter** (e4e2c8e) - Bill Thornton
- **platform-wide code quality review — 6,500+ lint fixes across 46 services** (9aae7e5) - Bill Thornton
- **fix(ai-automation-service-new): tests, schema, and OpenAI default model** (4f92f92) - Bill Thornton
- **YAML tests, deployment router, entity extraction, and validator** (34f6f50) - Bill Thornton
- **Fix activity-recognition bugs; ai-automation-service updates** (a8bbcf9) - Bill Thornton
- **fix(activity-recognition): quality gate fixes, tests, and refactors** (be3f154) - Bill Thornton
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (7e4a019) - Bill Thornton
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (624419d) - Bill Thornton
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (998501c) - Bill Thornton
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (e0099bb) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (93ab49f) - Bill Thornton


### Added

- **Phase 1 dependency updates, Dockerfile modernization, and documentation refresh** (7066ce7) - Bill Thornton
- **complete domain architecture restructuring (Epics 1-4)** (d47f7c0) - Bill Thornton
- **service groups decomposition + cross-group resilience rollout** (6e9cf95) - Bill Thornton
- **upgrade LLM/ML model stack — OpenAI SDK 2.x, gpt-5.2-codex, library alignment** (b62f1a6) - Bill Thornton
- **feat(activity-recognition): Phase 1+2 integration and quality improvements** (78f19c4) - Bill Thornton
- **feat(ai-automation-service-new): separate plan (gpt-4o-mini) and YAML (Codex) models** (1bb834b) - Bill Thornton
- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (35dccf6) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (a30197f) - wtthornton

### Fixed

- **resolve data-api startup and legacy shared.* imports (Phase 1 complete)** (296ce95) - Bill Thornton
- **resolve pre-existing e2e test failures** (d1d0921) - Bill Thornton
- **OTel mock fallbacks, blueprint-suggestion Docker context, resilience E2E tests** (7d6c3e9) - Bill Thornton
- **resolve 3 deployment bugs in resilience startup and health probes** (e206790) - Bill Thornton
- **fix(ha-ai-agent): inject entity inventory, fix device-intel auth, switch to gpt-4.1** (9d9c397) - Bill Thornton
- **resolve 5 deployment bugs across data-api, ha-ai-agent, ai-pattern, smart-meter** (e4e2c8e) - Bill Thornton
- **platform-wide code quality review — 6,500+ lint fixes across 46 services** (9aae7e5) - Bill Thornton
- **fix(ai-automation-service-new): tests, schema, and OpenAI default model** (4f92f92) - Bill Thornton
- **YAML tests, deployment router, entity extraction, and validator** (34f6f50) - Bill Thornton
- **Fix activity-recognition bugs; ai-automation-service updates** (a8bbcf9) - Bill Thornton
- **fix(activity-recognition): quality gate fixes, tests, and refactors** (be3f154) - Bill Thornton
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (7e4a019) - Bill Thornton
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (624419d) - Bill Thornton
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (998501c) - Bill Thornton
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (e0099bb) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (93ab49f) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (b6aeb25) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (3cb5415) - wtthornton


### Added

- **complete domain architecture restructuring (Epics 1-4)** (d47f7c0) - Bill Thornton
- **service groups decomposition + cross-group resilience rollout** (6e9cf95) - Bill Thornton
- **upgrade LLM/ML model stack — OpenAI SDK 2.x, gpt-5.2-codex, library alignment** (b62f1a6) - Bill Thornton
- **feat(activity-recognition): Phase 1+2 integration and quality improvements** (78f19c4) - Bill Thornton
- **feat(ai-automation-service-new): separate plan (gpt-4o-mini) and YAML (Codex) models** (1bb834b) - Bill Thornton
- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (35dccf6) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (a30197f) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (b929ef5) - wtthornton

### Fixed

- **resolve data-api startup and legacy shared.* imports (Phase 1 complete)** (296ce95) - Bill Thornton
- **resolve pre-existing e2e test failures** (d1d0921) - Bill Thornton
- **OTel mock fallbacks, blueprint-suggestion Docker context, resilience E2E tests** (7d6c3e9) - Bill Thornton
- **resolve 3 deployment bugs in resilience startup and health probes** (e206790) - Bill Thornton
- **fix(ha-ai-agent): inject entity inventory, fix device-intel auth, switch to gpt-4.1** (9d9c397) - Bill Thornton
- **resolve 5 deployment bugs across data-api, ha-ai-agent, ai-pattern, smart-meter** (e4e2c8e) - Bill Thornton
- **platform-wide code quality review — 6,500+ lint fixes across 46 services** (9aae7e5) - Bill Thornton
- **fix(ai-automation-service-new): tests, schema, and OpenAI default model** (4f92f92) - Bill Thornton
- **YAML tests, deployment router, entity extraction, and validator** (34f6f50) - Bill Thornton
- **Fix activity-recognition bugs; ai-automation-service updates** (a8bbcf9) - Bill Thornton
- **fix(activity-recognition): quality gate fixes, tests, and refactors** (be3f154) - Bill Thornton
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (7e4a019) - Bill Thornton
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (624419d) - Bill Thornton
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (998501c) - Bill Thornton
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (e0099bb) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (93ab49f) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (b6aeb25) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (3cb5415) - wtthornton


### Added

- **feat(eval): @trace_session wiring for all 4 AI agents** - proactive-agent-service, ai-automation-service-new, ai-core-service (2026-02-23)
- **feat(restructuring): complete domain architecture restructuring (Epics 1-4)** (7541d3a) - Bill Thornton
- **service groups decomposition + cross-group resilience rollout** (6e9cf95) - Bill Thornton
- **upgrade LLM/ML model stack — OpenAI SDK 2.x, gpt-5.2-codex, library alignment** (b62f1a6) - Bill Thornton
- **feat(activity-recognition): Phase 1+2 integration and quality improvements** (78f19c4) - Bill Thornton
- **feat(ai-automation-service-new): separate plan (gpt-4o-mini) and YAML (Codex) models** (1bb834b) - Bill Thornton
- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (35dccf6) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (a30197f) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (b929ef5) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (a5aefeb) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (b08a55e) - wtthornton

### Fixed

- **resolve pre-existing e2e test failures** (d1d0921) - Bill Thornton
- **OTel mock fallbacks, blueprint-suggestion Docker context, resilience E2E tests** (7d6c3e9) - Bill Thornton
- **resolve 3 deployment bugs in resilience startup and health probes** (e206790) - Bill Thornton
- **fix(ha-ai-agent): inject entity inventory, fix device-intel auth, switch to gpt-4.1** (9d9c397) - Bill Thornton
- **resolve 5 deployment bugs across data-api, ha-ai-agent, ai-pattern, smart-meter** (e4e2c8e) - Bill Thornton
- **platform-wide code quality review — 6,500+ lint fixes across 46 services** (9aae7e5) - Bill Thornton
- **fix(ai-automation-service-new): tests, schema, and OpenAI default model** (4f92f92) - Bill Thornton
- **YAML tests, deployment router, entity extraction, and validator** (34f6f50) - Bill Thornton
- **Fix activity-recognition bugs; ai-automation-service updates** (a8bbcf9) - Bill Thornton
- **fix(activity-recognition): quality gate fixes, tests, and refactors** (be3f154) - Bill Thornton
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (7e4a019) - Bill Thornton
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (624419d) - Bill Thornton
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (998501c) - Bill Thornton
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (e0099bb) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (93ab49f) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (b6aeb25) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (3cb5415) - wtthornton


### Added

- **service groups decomposition + cross-group resilience rollout** (6e9cf95) - Bill Thornton
- **upgrade LLM/ML model stack — OpenAI SDK 2.x, gpt-5.2-codex, library alignment** (b62f1a6) - Bill Thornton
- **feat(activity-recognition): Phase 1+2 integration and quality improvements** (78f19c4) - Bill Thornton
- **feat(ai-automation-service-new): separate plan (gpt-4o-mini) and YAML (Codex) models** (1bb834b) - Bill Thornton
- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (35dccf6) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (a30197f) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (b929ef5) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (a5aefeb) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (b08a55e) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (e819957) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (e74a072) - wtthornton

### Fixed

- **OTel mock fallbacks, blueprint-suggestion Docker context, resilience E2E tests** (7d6c3e9) - Bill Thornton
- **resolve 3 deployment bugs in resilience startup and health probes** (e206790) - Bill Thornton
- **fix(ha-ai-agent): inject entity inventory, fix device-intel auth, switch to gpt-4.1** (9d9c397) - Bill Thornton
- **resolve 5 deployment bugs across data-api, ha-ai-agent, ai-pattern, smart-meter** (e4e2c8e) - Bill Thornton
- **platform-wide code quality review — 6,500+ lint fixes across 46 services** (9aae7e5) - Bill Thornton
- **fix(ai-automation-service-new): tests, schema, and OpenAI default model** (4f92f92) - Bill Thornton
- **YAML tests, deployment router, entity extraction, and validator** (34f6f50) - Bill Thornton
- **Fix activity-recognition bugs; ai-automation-service updates** (a8bbcf9) - Bill Thornton
- **fix(activity-recognition): quality gate fixes, tests, and refactors** (be3f154) - Bill Thornton
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (7e4a019) - Bill Thornton
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (624419d) - Bill Thornton
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (998501c) - Bill Thornton
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (e0099bb) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (93ab49f) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (b6aeb25) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (3cb5415) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (7e360a9) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (94988a4) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (21612b6) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (4791f8a) - wtthornton

### Documentation

- **docs: update architecture docs from 6-group to 9-domain structure** (2026-02-23)
- **docs: update all epic/story files to match codebase reality** (2026-02-23)
- **docs: mark Deploy Pipeline (all 5 stories), Agent Eval (@trace_session 4/4), Activity Recognition (Story 2.2) complete** (2026-02-23)


### Added

- **feat(activity-recognition): Phase 1+2 integration and quality improvements** (78f19c4) - Bill Thornton
- **feat(ai-automation-service-new): separate plan (gpt-4o-mini) and YAML (Codex) models** (1bb834b) - Bill Thornton
- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (35dccf6) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (a30197f) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (b929ef5) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (a5aefeb) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (b08a55e) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (e819957) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (e74a072) - wtthornton

### Fixed

- **fix(ha-ai-agent): inject entity inventory, fix device-intel auth, switch to gpt-4.1** (9d9c397) - Bill Thornton
- **resolve 5 deployment bugs across data-api, ha-ai-agent, ai-pattern, smart-meter** (e4e2c8e) - Bill Thornton
- **platform-wide code quality review — 6,500+ lint fixes across 46 services** (9aae7e5) - Bill Thornton
- **fix(ai-automation-service-new): tests, schema, and OpenAI default model** (4f92f92) - Bill Thornton
- **YAML tests, deployment router, entity extraction, and validator** (34f6f50) - Bill Thornton
- **Fix activity-recognition bugs; ai-automation-service updates** (a8bbcf9) - Bill Thornton
- **fix(activity-recognition): quality gate fixes, tests, and refactors** (be3f154) - Bill Thornton
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (7e4a019) - Bill Thornton
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (624419d) - Bill Thornton
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (998501c) - Bill Thornton
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (e0099bb) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (93ab49f) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (b6aeb25) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (3cb5415) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (7e360a9) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (94988a4) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (21612b6) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (4791f8a) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (c75fe61) - wtthornton


### Added

- **feat(activity-recognition): Phase 1+2 integration and quality improvements** (78f19c4) - Bill Thornton
- **feat(ai-automation-service-new): separate plan (gpt-4o-mini) and YAML (Codex) models** (1bb834b) - Bill Thornton
- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (35dccf6) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (a30197f) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (b929ef5) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (a5aefeb) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (b08a55e) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (e819957) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (e74a072) - wtthornton

### Fixed

- **resolve 5 deployment bugs across data-api, ha-ai-agent, ai-pattern, smart-meter** (e4e2c8e) - Bill Thornton
- **platform-wide code quality review — 6,500+ lint fixes across 46 services** (9aae7e5) - Bill Thornton
- **fix(ai-automation-service-new): tests, schema, and OpenAI default model** (4f92f92) - Bill Thornton
- **YAML tests, deployment router, entity extraction, and validator** (34f6f50) - Bill Thornton
- **Fix activity-recognition bugs; ai-automation-service updates** (a8bbcf9) - Bill Thornton
- **fix(activity-recognition): quality gate fixes, tests, and refactors** (be3f154) - Bill Thornton
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (7e4a019) - Bill Thornton
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (624419d) - Bill Thornton
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (998501c) - Bill Thornton
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (e0099bb) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (93ab49f) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (b6aeb25) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (3cb5415) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (7e360a9) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (94988a4) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (21612b6) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (4791f8a) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (c75fe61) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (7d4caf3) - wtthornton


### Added

- **feat(activity-recognition): Phase 1+2 integration and quality improvements** (78f19c4) - Bill Thornton
- **feat(ai-automation-service-new): separate plan (gpt-4o-mini) and YAML (Codex) models** (1bb834b) - Bill Thornton
- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (35dccf6) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (a30197f) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (b929ef5) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (a5aefeb) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (b08a55e) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (e819957) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (e74a072) - wtthornton
- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (5acc00e) - wtthornton

### Fixed

- **platform-wide code quality review — 6,500+ lint fixes across 46 services** (9aae7e5) - Bill Thornton
- **fix(ai-automation-service-new): tests, schema, and OpenAI default model** (4f92f92) - Bill Thornton
- **YAML tests, deployment router, entity extraction, and validator** (34f6f50) - Bill Thornton
- **Fix activity-recognition bugs; ai-automation-service updates** (a8bbcf9) - Bill Thornton
- **fix(activity-recognition): quality gate fixes, tests, and refactors** (be3f154) - Bill Thornton
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (7e4a019) - Bill Thornton
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (624419d) - Bill Thornton
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (998501c) - Bill Thornton
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (e0099bb) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (93ab49f) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (b6aeb25) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (3cb5415) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (7e360a9) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (94988a4) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (21612b6) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (4791f8a) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (c75fe61) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (7d4caf3) - wtthornton


### Added

- **feat(activity-recognition): Phase 1+2 integration and quality improvements** (78f19c4) - Bill Thornton
- **feat(ai-automation-service-new): separate plan (gpt-4o-mini) and YAML (Codex) models** (1bb834b) - Bill Thornton
- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (35dccf6) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (a30197f) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (b929ef5) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (a5aefeb) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (b08a55e) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (e819957) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (e74a072) - wtthornton
- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (5acc00e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (e1ee24c) - wtthornton

### Fixed

- **fix(ai-automation-service-new): tests, schema, and OpenAI default model** (4f92f92) - Bill Thornton
- **YAML tests, deployment router, entity extraction, and validator** (34f6f50) - Bill Thornton
- **Fix activity-recognition bugs; ai-automation-service updates** (a8bbcf9) - Bill Thornton
- **fix(activity-recognition): quality gate fixes, tests, and refactors** (be3f154) - Bill Thornton
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (7e4a019) - Bill Thornton
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (624419d) - Bill Thornton
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (998501c) - Bill Thornton
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (e0099bb) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (93ab49f) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (b6aeb25) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (3cb5415) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (7e360a9) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (94988a4) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (21612b6) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (4791f8a) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (c75fe61) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (7d4caf3) - wtthornton


### Added

- **feat(ai-automation-service-new): separate plan (gpt-4o-mini) and YAML (Codex) models** (9ad4ffa) - Bill Thornton
- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (fd3bcf2) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (776d7e9) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (4d3e1c1) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (dbba879) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (0fcbb86) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (cd5dd14) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (9715cf9) - wtthornton
- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton

### Fixed

- **fix(ai-automation-service-new): tests, schema, and OpenAI default model** (a611e2b) - Bill Thornton
- **YAML tests, deployment router, entity extraction, and validator** (a7e8fb7) - Bill Thornton
- **Fix activity-recognition bugs; ai-automation-service updates** (21b9d0a) - Bill Thornton
- **fix(activity-recognition): quality gate fixes, tests, and refactors** (c66fb2c) - Bill Thornton
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (2391708) - Bill Thornton
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (70c2dae) - Bill Thornton
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (a1ffb78) - Bill Thornton
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (84ba8b9) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (777ffb9) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (1aef463) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (bc23214) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (c57e268) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (fa6fb67) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (8ac75e4) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (8346da4) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (3db7436) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton


### Added

- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (fd3bcf2) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (776d7e9) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (4d3e1c1) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (dbba879) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (0fcbb86) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (cd5dd14) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (9715cf9) - wtthornton
- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton

### Fixed

- **fix(ai-automation-service-new): tests, schema, and OpenAI default model** (a611e2b) - Bill Thornton
- **YAML tests, deployment router, entity extraction, and validator** (a7e8fb7) - Bill Thornton
- **Fix activity-recognition bugs; ai-automation-service updates** (21b9d0a) - Bill Thornton
- **fix(activity-recognition): quality gate fixes, tests, and refactors** (c66fb2c) - Bill Thornton
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (2391708) - Bill Thornton
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (70c2dae) - Bill Thornton
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (a1ffb78) - Bill Thornton
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (84ba8b9) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (777ffb9) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (1aef463) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (bc23214) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (c57e268) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (fa6fb67) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (8ac75e4) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (8346da4) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (3db7436) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton


### Added

- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (fd3bcf2) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (776d7e9) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (4d3e1c1) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (dbba879) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (0fcbb86) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (cd5dd14) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (9715cf9) - wtthornton
- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton

### Fixed

- **YAML tests, deployment router, entity extraction, and validator** (a7e8fb7) - Bill Thornton
- **Fix activity-recognition bugs; ai-automation-service updates** (21b9d0a) - Bill Thornton
- **fix(activity-recognition): quality gate fixes, tests, and refactors** (c66fb2c) - Bill Thornton
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (2391708) - Bill Thornton
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (70c2dae) - Bill Thornton
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (a1ffb78) - Bill Thornton
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (84ba8b9) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (777ffb9) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (1aef463) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (bc23214) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (c57e268) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (fa6fb67) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (8ac75e4) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (8346da4) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (3db7436) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton


### Added

- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (fd3bcf2) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (776d7e9) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (4d3e1c1) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (dbba879) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (0fcbb86) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (cd5dd14) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (9715cf9) - wtthornton
- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton

### Fixed

- **fix(activity-recognition): quality gate fixes, tests, and refactors** (c66fb2c) - Bill Thornton
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (2391708) - Bill Thornton
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (70c2dae) - Bill Thornton
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (a1ffb78) - Bill Thornton
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (84ba8b9) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (777ffb9) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (1aef463) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (bc23214) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (c57e268) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (fa6fb67) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (8ac75e4) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (8346da4) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (3db7436) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton
- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton


### Added

- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (fd3bcf2) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (776d7e9) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (4d3e1c1) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (dbba879) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (0fcbb86) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (cd5dd14) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (9715cf9) - wtthornton
- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton

### Fixed

- **fix(activity-recognition): quality gate fixes, tests, and refactors** (c66fb2c) - Bill Thornton
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (2391708) - Bill Thornton
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (70c2dae) - Bill Thornton
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (a1ffb78) - Bill Thornton
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (84ba8b9) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (777ffb9) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (1aef463) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (bc23214) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (c57e268) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (fa6fb67) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (8ac75e4) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (8346da4) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (3db7436) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton
- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton


### Added

- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (fd3bcf2) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (776d7e9) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (4d3e1c1) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (dbba879) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (0fcbb86) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (cd5dd14) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (9715cf9) - wtthornton
- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton

### Fixed

- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (2391708) - Bill Thornton
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (70c2dae) - Bill Thornton
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (a1ffb78) - Bill Thornton
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (84ba8b9) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (777ffb9) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (1aef463) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (bc23214) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (c57e268) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (fa6fb67) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (8ac75e4) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (8346da4) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (3db7436) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton
- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton


### Added

- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (fd3bcf2) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (776d7e9) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (4d3e1c1) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (dbba879) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (0fcbb86) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (cd5dd14) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (9715cf9) - wtthornton
- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton

### Fixed

- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (70c2dae) - Bill Thornton
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (a1ffb78) - Bill Thornton
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (84ba8b9) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (777ffb9) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (1aef463) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (bc23214) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (c57e268) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (fa6fb67) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (8ac75e4) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (8346da4) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (3db7436) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton
- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton


### Added

- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (fd3bcf2) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (776d7e9) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (4d3e1c1) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (dbba879) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (0fcbb86) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (cd5dd14) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (9715cf9) - wtthornton
- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton

### Fixed

- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (a1ffb78) - Bill Thornton
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (84ba8b9) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (777ffb9) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (1aef463) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (bc23214) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (c57e268) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (fa6fb67) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (8ac75e4) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (8346da4) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (3db7436) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton
- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton


### Added

- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (fd3bcf2) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (776d7e9) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (4d3e1c1) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (dbba879) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (0fcbb86) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (cd5dd14) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (9715cf9) - wtthornton
- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton

### Fixed

- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (84ba8b9) - Bill Thornton
- **resolve 10 bugs via TappsMCP and misc updates** (777ffb9) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (1aef463) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (bc23214) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (c57e268) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (fa6fb67) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (8ac75e4) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (8346da4) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (3db7436) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton
- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton
- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton


### Added

- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (fd3bcf2) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (776d7e9) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (4d3e1c1) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (dbba879) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (0fcbb86) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (cd5dd14) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (9715cf9) - wtthornton
- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton

### Fixed

- **resolve 10 bugs via TappsMCP and misc updates** (777ffb9) - Bill Thornton
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (1aef463) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (bc23214) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (c57e268) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (fa6fb67) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (8ac75e4) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (8346da4) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (3db7436) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton
- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton
- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton


### Added

- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (fd3bcf2) - wtthornton
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (776d7e9) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (4d3e1c1) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (dbba879) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (0fcbb86) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (cd5dd14) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (9715cf9) - wtthornton
- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton

### Fixed

- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (1aef463) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (bc23214) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (c57e268) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (fa6fb67) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (8ac75e4) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (8346da4) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (3db7436) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton
- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton
- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton


### Added

- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (776d7e9) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (4d3e1c1) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (dbba879) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (0fcbb86) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (cd5dd14) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (9715cf9) - wtthornton
- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton

### Fixed

- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (1aef463) - wtthornton
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (bc23214) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (c57e268) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (fa6fb67) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (8ac75e4) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (8346da4) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (3db7436) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton
- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton
- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton


### Added

- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (776d7e9) - wtthornton
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (4d3e1c1) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (dbba879) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (0fcbb86) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (cd5dd14) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (9715cf9) - wtthornton
- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton
- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton

### Fixed

- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (bc23214) - wtthornton
- **fix(deploy): end-to-end automation deployment to Home Assistant** (c57e268) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (fa6fb67) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (8ac75e4) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (8346da4) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (3db7436) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton
- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton
- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton


### Added

- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (4d3e1c1) - wtthornton
- **add automation-trace-service for HA trace + logbook ingestion** (dbba879) - wtthornton
- **feat(automation): YAML compiler + template validator live state filtering** (0fcbb86) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (cd5dd14) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (9715cf9) - wtthornton
- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton
- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton

### Fixed

- **fix(deploy): end-to-end automation deployment to Home Assistant** (c57e268) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (fa6fb67) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (8ac75e4) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (8346da4) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (3db7436) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton
- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton
- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton


### Added

- **feat(automation): YAML compiler + template validator live state filtering** (0fcbb86) - wtthornton
- **feat(deploy): deploy pipeline root cause fixes — 5/5 prompt deploy target** (cd5dd14) - wtthornton
- **feat(eval): L1 judge stability + Story 5.4 data-api integration** (9715cf9) - wtthornton
- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton
- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton

### Fixed

- **fix(deploy): end-to-end automation deployment to Home Assistant** (c57e268) - wtthornton
- **fix(eval): R5 preview exception keyword + sweep v4 results (74.2% → 95.4%)** (fa6fb67) - wtthornton
- **fix(eval): scope generated_yaml scanning to yaml_safety_check rule only** (8ac75e4) - wtthornton
- **fix(ci): add master branch to deployment workflow triggers** (8346da4) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (3db7436) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton
- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton
- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton
- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton


### Added

- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton
- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton
- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton

### Fixed

- **fix(ci): add master branch to deployment workflow triggers** (8346da4) - wtthornton
- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (3db7436) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton
- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton
- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton
- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton


### Added

- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton
- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton
- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton

### Fixed

- **fix(eval): evaluation sweep fixes — word boundaries, false positives, schema coercion** (3db7436) - wtthornton
- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton
- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton
- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton
- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton
- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton


### Added

- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton
- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton
- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton

### Fixed

- **fix(templates): HA 2024.x+ compliance — trigger/action/condition as lists** (e41d9d8) - wtthornton
- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton
- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton
- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton
- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton


### Added

- **feat(tests): add diagnostic mode, --output flag, and Unicode fixes to pipeline harness** (1beec0e) - wtthornton
- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton
- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton
- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton

### Fixed

- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton
- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton
- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton
- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton


### Added

- **feat(tests): add reusable Ask AI pipeline test harness with scoring & diagnostics** (061ac7d) - wtthornton
- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton
- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton
- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton

### Fixed

- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton
- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton
- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton
- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton


### Added

- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton
- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton
- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton

### Fixed

- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton
- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton
- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton
- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton
- **Fix orchestrator script references after rename** (2d89316) - wtthornton


### Added

- **feat(ai-agent): upgrade to GPT-5.2 reasoning model with 2026 prompt best practices** (28fe64c) - wtthornton
- **feat(evaluation): complete Agent Evaluation Framework (Pattern D) — all 34 stories** (34b5a8e) - wtthornton
- **feat(analytics): replace mock metrics with real in-memory instrumentation** (7f8fbed) - wtthornton
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton
- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton
- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton

### Fixed

- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton
- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton
- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton
- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton
- **Fix orchestrator script references after rename** (2d89316) - wtthornton


### Added

- **feat(synergy): sibling entity filtering for device pair synergies** — Filters out false synergy suggestions between entities belonging to the same device (e.g., Hue scenes and the lights they control). Uses `device_id` from entity registry for structural detection instead of name heuristics. Covers both area-based pair detection and co-occurrence pattern conversion. 13 new tests added.
- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton
- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton
- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton

### Fixed

- **fix(dashboard): use variable-based proxy_pass for dynamic DNS resolution** (343ff71) - wtthornton
- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton
- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton
- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton
- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton
- **Fix orchestrator script references after rename** (2d89316) - wtthornton


### Added

- **register Phase 2-4 validation routers in ai-automation-service** (304cdef) - wtthornton
- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton
- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton
- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton

### Fixed

- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton
- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton
- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton
- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton
- **Fix orchestrator script references after rename** (2d89316) - wtthornton


### Added

- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton
- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton
- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton

### Fixed

- **fix(docker): wrap sys.path manipulation in try/except for Docker compatibility** (cd48db8) - wtthornton
- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton
- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton
- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton
- **Fix orchestrator script references after rename** (2d89316) - wtthornton


### Added

- **Reusable Pattern Framework — Phases 2-4 complete** (149107c) - wtthornton
- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton
- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton

### Fixed

- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton
- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton
- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton
- **Fix orchestrator script references after rename** (2d89316) - wtthornton
- **Resolve ai-automation-ui TypeScript compilation errors** (3bd93bf) - wtthornton
- **Resolve api-automation-edge queue module naming conflict** (c93b149) - wtthornton


### Added

- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton
- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton
- **Add Phase 1 automated batch rebuild system for 40 services** (ec9e337) - wtthornton

### Fixed

- **fix(docker): resolve 5 container startup failures across stack** (0087706) - wtthornton
- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton
- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton
- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton
- **Fix orchestrator script references after rename** (2d89316) - wtthornton
- **Resolve ai-automation-ui TypeScript compilation errors** (3bd93bf) - wtthornton
- **Resolve api-automation-edge queue module naming conflict** (c93b149) - wtthornton


### Added

- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton
- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton
- **Add Phase 1 automated batch rebuild system for 40 services** (ec9e337) - wtthornton

### Fixed

- **fix(e2e): use request API for AI UI health check in global setup** (59be938) - wtthornton
- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton
- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton
- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton
- **Fix orchestrator script references after rename** (2d89316) - wtthornton
- **Resolve ai-automation-ui TypeScript compilation errors** (3bd93bf) - wtthornton
- **Resolve api-automation-edge queue module naming conflict** (c93b149) - wtthornton


### Added

- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton
- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton
- **Add Phase 1 automated batch rebuild system for 40 services** (ec9e337) - wtthornton
- **Phase 2 library upgrades - standard library updates** (9f8eeba) - wtthornton
- **Phase 1 library upgrades - critical compatibility fixes** (b17796f) - wtthornton

### Fixed

- **fix(e2e): expand and harden Playwright E2E test suite** (f9ef943) - wtthornton
- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton
- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton
- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton
- **Fix orchestrator script references after rename** (2d89316) - wtthornton
- **Resolve ai-automation-ui TypeScript compilation errors** (3bd93bf) - wtthornton
- **Resolve api-automation-edge queue module naming conflict** (c93b149) - wtthornton


### Added

- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton
- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton
- **Add Phase 1 automated batch rebuild system for 40 services** (ec9e337) - wtthornton
- **Phase 2 library upgrades - standard library updates** (9f8eeba) - wtthornton
- **Phase 1 library upgrades - critical compatibility fixes** (b17796f) - wtthornton
- **add Home Assistant automation linter service** (9212bed) - wtthornton

### Fixed

- **fix(e2e): comprehensive Playwright test quality pass — fix 43+ issues across all specs** (15eb6be) - wtthornton
- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton
- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton
- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton
- **Fix orchestrator script references after rename** (2d89316) - wtthornton
- **Resolve ai-automation-ui TypeScript compilation errors** (3bd93bf) - wtthornton
- **Resolve api-automation-edge queue module naming conflict** (c93b149) - wtthornton


### Added

- **feat(docker): add missing services to compose; align docs and Cursor refs** (d19b1fb) - wtthornton
- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton
- **Add Phase 1 automated batch rebuild system for 40 services** (ec9e337) - wtthornton
- **Phase 2 library upgrades - standard library updates** (9f8eeba) - wtthornton
- **Phase 1 library upgrades - critical compatibility fixes** (b17796f) - wtthornton
- **add Home Assistant automation linter service** (9212bed) - wtthornton

### Fixed

- **unit test fixes for conftest, ask_ai test button, and context7** (48a52f5) - wtthornton
- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton
- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton
- **Fix orchestrator script references after rename** (2d89316) - wtthornton
- **Resolve ai-automation-ui TypeScript compilation errors** (3bd93bf) - wtthornton
- **Resolve api-automation-edge queue module naming conflict** (c93b149) - wtthornton


### Added

- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton
- **Add Phase 1 automated batch rebuild system for 40 services** (ec9e337) - wtthornton
- **Phase 2 library upgrades - standard library updates** (9f8eeba) - wtthornton
- **Phase 1 library upgrades - critical compatibility fixes** (b17796f) - wtthornton
- **add Home Assistant automation linter service** (9212bed) - wtthornton
- **Implement entity capabilities enrichment and device card entity display** (571dbb7) - wtthornton

### Fixed

- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton
- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton
- **Fix orchestrator script references after rename** (2d89316) - wtthornton
- **Resolve ai-automation-ui TypeScript compilation errors** (3bd93bf) - wtthornton
- **Resolve api-automation-edge queue module naming conflict** (c93b149) - wtthornton


### Added

- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton
- **Add Phase 1 automated batch rebuild system for 40 services** (ec9e337) - wtthornton
- **Phase 2 library upgrades - standard library updates** (9f8eeba) - wtthornton
- **Phase 1 library upgrades - critical compatibility fixes** (b17796f) - wtthornton
- **add Home Assistant automation linter service** (9212bed) - wtthornton
- **Implement entity capabilities enrichment and device card entity display** (571dbb7) - wtthornton
- **Add Streamlit observability dashboard with OpenTelemetry integration** (6bdb15f) - wtthornton

### Fixed

- **add is_blueprint column migration for automation-miner** (45fa46e) - wtthornton
- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton
- **Fix orchestrator script references after rename** (2d89316) - wtthornton
- **Resolve ai-automation-ui TypeScript compilation errors** (3bd93bf) - wtthornton
- **Resolve api-automation-edge queue module naming conflict** (c93b149) - wtthornton


### Added

- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton
- **Add Phase 1 automated batch rebuild system for 40 services** (ec9e337) - wtthornton
- **Phase 2 library upgrades - standard library updates** (9f8eeba) - wtthornton
- **Phase 1 library upgrades - critical compatibility fixes** (b17796f) - wtthornton
- **add Home Assistant automation linter service** (9212bed) - wtthornton
- **Implement entity capabilities enrichment and device card entity display** (571dbb7) - wtthornton
- **Add Streamlit observability dashboard with OpenTelemetry integration** (6bdb15f) - wtthornton

### Fixed

- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton
- **Fix orchestrator script references after rename** (2d89316) - wtthornton
- **Resolve ai-automation-ui TypeScript compilation errors** (3bd93bf) - wtthornton
- **Resolve api-automation-edge queue module naming conflict** (c93b149) - wtthornton
- **Fix Docker deployment issues: FastAPI dependency injection and TypeScript errors** (88c7ac5) - wtthornton


### Added

- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton
- **Add Phase 1 automated batch rebuild system for 40 services** (ec9e337) - wtthornton
- **Phase 2 library upgrades - standard library updates** (9f8eeba) - wtthornton
- **Phase 1 library upgrades - critical compatibility fixes** (b17796f) - wtthornton
- **add Home Assistant automation linter service** (9212bed) - wtthornton
- **Implement entity capabilities enrichment and device card entity display** (571dbb7) - wtthornton
- **Add Streamlit observability dashboard with OpenTelemetry integration** (6bdb15f) - wtthornton

### Fixed

- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton
- **Fix orchestrator script references after rename** (2d89316) - wtthornton
- **Resolve ai-automation-ui TypeScript compilation errors** (3bd93bf) - wtthornton
- **Resolve api-automation-edge queue module naming conflict** (c93b149) - wtthornton
- **Fix Docker deployment issues: FastAPI dependency injection and TypeScript errors** (88c7ac5) - wtthornton


### Added

- **Add service tier ranking and clean up documentation** (f7a887a) - wtthornton
- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton
- **Add Phase 1 automated batch rebuild system for 40 services** (ec9e337) - wtthornton
- **Phase 2 library upgrades - standard library updates** (9f8eeba) - wtthornton
- **Phase 1 library upgrades - critical compatibility fixes** (b17796f) - wtthornton
- **add Home Assistant automation linter service** (9212bed) - wtthornton
- **Implement entity capabilities enrichment and device card entity display** (571dbb7) - wtthornton
- **Add Streamlit observability dashboard with OpenTelemetry integration** (6bdb15f) - wtthornton

### Changed

- **Improve code quality across 29 files in 25 services** (4bfb575) - wtthornton

### Fixed

- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton
- **Fix orchestrator script references after rename** (2d89316) - wtthornton
- **Resolve ai-automation-ui TypeScript compilation errors** (3bd93bf) - wtthornton
- **Resolve api-automation-edge queue module naming conflict** (c93b149) - wtthornton
- **Fix Docker deployment issues: FastAPI dependency injection and TypeScript errors** (88c7ac5) - wtthornton


### Added

- **Add diagnostics, backups, and migration artifacts to .gitignore** (263d12c) - wtthornton
- **Add --no-prompt flag for automated Phase D execution** (cfa9233) - wtthornton
- **Add --skip-tests flag to MQTT migration script** (b8da908) - wtthornton
- **Add --skip-tests flag to all migration scripts** (612fc8e) - wtthornton
- **Add Phase 1 automated batch rebuild system for 40 services** (ec9e337) - wtthornton
- **Phase 2 library upgrades - standard library updates** (9f8eeba) - wtthornton
- **Phase 1 library upgrades - critical compatibility fixes** (b17796f) - wtthornton
- **add Home Assistant automation linter service** (9212bed) - wtthornton
- **Implement entity capabilities enrichment and device card entity display** (571dbb7) - wtthornton
- **Add Streamlit observability dashboard with OpenTelemetry integration** (6bdb15f) - wtthornton

### Changed

- **Improve code quality across 29 files in 25 services** (4bfb575) - wtthornton

### Fixed

- **Fix blueprint-suggestion-service: create tests directory and migrate** (59827f0) - wtthornton
- **Fix data-retention InfluxDB write_api usage** (43b4664) - wtthornton
- **Fix energy-forecasting InfluxDB API to use new influxdb3-python** (e969324) - wtthornton
- **Fix orchestrator script references after rename** (2d89316) - wtthornton
- **Resolve ai-automation-ui TypeScript compilation errors** (3bd93bf) - wtthornton
- **Resolve api-automation-edge queue module naming conflict** (c93b149) - wtthornton
- **Fix Docker deployment issues: FastAPI dependency injection and TypeScript errors** (88c7ac5) - wtthornton
- **Fix type union syntax - use Optional/Union instead of | syntax for Python 3.12 compatibility** (2585bb2) - wtthornton

All notable changes to HomeIQ will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-02-06

### Major Release: Phase 2 Library Upgrades Complete

This release completes the Phase 2 library upgrade initiative, migrating all 31 Python services to modern library versions with breaking changes handled systematically.

### Added

- **TECH_STACK.md** - Comprehensive technology stack documentation
- **CHANGELOG.md** - Project changelog (this file)
- Phase 2 migration scripts for automated library upgrades
- Docker memory optimization across all 41 containers

### Changed

#### Library Upgrades (Breaking Changes)

| Library | Old | New | Migration |
|---------|-----|-----|-----------|
| pytest-asyncio | 0.x | 1.3.0 | Added `loop_scope="function"` parameter |
| tenacity | 8.x | 9.1.2 | Updated to `retry_if_exception_cause_type()` |
| asyncio-mqtt | 0.x | aiomqtt 2.4.0 | Package rename and API updates |
| influxdb-client | 1.x | influxdb3-python 0.17.0 | New `InfluxDBClient3` class, SQL queries |
| python-dotenv | 1.0.x | 1.2.1 | Minor API updates |

#### Service Updates

- **ai-automation-service-new**: Fixed Pydantic 2.12 compatibility with FastAPI dependency injection
  - Changed from `Annotated[Type, Depends()]` to `Type = Depends()` pattern
  - Updated `deployment_router.py` and `suggestion_router.py`

- **health-dashboard**: Fixed nginx proxy configuration for API authentication
  - Added `Authorization` header forwarding to `/api/v1/` location block

- **energy-forecasting**: Full InfluxDB 3.0 API migration
  - Updated `energy_loader.py` to use `InfluxDBClient3`
  - Changed from Flux queries to SQL queries

- **data-retention**: Updated InfluxDB write API
  - Changed from `write_api().write()` to `client.write()`

### Fixed

- **"Failed to load deployed automations: Unprocessable Entity"** error in AI Automation UI
  - Root cause: Pydantic 2.12 TypeAdapter incorrectly treating `Annotated` dependencies as Query parameters
  - Solution: Use traditional `= Depends()` style for FastAPI dependency injection

- **Admin Dashboard showing "unknown" status**
  - Root cause: nginx proxy not forwarding Authorization header for `/api/v1/` endpoints
  - Solution: Added `proxy_set_header Authorization` and `proxy_pass_header Authorization`

### Optimized

- **Docker Memory Limits** - Reduced overall memory footprint by ~5-6 GB
  | Category | Before | After | Savings |
  |----------|--------|-------|---------|
  | data-api | 1G | 256M | 75% |
  | openvino-service | 1.5G | 768M | 49% |
  | ner-service | 1G | 512M | 50% |
  | Standard services | 512M | 128M | 75% |
  | UI services | 256M | 64M | 75% |

### Migration Statistics

- **31/31** Python services migrated (100% success rate)
- **41/41** Docker images rebuilt
- **0** regression issues

---

## [1.9.0] - 2026-02-05

### Phase 2 Breaking Changes Migration

### Changed

- Initiated Phase 2 library upgrade automation
- Created migration scripts for:
  - `pytest-asyncio` 1.3.0 migration
  - `tenacity` 9.1.2 migration
  - `aiomqtt` 2.4.0 migration (from asyncio-mqtt)
  - `influxdb3-python` 0.17.0 migration

### Added

- Phase 2 planning documentation:
  - `phase2-implementation-plan.md`
  - `phase2-pytest-asyncio-migration-guide.md`
  - `phase2-tenacity-migration-guide.md`
  - `phase2-mqtt-migration-guide.md`
  - `phase2-influxdb-migration-guide.md`

---

## [1.8.0] - 2026-02-04

### Phase 1 Critical Compatibility Fixes

### Changed

- **SQLAlchemy**: 2.0.45 -> 2.0.46 (bug fixes, performance)
- **aiosqlite**: 0.21.0 -> 0.22.1 (async improvements, Python 3.13 support)

### Fixed

- Phase 0 infrastructure verification complete
- All 38/40 services rebuilt (95% success rate)

---

## [1.7.0] - 2026-01-xx

### Initial Phase 1 Library Upgrades

### Changed

- Updated core libraries to latest stable versions
- Established `requirements-base.txt` shared dependency file
- Implemented version range strategy for patch updates

### Added

- Library upgrade planning documentation
- Automated batch rebuild scripts
- Service health validation framework

---

## [1.6.0] - 2025-12-xx

### Automation Linter

### Added

- YAML automation linting service with 15+ quality rules
- Automation validation API endpoints
- Auto-fix capabilities for common issues

### Documentation

- `docs/automation-linter.md` - Feature documentation
- `docs/automation-linter-rules.md` - Complete rules catalog

---

## [1.5.0] - 2025-11-xx

### AI Automation UI

### Added

- Natural language automation creation interface
- Real-time suggestion generation
- Pattern detection visualization

### Changed

- Migrated from legacy ai-automation-service to ai-automation-service-new
- Improved deployment workflow

---

## [1.4.0] - 2025-10-xx

### Health Dashboard Enhancements

### Added

- System Status Hero component
- RAG Status monitoring
- Core System Cards (Ingestion, Storage)
- Performance sparklines
- Service dependency visualization

### Changed

- Redesigned Overview Tab for "5-second health check"
- Added data freshness indicators

---

## [1.3.0] - 2025-09-xx

### Data API Consolidation (Epic 13)

### Changed

- Consolidated data endpoints into data-api service
- Separated admin-api (system monitoring) from data-api (feature data)
- Implemented nginx proxy routing for API segmentation

---

## [1.2.0] - 2025-08-xx

### Event Flow Architecture (Epic 31)

### Changed

- Redesigned event ingestion pipeline
- Direct writes from websocket-ingestion to InfluxDB
- Inline normalization in websocket-ingestion

### Added

- Event flow architecture documentation
- InfluxDB schema documentation

---

## [1.1.0] - 2025-07-xx

### Sports Data Integration

### Added

- Sports API service (NFL, NHL, MLB support)
- Live game tracking
- Home Assistant game context integration

---

## [1.0.0] - 2025-06-xx

### Initial Release

### Added

- Core microservices architecture (30+ services)
- Home Assistant WebSocket integration
- AI-powered automation suggestions
- Device intelligence service
- Weather, energy pricing, air quality enrichment
- Health Dashboard (React)
- AI Automation UI (React)
- InfluxDB time-series storage
- SQLite metadata storage
- OpenTelemetry observability

---

## Version Naming

- **Major (X.0.0)**: Breaking changes, major features
- **Minor (0.X.0)**: New features, non-breaking changes
- **Patch (0.0.X)**: Bug fixes, documentation updates

---

## Links

- [README](README.md)
- [Tech Stack](TECH_STACK.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Documentation](docs/)
