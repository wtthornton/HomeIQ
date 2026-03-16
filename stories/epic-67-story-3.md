# Story 67.3 -- Error Context Prompt Engineering

<!-- docsmcp:start:user-story -->

> **As a** developer, **I want** an optimized error-feedback prompt template for LLM retry calls, **so that** the LLM can effectively fix validation errors without changing valid parts

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that the LLM receives optimally structured error feedback enabling it to fix validation errors without changing valid YAML parts.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Design the error-feedback prompt template that tells the LLM what went wrong. Include: original user intent, generated YAML that failed, specific validation errors with line numbers, and instruction to fix only the errors without changing valid parts.

See [Epic 67](stories/epic-67-automation-validation-loop.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ai-automation-service-new/src/prompts/error_feedback.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create error feedback prompt template (`domains/automation-core/ai-automation-service-new/src/prompts/error_feedback.py`)
- [ ] Test with missing trigger failures (`tests/unit/test_error_feedback_prompt.py`)
- [ ] Test with invalid entity_id failures (`tests/unit/test_error_feedback_prompt.py`)
- [ ] Test with schema violation failures (`tests/unit/test_error_feedback_prompt.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Prompt template includes original intent and failed YAML and error details
- [ ] Uses structured JSON format for error context
- [ ] Instructs LLM to fix only errors and preserve valid parts
- [ ] Tested against common failure patterns

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 67](stories/epic-67-automation-validation-loop.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_prompt_template_includes_original_intent_failed_yaml_error_details` -- Prompt template includes original intent and failed YAML and error details
2. `test_ac2_uses_structured_json_format_error_context` -- Uses structured JSON format for error context
3. `test_ac3_instructs_llm_fix_only_errors_preserve_valid_parts` -- Instructs LLM to fix only errors and preserve valid parts
4. `test_ac4_tested_against_common_failure_patterns` -- Tested against common failure patterns

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (70%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (65%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- List stories or external dependencies that must complete first...

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Can be developed and delivered independently
- [ ] **N**egotiable -- Details can be refined during implementation
- [x] **V**aluable -- Delivers value to a user or the system
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
