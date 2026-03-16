# Story 70.1 -- Procedural Skill Learning

<!-- docsmcp:start:user-story -->

> **As a** returning user, **I want** the agent to remember successful automation procedures from past conversations, **so that** I don't have to repeat the same multi-turn discovery process for common patterns

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that ha-ai-agent-service can extract reusable procedures from successful multi-turn automation conversations, store them as skills in PostgreSQL with pgvector embeddings, and recall semantically relevant skills for future requests — reducing repeat conversations from 5+ turns to 1-2 turns.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Implement the self-improving skill learning system. After a successful automation conversation (5+ tool-calling iterations, or user explicitly requests save), extract the procedure into a structured skill. Store in PostgreSQL `agent.skills` table with pgvector embedding for semantic recall. Recall relevant skills during prompt assembly and inject into system prompt (500-token budget).

Ported from Hermes Agent `skill_manager_tool.py` + `skills_tool.py`. Adapted: PostgreSQL instead of flat files, pgvector instead of filename matching, homeiq_memory for embeddings.

See [Epic 70](stories/epic-70-hermes-self-improving-agent.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ha-ai-agent-service/src/services/skill_learning/__init__.py`
- `domains/automation-core/ha-ai-agent-service/src/services/skill_learning/skill_store.py`
- `domains/automation-core/ha-ai-agent-service/src/services/skill_learning/skill_extractor.py`
- `domains/automation-core/ha-ai-agent-service/src/services/skill_learning/skill_recall.py`
- `domains/automation-core/ha-ai-agent-service/src/tools/skill_tools.py`
- `domains/automation-core/ha-ai-agent-service/alembic/versions/XXX_add_skills_table.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create alembic migration: `agent.skills` table (id UUID, name VARCHAR(64), description VARCHAR(1024), category VARCHAR(64), area_pattern VARCHAR(128), trigger_types JSONB, body TEXT, embedding vector(384), created_at, updated_at, use_count INT DEFAULT 0, last_used_at TIMESTAMP)
- [ ] Implement `SkillStore` class (create, get, update, delete, search_by_embedding, increment_use_count)
- [ ] Implement `SkillExtractor.extract(conversation_messages, tool_calls, outcome) → Skill` using LLM structured output
- [ ] Implement `SkillRecall.recall(user_message, area_id=None, category=None, limit=3) → list[Skill]`
- [ ] Add `save_automation_skill` tool schema to tool_schemas.py (name, description, category)
- [ ] Add `recall_skills` internal function (not exposed as tool — called by prompt_assembly)
- [ ] Wire skill recall into `prompt_assembly_service.py` after memory injection (500-token budget, `## Relevant Procedures` section)
- [ ] Add trigger heuristics in `chat_endpoints.py` after `_run_openai_loop()` returns (fire-and-forget `asyncio.create_task`)
- [ ] Add `ENABLE_SKILL_LEARNING=true` env var to config.py
- [ ] Write unit tests: SkillStore CRUD, SkillExtractor extraction, SkillRecall search + filtering

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Skills table created in `agent` schema with pgvector embedding column
- [ ] Agent extracts a skill after a 5+ iteration successful conversation (fire-and-forget)
- [ ] Agent extracts a skill when user says "remember this" or "save this pattern"
- [ ] Extracted skills include: name, description, category, area_pattern, step-by-step procedure, known pitfalls
- [ ] Skills recalled via embedding similarity (cosine distance) with optional area/category filter
- [ ] Top 3 relevant skills injected into system prompt (500-token budget)
- [ ] use_count and last_used_at tracked for each recall
- [ ] Feature disabled when ENABLE_SKILL_LEARNING=false

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 70](stories/epic-70-hermes-self-improving-agent.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_skill_store_create_and_retrieve` -- Create a skill and retrieve by ID
2. `test_skill_store_search_by_embedding` -- Search skills by embedding similarity returns ranked results
3. `test_skill_extractor_extracts_from_conversation` -- Extract skill from a 6-turn automation conversation
4. `test_skill_extractor_skips_short_conversations` -- No extraction for conversations under 5 iterations
5. `test_skill_extractor_explicit_save_request` -- Extract when user message contains "remember this"
6. `test_skill_recall_filters_by_area` -- Recall filters results by area_pattern match
7. `test_skill_recall_respects_token_budget` -- Recalled skills fit within 500-token budget
8. `test_skill_recall_increments_use_count` -- use_count incremented on each recall
9. `test_skill_learning_disabled_via_env` -- No extraction when ENABLE_SKILL_LEARNING=false

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Embedding model: use same model as homeiq_memory (sentence-transformers, 384-dim)
- Extraction prompt should output structured JSON: {name, description, category, area_pattern, trigger_types, body}
- Skill body format: markdown with sections (## Steps, ## Entity Selection, ## Validation, ## Pitfalls)
- Fire-and-forget extraction: don't block the chat response on skill creation
- Skills with use_count=0 and age >90 days should be candidates for pruning (future story)

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- homeiq-memory library (complete — provides embedding generation)
- pgvector extension in PostgreSQL (already installed for Memory Brain)
- Story 70.2 (Skills Guard) MUST ship together — no unscanned skills allowed

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [ ] **I**ndependent -- Requires 70.2 (ships together), otherwise independent
- [x] **N**egotiable -- Trigger heuristics and token budget are tunable
- [x] **V**aluable -- Reduces repeat conversations from 5+ turns to 1-2 turns
- [x] **E**stimable -- Clear scope: store + extractor + recall + integration
- [ ] **S**mall -- 5 points, borderline — could split extraction and recall
- [x] **T**estable -- Clear criteria: extraction triggers, recall accuracy, budget compliance

<!-- docsmcp:end:invest -->
