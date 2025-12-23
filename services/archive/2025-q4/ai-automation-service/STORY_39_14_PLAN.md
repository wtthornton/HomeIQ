# Story 39.14: Service Layer Reorganization Plan

**Epic 39, Story 39.14**  
**Status:** In Progress

## Overview

Reorganize service layer by domain, improve dependency injection, and extract background workers to improve code maintainability.

## Current Service Structure Analysis

### Existing Domain Directories
- `automation/` - Automation services (YAML generation, deployment, validation)
- `clarification/` - Clarification detection and question generation
- `conversation/` - Conversation context and history
- `device/` - Device context services
- `entity/` - Entity extraction, enrichment, validation
- `learning/` - Pattern learning, RLHF, quality scoring
- `rag/` - RAG client and retrieval
- `blueprints/` - Blueprint matching and rendering
- `confidence/` - Confidence calculation
- `function_calling/` - Function calling registry

### Top-Level Services (Needs Organization)
- `alias_service.py` - Alias management → `device/` or new `management/`
- `component_detector.py` - Component detection → `entity/`
- `comprehensive_entity_enrichment.py` - Entity enrichment → `entity/`
- `device_matching.py` - Device matching → `device/`
- `entity_attribute_service.py` - Entity attributes → `entity/`
- `entity_capability_enrichment.py` - Capability enrichment → `entity/`
- `entity_context_cache.py` - Entity context caching → `entity/`
- `entity_id_validator.py` - Entity validation → `entity/`
- `entity_validator.py` - Entity validation → `entity/`
- `enrichment_context_fetcher.py` - Context fetching → `entity/`
- `ensemble_entity_validator.py` - Entity validation → `entity/`
- `error_recovery.py` - Error recovery → `core/` or `utils/`
- `event_driven_template_matcher.py` - Template matching → `blueprints/`
- `model_comparison_service.py` - Model comparison → `ml/` or `analytics/`
- `parallel_model_tester.py` - Model testing → `ml/` or `analytics/`
- `pattern_context_service.py` - Pattern context → `pattern/` (may be in pattern service)
- `reverse_engineering_metrics.py` - Metrics → `analytics/`
- `safety_validator.py` - Safety validation → `automation/` or `validation/`
- `service_container.py` - Service container → `core/`
- `service_validator.py` - Service validation → `core/` or `validation/`
- `suggestion_context_enricher.py` - Suggestion enrichment → `suggestion/`
- `synergy_context_service.py` - Synergy context → `pattern/` (may be in pattern service)
- `template_pattern_fusion.py` - Template/pattern fusion → `blueprints/` or `pattern/`
- `yaml_self_correction.py` - YAML correction → `automation/`
- `yaml_structure_validator.py` - YAML validation → `automation/`

## Reorganization Plan

### Phase 1: Create Domain Structure

Create clear domain directories:
- `services/domain/automation/` - All automation services
- `services/domain/entity/` - All entity services
- `services/domain/device/` - All device services
- `services/domain/pattern/` - Pattern and synergy services
- `services/domain/learning/` - Learning and RLHF services
- `services/domain/conversation/` - Conversation services
- `services/domain/rag/` - RAG services
- `services/domain/validation/` - Validation services
- `services/domain/analytics/` - Analytics and metrics
- `services/core/` - Core infrastructure (service container, error recovery)
- `services/workers/` - Background workers

### Phase 2: Move Services to Domains

Move top-level services to appropriate domains.

### Phase 3: Improve Dependency Injection

- Create service factories
- Use dependency injection for service dependencies
- Extract service initialization from routers

### Phase 4: Extract Background Workers

- Extract scheduler to `workers/`
- Extract any background job processing
- Improve worker lifecycle management

## Acceptance Criteria

- ✅ Services organized by domain
- ✅ Dependency injection improved
- ✅ Background workers extracted
- ✅ Code maintainability improved

