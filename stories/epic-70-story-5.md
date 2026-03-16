# Story 70.5 -- Subagent Delegation

<!-- docsmcp:start:user-story -->

> **As a** user, **I want** to say "set up automations for the kitchen, bedroom, and living room" and have the agent work on all three areas in parallel, **so that** complex multi-area requests complete ~3x faster

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that ha-ai-agent-service can decompose multi-area requests into parallel subagent loops, each with area-scoped context and restricted toolsets, completing multi-area work ~3x faster than sequential processing.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Implement subagent delegation ported from Hermes Agent `delegate_tool.py`. Parent agent spawns up to 3 parallel child `_run_openai_loop()` instances. Each child gets area-filtered context (only entities/devices from its assigned area), restricted toolset (no delegation, no skill saving), fresh conversation, and a per-subagent token budget. Parent blocks until all children complete, then synthesizes results.

See [Epic 70](stories/epic-70-hermes-self-improving-agent.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ha-ai-agent-service/src/services/delegation/__init__.py`
- `domains/automation-core/ha-ai-agent-service/src/services/delegation/delegate_service.py`
- `domains/automation-core/ha-ai-agent-service/src/services/delegation/subagent_runner.py`
- `domains/automation-core/ha-ai-agent-service/src/tools/delegate_tools.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Implement `SubagentRunner.run(goal, context, area_id, toolsets, max_iterations=15, max_tokens=8000) → SubagentResult`
- [ ] SubagentRunner wraps `_run_openai_loop()` with scoped OpenAI client and area-filtered context
- [ ] Implement area-scoped context builder: filter `context_builder` output by area_id (only entities, devices, automations for that area)
- [ ] Implement `DelegateService.delegate(tasks: list[DelegateTask]) → list[SubagentResult]` using `asyncio.gather()`
- [ ] DelegateTask: goal (str), context (str), area (str), toolsets (list[str]), max_iterations (int)
- [ ] SubagentResult: status (completed/failed/budget_exceeded), summary (str), tool_trace (list), tokens_used (int), duration_ms (int)
- [ ] Restricted toolset for subagents: remove `delegate_task`, `save_automation_skill`, `search_past_conversations`
- [ ] Per-subagent token budget enforcement: terminate loop if output tokens exceed max_tokens
- [ ] Add `delegate_task` tool schema: single task (goal + context + area) or batch (tasks array, max 3)
- [ ] Wire into tool_execution.py as a tool handler
- [ ] Parent synthesizes child results into unified response message
- [ ] Add DELEGATION_ENABLED (default true), MAX_SUBAGENTS (default 3), SUBAGENT_MAX_TOKENS (default 8000) to config.py
- [ ] Log subagent lifecycle: spawned (task_id, area, goal), completed (status, duration, tokens), failed (error)
- [ ] Write unit tests: single delegation, batch delegation, budget exceeded, area scoping, toolset restriction

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] `delegate_task` tool available to the agent with single and batch modes
- [ ] Batch mode runs up to 3 subagents in parallel via asyncio.gather
- [ ] Each subagent gets area-filtered context (only entities/devices from assigned area)
- [ ] Subagents cannot call delegate_task (no recursive delegation)
- [ ] Subagents cannot call save_automation_skill (no skill creation from subagents)
- [ ] Per-subagent token budget enforced (loop terminates on exceed, returns partial result)
- [ ] Parent receives structured results from all subagents
- [ ] Feature disabled when DELEGATION_ENABLED=false

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 70](stories/epic-70-hermes-self-improving-agent.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_delegate_single_task` -- Single delegation spawns one subagent, returns result
2. `test_delegate_batch_parallel` -- 3-task batch runs in parallel, all results returned
3. `test_delegate_area_scoped_context` -- Subagent only sees entities from assigned area
4. `test_delegate_restricted_toolset` -- Subagent cannot call delegate_task or save_automation_skill
5. `test_delegate_budget_exceeded` -- Subagent terminated at token budget, returns partial result
6. `test_delegate_max_subagents_enforced` -- Batch with 5 tasks rejects (max 3)
7. `test_delegate_subagent_failure_isolated` -- One subagent fails, others complete normally
8. `test_delegate_disabled_via_env` -- Tool unavailable when DELEGATION_ENABLED=false

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 70.3 (Smart Model Routing) — subagents can route to cheap model for simple subtasks
- Epic 60 (Chat Endpoint Refactor, complete) — `_run_openai_loop()` extracted and reusable

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Can function without other 70.x stories (uses primary model if 70.3 not available)
- [x] **N**egotiable -- Max subagents, token budget, restricted toolsets all configurable
- [x] **V**aluable -- ~3x faster multi-area requests, new capability
- [x] **E**stimable -- Clear scope: runner + service + tool + integration
- [ ] **S**mall -- 5 points, borderline — runner and service are tightly coupled
- [x] **T**estable -- Parallel execution, budget enforcement, area scoping all testable

<!-- docsmcp:end:invest -->
