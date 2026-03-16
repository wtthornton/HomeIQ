# Story 70.7 -- User Modeling

<!-- docsmcp:start:user-story -->

> **As a** returning user, **I want** the agent to learn my preferences over time (confirmation style, trigger preferences, risk tolerance), **so that** interactions become more personalized and efficient across sessions

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that ha-ai-agent-service builds cross-session user preference profiles that shape agent behavior — learning from interaction patterns to provide increasingly personalized automation suggestions and conversation flow.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Build a user modeling system adapted from Hermes Agent's Honcho integration. Extract preference signals from conversations (background task), store as per-dimension profiles in PostgreSQL, inject into system prompt to shape agent behavior. Integrates with Epic 68 (proactive agent can query risk tolerance for autonomous execution thresholds).

See [Epic 70](stories/epic-70-hermes-self-improving-agent.md) for project context and shared definitions.

**Profile dimensions:**
- Confirmation preference: always confirm / confirm risky only / auto-approve low-risk
- Trigger preferences: prefers motion sensors vs time-based vs state-based
- Naming patterns: how user refers to rooms/devices (natural language → entity mapping)
- Risk tolerance: conservative → aggressive for autonomous actions
- Communication style: verbose explanations vs terse responses

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ha-ai-agent-service/src/services/user_modeling/__init__.py`
- `domains/automation-core/ha-ai-agent-service/src/services/user_modeling/profile_store.py`
- `domains/automation-core/ha-ai-agent-service/src/services/user_modeling/preference_extractor.py`
- `domains/automation-core/ha-ai-agent-service/src/services/user_modeling/profile_injector.py`
- `domains/automation-core/ha-ai-agent-service/alembic/versions/XXX_add_user_profiles_table.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create alembic migration: `agent.user_profiles` table (id, user_id VARCHAR, dimension VARCHAR(64), value JSONB, confidence FLOAT, updated_at TIMESTAMP, expires_at TIMESTAMP)
- [ ] Implement `ProfileStore` (upsert by user_id+dimension, get_profile, delete_profile, prune_expired)
- [ ] Implement `PreferenceExtractor.extract(conversation_messages) → list[PreferenceSignal]` using LLM structured output
- [ ] PreferenceSignal: dimension, value, confidence (0.0-1.0)
- [ ] Confidence update rule: new_confidence = max(existing × 0.8 + new × 0.2, new) — decay old, boost confirmed
- [ ] Implement `ProfileInjector.inject(user_id) → str` — format profile as system prompt section (200-token budget)
- [ ] Wire extraction as fire-and-forget background task in chat_endpoints.py (like memory_extractor)
- [ ] Wire injection into prompt_assembly_service.py (200-token budget, `## User Preferences` section)
- [ ] Add admin-api endpoint: GET /api/v1/user-profiles/{user_id} (read profile), DELETE /api/v1/user-profiles/{user_id} (reset)
- [ ] Add USER_MODELING_ENABLED (default true), PROFILE_TTL_DAYS (default 90) to config.py
- [ ] Write unit tests: store CRUD, extraction, injection, confidence decay, TTL expiry

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] User profiles stored in `agent.user_profiles` with per-dimension confidence scores
- [ ] Preferences extracted from conversations as background task (non-blocking)
- [ ] Confidence scores decay over time and increase with repeated confirmation
- [ ] Profile injected into system prompt (200-token budget)
- [ ] Expired preferences (>90 days default) automatically pruned
- [ ] User can view and reset their profile via admin-api
- [ ] Feature disabled when USER_MODELING_ENABLED=false

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 70](stories/epic-70-hermes-self-improving-agent.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_profile_store_upsert_new_dimension` -- First preference for a dimension creates new record
2. `test_profile_store_upsert_existing_dimension` -- Repeated preference updates confidence
3. `test_confidence_decay_formula` -- Old confidence decays, new signal boosts
4. `test_extractor_identifies_confirmation_preference` -- User always says "yes deploy it" → auto-approve signal
5. `test_extractor_identifies_trigger_preference` -- User repeatedly chooses motion sensors → motion preference
6. `test_injector_respects_token_budget` -- Injected profile text ≤ 200 tokens
7. `test_prune_expired_profiles` -- Preferences older than TTL removed
8. `test_admin_api_get_profile` -- GET returns user's profile dimensions
9. `test_admin_api_delete_profile` -- DELETE resets user's profile
10. `test_modeling_disabled_via_env` -- No extraction when USER_MODELING_ENABLED=false

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Existing conversation_service.py (messages for extraction)
- Epic 68 (Proactive Agent) can consume profiles for autonomous execution thresholds

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- No hard dependencies on other 70.x stories
- [x] **N**egotiable -- Dimensions, TTL, confidence formula all tunable
- [x] **V**aluable -- Increasingly personalized interactions across sessions
- [x] **E**stimable -- Clear scope: store + extractor + injector + admin API
- [ ] **S**mall -- 5 points, multiple components but well-defined boundaries
- [x] **T**estable -- Confidence math, extraction, injection, TTL all testable

<!-- docsmcp:end:invest -->
