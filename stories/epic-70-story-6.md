# Story 70.6 -- Session Search (Cross-Conversation Recall)

<!-- docsmcp:start:user-story -->

> **As a** returning user, **I want** to say "last week I set up the garage lights — do the same for the shed" and have the agent recall that conversation, **so that** I don't have to re-explain my preferences and patterns

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that ha-ai-agent-service can search past conversations via PostgreSQL full-text search and return summarized relevant sessions as context for the current conversation — enabling cross-session continuity without relying solely on the Memory Brain.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Add a `search_past_conversations` tool that queries the existing messages table using PostgreSQL FTS (tsvector + GIN index). Group matches by conversation, select top 3, summarize each via cheap model, return as context. Adapted from Hermes Agent `session_search_tool.py` — uses PostgreSQL instead of SQLite FTS5.

See [Epic 70](stories/epic-70-hermes-self-improving-agent.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ha-ai-agent-service/src/services/session_search.py`
- `domains/automation-core/ha-ai-agent-service/src/tools/session_search_tools.py`
- `domains/automation-core/ha-ai-agent-service/alembic/versions/XXX_add_message_fts_index.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create alembic migration: add `search_vector tsvector` column to messages table, create GIN index, add trigger to auto-update on INSERT/UPDATE
- [ ] Implement `SessionSearch.search(query: str, exclude_conversation_id: str, limit: int = 3) → list[SessionSummary]`
- [ ] FTS query: split query into keywords joined with OR (broader recall), rank by ts_rank
- [ ] Group matches by conversation_id, deduplicate, select top N conversations by match count
- [ ] For each matched conversation: load messages, truncate to ~4K chars centered on match positions
- [ ] Summarize each conversation via cheap model (from 70.3): date, topic, what was done, outcome
- [ ] SessionSummary: conversation_id, date, topic, summary, match_score
- [ ] Add `search_past_conversations` tool schema (query: str, limit: int)
- [ ] Wire into tool_execution.py as a tool handler
- [ ] Exclude current conversation from search results
- [ ] Add SESSION_SEARCH_ENABLED (default true) to config.py
- [ ] Write unit tests: FTS query building, conversation grouping, summarization, exclusion

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] tsvector column + GIN index added to messages table via alembic migration
- [ ] `search_past_conversations` tool available to the agent
- [ ] Search returns top 3 relevant past conversations as summaries
- [ ] Current conversation excluded from search results
- [ ] Each summary includes: date, topic, what was done, outcome
- [ ] FTS uses OR-joined keywords for broad recall
- [ ] Feature disabled when SESSION_SEARCH_ENABLED=false

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 70](stories/epic-70-hermes-self-improving-agent.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_fts_query_builds_or_keywords` -- "garage light automation" → "garage | light | automation"
2. `test_search_groups_by_conversation` -- Matches from same conversation grouped together
3. `test_search_returns_top_3` -- More than 3 matching conversations → only top 3 returned
4. `test_search_excludes_current_conversation` -- Current conversation_id filtered out
5. `test_search_summarizes_matches` -- Each result includes date, topic, summary
6. `test_search_empty_results` -- No matches → empty list returned (not error)
7. `test_search_disabled_via_env` -- Tool unavailable when SESSION_SEARCH_ENABLED=false

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 70.3 (Smart Model Routing) — uses cheap model for summarization
- Existing conversation_service.py (messages table already exists)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Can use primary model if 70.3 not available
- [x] **N**egotiable -- Result limit, summary length, FTS strategy all tunable
- [x] **V**aluable -- Enables cross-session continuity for returning users
- [x] **E**stimable -- Clear scope: migration + search service + tool
- [x] **S**mall -- 3 points, leverages existing PostgreSQL infrastructure
- [x] **T**estable -- FTS queries, grouping, and exclusion are deterministic

<!-- docsmcp:end:invest -->
