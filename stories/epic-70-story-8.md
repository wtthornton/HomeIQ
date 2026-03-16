# Story 70.8 -- Prompt Caching

<!-- docsmcp:start:user-story -->

> **As a** system operator, **I want** stable system prompt content cached across conversation turns, **so that** input token costs are reduced ~75% on multi-turn conversations

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** S

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that ha-ai-agent-service maximizes prompt cache hits by structuring messages to keep stable content (system prompt, context injection) in a consistent prefix position. Reduces input token costs ~75% on multi-turn conversations.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Port the prompt caching strategy from Hermes Agent `prompt_caching.py`. For Anthropic: apply explicit `cache_control` markers to system prompt + last 3 turns. For OpenAI: restructure messages to keep system prompt stable (OpenAI automatically caches consistent prefixes). Both strategies maximize cache hits by ensuring the expensive context injection (entity inventories, device summaries, patterns) is in a stable position.

See [Epic 70](stories/epic-70-hermes-self-improving-agent.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ha-ai-agent-service/src/services/prompt_caching.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Implement `apply_anthropic_cache_control(messages) → messages` — add cache_control markers to system prompt + last 3 non-system messages
- [ ] Implement `optimize_openai_cache_layout(messages) → messages` — ensure system prompt is stable across turns (don't regenerate context that hasn't changed)
- [ ] Add context stability detection: hash context_builder output, skip regeneration if unchanged
- [ ] Wire into openai_client.py before API call (select strategy based on provider)
- [ ] Add PROMPT_CACHING_ENABLED (default true) to config.py
- [ ] Log cache-related metrics: context_hash, is_regenerated, estimated_cache_savings
- [ ] Write unit tests: marker placement, layout optimization, stability detection

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Anthropic messages include cache_control markers on system prompt + last 3 turns
- [ ] OpenAI messages structured for maximum automatic cache hits (stable prefix)
- [ ] Context not regenerated if context_builder output hash unchanged
- [ ] Cache strategy selected based on provider (Anthropic explicit, OpenAI layout)
- [ ] Feature disabled when PROMPT_CACHING_ENABLED=false

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 70](stories/epic-70-hermes-self-improving-agent.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_anthropic_cache_markers_applied` -- System prompt and last 3 messages get cache_control
2. `test_openai_stable_prefix` -- System prompt position consistent across turns
3. `test_context_stability_detection` -- Unchanged context skips regeneration
4. `test_context_change_triggers_regeneration` -- New entity in context triggers regeneration
5. `test_caching_disabled_via_env` -- No markers applied when PROMPT_CACHING_ENABLED=false

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- None — fully independent, can ship at any time

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Fully independent
- [x] **N**egotiable -- Cache strategy and TTL are tunable
- [x] **V**aluable -- ~75% input token cost reduction on multi-turn conversations
- [x] **E**stimable -- Clear scope: single module
- [x] **S**mall -- 2 points, smallest story in epic
- [x] **T**estable -- Marker placement and stability detection are deterministic

<!-- docsmcp:end:invest -->
