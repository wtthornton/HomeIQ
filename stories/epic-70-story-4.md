# Story 70.4 -- Context Compression

<!-- docsmcp:start:user-story -->

> **As a** user building a complex automation, **I want** long conversations to be intelligently compressed rather than truncated, **so that** the agent retains my intent and prior decisions across extended multi-turn interactions

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that conversations exceeding 50% of the context window are intelligently compressed (protect first 3 + last 4 turns, summarize middle) rather than crudely truncated. This extends usable conversation length from ~16K to ~32K effective tokens.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Implement context compression using the protection-and-summarization algorithm from Hermes Agent `context_compressor.py`. When token count exceeds threshold, protect head and tail turns, summarize the middle via cheap model (from 70.3). Includes orphaned tool_call/tool_result pair sanitization to prevent API errors after compression.

See [Epic 70](stories/epic-70-hermes-self-improving-agent.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ha-ai-agent-service/src/services/context_compressor.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Implement `ContextCompressor.should_compress(messages, threshold_pct=0.5) → bool` using tiktoken token counting
- [ ] Implement `ContextCompressor.compress(messages, protect_head=3, protect_tail=4) → compressed_messages`
- [ ] Implement summarization prompt: "Summarize the following conversation turns. Extract: actions taken (tool calls, results), decisions made, data needed to resume. Target ~2500 tokens."
- [ ] Implement orphan sanitization: detect tool_call messages without matching tool_result (and vice versa), remove orphaned pairs
- [ ] Use cheap model from 70.3 for summarization (temperature=0.3)
- [ ] Graceful fallback: if summarization fails, drop middle turns without summary
- [ ] Wire into `prompt_assembly_service.py` replacing current truncation logic
- [ ] Add CONTEXT_COMPRESSION_ENABLED (default true), COMPRESSION_THRESHOLD_PCT (default 0.5) to config.py
- [ ] Log compression stats: tokens_before, tokens_after, turns_compressed, turns_protected
- [ ] Write unit tests: threshold detection, turn protection, orphan cleanup, summarization, fallback

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Compression triggers when tokens exceed 50% of context window
- [ ] First 3 turns (system + initial exchange) always preserved verbatim
- [ ] Last 4 turns (recent context) always preserved verbatim
- [ ] Middle turns summarized into ~2500 token summary
- [ ] Orphaned tool_call/tool_result pairs sanitized after compression
- [ ] Summarization failure falls back to dropping middle turns
- [ ] Compression stats logged (tokens before/after, turns compressed)
- [ ] Feature disabled when CONTEXT_COMPRESSION_ENABLED=false

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 70](stories/epic-70-hermes-self-improving-agent.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_should_compress_below_threshold` -- 40% token usage → no compression
2. `test_should_compress_above_threshold` -- 60% token usage → triggers compression
3. `test_compress_protects_head_turns` -- First 3 turns preserved verbatim
4. `test_compress_protects_tail_turns` -- Last 4 turns preserved verbatim
5. `test_compress_summarizes_middle` -- Middle turns replaced with summary message
6. `test_compress_sanitizes_orphaned_tool_calls` -- Unpaired tool_call removed
7. `test_compress_sanitizes_orphaned_tool_results` -- Unpaired tool_result removed
8. `test_compress_fallback_on_summarization_failure` -- Drops middle turns without summary

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 70.3 (Smart Model Routing) — uses cheap model for summarization

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Only depends on 70.3 for cheap model (can hardcode model as fallback)
- [x] **N**egotiable -- Threshold, head/tail counts, summary token target all tunable
- [x] **V**aluable -- Extends usable conversation length ~2x
- [x] **E**stimable -- Clear scope: single module with well-defined algorithm
- [x] **S**mall -- 3 points, single file
- [x] **T**estable -- Deterministic threshold + turn protection, mockable summarization

<!-- docsmcp:end:invest -->
