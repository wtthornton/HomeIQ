# Commit Plan for Pending Changes

## Overview
This document outlines the logical grouping of all pending changes into meaningful commits.

## Commit Groups

### 1. BMAD Phase 1 Features - Workflow Init & Quick Fix
**Type:** Feature Addition  
**Files:**
- `.bmad-core/tasks/workflow-init.md` (new)
- `.bmad-core/workflows/quick-fix.yaml` (new)
- `.bmad-core/utils/agent-customization-loader.md` (new)
- `.bmad-core/utils/svg-workflow-generator.md` (new)
- `.bmad-core/agents/bmad-master.md` (modified)
- `.bmad-core/core-config.yaml` (modified)
- `.bmad-core/tasks/shard-doc.md` (modified)
- `.bmad-core/workflows/greenfield-fullstack.yaml` (modified)
- `.cursor/rules/bmad-workflow.mdc` (modified)
- `.cursor/rules/README.mdc` (modified)

**Commit Message:**
```
feat(bmad): Add Phase 1 features - workflow-init and quick-fix workflow

- Add workflow-init task for automatic workflow track recommendation
- Add quick-fix.yaml workflow for bug fixes and small features
- Add agent customization loader and SVG workflow generator utilities
- Update bmad-master agent and core config for Phase 1 features
- Enhance shard-doc task with cross-reference support
- Update workflow documentation and README
```

---

### 2. BMAD Agent Rules - Context7 KB Integration
**Type:** Enhancement  
**Files:**
- `.cursor/rules/bmad/analyst.mdc` (modified)
- `.cursor/rules/bmad/architect.mdc` (modified)
- `.cursor/rules/bmad/bmad-master.mdc` (modified)
- `.cursor/rules/bmad/dev.mdc` (modified)
- `.cursor/rules/bmad/pm.mdc` (modified)
- `.cursor/rules/bmad/po.mdc` (modified)
- `.cursor/rules/bmad/qa.mdc` (modified)
- `.cursor/rules/bmad/sm.mdc` (modified)
- `.cursor/rules/bmad/ux-expert.mdc` (modified)

**Commit Message:**
```
feat(bmad): Add Context7 KB integration to all BMAD agents

- Add Context7 KB commands to all agent personas
- Implement KB-first documentation lookup pattern
- Add KB cache management commands to bmad-master
- Update agent documentation with Context7 usage examples
```

---

### 3. Epic 33-35 Documentation - External Data Generation
**Type:** Documentation  
**Files:**
- `docs/prd/epic-33-foundation-external-data-generation.md` (new)
- `docs/prd/epic-34-advanced-external-data-generation.md` (new)
- `docs/prd/epic-35-external-data-integration-correlation.md` (new)
- `docs/prd/epic-36-correlation-analysis-foundation.md` (new)
- `docs/prd/epic-37-correlation-analysis-optimization.md` (new)
- `docs/prd/epic-38-correlation-analysis-advanced.md` (new)
- `docs/prd/epic-39-ai-automation-service-modularization.md` (new)
- `docs/prd/epic-40-dual-deployment-configuration.md` (new)
- `docs/prd/epic-list.md` (modified)
- All `docs/stories/story-33.*.md` files (new)
- All `docs/stories/story-34.*.md` files (new)
- All `docs/stories/story-35.*.md` files (new)
- All `docs/qa/gates/33.*.yml` files (new)
- All `docs/qa/gates/34.*.yml` files (new)
- `docs/qa/34-advanced-external-data-generation-qa-summary.md` (new)

**Commit Message:**
```
docs: Add Epic 33-35 documentation for external data generation

- Add Epic 33: Foundation External Data Generation (weather, carbon)
- Add Epic 34: Advanced External Data Generation (pricing, calendar)
- Add Epic 35: External Data Integration & Correlation
- Add Epic 36-38: Correlation Analysis series
- Add Epic 39-40: Service modularization and deployment
- Add all associated user stories (33.1-35.6)
- Add QA gates and assessment documents
- Update epic list with new epics
```

---

### 4. Synthetic External Data Generators Implementation
**Type:** Feature Implementation  
**Files:**
- `services/ai-automation-service/src/training/synthetic_weather_generator.py` (new)
- `services/ai-automation-service/src/training/synthetic_carbon_intensity_generator.py` (new)
- `services/ai-automation-service/src/training/synthetic_electricity_pricing_generator.py` (new)
- `services/ai-automation-service/src/training/synthetic_calendar_generator.py` (new)
- `services/ai-automation-service/src/training/synthetic_external_data_generator.py` (new)
- `services/ai-automation-service/src/training/synthetic_home_generator.py` (modified)
- `services/ai-automation-service/src/training/synthetic_home_ha_loader.py` (new)
- `services/ai-automation-service/src/training/synthetic_home_openai_generator.py` (new)
- `services/ai-automation-service/scripts/generate_synthetic_homes.py` (modified)
- `services/ai-automation-service/tests/training/test_synthetic_carbon_intensity_generator.py` (new)
- `services/ai-automation-service/tests/training/` (other test files if any)

**Commit Message:**
```
feat(training): Implement synthetic external data generators

- Add weather generator with seasonal/daily patterns and HVAC correlation
- Add carbon intensity generator with time-of-day and seasonal patterns
- Add electricity pricing generator with time-of-use and market dynamics
- Add calendar generator with work schedules and presence patterns
- Add unified external data generator for coordinated generation
- Enhance synthetic home generator with external data integration
- Add Home Assistant loader and OpenAI generator variants
- Add comprehensive tests for carbon intensity generator
- Update generate_synthetic_homes script for new generators
```

---

### 5. AI Automation Service - GNN Synergy & Quality Framework
**Type:** Feature Enhancement  
**Files:**
- `services/ai-automation-service/src/synergy_detection/gnn_synergy_detector.py` (modified)
- `services/ai-automation-service/src/services/learning/ensemble_quality_scorer.py` (new)
- `services/ai-automation-service/src/services/learning/fbvl_quality_scorer.py` (new)
- `services/ai-automation-service/src/services/learning/hitl_quality_enhancer.py` (new)
- `services/ai-automation-service/src/services/learning/pattern_drift_detector.py` (new)
- `services/ai-automation-service/src/services/learning/pattern_rlhf.py` (new)
- `services/ai-automation-service/src/services/learning/quality_calibration_loop.py` (new)
- `services/ai-automation-service/src/services/learning/weight_optimization_loop.py` (new)
- `services/ai-automation-service/src/synergy_detection/real_world_rules.py` (new)
- `services/ai-automation-service/src/synergy_detection/rules_manager.py` (new)
- `services/ai-automation-service/src/synergy_detection/spatial_validator.py` (new)
- `services/ai-automation-service/tests/test_gnn_synergy_detector.py` (new)
- `services/ai-automation-service/tests/test_real_world_rules.py` (new)
- `services/ai-automation-service/tests/test_spatial_validator.py` (new)
- `services/ai-automation-service/tests/test_co_occurrence_detector.py` (modified)
- `services/ai-automation-service/tests/test_synergy_detector.py` (modified)
- `services/ai-automation-service/tests/test_time_of_day_detector.py` (modified)

**Commit Message:**
```
feat(ai-automation): Enhance GNN synergy detection and quality framework

- Major refactor of GNN synergy detector with improved architecture
- Add ensemble quality scorer with multiple scoring strategies
- Add feedback-based learning (FBVL) quality scorer
- Add human-in-the-loop (HITL) quality enhancer
- Add pattern drift detection and RLHF components
- Add quality calibration and weight optimization loops
- Add real-world rules and rules manager for synergy validation
- Add spatial validator for location-based pattern validation
- Add comprehensive tests for new components
- Update existing synergy detector tests
```

---

### 6. AI Automation Service - Home Type Integration
**Type:** Feature Enhancement  
**Files:**
- `services/ai-automation-service/src/clients/home_type_client.py` (new)
- `services/ai-automation-service/src/home_type/integration_helpers.py` (new)
- `services/ai-automation-service/src/services/learning/user_profile_builder.py` (modified)
- `services/ai-automation-service/src/services/pattern_context_service.py` (modified)
- `services/ai-automation-service/tests/test_home_type_client.py` (new)
- `services/ai-automation-service/tests/test_home_type_pattern_detection.py` (new)
- `services/ai-automation-service/tests/test_home_type_quality_scorer.py` (new)
- `services/ai-automation-service/tests/test_home_type_suggestion_ranking.py` (new)
- `services/ai-automation-service/tests/test_integration_helpers.py` (new)
- `services/ai-automation-service/tests/integration/test_home_type_integration.py` (new)
- `services/ai-automation-service/scripts/train_home_type_classifier.py` (modified)

**Commit Message:**
```
feat(ai-automation): Add home type categorization integration

- Add home type client for device-context-classifier service integration
- Add integration helpers for home type pattern detection
- Enhance user profile builder with home type context
- Update pattern context service for home type awareness
- Add comprehensive tests for home type integration
- Update home type classifier training script
```

---

### 7. AI Automation Service - API & Core Updates
**Type:** Feature Enhancement  
**Files:**
- `services/ai-automation-service/src/api/admin_router.py` (modified)
- `services/ai-automation-service/src/api/ask_ai_router.py` (modified)
- `services/ai-automation-service/src/api/suggestion_router.py` (modified)
- `services/ai-automation-service/src/config.py` (modified)
- `services/ai-automation-service/src/database/__init__.py` (modified)
- `services/ai-automation-service/src/database/crud.py` (modified)
- `services/ai-automation-service/src/database/models.py` (modified)
- `services/ai-automation-service/src/llm/openai_client.py` (modified)
- `services/ai-automation-service/src/llm/rate_limit_checker.py` (new)
- `services/ai-automation-service/src/main.py` (modified)
- `services/ai-automation-service/src/scheduler/daily_analysis.py` (modified)
- `services/ai-automation-service/src/services/service_container.py` (modified)
- `services/ai-automation-service/Dockerfile` (modified)
- `services/ai-automation-service/requirements.txt` (modified)

**Commit Message:**
```
feat(ai-automation): Enhance API endpoints and core service functionality

- Enhance admin router with new management endpoints
- Expand ask_ai_router with improved AI interactions
- Update suggestion router with better ranking
- Add rate limit checker for OpenAI API
- Enhance database CRUD operations and models
- Update daily analysis scheduler
- Add new dependencies to requirements.txt
- Update Dockerfile for new dependencies
```

---

### 8. Device Database & Intelligence Services
**Type:** Feature Addition  
**Files:**
- `services/device-context-classifier/` (new directory)
- `services/device-database-client/` (new directory)
- `services/device-health-monitor/` (new directory)
- `services/device-intelligence-service/src/capability_discovery/` (new)
- `services/device-recommender/` (new directory)
- `services/device-setup-assistant/` (new directory)
- `services/data-api/src/services/capability_discovery.py` (new)
- `services/data-api/src/services/device_classifier.py` (new)
- `services/data-api/src/services/device_database.py` (new)
- `services/data-api/src/services/device_health.py` (new)
- `services/data-api/src/services/device_recommender.py` (new)
- `services/data-api/src/services/setup_assistant.py` (new)
- `services/data-api/src/devices_endpoints.py` (modified)
- `services/data-api/alembic/versions/006_add_device_intelligence_fields.py` (new)
- `docs/DEVICE_DATABASE_ENHANCEMENTS.md` (new)
- `DEPLOYMENT_DEVICE_DATABASE.md` (new)

**Commit Message:**
```
feat(device-intelligence): Add device database and intelligence services

- Add device-context-classifier service
- Add device-database-client library
- Add device-health-monitor service
- Add device-intelligence-service capability discovery
- Add device-recommender service
- Add device-setup-assistant service
- Add device intelligence services to data-api
- Add database migration for device intelligence fields
- Add device database documentation
```

---

### 9. Data API & Retention Service Updates
**Type:** Enhancement  
**Files:**
- `services/data-api/src/events_endpoints.py` (modified)
- `services/data-retention/src/materialized_views.py` (modified)
- `services/data-retention/src/s3_archival.py` (modified)
- `services/data-retention/src/storage_analytics.py` (modified)
- `services/data-retention/src/tiered_retention.py` (modified)
- `services/energy-correlator/src/correlator.py` (modified)
- `services/websocket-ingestion/src/influxdb_schema.py` (modified)

**Commit Message:**
```
feat(data-services): Enhance data API and retention services

- Enhance events endpoints with new query capabilities
- Improve materialized views for better performance
- Enhance S3 archival with better error handling
- Add storage analytics improvements
- Update tiered retention policies
- Enhance energy correlator with better patterns
- Update InfluxDB schema with new fields
```

---

### 10. UI Enhancements - Admin Panel & AskAI
**Type:** Feature Enhancement  
**Files:**
- `services/ai-automation-ui/src/api/admin.ts` (modified)
- `services/ai-automation-ui/src/pages/Admin.tsx` (modified)
- `services/ai-automation-ui/src/pages/AskAI.tsx` (modified)
- `services/ai-automation-ui/src/pages/Synergies.tsx` (modified)
- `services/ai-automation-ui/Dockerfile` (modified)

**Commit Message:**
```
feat(ui): Enhance admin panel and AskAI interface

- Add comprehensive admin panel features
- Enhance AskAI interface with improved UX
- Update Synergies page with better visualization
- Update Dockerfile for new dependencies
```

---

### 11. Documentation Updates - Architecture & API
**Type:** Documentation  
**Files:**
- `docs/architecture.md` (modified)
- `docs/architecture/coding-standards.md` (modified)
- `docs/architecture/index.md` (modified)
- `docs/architecture/source-tree.md` (modified)
- `docs/architecture/tech-stack.md` (modified)
- `docs/architecture/home-type-categorization.md` (new)
- `docs/api/API_REFERENCE.md` (modified)
- `docs/DOCUMENTATION_INDEX.md` (modified)
- `docs/README.md` (modified)
- `docs/SERVICES_OVERVIEW.md` (modified)
- `docs/current/operations/soft-prompt-training.md` (modified)
- `docs/current/BMAD_DEVELOPER_GUIDE.md` (new)
- `docs/kb/` (all new KB cache files)

**Commit Message:**
```
docs: Update architecture and API documentation

- Update architecture documentation with latest patterns
- Add comprehensive coding standards document
- Add home type categorization architecture doc
- Update API reference with new endpoints
- Update documentation index and services overview
- Add BMAD developer guide
- Add Context7 KB cache documentation
- Update soft prompt training guide
```

---

### 12. Scripts & Utilities
**Type:** Tooling  
**Files:**
- `scripts/analyze_datasets.py` (new)
- `scripts/analyze_device_matching_fix.py` (new)
- `scripts/analyze_device_type_event_frequency.py` (new)
- `scripts/analyze_production_ha_events.py` (new)
- `scripts/check_ha_token.ps1` (new)
- `scripts/check_openai_rate_limits.py` (new)
- `scripts/deploy-device-database-services.ps1` (new)
- `scripts/deploy-device-database-services.sh` (new)
- `scripts/deploy_home_type_integration.ps1` (new)
- `scripts/deploy_home_type_integration.sh` (new)
- `scripts/ensure_model_cache.py` (new)
- `scripts/fetch-tech-stack-docs.sh` (new)
- `scripts/load_dataset_to_ha.py` (new)
- `scripts/run_pattern_synergy_tests.py` (new)
- `scripts/run_tests_with_env.ps1` (new)
- `scripts/setup_ha_test.ps1` (new)
- `scripts/setup_ha_test.sh` (new)
- `scripts/verify_home_type_integration.py` (new)
- `scripts/train_soft_prompt.py` (modified)
- All `services/ai-automation-service/scripts/*.py` (new/modified)

**Commit Message:**
```
feat(scripts): Add analysis, deployment, and utility scripts

- Add dataset analysis scripts
- Add device matching and event frequency analysis
- Add Home Assistant test setup scripts
- Add deployment scripts for device database and home type
- Add OpenAI rate limit checking
- Add model cache management
- Add pattern synergy test runner
- Add tech stack documentation fetcher
- Update soft prompt training script
```

---

### 13. Configuration & Infrastructure
**Type:** Configuration  
**Files:**
- `docker-compose.yml` (modified)
- `.gitignore` (modified)
- `README.md` (modified)
- `services/ai-automation-service/data/ask_ai.db` (new - should be gitignored)
- `services/ai-automation-service/alembic/versions/20250126_add_training_type.py` (new)
- `services/data-api/alembic/versions/006_add_device_intelligence_fields.py` (new)

**Commit Message:**
```
chore: Update configuration and infrastructure

- Update docker-compose.yml with new services
- Update .gitignore for new file patterns
- Update README.md with latest project info
- Add database migrations for training type and device intelligence
```

---

### 14. Implementation Notes & Analysis (Optional - Consider Gitignoring)
**Type:** Documentation (Implementation Notes)  
**Files:**
- All files in `implementation/` directory (new/modified)
- These are implementation notes and may be better in gitignore

**Note:** Consider adding `implementation/` to `.gitignore` except for key reference documents, or commit separately as implementation history.

**Commit Message (if committing):**
```
docs(implementation): Add implementation notes and analysis

- Add analysis documents for various features
- Add deployment summaries and verification results
- Add training and testing execution plans
- Add competitive analysis and enhancement plans
```

---

## Execution Order

1. Commit 1: BMAD Phase 1 Features
2. Commit 2: BMAD Agent Rules
3. Commit 3: Epic 33-35 Documentation
4. Commit 4: Synthetic External Data Generators
5. Commit 5: GNN Synergy & Quality Framework
6. Commit 6: Home Type Integration
7. Commit 7: API & Core Updates
8. Commit 8: Device Database Services
9. Commit 9: Data API & Retention Updates
10. Commit 10: UI Enhancements
11. Commit 11: Documentation Updates
12. Commit 12: Scripts & Utilities
13. Commit 13: Configuration & Infrastructure
14. Commit 14: Implementation Notes (optional)

## Notes

- Some files may need to be checked for `.gitignore` patterns (e.g., `ask_ai.db`)
- Implementation notes directory might be better excluded from git
- Test files should be committed with their corresponding features
- Database migration files should be committed with their features

