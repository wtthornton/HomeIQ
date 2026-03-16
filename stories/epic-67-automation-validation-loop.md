# Epic 67: AI Automation Service — Self-Healing Validation Loop

<!-- docsmcp:start:metadata -->
**Status:** Proposed
**Priority:** P1 - High
**Estimated LOE:** ~1 week (1 developer)
**Dependencies:** Epic 66 (classification doc for context)

<!-- docsmcp:end:metadata -->

---

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

We are doing this so that ai-automation-service-new can automatically retry and fix LLM-generated YAML that fails validation, instead of returning broken output to the user and requiring manual iteration — closing the gap between the existing validation services (automation-linter, yaml-validation-service) and the YAML generation pipeline.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:goal -->
## Goal

Add an iterative validation-retry loop to ai-automation-service-new that runs generated YAML through automation-linter and yaml-validation-service, feeds errors back to the LLM for correction (up to 3 attempts), and returns the first passing result or the best attempt with clear error context.

**Tech Stack:** homeiq, Python >=3.11

<!-- docsmcp:end:goal -->

<!-- docsmcp:start:motivation -->
## Motivation

Currently ai-automation-service-new makes a single LLM call to generate Home Assistant automation YAML. When the output has validation errors (missing required fields, invalid entity references, schema violations), the user must manually identify and fix issues. The automation-linter and yaml-validation-service are already deployed and running but are not called inline during generation. Wiring them into a retry loop would dramatically improve first-attempt success rates at minimal infrastructure cost.

<!-- docsmcp:end:motivation -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Generated YAML is validated against automation-linter before being returned to the user
- [ ] When validation fails the LLM receives error context and retries (max 3 attempts configurable)
- [ ] First passing result is returned immediately without exhausting all retries
- [ ] If all retries fail the best attempt is returned with structured error details
- [ ] Retry loop adds less than 5 seconds average latency for passing-on-first-try cases
- [ ] Circuit breaker prevents retry loop from hanging if linter/validator services are down
- [ ] Metrics track: first-attempt pass rate and average retries needed and total generation latency

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:stories -->
## Stories

### 67.1 -- Validation Client Integration

**Points:** 2

Create a ValidationClient in ai-automation-service-new that calls automation-linter POST /lint and yaml-validation-service POST /validate. Include circuit breaker wrapping and timeout (2s per call). Return structured ValidationResult with pass/fail, findings list, and severity.

**Tasks:**
- [ ] Implement validation client integration
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Validation Client Integration is implemented, tests pass, and documentation is updated.

---

### 67.2 -- Retry Loop in YAML Generation Pipeline

**Points:** 3

Wrap the existing yaml_generation_service.generate() call in a retry loop. On validation failure, construct an error-context prompt with the original request + generated YAML + validation errors, and call the LLM again. Max retries configurable (default 3). Track attempt number in response metadata.

**Tasks:**
- [ ] Implement retry loop in yaml generation pipeline
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Retry Loop in YAML Generation Pipeline is implemented, tests pass, and documentation is updated.

---

### 67.3 -- Error Context Prompt Engineering

**Points:** 2

Design the error-feedback prompt template that tells the LLM what went wrong. Include: original user intent, generated YAML that failed, specific validation errors with line numbers, and instruction to fix only the errors without changing valid parts. Test with common failure patterns (missing triggers, invalid entity_id format, schema violations).

**Tasks:**
- [ ] Implement error context prompt engineering
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Error Context Prompt Engineering is implemented, tests pass, and documentation is updated.

---

### 67.4 -- Graceful Degradation & Circuit Breaker

**Points:** 2

When automation-linter or yaml-validation-service is unreachable, skip validation and return the raw LLM output with a warning flag (validated: false). Use existing CircuitBreaker from homeiq-resilience. Log AI FALLBACK: prefix for monitoring.

**Tasks:**
- [ ] Implement graceful degradation & circuit breaker
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Graceful Degradation & Circuit Breaker is implemented, tests pass, and documentation is updated.

---

### 67.5 -- Metrics & Observability

**Points:** 1

Add Prometheus metrics: yaml_generation_first_pass_rate, yaml_generation_retries_total, yaml_generation_latency_seconds (histogram with attempt label). Wire into existing observability-dashboard.

**Tasks:**
- [ ] Implement metrics & observability
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Metrics & Observability is implemented, tests pass, and documentation is updated.

---

### 67.6 -- Integration Tests

**Points:** 2

End-to-end tests covering: pass-on-first-try (no retry overhead), pass-on-second-try (error feedback works), all-retries-exhausted (returns best attempt), linter-down (graceful degradation). Use real automation-linter and yaml-validation-service instances.

**Tasks:**
- [ ] Implement integration tests
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Integration Tests is implemented, tests pass, and documentation is updated.

---

<!-- docsmcp:end:stories -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- ai-automation-service-new is at domains/automation-core/ai-automation-service-new/
- Existing OpenAI client in src/clients/openai_client.py — reuse for retry calls
- automation-linter at port 8034 has POST /lint endpoint
- yaml-validation-service at port 8041 has POST /validate endpoint
- Use homeiq-resilience CircuitBreaker (3 failures and 60s recovery) for both validation services
- Error prompt should use structured JSON format not free text to improve LLM correction accuracy

**Project Structure:** 0 packages, 0 modules, 0 public APIs

### Expert Recommendations

- **Security Expert** (76%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (64%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:non-goals -->
## Out of Scope / Future Considerations

- Adding tool-calling or multi-step agent behavior — this is a simple retry loop not an agent upgrade
- Changing the CLI deterministic path which bypasses LLM entirely
- Modifying automation-linter or yaml-validation-service APIs

<!-- docsmcp:end:non-goals -->

<!-- docsmcp:start:success-metrics -->
## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| All 7 acceptance criteria met | 0/7 | 7/7 | Checklist review |
| All 6 stories completed | 0/6 | 6/6 | Sprint board |

<!-- docsmcp:end:success-metrics -->

<!-- docsmcp:start:implementation-order -->
## Implementation Order

1. Story 67.1: Validation Client Integration
2. Story 67.2: Retry Loop in YAML Generation Pipeline
3. Story 67.3: Error Context Prompt Engineering
4. Story 67.4: Graceful Degradation & Circuit Breaker
5. Story 67.5: Metrics & Observability
6. Story 67.6: Integration Tests

<!-- docsmcp:end:implementation-order -->

<!-- docsmcp:start:risk-assessment -->
## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| No risks identified | - | - | Consider adding risks during planning |

**Expert-Identified Risks:**

- **Security Expert**: *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*

<!-- docsmcp:end:risk-assessment -->

<!-- docsmcp:start:files-affected -->
## Files Affected

| File | Story | Action |
|---|---|---|
| Files will be determined during story refinement | - | - |

<!-- docsmcp:end:files-affected -->
