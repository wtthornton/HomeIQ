# Epic 70: Self-Improving Agent — Hermes-Inspired Learning & Delegation

<!-- docsmcp:start:metadata -->
**Status:** Proposed
**Priority:** P1 - High
**Estimated LOE:** ~3-4 weeks (1 developer)
**Dependencies:** Epic 60 (chat endpoint refactor, complete), Memory Brain lib (homeiq-memory, complete)
**Enhances:** Epic 69 (model routing — Story 70.3 provides the routing engine that 69.1 classifies for), Epic 68 (proactive agent — learns from skill library)
**Inspiration:** [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) — MIT licensed, patterns ported, no runtime dependency

<!-- docsmcp:end:metadata -->

---

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

We are doing this so that ha-ai-agent-service evolves from a stateless request-response agent into a self-improving system that learns reusable procedures from successful multi-turn conversations, delegates complex multi-area requests to parallel subagents, compresses long conversation context intelligently, searches past sessions for relevant prior work, and routes requests to cost-appropriate models — making the agent faster, cheaper, and smarter with every interaction.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:goal -->
## Goal

Port 8 self-improving patterns from Hermes Agent (NousResearch) into HomeIQ's ha-ai-agent-service, adapted to our PostgreSQL-backed, FastAPI microservice architecture. Zero runtime dependency on hermes-agent — only the patterns are ported.

**Tech Stack:** homeiq, Python >=3.11

**Architectural principle:** Every autonomy feature ships with its safety pair.

| Autonomy Feature | Safety Pair |
|---|---|
| Skill Learning (70.1) | Skills Guard (70.2) — scan every generated skill |
| Subagent Delegation (70.5) | Budget controls (70.5d) — cap tokens/cost per subagent |
| Session Search (70.6) | PII filtering — don't leak cross-user conversation data |
| User Modeling (70.7) | Data retention — configurable TTL, opt-out |

<!-- docsmcp:end:goal -->

<!-- docsmcp:start:motivation -->
## Motivation

ha-ai-agent-service handles ~60% simple state queries and ~40% complex automation requests. Today it uses the same model, same context strategy, and same single-threaded loop for all requests. It has no memory of successful procedures, no ability to decompose multi-area requests, and truncates rather than compresses long conversations. Users repeat the same multi-turn discovery process for common automation patterns across rooms.

Hermes Agent (8K GitHub stars, MIT license) has solved these problems for general-purpose chat agents. Their patterns — procedural skill learning, subagent delegation, smart model routing, context compression, session search, prompt caching, skills guard, and user modeling — map directly to HomeIQ's conversational agent use case. This epic ports the patterns without taking the dependency.

**Cross-review validated:** Two independent project reviews (TheStudio pipeline architecture) confirmed that learning features (skills, memory, user modeling) are highest-value for interactive chat assistants, while defensive features (injection scanning, budget control) are universally important. Both agreed context compression is universally beneficial.

<!-- docsmcp:end:motivation -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Agent auto-creates reusable skill files after complex (5+ turn) successful automation conversations
- [ ] All agent-generated skills are security-scanned before storage (100+ threat patterns)
- [ ] Simple queries (state checks, "is X on?") route to cheap model, complex queries to primary model
- [ ] Conversations exceeding 50% context window are intelligently compressed (preserve first 3 + last 4 turns, summarize middle)
- [ ] Complex multi-area requests spawn up to 3 parallel subagents with area-scoped context
- [ ] Past conversations are searchable via PostgreSQL FTS and returned as summarized context
- [ ] User preferences (confirmation style, trigger preferences, risk tolerance) are modeled across sessions
- [ ] Prompt caching reduces input token costs on multi-turn conversations
- [ ] All features have kill switches via environment variables
- [ ] No runtime dependency on hermes-agent package

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:stories -->
## Stories

### 70.1 -- Procedural Skill Learning

**Points:** 5

**The self-improving core.** After a successful multi-turn (5+) automation conversation, the agent extracts the procedure into a reusable skill stored in PostgreSQL. Skills are recalled via embedding similarity (homeiq_memory) when future requests match. Skills are updated when the agent encounters uncovered edge cases during execution.

**Trigger heuristics** (ported from Hermes `skill_manager_tool.py`):
- Complex task succeeds after 5+ tool-calling iterations
- Error handling overcomes obstacles during the conversation
- User corrections lead to a successful outcome
- User explicitly says "remember this" or "save this pattern"

**Skill format:** YAML frontmatter (name, description, category, area_pattern, trigger_types) + markdown body (step-by-step procedure, entity selection hints, validation notes, known pitfalls).

**Storage:** PostgreSQL `agent.skills` table + pgvector embedding for semantic recall. NOT flat files.

**Integration points:**
- New tool `save_automation_skill` in tool_schemas.py (LLM decides when to save)
- New tool `recall_skills` called by prompt_assembly_service before building context
- Skills injected into system prompt under `## Relevant Procedures` section (500-token budget)
- Skill recall uses homeiq_memory embedding search with category + area filtering

**Files:**
- `domains/automation-core/ha-ai-agent-service/src/services/skill_learning/skill_store.py`
- `domains/automation-core/ha-ai-agent-service/src/services/skill_learning/skill_extractor.py`
- `domains/automation-core/ha-ai-agent-service/src/services/skill_learning/skill_recall.py`
- `domains/automation-core/ha-ai-agent-service/src/tools/skill_tools.py`
- `domains/automation-core/ha-ai-agent-service/alembic/versions/XXX_add_skills_table.py`

**Tasks:**
- [ ] Create `agent.skills` table (id, name, description, category, area_pattern, trigger_types, body, embedding, created_at, updated_at, use_count, last_used_at)
- [ ] Implement SkillStore (CRUD + embedding search via homeiq_memory)
- [ ] Implement SkillExtractor (analyze conversation trajectory → extract procedure)
- [ ] Implement SkillRecall (query by embedding similarity + category + area filter)
- [ ] Add `save_automation_skill` and `recall_skills` tool schemas
- [ ] Wire skill recall into prompt_assembly_service (500-token budget, after memory injection)
- [ ] Add trigger heuristics to `_run_openai_loop()` exit path (fire-and-forget extraction)
- [ ] Write unit tests for store, extractor, recall
- [ ] Add `ENABLE_SKILL_LEARNING=true` env var kill switch

---

### 70.2 -- Skills Guard (Security Scanner)

**Points:** 3

**Safety pair for 70.1.** Every skill created by the agent (or recalled from storage) is scanned for malicious patterns before use. Ported from Hermes `skills_guard.py` with HomeIQ-specific additions for HA security.

**Threat categories** (100+ regex patterns):
- Prompt injection (role hijacking, "ignore previous instructions", hidden Unicode)
- HA-specific: `shell_command`, `command_line`, `python_script`, `pyscript` service calls
- Exfiltration (env var theft, credential access, DNS tunneling)
- Destructive (recursive deletion, system file overwrites)
- Structural anomalies (excessive size, binary content, symlink escape)

**Integration:** Scanner runs synchronously before skill storage (block on fail) and asynchronously on skill recall (warn on fail, exclude from context).

**Files:**
- `domains/automation-core/ha-ai-agent-service/src/services/skill_learning/skills_guard.py`
- `domains/automation-core/ha-ai-agent-service/src/services/skill_learning/threat_patterns.py`

**Tasks:**
- [ ] Port regex threat pattern library from Hermes skills_guard.py (~100 patterns)
- [ ] Add HomeIQ-specific patterns (HA shell_command, command_line, pyscript, hassio, rest_command)
- [ ] Implement SkillsGuard.scan() → ScanResult (verdict, findings, severity)
- [ ] Wire into SkillStore.create() as blocking pre-check
- [ ] Wire into SkillRecall as async filter (exclude flagged skills from context)
- [ ] Add invisible character detection (zero-width, directional override Unicode)
- [ ] Write unit tests with known-bad skill samples
- [ ] Log all scan results for audit trail

---

### 70.3 -- Smart Model Routing

**Points:** 3

Route simple queries to a cheap/fast model and complex queries to the primary model. Ported from Hermes `smart_model_routing.py`, adapted to HomeIQ's domain.

**Routing heuristics:**
- **Cheap model** (gpt-4.1-mini / Claude Haiku): message <160 chars AND <28 words AND no code blocks/URLs AND no automation keywords (create, set up, configure, automate, schedule, condition, trigger)
- **Primary model** (gpt-5.2-codex): everything else
- **Fallback:** any routing failure → primary model (never degrade on error)

**Relationship to Epic 69:** This story provides the routing engine. Epic 69 Story 69.1 adds eval-score-driven adaptive routing on top. They compose — 70.3 is the heuristic base, 69.1 adds the feedback loop.

**Files:**
- `domains/automation-core/ha-ai-agent-service/src/services/smart_routing.py`
- `domains/automation-core/ha-ai-agent-service/src/config.py` (add CHEAP_MODEL, CHEAP_MODEL_MAX_CHARS, CHEAP_MODEL_MAX_WORDS)

**Tasks:**
- [ ] Implement `choose_model_route(message: str, settings: Settings) → ModelRoute`
- [ ] Add CHEAP_MODEL, CHEAP_MODEL_BASE_URL, ROUTING_ENABLED env vars
- [ ] Wire into chat_endpoints.py before `_run_openai_loop()` call
- [ ] Log routing decisions (model chosen, reason, message length)
- [ ] Track cost savings (estimated tokens × model pricing)
- [ ] Write unit tests for routing heuristics (simple/complex/edge cases)
- [ ] Ensure tool-calling iterations always use primary model (only first call can route cheap)

---

### 70.4 -- Context Compression

**Points:** 3

When conversation exceeds 50% of context window, preserve first 3 + last 4 turns, LLM-summarize everything in between. Ported from Hermes `context_compressor.py`.

**Algorithm:**
1. Check token count after each `_run_openai_loop()` iteration
2. If tokens > `context_length × 0.5` → trigger compression
3. Protect first 3 turns (system prompt + initial exchange) and last 4 turns (recent context)
4. Summarize middle turns via cheap model (from 70.3) with temperature=0.3, target ~2500 tokens
5. Summary captures: actions taken, results obtained, decisions made, data needed to resume
6. Sanitize orphaned tool_call/tool_result pairs (prevent API rejection)
7. If summarization fails → drop middle turns without summary (graceful fallback)

**Replaces:** Current crude truncation in prompt_assembly_service.py (hard 16K budget).

**Files:**
- `domains/automation-core/ha-ai-agent-service/src/services/context_compressor.py`

**Tasks:**
- [ ] Implement ContextCompressor.compress(messages, threshold_pct, protect_head, protect_tail)
- [ ] Implement summarization prompt (extract actions, results, decisions, resume data)
- [ ] Add orphaned tool_call/tool_result pair sanitization
- [ ] Wire into prompt_assembly_service.py (replace truncation with compression)
- [ ] Use cheap model from 70.3 for summarization calls
- [ ] Add CONTEXT_COMPRESSION_ENABLED, COMPRESSION_THRESHOLD_PCT env vars
- [ ] Write unit tests (threshold detection, turn protection, orphan cleanup, fallback)
- [ ] Track compression stats (tokens before/after, turns compressed)

---

### 70.5 -- Subagent Delegation

**Points:** 5

Spawn up to 3 parallel child agent loops with restricted toolsets and area-scoped context. Ported from Hermes `delegate_tool.py`.

**Pattern:**
- Parent agent recognizes multi-area request ("set up automations for kitchen, bedroom, and living room")
- Spawns up to 3 child `_run_openai_loop()` instances, each with:
  - Area-filtered context (only entities/devices from assigned area)
  - Restricted toolset (no `delegate_task`, no `save_automation_skill`)
  - Fresh conversation (no parent history — all context passed via `context` parameter)
  - Per-subagent token budget (configurable, default 8K output tokens)
  - Max 15 iterations (half of parent's limit)
- Parent blocks until all children complete via `asyncio.gather()`
- Children return structured results: status, summary, tool_trace, tokens_used, duration
- Parent synthesizes child results into unified response

**Safety pair:** Per-subagent token/cost budget. If a subagent exceeds budget, it's terminated and returns partial results.

**Files:**
- `domains/automation-core/ha-ai-agent-service/src/services/delegation/delegate_service.py`
- `domains/automation-core/ha-ai-agent-service/src/services/delegation/subagent_runner.py`
- `domains/automation-core/ha-ai-agent-service/src/tools/delegate_tools.py`

**Tasks:**
- [ ] Implement SubagentRunner (lightweight wrapper around `_run_openai_loop()` with scoped context)
- [ ] Implement DelegateService (dispatch tasks, collect results, enforce budgets)
- [ ] Add `delegate_task` tool schema (goal, context, area, toolsets, max_iterations)
- [ ] Build area-scoped context builder (filter context_builder output by area_id)
- [ ] Implement per-subagent token budget enforcement
- [ ] Wire into tool_execution.py as a tool handler
- [ ] Add DELEGATION_ENABLED, MAX_SUBAGENTS=3, SUBAGENT_MAX_TOKENS=8000 env vars
- [ ] Write unit tests (single task, batch, budget exceeded, area scoping)
- [ ] Log subagent lifecycle (spawned, completed, failed, budget_exceeded)

---

### 70.6 -- Session Search (Cross-Conversation Recall)

**Points:** 3

Search past conversations via PostgreSQL full-text search. Return summarized relevant sessions as context for the current conversation.

**Implementation (adapted from Hermes `session_search_tool.py`):**
1. User asks about prior work ("last week I set up an automation for the garage...")
2. Agent calls `search_past_conversations` tool with query keywords
3. PostgreSQL FTS query against `agent.messages` table (tsvector index)
4. Group matches by conversation_id, deduplicate, select top 3 sessions
5. For each session: load conversation, truncate to ~4K chars centered on matches
6. Summarize each session via cheap model (from 70.3)
7. Return per-session summaries with metadata (date, topic, outcome)

**Safety:** Exclude current conversation from results. Filter by user_id if multi-user is enabled.

**Leverages existing infrastructure:** conversation_service.py already stores messages in PostgreSQL. This story adds a tsvector index and search tool.

**Files:**
- `domains/automation-core/ha-ai-agent-service/src/services/session_search.py`
- `domains/automation-core/ha-ai-agent-service/src/tools/session_search_tools.py`
- `domains/automation-core/ha-ai-agent-service/alembic/versions/XXX_add_message_fts_index.py`

**Tasks:**
- [ ] Add tsvector column + GIN index to messages table (alembic migration)
- [ ] Implement SessionSearch.search(query, exclude_conversation_id, limit=3)
- [ ] Implement session summarization (cheap model, ~4K char input, ~500 token output)
- [ ] Add `search_past_conversations` tool schema
- [ ] Wire into tool_execution.py as a tool handler
- [ ] Add SESSION_SEARCH_ENABLED env var
- [ ] Write unit tests (FTS query, grouping, summarization, exclusion)

---

### 70.7 -- User Modeling

**Points:** 5

Build cross-session user preference profiles that shape agent behavior. Adapted from Hermes Honcho integration.

**Profile dimensions:**
- Confirmation preference (always confirm / confirm risky only / auto-approve low-risk)
- Trigger preferences (prefers motion sensors vs time-based vs state-based)
- Naming patterns (how user refers to rooms/devices — natural language → entity mapping)
- Risk tolerance (conservative → aggressive for autonomous actions)
- Communication style (verbose explanations vs terse responses)

**Extraction:** Background task after each conversation (like existing memory_extractor). LLM analyzes conversation for preference signals. Stored in `agent.user_profiles` table with per-dimension scores.

**Injection:** Profile loaded at prompt assembly time, injected into system prompt as `## User Preferences` section (200-token budget). Shapes tool behavior (e.g., skip confirmation for users with auto-approve preference).

**Safety pair:** Configurable TTL per preference dimension. User can reset profile via admin-api. Opt-out via `USER_MODELING_ENABLED=false`.

**Relationship to Epic 68:** Proactive agent (68.3) can query user_profiles for risk tolerance when deciding autonomous execution threshold.

**Files:**
- `domains/automation-core/ha-ai-agent-service/src/services/user_modeling/profile_store.py`
- `domains/automation-core/ha-ai-agent-service/src/services/user_modeling/preference_extractor.py`
- `domains/automation-core/ha-ai-agent-service/src/services/user_modeling/profile_injector.py`
- `domains/automation-core/ha-ai-agent-service/alembic/versions/XXX_add_user_profiles_table.py`

**Tasks:**
- [ ] Create `agent.user_profiles` table (user_id, dimension, value, confidence, updated_at, expires_at)
- [ ] Implement ProfileStore (CRUD + dimension queries)
- [ ] Implement PreferenceExtractor (analyze conversation → extract preference signals)
- [ ] Implement ProfileInjector (load profile → format for system prompt)
- [ ] Wire extraction as fire-and-forget background task in chat_endpoints.py
- [ ] Wire injection into prompt_assembly_service.py (200-token budget)
- [ ] Add admin-api endpoint: GET/DELETE /api/v1/user-profiles/{user_id}
- [ ] Add USER_MODELING_ENABLED, PROFILE_TTL_DAYS=90 env vars
- [ ] Write unit tests for store, extractor, injector

---

### 70.8 -- Prompt Caching

**Points:** 2

Apply cache control markers to system prompt + last 3 turns to reduce input token costs. Ported from Hermes `prompt_caching.py`.

**Strategy:** `system_and_3` — mark system prompt (stable across turns) + last 3 non-system messages with cache_control headers. Reduces input token costs ~75% on multi-turn conversations.

**Provider support:**
- Anthropic: native `cache_control: {"type": "ephemeral"}` with 5min TTL
- OpenAI: automatic context caching (no explicit markers needed, but structure messages to maximize cache hits)

**Implementation:** Applied in openai_client.py before API calls. For OpenAI, restructure messages to keep system prompt stable (maximize automatic caching). For Anthropic (if added via 70.3 multi-model), apply explicit cache markers.

**Files:**
- `domains/automation-core/ha-ai-agent-service/src/services/prompt_caching.py`

**Tasks:**
- [ ] Implement apply_cache_control(messages, strategy="system_and_3") for Anthropic format
- [ ] Implement message restructuring for OpenAI automatic caching (stable system prompt prefix)
- [ ] Wire into openai_client.py before API call
- [ ] Add PROMPT_CACHING_ENABLED env var
- [ ] Track cache hit rates and cost savings in logs
- [ ] Write unit tests (marker placement, message format handling)

<!-- docsmcp:end:stories -->

---

<!-- docsmcp:start:dependency-graph -->
## Dependency Graph

```
70.1 Skill Learning ─┬─► 70.2 Skills Guard (MUST ship together)
                     │
70.3 Smart Routing ──┼─► 70.4 Context Compression (uses cheap model)
                     │   70.5 Subagent Delegation (routes subagents to cheap model)
                     │   70.6 Session Search (uses cheap model for summarization)
                     │
70.7 User Modeling ──┘   (enhances skill recall + delegation decisions)
70.8 Prompt Caching      (independent — ship whenever convenient)
```

**Recommended execution order:**
1. **70.3** Smart Model Routing (unblocks 70.4, 70.5, 70.6)
2. **70.1 + 70.2** Skill Learning + Skills Guard (ship together)
3. **70.4** Context Compression
4. **70.5** Subagent Delegation
5. **70.6** Session Search
6. **70.7** User Modeling
7. **70.8** Prompt Caching

Stories 70.1+70.2 can run in parallel with 70.4 (after 70.3 ships).
Stories 70.5 and 70.6 can run in parallel.
Story 70.8 is fully independent.

<!-- docsmcp:end:dependency-graph -->

---

<!-- docsmcp:start:definition-of-done -->
## Definition of Done (all stories)

1. Implementation complete with type hints
2. Unit tests pass (pytest)
3. `tapps_quick_check` passes on all new/modified Python files
4. Feature behind env var kill switch (default: enabled)
5. No runtime dependency on hermes-agent package
6. Observability: structured logging for all new operations
7. Alembic migration tested (up + down)

<!-- docsmcp:end:definition-of-done -->

---

<!-- docsmcp:start:risks -->
## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Skill extraction produces low-quality procedures | Agent recalls bad advice | Skills Guard scanning + use_count tracking (prune unused skills after 90 days) |
| Subagent token costs spiral | Unexpected API bills | Per-subagent budget caps, delegation disabled by default for cost-sensitive deployments |
| Context compression loses critical context | Agent forgets user intent mid-conversation | Protect first 3 + last 4 turns, graceful fallback to truncation on summarization failure |
| Smart routing sends complex queries to cheap model | Quality degradation | Conservative heuristics (keyword blocklist), fallback to primary on any uncertainty, Epic 69 adds eval-driven correction |
| Session search returns irrelevant past conversations | Noisy context injection | Top-3 limit, relevance summarization, exclude current session |

<!-- docsmcp:end:risks -->

---

<!-- docsmcp:start:metrics -->
## Success Metrics

| Metric | Baseline | Target |
|---|---|---|
| Repeat automation conversations (same pattern, different room) | 5+ turns | 1-2 turns (skill recalled) |
| API cost per simple query | ~$0.02 (gpt-5.2-codex) | ~$0.002 (gpt-4.1-mini) — 90% reduction |
| Max conversation length before context loss | ~16K tokens (hard truncation) | ~32K tokens (compression extends usable window 2x) |
| Multi-area request completion time | Sequential (N × single) | Parallel (single + overhead) — ~3x faster for 3 areas |
| Cross-session context recall | None | Top-3 relevant sessions summarized |

<!-- docsmcp:end:metrics -->
