# Commit Execution Guide

## Pre-Commit Checklist

### 1. Check for files that should be gitignored
```bash
# Check if ask_ai.db should be ignored
git check-ignore services/ai-automation-service/data/ask_ai.db
```

**Note:** If `ask_ai.db` is a runtime database, add to `.gitignore`:
```
# Runtime database files in services
services/*/data/*.db
services/*/data/*.db-shm
services/*/data/*.db-wal
```

### 2. Review implementation/ directory
The `implementation/` directory contains many files. According to project structure rules, these should be committed but may be archived quarterly. Consider committing them as a separate "implementation history" commit.

---

## Commit Execution Script

### Commit 1: BMAD Phase 1 Features
```bash
git add .bmad-core/tasks/workflow-init.md
git add .bmad-core/workflows/quick-fix.yaml
git add .bmad-core/utils/agent-customization-loader.md
git add .bmad-core/utils/svg-workflow-generator.md
git add .bmad-core/agents/bmad-master.md
git add .bmad-core/core-config.yaml
git add .bmad-core/tasks/shard-doc.md
git add .bmad-core/workflows/greenfield-fullstack.yaml
git add .cursor/rules/bmad-workflow.mdc
git add .cursor/rules/README.mdc
git commit -m "feat(bmad): Add Phase 1 features - workflow-init and quick-fix workflow

- Add workflow-init task for automatic workflow track recommendation
- Add quick-fix.yaml workflow for bug fixes and small features
- Add agent customization loader and SVG workflow generator utilities
- Update bmad-master agent and core config for Phase 1 features
- Enhance shard-doc task with cross-reference support
- Update workflow documentation and README"
```

### Commit 2: BMAD Agent Rules - Context7 KB Integration
```bash
git add .cursor/rules/bmad/analyst.mdc
git add .cursor/rules/bmad/architect.mdc
git add .cursor/rules/bmad/bmad-master.mdc
git add .cursor/rules/bmad/dev.mdc
git add .cursor/rules/bmad/pm.mdc
git add .cursor/rules/bmad/po.mdc
git add .cursor/rules/bmad/qa.mdc
git add .cursor/rules/bmad/sm.mdc
git add .cursor/rules/bmad/ux-expert.mdc
git commit -m "feat(bmad): Add Context7 KB integration to all BMAD agents

- Add Context7 KB commands to all agent personas
- Implement KB-first documentation lookup pattern
- Add KB cache management commands to bmad-master
- Update agent documentation with Context7 usage examples"
```

### Commit 3: Epic 33-35 Documentation
```bash
git add docs/prd/epic-33-foundation-external-data-generation.md
git add docs/prd/epic-34-advanced-external-data-generation.md
git add docs/prd/epic-35-external-data-integration-correlation.md
git add docs/prd/epic-36-correlation-analysis-foundation.md
git add docs/prd/epic-37-correlation-analysis-optimization.md
git add docs/prd/epic-38-correlation-analysis-advanced.md
git add docs/prd/epic-39-ai-automation-service-modularization.md
git add docs/prd/epic-40-dual-deployment-configuration.md
git add docs/prd/epic-list.md
git add docs/stories/story-33.*.md
git add docs/stories/story-34.*.md
git add docs/stories/story-35.*.md
git add docs/qa/gates/33.*.yml
git add docs/qa/gates/34.*.yml
git add docs/qa/34-advanced-external-data-generation-qa-summary.md
git commit -m "docs: Add Epic 33-35 documentation for external data generation

- Add Epic 33: Foundation External Data Generation (weather, carbon)
- Add Epic 34: Advanced External Data Generation (pricing, calendar)
- Add Epic 35: External Data Integration & Correlation
- Add Epic 36-38: Correlation Analysis series
- Add Epic 39-40: Service modularization and deployment
- Add all associated user stories (33.1-35.6)
- Add QA gates and assessment documents
- Update epic list with new epics"
```

### Commit 4: Synthetic External Data Generators
```bash
git add services/ai-automation-service/src/training/synthetic_weather_generator.py
git add services/ai-automation-service/src/training/synthetic_carbon_intensity_generator.py
git add services/ai-automation-service/src/training/synthetic_electricity_pricing_generator.py
git add services/ai-automation-service/src/training/synthetic_calendar_generator.py
git add services/ai-automation-service/src/training/synthetic_external_data_generator.py
git add services/ai-automation-service/src/training/synthetic_home_ha_loader.py
git add services/ai-automation-service/src/training/synthetic_home_openai_generator.py
git add services/ai-automation-service/src/training/synthetic_home_generator.py
git add services/ai-automation-service/scripts/generate_synthetic_homes.py
git add services/ai-automation-service/tests/training/
git commit -m "feat(training): Implement synthetic external data generators

- Add weather generator with seasonal/daily patterns and HVAC correlation
- Add carbon intensity generator with time-of-day and seasonal patterns
- Add electricity pricing generator with time-of-use and market dynamics
- Add calendar generator with work schedules and presence patterns
- Add unified external data generator for coordinated generation
- Enhance synthetic home generator with external data integration
- Add Home Assistant loader and OpenAI generator variants
- Add comprehensive tests for generators
- Update generate_synthetic_homes script for new generators"
```

### Commit 5: GNN Synergy & Quality Framework
```bash
git add services/ai-automation-service/src/synergy_detection/gnn_synergy_detector.py
git add services/ai-automation-service/src/services/learning/ensemble_quality_scorer.py
git add services/ai-automation-service/src/services/learning/fbvl_quality_scorer.py
git add services/ai-automation-service/src/services/learning/hitl_quality_enhancer.py
git add services/ai-automation-service/src/services/learning/pattern_drift_detector.py
git add services/ai-automation-service/src/services/learning/pattern_rlhf.py
git add services/ai-automation-service/src/services/learning/quality_calibration_loop.py
git add services/ai-automation-service/src/services/learning/weight_optimization_loop.py
git add services/ai-automation-service/src/synergy_detection/real_world_rules.py
git add services/ai-automation-service/src/synergy_detection/rules_manager.py
git add services/ai-automation-service/src/synergy_detection/spatial_validator.py
git add services/ai-automation-service/tests/test_gnn_synergy_detector.py
git add services/ai-automation-service/tests/test_real_world_rules.py
git add services/ai-automation-service/tests/test_spatial_validator.py
git add services/ai-automation-service/tests/test_co_occurrence_detector.py
git add services/ai-automation-service/tests/test_synergy_detector.py
git add services/ai-automation-service/tests/test_time_of_day_detector.py
git commit -m "feat(ai-automation): Enhance GNN synergy detection and quality framework

- Major refactor of GNN synergy detector with improved architecture
- Add ensemble quality scorer with multiple scoring strategies
- Add feedback-based learning (FBVL) quality scorer
- Add human-in-the-loop (HITL) quality enhancer
- Add pattern drift detection and RLHF components
- Add quality calibration and weight optimization loops
- Add real-world rules and rules manager for synergy validation
- Add spatial validator for location-based pattern validation
- Add comprehensive tests for new components
- Update existing synergy detector tests"
```

### Commit 6: Home Type Integration
```bash
git add services/ai-automation-service/src/clients/home_type_client.py
git add services/ai-automation-service/src/home_type/integration_helpers.py
git add services/ai-automation-service/src/services/learning/user_profile_builder.py
git add services/ai-automation-service/src/services/pattern_context_service.py
git add services/ai-automation-service/tests/test_home_type_client.py
git add services/ai-automation-service/tests/test_home_type_pattern_detection.py
git add services/ai-automation-service/tests/test_home_type_quality_scorer.py
git add services/ai-automation-service/tests/test_home_type_suggestion_ranking.py
git add services/ai-automation-service/tests/test_integration_helpers.py
git add services/ai-automation-service/tests/integration/test_home_type_integration.py
git add services/ai-automation-service/scripts/train_home_type_classifier.py
git commit -m "feat(ai-automation): Add home type categorization integration

- Add home type client for device-context-classifier service integration
- Add integration helpers for home type pattern detection
- Enhance user profile builder with home type context
- Update pattern context service for home type awareness
- Add comprehensive tests for home type integration
- Update home type classifier training script"
```

### Commit 7: AI Automation Service - API & Core Updates
```bash
git add services/ai-automation-service/src/api/admin_router.py
git add services/ai-automation-service/src/api/ask_ai_router.py
git add services/ai-automation-service/src/api/suggestion_router.py
git add services/ai-automation-service/src/config.py
git add services/ai-automation-service/src/database/__init__.py
git add services/ai-automation-service/src/database/crud.py
git add services/ai-automation-service/src/database/models.py
git add services/ai-automation-service/src/llm/openai_client.py
git add services/ai-automation-service/src/llm/rate_limit_checker.py
git add services/ai-automation-service/src/main.py
git add services/ai-automation-service/src/scheduler/daily_analysis.py
git add services/ai-automation-service/src/services/service_container.py
git add services/ai-automation-service/Dockerfile
git add services/ai-automation-service/requirements.txt
git commit -m "feat(ai-automation): Enhance API endpoints and core service functionality

- Enhance admin router with new management endpoints
- Expand ask_ai_router with improved AI interactions
- Update suggestion router with better ranking
- Add rate limit checker for OpenAI API
- Enhance database CRUD operations and models
- Update daily analysis scheduler
- Add new dependencies to requirements.txt
- Update Dockerfile for new dependencies"
```

### Commit 8: Device Database & Intelligence Services
```bash
git add services/device-context-classifier/
git add services/device-database-client/
git add services/device-health-monitor/
git add services/device-intelligence-service/src/capability_discovery/
git add services/device-recommender/
git add services/device-setup-assistant/
git add services/data-api/src/services/capability_discovery.py
git add services/data-api/src/services/device_classifier.py
git add services/data-api/src/services/device_database.py
git add services/data-api/src/services/device_health.py
git add services/data-api/src/services/device_recommender.py
git add services/data-api/src/services/setup_assistant.py
git add services/data-api/src/devices_endpoints.py
git add services/data-api/alembic/versions/006_add_device_intelligence_fields.py
git add docs/DEVICE_DATABASE_ENHANCEMENTS.md
git add DEPLOYMENT_DEVICE_DATABASE.md
git commit -m "feat(device-intelligence): Add device database and intelligence services

- Add device-context-classifier service
- Add device-database-client library
- Add device-health-monitor service
- Add device-intelligence-service capability discovery
- Add device-recommender service
- Add device-setup-assistant service
- Add device intelligence services to data-api
- Add database migration for device intelligence fields
- Add device database documentation"
```

### Commit 9: Data API & Retention Service Updates
```bash
git add services/data-api/src/events_endpoints.py
git add services/data-retention/src/materialized_views.py
git add services/data-retention/src/s3_archival.py
git add services/data-retention/src/storage_analytics.py
git add services/data-retention/src/tiered_retention.py
git add services/energy-correlator/src/correlator.py
git add services/websocket-ingestion/src/influxdb_schema.py
git commit -m "feat(data-services): Enhance data API and retention services

- Enhance events endpoints with new query capabilities
- Improve materialized views for better performance
- Enhance S3 archival with better error handling
- Add storage analytics improvements
- Update tiered retention policies
- Enhance energy correlator with better patterns
- Update InfluxDB schema with new fields"
```

### Commit 10: UI Enhancements
```bash
git add services/ai-automation-ui/src/api/admin.ts
git add services/ai-automation-ui/src/pages/Admin.tsx
git add services/ai-automation-ui/src/pages/AskAI.tsx
git add services/ai-automation-ui/src/pages/Synergies.tsx
git add services/ai-automation-ui/Dockerfile
git commit -m "feat(ui): Enhance admin panel and AskAI interface

- Add comprehensive admin panel features
- Enhance AskAI interface with improved UX
- Update Synergies page with better visualization
- Update Dockerfile for new dependencies"
```

### Commit 11: Documentation Updates
```bash
git add docs/architecture.md
git add docs/architecture/coding-standards.md
git add docs/architecture/index.md
git add docs/architecture/source-tree.md
git add docs/architecture/tech-stack.md
git add docs/architecture/home-type-categorization.md
git add docs/api/API_REFERENCE.md
git add docs/DOCUMENTATION_INDEX.md
git add docs/README.md
git add docs/SERVICES_OVERVIEW.md
git add docs/current/operations/soft-prompt-training.md
git add docs/current/BMAD_DEVELOPER_GUIDE.md
git add docs/kb/
git commit -m "docs: Update architecture and API documentation

- Update architecture documentation with latest patterns
- Add comprehensive coding standards document
- Add home type categorization architecture doc
- Update API reference with new endpoints
- Update documentation index and services overview
- Add BMAD developer guide
- Add Context7 KB cache documentation
- Update soft prompt training guide"
```

### Commit 12: Scripts & Utilities
```bash
git add scripts/analyze_datasets.py
git add scripts/analyze_device_matching_fix.py
git add scripts/analyze_device_type_event_frequency.py
git add scripts/analyze_production_ha_events.py
git add scripts/check_ha_token.ps1
git add scripts/check_openai_rate_limits.py
git add scripts/deploy-device-database-services.ps1
git add scripts/deploy-device-database-services.sh
git add scripts/deploy_home_type_integration.ps1
git add scripts/deploy_home_type_integration.sh
git add scripts/ensure_model_cache.py
git add scripts/fetch-tech-stack-docs.sh
git add scripts/load_dataset_to_ha.py
git add scripts/run_pattern_synergy_tests.py
git add scripts/run_tests_with_env.ps1
git add scripts/setup_ha_test.ps1
git add scripts/setup_ha_test.sh
git add scripts/verify_home_type_integration.py
git add scripts/train_soft_prompt.py
git add services/ai-automation-service/scripts/
git commit -m "feat(scripts): Add analysis, deployment, and utility scripts

- Add dataset analysis scripts
- Add device matching and event frequency analysis
- Add Home Assistant test setup scripts
- Add deployment scripts for device database and home type
- Add OpenAI rate limit checking
- Add model cache management
- Add pattern synergy test runner
- Add tech stack documentation fetcher
- Update soft prompt training script"
```

### Commit 13: Configuration & Infrastructure
```bash
git add docker-compose.yml
git add .gitignore
git add README.md
git add services/ai-automation-service/alembic/versions/20250126_add_training_type.py
git commit -m "chore: Update configuration and infrastructure

- Update docker-compose.yml with new services
- Update .gitignore for new file patterns
- Update README.md with latest project info
- Add database migrations for training type"
```

### Commit 14: Implementation Notes (Optional)
```bash
# Review implementation/ directory first
# Consider if these should be committed or archived
git add implementation/
git commit -m "docs(implementation): Add implementation notes and analysis

- Add analysis documents for various features
- Add deployment summaries and verification results
- Add training and testing execution plans
- Add competitive analysis and enhancement plans"
```

---

## Quick All-in-One Script (PowerShell)

```powershell
# Pre-flight: Check for database files
if (Test-Path "services/ai-automation-service/data/ask_ai.db") {
    Write-Host "WARNING: ask_ai.db found - check if it should be gitignored"
}

# Execute commits in order
# (Copy each commit block from above)
```

---

## Verification

After all commits:
```bash
git log --oneline -14
git status
```

Ensure:
- No uncommitted changes remain
- All commits have meaningful messages
- Database files are properly ignored
- Implementation notes are handled appropriately

