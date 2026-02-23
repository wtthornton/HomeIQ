---
epic: reusable-pattern-framework
priority: high
status: complete
estimated_duration: 2-3 weeks
risk_level: low
source: PRD – Automation Architecture & Reusable Patterns (Phase 2)
---

# Epic: Reusable Pattern Framework

**Status:** Complete
**Priority:** High
**Duration:** 2–3 weeks
**Risk Level:** Low
**PRD Reference:** `docs/planning/automation-architecture-reusable-patterns-prd.md` (Phase 2)

## Overview

Extract the three proven patterns from the Automation Improvements epic into shared, reusable abstractions that can be applied across HomeIQ services. This is the foundational infrastructure work that enables Phase 3 and Phase 4 domain extensions.

**Patterns to extract:**
1. **RAGContextService** – Generic keyword-match → corpus-load → context-inject interface
2. **UnifiedValidationRouter** – Orchestrated multi-backend validation with standardized response shape
3. **PostActionVerifier** – Action → verify → map-warnings interface for post-action feedback

## Objectives

1. Define abstract interfaces/base classes for all three patterns
2. Refactor existing automation implementations to use the new abstractions
3. Ensure zero regression in existing automation flow (RAG, validation, deploy verification)
4. Document patterns with usage examples so new domains can adopt quickly

## Success Criteria

- [x] `RAGContextService` interface defined; `AutomationRAGService` refactored to implement it
- [x] `UnifiedValidationRouter` template defined; `automation_yaml_validate_router` refactored to use it
- [x] `PostActionVerifier` interface defined; `ha_client.deploy_automation` refactored to use it
- [x] All existing tests pass (no regression) — 26/26 RAG tests pass; 45/45 shared pattern tests pass
- [x] Developer documentation with examples for each pattern (`libs/homeiq-patterns/README.md`)

---

## User Stories

### Story 1: Define RAGContextService Interface — Complete

**As a** service developer
**I want** a standard `RAGContextService` interface with keyword matching, corpus loading, and context formatting
**So that** I can create new domain RAG services (Energy, Security, Device Setup) without reimplementing boilerplate

**Acceptance Criteria:**
- [x] `RAGContextService` base class/interface defined in shared module → `libs/homeiq-patterns/src/homeiq_patterns/rag_context_service.py`
- [x] Methods: `detect_intent(prompt) → bool`, `load_corpus() → str`, `get_context(prompt) → str`
- [x] Configurable keyword list (tuple/set) and corpus path per implementation
- [x] Support for static file corpus and dynamically assembled corpus
- [x] `AutomationRAGService` refactored to extend `RAGContextService` → `domains/automation-core/ha-ai-agent-service/src/services/automation_rag_service.py`
- [x] Unit tests for base class and refactored `AutomationRAGService` → 10 base class tests + 26 existing tests pass

**Story Points:** 3
**Dependencies:** None
**Affected Services:** ha-ai-agent-service (8030)

---

### Story 2: Define RAGContextRegistry for Multi-Domain Context Assembly — Complete

**As a** the ContextBuilder in ha-ai-agent-service
**I want** a registry that manages multiple RAGContextService implementations
**So that** I can run multiple domain detections (sports, energy, security) in parallel and merge results into the prompt

**Acceptance Criteria:**
- [x] `RAGContextRegistry` class manages registered `RAGContextService` instances → `libs/homeiq-patterns/src/homeiq_patterns/rag_context_registry.py`
- [x] `register(service: RAGContextService)` method to add domain services
- [x] `get_all_context(prompt) → list[str]` runs all registered services and returns matching contexts
- [x] `ContextBuilder` refactored to use `RAGContextRegistry` instead of direct `AutomationRAGService` calls
- [x] Context injection order is deterministic (registration order)
- [x] Unit tests for registry with multiple mock services → 11 registry tests

**Story Points:** 3
**Dependencies:** Story 1 (RAGContextService interface)
**Affected Services:** ha-ai-agent-service (8030)

---

### Story 3: Define UnifiedValidationRouter Template — Complete

**As a** service developer
**I want** a reusable validation router template that orchestrates multiple validation backends and returns a standardized response
**So that** new validation endpoints (blueprints, scenes, scripts) follow the same pattern without duplicating orchestration logic

**Acceptance Criteria:**
- [x] `UnifiedValidationRouter` base class/template defined in shared module → `libs/homeiq-patterns/src/homeiq_patterns/unified_validation_router.py`
- [x] Standard request model: `content`, `normalize`, `validate_entities`, `validate_services` → `ValidationRequest`
- [x] Standard response model: `valid`, `errors`, `warnings`, `{domain}_validation` subsections, `score`, `fixed_content`, `fixes_applied` → `ValidationResponse`
- [x] Pluggable validation backend interface: `validate(content) → ValidationResult` → `ValidationBackend`
- [x] Error categorization logic (entity vs service vs schema errors) is configurable → `categorize_errors()` + `error_categories` dict
- [x] `automation_yaml_validate_router` refactored to extend `UnifiedValidationRouter` → `AutomationYAMLValidationRouter`
- [x] Unit tests for base template and refactored automation router → 13 tests

**Story Points:** 5
**Dependencies:** None
**Affected Services:** ai-automation-service-new (8024)

---

### Story 4: Define PostActionVerifier Interface — Complete

**As a** service developer
**I want** a standard `PostActionVerifier` interface for action → verify → map-warnings
**So that** new deploy/apply flows (blueprints, scenes, device setup) include post-action verification without reimplementing the pattern

**Acceptance Criteria:**
- [x] `PostActionVerifier` base class/interface defined in shared module → `libs/homeiq-patterns/src/homeiq_patterns/post_action_verifier.py`
- [x] Methods: `verify(action_result) → VerificationResult`, `map_warnings(verification) → list[Warning]`
- [x] `VerificationResult` model: `success`, `state`, `warnings`, `metadata` + backward-compat `verification_warning` property
- [x] `ha_client.deploy_automation` post-deploy logic refactored to use `PostActionVerifier` → `AutomationDeployVerifier`
- [x] Deployment service passes through verification results unchanged
- [x] Unit tests for base interface and refactored deploy verification → 11 tests

**Story Points:** 3
**Dependencies:** None
**Affected Services:** ai-automation-service-new (8024)

---

### Story 5: Developer Documentation for Reusable Patterns — Complete

**As a** developer extending HomeIQ
**I want** clear documentation explaining each reusable pattern with code examples
**So that** I can quickly implement new domain RAG services, validation endpoints, or post-action verifiers

**Acceptance Criteria:**
- [x] Documentation covers RAGContextService: interface, registration, corpus format, example implementation
- [x] Documentation covers UnifiedValidationRouter: template, backend interface, response shape, example
- [x] Documentation covers PostActionVerifier: interface, verification flow, warning mapping, example
- [x] Each pattern has a "quick start" showing minimal implementation steps
- [x] Linked from PRD and architecture docs → `libs/homeiq-patterns/README.md`

**Story Points:** 2
**Dependencies:** Stories 1-4

---

## Dependencies

```
Story 1 (RAGContextService) ──> Story 2 (RAGContextRegistry)
Story 3 (ValidationRouter)     (independent)
Story 4 (PostActionVerifier)   (independent)
Stories 1-4 ──────────────────> Story 5 (Documentation)
```

## Suggested Execution Order

1. **Stories 1, 3, 4** – Define all three interfaces (can be parallelized)
2. **Story 2** – RAGContextRegistry (depends on Story 1)
3. **Story 5** – Documentation (after all interfaces are stable)

## Implementation Artifacts

| Artifact | Path |
|----------|------|
| **Shared Patterns Package** | `libs/homeiq-patterns/` |
| RAGContextService | `libs/homeiq-patterns/src/homeiq_patterns/rag_context_service.py` |
| RAGContextRegistry | `libs/homeiq-patterns/src/homeiq_patterns/rag_context_registry.py` |
| UnifiedValidationRouter | `libs/homeiq-patterns/src/homeiq_patterns/unified_validation_router.py` |
| PostActionVerifier | `libs/homeiq-patterns/src/homeiq_patterns/post_action_verifier.py` |
| Developer Documentation | `libs/homeiq-patterns/README.md` |
| Unit Tests (45 tests) | `libs/homeiq-patterns/tests/` |
| **Refactored Services** | |
| AutomationRAGService (extends RAGContextService) | `domains/automation-core/ha-ai-agent-service/src/services/automation_rag_service.py` |
| ContextBuilder (uses RAGContextRegistry) | `domains/automation-core/ha-ai-agent-service/src/services/context_builder.py` |
| PromptAssemblyService (uses registry) | `domains/automation-core/ha-ai-agent-service/src/services/prompt_assembly_service.py` |
| AutomationYAMLValidationRouter (extends UnifiedValidationRouter) | `domains/automation-core/ai-automation-service-new/src/api/automation_yaml_validate_router.py` |
| AutomationDeployVerifier (extends PostActionVerifier) | `domains/automation-core/ai-automation-service-new/src/services/automation_deploy_verifier.py` |
| HomeAssistantClient (uses AutomationDeployVerifier) | `domains/automation-core/ai-automation-service-new/src/clients/ha_client.py` |

## References

- [PRD: Automation Architecture & Reusable Patterns](../docs/planning/automation-architecture-reusable-patterns-prd.md)
- [Epic: Automation Improvements (predecessor)](epic-homeiq-automation-improvements.md)
- [Epic: High-Value Domain Extensions (next)](epic-high-value-domain-extensions.md)
