# Story 70.3 -- Smart Model Routing

<!-- docsmcp:start:user-story -->

> **As a** system operator, **I want** simple state-check queries to route to a cheap/fast model, **so that** API costs drop 40-60% on routine queries without degrading complex automation generation

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that ha-ai-agent-service routes ~60% of queries (simple state checks like "is the kitchen light on?") to a cheap model (gpt-4.1-mini) while preserving the primary model (gpt-5.2-codex) for complex automation requests. This is the foundation for 70.4 (compression), 70.5 (delegation), and 70.6 (session search) which all use the cheap model for auxiliary tasks.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Implement a lightweight request classifier that routes messages to cheap or primary models based on heuristics. Ported from Hermes Agent `smart_model_routing.py`, adapted to HomeIQ's HA domain with automation-specific keyword detection.

**Relationship to Epic 69 (Story 69.1):** This provides the static heuristic routing engine. Epic 69 adds eval-score-driven adaptive routing on top. They compose — this is the base, 69.1 adds the feedback loop.

See [Epic 70](stories/epic-70-hermes-self-improving-agent.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ha-ai-agent-service/src/services/smart_routing.py`
- `domains/automation-core/ha-ai-agent-service/src/config.py` (add settings)

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add to config.py: CHEAP_MODEL (default "gpt-4.1-mini"), CHEAP_MODEL_BASE_URL, CHEAP_MODEL_API_KEY, ROUTING_ENABLED (default true), CHEAP_MODEL_MAX_CHARS (160), CHEAP_MODEL_MAX_WORDS (28)
- [ ] Implement `choose_model_route(message: str, settings: Settings) → ModelRoute(model, base_url, api_key, reason, is_cheap)`
- [ ] Cheap model criteria: length < MAX_CHARS AND words < MAX_WORDS AND no code blocks AND no URLs AND no automation keywords
- [ ] Automation keyword blocklist: create, set up, configure, automate, schedule, condition, trigger, when, if, automation, blueprint, scene, script
- [ ] Primary model fallback on any routing exception
- [ ] Wire into `chat_endpoints.py` before `_run_openai_loop()` — pass model config through
- [ ] Ensure tool-calling iterations beyond first always use primary model
- [ ] Log routing decisions: model, reason, message_length, word_count
- [ ] Write unit tests: simple queries → cheap, complex queries → primary, edge cases

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] "Is the kitchen light on?" routes to cheap model
- [ ] "Create an automation that turns off lights at midnight" routes to primary model
- [ ] Messages with code blocks, URLs, or >160 chars route to primary model
- [ ] Routing exceptions fall back to primary model (never degrade on error)
- [ ] Tool-calling iterations after the first use primary model
- [ ] Routing decision logged with model and reason
- [ ] Feature disabled when ROUTING_ENABLED=false

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 70](stories/epic-70-hermes-self-improving-agent.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_route_simple_state_query_to_cheap` -- "Is the bedroom light on?" → cheap model
2. `test_route_automation_request_to_primary` -- "Create a motion automation for the hallway" → primary
3. `test_route_long_message_to_primary` -- 200-char message → primary regardless of content
4. `test_route_code_block_to_primary` -- Message with ``` block → primary
5. `test_route_url_to_primary` -- Message with URL → primary
6. `test_route_fallback_on_exception` -- Config error → primary model (never fails)
7. `test_route_disabled_via_env` -- ROUTING_ENABLED=false → always primary

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- None — first story to implement in Epic 70

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Fully independent, no prerequisites
- [x] **N**egotiable -- Keyword list and thresholds are tunable
- [x] **V**aluable -- 40-60% cost reduction on simple queries
- [x] **E**stimable -- Clear scope: classifier + config + integration
- [x] **S**mall -- 3 points, single module
- [x] **T**estable -- Each routing decision is deterministic and testable

<!-- docsmcp:end:invest -->
