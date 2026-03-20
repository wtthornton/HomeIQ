# Epic 97: Prompt Caching & Claude Provider

**Priority:** P1 High — Cost Reduction
**Effort:** 1–2 weeks (6 stories, 22 points)
**Sprint:** 44
**Depends on:** Epic 94 (Prompt Sections to Config — helpful but not blocking)
**Origin:** Sapphire Review — 2026 Research Recommendation #2

## Problem Statement

Every `ha-ai-agent-service` request sends 10K–30K tokens of static context to OpenAI GPT-5.2:
- System prompt (~3K tokens, Section 0–9)
- Entity inventory (~5K–15K tokens, all entities by area)
- Binary sensors (~1K tokens)
- Existing automations (~1K tokens)
- RAG context (~2K–5K tokens)
- Automation patterns (~1K tokens)
- Trigger platforms reference (~500 tokens)

This static prefix is identical across conversations. With OpenAI, it's paid in full every request. Anthropic's prompt caching reduces repeated prefix costs by ~90% — cached tokens cost 1/10th of uncached.

Additionally, HomeIQ is locked to a single LLM provider (OpenAI GPT-5.2). Adding Claude as an alternative provides:
1. **Cost reduction** via prompt caching (primary motivation)
2. **Provider redundancy** — if OpenAI goes down, Claude takes over
3. **Quality comparison** — Claude's extended thinking may improve complex automation generation
4. **Leverage existing HomeIQ architecture** — `proactive-agent-service` already has multi-provider patterns

HA 2026.3 already uses Anthropic prompt caching — it's proven in the HA ecosystem.

## Approach

1. Add Claude/Anthropic SDK as an LLM provider in `ha-ai-agent-service`
2. Implement prompt caching with `cache_control` breakpoints on static prefix
3. Add provider selection config (GPT-5.2 or Claude, with fallback)
4. Benchmark cost and quality side-by-side

---

## Story 97.1: Add Anthropic SDK & Claude Provider

**Points:** 5 | **Type:** Feature
**Goal:** `ha-ai-agent-service` can call Claude models via Anthropic API

### Tasks

- [x] **97.1.1** Add `anthropic>=0.40.0` to `requirements.txt`
- [x] **97.1.2** Add settings to `config.py`:
  ```python
  anthropic_api_key: SecretStr | None = None
  anthropic_model: str = "claude-sonnet-4-6"  # Default to cost-effective model
  llm_provider: str = "openai"  # "openai" or "anthropic"
  llm_fallback_provider: str | None = "openai"  # Fallback if primary fails
  ```
- [x] **97.1.3** Create `src/clients/anthropic_client.py`:
  ```python
  class AnthropicLLMClient:
      """Claude LLM client with prompt caching support."""

      def __init__(self, api_key: str, model: str):
          self.client = anthropic.AsyncAnthropic(api_key=api_key)
          self.model = model

      async def chat_completion(
          self,
          system_prompt: str,
          messages: list[dict],
          tools: list[dict] | None = None,
          max_tokens: int = 4096,
      ) -> LLMResponse:
          """
          Call Claude API with OpenAI-compatible message format.
          Handles format translation internally.
          """
          ...
  ```
- [x] **97.1.4** Translate between OpenAI message format (used throughout HomeIQ) and Anthropic format:
  - OpenAI `{"role": "system", "content": "..."}` → Anthropic `system` parameter
  - OpenAI tool calling format → Anthropic tool use format
  - Anthropic `tool_use` blocks → OpenAI `tool_calls` format (for downstream processing)
- [x] **97.1.5** Create `LLMResponse` dataclass (provider-agnostic):
  ```python
  @dataclass
  class LLMResponse:
      content: str
      tool_calls: list[ToolCall] | None
      usage: TokenUsage
      model: str
      provider: str  # "openai" or "anthropic"
      cached_tokens: int  # Prompt cache hit tokens
  ```
- [x] **97.1.6** Add unit tests with mocked Anthropic API

### Acceptance Criteria

- [x]Claude API call succeeds with system prompt + user message
- [x]Tool calling works (preview/create/suggest automation tools)
- [x]Response is normalized to `LLMResponse` format
- [x]OpenAI message format transparently translated to/from Anthropic

---

## Story 97.2: Implement Prompt Caching

**Points:** 5 | **Type:** Feature
**Goal:** Static prompt prefix is cached via Anthropic's prompt caching, reducing token costs ~90%

### Tasks

- [x] **97.2.1** Identify cache breakpoints in the prompt assembly pipeline:
  ```
  ┌─────────────────────────────┐
  │  System Prompt (Sections 0-9) │  ← CACHE BREAKPOINT 1 (stable across all requests)
  │  ~3K tokens                   │
  ├─────────────────────────────┤
  │  Entity Inventory             │  ← CACHE BREAKPOINT 2 (stable for ~5 min, refreshes periodically)
  │  ~5K-15K tokens               │
  ├─────────────────────────────┤
  │  RAG + Patterns + Sensors     │  ← CACHE BREAKPOINT 3 (stable per conversation)
  │  ~3K-5K tokens                │
  ├─────────────────────────────┤
  │  Conversation History         │  ← NOT CACHED (changes every message)
  │  User Message                 │
  └─────────────────────────────┘
  ```
- [x] **97.2.2** Add `cache_control: {"type": "ephemeral"}` to system prompt content blocks:
  ```python
  system = [
      {
          "type": "text",
          "text": system_prompt_text,
          "cache_control": {"type": "ephemeral"}
      },
      {
          "type": "text",
          "text": entity_context,
          "cache_control": {"type": "ephemeral"}
      }
  ]
  ```
- [x] **97.2.3** Track cache hit rate in `LLMResponse.cached_tokens`
- [x] **97.2.4** Log cache performance: `"Prompt cache: {cached_tokens}/{total_input_tokens} tokens cached ({pct}%)"`
- [x] **97.2.5** Add metrics: `homeiq_llm_cache_hit_tokens_total`, `homeiq_llm_cache_miss_tokens_total`
- [x] **97.2.6** Unit tests: verify cache_control blocks are set correctly in API calls

### Acceptance Criteria

- [x]First request: 0% cache hit (cold cache)
- [x]Second request (same conversation): ≥80% cache hit on system prompt
- [x]Subsequent requests: ≥90% cache hit on system + entity context
- [x]Cache hit rate logged and available in Prometheus metrics

---

## Story 97.3: Provider Selection & Fallback

**Points:** 3 | **Type:** Feature
**Goal:** Configurable LLM provider with automatic fallback

### Tasks

- [x] **97.3.1** Create `src/services/llm_router.py`:
  ```python
  class LLMRouter:
      """Routes LLM calls to configured provider with fallback."""

      def __init__(self, settings: Settings):
          self.primary = self._create_client(settings.llm_provider, settings)
          self.fallback = self._create_client(settings.llm_fallback_provider, settings) if settings.llm_fallback_provider else None
          self.circuit_breaker = CircuitBreaker(
              failure_threshold=3,
              recovery_timeout=60,
              half_open_timeout=120,
          )

      async def chat_completion(self, **kwargs) -> LLMResponse:
          try:
              return await self.circuit_breaker.call(
                  self.primary.chat_completion, **kwargs
              )
          except CircuitBreakerOpen:
              if self.fallback:
                  logger.warning("Primary LLM provider down, using fallback")
                  return await self.fallback.chat_completion(**kwargs)
              raise
  ```
- [x] **97.3.2** Wire `LLMRouter` into `prompt_assembly_service.py` (replace direct OpenAI client usage)
- [x] **97.3.3** Support env var override: `LLM_PROVIDER=anthropic` to switch without config change
- [x] **97.3.4** Add health check: `/api/v1/health` reports primary and fallback provider status
- [x] **97.3.5** Add unit tests: primary fails → fallback activates; circuit breaker opens/closes

### Acceptance Criteria

- [x]`LLM_PROVIDER=anthropic` → Claude is primary, GPT-5.2 is fallback
- [x]Primary provider 3 failures → circuit breaker opens → fallback activates
- [x]Primary recovers → circuit breaker half-opens → back to primary
- [x]Health endpoint shows both provider statuses

---

## Story 97.4: Tool Schema Translation

**Points:** 3 | **Type:** Feature
**Goal:** HomeIQ's 3 OpenAI-format tool schemas work with Claude's tool use format

### Tasks

- [x] **97.4.1** Create `src/utils/tool_translator.py`:
  ```python
  def openai_tools_to_anthropic(tools: list[dict]) -> list[dict]:
      """Convert OpenAI function calling schema to Anthropic tool use schema."""
      # OpenAI: {"type": "function", "name": "...", "parameters": {...}}
      # Anthropic: {"name": "...", "description": "...", "input_schema": {...}}
      ...

  def anthropic_tool_result_to_openai(tool_use_block: dict) -> dict:
      """Convert Anthropic tool_use response to OpenAI tool_calls format."""
      ...
  ```
- [x] **97.4.2** Translate HomeIQ's 3 tools (`HA_TOOLS` in `tool_schemas.py`):
  - `preview_automation_from_prompt`
  - `create_automation_from_prompt`
  - `suggest_automation_enhancements`
- [x] **97.4.3** Handle tool result submission: Anthropic requires `tool_result` blocks, OpenAI uses `tool` role messages
- [x] **97.4.4** Add round-trip tests: OpenAI format → Anthropic format → call → response → OpenAI format

### Acceptance Criteria

- [x]All 3 HomeIQ tools work with Claude (preview, create, suggest)
- [x]Tool call arguments are correctly parsed from Claude responses
- [x]Tool results are correctly submitted back to Claude for follow-up
- [x]Multi-step tool calling works (preview → approval → create)

---

## Story 97.5: Cost & Quality Benchmarking

**Points:** 3 | **Type:** Testing
**Goal:** Quantify cost savings and quality comparison between GPT-5.2 and Claude

### Tasks

- [x] **97.5.1** Create benchmark script: `scripts/benchmark_llm_providers.py`
  - 20 representative automation prompts (simple, complex, multi-entity, sports, motion)
  - Run each through both providers
  - Compare: token usage, cost, cache hit rate, response quality, YAML validity
- [x] **97.5.2** Quality scoring:
  - YAML validation pass rate (via yaml-validation-service)
  - Entity resolution accuracy (correct entity_ids used)
  - Instruction following (preview before create, no direct execution)
- [x] **97.5.3** Cost comparison:
  ```
  | Provider        | Avg Input Tokens | Avg Output Tokens | Cost/Request | Cache Savings |
  |-----------------|------------------|-------------------|--------------|---------------|
  | GPT-5.2         |       ?          |        ?          |      ?       |     N/A       |
  | Claude Sonnet   |       ?          |        ?          |      ?       |      ?%       |
  | Claude (cached) |       ?          |        ?          |      ?       |      ?%       |
  ```
- [x] **97.5.4** Write results to `docs/LLM_BENCHMARK.md`
- [x] **97.5.5** Recommend default provider based on results

### Acceptance Criteria

- [x]20 prompts tested on both providers
- [x]Cost comparison shows ≥50% savings with Claude prompt caching
- [x]Quality comparison shows no significant degradation
- [x]Recommendation documented with data

---

## Story 97.6: Extended Thinking for Complex Automations

**Points:** 3 | **Type:** Enhancement
**Goal:** Use Claude's extended thinking for complex multi-trigger/multi-action automations

### Tasks

- [x] **97.6.1** Add complexity detection in `prompt_assembly_service.py`:
  ```python
  def _is_complex_automation(self, user_message: str) -> bool:
      """Detect if automation request is complex enough for extended thinking."""
      indicators = [
          len(user_message) > 200,                    # Long description
          user_message.count(" and ") > 2,             # Multiple conditions
          any(kw in user_message.lower() for kw in     # Complex patterns
              ["if then else", "between", "unless", "except when",
               "multiple", "sequence", "chain", "schedule"]),
      ]
      return sum(indicators) >= 2
  ```
- [x] **97.6.2** Enable `thinking` parameter for complex automations:
  ```python
  if self._is_complex_automation(user_message):
      response = await self.anthropic_client.chat_completion(
          ...,
          thinking={"type": "enabled", "budget_tokens": 4096}
      )
  ```
- [x] **97.6.3** Parse thinking blocks from response (log for debugging, don't show to user)
- [x] **97.6.4** Compare quality: complex automations with vs without thinking (accuracy of YAML, entity resolution, trigger logic)
- [x] **97.6.5** Add unit tests: complexity detection, thinking block parsing

### Acceptance Criteria

- [x]Simple requests ("turn on office lights at sunset") → no extended thinking (saves tokens)
- [x]Complex requests ("if motion in office and it's after sunset, turn on lights unless they're already on, and also set temperature to 72") → extended thinking enabled
- [x]Thinking blocks logged for debugging but not shown in UI
- [x]Quality improvement measurable on complex automation benchmark set

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Anthropic API key management | Same pattern as OpenAI key — `ANTHROPIC_API_KEY` in `.env` |
| Tool calling format differences | Translator handles bidirectional conversion; round-trip tests |
| Prompt caching invalidation | Cache breakpoints at stable boundaries; entity context refreshes trigger new cache |
| Claude produces different YAML style | YAML validation service catches all structural issues; style differences are acceptable |
| Cost of running both providers | Benchmark first; only pay for active provider (fallback = cold standby) |
| Extended thinking token cost | Only enabled for complex automations; budget capped at 4096 tokens |
